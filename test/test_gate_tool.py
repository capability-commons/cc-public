"""
---

id_self:                pym_test.test_gate_tool
guid_self:              pym_3d0d3c58d6514d829598e79a51cc1c77
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate tool controls
brief:                  |
                        Runs each gate tool against a defect it is
                        meant to catch and asserts that the tool
                        fails.
description:            |
                        A tool that ran and exited zero has shown that
                        it ran. Whether it would have said anything
                        had there been something to say is a separate
                        question, and this is where it is answered.
                        One control per tool, each pointing the tool
                        at a known defect outside the tree so that the
                        repository never holds a broken file.
relation:               []

...
"""


import pathlib
import subprocess
import sys
import tempfile

import conftest


TYPE_ERROR = '''import typing


def statement(document: dict[str, typing.Any]) -> int:
    return ' '.join(str(document).split())
'''


def _mypy(text):
    """
    Run the configured type checker over one file holding text, outside
    the tree, and return what it did.

    """

    with tempfile.TemporaryDirectory() as name:
        filepath = pathlib.Path(name) / 'probe.py'
        filepath.write_text(text, encoding = 'utf-8')
        return subprocess.run(                                    # noqa: S603
                    [sys.executable, '-m', 'mypy', '--no-incremental',
                     '--python-version', '3.14', '--strict', str(filepath)],
                    cwd            = str(conftest.ROOT),
                    capture_output = True,
                    text           = True,
                    check          = False)


def test_the_type_checker_fails_on_a_wrong_return_type():
    # The defect mypy is in the gate to catch. Without this, a green
    # `pixi run type` says only that mypy ran.
    done = _mypy(TYPE_ERROR)
    assert done.returncode != 0
    assert 'return-value' in done.stdout


def test_the_type_checker_passes_what_is_right():
    # And it is not simply failing everything: the same shape, correct.
    done = _mypy(TYPE_ERROR.replace('-> int:', '-> str:'))
    assert done.returncode == 0, done.stdout


# Every statement of this runs when flag is true. The branch where the
# condition is false never does, which is exactly the difference between
# the two measurements and the reason for the migration.
#
COVERED = '''def taken(flag):
    answer = 'no'
    if flag:
        answer = 'yes'
    return answer
'''

EXERCISES_ONE_BRANCH = '''import probe


def test_one_way():
    assert probe.taken(True) == 'yes'
'''


def _coverage(floor, is_branch):
    """
    Run the suite of a tiny package outside the tree under a coverage
    floor, and return what it did.

    One function with one branch, and a test that takes it one way. The
    branch the test does not take is the defect the floor is here to
    notice.

    """

    with tempfile.TemporaryDirectory() as name:
        dirpath = pathlib.Path(name)
        (dirpath / 'probe.py').write_text(COVERED, encoding = 'utf-8')
        (dirpath / 'test_probe.py').write_text(EXERCISES_ONE_BRANCH,
                                               encoding = 'utf-8')

        # An empty config, so the probe does not inherit this
        # repository's pytest settings and measure this repository.
        (dirpath / 'probe.ini').write_text('[pytest]\n', encoding = 'utf-8')
        return subprocess.run(                                    # noqa: S603
                    [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                     '-c', str(dirpath / 'probe.ini'), str(dirpath),
                     '--cov=probe', '--cov-report=',
                     *(['--cov-branch'] if is_branch else []),
                     '--cov-fail-under=' + str(floor)],
                    cwd            = str(dirpath),
                    capture_output = True,
                    text           = True,
                    check          = False)


def test_the_coverage_floor_fails_when_coverage_is_under_it():
    # Without this, a green run says the floor was configured, not that
    # it would have stopped anything.
    done = _coverage(100, is_branch = True)
    assert done.returncode != 0
    assert 'Coverage failure' in done.stdout or 'Required test coverage' in done.stdout


def test_the_coverage_floor_passes_when_coverage_is_over_it():
    done = _coverage(50, is_branch = True)
    assert done.returncode == 0, done.stdout


def test_branch_measurement_sees_what_statement_measurement_does_not():
    # Every statement of taken() runs; the branch where the condition is
    # false never does. A floor of 100 passes without --cov-branch and
    # fails with it, which is the whole reason for the migration.
    assert _coverage(100, is_branch = False).returncode == 0
    assert _coverage(100, is_branch = True).returncode != 0


def test_the_packaging_smoke_tells_the_wheel_from_the_checkout():
    # The one thing the smoke exists to decide. cc_public is installed
    # editable, so the checkout is importable, and a smoke test that
    # merely imports it may be reading the tree the wheel was built
    # from. This is that judgement, exercised both ways.
    import package_smoke

    with tempfile.TemporaryDirectory() as name:
        elsewhere = pathlib.Path(name)
        assert package_smoke.is_inside(elsewhere / 'lib' / 'cc_public' / '__init__.py',
                                       elsewhere)
        assert not package_smoke.is_inside(conftest.ROOT / 'src' / 'cc_public' /
                                           '__init__.py', elsewhere)

    # And the negative it is guarding against: this interpreter has the
    # editable install, so what it imports is inside the repository.
    # A smoke run against an environment like this one must not pass.
    import cc_public

    assert package_smoke.is_inside(cc_public.__file__, conftest.ROOT)
