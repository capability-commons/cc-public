"""
---

id_self:                pym_test.test_decision
guid_self:              pym_a3a2af5d41474aacaf5552314ea7c694
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Decision tests
brief:                  |
                        Tests of decisions and the promotion gate: the
                        digest, the decide path, the check, and what
                        promotion admits and refuses.
description:            |
                        Makes decisions over items and checks that an
                        edit stales them and an expiry ends them; runs
                        a concept whose challenge does not conclude
                        and checks that promotion refuses it until a
                        waiver decides it; checks that an evidential
                        candidate is promoted only with a quote the
                        cited observation holds.
relation:               []

...
"""


import pytest

import cc_public.check
import cc_public.decision
import cc_public.edit.decide
import cc_public.edit.field
import cc_public.edit.tree
import cc_public.load
import cc_public.workflow.run
from conftest import clean
from test_concept import BIND, CANDIDATES, ID_OBSERVATION, Proposer, deploy
from test_run import Judge


BY = dict(actor = 'Test Person', role = 'engineering authority', authority = 'the test suite')


def _found(root, id_check):
    report = cc_public.check.check(list_path = [root])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == id_check]
    return found


def test_a_decision_is_over_exact_content_and_an_edit_stales_it(tree, tmp_path):
    item = cc_public.edit.decide.decide(tree, 'select', ['need_runs_bounded'], by = BY, brief = 'Chosen for the test.',
                                        expiry = '2999-01-01')
    assert item.id_self == 'dcn_select_runs_bounded'
    doc = cc_public.load.from_file(item.filepath)
    assert doc['outcome'] == 'select' and doc['actor'] == 'Test Person'
    (subject,) = doc['subject']
    assert subject['id_item'] == 'need_runs_bounded' and len(subject['digest']) == 8
    assert clean(tmp_path) == []
    found = _found(tmp_path, 'decision')
    assert found['count_item'] == 1 and found['nonconformity'] == []
    cc_public.edit.field.set_field(tree, 'need_runs_bounded', 'purpose', value = 'something else')
    (fault,) = _found(tmp_path, 'decision')['nonconformity']
    assert fault['severity'] == 'advisory' and 'need_runs_bounded has changed' in fault['message']


def test_an_expired_decision_is_reported_and_holds_nothing(tree, tmp_path):
    item = cc_public.edit.decide.decide(tree, 'lead', ['need_runs_bounded'], by = BY, brief = 'Once.',
                                        expiry = '2020-01-01')
    (fault,) = _found(tmp_path, 'decision')['nonconformity']
    assert 'Expired' in fault['message']
    doc = cc_public.load.from_file(item.filepath)
    assert not cc_public.decision.holds(doc, cc_public.decision.index(tree.context.map_document))
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.decide.decide(tree, 'veto', ['need_runs_bounded'], by = BY, brief = 'No.')


def _concept(repo, verdict, candidates = CANDIDATES):
    deploy(repo)
    gen = Proposer(candidates = candidates)
    r   = cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                                     BIND, gen, Judge(verdict), generator_challenge = gen)
    assert r['stopped'] is None, r['stopped']
    return r


def _promote(repo):
    return cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                                      {'promote.input.concept': 'cpt_field_power_cell'}, Proposer(), None)


@pytest.mark.slow
def test_a_concluded_challenge_admits_and_the_requirement_names_the_run(repo):
    r = _concept(repo, 'met')
    assert r['outcome'] == 'completed'
    p = _promote(repo)
    assert p['stopped'] is None, p['stopped']
    doc = cc_public.load.from_file(repo / 'requirement' / 'req_field_power_cell_carry.yaml')
    (edge,) = [e for e in doc['relation'] if e['id_relation'] == 'r_is_admitted_by']
    assert edge['id_target'] == r['execution']
    assert clean(repo) == []


@pytest.mark.slow
def test_an_exhausted_challenge_refuses_promotion_until_a_waiver_admits_it(repo):
    r = _concept(repo, 'unmet')
    assert r['outcome'] == 'exhausted'
    p = _promote(repo)
    assert p['stopped'] and 'not admitted' in p['stopped'] and 'exhausted' in p['stopped'], p['stopped']
    assert not (repo / 'requirement' / 'req_field_power_cell_carry.yaml').exists()
    tree = cc_public.edit.tree.Tree([repo])
    waiver = cc_public.edit.decide.decide(tree, 'waive', ['cpt_field_power_cell'],
                                          by = BY, brief = 'A bounded experiment despite the open challenge.',
                                          condition = 'Prototype only.', expiry = '2999-01-01')
    p = _promote(repo)
    assert p['stopped'] is None, p['stopped']
    doc = cc_public.load.from_file(repo / 'requirement' / 'req_field_power_cell_carry.yaml')
    (edge,) = [e for e in doc['relation'] if e['id_relation'] == 'r_is_admitted_by']
    assert edge['id_target'] == waiver.id_self
    assert clean(repo) == []


@pytest.mark.slow
def test_an_evidential_candidate_is_admitted_only_with_a_quote_the_observation_holds(repo):
    evidential = [dict(c) for c in CANDIDATES]
    evidential[0] = {k: v for (k, v) in evidential[0].items() if k != 'quote'}   # endurance, no quote
    _concept(repo, 'met', evidential)
    p = _promote(repo)
    assert p['stopped'] and 'evidential claim with no quote' in p['stopped'], p['stopped']
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'crq_field_power_cell.endurance', 'quote',
                                   value = 'Fourth night without grid power.')
    p = _promote(repo)
    assert p['stopped'] and 'no observation behind the concept holds' in p['stopped'], p['stopped']
    cc_public.edit.field.set_field(tree, 'crq_field_power_cell.endurance', 'quote',
                                   value = 'Third night without grid power.')
    p = _promote(repo)
    assert p['stopped'] is None, p['stopped']
    doc = cc_public.load.from_file(repo / 'requirement' / 'req_field_power_cell_endurance.yaml')
    assert doc['claim'] == 'evidential' and doc['quote'].strip() == 'Third night without grid power.'
    assert [e['id_target'] for e in doc['relation'] if e['id_relation'] == 'r_cites'] == [ID_OBSERVATION]
    assert clean(repo) == []
