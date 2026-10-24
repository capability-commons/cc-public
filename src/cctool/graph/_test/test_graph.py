"""
---

id_self:                pym_cctool.graph._test.test_graph
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

import cctool.graph.item
import cctool.graph.logic
import cctool.graph.extract
import cctool.graph.prefix
import cctool.graph.sql
import cctool.graph.text


ID_CONCERN = 'concern_safety'


def test_declared_reads_the_columns_of_each_predicate():
    text = '% decl a(x: symbol,\n%        y: number)\n  %decl b(z)\nc(1). % decl c(w)'
    assert cctool.graph.logic.declared(text) == {'a': (('x', 'symbol'), ('y', 'number')),
                                                      'b': (('z', 'symbol'),)}


def test_worded_reads_the_did_and_fix_in_the_item_of_each_predicate():
    text = ('% ---\n% did: |\n%   {x} is\n%   wrong.\n% fix: Mend it.\n% ...\n'
            '% decl a(x: symbol)\n#show a/1.\n'
            '% decl b(y: symbol)\n#show b/1.\n'
            '% ---\n% fix: Only this.\n% ...\n% decl c(z: symbol)\n'
            '% did  The older form,\n% fix  which is not read.\n')
    assert cctool.graph.logic.worded(text) == {'a': {'did': '{x} is wrong.', 'fix': 'Mend it.'},
                                                    'c': {'fix': 'Only this.'}}


def test_described_words_each_row_and_gives_the_fix_once():
    rows        = {'a': [('p', 'f.yaml', '3'), ('q', 'f.yaml', '')], 'b': [('r',)]}
    map_column  = {'a': ('x', 'file', 'line'), 'b': ('y',)}
    map_wording = {'a': {'did': '{x} is wrong.', 'fix': 'Mend it.'}}
    assert cctool.graph.logic.described(rows, map_column, map_wording) == [
               'f.yaml:3: a: p is wrong.',
               'f.yaml: a: q is wrong.',
               '  fix: Mend it.',
               'b: r']


def test_output_reads_every_predicate_named_in_order():
    text = '#show b/1.\n#show a/2. #show c / 0 . % #show d/1.\n#show b/1.'
    assert cctool.graph.logic.output(text) == ['b', 'a', 'c']


def test_logic_returns_each_output_predicate_in_order(tree):
    facts = cctool.graph.extract.extract(tree)
    rules = ('#show t/1. #show i/1.\n'
             't(Type) :- has_type("{c}", Type).\n'
             'i(Id) :- item(Id, _, _, _, _), Id = "{c}".').format(c = ID_CONCERN)
    rows  = cctool.graph.logic.run(facts, rules)
    assert list(rows.items()) == [('t', [('type_concern',)]), ('i', [(ID_CONCERN,)])]


def test_logic_reports_where_the_rules_begin(tree):
    facts = cctool.graph.extract.extract(tree)
    with pytest.raises(cctool.graph.logic.ErrorLogic, match = 'rules given begin at line'):
        cctool.graph.logic.run(facts, '#show o/1. o(X) :- item(X), not p(Y).')


def test_logic_refuses_a_predicate_that_nothing_defines(tree):
    facts = cctool.graph.extract.extract(tree)
    with pytest.raises(cctool.graph.logic.ErrorLogic, match = 'does not occur in any rule head'):
        cctool.graph.logic.run(facts, '#show o/1. o(X) :- itme(X, _, _, _, _).')


def test_logic_accepts_an_input_predicate_with_no_rows(tree):
    facts = cctool.graph.extract.extract(tree)
    facts['inverse_relation'] = set()
    rows  = cctool.graph.logic.run(facts, '#show o/1. o(X) :- inverse_relation(X, _).')
    assert rows == {'o': []}


def test_logic_refuses_rules_with_no_answer_set(tree):
    facts = cctool.graph.extract.extract(tree)
    with pytest.raises(cctool.graph.logic.ErrorLogic, match = 'no answer set'):
        cctool.graph.logic.run(facts, '#show o/1. o(X) :- tree_file(X). :- tree_file(_).')


def test_logic_refuses_rules_with_more_than_one_answer_set(tree):
    facts = cctool.graph.extract.extract(tree)
    with pytest.raises(cctool.graph.logic.ErrorLogic, match = 'more than one answer set'):
        cctool.graph.logic.run(facts, '#show o/1. {o(1); o(2)}.')


def test_a_fact_with_a_tab_or_a_newline_is_read_as_written(tree):
    text = 'A tab\there, and a newline\nthere, with \\ and "quotes".'
    facts = cctool.graph.extract.extract(tree)
    facts['tree_file'].add((text,))
    rows  = cctool.graph.logic.run(facts, '#show f/1. f(F) :- tree_file(F), F = "{}".'.format(
        text.translate(cctool.graph.logic.MAP_ESCAPE)))
    assert rows == {'f': [(text,)]}


def test_sql_sees_base_and_derived_predicates(tree):
    facts = cctool.graph.extract.extract(tree)
    text  = ("SELECT item.id, has_type.type FROM item JOIN has_type USING (id) "
             "WHERE id = 'concern_safety'")
    assert cctool.graph.sql.query(facts, text) == (('id', 'type'), [(ID_CONCERN, 'type_concern')])


def test_a_reference_field_is_an_edge_of_the_graph(tree):
    facts = cctool.graph.extract.extract(tree)
    rows  = cctool.graph.logic.run(facts, '#show o/2. o(S, T) :- graph_edge(S, "concept", T), '
                                             'S = "type_concern".')
    assert rows == {'o': [('type_concern', 'concept_concern')]}


def test_sql_reports_an_error(tree):
    facts = cctool.graph.extract.extract(tree)
    with pytest.raises(sqlite3.Error):
        cctool.graph.sql.query(facts, 'SELECT nothing FROM nowhere')


def test_an_item_in_a_docstring_is_placed_on_its_line_of_the_file(tree):
    path = tree / 'src/x/y.py'
    path.parent.mkdir(parents = True)
    path.write_text('# A comment.\n"""\n\n---\nid_self: pym_x.y\nguid_self: pym_1\n...\n"""\n')
    facts = cctool.graph.extract.extract(tree)
    assert ('pym_x.y', 'pym_1', '', 'src/x/y.py', '5') in facts['item']


def test_a_comment_header_may_follow_the_line_that_names_an_interpreter(tree):
    path = tree / 'src/x.sh'
    path.parent.mkdir(exist_ok = True)
    path.write_text('#!/bin/sh\n# ---\n# id_self: file_x\n# guid_self: file_1\n# ...\n')
    facts = cctool.graph.extract.extract(tree)
    assert ('file_x', 'file_1', '', 'src/x.sh', '3') in facts['item']


def test_a_line_is_an_integer_in_sql(tree):
    facts = cctool.graph.extract.extract(tree)
    text  = ("SELECT typeof(line) AS t FROM item "
             "UNION SELECT typeof(line) AS t FROM reference")
    assert cctool.graph.sql.query(facts, text) == (('t',), [('integer',)])


def test_text_rows_hold_the_prose_of_each_item_and_no_names(tree):
    list_row = cctool.graph.text.rows(cctool.graph.extract.documents(tree))
    assert ('dec_cross_item_checks_engine', 'title', 'Engine of the cross-item checks') in list_row
    assert not [row for row in list_row
                if row[1].startswith(('id_', 'guid_', '$')) or row[1] == 'copyright']


def test_text_names_the_decision_and_standing_of_each_option_it_finds(tree):
    map_document          = cctool.graph.extract.documents(tree)
    facts                 = cctool.graph.extract.facts_of(map_document)
    (tuple_column, rows)  = cctool.graph.text.search(facts, map_document,
                                                     'cross-item checks in Souffle or Rust')
    map_hit               = {row[1]: dict(zip(tuple_column, row, strict = True)) for row in rows}
    assert map_hit['opt_cross_item_checks_in_souffle']['standing']      == 'rejected'
    assert map_hit['opt_cross_item_checks_in_souffle']['ruling'] == 'ruling_cross_item_checks_engine'
    assert map_hit['opt_cross_item_checks_in_souffle']['upheld']        == 'opt_cross_item_checks_in_clingo'
    assert map_hit['opt_tooling_in_rust']['standing']                   == 'open'
    assert map_hit['opt_tooling_in_rust']['decision']                      == 'dec_tooling_language'


def test_text_by_decision_leads_from_any_hit_to_its_decision(tree):
    map_document  = cctool.graph.extract.documents(tree)
    facts         = cctool.graph.extract.facts_of(map_document)
    (_, rows)     = cctool.graph.text.search(facts, map_document, 'souffle clingo',
                                             is_decision = True)
    assert rows[0][1] == 'dec_cross_item_checks_engine'


def test_text_widens_a_query_by_the_other_terms_of_the_concept_it_names(tree):
    list_concept = cctool.graph.text.terms(cctool.graph.extract.documents(tree))
    assert ('concept_register_entry', 'register entry') in cctool.graph.text.widen(
        'each regentry', list_concept)
    assert ('concept_register_entry', 'regentry') in cctool.graph.text.widen(
        'the register entries', list_concept)
    assert not [concept for (concept, _) in cctool.graph.text.widen('a list', list_concept)
                if concept == 'concept_register']
    assert cctool.graph.text.match('each regentry', ['register entry']) == (
        '"each" OR "regentry" OR "register entry"')


def test_text_hits_rank_each_item_once_for_logic(tree):
    map_document = cctool.graph.extract.documents(tree)
    facts        = cctool.graph.extract.facts_of(map_document)
    set_hit      = cctool.graph.text.hits(map_document, 'souffle clingo')
    assert sorted(int(rank) for (_, _, rank) in set_hit) == list(range(1, len(set_hit) + 1))
    rules        = '#show best/1.\nbest(Id) :- text_hit(Id, _, Rank), Rank < 2.'
    rows         = cctool.graph.logic.run(facts | {'text_hit': set_hit}, rules,
                                               cctool.graph.text.MAP_COLUMN_HIT)
    assert len(rows['best']) == 1


def test_text_refuses_a_query_it_cannot_read(tree):
    map_document = cctool.graph.extract.documents(tree)
    facts        = cctool.graph.extract.facts_of(map_document)
    with pytest.raises(cctool.graph.text.ErrorText):
        cctool.graph.text.search(facts, map_document, '-- ?')
    with pytest.raises(cctool.graph.text.ErrorText):
        cctool.graph.text.search(facts, map_document, 'AND', is_match = True)


def test_sql_searches_the_prose_of_items(tree):
    map_document = cctool.graph.extract.documents(tree)
    facts        = cctool.graph.extract.facts_of(map_document)
    text         = ("SELECT id FROM item_text WHERE item_text MATCH 'souffle' "
                    "AND id = 'opt_cross_item_checks_in_souffle' AND field = 'title'")
    assert cctool.graph.sql.query(facts, text, cctool.graph.text.rows(map_document)) == (
        ('id',), [('opt_cross_item_checks_in_souffle',)])


def test_a_link_to_a_term_reads_as_the_term():
    text = 'Each [[items]] and [[concept_item|thing]].'
    assert cctool.graph.item.terms(text) == 'Each items and thing.'
    assert cctool.graph.item.terms(text, lambda term, concept: concept or term) == (
        'Each items and concept_item.')


def test_a_term_is_found_in_text_by_its_longest_form_and_not_in_links_or_ids(tree):
    map_document = cctool.graph.extract.documents(tree)
    terms        = cctool.graph.extract._terms(map_document)
    text         = 'Data items, two entries and a [[data item]] in reg_data_item_type.'
    plain        = cctool.graph.extract.REGEX_TERM_LINK.sub(lambda m: ' ' * len(m.group(0)),
                                                              text)
    plain        = cctool.graph.extract.REGEX_MENTION.sub(lambda m: ' ' * len(m.group(0)),
                                                            plain)
    assert cctool.graph.extract._term_words(plain, terms) == [('data item', 0),
                                                                  ('entry', 16)]


def test_the_prefix_of_each_type_is_the_one_its_register_entry_gives(tree):
    facts = cctool.graph.extract.extract(tree)
    map_register = {row[0]: row[1] for row in facts['type_prefix']}
    assert map_register == cctool.graph.prefix.MAP_PREFIX
