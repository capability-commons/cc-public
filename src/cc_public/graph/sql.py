"""
---

id_self:                pym_cc_public.graph.sql
guid_self:              pym_a916d15a71794a0f901fcf461341734d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  SQL evaluation
brief:                  |
                        Evaluate an SQL query over the facts of the
                        graph of data items, with SQLite.
description:            |
                        This module loads the base relations and the
                        derived relations into an in-memory SQLite
                        database, one table for each, with the columns
                        Datalog gives them. The derived relations are
                        computed by souffle from derive.dl, so they
                        are defined once, for both languages. A query
                        changes nothing outside the database it runs
                        in.
relation:               []

...
"""


import sqlite3

import cc_public.graph.datalog
import cc_public.graph.extract


# -----------------------------------------------------------------------------
def connect(facts: cc_public.graph.extract.Facts) -> sqlite3.Connection:
    """
    Return an in-memory database holding the base relations of facts
    and the relations derived from them.

    """

    map_column = {name: tuple_column for (name, (tuple_column, _))
                                      in cc_public.graph.extract.RELATION.items()}
    map_derive = cc_public.graph.datalog.derived()
    rules      = ''.join('.output {name}\n'.format(name = name) for name in map_derive)
    rows       = {name: sorted(set_row) for (name, set_row) in facts.items()}

    map_column.update(map_derive)
    rows.update(cc_public.graph.datalog.run(facts, rules))

    connection = sqlite3.connect(':memory:')

    for (name, tuple_column) in map_column.items():
        connection.execute('CREATE TABLE "{name}" ({column})'.format(
                              name   = name,
                              column = ', '.join('"{c}" TEXT'.format(c = column)
                                                 for column in tuple_column)))
        # The names are those declared in RELATION and derive.dl, not input.
        connection.executemany('INSERT INTO "{name}" VALUES ({mark})'.format(  # noqa: S608
                                  name = name,
                                  mark = ', '.join('?' * len(tuple_column))),
                               rows.get(name, []))

    return connection


# -----------------------------------------------------------------------------
def query(facts: cc_public.graph.extract.Facts,
          text:  str) -> tuple[tuple[str, ...], list[tuple]]:
    """
    Return the columns and the rows of the query text, evaluated over
    facts. Raise sqlite3.Error if it cannot be evaluated.

    """

    connection = connect(facts)

    try:
        cursor       = connection.execute(text)
        tuple_column = tuple(each[0] for each in cursor.description or ())
        return (tuple_column, cursor.fetchall())
    finally:
        connection.close()
