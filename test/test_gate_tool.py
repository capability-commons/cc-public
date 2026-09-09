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
