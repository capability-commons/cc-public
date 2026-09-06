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
                        from the specimens in the tree.
description:            |
                        The projection rooted at the frontline power
                        observation holds the need, the concepts with
                        their entries, the promoted requirements with
                        findings from a report, the runs and the
                        drawing; the briefing and the appendix render
                        from it and the PDF is written; a root that is
                        not an observation is refused by resolution.
relation:               []

...
"""


import pathlib

import pytest

import cc_public.edit.tree
import cc_public.render.dossier
import cc_public.render.graph
import cc_public.render.html
import cc_public.render.pdf


ROOT = pathlib.Path(__file__).parent.parent


def test_the_dossier_projects_the_specimens_and_renders_both_documents(tmp_path):
    tree = cc_public.edit.tree.Tree([ROOT])
    first = cc_public.render.dossier.dossier(tree, 'obs_frontline_power_post')
    id_req = first['requirement'][0]['id']
    report = {'report': {'check': [{'id_check': 'eval', 'nonconformity': [
        {'filepath': str(ROOT / 'eval' / 'evl_req_singular.yaml'),
         'path':     id_req,
         'message':  'Two objects joined by and. rule_r19_combinators.',
         'severity': 'advisory'}]}]}}
    d = cc_public.render.dossier.dossier(tree, 'obs_frontline_power_post', report)

    assert d['observation']['id'] == 'obs_frontline_power_post'
    assert d['observation']['digest'].startswith('sha256:')
    (need,) = d['need']
    assert need['id'] == 'need_frontline_multiday_offgrid_power'
    assert need['statement'].startswith('In a frontline position') and ' need ' in need['statement']
    assert len(d['concept']) >= 3 and all(c['framing']['id'].startswith('frame_') for c in d['concept'])
    promoted = [c for c in d['concept'] if c['promoted']]
    assert promoted and all(len(c['requirement']) >= 10 for c in promoted)
    assert all(10 <= len(c['candidate']) <= 30 for c in d['concept'])
    req = next(r for r in d['requirement'] if r['id'] == id_req)
    assert req['finding'] == [{'eval': 'evl_req_singular', 'severity': 'advisory',
                               'message': 'Two objects joined by and. rule_r19_combinators.'}]
    assert req['gap'] and 'implements' in req['gap'][0]
    assert d['finding_count'] == 1
    runs = [e for e in d['execution'] if e['workflow'] == 'wf_concept_from_need']
    assert runs and all(e['challenger'] and e['passes'] >= 1 for e in runs)
    assert 'digraph' in d['graph']['dot'] and 'flowchart' in d['graph']['mermaid']
    assert ('observation', 'obs_frontline_power_post', d['observation']['guid']) in d['identity']

    svg = cc_public.render.graph.svg(d['graph']['dot'])
    assert svg.startswith('<svg') and need['title'].split()[0] in svg   # labels are titles
    briefing = cc_public.render.html.briefing(d)
    appendix = cc_public.render.html.appendix(d, svg)
    assert 'Proposed solutions' in briefing and need['title'] in briefing and '<script' not in briefing
    assert 'How this was made' in appendix and 'In five moves' not in briefing
    assert 'rule_r19_combinators' in appendix and '<svg' in appendix
    assert 'rule_r19_combinators' not in briefing               # findings live in the appendix

    path = cc_public.render.pdf.write(briefing, tmp_path / 'out' / 'briefing.pdf')
    assert path.read_bytes()[:5] == b'%PDF-' and path.stat().st_size > 10000


def test_a_dossier_needs_an_item_the_tree_holds():
    tree = cc_public.edit.tree.Tree([ROOT])
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.render.dossier.dossier(tree, 'obs_nowhere')
