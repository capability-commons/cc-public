"""
---

id_self:                pym_test.test_adapter_control
guid_self:              pym_52c63e1d68b54a2b80d73b9b3719431d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Adapter control set
brief:                  |
                        Runs each control function through the real
                        adapter and asserts the pair it reads.
description:            |
                        The mapping from what pytest reports to an
                        execution outcome and a conformance result
                        decides every verdict this repository records,
                        and nothing else checks it. These run pytest
                        for real, so the assumption about what pytest
                        emits is tested rather than restated.

relation:

  - id_relation:        r_satisfies
    guid_relation:      r_0a4f8ded2f2c4b138bcdfbed9e83ecd4
    id_target:          obj_tool_accounted
    guid_target:        obj_8fd2a89590e744b2ad120aa31b2edb71

...
"""


import conftest

import cc_public.adapter.pytest_function as adapter
import cc_public.edit.tree


CONTROL  = 'pyf_test.control_adapter.'
ID_CASE  = 'tc_path_reported'
ID_UNDER = 'pyf_cc_public.query.database.path'


def _run(name):
    """
    Run one control through the adapter against this repository.

    """

    tree = cc_public.edit.tree.Tree(['.'])
    return adapter.run(tree.context.map_document,
                       {'id_test': CONTROL + name},
                       conftest.ROOT)


def test_a_control_that_passes_is_completed_and_passed():
    seen = _run('test_passes')
    assert (seen.execution_outcome, seen.conformance_result) == ('completed', 'passed')


def test_a_control_that_fails_is_completed_and_failed():
    seen = _run('test_fails')
    assert (seen.execution_outcome, seen.conformance_result) == ('completed', 'failed')
    assert 'the control that is meant to fail' in seen.observation


def test_a_control_whose_setup_errors_is_an_error_and_no_result():
    # Nothing about the item under test was observed, so there is no
    # verdict to record: a result of any kind here would be a claim the
    # run cannot support.
    seen = _run('test_errors_in_setup')
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None


def test_a_control_whose_teardown_errors_is_an_error_and_no_result():
    seen = _run('test_errors_in_teardown')
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None


def test_a_control_that_skips_is_completed_and_not_applicable():
    seen = _run('test_skips')
    assert (seen.execution_outcome, seen.conformance_result) \
           == ('completed', 'not_applicable')


def test_a_control_run_twice_is_one_verdict():
    # A parameterised function is one test function and one item, so it
    # carries one verdict rather than one for each instance.
    seen = _run('test_parameterised')
    assert (seen.execution_outcome, seen.conformance_result) == ('completed', 'passed')


def test_a_control_run_twice_that_fails_once_is_one_failure():
    # The verdict is over every instance, not the first. A reader that
    # returned at the first report that passed called this passed,
    # which hid every failure after a pass in a case of many.
    seen = _run('test_parameterised_one_fails')
    assert (seen.execution_outcome, seen.conformance_result) == ('completed', 'failed')


def test_a_control_the_tree_does_not_hold_is_not_run():
    seen = _run('test_absent')
    assert seen.execution_outcome  == 'not_run'
    assert seen.conformance_result is None
    assert seen.node is None


def test_a_control_stopped_at_its_timeout_is_an_error_and_no_result():
    # A run that was stopped never reached an end, so it says nothing
    # about the item under test. pytest-timeout reports it as an
    # ordinary call failure, and reading that as a failure would name
    # the item in a report for something the run never observed.
    seen = _run('test_times_out')
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None
    assert 'timeout' in seen.observation.lower()


def test_a_timeout_establishes_no_evidence_and_makes_no_report(tree):
    import cc_public.evidence
    import cc_public.nonconformity

    document = {'id_self':           'tex_20260909000000_abcdef',
                'guid_self':         'tex_' + '0' * 32,
                'id_case':           ID_CASE,
                'guid_case':         tree.resolve(ID_CASE).guid_self,
                'id_method':         'tm_pytest_function',
                'guid_method':       tree.resolve('tm_pytest_function').guid_self,
                'id_under_test':     ID_UNDER,
                'guid_under_test':   tree.resolve(ID_UNDER).guid_self,
                'digest_under_test': 'abcd1234',
                'adapter_version':   'pytest 9.1.1',
                'execution_outcome': 'error',
                'result': {'main': {'observation': 'stopped at its timeout\n'}}}

    assert cc_public.evidence.from_execution(tree, document) is None
    assert not cc_public.nonconformity.from_execution(
                tree.context.map_document, document, dict(tree.defaults()))
