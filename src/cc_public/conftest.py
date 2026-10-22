"""
---

id_self:                pym_cc_public.conftest
guid_self:              pym_8c07ee653351466fa401605f3b360b5f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test fixtures
brief:                  |
                        The fixtures the tests share: a copy of the
                        repository to break.
description:            |
                        This module holds the fixtures. Every test
                        runs wherever the environment is installed,
                        since clingo is part of it. A copy keeps only
                        a fixed slice of the deliberations, the
                        decisions the tests name, so the tests neither
                        slow down nor change meaning as the
                        deliberations in the repository grow.
edge:                   []

...
"""


import pathlib
import shutil

import pytest


DIR_REPO  = pathlib.Path(__file__).resolve().parents[2]

# What a copy leaves out: version control, environments, caches and
# local tools.
#
TUPLE_SKIP = ('.git', '.pixi', '.venv', '_tools', '__pycache__', '.ruff_cache',
              '.pytest_cache', '*.egg-info')


# The decisions a copy keeps: those the tests name. Every other folder of
# _data/decision is left out.
#
DIR_DECISION        = DIR_REPO / '_data' / 'decision'
TUPLE_DECISION_KEPT = ('dec_cross_item_checks_engine', 'dec_tooling_language')


# -----------------------------------------------------------------------------
def _ignore(dir_from: str, list_name: list[str]) -> set[str]:
    """
    Return the names in dir_from that a copy leaves out: those that
    match TUPLE_SKIP and, in _data/decision, the decisions the tests do not
    name.

    """

    set_skip = shutil.ignore_patterns(*TUPLE_SKIP)(dir_from, list_name)
    if pathlib.Path(dir_from) == DIR_DECISION:
        set_skip |= {name for name in list_name if name not in TUPLE_DECISION_KEPT}
    return set_skip


# -----------------------------------------------------------------------------
def pytest_configure(config):
    """
    Register the mark prepush, which the pre-commit gate leaves out.

    """

    config.addinivalue_line('markers', 'prepush: left out of the pre-commit gate, which '
                                       'the pre-push gate is not; it tests the commit '
                                       'and history machinery')


# -----------------------------------------------------------------------------
@pytest.fixture
def tree(tmp_path):
    """
    Yield the root of a copy of the repository: its data items, its
    source and the files at its root, without version control,
    environments or caches, and with only the decisions in
    TUPLE_DECISION_KEPT.

    The copy is removed when the test ends. A run makes one for each of
    some hundreds of tests, and pytest keeps the temporary folders of
    its last three runs, so copies left behind would fill a disk with
    few inodes.

    """

    shutil.copytree(DIR_REPO, tmp_path,
                    ignore        = _ignore,
                    dirs_exist_ok = True)
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors = True)
