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
                        node; a key the entry schema does not declare
                        is dropped with a note; a concept with too few
                        candidate requirements fails the schema and
                        the run restores; promotion makes one proposed
                        requirement item per candidate and refuses to
                        promote twice. Each test seeds its own
                        observation and need, since those live in the
                        segment that demonstrates them.
relation:               []

...
"""


import json

import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.observe
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

CAPTURE = {'schema_version': 1,
           'source_kind':    'social_post',
           'platform':       'x',
           'post_id':        '7',
           'source_uri':     'https://example.invalid/unit/status/7',
           'author_handle':  '@unit_example',
           'published_at':   '2026-08-30T06:40:00Z',
           'captured_at':    '2026-09-06T11:00:00Z',
           'text':           'Third night without grid power. We need power that lasts days.',
           'capture_method': 'supplied_scrape'}

NEED = {'title':    'Power through grid loss',
        'subject':  'frontline teams at positions cut from grid power',
        'outcome':  'communications and drone batteries to stay powered for days',
        'purpose':  'keep reconnaissance and command running',
        'context':  'a position whose resupply road is under fire',
        'evidence': 'One post, obs_x_7, reports three nights without power. It establishes '
                    'neither how often this happens nor how many positions are affected.',
        'status':   'proposed'}

ID_OBSERVATION = 'obs_x_7'
ID_NEED        = 'need_power_through_grid_loss'
ID_FRAMING     = 'frame_supply'
ID_GUIDE       = 'reg_writing_style_rule'

BIND = {'propose.input.need':        ID_NEED,
        'propose.input.framing':     ID_FRAMING,
        'propose.input.observation': ID_OBSERVATION,
        'propose.input.guide':       ID_GUIDE,
        'challenge.input.need':      ID_NEED,
        'challenge.input.guide':     ID_GUIDE}


def seed(repo):
    """
    Put the demonstration's first two rungs into a test tree: an
    observation captured from a post, and the need it supports. The
    items themselves live in the segment that demonstrates them, not
    here, so a test that needs them makes its own.

    """
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.observe.observe(tree, CAPTURE)
    cc_public.edit.new.new(tree, 't_need', ID_NEED, tree.defaults())
    for (field, value) in NEED.items():
        cc_public.edit.field.set_field(tree, ID_NEED, field, value = value)
    cc_public.edit.link.link(tree, ID_NEED, 'r_is_derived_from', ID_OBSERVATION)
    return (ID_OBSERVATION, ID_NEED)


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
    seed(repo)
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
        ('r_is_derived_from', ID_NEED),
        ('r_is_framed_by', ID_FRAMING)]
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
            ('r_is_derived_from', ID_NEED)]
    assert clean(repo) == []

    before = sorted(p.name for p in (repo / 'requirement').iterdir())
    r = cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                                   {'promote.input.concept': concept}, Proposer(), None)
    assert r['stopped'] and 'promoted before' in r['stopped']
    assert sorted(p.name for p in (repo / 'requirement').iterdir()) == before
