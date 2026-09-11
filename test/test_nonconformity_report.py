"""
---

id_self:                pym_test.test_nonconformity_report
guid_self:              pym_f78d406b65a84206b14a09f4aacc8310
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Nonconformity report schema tests
brief:                  |
                        Tests that a report states both what was
                        expected and what was observed, and keeps the
                        origin it came from.
description:            |
                        A report states both what was expected and
                        what was observed, and these tests hold that.
                        The origin distinguishes a failure a check
                        observed from one a test or an eval observed,
                        across one shape.
relation:               []

...
"""


import copy

import pytest

import cc_public.check.schema


ID_SCHEMA = 'sch_nonconformity_report'

REPORT = {
    'id_self':         'ncr_probe',
    'guid_self':       'ncr_' + '0' * 32,
    'title':           'A probe report',
    'brief':           'A report written to try the schema.\n',
    'description':     'It is thrown away.\n',
    'copyright':       'Copyright 2026 William Payne',
    'license':         'Apache-2.0',
    'protective_mark': [{'id_mark':   'mark_public',
                         'guid_mark': 'mark_0c96ccb7b7534574acf6ed42f9deba0f'}],
    'expected':        'The shortest path between the two items.\n',
    'observed':        'No path was reported.\n',
    'origin':          'test',
    'id_subject':      'pyf_cc_public.query.database.path',
    'guid_subject':    'pyf_' + '1' * 32,
    'severity':        'critical',
    'time_detected':   '2026-09-08T01:00:04Z',
    'relation':        []}


@pytest.fixture(name = 'validate')
def _validate(tree, tmp_path):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    def run(report):
        return cc_public.check.schema.validate(copy.deepcopy(report), ID_SCHEMA,
                                               map_schema, registry)

    return run


def test_a_complete_report_conforms(validate):
    assert validate(REPORT) == []


@pytest.mark.parametrize('field', ['expected', 'observed'])
def test_a_report_missing_either_half_is_refused(validate, field):
    report = copy.deepcopy(REPORT)
    del report[field]
    messages = [message for (_, message) in validate(report)]
    assert any(field in message for message in messages)


@pytest.mark.parametrize('origin', ['check', 'test', 'eval'])
def test_each_origin_is_kept(validate, origin):
    report = copy.deepcopy(REPORT)
    report['origin'] = origin
    assert validate(report) == []


def test_an_origin_the_enumeration_does_not_hold_is_refused(validate):
    report = copy.deepcopy(REPORT)
    report['origin'] = 'hunch'
    messages = [message for (_, message) in validate(report)]
    assert any('hunch' in message for message in messages)


def test_a_severity_outside_the_two_the_repository_uses_is_refused(validate):
    report = copy.deepcopy(REPORT)
    report['severity'] = 'blocker'
    messages = [message for (_, message) in validate(report)]
    assert any('blocker' in message for message in messages)


def test_a_report_may_name_the_execution_that_produced_it(validate):
    report = copy.deepcopy(REPORT)
    report['id_execution']   = 'tex_probe'
    report['guid_execution'] = 'tex_' + '2' * 32
    assert validate(report) == []


def test_a_field_the_schema_does_not_declare_is_refused(validate):
    report = copy.deepcopy(REPORT)
    report['assignee'] = 'somebody'
    messages = [message for (_, message) in validate(report)]
    assert any('assignee' in message for message in messages)
