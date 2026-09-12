"""
---

id_self:                pym_test.test_requirement_set
guid_self:              pym_6053c94a8b95457d8383ca1dc9b0f3f3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement set tests
brief:                  |
                        Tests of requirement sets: gathering, showing
                        members to a judge, the set checks, and the
                        coverage review.
description:            |
                        These tests gather the requirements of a
                        concept into a set. They check that a judge
                        and a model are shown the members as composed
                        statements, and that the requirement check
                        reports a member on another entity, a
                        duplicated obligation, an unreviewed set, and
                        an uncovered class. They also check that the
                        review workflow fills the coverage table from
                        a scripted model.
relation:               []

...
"""


import json

import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.gather
import cc_public.edit.tree
import cc_public.eval.select
import cc_public.load
import cc_public.workflow.produce
import cc_public.workflow.run
from conftest import clean
from test_concept import BIND, Proposer, deploy
from test_run import Judge


ID_CONCEPT = 'cpt_field_power_cell'
ID_SET     = 'rqs_field_power_cell'


def _promoted(repo):
    deploy(repo)
    gen = Proposer()
    cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                               BIND, gen, Judge('met'), generator_challenge = gen)
    r = cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                                   {'promote.input.concept': ID_CONCEPT}, Proposer(), None)
    assert r['stopped'] is None, r['stopped']
    return cc_public.edit.tree.Tree([repo])


def _found(root):
    report = cc_public.check.check(list_path = [root])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'requirement']
    return [n['message'] for n in found['nonconformity']]


@pytest.mark.slow
def test_gather_makes_a_set_of_the_promoted_requirements_and_gathers_once(repo):
    tree = _promoted(repo)
    (item, added) = cc_public.edit.gather.gather(tree, ID_CONCEPT)
    assert item.id_self == ID_SET and len(added) == 10
    doc = cc_public.load.from_file(item.filepath)
    assert doc['entity'] == 'Field_Power_Cell' and doc['status'] == 'proposed'
    assert sorted(e['id_target'] for e in doc['relation'] if e['id_relation'] == 'r_includes') == sorted(added)
    (item, again) = cc_public.edit.gather.gather(tree, ID_CONCEPT)
    assert again == []
    assert clean(repo) == []
    messages = _found(repo)
    assert any('Not yet reviewed' in m for m in messages)
    assert not any('is on' in m for m in messages)


@pytest.mark.slow
def test_a_judge_and_a_model_are_shown_the_members_as_statements(repo):
    tree = _promoted(repo)
    cc_public.edit.gather.gather(tree, ID_CONCEPT)
    ctx   = cc_public.check.context([repo])[0]
    sel   = cc_public.eval.select.Selector(id_eval = ('evl_set_consistent',))
    tasks = list(cc_public.eval.select.select(ctx, sel))
    assert [t.id_subject for t in tasks] == [(ID_SET,)]
    text = tasks[0].text_input
    assert 'member:' in text and 'entity:' in text and 'Field_Power_Cell' in text
    assert 'req_field_power_cell_carry: The Field_Power_Cell shall be carried by two people over 500 metres.' in text
    shown = cc_public.workflow.produce.render(tree, ID_SET)
    assert 'req_field_power_cell_endurance: The Field_Power_Cell shall power' in shown


@pytest.mark.slow
def test_the_set_checks_report_another_entity_a_duplicate_and_uncovered_classes(repo):
    tree = _promoted(repo)
    cc_public.edit.gather.gather(tree, ID_CONCEPT)
    cc_public.edit.field.set_field(tree, 'req_field_power_cell_more_1', 'entity', value = 'Other_Thing')
    cc_public.edit.field.set_field(tree, 'req_field_power_cell_more_2', 'object', value = 'obligation 3')
    messages = _found(repo)
    assert any('req_field_power_cell_more_1 is on Other_Thing' in m for m in messages)
    assert any('more_3 and req_field_power_cell_more_2 oblige' in m or 'more_2 and req_field_power_cell_more_3 oblige' in m for m in messages)


class Reviewer:
    """A generator answering the review with a coverage table."""

    id_model = 'scripted'

    def produce(self, prompt, map_input, list_field, want_slug):
        assert 'member' in map_input['set'] and 'shall power' in map_input['set']
        rows = [{'key': k, 'status': 'covered', 'note': 'req_field_power_cell_endurance.'}
                for k in ('normal', 'abnormal', 'misuse', 'maintenance', 'deployment', 'safety')]
        rows.append({'key': 'budget', 'status': 'uncovered', 'note': 'No mass limit is stated: how heavy may the cell be?'})
        return {'coverage': json.dumps(rows)}


@pytest.mark.slow
def test_the_review_workflow_fills_the_coverage_and_the_check_reports_the_uncovered_class(repo):
    tree = _promoted(repo)
    cc_public.edit.gather.gather(tree, ID_CONCEPT)
    r = cc_public.workflow.run.run(repo, 'wf_review_set', 'dep_review_set_local',
                                   {'review.input.set': ID_SET, 'review.input.guide': 'reg_writing_style_rule'},
                                   Reviewer(), None)
    assert r['stopped'] is None, r['stopped']
    doc = cc_public.load.from_file(repo / 'requirement_set' / (ID_SET + '.yaml'))
    assert sorted(doc['coverage']) == sorted(['normal', 'abnormal', 'misuse', 'maintenance', 'deployment', 'safety', 'budget'])
    assert doc['coverage']['budget']['status'] == 'uncovered'
    assert doc['coverage']['budget']['id_self'] == 'cov_field_power_cell.budget'
    messages = _found(repo)
    assert any('Uncovered: budget. No mass limit' in m for m in messages)
    assert not any('Not yet reviewed' in m for m in messages)
    assert clean(repo) == []


@pytest.mark.slow
def test_a_run_takes_a_list_of_roots_and_writes_into_the_first(repo):
    tree = _promoted(repo)
    cc_public.edit.gather.gather(tree, ID_CONCEPT)
    r = cc_public.workflow.run.run([repo], 'wf_review_set', 'dep_review_set_local',
                                   {'review.input.set': ID_SET, 'review.input.guide': 'reg_writing_style_rule'},
                                   Reviewer(), None)
    assert r['stopped'] is None, r['stopped']
    assert (repo / 'execution' / (r['execution'] + '.yaml')).exists()
