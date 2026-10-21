"""
---

id_self:                pym_cc_public.graph._test.test_graph
guid_self:              pym_85dd4670224a4887a513f04411f2400e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Graph tests
brief:                  |
                        Tests of logic programs and SQL evaluation
                        over the facts of the graph.
description:            |
                        Each test queries a copy of the repository's
                        data items, and expects exactly the rows that
                        the query should return.
edge:                   []

...
"""


import sqlite3

import pytest

import cc_public.graph.logic
import cc_public.graph.extract
import cc_public.graph.sql
import cc_public.graph.text


ID_CONCERN = 'concern_safety'


def test_declared_reads_the_columns_of_each_predicate():
    text = '% decl a(x: symbol,\n%        y: number)\n  %decl b(z)\nc(1). % decl c(w)'
    assert cc_public.graph.logic.declared(text) == {'a': (('x', 'symbol'), ('y', 'number')),
                                                      'b': (('z', 'symbol'),)}


def test_worded_reads_the_did_and_fix_after_each_declaration():
    text = ('% decl a(x: symbol)\n% did  {x} is\n%      wrong.\n% fix  Mend it.\n#show a/1.\n'
            '% decl b(y: symbol)\n#show b/1.\n% decl c(z: symbol)\n% fix  Only this.')
    assert cc_public.graph.logic.worded(text) == {'a': {'did': '{x} is wrong.', 'fix': 'Mend it.'},
                                                    'c': {'fix': 'Only this.'}}


def test_described_words_each_row_and_gives_the_fix_once():
    rows        = {'a': [('p', 'f.yaml', '3'), ('q', 'f.yaml', '')], 'b': [('r',)]}
    map_column  = {'a': ('x', 'file', 'line'), 'b': ('y',)}
    map_wording = {'a': {'did': '{x} is wrong.', 'fix': 'Mend it.'}}
    assert cc_public.graph.logic.described(rows, map_column, map_wording) == [
               'f.yaml:3: a: p is wrong.',
               'f.yaml: a: q is wrong.',
               '  fix: Mend it.',
               'b: r']


def test_output_reads_every_predicate_named_in_order():
    text = '#show b/1.\n#show a/2. #show c / 0 . % #show d/1.\n#show b/1.'
    assert cc_public.graph.logic.output(text) == ['b', 'a', 'c']


def test_logic_returns_each_output_predicate_in_order(tree):
    facts = cc_public.graph.extract.extract(tree)
    rules = ('#show t/1. #show i/1.\n'
             't(Type) :- has_type("{c}", Type).\n'
             'i(Id) :- item(Id, _, _, _, _), Id = "{c}".').format(c = ID_CONCERN)
    rows  = cc_public.graph.logic.run(facts, rules)
    assert list(rows.items()) == [('t', [('type_concern',)]), ('i', [(ID_CONCERN,)])]


def test_logic_reports_where_the_rules_begin(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(cc_public.graph.logic.ErrorLogic, match = 'rules given begin at line'):
        cc_public.graph.logic.run(facts, '#show o/1. o(X) :- item(X), not p(Y).')


def test_logic_refuses_a_predicate_that_nothing_defines(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(cc_public.graph.logic.ErrorLogic, match = 'does not occur in any rule head'):
        cc_public.graph.logic.run(facts, '#show o/1. o(X) :- itme(X, _, _, _, _).')


def test_logic_accepts_an_input_predicate_with_no_rows(tree):
    facts = cc_public.graph.extract.extract(tree)
    facts['inverse_relation'] = set()
    rows  = cc_public.graph.logic.run(facts, '#show o/1. o(X) :- inverse_relation(X, _).')
    assert rows == {'o': []}


def test_logic_refuses_rules_with_no_answer_set(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(cc_public.graph.logic.ErrorLogic, match = 'no answer set'):
        cc_public.graph.logic.run(facts, '#show o/1. o(X) :- tree_file(X). :- tree_file(_).')


def test_logic_refuses_rules_with_more_than_one_answer_set(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(cc_public.graph.logic.ErrorLogic, match = 'more than one answer set'):
        cc_public.graph.logic.run(facts, '#show o/1. {o(1); o(2)}.')


def test_a_fact_with_a_tab_or_a_newline_is_read_as_written(tree):
    text = 'A tab\there, and a newline\nthere, with \\ and "quotes".'
    facts = cc_public.graph.extract.extract(tree)
    facts['tree_file'].add((text,))
    rows  = cc_public.graph.logic.run(facts, '#show f/1. f(F) :- tree_file(F), F = "{}".'.format(
        text.translate(cc_public.graph.logic.MAP_ESCAPE)))
    assert rows == {'f': [(text,)]}


def test_sql_sees_base_and_derived_predicates(tree):
    facts = cc_public.graph.extract.extract(tree)
    text  = ("SELECT item.id, has_type.type FROM item JOIN has_type USING (id) "
             "WHERE id = 'concern_safety'")
    assert cc_public.graph.sql.query(facts, text) == (('id', 'type'), [(ID_CONCERN, 'type_concern')])


def test_a_reference_field_is_an_edge_of_the_graph(tree):
    facts = cc_public.graph.extract.extract(tree)
    rows  = cc_public.graph.logic.run(facts, '#show o/2. o(S, T) :- graph_edge(S, "concept", T), '
                                             'S = "type_concern".')
    assert rows == {'o': [('type_concern', 'concept_concern')]}


def test_sql_reports_an_error(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(sqlite3.Error):
        cc_public.graph.sql.query(facts, 'SELECT nothing FROM nowhere')


def test_an_item_in_a_docstring_is_placed_on_its_line_of_the_file(tree):
    path = tree / 'src/x/y.py'
    path.parent.mkdir(parents = True)
    path.write_text('# A comment.\n"""\n\n---\nid_self: pym_x.y\nguid_self: pym_1\n...\n"""\n')
    facts = cc_public.graph.extract.extract(tree)
    assert ('pym_x.y', 'pym_1', '', 'src/x/y.py', '5') in facts['item']


def test_a_comment_header_may_follow_the_line_that_names_an_interpreter(tree):
    path = tree / 'src/x.sh'
    path.parent.mkdir(exist_ok = True)
    path.write_text('#!/bin/sh\n# ---\n# id_self: file_x\n# guid_self: file_1\n# ...\n')
    facts = cc_public.graph.extract.extract(tree)
    assert ('file_x', 'file_1', '', 'src/x.sh', '3') in facts['item']


def test_a_line_is_an_integer_in_sql(tree):
    facts = cc_public.graph.extract.extract(tree)
    text  = ("SELECT typeof(line) AS t FROM item "
             "UNION SELECT typeof(line) AS t FROM reference")
    assert cc_public.graph.sql.query(facts, text) == (('t',), [('integer',)])


def test_text_rows_hold_the_prose_of_each_item_and_no_names(tree):
    list_row = cc_public.graph.text.rows(cc_public.graph.extract.documents(tree))
    assert ('dec_cross_item_checks_engine', 'title', 'Engine of the cross-item checks') in list_row
    assert not [row for row in list_row
                if row[1].startswith(('id_', 'guid_', '$')) or row[1] == 'copyright']


def test_text_names_the_decision_and_standing_of_each_option_it_finds(tree):
    map_document          = cc_public.graph.extract.documents(tree)
    facts                 = cc_public.graph.extract.facts_of(map_document)
    (tuple_column, rows)  = cc_public.graph.text.search(facts, map_document,
                                                        'cross-item checks in Souffle or Rust')
    map_hit               = {row[1]: dict(zip(tuple_column, row, strict = True)) for row in rows}
    assert map_hit['opt_cross_item_checks_in_souffle']['standing']      == 'rejected'
    assert map_hit['opt_cross_item_checks_in_souffle']['ruling'] == 'ruling_cross_item_checks_engine'
    assert map_hit['opt_cross_item_checks_in_souffle']['upheld']        == 'opt_cross_item_checks_in_clingo'
    assert map_hit['opt_tooling_in_rust']['standing']                   == 'open'
    assert map_hit['opt_tooling_in_rust']['decision']                      == 'dec_tooling_language'


def test_text_by_decision_leads_from_any_hit_to_its_decision(tree):
    map_document  = cc_public.graph.extract.documents(tree)
    facts         = cc_public.graph.extract.facts_of(map_document)
    (_, rows)     = cc_public.graph.text.search(facts, map_document, 'souffle clingo',
                                                is_decision = True)
    assert rows[0][1] == 'dec_cross_item_checks_engine'


def test_text_widens_a_query_by_the_other_terms_of_the_concept_it_names(tree):
    list_concept = cc_public.graph.text.terms(cc_public.graph.extract.documents(tree))
    assert ('concept_register_entry', 'register entry') in cc_public.graph.text.widen(
        'each regentry', list_concept)
    assert ('concept_register_entry', 'regentry') in cc_public.graph.text.widen(
        'the register entries', list_concept)
    assert not [concept for (concept, _) in cc_public.graph.text.widen('a list', list_concept)
                if concept == 'concept_register']
    assert cc_public.graph.text.match('each regentry', ['register entry']) == (
        '"each" OR "regentry" OR "register entry"')


def test_text_hits_rank_each_item_once_for_logic(tree):
    map_document = cc_public.graph.extract.documents(tree)
    facts        = cc_public.graph.extract.facts_of(map_document)
    set_hit      = cc_public.graph.text.hits(map_document, 'souffle clingo')
    assert sorted(int(rank) for (_, _, rank) in set_hit) == list(range(1, len(set_hit) + 1))
    rules        = '#show best/1.\nbest(Id) :- text_hit(Id, _, Rank), Rank < 2.'
    rows         = cc_public.graph.logic.run(facts | {'text_hit': set_hit}, rules,
                                               cc_public.graph.text.MAP_COLUMN_HIT)
    assert len(rows['best']) == 1


def test_text_refuses_a_query_it_cannot_read(tree):
    map_document = cc_public.graph.extract.documents(tree)
    facts        = cc_public.graph.extract.facts_of(map_document)
    with pytest.raises(cc_public.graph.text.ErrorText):
        cc_public.graph.text.search(facts, map_document, '-- ?')
    with pytest.raises(cc_public.graph.text.ErrorText):
        cc_public.graph.text.search(facts, map_document, 'AND', is_match = True)


def test_sql_searches_the_prose_of_items(tree):
    map_document = cc_public.graph.extract.documents(tree)
    facts        = cc_public.graph.extract.facts_of(map_document)
    text         = ("SELECT id FROM item_text WHERE item_text MATCH 'souffle' "
                    "AND id = 'opt_cross_item_checks_in_souffle' AND field = 'title'")
    assert cc_public.graph.sql.query(facts, text, cc_public.graph.text.rows(map_document)) == (
        ('id',), [('opt_cross_item_checks_in_souffle',)])
