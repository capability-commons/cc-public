"""
---

id_self:                pym_cc_public.web._test.test_restriction
guid_self:              pym_55673c5342ee4f5ab59c0954a90953ab
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Relation restriction page tests
brief:                  |
                        Tests of the sentences that relation and role
                        pages show about relation restrictions.
description:            |
                        Each test reads a copy of the repository and
                        checks the sentences of a relation or role
                        page, served or composed.
relation:               []

...
"""


import http

import cc_public.web.argument
import cc_public.web.restriction
import cc_public.web.server


# -----------------------------------------------------------------------------
def _body(tree, id_item):
    """
    Return the page of id_item, served from the tree.

    """

    (status, _, body) = cc_public.web.server.respond(tree, '/item/' + id_item)
    assert status == http.HTTPStatus.OK
    return body.decode()


# -----------------------------------------------------------------------------
def _excluded(tree, id_role):
    """
    Turn the literal that admits id_role in the relation restriction
    register into one that excludes it. The graph of the review reads
    ids, so the guid of the relation is left as it was.

    """

    path = tree / '_data/register/reg_relation_restriction.yaml'
    text = path.read_text()
    old  = 'id_relation:    r_admits\n'
    end  = 'id_target:      {id}\n'.format(id = id_role)
    stop = text.index(end)
    head = text.rindex(old, 0, stop)
    path.write_text(text[:head] + 'id_relation:    r_excludes\n' + text[head + len(old):])


def test_a_relation_page_reads_each_end_by_its_restrictions(tree):
    body = _body(tree, 'r_supports')
    assert 'The source <a href="/item/rrs_is_argument">is an argument</a>.' in body
    assert 'The target <a href="/item/rrs_is_arguable">is arguable</a>.' in body


def test_a_relation_page_says_an_end_without_restrictions_is_open(tree):
    assert 'The target is open to any item.' in _body(tree, 'r_is_about')


def test_a_role_page_names_its_players_and_the_relations_that_admit_it(tree):
    body = _body(tree, 'rol_arguable')
    assert ('Played by the items of <a href="/type/t_annotation">Annotation type</a> and '
            '<a href="/type/t_option">Option type</a>.') in body
    assert ('Admitted at the target of <a href="/item/r_challenges">Challenges relation</a> and '
            '<a href="/item/r_supports">Supports relation</a>.') in body


def test_a_role_page_names_the_relations_that_exclude_it(tree):
    _excluded(tree, 'rol_requirement')
    graph = cc_public.web.argument.Graph(tree)
    assert cc_public.web.restriction.sentences(graph, 'rol_requirement')[1:] == [
        ['Excluded at the source of ',
         ('r_has_actor', 'Has actor relation'), ', ',
         ('r_has_process', 'Has process relation'), ' and ',
         ('r_has_subject', 'Has subject relation'), '.']]


def test_an_item_that_is_neither_relation_nor_role_has_no_sentences(tree):
    graph = cc_public.web.argument.Graph(tree)
    assert cc_public.web.restriction.sentences(graph, 'rrs_is_argument') == []

