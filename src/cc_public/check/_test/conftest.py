"""
---

id_self:                pym_cc_public.check._test.conftest
guid_self:              pym_8c07ee653351466fa401605f3b360b5f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Checker test fixtures
brief:                  |
                        The fixtures the checker tests share: a copy
                        of the repository's data items to break.
description:            |
                        This module holds the fixtures. A test that
                        needs souffle is skipped where souffle cannot
                        be found, since the checker cannot run without
                        it.
relation:               []

...
"""


import os
import pathlib
import shutil

import pytest


DIR_REPO  = pathlib.Path(__file__).resolve().parents[4]
DIR_DATA  = '_data'


# -----------------------------------------------------------------------------
@pytest.fixture
def souffle():
    """
    Skip the test where souffle cannot be found.

    """

    if shutil.which(os.environ.get('SOUFFLE', 'souffle')) is None:
        pytest.skip('souffle cannot be found')


# -----------------------------------------------------------------------------
@pytest.fixture
def tree(souffle, tmp_path):
    """
    Return the root of a copy of the repository's data items.

    """

    shutil.copytree(DIR_REPO / DIR_DATA, tmp_path / DIR_DATA)
    return tmp_path
