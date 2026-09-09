"""
---

id_self:                pym_test.package_smoke
guid_self:              pym_3929a5d9a960439b9476f24c4140c723
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Packaging smoke check
brief:                  |
                        Builds nothing itself: installs the built
                        wheel into an environment of its own and asks
                        whether the tool that comes out works and came
                        from the wheel.
description:            |
                        An editable install makes the checkout
                        importable, so a smoke test that merely
                        imports cc_public proves nothing about the
                        wheel: it may be reading the very tree the
                        wheel was built from. This installs into a
                        virtual environment without system site
                        packages and asserts the module it gets is
                        inside that environment and not inside the
                        repository.

                        Run by the package-check task, never by the
                        suite, since it builds and reaches the
                        network.
relation:               []

...
"""


import pathlib
import subprocess
import sys
import tempfile
import venv


ROOT = pathlib.Path(__file__).resolve().parent.parent


def is_inside(filepath, dirpath):
    """
    Return whether filepath lies at or below dirpath.

    The whole question this script exists to answer. An editable
    install puts the checkout on the path, so a tool that imports
    cc_public may be reading the tree the wheel was built from rather
    than the wheel.

    """

    try:
        pathlib.Path(filepath).resolve().relative_to(pathlib.Path(dirpath).resolve())
    except ValueError:
        return False

    return True


def _wheel():
    """
    Return the one wheel in dist/, or fail saying what was found.

    """

    found = sorted((ROOT / 'dist').glob('*.whl'))

    if len(found) != 1:
        raise SystemExit('Expected one wheel in dist/, found {n}.'.format(
                                                            n = len(found)))
    return found[0]


def _run(command, cwd = None):
    return subprocess.run(command, cwd = cwd, capture_output = True,  # noqa: S603
                          text = True, check = False)


def main():
    """
    Install the wheel into an environment of its own and exercise it.

    """

    wheel = _wheel()

    with tempfile.TemporaryDirectory() as name:
        dirpath = pathlib.Path(name)
        venv.EnvBuilder(with_pip = True, symlinks = True).create(dirpath)
        binary = dirpath / ('Scripts' if sys.platform == 'win32' else 'bin')

        done = _run([str(binary / 'python'), '-m', 'pip', 'install', '-q', str(wheel)])
        if done.returncode != 0:
            raise SystemExit('The wheel would not install.\n' + done.stderr)

        # Where did the tool actually come from? Answered before anything
        # else, since every later answer depends on it.
        done = _run([str(binary / 'python'), '-c',
                     'import cc_public; print(cc_public.__file__)'])
        if done.returncode != 0:
            raise SystemExit('The installed package would not import.\n' + done.stderr)

        origin = done.stdout.strip()

        if not is_inside(origin, dirpath):
            raise SystemExit(
                'The tool imported {origin}, which is not in the environment the '
                'wheel was installed into. It is reading something else.'.format(
                                                                origin = origin))
        if is_inside(origin, ROOT):
            raise SystemExit(
                'The tool imported {origin}, which is inside the repository. That '
                'is the checkout, not the wheel.'.format(origin = origin))

        for argument in (['--help'], ['trace', '--criticality']):
            done = _run([str(binary / 'cctool'), *argument], cwd = str(ROOT))
            if done.returncode != 0:
                raise SystemExit(
                    'cctool {argument} failed from the installed wheel.\n{err}'.format(
                            argument = ' '.join(argument), err = done.stderr))

        print('The wheel installs, imports from {origin}, and its cctool runs.'.format(
                                                                origin = origin))


if __name__ == '__main__':
    main()
