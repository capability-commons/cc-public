"""
---

id_self:                pym_cctool._test.test_fixture
guid_self:              pym_979df50a166f410bafba75c88fec3655
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Fixture tests
brief:                  |
                        Tests of the fixtures that the tests share.
description:            |
                        A copy of the repository is made while other
                        workers run tests that write caches in it, so
                        the copy must leave those caches out.
edge:                   []

...
"""


import cctool.conftest


def test_a_copy_of_the_repository_leaves_out_the_caches_that_tests_write():
    set_skip = cctool.conftest._ignore(str(cctool.conftest.DIR_REPO),
                                       ['.hypothesis', '.pytest_cache', '_data', 'README.md'])
    assert set_skip == {'.hypothesis', '.pytest_cache'}


def test_a_copy_leaves_out_an_annotation_that_names_a_decision_the_fixture_lacks():
    assert cctool.conftest.names_absent_decision_item('It argues ann_a_wrong_merge_passes_silently.')
    assert cctool.conftest.names_absent_decision_item('About dec_how_work_lands_quickly.')
    assert not cctool.conftest.names_absent_decision_item('About dec_tooling_language.')
    assert not cctool.conftest.names_absent_decision_item('About pym_cctool.check.citation.')
