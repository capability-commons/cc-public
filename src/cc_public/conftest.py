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
                        since clingo is part of it.
relation:               []

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


# -----------------------------------------------------------------------------
@pytest.fixture
def tree(tmp_path):
    """
    Return the root of a copy of the repository: its data items, its
    source and the files at its root, without version control,
    environments or caches.

    """

    shutil.copytree(DIR_REPO, tmp_path,
                    ignore        = shutil.ignore_patterns(*TUPLE_SKIP),
                    dirs_exist_ok = True)
    return tmp_path
