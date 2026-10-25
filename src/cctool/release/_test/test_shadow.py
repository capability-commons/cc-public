"""
---

id_self:                pym_cctool.release._test.test_shadow
guid_self:              pym_1c6a0ba3a14c4ee7882692e579bf66e1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Shadow tests
brief:                  |
                        Tests of finding the items that a release
                        leaves behind but names, and of the check of a
                        file of shadows.
description:            |
                        Each test reads a copy of the repository,
                        whose pyproject.toml says what the wheel
                        holds, as pym_cctool.release.shadow reads it.
edge:                   []

...
"""


import cctool.check.check
import cctool.graph.extract
import cctool.release.shadow


PATH_ITEM         = '_data/logical_component/lco_release.yaml'
PATH_SHADOW       = '_data/shadow/segment_cc_public.yaml'


# -----------------------------------------------------------------------------
def test_the_package_holds_data_and_code_but_not_tests_or_the_hook(tree):
    table = cctool.release.shadow.wheel(tree)
    assert [file for file in ('_data/register/reg_concept.yaml',
                              'src/cctool/check/check.py',
                              'src/cctool/check/check.lp',
                              'src/cctool/_test/test_wheel.py',
                              'src/cctool/check/_test/test_check.py',
                              'src/cctool/conftest.py',
                              'src/cctool/release/hook.py',
                              'pyproject.toml',
                              '.githooks/pre-push')
            if cctool.release.shadow.is_shipped(file, table)] == [
        '_data/register/reg_concept.yaml', 'src/cctool/check/check.py',
        'src/cctool/check/check.lp']


# -----------------------------------------------------------------------------
def test_an_item_left_behind_that_shipped_prose_names_gets_a_shadow(tree):
    text = (tree / PATH_ITEM).read_text(encoding = 'utf-8')
    (tree / PATH_ITEM).write_text(text.replace('title:', 'note:                   See '
                                               'file_pyproject.\ntitle:', 1), encoding = 'utf-8')
    (segment, list_shadow) = cctool.release.shadow.shadows(tree)
    assert segment == ('segment_cc_public', 'segment_1d15a7ac18724bbbabe22e5ff2b79a72')
    assert ('file_pyproject', 'file_db37a056b6f3467c82134c30f201f391') in list_shadow
    assert all(not cctool.release.shadow.is_shipped(file, cctool.release.shadow.wheel(tree))
               for (id_self, _, _, file, _) in
               cctool.graph.extract.facts_of(cctool.graph.extract.documents(tree),
                                             with_tool = False)['item']
               if id_self in {each for (each, _) in list_shadow})


# -----------------------------------------------------------------------------
def test_a_shadow_beside_its_item_is_no_repeat_and_needs_no_schema(tree):
    segment = ('segment_cc_public', 'segment_1d15a7ac18724bbbabe22e5ff2b79a72')
    shadow  = ('file_pyproject', 'file_db37a056b6f3467c82134c30f201f391')
    (tree / PATH_SHADOW).parent.mkdir()
    (tree / PATH_SHADOW).write_text(cctool.release.shadow.text(segment, [shadow]),
                                    encoding = 'utf-8')
    failures = cctool.check.check.check(tree)
    assert failures == {}
