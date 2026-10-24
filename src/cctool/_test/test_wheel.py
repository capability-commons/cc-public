"""
---

id_self:                pym_cctool._test.test_wheel
guid_self:              pym_c7863e7b0ae1416eb630caa3c1343cd1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Wheel tests
brief:                  |
                        Tests of the wheel that the build backend
                        makes from the tree.
description:            |
                        Each test reads one wheel, built from the tree
                        by hatchling, the build backend that
                        pyproject.toml names. The wheel holds every
                        file under _data at cctool/_data, and every
                        module and logic program of cctool, and leaves
                        out the tests and their fixtures. The wheel
                        grows with the data, so the tests are marked
                        slow, and hatchling is imported only when they
                        run, so that an environment without it can
                        still collect them.
edge:                   []

...
"""


import zipfile

import pytest

import cctool.conftest


pytestmark = pytest.mark.slow


DIR_DATA          = cctool.conftest.DIR_REPO / '_data'
DIR_PACKAGE       = cctool.conftest.DIR_REPO / 'src' / 'cctool'
PREFIX_DATA       = 'cctool/_data/'
PREFIX_PACKAGE    = 'cctool/'
NAME_TEST         = '_test'
NAME_CONFTEST     = 'conftest.py'
NAME_CACHE        = '__pycache__'
TUPLE_SUFFIX      = ('.py', '.lp')


# -----------------------------------------------------------------------------
@pytest.fixture(scope = 'module')
def set_name(tmp_path_factory):
    """
    Return the name of each file in a wheel built from the tree, by the
    build backend that pyproject.toml names, run from the root of the
    tree as an installer would run it.

    """

    import hatchling.build

    dir_wheel = tmp_path_factory.mktemp('wheel')
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.chdir(cctool.conftest.DIR_REPO)
        name_wheel = hatchling.build.build_wheel(str(dir_wheel))
    with zipfile.ZipFile(dir_wheel / name_wheel) as wheel:
        return set(wheel.namelist())


# -----------------------------------------------------------------------------
def _is_shipped(path):
    """
    Return True if path, a file under src/cctool, is code the wheel
    should hold: a module or logic program outside the tests.

    """

    list_part = path.relative_to(DIR_PACKAGE).parts
    return (path.suffix in TUPLE_SUFFIX
            and NAME_TEST not in list_part
            and NAME_CACHE not in list_part
            and path.name != NAME_CONFTEST)


def test_the_wheel_holds_every_file_of_data_under_cctool_data(set_name):
    set_data = {PREFIX_DATA + str(path.relative_to(DIR_DATA))
                for path in DIR_DATA.rglob('*') if path.is_file()}
    assert set_data
    assert {name for name in set_name if name.startswith(PREFIX_DATA)} == set_data


def test_the_wheel_holds_every_module_and_logic_program_of_cctool(set_name):
    set_code = {PREFIX_PACKAGE + str(path.relative_to(DIR_PACKAGE))
                for path in DIR_PACKAGE.rglob('*') if _is_shipped(path)}
    assert set_code - set_name == set()


def test_the_wheel_holds_no_test_and_no_fixture(set_name):
    set_found = {name for name in set_name
                 if not name.startswith(PREFIX_DATA)
                 and (NAME_TEST in name.split('/') or name.endswith(NAME_CONFTEST))}
    assert set_found == set()
