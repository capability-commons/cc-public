"""
---

id_self:                pym_cctool.release.smoke
guid_self:              pym_c174a0c53e9e40cfbce7c0e698f809ba
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Smoke test of a release
brief:                  |
                        Build the package of a commit, install it in a
                        fresh environment, and check with what was
                        installed, as the release gate does before a
                        tag.
description:            |
                        WTP ruled on 2026-10-24 that before a release
                        is tagged its package is built from the tagged
                        tree and installed in a fresh environment,
                        that cctool check passes on the data it ships,
                        and that a fixture peer checks against it
                        (ruling_release_gate). This module is that
                        smoke test. The tests on every Python and the
                        full check are pixi tasks of their own, which
                        pixi run release-gate runs before it. The
                        fresh environment resolves the declared ranges
                        of the dependencies rather than the lock, as
                        the ruling says, so the package indexes must
                        be reachable.
edge:                   []

...
"""


import os
import pathlib
import subprocess
import sys
import typing

import cctool.gate.gate
import cctool.graph.extract


# The build of the wheel, run in the copy of the commit as an installer
# runs it, by the build backend that pyproject.toml names. It prints
# the name of the wheel.
#
SCRIPT_BUILD      = 'import sys, hatchling.build; print(hatchling.build.build_wheel(sys.argv[1]))'

# Where the installed package holds its data, as the fresh environment
# prints it.
#
SCRIPT_DATA       = ('import pathlib, cctool; '
                     'print(pathlib.Path(cctool.__file__).parent / {dir!r})').format(
                        dir = cctool.graph.extract.DIR_DATA)

# The fixture peer, which consumes the installed package.
#
NAME_PEER         = 'release_smoke'
TUPLE_PEER        = ('--title',     'The release smoke segment',
                     '--brief',     'A fixture peer that the smoke test of a release makes.',
                     '--copyright', 'Copyright 2026 The release gate',
                     '--license',   'Apache-2.0')

# The variables a run of the installed cctool leaves out, so that it
# reads the package it installed and no other.
#
SET_ENV_DROPPED   = {'PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONSAFEPATH'}

LINES_SHOWN       = 12
SECONDS_STEP      = 1800


# -----------------------------------------------------------------------------
def smoke(root:     pathlib.Path,
          rev:      str,
          dir_work: pathlib.Path,
          say:      typing.Callable[[str], None]) -> list[str]:
    """
    Run the smoke test of the release gate on the commit rev of the
    repository at root, in the empty folder dir_work, and return a
    sentence for each step that fails. say is given a line before each
    step. Raise cctool.gate.gate.ErrorGate if rev cannot be copied.

    The commit is copied as git stores it, and its wheel built by the
    build backend; the wheel is installed in a fresh environment, which
    resolves the dependencies from their declared ranges rather than
    the lock. The installed package must hold the _data of the commit,
    file for file, its cctool check must pass on the copy, and a
    fixture peer that it makes must pass its own check and status.

    """

    dir_tree  = dir_work / 'tree'
    dir_wheel = dir_work / 'wheel'
    dir_venv  = dir_work / 'venv'
    dir_peer  = dir_work / 'peer'
    for path in (dir_wheel, dir_peer):
        path.mkdir(parents = True)

    say('Copying {rev} as git stores it.'.format(rev = rev))
    cctool.gate.gate.copy_commit(root, rev, dir_tree)

    say('Building the wheel.')
    (code, output) = _run([sys.executable, '-c', SCRIPT_BUILD, str(dir_wheel)], dir_tree)
    if code != 0:
        return [_failed('The wheel cannot be built from {rev}'.format(rev = rev), output)]
    path_wheel = dir_wheel / output.strip().splitlines()[-1]

    say('Installing {name} in a fresh environment.'.format(name = path_wheel.name))
    (code, output) = _run([sys.executable, '-m', 'venv', str(dir_venv)], dir_work)
    if code != 0:
        return [_failed('A fresh environment cannot be made', output)]
    python = dir_venv / 'bin' / 'python'
    tool   = str(dir_venv / 'bin' / 'cctool')
    (code, output) = _run([str(python), '-m', 'pip', 'install', '--quiet', str(path_wheel)],
                          dir_work)
    if code != 0:
        return [_failed('The wheel cannot be installed in a fresh environment', output)]

    list_found = []

    say('Comparing the data the package holds with that of {rev}.'.format(rev = rev))
    (code, output) = _run([str(python), '-c', SCRIPT_DATA], dir_work)
    if code != 0:
        return [_failed('The installed package cannot be imported', output)]
    list_found += data_differences(dir_tree / cctool.graph.extract.DIR_DATA,
                                   pathlib.Path(output.strip()))

    say('Checking {rev} with the installed cctool.'.format(rev = rev))
    (code, output) = _run([tool, 'check', '--root', str(dir_tree)], dir_work)
    if code != 0:
        list_found.append(_failed('The installed cctool check of {rev} exits with {code}'.format(
                                      rev = rev, code = code), output))

    say('Making and checking a fixture peer.')
    for list_arg in (['peer', 'init', NAME_PEER, *TUPLE_PEER],
                     ['check'],
                     ['peer', 'status']):
        (code, output) = _run([tool, *list_arg, '--root', str(dir_peer)], dir_work)
        if code != 0:
            list_found.append(_failed('The installed cctool {command} of the fixture peer '
                                      'exits with {code}'.format(command = ' '.join(list_arg[:2]),
                                                                 code    = code), output))
            break

    return list_found


# -----------------------------------------------------------------------------
def data_differences(dir_tree: pathlib.Path, dir_package: pathlib.Path) -> list[str]:
    """
    Return a sentence if the data dir_package, that of an installed
    package, is not dir_tree, that of the commit it was built from,
    file for file. The package may hold shadows besides.

    """

    map_tree    = _files(dir_tree)
    map_package = _files(dir_package)
    list_gone   = sorted(name for name in map_tree if map_package.get(name) != map_tree[name])
    list_extra  = sorted(name for name in map_package
                         if name not in map_tree
                         and not name.startswith(cctool.graph.extract.DIR_SHADOW + '/'))

    if not (list_gone or list_extra):
        return []

    return ['The installed package does not hold the data of the commit: {gone} files are '
            'missing or differ, and {extra} are extra, such as {name}.'.format(
                gone  = len(list_gone),
                extra = len(list_extra),
                name  = (list_gone + list_extra)[0])]


# -----------------------------------------------------------------------------
def _files(dir_data: pathlib.Path) -> dict[str, bytes]:
    """
    Return the bytes of each file under dir_data, by its path from
    there, or none if dir_data is not a folder.

    """

    if not dir_data.is_dir():
        return {}

    return {path.relative_to(dir_data).as_posix(): path.read_bytes()
            for path in dir_data.rglob('*') if path.is_file()}


# -----------------------------------------------------------------------------
def _run(list_arg: list[str], cwd: pathlib.Path) -> tuple[int, str]:
    """
    Return the exit status and the output, both streams together, of
    the program list_arg run in cwd, with no variable that would point
    python at another package. A program that cannot be started exits
    with 127, and one that runs too long with 124.

    """

    env = {name: value for (name, value) in os.environ.items() if name not in SET_ENV_DROPPED}

    try:
        result = subprocess.run(list_arg,
                                cwd     = cwd,
                                env     = env,
                                stdout  = subprocess.PIPE,
                                stderr  = subprocess.STDOUT,
                                text    = True,
                                check   = False,
                                timeout = SECONDS_STEP)
    except OSError as error:
        return (127, str(error))
    except subprocess.TimeoutExpired:
        return (124, 'Stopped after {count} s.'.format(count = SECONDS_STEP))

    return (result.returncode, result.stdout)


# -----------------------------------------------------------------------------
def _failed(what: str, output: str) -> str:
    """
    Return the sentence that what failed, with the last lines of its
    output.

    """

    list_line = [line for line in output.strip().splitlines() if line.strip()][-LINES_SHOWN:]
    if not list_line:
        return what + '.'
    return '{what}:\n{lines}'.format(what  = what,
                                     lines = '\n'.join('  ' + line for line in list_line))
