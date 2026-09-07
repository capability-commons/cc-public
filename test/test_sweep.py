"""
---

id_self:                pym_test.test_sweep
guid_self:              pym_ddaffaf6dfb24c91943e27e3b3b52a2c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Sweep tests
brief:                  |
                        Tests of the sweep: a report becomes groups,
                        and a scripted model proposes a rule from
                        them.
description:            |
                        Writes a small check report with eval
                        findings, makes a sweep from it and checks the
                        groups, their counts, items and samples, and
                        that an invented rule name groups under its
                        eval alone; then runs the proposing workflow
                        with a scripted model and checks the proposal
                        derives from the sweep.
relation:               []

...
"""


import json

import cc_public.edit.sweep
import cc_public.edit.tree
import cc_public.load
import cc_public.workflow.run
from conftest import clean


def _report(tmp_path):
    findings = [
        {'filepath': '/x/eval/evl_req_singular.yaml', 'path': 'req_a', 'severity': 'advisory',
         'message': 'Two objects joined by and. rule_r19_combinators.'},
        {'filepath': '/x/eval/evl_req_singular.yaml', 'path': 'req_b', 'severity': 'advisory',
         'message': 'Two objects joined by and: the picture and the controls. rule_r19_combinators.'},
        {'filepath': '/x/eval/evl_req_singular.yaml', 'path': 'req_c', 'severity': 'advisory',
         'message': 'Two verbs. rule_r18_single_thought.'},
        {'filepath': '/x/eval/evl_req_self_contained.yaml', 'path': 'req_d', 'severity': 'advisory',
         'message': 'Hub is ordinary. rule_r06_undefined_terms. No rule named rule_r06_undefined_terms is in the register.'}]
    report = {'report': {'check': [
        {'id_check': 'parse', 'count_item': 3, 'nonconformity': []},
        {'id_check': 'eval', 'count_item': 40, 'detail': {'id_model': 'openai/gpt-5.1'},
         'nonconformity': findings}]}}
    path = tmp_path / 'report.json'
    path.write_text(json.dumps(report))
    return path


def test_a_report_becomes_a_sweep_grouped_by_eval_and_rule(tree, tmp_path):
    item = cc_public.edit.sweep.sweep(tree, _report(tmp_path), 'swp_test')
    doc  = cc_public.load.from_file(item.filepath)
    assert doc['judge'] == 'openai/gpt-5.1' and doc['count_judgement'] == 40 and doc['count_finding'] == 4
    assert list(doc['group']) == ['req_singular_r19_combinators', 'req_self_contained_none', 'req_singular_r18_single_thought']
    first = doc['group']['req_singular_r19_combinators']
    assert first['id_self'] == 'fgp_test.req_singular_r19_combinators'
    assert first['id_eval'] == 'evl_req_singular' and first['rule'] == 'rule_r19_combinators'
    assert first['count'] == 2 and first['item'].split() == ['req_a', 'req_b']
    assert 'the picture and the controls' in ' '.join(first['sample'].split())
    assert 'rule' not in doc['group']['req_self_contained_none']   # an invented rule groups under the eval alone
    assert clean(tmp_path) == []


class Proposer:
    id_model = 'scripted'

    def produce(self, prompt, map_input, list_field, want_slug):
        assert 'singular_r19_combinators' in map_input['sweep'] and 'rule_r19' in map_input['rules']
        return {'title':       'One object per statement',
                'brief':       'An object slot holds one thing; two joined by and are two requirements.',
                'description': 'Answers singular_r19_combinators, 2 findings: two objects joined by and.',
                'follows':     'The Hub shall display the Picture.',
                'breaks':      'The Hub shall display the Picture and the Controls.',
                'check':       'The object slot holds the word and between two noun phrases.',
                'slug':        'one_object_per_statement'}


def test_the_proposing_workflow_writes_a_proposal_deriving_from_the_sweep(repo, tmp_path):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.sweep.sweep(tree, _report(tmp_path), 'swp_test')
    r = cc_public.workflow.run.run(repo, 'wf_propose_rule', 'dep_propose_rule_local',
                                   {'propose.input.sweep': 'swp_test',
                                    'propose.input.rules': 'reg_requirement_rule',
                                    'propose.input.guide': 'reg_writing_style_rule'},
                                   Proposer(), None)
    assert r['stopped'] is None, r['stopped']
    (made,) = r['node'][0]['made']
    doc = cc_public.load.from_file(repo / 'proposal' / (made + '.yaml'))
    assert doc['status'] == 'proposed' and doc['check'].startswith('The object slot')
    assert [e['id_target'] for e in doc['relation'] if e['id_relation'] == 'r_is_derived_from'] == ['swp_test']
    assert clean(repo) == []
