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
                        Tests of Datalog and SQL evaluation over the
                        facts of the graph.
description:            |
                        Each test queries a copy of the repository's
                        data items, and expects exactly the rows that
                        the query should return.
relation:               []

...
"""


import sqlite3

import pytest

import cc_public.graph.datalog
import cc_public.graph.extract
import cc_public.graph.sql


ID_CONCERN = 'concern_safety'


def test_declared_reads_the_columns_of_each_relation():
    text = '.decl a(x:symbol, y:number)\n.decl b(\n    z)'
    assert cc_public.graph.datalog.declared(text) == {'a': (('x', 'symbol'), ('y', 'number')),
                                                      'b': (('z', 'symbol'),)}


def test_output_reads_every_relation_named_in_order():
    text = '.output b\n.output a, c .output b'
    assert cc_public.graph.datalog.output(text) == ['b', 'a', 'c']


def test_datalog_returns_each_output_relation_in_order(tree):
    facts = cc_public.graph.extract.extract(tree)
    rules = ('.decl t(type:symbol) .decl i(id:symbol) .output t, i\n'
             't(x) :- type_of("{c}", x).\n'
             'i(x) :- item(x, _, _, _, _), x = "{c}".').format(c = ID_CONCERN)
    rows  = cc_public.graph.datalog.run(facts, rules)
    assert list(rows.items()) == [('t', [('t_concern',)]), ('i', [(ID_CONCERN,)])]


def test_datalog_reports_where_the_rules_begin(tree):
    facts = cc_public.graph.extract.extract(tree)
    with pytest.raises(cc_public.graph.datalog.ErrorDatalog, match = 'rules given begin at line'):
        cc_public.graph.datalog.run(facts, '.decl o(x:symbol) .output o o(x) :- item(x).')


def test_sql_sees_base_and_derived_relations(tree):
    facts = cc_public.graph.extract.extract(tree)
    text  = ("SELECT item.id, type_of.type FROM item JOIN type_of USING (id) "
             "WHERE id = 'concern_safety'")
    assert cc_public.graph.sql.query(facts, text) == (('id', 'type'), [(ID_CONCERN, 't_concern')])


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
