"""
---

id_self:                pym_cc_public.gate.gate
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

                        A commit that stages no code, only data, is
                        not tested: the tests test the code. The gate
                        of a push runs them on what is pushed. The
                        tests marked prepush, which test the commit
                        and history machinery, are left to the gate of
                        a push too.

                        The stages run side by side, and pytest-xdist
                        hands the tests out to one worker for each
                        processor, so that the gate takes about as
                        long as its tests take divided among the
                        processors.
usage:                  |
                        cctool gate [--root DIR]

                        Run before each commit by
                        .githooks/pre-commit.
edge:                   []

...
"""


import concurrent.futures
import io
import os
import pathlib
import subprocess
import sys
import tarfile
import tempfile

import cc_public.check.store


# The tests that the gate of a push runs, and those that the gate of a
# commit runs. The tests marked prepush test the commit and history
# machinery, and are left to the gate of a push.
#
MARK_PUSH     = 'not slow'
MARK_COMMIT   = 'not slow and not prepush'

# Each stage: its name, and the command that runs it in the root of the
# copy. {python} is the interpreter that runs the gate. The tests run on
# one worker for each processor, each worker taking the next test when
# it is free, and the tests marked slow are left out: they grow with the
# data, or repeat the check stage.
#
TUPLE_STAGE   = (('check', ('{python}', '-m', 'cc_public.cli.command', 'check')),
                 ('lint',  ('ruff', 'check', '--no-cache', 'src')),
                 ('test',  ('{python}', '-m', 'pytest', '-p', 'no:cacheprovider',
                            '-n', 'auto', '--dist', 'worksteal', '-m', MARK_PUSH)))
DIR_SOURCE    = 'src'
NAME_TEST     = 'test'

# The paths that hold code, or what the code runs with. A commit that
# stages none of them changes no code, so its gate leaves out the
# tests, which test the code. The gate of a push runs every stage on
# what is pushed, so a test that the data breaks is still caught there.
#
TUPLE_CODE    = ('src/', 'pyproject.toml', 'pixi.lock', '.githooks/')
PREFIX_GIT    = 'GIT_'
PREFIX_COPY   = 'cc_gate_'
DIR_STORE     = 'cc_public_store'

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
    that runs for longer than seconds is stopped, and fails.

    """

    tuple_stage = tuple_stage or TUPLE_STAGE

    with tempfile.TemporaryDirectory(prefix = PREFIX_COPY) as name:
        dir_copy = pathlib.Path(name)
        if rev is None:
            copy_staged(root, dir_copy)
        else:
            copy_commit(root, rev, dir_copy)
        env      = _environment(dir_copy)
        env.pop(cc_public.check.store.ENV_STORE, None)
        if rev is None:
            env[cc_public.check.store.ENV_STORE] = str(store(root))
        list_job = [[arg.format(python = sys.executable) for arg in tuple_arg]
                    for (_, tuple_arg) in tuple_stage]

        with concurrent.futures.ThreadPoolExecutor(max_workers = len(list_job)) as executor:
            list_done = list(executor.map(lambda list_arg: _run(list_arg, dir_copy, env, seconds),
                                          list_job))

    return [(name_stage, *done)
            for ((name_stage, _), done) in zip(tuple_stage, list_done, strict = True)]


# -----------------------------------------------------------------------------
def stages(root: pathlib.Path) -> tuple:
    """
    Return the stages that gate the staged content of the repository at
    root: TUPLE_STAGE, with the tests marked prepush left out, and with
    no tests at all if no code is staged.

    """

    if not is_code_staged(root):
        return tuple(stage for stage in TUPLE_STAGE if stage[0] != NAME_TEST)

    return tuple((name, tuple(MARK_COMMIT if arg == MARK_PUSH else arg for arg in tuple_arg))
                 for (name, tuple_arg) in TUPLE_STAGE)


# -----------------------------------------------------------------------------
def is_code_staged(root: pathlib.Path) -> bool:
    """
    Return whether the staged content of the repository at root adds,
    changes or removes a path of TUPLE_CODE. Before the first commit,
    everything staged is new, and code is taken to be staged.

    """

    try:
        text = subprocess.run(['git', 'diff', '--cached', '--name-only', '--no-renames',
                               'HEAD'],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout
    except subprocess.CalledProcessError:
        return True

    return any(path.startswith(TUPLE_CODE) for path in text.splitlines())


# -----------------------------------------------------------------------------
def store(root: pathlib.Path) -> pathlib.Path:
    """
    Return the store of the checker for the gate of a commit of the
    repository at root: a directory in its git directory, which each of
    its worktrees shares.

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

    return (root / name).resolve() / DIR_STORE


# -----------------------------------------------------------------------------
def _run(list_arg: list[str],
         dir_copy: pathlib.Path,
         env:      dict[str, str],
         seconds:  float) -> tuple[bool, str]:
    """
    Return whether the command list_arg passed in dir_copy within
    seconds, and what it printed.

    """

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
        return (False, printed + 'Stopped after {seconds:g} s, the time limit of a '
                                 'stage.\n'.format(seconds = seconds))

    return (done.returncode == 0, done.stdout + done.stderr)


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
