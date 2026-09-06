"""
---

id_self:                pym_test.test_render
guid_self:              pym_883a4fc6bd234731a80c020231cbde9e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Rendering tests
brief:                  |
                        The dossier projection, the pages and the PDF,
                        over a demonstration the test builds.
description:            |
                        The test builds what a demonstration segment
                        holds, an observation, the need it supports, a
                        concept under a framing, the requirements
                        promoted from it and an assessment citing the
                        observation, then projects the dossier over
                        it: the leading assessment orders the concept,
                        the findings of a report reach each
                        requirement, the trace gaps are there, the
                        drawing is labelled by title, the briefing
                        leads with the solutions and the appendix
                        carries the findings. The items themselves
                        live in the segment that demonstrates them,
                        not here.
relation:               []

...
"""



import pytest

import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.render.dossier
import cc_public.render.graph
import cc_public.render.html
import cc_public.render.pdf
import cc_public.workflow.run
from test_concept import BIND, ID_NEED, ID_OBSERVATION, Proposer, deploy
from test_run import Judge


ID_CONCEPT    = 'cpt_field_power_cell'
ID_ASSESSMENT = 'asmt_field_power_cell_assessed'
DIMENSION     = ('maturity', 'off_the_shelf', 'integration', 'logistics', 'cost',
                 'time_to_field', 'operational_fit')


def built(repo):
    """
    Build a demonstration in a test tree, as the segment that
    demonstrates it holds one: an observation, the need it supports, a
    concept under a framing, the requirements promoted from it, and an
    assessment of its feasibility citing the observation.

    """
    deploy(repo)                                   # seeds the observation and the need
    gen = Proposer()
    cc_public.workflow.run.run(repo, 'wf_concept_from_need', 'dep_concept_from_need_local',
                               BIND, gen, Judge('met'), generator_challenge = gen)
    cc_public.workflow.run.run(repo, 'wf_promote_concept', 'dep_promote_local',
                               {'promote.input.concept': ID_CONCEPT}, gen, None)

    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.new.new(tree, 't_assessment', ID_ASSESSMENT, tree.defaults())
    cc_public.edit.field.set_field(tree, ID_ASSESSMENT, 'title', value = 'Field power cell assessed')
    cc_public.edit.field.set_field(tree, ID_ASSESSMENT, 'assessor', value = 'a test')
    cc_public.edit.field.set_field(tree, ID_ASSESSMENT, 'verdict', value = 'feasible_now')
    cc_public.edit.field.set_field(tree, ID_ASSESSMENT, 'summary',
                                   prose = 'Every part is on the shelf.')
    for name in DIMENSION:
        cc_public.edit.insert.insert(tree, 't_dimension', name, ID_ASSESSMENT, 'dimension')
        entry = 'dim_field_power_cell_assessed.' + name
        cc_public.edit.field.set_field(tree, entry, 'rating', value = 'strong')
        cc_public.edit.field.set_field(tree, entry, 'rationale', prose = 'Bought, not built.')
    cc_public.edit.insert.insert(tree, 't_product', 'cell', ID_ASSESSMENT, 'product')
    for (field, value) in (('name', 'A commercial battery module'), ('maturity', 'commercial')):
        cc_public.edit.field.set_field(tree, 'prd_field_power_cell_assessed.cell', field, value = value)
    for (field, value) in (('role', 'The energy the cell stores.'),
                           ('support', 'The observation read, and nothing more.')):
        cc_public.edit.field.set_field(tree, 'prd_field_power_cell_assessed.cell', field, prose = value)
    cc_public.edit.link.link(tree, 'prd_field_power_cell_assessed.cell', 'r_cites', ID_OBSERVATION)
    cc_public.edit.link.link(tree, ID_ASSESSMENT, 'r_cites', ID_OBSERVATION)
    cc_public.edit.link.link(tree, ID_ASSESSMENT, 'r_assesses', ID_CONCEPT)

    return cc_public.edit.tree.Tree([repo])


def test_the_dossier_projects_a_demonstration_and_renders_both_documents(repo, tmp_path):
    tree   = built(repo)
    first  = cc_public.render.dossier.dossier(tree, ID_OBSERVATION)
    id_req = first['requirement'][0]['id']
    report = {'report': {'check': [{'id_check': 'eval', 'nonconformity': [
        {'filepath': str(repo / 'eval' / 'evl_req_singular.yaml'),
         'path':     id_req,
         'message':  'Two objects joined by and. rule_r19_combinators.',
         'severity': 'advisory'}]}]}}
    d = cc_public.render.dossier.dossier(tree, ID_OBSERVATION, report)

    assert d['observation']['id'] == ID_OBSERVATION
    assert d['observation']['digest'].startswith('sha256:')
    (need,) = d['need']
    assert need['id'] == ID_NEED and ' need ' in need['statement']
    (concept,) = d['concept']
    assert concept['framing']['id'].startswith('frame_') and concept['promoted']
    assert 10 <= len(concept['candidate']) <= 30
    assert len(concept['requirement']) == len(concept['candidate'])

    # The assessment leads because it cites something; its verdict
    # orders the concept and reaches the requirement's findings.
    assert concept['verdict'] == 'feasible_now'
    assert concept['lead']['made_by'] == 'person' and concept['lead']['assessor'] == 'a test'
    assert [dm['key'] for dm in concept['lead']['dimension']] == list(DIMENSION)
    assert concept['lead']['product'][0]['cited'][0]['id'] == ID_OBSERVATION
    assert [r['id'] for r in d['reference']] == [ID_OBSERVATION]

    req = next(r for r in d['requirement'] if r['id'] == id_req)
    assert req['finding'] == [{'eval': 'evl_req_singular', 'severity': 'advisory',
                               'message': 'Two objects joined by and. rule_r19_combinators.'}]
    assert req['gap'] and 'implements' in req['gap'][0]
    assert d['finding_count'] == 1
    runs = [e for e in d['execution'] if e['workflow'] == 'wf_concept_from_need']
    assert runs and all(e['passes'] >= 1 for e in runs)
    assert 'digraph' in d['graph']['dot'] and 'flowchart' in d['graph']['mermaid']
    assert ('assessment', ID_ASSESSMENT, d['assessment'][0]['guid']) in d['identity']

    svg = cc_public.render.graph.svg(d['graph']['dot'])
    assert svg.startswith('<svg') and need['title'].split()[0] in svg
    briefing = cc_public.render.html.briefing(d)
    appendix = cc_public.render.html.appendix(d, svg)
    assert 'Proposed solutions' in briefing and need['title'] in briefing
    assert 'feasible now' in briefing and '<script' not in briefing
    assert 'rule_r19_combinators' in appendix and '<svg' in appendix
    assert 'How this was made' in appendix
    assert 'rule_r19_combinators' not in briefing        # findings live in the appendix

    path = cc_public.render.pdf.write(briefing, tmp_path / 'out' / 'briefing.pdf')
    assert path.read_bytes()[:5] == b'%PDF-' and path.stat().st_size > 10000


def test_a_dossier_needs_an_item_the_tree_holds(repo):
    tree = cc_public.edit.tree.Tree([repo])
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.render.dossier.dossier(tree, 'obs_nowhere')
