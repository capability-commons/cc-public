"""
---

id_self:                pym_test.test_test_execution
guid_self:              pym_beeb983143bd44c1b95a8426dd212acc
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test execution schema tests
brief:                  |
                        Tests that an execution records what it bound
                        with a digest for each, and that an execution
                        which did not complete holds no passing
                        result.
description:            |
                        The execution outcome and the conformance
                        result are two fields, and a completed
                        execution may hold a failed result. An
                        execution that errored, did not run or was
                        cancelled may hold a failed, inconclusive or
                        not applicable result and not a passing one,
                        which is refused at the result that claims it.
relation:               []

...
"""


import copy

import pytest

import cc_public.check.schema


ID_SCHEMA = 'sch_test_execution'

RESULT = {'id_self':            'tres_20260908000000_abcdef.main',
          'guid_self':          'tres_' + '4' * 32,
          'conformance_result': 'passed',
          'observation':        'The shortest path was reported.\n'}

EXECUTION = {
    'id_self':          'tex_20260908000000_abcdef',
    'guid_self':        'tex_' + '0' * 32,
    'title':            'A probe execution',
    'brief':            'An execution written to try the schema.\n',
    'description':      'It is thrown away.\n',
    'copyright':        'Copyright 2026 William Payne',
    'license':          'Apache-2.0',
    'protective_mark':  [{'id_mark':   'mark_public',
                          'guid_mark': 'mark_0c96ccb7b7534574acf6ed42f9deba0f'}],
    'id_method':        'tm_probe',
    'guid_method':      'tm_' + '1' * 32,
    'digest_method':    'aa11',
    'id_case':          'tc_probe',
    'guid_case':        'tc_' + '2' * 32,
    'digest_case':      'bb22',
    'id_under_test':    'pyf_cc_public.query.database.path',
    'guid_under_test':  'pyf_' + '3' * 32,
    'digest_under_test': 'cc33',
    'id_adapter':       'pym_cc_public.adapter.pytest_function',
    'guid_adapter':     'pym_' + '4' * 32,
    'time_start':       '2026-09-08T01:00:00Z',
    'time_finish':      '2026-09-08T01:00:04Z',
    'execution_outcome': 'completed',
    'result':           {'main': RESULT},
    'relation':         []}


@pytest.fixture(name = 'validate')
def _validate(tree, tmp_path):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    def run(execution):
        return cc_public.check.schema.validate(copy.deepcopy(execution), ID_SCHEMA,
                                               map_schema, registry)

    return run


def test_a_complete_execution_conforms(validate):
    assert validate(EXECUTION) == []


def test_a_completed_execution_may_hold_a_failed_result(validate):
    execution = copy.deepcopy(EXECUTION)
    execution['result']['main']['conformance_result'] = 'failed'
    assert validate(execution) == []


@pytest.mark.parametrize('outcome', ['error', 'not_run', 'cancelled'])
def test_an_execution_that_did_not_complete_holds_no_passing_result(validate, outcome):
    execution = copy.deepcopy(EXECUTION)
    execution['execution_outcome'] = outcome
    (path, message) = validate(execution)[0]
    assert path == 'result.main.conformance_result'
    assert "'passed' is not one of" in message


@pytest.mark.parametrize('outcome', ['error', 'not_run', 'cancelled'])
def test_an_execution_that_did_not_complete_may_hold_any_other_result(validate, outcome):
    execution = copy.deepcopy(EXECUTION)
    execution['execution_outcome'] = outcome
    execution['result']['main']['conformance_result'] = 'inconclusive'
    assert validate(execution) == []


def test_an_execution_with_no_digest_for_its_method_is_refused(validate):
    execution = copy.deepcopy(EXECUTION)
    del execution['digest_method']
    messages = [message for (_, message) in validate(execution)]
    assert any('digest_method' in message for message in messages)


def test_an_execution_with_no_result_is_refused(validate):
    execution = copy.deepcopy(EXECUTION)
    execution['result'] = {}
    ((path, message),) = validate(execution)
    assert path == 'result' and 'non-empty' in message


def test_a_result_with_no_observation_is_refused(validate):
    execution = copy.deepcopy(EXECUTION)
    del execution['result']['main']['observation']
    messages = [message for (_, message) in validate(execution)]
    assert any('observation' in message for message in messages)


def test_an_outcome_the_enumeration_does_not_hold_is_refused(validate):
    execution = copy.deepcopy(EXECUTION)
    execution['execution_outcome'] = 'flaky'
    messages = [message for (_, message) in validate(execution)]
    assert any('flaky' in message for message in messages)


def test_a_field_the_schema_does_not_declare_is_refused(validate):
    execution = copy.deepcopy(EXECUTION)
    execution['command'] = 'pytest -q'
    messages = [message for (_, message) in validate(execution)]
    assert any('command' in message for message in messages)


@pytest.mark.parametrize('outcome', ['error', 'not_run', 'cancelled'])
def test_a_result_of_an_execution_that_did_not_complete_needs_no_conformance(validate,
                                                                             outcome):
    execution = copy.deepcopy(EXECUTION)
    execution['execution_outcome'] = outcome
    del execution['result']['main']['conformance_result']
    assert validate(execution) == []


def test_a_completed_execution_states_a_conformance_result(validate):
    execution = copy.deepcopy(EXECUTION)
    del execution['result']['main']['conformance_result']
    messages = [message for (_, message) in validate(execution)]
    assert any('conformance_result' in message for message in messages)


@pytest.mark.parametrize('field', ['id_case', 'guid_case', 'id_method', 'guid_method',
                                   'id_under_test', 'guid_under_test',
                                   'id_adapter', 'guid_adapter'])
def test_an_execution_says_what_it_bound(validate, field):
    # The schema required three digests and none of the identities
    # beside them, so an execution could carry a digest of something it
    # did not name, and the command that reads one reads id_case
    # unconditionally: valid and unusable.
    execution = copy.deepcopy(EXECUTION)
    del execution[field]

    assert validate(execution), field
