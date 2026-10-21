"""
---

id_self:                pym_cc_public.requirement._test.test_compose
guid_self:              pym_132f2ec441624e6f8130aa42224c9885
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement composer tests
brief:                  |
                        Tests of the composition of requirement
                        statements.
description:            |
                        Each test composes a requirement written in
                        the test, and one composes every requirement
                        in a copy of the repository.
relation:               []

...
"""


import pytest

import cc_public.graph.extract
import cc_public.requirement.compose


MAP_NODE = {'lc_x':    {'id_self': 'lc_x',    'title': 'Checker'},
            'lc_user': {'id_self': 'lc_user', 'title': 'Maintainer'},
            'con_x':   {'id_self': 'con_x',   'term_preferred': 'report'}}


def _requirement(**map_field):
    list_edge = [('r_has_subject', 'lc_x'), ('r_has_process', 'con_x')]
    if map_field.get('activity') == 'interaction':
        list_edge.append(('r_has_actor', 'lc_user'))
    requirement = {'modal_verb': 'shall',
                   'activity':   'autonomous',
                   'object':     'each failure',
                   'relation':   [{'id_relation': id_relation, 'id_target': id_target}
                                  for (id_relation, id_target) in list_edge]}
    requirement.update(map_field)
    return requirement


def test_an_autonomous_requirement_composes():
    text = cc_public.requirement.compose.statement(_requirement(), MAP_NODE.get)
    assert text == 'The Checker shall report each failure.'


@pytest.mark.parametrize(('kind', 'keyword'), [('logic', 'If'),
                                               ('event', 'As soon as'),
                                               ('time',  'As long as')])
def test_a_condition_opens_with_the_keyword_of_its_kind(kind, keyword):
    requirement = _requirement(condition_kind = kind, condition = 'the tree is read')
    text        = cc_public.requirement.compose.statement(requirement, MAP_NODE.get)
    assert text == '{keyword} the tree is read, the Checker shall report each failure.'.format(
                       keyword = keyword)


def test_an_interaction_names_its_actor():
    requirement = _requirement(activity = 'interaction', qualifier = 'within one second')
    text        = cc_public.requirement.compose.statement(requirement, MAP_NODE.get)
    assert text == ('The Checker shall provide the Maintainer with the ability to report '
                    'each failure within one second.')


def test_an_interface_is_able_to():
    requirement = _requirement(activity = 'interface', modal_verb = 'should')
    text        = cc_public.requirement.compose.statement(requirement, MAP_NODE.get)
    assert text == 'The Checker should be able to report each failure.'


@pytest.mark.parametrize('requirement', [
    _requirement(condition = 'the tree is read'),
    _requirement(relation = []),
    _requirement(activity = 'interaction', relation = [{'id_relation': 'r_has_subject',
                                                       'id_target':   'lc_x'},
                                                      {'id_relation': 'r_has_process',
                                                       'id_target':   'con_x'}]),
    _requirement(object = '')])
def test_slots_that_do_not_compose_are_refused(requirement):
    with pytest.raises(cc_public.requirement.compose.ErrorCompose):
        cc_public.requirement.compose.statement(requirement, MAP_NODE.get)


def test_a_process_that_is_not_a_concept_is_refused():
    requirement = _requirement()
    with pytest.raises(cc_public.requirement.compose.ErrorCompose):
        cc_public.requirement.compose.statement(requirement, {'lc_x': MAP_NODE['lc_x']}.get)


def test_every_requirement_in_the_tree_composes(tree):
    map_node = {}
    for (document, _) in cc_public.graph.extract.documents(tree).values():
        _collect(document, map_node)
    list_requirement = [node for (id_item, node) in map_node.items()
                        if id_item.startswith('req_')]
    assert list_requirement
    for requirement in list_requirement:
        assert cc_public.requirement.compose.statement(requirement, map_node.get).endswith('.')


def _collect(node, map_node):
    if isinstance(node, list):
        for value in node:
            _collect(value, map_node)
    elif isinstance(node, dict):
        if isinstance(node.get('id_self'), str):
            map_node[node['id_self']] = node
        for value in node.values():
            _collect(value, map_node)
