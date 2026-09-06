"""
---

id_self:                pym_test.test_concept
guid_self:              pym_c5f0ba1db6944092b01172646e68b85d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Concept tests
brief:                  |
                        The concept workflow makes one proposed
                        concept under a framing, challenged, with its
                        candidate requirements bounded.
description:            |
                        A scripted run makes a concept deriving from
                        the need and framed by the framing, with
                        assumption and candidate requirement entries
                        carrying identities, challenged by the second
                        node; a concept with too few candidate
                        requirements fails the schema and the run
                        restores.
relation:               []

...
"""


import json

import cc_public.check
import cc_public.edit.field
import cc_public.edit.tree
import cc_public.load
import cc_public.workflow.run
from conftest import clean
from test_run import Judge


CANDIDATES = [
    {'key': 'endurance', 'statement': 'The Field_Power_Cell shall power a terminal and two chargers for 72 hours without refuelling.',
     'rationale': 'The post reports three nights without power.', 'category': 'function'},
    {'key': 'carry', 'statement': 'The Field_Power_Cell shall be carried by two people over 500 metres.',
     'rationale': 'Resupply roads are under fire, so it moves on foot.', 'category': 'fit'},
    {'key': 'charge', 'statement': 'The Field_Power_Cell shall recharge from a vehicle supply within four hours.',
     'rationale': 'Chargers are the load the post names.', 'category': 'function'},
    {'key': 'state', 'statement': 'The Field_Power_Cell shall show its remaining energy.',
     'rationale': 'Teams must plan around what is left.', 'category': 'quality', '__category': 'noise'}]
CANDIDATES += [{'key': 'more_{n}'.format(n = n),
                'statement': 'The Field_Power_Cell shall meet obligation {n}.'.format(n = n),
                'rationale': 'A further obligation.', 'category': 'quality'} for n in range(6)]

BIND = {'propose.input.need':        'need_frontline_multiday_offgrid_power',
        'propose.input.framing':     'frame_supply',
        'propose.input.observation': 'obs_frontline_power_post',
        'propose.input.guide':       'reg_writing_style_rule',
        'challenge.input.need':      'need_frontline_multiday_offgrid_power',
        'challenge.input.guide':     'reg_writing_style_rule'}


class Proposer:
    """A generator answering the proposer and the challenger."""

    id_model = 'scripted'

    def __init__(self, candidates = CANDIDATES):
        self.calls      = []
        self.candidates = candidates

    def produce(self, prompt, map_input, list_field, want_slug):
        self.calls.append((sorted(map_input), list(list_field)))
        if list_field == ['challenge']:
            return {'challenge': 'The fuel assumption rests on one post.'}
        answer = {'title':        'Field power cell',
                  'brief':        'A battery, a controller and a panel in one case, carried to the position.',
                  'entity':       'Field_Power_Cell',
                  'operation':    'The team carries the cell to the position and plugs in the terminal.',
                  'architecture': 'A battery, a charge controller and a folding solar panel.',
                  'effect':       'Power for several days; it does not refuel a generator.',
                  'assumption':   json.dumps([{'key': 'fuel_scarce',
                                               'statement': 'Fuel cannot be brought in for days.',
                                               'evidence': 'The post reports a road under fire.'}]),
                  'risk':         'Cloud for days leaves the cell flat.',
                  'candidate_requirement': json.dumps(self.candidates),
                  'resolution':   '',
                  'slug':         'field_power_cell'}
        return {f: answer[f] for f in list(list_field) + (['slug'] if want_slug else [])}


def deploy(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'dep_concept_from_need_local', 'admit_unmeasured',
                                   value = True)                # the scripted judge is measured nowhere


def test_a_concept_is_proposed_under_a_framing_and_challenged(repo):
    deploy(repo)
    gen = Proposer()
    r   = cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                                     BIND, gen, Judge('met'), generator_challenge = gen)
    assert r['stopped'] is None, r['stopped']
    assert [e['node'] for e in r['node']] == ['propose', 'challenge']
    assert r['node'][0]['made'] == ['cpt_field_power_cell']
    assert r['node'][1]['revised'] == ['cpt_field_power_cell']
    assert gen.calls[0] == (['framing', 'guide', 'need', 'observation'],
                            ['title', 'brief', 'entity', 'operation', 'architecture', 'effect',
                             'assumption', 'risk', 'candidate_requirement', 'resolution'])
    assert gen.calls[1] == (['guide', 'need', 'proposal'], ['challenge'])

    doc = cc_public.load.from_file(repo / 'concept' / 'cpt_field_power_cell.yaml')
    assert doc['status'] == 'proposed' and doc['entity'] == 'Field_Power_Cell'
    assert sorted((e['id_relation'], e['id_target']) for e in doc['relation']) == [
        ('r_is_derived_from', 'need_frontline_multiday_offgrid_power'),
        ('r_is_framed_by', 'frame_supply')]
    assert list(doc['candidate_requirement'])[:4] == ['endurance', 'carry', 'charge', 'state']
    assert len(doc['candidate_requirement']) == 10 and doc['brief'].startswith('A battery')
    entry = doc['candidate_requirement']['carry']
    assert entry['id_self'] == 'crq_field_power_cell.carry' and entry['category'] == 'fit'
    assert entry['statement'].startswith('The Field_Power_Cell shall be carried')
    assert doc['assumption']['fuel_scarce']['id_self'] == 'asm_field_power_cell.fuel_scarce'
    assert doc['challenge'].startswith('The fuel assumption') and 'resolution' not in doc
    assert any('__category is not a field' in n for n in r['node'][0]['note'])
    assert '__category' not in doc['candidate_requirement']['state']
    assert r['outcome'] == 'completed'
    assert clean(repo) == []


def test_too_few_candidate_requirements_fail_the_schema_and_the_run_restores(repo):
    deploy(repo)
    gen = Proposer(candidates = CANDIDATES[:5])
    r   = cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                                     BIND, gen, Judge('met'), generator_challenge = gen)
    assert r['stopped'] and 'critical' in r['stopped'], r['stopped']
    assert not (repo / 'concept' / 'cpt_field_power_cell.yaml').exists()
    assert clean(repo) == []


def test_promotion_makes_a_proposed_requirement_from_each_candidate_and_refuses_twice(repo):
    deploy(repo)
    gen = Proposer()
    cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                               BIND, gen, Judge('met'), generator_challenge = gen)
    concept = 'cpt_field_power_cell'
    r = cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                                   {'promote.input.concept': concept}, Proposer(), None)
    assert r['stopped'] is None, r['stopped']
    (node,) = r['node']
    assert node['revised'] == [concept] and len(node['made']) >= 3
    assert all(i.startswith('req_field_power_cell_') for i in node['made'])
    doc = cc_public.load.from_file(repo / 'concept' / (concept + '.yaml'))
    assert len(node['made']) == len(doc['candidate_requirement'])
    for (key, entry) in doc['candidate_requirement'].items():
        req = cc_public.load.from_file(repo / 'requirement' / f'req_field_power_cell_{key}.yaml')
        assert req['status'] == 'proposed' and req['category'] == entry['category']
        assert req['statement'].split() == entry['statement'].split()
        assert len(req['title']) <= 80 and req['title'][0].isupper()
        assert sorted((e['id_relation'], e['id_target']) for e in req['relation']) == [
            ('r_is_derived_from', concept),
            ('r_is_derived_from', 'need_frontline_multiday_offgrid_power')]
    assert clean(repo) == []

    before = sorted(p.name for p in (repo / 'requirement').iterdir())
    r = cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                                   {'promote.input.concept': concept}, Proposer(), None)
    assert r['stopped'] and 'promoted before' in r['stopped']
    assert sorted(p.name for p in (repo / 'requirement').iterdir()) == before
