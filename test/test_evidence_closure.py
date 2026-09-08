"""
---

id_self:                pym_test.test_evidence_closure
guid_self:              pym_a5d3f81c604b47e2b9c7e0f2a6d1483b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Evidence closure tests
brief:                  |
                        Tests that a result makes evidence current,
                        that a change within the closure stales it and
                        a change outside it does not, and that a row
                        written before the richer references stays
                        readable.
description:            |
                        The closure is drawn from the relations that
                        declare a dependency, so each test changes one
                        item and asks whether the digest moved.
relation:               []

...
"""


import cc_public.check.evidence
import cc_public.edit.field
import cc_public.edit.link
import cc_public.evidence
import cc_public.testing


ID_CASE   = 'tc_path_reported'
ID_REQ    = 'req_path_reported'
ID_METHOD = 'tm_pytest_function'
ID_UNDER  = 'pyf_cc_public.query.database.path'


def _digest(tree):
    return cc_public.check.evidence.digest(
                tree.context.map_document,
                tree.resolve(ID_REQ).guid_self,
                tree.resolve(ID_CASE).guid_self)


def _execution(tree, conformance, outcome = 'completed'):
    return {'id_self':           'tex_20260908000000_abcdef',
            'guid_self':         'tex_' + '0' * 32,
            'id_case':           ID_CASE,
            'guid_case':         tree.resolve(ID_CASE).guid_self,
            'id_method':         ID_METHOD,
            'guid_method':       tree.resolve(ID_METHOD).guid_self,
            'id_under_test':     ID_UNDER,
            'guid_under_test':   tree.resolve(ID_UNDER).guid_self,
            'digest_under_test': 'abcd1234',
            'adapter_version':   'pytest 9.1.1',
            'execution_outcome': outcome,
            'result': {'main': {'conformance_result': conformance,
                                'observation':        'observed\n'}}}


def _row(tree):
    document = tree.context.map_document[tree.resolve('evd_pytest').location]
    return next((one for one in document['case'].values()
                 if one.get('id_requirement') == ID_REQ
                 and one.get('id_case') == ID_CASE), None)


def test_the_closure_reaches_what_a_verdict_rests_on(tree):
    reached = cc_public.testing.closure(tree.context.map_document, [ID_CASE, ID_REQ])
    assert ID_METHOD in reached                                   # by r_uses_test_method
    assert ID_UNDER  in reached                                   # by r_is_implemented_by
    assert 'pym_cc_public.adapter.pytest_function' in reached     # the method's adapter
    assert 'ddr_source_identifier' not in reached                 # r_decides is not one


def test_a_passing_result_makes_the_requirement_evidence_current(tree):
    assert cc_public.evidence.from_execution(tree, _execution(tree, 'passed')) is not None
    row = _row(tree)
    assert row['outcome']      == 'passed'
    assert row['digest']       == _digest(tree)
    assert row['id_method']    == ID_METHOD
    assert row['id_execution'] == 'tex_20260908000000_abcdef'


def test_a_failing_result_makes_the_current_evidence_say_so(tree):
    cc_public.evidence.from_execution(tree, _execution(tree, 'failed'))
    assert _row(tree)['outcome'] == 'failed'


def test_a_run_that_did_not_complete_establishes_nothing(tree):
    assert cc_public.evidence.from_execution(
                tree, _execution(tree, None, 'error')) is None
    assert _row(tree) is None


def test_an_observation_that_is_not_a_verdict_establishes_nothing(tree):
    for conformance in ('not_applicable', 'inconclusive'):
        assert cc_public.evidence.from_execution(
                    tree, _execution(tree, conformance)) is None


def test_changing_the_method_stales_the_evidence(tree):
    before = _digest(tree)
    cc_public.edit.field.set_field(tree, ID_METHOD, 'verdict_rule',
                                   prose = 'Passed where it passed.')
    assert _digest(tree) != before


def test_changing_the_case_stales_the_evidence(tree):
    before = _digest(tree)
    cc_public.edit.field.set_field(tree, ID_CASE, 'expectation',
                                   prose = 'Something else entirely.')
    assert _digest(tree) != before


def test_changing_the_item_under_test_stales_the_evidence(tree, tmp_path):
    before   = _digest(tree)
    filepath = tmp_path / 'src' / 'cc_public' / 'query.py'
    filepath.write_text(filepath.read_text().replace('def path(self, name_from, name_to):',
                                                     'def path(self, name_from, name_to, x = 1):'))
    tree.refresh(filepath)
    assert _digest(tree) != before


def test_changing_the_requirement_stales_the_evidence(tree):
    before = _digest(tree)
    cc_public.edit.field.set_field(tree, ID_REQ, 'object', value = 'the Longest Path')
    assert _digest(tree) != before


def test_a_change_outside_the_closure_does_not_stale_the_evidence(tree):
    before = _digest(tree)
    cc_public.edit.field.set_field(tree, 'ddr_source_identifier', 'consequence',
                                   prose = 'Something quite different is written here.')
    cc_public.edit.field.set_field(tree, ID_CASE, 'description',
                                   prose = 'Reworded, and nothing about what is run.')
    assert _digest(tree) == before


def test_a_row_written_before_the_richer_references_stays_readable(tree):
    cc_public.evidence.from_execution(tree, _execution(tree, 'passed'))
    row = _row(tree)
    for key in ('id_method', 'id_execution', 'id_under_test'):
        del row[key]
        del row['guid' + key[2:]]
    assert row['id_requirement'] == ID_REQ
    assert row['digest'] == _digest(tree)
