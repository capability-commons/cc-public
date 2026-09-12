"""
---

id_self:                pym_test.test_test_method
guid_self:              pym_0719d34d5db6474bb0c37c9635d23530
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test method schema tests
brief:                  |
                        Tests that a test method entry accepts a
                        complete method in each execution form, and
                        refuses a mixed, an incomplete and an
                        undeclared one.
description:            |
                        The execution form is a keyed object that
                        holds exactly one of three forms. A method
                        with two forms, a method with none, a method
                        with a field of one form written under
                        another, and a method with a field the
                        envelope does not declare are all refused.
                        Each is refused where it is written.
relation:               []

...
"""


import copy

import pytest

import cc_public.check
import cc_public.check.schema


ID_SCHEMA = 'sch_reg_test_method'

ENTRY = {
    'id_self':            'tm_probe',
    'guid_self':          'tm_' + '0' * 32,
    'title':              'A probe',
    'brief':              'A probe method.\n',
    'description':        'A method written to try the schema.\n',
    'alias':              [],
    'status':             'proposed',
    'version':            '1.0',
    'verification_class': 'test',
    'procedure':          'Run the thing.\n',
    'observation':        'What the thing printed.\n',
    'verdict_rule':       'Passed when it printed nothing.\n',
    'id_schema_case':     'sch_probe_case',
    'guid_schema_case':   'sch_' + '1' * 32,
    'execution_form':     {'automated': {'id_adapter':   'pyf_cc_public.probe.run',
                                         'guid_adapter': 'pyf_' + '2' * 32}}}

REGISTER = {
    'id_self':          'reg_probe',
    'guid_self':        'reg_' + '3' * 32,
    'title':            'A probe register',
    'brief':            'A register written to try the schema.\n',
    'description':      'It holds one probe method.\n',
    'usage':            'Tried and thrown away.\n',
    'note':             'None.\n',
    'copyright':        'Copyright 2026 William Payne',
    'license':          'Apache-2.0',
    'protective_mark':  [{'id_mark':   'mark_public',
                          'guid_mark': 'mark_0c96ccb7b7534574acf6ed42f9deba0f'}],
    'status':           'draft',
    'relation':         [],
    'table':            {}}


@pytest.fixture(name = 'validate')
def _validate(tree, tmp_path):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    def run(entry):
        document          = copy.deepcopy(REGISTER)
        document['table'] = {entry['id_self']: copy.deepcopy(entry)}
        return cc_public.check.schema.validate(document, ID_SCHEMA, map_schema, registry)

    return run


def test_a_complete_automated_method_conforms(validate):
    assert validate(ENTRY) == []


def test_a_complete_evaluated_inspection_method_conforms(validate):
    entry = copy.deepcopy(ENTRY)
    entry['verification_class'] = 'inspection'
    entry['execution_form'] = {'evaluated_inspection': {'id_eval':   'evl_probe',
                                                        'guid_eval': 'evl_' + '4' * 32,
                                                        'count_confirm': 5}}
    assert validate(entry) == []


def test_a_complete_manual_method_conforms(validate):
    entry = copy.deepcopy(ENTRY)
    entry['verification_class'] = 'demonstration'
    entry['execution_form'] = {'manual': {'instruction': 'Look at it.\n',
                                          'safety':      'Do not touch it.\n'}}
    assert validate(entry) == []


def test_two_forms_at_once_are_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['execution_form']['manual'] = {'instruction': 'Look at it.\n'}
    (error,) = validate(entry)
    assert error[0].endswith('execution_form')
    assert 'too many properties' in error[1].lower() or 'maxProperties' in error[1]


def test_no_form_at_all_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['execution_form'] = {}
    (error,) = validate(entry)
    assert error[0].endswith('execution_form')


def test_a_form_the_union_does_not_name_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['execution_form'] = {'scripted': {'command': 'rm -rf /'}}
    messages = [message for (_, message) in validate(entry)]
    assert any('scripted' in message for message in messages)


def test_a_field_of_one_form_written_under_another_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['execution_form'] = {'automated': {'id_adapter':   'pyf_cc_public.probe.run',
                                             'guid_adapter': 'pyf_' + '2' * 32,
                                             'instruction':  'Look at it.\n'}}
    (path, message) = validate(entry)[0]
    assert path.endswith('automated')
    assert 'instruction' in message


def test_an_automated_form_naming_no_adapter_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['execution_form'] = {'automated': {'timeout_second': 30}}
    messages = [message for (_, message) in validate(entry)]
    assert any('id_adapter' in message for message in messages)


def test_a_field_the_envelope_does_not_declare_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['command'] = 'pytest -q'
    messages = [message for (_, message) in validate(entry)]
    assert any('command' in message for message in messages)


def test_an_envelope_missing_its_verdict_rule_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    del entry['verdict_rule']
    messages = [message for (_, message) in validate(entry)]
    assert any('verdict_rule' in message for message in messages)


def test_a_version_that_is_not_a_dotted_number_is_refused(validate):
    entry = copy.deepcopy(ENTRY)
    entry['version'] = 'one point oh'
    messages = [message for (_, message) in validate(entry)]
    assert any('does not match' in message for message in messages)

    # A version written as a block scalar is refused by the datum rule in the
    # schema check, not here: validate over the register is the one place that
    # rule does not reach an entry. test_schema.py holds it.
