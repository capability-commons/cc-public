"""
---

id_self:                pym_test.test_adapter
guid_self:              pym_3f7c1a92d4be4e8090c5b7a61f2e8d47
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pytest adapter tests
brief:                  |
                        Tests that the adapter tells a pass, a
                        failure, a skip, an error and an absent node
                        apart, and that a run that did not complete
                        carries no conformance result.
description:            |
                        The normalisation is tested against reports
                        made here, so that every outcome is covered
                        without running five test sessions. One test
                        runs a real case end to end and writes
                        nothing.
relation:               []

...
"""


import cc_public.adapter
import cc_public.adapter.pytest_function as adapter
import cc_public.edit.tree


ID_CASE  = 'tc_path_reported'
ID_UNDER = 'pyf_cc_public.query.database.path'
NODE     = 'test/test_query.py::test_a_shortest_path_is_reported_or_its_absence'


class _Collector:
    """
    A collector holding reports written here rather than by pytest.

    """

    def __init__(self, list_report = (), list_collect = ()):
        self.list_report  = list(list_report)
        self.list_collect = list(list_collect)


def _seen(list_report = (), list_collect = ()):
    return adapter._observation(_Collector(list_report, list_collect), NODE, 0.5)


def test_a_call_that_passed_is_a_completed_pass():
    seen = _seen([('setup', 'passed', ''), ('call', 'passed', '')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'passed'


def test_a_call_that_failed_is_a_completed_failure():
    seen = _seen([('setup', 'passed', ''), ('call', 'failed', 'assert 1 == 2')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'failed'
    assert 'assert 1 == 2' in seen.observation


def test_a_skip_is_completed_and_not_applicable():
    seen = _seen([('setup', 'skipped', 'not today')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'not_applicable'


def test_an_error_in_setup_is_an_execution_error_and_no_result():
    seen = _seen([('setup', 'failed', 'the fixture could not be made')])
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None
    assert 'setup' in seen.observation


def test_a_node_that_could_not_be_collected_is_an_execution_error_and_no_result():
    seen = _seen(list_collect = ['SyntaxError'])
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None


def test_a_node_nothing_ran_for_is_not_run_and_no_result():
    seen = _seen()
    assert seen.execution_outcome  == 'not_run'
    assert seen.conformance_result is None


def test_a_run_produces_a_conforming_execution_and_writes_nothing(tmp_path):
    # Read against the repository itself: the fixture tree holds no test/,
    # so the test function a case names is not in it.
    tree              = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, ID_CASE, ID_UNDER)
    assert problem == []
    assert document['execution_outcome'] == 'completed'
    assert document['result']['main']['conformance_result'] == 'passed'
    assert document['id_method']     == 'tm_pytest_function'
    assert document['digest_method'] and document['digest_case']
    assert document['adapter_version'].startswith('pytest ')
    assert not list(tmp_path.iterdir())


def test_a_case_that_does_not_resolve_yields_no_execution():
    tree = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, 'tc_absent', ID_UNDER)
    assert document is None
    assert 'tc_absent' in problem[0]


def test_an_item_the_tree_lacks_yields_no_execution():
    tree = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, ID_CASE, 'pyf_absent.absent')
    assert document is None
    assert 'nothing to observe' in problem[0]
