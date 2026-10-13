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
    text = '.decl a(x:symbol, y:number)\n.decl b(\n    z:symbol)'
    assert cc_public.graph.datalog.declared(text) == {'a': ('x', 'y'), 'b': ('z',)}


def test_output_reads_every_relation_named_in_order():
    text = '.output b\n.output a, c .output b'
    assert cc_public.graph.datalog.output(text) == ['b', 'a', 'c']


def test_datalog_returns_each_output_relation_in_order(tree):
    facts = cc_public.graph.extract.extract(tree)
    rules = ('.decl t(type:symbol) .decl i(id:symbol) .output t, i\n'
             't(x) :- type_of("{c}", x).\n'
             'i(x) :- item(x, _, _, _), x = "{c}".').format(c = ID_CONCERN)
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
