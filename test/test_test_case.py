"""
---

id_self:                pym_test.test_test_case
guid_self:              pym_18070ecf0c4a45e19253d00551825ed4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test case schema tests
brief:                  |
                        Tests that a test case names exactly one test
                        method, requires what it is given and what is
                        expected, and governs its external vectors.
description:            |
                        The configuration is the one field whose shape
                        a method decides, so anything is accepted
                        there and a check validates it elsewhere. An
                        external vector states its locator and its
                        digest. That a case names exactly one test
                        method is the cardinality of
                        r_uses_test_method, which test_relation.py
                        holds.
relation:               []

...
"""


import copy

import pytest

import cc_public.check.schema


ID_SCHEMA = 'sch_test_case'

EDGE_METHOD = {'id_relation':   'r_uses_test_method',
               'guid_relation': 'r_' + '0' * 32,
               'id_target':     'tm_probe',
               'guid_target':   'tm_' + '1' * 32}

EDGE_VERIFY = {'id_relation':   'r_verifies',
               'guid_relation': 'r_' + '2' * 32,
               'id_target':     'req_path_reported',
               'guid_target':   'req_' + '3' * 32}

CASE = {
    'id_self':         'tc_probe',
    'guid_self':       'tc_' + '4' * 32,
    'title':           'A probe case',
    'brief':           'A case written to try the schema.\n',
    'description':     'It is thrown away.\n',
    'copyright':       'Copyright 2026 William Payne',
    'license':         'Apache-2.0',
    'protective_mark': [{'id_mark':   'mark_public',
                         'guid_mark': 'mark_0c96ccb7b7534574acf6ed42f9deba0f'}],
    'version':         '1.0',
    'input':           'The tree, and two item names.\n',
    'expectation':     'The shorter of the two paths between them.\n',
    'status':          'proposed',
    'relation':        [EDGE_METHOD, EDGE_VERIFY]}


@pytest.fixture(name = 'validate')
def _validate(tree, tmp_path):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    def run(case):
        return cc_public.check.schema.validate(copy.deepcopy(case), ID_SCHEMA,
                                               map_schema, registry)

    return run


def test_a_complete_case_conforms(validate):
    assert validate(CASE) == []


# A case names exactly one test method. That is the cardinality of
# r_uses_test_method, reported by the relation check, and test_relation.py
# holds it.


def test_a_case_with_no_expectation_is_refused(validate):
    case = copy.deepcopy(CASE)
    del case['expectation']
    messages = [message for (_, message) in validate(case)]
    assert any('expectation' in message for message in messages)


def test_the_configuration_takes_what_its_method_asks_for(validate):
    case = copy.deepcopy(CASE)
    case['configuration'] = {'node': 'test/test_query.py::test_path', 'strict': True}
    assert validate(case) == []


def test_a_field_the_schema_does_not_declare_is_refused(validate):
    case = copy.deepcopy(CASE)
    case['command'] = 'pytest -q'
    messages = [message for (_, message) in validate(case)]
    assert any('command' in message for message in messages)


def test_an_external_vector_states_its_locator_and_digest(validate):
    case = copy.deepcopy(CASE)
    case['artifact'] = [{'locator':          'https://example.invalid/capture.bin',
                         'digest':           'a3f1',
                         'digest_algorithm': 'sha256',
                         'media_type':       'application/octet-stream',
                         'size_byte':        4096}]
    assert validate(case) == []


def test_an_external_vector_without_a_digest_is_refused(validate):
    case = copy.deepcopy(CASE)
    case['artifact'] = [{'locator': 'https://example.invalid/capture.bin'}]
    messages = [message for (_, message) in validate(case)]
    assert any('digest' in message for message in messages)
