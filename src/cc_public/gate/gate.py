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

                        A stage runs without the git environment of
                        the hook that started it, so that a test which
                        makes a repository of its own cannot touch the
                        index of the commit.
usage:                  |
                        cctool gate [--root DIR]

                        Run before each commit by
                        .githooks/pre-commit. The gate refuses to run
                        without souffle, because the tests that need
                        souffle would otherwise be skipped and pass.
relation:               []

...
"""


import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


# Each stage: its name, and the command that runs it in the root of the
# copy. {python} is the interpreter that runs the gate.
#
TUPLE_STAGE   = (('check', ('{python}', '-m', 'cc_public.cli.command', 'check')),
                 ('lint',  ('ruff', 'check', '--no-cache', 'src')),
                 ('test',  ('{python}', '-m', 'pytest', '-p', 'no:cacheprovider')))
DIR_SOURCE    = 'src'
PREFIX_GIT    = 'GIT_'
PREFIX_COPY   = 'cc_gate_'


# -----------------------------------------------------------------------------
class ErrorGate(Exception):
    """
    The gate cannot be run.

    """


# -----------------------------------------------------------------------------
def gate(root: pathlib.Path,
         tuple_stage: tuple | None = None) -> list[tuple[str, bool, str]]:
    """
    Return, for each stage in order, its name, whether it passed, and
    what it printed, run over the staged content of the repository at
    root. The stages are TUPLE_STAGE unless tuple_stage names others.

    """

    souffle = os.environ.get('SOUFFLE', 'souffle')
    if shutil.which(souffle) is None:
        raise ErrorGate('souffle cannot be found. Put it on the PATH, or name it in the '
                        'SOUFFLE environment variable.')

    list_result = []

    with tempfile.TemporaryDirectory(prefix = PREFIX_COPY) as name:
        dir_copy = pathlib.Path(name)
        copy_staged(root, dir_copy)
        env      = _environment(dir_copy)
        for (name_stage, tuple_arg) in (tuple_stage or TUPLE_STAGE):
            list_arg = [arg.format(python = sys.executable) for arg in tuple_arg]
            try:
                done = subprocess.run(list_arg,
                                      cwd            = dir_copy,
                                      env            = env,
                                      capture_output = True,
                                      text           = True,
                                      check          = False)
            except FileNotFoundError as error:
                raise ErrorGate('{name} cannot be found.'.format(name = list_arg[0])) from error
            list_result.append((name_stage, done.returncode == 0, done.stdout + done.stderr))

    return list_result


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
