"""
---

id_self:                pym_cctool.graph.sql
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
                        This module loads the base predicates and the
                        derived predicates into an in-memory SQLite
                        database, one table for each, with the columns
                        the logic program gives them. The derived
                        predicates are computed by clingo from
                        derive.lp, so they are defined once, for both
                        languages. The prose of each item is in
                        item_text, a full-text table. A query changes
                        nothing outside the database it runs in: one
                        that would attach a database, as ATTACH and
                        VACUUM INTO do, is refused.
edge:                   []

...
"""


import sqlite3

import cctool.graph.logic
import cctool.graph.extract


# A number is an integer in SQL, and a symbol is text.
#
MAP_TYPE          = {'symbol': 'TEXT', 'number': 'INTEGER'}

# The prose of each item, one row for each field, as an FTS5 table.
# Words are stemmed, so that a query for a field also finds fields.
#
SQL_TEXT          = ('CREATE VIRTUAL TABLE item_text USING fts5('
                     "id UNINDEXED, field UNINDEXED, text, tokenize = 'porter unicode61')")

# Why a query that would attach a database, and so make or change a
# file, is refused.
#
TEXT_ATTACH       = ('A query cannot attach a database, as ATTACH and VACUUM INTO do, since it '
                     'changes nothing outside the database it runs in.')


# -----------------------------------------------------------------------------
def connect(facts:    cctool.graph.extract.Facts,
            list_text: list[tuple[str, str, str]] = ()) -> sqlite3.Connection:
    """
    Return an in-memory database holding the base predicates of facts
    and the predicates derived from them, and item_text, a full-text
    table that holds the rows of list_text.

    """

    map_column = {name: tuple(cctool.graph.extract.column(spec) for spec in tuple_spec)
                  for (name, (tuple_spec, _)) in cctool.graph.extract.PREDICATE.items()}
    map_derive = cctool.graph.logic.derived()
    rules      = ''.join(cctool.graph.logic.show(name, map_derive) for name in map_derive)
    rows       = {name: sorted(set_row) for (name, set_row) in facts.items()}

    map_column.update(map_derive)
    rows.update(cctool.graph.logic.run(facts, rules))

    connection = sqlite3.connect(':memory:')

    for (name, tuple_column) in map_column.items():
        connection.execute('CREATE TABLE "{name}" ({column})'.format(
                              name   = name,
                              column = ', '.join('"{c}" {t}'.format(c = column,
                                                                     t = MAP_TYPE[type_column])
                                                 for (column, type_column) in tuple_column)))
        # The names are those declared in PREDICATE and derive.lp, not input.
        connection.executemany('INSERT INTO "{name}" VALUES ({mark})'.format(  # noqa: S608
                                  name = name,
                                  mark = ', '.join('?' * len(tuple_column))),
                               rows.get(name, []))

    connection.execute(SQL_TEXT)
    connection.executemany('INSERT INTO item_text VALUES (?, ?, ?)', list_text)

    return connection


# -----------------------------------------------------------------------------
def query(facts:     cctool.graph.extract.Facts,
          text:      str,
          list_text: list[tuple[str, str, str]] = ()) -> tuple[tuple[str, ...], list[tuple]]:
    """
    Return the columns and the rows of the query text, evaluated over
    facts and the prose in list_text. Raise sqlite3.Error if it cannot
    be evaluated, or if it would attach a database.

    """

    connection  = connect(facts, list_text)
    list_denied = []

    # -------------------------------------------------------------------------
    def authorize(action: int, *_) -> int:
        """
        Deny the attachment of a database, and allow anything else.

        """

        if action == sqlite3.SQLITE_ATTACH:
            list_denied.append(action)
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    connection.set_authorizer(authorize)

    try:
        cursor       = connection.execute(text)
        tuple_column = tuple(each[0] for each in cursor.description or ())
        return (tuple_column, cursor.fetchall())
    except sqlite3.DatabaseError as error:
        if list_denied:
            raise sqlite3.DatabaseError(TEXT_ATTACH) from error
        raise
    finally:
        connection.close()
