"""
---

id_self:                pym_cctool.gate.gate
guid_self:              pym_6bb604090d8f4b4f8a067eac451fce87
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate
brief:                  |
                        Check, lint and test the content that a commit
                        would record.
description:            |
                        The gate copies the staged content of a
                        repository, which is what a commit records,
                        into a temporary directory, and runs each
                        stage in that copy. The copy's own source is
                        first on the python path, so the code that a
                        commit records is the code that checks it. An
                        unstaged edit in the working copy can neither
                        fail a commit nor let one pass.

                        The check of a commit keeps what it finds in a
                        store in the git directory, and reuses it for
                        files unchanged since, as long as the code
                        that found it is unchanged too. The gate of a
                        push uses no store.

                        A stage runs without the git environment of
                        the hook that started it, so that a test which
                        makes a repository of its own cannot touch the
                        index of the commit.

                        A commit that stages no code, only data, runs
                        only the tests that read the data of the
                        repository or a copy of it, and a commit that
                        stages only decisions, which the tests do not
                        need to see, runs none. The gate of a push
                        runs every test on what is pushed. The tests
                        marked prepush, which test the commit and
                        history machinery, are left to the gate of a
                        push too.

                        The stages run side by side, and pytest-xdist
                        hands the tests out to one worker for each
                        processor, so that the gate takes about as
                        long as its tests take divided among the
                        processors.

                        Each run times its stages and appends a line
                        for each to a log of timings in the git
                        directory, as ruling_cpp_built_when_staged
                        asks, so that what a change costs the gate can
                        be seen later.
usage:                  |
                        cctool gate [--root DIRPATH]

                        Run before each commit by
                        .githooks/pre-commit.
edge:                   []

...
"""


import concurrent.futures
import datetime
import io
import os
import pathlib
import platform
import resource
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

import cctool.check.store
import cctool.gate.timing


# The tests that the gate of a push runs, those that the gate of a
# commit runs, and those that it runs when the commit stages data but no
# code. The tests marked prepush test the commit and history machinery,
# and are left to the gate of a push. The tests marked reads_data read
# the data of the repository, or a copy of it, so a change to the data
# alone can break them.
#
MARK_PUSH     = 'not slow'
MARK_COMMIT   = 'not slow and not prepush'
MARK_DATA     = 'reads_data and not slow and not prepush'

# Each stage: its name, and the command that runs it in the root of the
# copy. {python} is the interpreter that runs the gate. The tests run on
# one worker for each processor, each worker taking the next test when
# it is free, and the tests marked slow are left out: they grow with the
# data, or repeat the check stage. pytest reports the seconds of each
# test to {report}, a file outside the copy, in JUnit XML.
#
TUPLE_STAGE   = (('check', ('{python}', '-m', 'cctool.cli.command', 'check')),
                 ('lint',  ('ruff', 'check', '--no-cache', 'src')),
                 ('test',  ('{python}', '-m', 'pytest', '-p', 'no:cacheprovider',
                            '-n', 'auto', '--dist', 'worksteal', '-m', MARK_PUSH,
                            '--junitxml={report}')))
DIR_SOURCE    = 'src'
NAME_TEST     = 'test'

# The paths that hold code, or what the code runs with. A commit that
# stages none of them changes no code, so its gate leaves out the
# tests, which test the code. The gate of a push runs every stage on
# what is pushed, so a test that the data breaks is still caught there.
#
# The skills and AGENTS.md count as code: they quote cctool commands,
# and the tests check those quotes, so that the guidance for agents is
# kept aligned with the code of the command line.
#
TUPLE_CODE    = ('src/', 'pyproject.toml', 'pixi.lock', '.githooks/', '.agents/skills/',
                 'AGENTS.md')

# The paths whose change no test needs to see: the decisions. A copy
# made for a test holds the frozen decisions of the fixture in place of
# those of the repository, and the one test that reads the decisions of
# the repository repeats the check of their layout, which the check
# stage makes anyway. A commit that stages only these leaves out the
# tests.
#
TUPLE_UNREAD  = ('_data/decision/',)

PREFIX_GIT    = 'GIT_'
PREFIX_COPY   = 'cc_gate_'
PREFIX_REPORT = 'cc_gate_report_'
FILE_REPORT   = 'junit.xml'
DIR_STORE     = 'cctool_store'

# What a stage came to, as the log of timings records it.
#
OUTCOME_OK    = 'passed'
OUTCOME_FAIL  = 'failed'
OUTCOME_STOP  = 'stopped'

# A stage that runs longer than this, in seconds, is stopped and fails,
# so that a stage that hangs cannot hold a commit for ever. The whole
# gate takes about a minute and a half on two processors.
#
SECONDS_STAGE = 600


# -----------------------------------------------------------------------------
class ErrorGate(Exception):
    """
    The gate cannot be run.

    """


# -----------------------------------------------------------------------------
def gate(root:        pathlib.Path,
         tuple_stage: tuple | None = None,
         rev:         str | None = None,
         seconds:     float = SECONDS_STAGE) -> list[tuple[str, bool, str]]:
    """
    Return, for each stage in order, its name, whether it passed, and
    what it printed, run over the staged content of the repository at
    root, or over the content of the commit rev if it is given. The
    stages are TUPLE_STAGE unless tuple_stage names others. A stage
    that runs for longer than seconds is stopped, and fails. The time
    of each stage is appended to the log of timings.

    """

    tuple_stage = tuple_stage or TUPLE_STAGE
    start       = datetime.datetime.now(datetime.UTC).isoformat(timespec = 'seconds')
    usage       = resource.getrusage(resource.RUSAGE_CHILDREN)

    with (tempfile.TemporaryDirectory(prefix = PREFIX_COPY) as name,
          tempfile.TemporaryDirectory(prefix = PREFIX_REPORT) as name_report):
        dir_copy    = pathlib.Path(name)
        path_report = pathlib.Path(name_report) / FILE_REPORT
        if rev is None:
            copy_staged(root, dir_copy)
        else:
            copy_commit(root, rev, dir_copy)
        env         = _environment(dir_copy)
        env.pop(cctool.check.store.ENV_STORE, None)
        if rev is None:
            env[cctool.check.store.ENV_STORE] = str(store(root))
        list_job    = [[arg.format(python = sys.executable, report = path_report)
                        for arg in tuple_arg]
                       for (_, tuple_arg) in tuple_stage]

        with concurrent.futures.ThreadPoolExecutor(max_workers = len(list_job)) as executor:
            list_done = list(executor.map(lambda list_arg: _run(list_arg, dir_copy, env, seconds),
                                          list_job))

        map_test    = cctool.gate.timing.durations(path_report)

    cctool.gate.timing.append(timing_log(root),
                              _timings(root, rev, tuple_stage, list_done, start, usage, map_test))

    return [(name_stage, outcome == OUTCOME_OK, printed)
            for ((name_stage, _), (outcome, printed, _)) in zip(tuple_stage, list_done,
                                                                 strict = True)]


# -----------------------------------------------------------------------------
def _timings(root:        pathlib.Path,
             rev:         str | None,
             tuple_stage: tuple,
             list_done:   list[tuple[str, str, float]],
             start:       str,
             usage:       resource.struct_rusage,
             map_test:    dict[str, float]) -> list[dict]:
    """
    Return a line of the log of timings for each stage of a run of the
    gate that started at start, when the children of this process had
    used usage: its name, outcome and wall seconds, and what the run
    gated and where. The stages run side by side, so the processor
    seconds are those of the whole run, on each line. The line of the
    stage named NAME_TEST holds the seconds of each test in map_test.

    """

    after    = resource.getrusage(resource.RUSAGE_CHILDREN)
    run      = uuid.uuid4().hex
    map_base = {'run':             run,
                'start':           start,
                'seconds_cpu_run': round(after.ru_utime + after.ru_stime
                                         - usage.ru_utime - usage.ru_stime, 3),
                'tree':            _digest(root, rev),
                'commit':          None if rev is None else _git(root, rev + '^{commit}'),
                'host':            platform.node(),
                'python':          platform.python_version()}

    list_line = []
    for ((name_stage, _), (outcome, _, seconds)) in zip(tuple_stage, list_done, strict = True):
        line = {'stage': name_stage, **map_base, 'seconds': round(seconds, 3),
                'outcome': outcome}
        if name_stage == NAME_TEST:
            line['tests'] = map_test
        list_line.append(line)

    return list_line


# -----------------------------------------------------------------------------
def _digest(root: pathlib.Path, rev: str | None) -> str | None:
    """
    Return the digest of the tree that the gate of root runs over: that
    of the commit rev, or of the staged content if rev is None. It is
    None if git cannot give it, as when the index holds a conflict.

    """

    if rev is not None:
        return _git(root, rev + '^{tree}')

    try:
        return subprocess.run(['git', 'write-tree'],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


# -----------------------------------------------------------------------------
def _git(root: pathlib.Path, rev: str) -> str | None:
    """
    Return the object name that rev names in the repository at root, or
    None if it names none.

    """

    try:
        return subprocess.run(['git', 'rev-parse', '--verify', '--quiet', rev],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout.strip()
    except subprocess.CalledProcessError:
        return None


# -----------------------------------------------------------------------------
def stages(root: pathlib.Path) -> tuple:
    """
    Return the stages that gate the staged content of the repository at
    root: TUPLE_STAGE, with the tests marked prepush left out. If no
    code is staged, only the tests marked reads_data run, and none at
    all if only paths of TUPLE_UNREAD are staged.

    """

    list_path = staged(root)
    if list_path is None or any(path.startswith(TUPLE_CODE) for path in list_path):
        mark = MARK_COMMIT
    elif any(not path.startswith(TUPLE_UNREAD) for path in list_path):
        mark = MARK_DATA
    else:
        return tuple(stage for stage in TUPLE_STAGE if stage[0] != NAME_TEST)

    return tuple((name, tuple(mark if arg == MARK_PUSH else arg for arg in tuple_arg))
                 for (name, tuple_arg) in TUPLE_STAGE)


# -----------------------------------------------------------------------------
def is_code_staged(root: pathlib.Path) -> bool:
    """
    Return whether the staged content of the repository at root adds,
    changes or removes a path of TUPLE_CODE. Before the first commit,
    everything staged is new, and code is taken to be staged.

    """

    list_path = staged(root)
    return list_path is None or any(path.startswith(TUPLE_CODE) for path in list_path)


# -----------------------------------------------------------------------------
def staged(root: pathlib.Path) -> list[str] | None:
    """
    Return the paths that the staged content of the repository at root
    adds, changes or removes, or None before the first commit, when
    everything staged is new.

    """

    try:
        text = subprocess.run(['git', 'diff', '--cached', '--name-only', '--no-renames',
                               'HEAD'],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout
    except subprocess.CalledProcessError:
        return None

    return text.splitlines()


# -----------------------------------------------------------------------------
def store(root: pathlib.Path) -> pathlib.Path:
    """
    Return the store of the checker for the gate of a commit of the
    repository at root: a directory in its git directory, which each of
    its worktrees shares.

    """

    return git_dir(root) / DIR_STORE


# -----------------------------------------------------------------------------
def timing_log(root: pathlib.Path) -> pathlib.Path:
    """
    Return the log of timings of the gate of the repository at root: a
    file in its git directory, which each of its worktrees shares.

    """

    return git_dir(root) / cctool.gate.timing.FILE_LOG


# -----------------------------------------------------------------------------
def git_dir(root: pathlib.Path) -> pathlib.Path:
    """
    Return the git directory of the repository at root that each of its
    worktrees shares.

    """

    try:
        name = subprocess.run(['git', 'rev-parse', '--git-common-dir'],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout.strip()
    except subprocess.CalledProcessError as error:
        raise ErrorGate('The git directory cannot be found: {text}'.format(
                                                text = error.stderr.strip())) from error

    return (root / name).resolve()


# -----------------------------------------------------------------------------
def _run(list_arg: list[str],
         dir_copy: pathlib.Path,
         env:      dict[str, str],
         seconds:  float) -> tuple[str, str, float]:
    """
    Return the outcome of the command list_arg in dir_copy, stopped
    after seconds, what it printed, and the wall seconds it took.

    """

    clock = time.perf_counter()
    try:
        done = subprocess.run(list_arg,
                              cwd            = dir_copy,
                              env            = env,
                              capture_output = True,
                              text           = True,
                              check          = False,
                              timeout        = seconds)
    except FileNotFoundError as error:
        raise ErrorGate('{name} cannot be found.'.format(name = list_arg[0])) from error
    except subprocess.TimeoutExpired as error:
        printed = ''.join(each.decode(errors = 'replace') if isinstance(each, bytes) else each
                          for each in (error.stdout, error.stderr) if each)
        return (OUTCOME_STOP,
                printed + 'Stopped after {seconds:g} s, the time limit of a '
                          'stage.\n'.format(seconds = seconds),
                time.perf_counter() - clock)

    return (OUTCOME_OK if done.returncode == 0 else OUTCOME_FAIL,
            done.stdout + done.stderr,
            time.perf_counter() - clock)


# -----------------------------------------------------------------------------
def copy_staged(root: pathlib.Path, dir_copy: pathlib.Path) -> None:
    """
    Write the staged content of the repository at root into dir_copy.

    """

    try:
        subprocess.run(['git', 'checkout-index', '--all',
                        '--prefix={dir}{sep}'.format(dir = dir_copy, sep = os.sep)],
                       cwd            = root,
                       capture_output = True,
                       text           = True,
                       check          = True)
    except subprocess.CalledProcessError as error:
        raise ErrorGate('The staged content cannot be copied: {text}'.format(
                                                text = error.stderr.strip())) from error


# -----------------------------------------------------------------------------
def copy_commit(root: pathlib.Path, rev: str, dir_copy: pathlib.Path) -> None:
    """
    Write the content of the commit rev of the repository at root into
    dir_copy.

    """

    try:
        archive = subprocess.run(['git', 'archive', '--format=tar', rev],
                                 cwd            = root,
                                 capture_output = True,
                                 check          = True).stdout
    except subprocess.CalledProcessError as error:
        raise ErrorGate('The commit {rev} cannot be copied: {text}'.format(
                            rev = rev, text = error.stderr.decode().strip())) from error

    with tarfile.open(fileobj = io.BytesIO(archive)) as file:
        file.extractall(dir_copy, filter = 'data')


# -----------------------------------------------------------------------------
def _environment(dir_copy: pathlib.Path) -> dict[str, str]:
    """
    Return the environment that a stage runs in: this one, without the
    variables git sets for its hooks, and with the source of the copy
    first on the python path.

    """

    env = {key: value for (key, value) in os.environ.items()
           if not key.startswith(PREFIX_GIT)}

    list_path         = [str(dir_copy / DIR_SOURCE), os.environ.get('PYTHONPATH', '')]
    env['PYTHONPATH'] = os.pathsep.join(path for path in list_path if path)

    return env
