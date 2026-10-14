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

                        The stages run side by side, one to a
                        processor, and the tests are split by file
                        into one shard for each processor, so that the
                        gate takes about as long as its longest shard.
usage:                  |
                        cctool gate [--root DIR]

                        Run before each commit by
                        .githooks/pre-commit. The gate refuses to run
                        without souffle, because the tests that need
                        souffle would otherwise be skipped and pass.
relation:               []

...
"""


import concurrent.futures
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile


# Each stage: its name, and the command that runs it in the root of the
# copy. {python} is the interpreter that runs the gate. A stage with
# {shard} in its command runs once for each shard of the test files,
# with the files of the shard in place of {shard}.
#
ARG_SHARD     = '{shard}'
TUPLE_STAGE   = (('check', ('{python}', '-m', 'cc_public.cli.command', 'check')),
                 ('lint',  ('ruff', 'check', '--no-cache', 'src')),
                 ('test',  ('{python}', '-m', 'pytest', '-p', 'no:cacheprovider', ARG_SHARD)))
GLOB_TEST     = 'test_*.py'
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

    count = os.cpu_count() or 1

    with tempfile.TemporaryDirectory(prefix = PREFIX_COPY) as name:
        dir_copy = pathlib.Path(name)
        copy_staged(root, dir_copy)
        env      = _environment(dir_copy)
        list_job = []
        for (name_stage, tuple_arg) in (tuple_stage or TUPLE_STAGE):
            list_arg = [arg.format(python = sys.executable) if arg != ARG_SHARD else arg
                        for arg in tuple_arg]
            if ARG_SHARD not in list_arg:
                list_job.append((name_stage, list_arg))
                continue
            index = list_arg.index(ARG_SHARD)
            for list_file in shards(dir_copy, count):
                list_job.append((name_stage, list_arg[:index] + list_file + list_arg[index + 1:]))

        with concurrent.futures.ThreadPoolExecutor(max_workers = count) as executor:
            list_done = list(executor.map(lambda job: _run(job[1], dir_copy, env), list_job))

    map_result = {}
    for ((name_stage, _), (is_passed, text)) in zip(list_job, list_done, strict = True):
        (was_passed, before) = map_result.get(name_stage, (True, ''))
        map_result[name_stage] = (was_passed and is_passed, before + text)

    return [(name_stage, *result) for (name_stage, result) in map_result.items()]


# -----------------------------------------------------------------------------
def shards(dir_copy: pathlib.Path, count: int) -> list[list[str]]:
    """
    Return the test files under the source of dir_copy, split into at
    most count shards of about equal size, the largest file first, each
    file put in the shard that is smallest so far.

    """

    list_path  = sorted((dir_copy / DIR_SOURCE).rglob(GLOB_TEST),
                        key = lambda path: (-path.stat().st_size, str(path)))
    list_shard = [[0, []] for _ in range(max(1, min(count, len(list_path))))]

    for path in list_path:
        shard     = min(list_shard, key = lambda each: each[0])
        shard[0] += path.stat().st_size
        shard[1].append(str(path.relative_to(dir_copy)))

    return [sorted(list_file) for (_, list_file) in list_shard]


# -----------------------------------------------------------------------------
def _run(list_arg: list[str], dir_copy: pathlib.Path, env: dict[str, str]) -> tuple[bool, str]:
    """
    Return whether the command list_arg passed in dir_copy, and what it
    printed.

    """

    try:
        done = subprocess.run(list_arg,
                              cwd            = dir_copy,
                              env            = env,
                              capture_output = True,
                              text           = True,
                              check          = False)
    except FileNotFoundError as error:
        raise ErrorGate('{name} cannot be found.'.format(name = list_arg[0])) from error

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
