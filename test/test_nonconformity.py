"""
---

id_self:                pym_test.test_nonconformity
guid_self:              pym_8c41d7b60e9a4f2ea35b91c7d0e46f38
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Nonconformity report tests
brief:                  |
                        Tests that a check finding and a failed test
                        become the same report, that an absence of
                        observation becomes none, and that a report is
                        written only when it is asked for.
description:            |
                        Every report made in these tests is validated
                        against sch_nonconformity_report. A shape that
                        would not be a valid item therefore fails
                        here, rather than at the moment somebody asks
                        for the report to be kept.
relation:               []

...
"""


import pathlib

import cc_public.check
import cc_public.check.schema
import cc_public.edit.new
import cc_public.nonconformity


ID_SCHEMA = 'sch_nonconformity_report'
ID_CASE   = 'tc_path_reported'
ID_UNDER  = 'pyf_cc_public.query.database.path'


def _defaults(tree):
    defaults = dict(tree.defaults())
    defaults['guid_mark'] = tree.resolve(defaults['id_mark']).guid_self
    return defaults


def _invalid(tree, document):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    return cc_public.check.schema.validate(
                document, ID_SCHEMA, map_schema,
                cc_public.check.schema.registry(map_schema))


def _report(id_check, title, message, filepath, severity = 'critical'):
    return {'check': [{'id_check':      id_check,
                       'title':         title,
                       'nonconformity': [{'filepath': filepath,
                                          'path':     'table.term_performer.term',
                                          'message':  message,
                                          'severity': severity}]}]}


def _execution(tree, conformance, outcome = 'completed'):
    return {'id_self':           'tex_20260908000000_abcdef',
            'guid_self':         'tex_' + '0' * 32,
            'id_case':           ID_CASE,
            'guid_case':         tree.resolve(ID_CASE).guid_self,
            'id_method':         'tm_pytest_function',
            'guid_method':       tree.resolve('tm_pytest_function').guid_self,
            'id_under_test':     ID_UNDER,
            'digest_under_test': 'abcd1234',
            'execution_outcome': outcome,
            'result': {'main': dict({'observation': 'assert [] == [Step()]\n'},
                                    **({'conformance_result': conformance}
                                       if conformance else {}))}}


def test_a_check_finding_becomes_a_report_the_schema_accepts(tree):
    location = str(tree.resolve('term_performer').location)
    report   = _report('schema', 'Items conform to schema',
                       "'NOT a term!' does not match", location)

    (made,) = cc_public.nonconformity.from_report(tree.context.map_document, report,
                                                  _defaults(tree))

    assert _invalid(tree, made) == []
    assert made['origin']            == 'check'
    assert made['expected'].strip()  == 'Items conform to schema'
    assert 'does not match' in made['observed']
    assert made['id_subject']        == 'reg_term'
    assert made['path']              == 'table.term_performer.term'


def test_the_expectation_is_the_check_and_cannot_drift_from_it(tree):
    location = str(tree.resolve('term_performer').location)
    report   = _report('relation', 'Edges hold between the kinds of thing their '
                                   'relation allows', 'an edge runs to nothing', location)
    (made,)  = cc_public.nonconformity.from_report(tree.context.map_document, report,
                                                   _defaults(tree))
    assert made['expected'].strip().startswith('Edges hold between')


def test_a_finding_of_the_eval_check_keeps_eval_as_its_origin(tree):
    location = str(tree.resolve('term_performer').location)
    report   = _report('eval', 'Items meet their evals', 'Unmet on 5 of 5', location,
                       severity = 'advisory')
    (made,)  = cc_public.nonconformity.from_report(tree.context.map_document, report,
                                                   _defaults(tree))
    assert made['origin']   == 'eval'
    assert made['severity'] == 'advisory'


def test_a_failed_test_becomes_a_report_carrying_what_the_case_expects(tree):
    case     = tree.context.map_document[tree.resolve(ID_CASE).location]
    (made,)  = cc_public.nonconformity.from_execution(
                        tree.context.map_document, _execution(tree, 'failed'),
                        _defaults(tree), case.get('expectation'))

    assert _invalid(tree, made) == []
    assert made['origin']       == 'test'
    assert made['id_subject']   == ID_UNDER
    assert made['id_case']      == ID_CASE
    assert 'shortest path' in made['expected']
    assert 'assert' in made['observed']


def test_an_execution_that_did_not_complete_yields_no_report(tree):
    for outcome in ('error', 'not_run', 'cancelled'):
        assert cc_public.nonconformity.from_execution(
                    tree.context.map_document, _execution(tree, None, outcome),
                    _defaults(tree)) == ()


def test_an_observation_that_is_not_a_failure_yields_no_report(tree):
    for conformance in ('passed', 'not_applicable', 'inconclusive'):
        assert cc_public.nonconformity.from_execution(
                    tree.context.map_document, _execution(tree, conformance),
                    _defaults(tree)) == ()


def test_making_a_report_writes_nothing(tree, tmp_path):
    before = sorted(p.name for p in tmp_path.iterdir())
    cc_public.nonconformity.from_execution(tree.context.map_document,
                                           _execution(tree, 'failed'), _defaults(tree))
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert not (tmp_path / 'nonconformity').exists()


def test_a_report_is_written_only_when_it_is_asked_for(tree, tmp_path):
    (made,) = cc_public.nonconformity.from_execution(
                    tree.context.map_document, _execution(tree, 'failed'), _defaults(tree))

    id_self = cc_public.edit.new.from_document(tree, 't_nonconformity_report', made)

    assert (tmp_path / 'nonconformity' / (id_self + '.yaml')).is_file()

    critical = [n['message']
                for c in cc_public.check.check(list_path = [pathlib.Path(tmp_path)])
                                     ['report']['check']
                for n in c['nonconformity'] if n['severity'] == 'critical']
    assert critical == []


def test_a_brief_says_what_failed_and_not_the_first_line_of_a_traceback(tree):
    execution = _execution(tree, 'failed')
    execution['result']['main']['observation'] = (
            'tree = <cc_public.edit.tree.Tree object at 0x106b58690>\n'
            'E   assert [] == [Step()]\n')

    (made,) = cc_public.nonconformity.from_execution(tree.context.map_document, execution,
                                                     _defaults(tree))

    assert '0x' not in made['brief']
    assert made['brief'].strip() == ('pyf_cc_public.query.database.path does not meet '
                                     'what tc_path_reported expects of it.')
    assert '0x106b58690' in made['observed']       # the evidence is kept whole


def test_a_report_names_the_run_it_came_from_by_an_edge(tree):
    # A field does not carry what an edge should, and a kept report
    # held id_execution and an empty relation list, so nothing could be
    # walked from the report to the run that produced it.
    # Only where the execution is kept: an edge naming a run the tree
    # does not hold would dangle, and a development run leaves none.
    (plain,) = cc_public.nonconformity.from_execution(
                    tree.context.map_document, _execution(tree, 'failed'), _defaults(tree))
    assert plain['relation'] == []

    (made,) = cc_public.nonconformity.from_execution(
                    tree.context.map_document, _execution(tree, 'failed'), _defaults(tree),
                    is_kept = True)

    (edge,) = [e for e in made['relation'] if e['id_relation'] == 'r_results_from']
    assert edge['id_target'].startswith('tex_')
    assert edge['guid_target']
