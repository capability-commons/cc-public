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

                        Each file is copied as git stores it, from its
                        blob, so that no attribute of the repository,
                        such as export-ignore, export-subst, eol or
                        filter, can change what the stages see. A link
                        is copied as a link, and one that leads out of
                        the tree is refused.

                        A stage runs without the git environment of
                        the hook that started it, so that a test which
                        makes a repository of its own cannot touch the
                        index of the commit. It runs without the
                        variables that steer pytest, cctool or python
                        too, other than the python path it is given,
                        so that the verdict does not depend on the
                        shell that started it.

                        The gate of a commit runs the check and the
                        lint, and no tests: the landing queue runs the
                        tests of a patch on its tip before it lands,
                        and writes a gate result. The gate of a push
                        runs every test not marked slow on what is
                        pushed, unless a gate result proves that the
                        tip passed them.

                        The stages run side by side, and pytest-xdist
                        hands the tests out to one worker for each
                        processor, so that the gate takes about as
                        long as its tests take divided among the
                        processors.

                        A test that is skipped fails the test stage,
                        with its reason, since a test the gate cannot
                        run, as when a tool it needs is missing, tests
                        nothing: a gate that passed it would pass code
                        that no test has run.

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
import os
import pathlib
import platform
import resource
import subprocess
import sys
import tempfile
import time
import uuid

import cctool.check.store
import cctool.gate.timing


# The tests that the gate of a push runs, and the landing queue on the
# tip of each patch: every test but those marked slow.
#
MARK_PUSH     = 'not slow'

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

# The stages of the gate of a commit: those of a push but the tests,
# which the landing queue runs on each patch before it lands, so that a
# commit takes seconds. A stage that makes a commit slow is a defect.
#
TUPLE_COMMIT  = tuple(stage for stage in TUPLE_STAGE if stage[0] != NAME_TEST)

# The variables a stage runs without: those git sets for its hooks, and
# those that would change what pytest, cctool or python does. The python
# path is set for the stage afresh.
#
TUPLE_UNSET   = ('GIT_', 'PYTEST_', 'CCTOOL_', 'PYTHON')
ENV_PATH      = 'PYTHONPATH'

# The modes of the entries of a git tree or index: a file, one that may
# be run, and a link. An entry of a submodule, a commit, holds no
# content in this repository and is passed over.
#
MAP_MODE      = {'100644': 0o644, '100755': 0o755}
MODE_LINK     = '120000'
MODE_MODULE   = '160000'
STAGE_MERGED  = '0'

PREFIX_COPY   = 'cc_gate_'
PREFIX_REPORT = 'cc_gate_report_'
FILE_REPORT   = 'junit.xml'
DIR_STORE     = 'cctool_store'

# Why the test stage fails when a test is skipped.
#
TEXT_SKIPPED  = ('{count} {noun} skipped, and a test the gate cannot run tests nothing. Install '
                 'what each needs, as its reason says, or mark it slow if it belongs only to '
                 'the slow run:\n{lines}\n')

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
        list_failed = cctool.gate.timing.failed(path_report)
        list_done   = _with_skips(tuple_stage, list_done,
                                  cctool.gate.timing.skipped(path_report))

    cctool.gate.timing.append(timing_log(root),
                              _timings(root, rev, tuple_stage, list_done, start, usage, map_test,
                                       list_failed))

    return [(name_stage, outcome == OUTCOME_OK, printed)
            for ((name_stage, _), (outcome, printed, _)) in zip(tuple_stage, list_done,
                                                                 strict = True)]


# -----------------------------------------------------------------------------
def _with_skips(tuple_stage: tuple,
                list_done:   list[tuple[str, str, float]],
                list_skip:   list[tuple[str, str]]) -> list[tuple[str, str, float]]:
    """
    Return list_done, what each stage of tuple_stage came to, with the
    stage named NAME_TEST failed and its skipped tests said if
    list_skip holds any.

    """

    if not list_skip:
        return list_done

    text = TEXT_SKIPPED.format(count = len(list_skip),
                               noun  = 'test was' if len(list_skip) == 1 else 'tests were',
                               lines = '\n'.join('  {test}: {reason}'.format(test   = test,
                                                                              reason = reason)
                                                  for (test, reason) in list_skip))

    return [(OUTCOME_FAIL, printed + text, seconds) if name_stage == NAME_TEST
            else (outcome, printed, seconds)
            for ((name_stage, _), (outcome, printed, seconds)) in zip(tuple_stage, list_done,
                                                                      strict = True)]


# -----------------------------------------------------------------------------
def _timings(root:        pathlib.Path,
             rev:         str | None,
             tuple_stage: tuple,
             list_done:   list[tuple[str, str, float]],
             start:       str,
             usage:       resource.struct_rusage,
             map_test:    dict[str, float],
             list_failed: list[str]) -> list[dict]:
    """
    Return a line of the log of timings for each stage of a run of the
    gate that started at start, when the children of this process had
    used usage: its name, outcome and wall seconds, and what the run
    gated and where. The stages run side by side, so the processor
    seconds are those of the whole run, on each line. The line of the
    stage named NAME_TEST holds the seconds of each test in map_test,
    and names each test of list_failed, which failed.

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
            line['tests']  = map_test
            line['failed'] = list_failed
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
    Write the staged content of the repository at root into dir_copy,
    each file as git stores it.

    """

    what       = 'The staged content'
    list_entry = []

    for record in _listed(root, ['ls-files', '--stage', '-z'], what):
        (info, path)        = record.split(b'\t', 1)
        (mode, name, stage) = info.decode().split()
        if stage != STAGE_MERGED:
            raise ErrorGate('{what} cannot be copied, as {path} is unmerged.'.format(
                                what = what, path = os.fsdecode(path)))
        list_entry.append((mode, name, os.fsdecode(path)))

    _write(root, list_entry, dir_copy, what)


# -----------------------------------------------------------------------------
def copy_commit(root: pathlib.Path, rev: str, dir_copy: pathlib.Path) -> None:
    """
    Write the content of the commit rev of the repository at root into
    dir_copy, each file as git stores it.

    """

    what       = 'The commit {rev}'.format(rev = rev)
    list_entry = []

    for record in _listed(root, ['ls-tree', '-r', '-z', '--full-tree', rev], what):
        (info, path)   = record.split(b'\t', 1)
        (mode, _, name) = info.decode().split()
        list_entry.append((mode, name, os.fsdecode(path)))

    _write(root, list_entry, dir_copy, what)


# -----------------------------------------------------------------------------
def _listed(root: pathlib.Path, list_arg: list[str], what: str) -> list[bytes]:
    """
    Return the records, ended by NUL, that git prints for list_arg in
    the repository at root. what names the content being copied.

    """

    try:
        text = subprocess.run(['git', *list_arg],
                              cwd            = root,
                              capture_output = True,
                              check          = True).stdout
    except subprocess.CalledProcessError as error:
        raise ErrorGate('{what} cannot be copied: {text}'.format(
                            what = what, text = error.stderr.decode().strip())) from error

    return [record for record in text.split(b'\0') if record]


# -----------------------------------------------------------------------------
def _write(root:       pathlib.Path,
           list_entry: list[tuple[str, str, str]],
           dir_copy:   pathlib.Path,
           what:       str) -> None:
    """
    Write each entry of list_entry, its mode, object name and path, into
    dir_copy from the object git holds for it. The links are written
    last, so that no file is written through one, and a link that leads
    out of dir_copy is refused.

    """

    list_entry = [entry for entry in list_entry if entry[0] != MODE_MODULE]
    list_blob  = _blobs(root, [name for (_, name, _) in list_entry], what)
    list_link  = []

    for ((mode, _, path), blob) in zip(list_entry, list_blob, strict = True):
        target = dir_copy / path
        if _is_outside(path):
            raise ErrorGate('{what} cannot be copied, as it holds the path {path}, outside '
                            'the tree.'.format(what = what, path = path))
        if mode == MODE_LINK:
            list_link.append((path, os.fsdecode(blob)))
            continue
        if mode not in MAP_MODE:
            raise ErrorGate('{what} cannot be copied, as {path} has the mode {mode}, which '
                            'is not that of a file.'.format(what = what, path = path,
                                                              mode = mode))
        try:
            target.parent.mkdir(parents = True, exist_ok = True)
            target.write_bytes(blob)
            os.chmod(target, MAP_MODE[mode])
        except OSError as error:
            raise _unwritten(what, path, error) from error

    for (path, link) in list_link:
        if _is_outside(os.path.join(os.path.dirname(path), link)):
            raise ErrorGate('{what} cannot be copied, as it holds a link at {path} to {link}, '
                            'outside the tree.'.format(what = what, path = path, link = link))
        target = dir_copy / path
        try:
            target.parent.mkdir(parents = True, exist_ok = True)
            os.symlink(link, target)
        except OSError as error:
            raise _unwritten(what, path, error) from error


# -----------------------------------------------------------------------------
def _is_outside(path: str) -> bool:
    """
    Return whether path, read from the root of a copy, leads out of it.

    """

    normal = os.path.normpath(path)
    return (os.path.isabs(path)
            or normal == os.pardir
            or normal.startswith(os.pardir + os.sep))


# -----------------------------------------------------------------------------
def _unwritten(what: str, path: str, error: OSError) -> ErrorGate:
    """
    Return the error that says path, of the content what names, cannot
    be written, as error says.

    """

    return ErrorGate('{what} cannot be copied, as {path} cannot be written: {reason}.'.format(
                         what = what, path = path, reason = error.strerror or error))


# -----------------------------------------------------------------------------
def _blobs(root: pathlib.Path, list_name: list[str], what: str) -> list[bytes]:
    """
    Return the content of each object of list_name, in order, as git
    cat-file gives it.

    """

    try:
        data = subprocess.run(['git', 'cat-file', '--batch'],
                              cwd            = root,
                              input          = ''.join(name + '\n' for name in list_name).encode(),
                              capture_output = True,
                              check          = True).stdout
    except subprocess.CalledProcessError as error:
        raise ErrorGate('{what} cannot be copied: {text}'.format(
                            what = what, text = error.stderr.decode().strip())) from error

    list_blob = []
    index     = 0
    for name in list_name:
        end    = data.index(b'\n', index)
        header = data[index:end].split()
        if len(header) != 3:
            raise ErrorGate('{what} cannot be copied, as git holds no object {name}.'.format(
                                what = what, name = name))
        size  = int(header[2])
        list_blob.append(data[end + 1:end + 1 + size])
        index = end + 1 + size + 1

    return list_blob


# -----------------------------------------------------------------------------
def _environment(dir_copy: pathlib.Path) -> dict[str, str]:
    """
    Return the environment that a stage runs in: this one, without the
    variables of TUPLE_UNSET, and with the source of the copy first on
    the python path, ahead of the python path of this one.

    """

    env = {key: value for (key, value) in os.environ.items()
           if not key.startswith(TUPLE_UNSET)}

    list_path     = [str(dir_copy / DIR_SOURCE), os.environ.get(ENV_PATH, '')]
    env[ENV_PATH] = os.pathsep.join(path for path in list_path if path)

    return env
