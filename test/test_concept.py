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
     'rationale': 'Teams must plan around what is left.', 'category': 'quality'}]

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
                            ['title', 'entity', 'operation', 'architecture', 'effect',
                             'assumption', 'risk', 'candidate_requirement', 'resolution'])
    assert gen.calls[1] == (['guide', 'need', 'proposal'], ['challenge'])

    doc = cc_public.load.from_file(repo / 'concept' / 'cpt_field_power_cell.yaml')
    assert doc['status'] == 'proposed' and doc['entity'] == 'Field_Power_Cell'
    assert sorted((e['id_relation'], e['id_target']) for e in doc['relation']) == [
        ('r_is_derived_from', 'need_frontline_multiday_offgrid_power'),
        ('r_is_framed_by', 'frame_supply')]
    assert list(doc['candidate_requirement']) == ['endurance', 'carry', 'charge', 'state']
    entry = doc['candidate_requirement']['carry']
    assert entry['id_self'] == 'crq_field_power_cell.carry' and entry['category'] == 'fit'
    assert entry['statement'].startswith('The Field_Power_Cell shall be carried')
    assert doc['assumption']['fuel_scarce']['id_self'] == 'asm_field_power_cell.fuel_scarce'
    assert doc['challenge'].startswith('The fuel assumption') and 'resolution' not in doc
    assert r['outcome'] == 'completed'
    assert clean(repo) == []


def test_too_few_candidate_requirements_fail_the_schema_and_the_run_restores(repo):
    deploy(repo)
    gen = Proposer(candidates = CANDIDATES[:2])
    r   = cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                                     BIND, gen, Judge('met'), generator_challenge = gen)
    assert r['stopped'] and 'critical' in r['stopped'], r['stopped']
    assert not (repo / 'concept' / 'cpt_field_power_cell.yaml').exists()
    assert clean(repo) == []
