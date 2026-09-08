"""
---

id_self:                pym_test.test_relation
guid_self:              pym_f56e1bf5d13c4092b324a8457cd696c5
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Relation check tests
brief:                  |
                        Tests of the semantics a relation entry
                        declares: transitivity and incompatibility.
description:            |
                        Writes concept edges that break each declared
                        semantic and checks that the relation check
                        reports it, at the edge and with the severity
                        the defect earns. An edge a chain already
                        implies is advisory. Two incompatible
                        relations between one pair are critical.
relation:               []

...
"""


import cc_public.check
import cc_public.edit.link


NARROWER = 'r_is_narrower_than'
PART_OF  = 'r_is_part_of'


def _findings(tmp_path):
    report  = cc_public.check.check(list_path = [tmp_path])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'relation']
    return [(n['severity'], n['message']) for n in found['nonconformity']]


def test_the_glossary_as_it_stands_earns_nothing(tree, tmp_path):
    assert _findings(tmp_path) == []


def test_an_edge_a_chain_already_implies_is_advisory(tree, tmp_path):
    cc_public.edit.link.link(tree, 'term_source_item', NARROWER, 'term_item')
    assert _findings(tmp_path) == []                     # the chain alone says something
    cc_public.edit.link.link(tree, 'term_python_module', NARROWER, 'term_item')
    ((severity, message),) = _findings(tmp_path)
    assert severity == 'advisory'
    assert 'chain of its edges runs from term_python_module to term_item' in message


def test_two_incompatible_relations_between_one_pair_are_critical(tree, tmp_path):
    cc_public.edit.link.link(tree, 'term_port', NARROWER, 'term_component')
    ((severity, message),) = _findings(tmp_path)
    assert severity == 'critical'
    assert 'may not both hold between a pair' in message
    assert 'term_port and term_component' in message


def test_incompatibility_holds_whichever_way_the_other_edge_runs(tree, tmp_path):
    cc_public.edit.link.link(tree, 'term_source_item', PART_OF, 'term_python_module')
    ((severity, message),) = _findings(tmp_path)          # r_is_part_of declares nothing
    assert severity == 'critical'
    assert 'r_is_narrower_than and r_is_part_of' in message


def test_an_item_holding_more_edges_than_a_relation_allows_is_reported(tree, tmp_path):
    node = 'node_accept_requirement.accept'
    cc_public.edit.link.link(tree, node, 'r_instantiates', 'cmp_assess_concept')
    ((severity, message),) = _findings(tmp_path)
    assert severity == 'critical'
    assert 'at most 1 r_instantiates edge' in message and 'holds 2' in message


def test_an_item_holding_fewer_than_a_relation_requires_is_reported(tree, tmp_path):
    node = 'node_accept_requirement.accept'
    cc_public.edit.link.unlink(tree, node, 'r_instantiates', 'cmp_accept_requirement')
    ((severity, message),) = _findings(tmp_path)
    assert severity == 'critical'
    assert 'holds 0 r_instantiates edge' in message and 'at least 1' in message
