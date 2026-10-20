"""
---

id_self:                pym_cc_public.graph.text
guid_self:              pym_51510fcad31648b2b9291b35bea2f59b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Text search
brief:                  |
                        Find data items by the words of their prose,
                        ranked by BM25, and say what the graph holds
                        about each one.
description:            |
                        This module gives SQLite the prose of every
                        item as item_text, an FTS5 table, and ranks
                        the items whose prose matches a query. Each
                        hit is expanded through the graph: to the
                        decision it belongs to, to the ruling that
                        settles that decision and the options it
                        upholds, to the standing of an option, and to
                        the concerns an annotation speaks for. A grep
                        of the files finds the words; this also says
                        how each argument they appear in was settled.

                        A plain query that names a concept by one of
                        its preferred or admitted terms also matches
                        the other terms of that concept. The hits can
                        also be given to Datalog rules as text_hit
                        facts.
relation:               []

...
"""


import re
import sqlite3
import typing

import cc_public.graph.datalog
import cc_public.graph.extract
import cc_public.graph.sql


# The fields whose text is not prose: names, patterns, rights and the
# fields of a JSON Schema that hold no words.
#
SET_KEY_SKIP      = cc_public.graph.extract.SET_KEY_UNNAMED | {'copyright', 'license', 'type'}
PREFIX_SKIP       = (cc_public.graph.extract.PREFIX_ID,
                     cc_public.graph.extract.PREFIX_GUID,
                     '$')

# A word of a plain query. Each is matched on its own, and an item
# that matches more of them ranks higher.
#
REGEX_WORD        = re.compile(r'[A-Za-z0-9]+')

# The terms of a concept that widen a query: those that name it. A
# deprecated term is left out, because several are ordinary words with
# other senses.
#
TUPLE_KEY_TERM    = ('term_preferred', 'term_admitted')
PREFIX_CONCEPT    = 'con_'

# The query on its own, stemmed as item_text is, so that a term can be
# looked for in it as a phrase.
#
SQL_QUERY_TEXT    = ('CREATE VIRTUAL TABLE query_text USING fts5('
                     "text, tokenize = 'porter unicode61')")

# The rank of each item that matches, from 1 for the best, and the
# field it matches best in.
#
SQL_RANK          = """
SELECT id, field, min(score) AS score
FROM hit
GROUP BY id
ORDER BY score, id
"""

# A text hit as a relation for Datalog rules.
#
MAP_COLUMN_HIT    = {'text_hit': (('id',    cc_public.graph.extract.TYPE_SYMBOL),
                                  ('field', cc_public.graph.extract.TYPE_SYMBOL),
                                  ('rank',  cc_public.graph.datalog.TYPE_NUMBER))}

# Each field that matches, with its BM25 score, lower being better.
# bm25() can be used only in a plain query of the table, so the hits
# are kept in a table of their own, and so is what each hit is.
#
# What each hit is: the item, the field that matched best and its
# title, and what the graph says of it, read from the decision_of and
# settles tables that derive.lp gives. The decision is the one it belongs
# to, the ruling is the one that settles that decision, and upheld
# names the options that ruling upholds. The standing of an
# option is upheld, rejected or open. A higher score is a better
# match.
#
SQL_HIT           = """
CREATE TEMP TABLE hit AS
SELECT id, field, bm25(item_text) AS score
FROM item_text
WHERE item_text MATCH ?
"""

SQL_FOUND         = """
CREATE TEMP TABLE described AS
WITH best AS (
    SELECT id, field, min(score) AS score
    FROM hit
    GROUP BY id
),
settle AS MATERIALIZED (
    SELECT settles.ruling, edge.relation, settles.option, decision_of.decision
    FROM settles
    JOIN primary_edge AS edge ON edge.source = settles.ruling
                             AND edge.target = settles.option
                             AND edge.relation IN ('r_upholds', 'r_rejects')
    JOIN decision_of ON decision_of.id = settles.option
),
found AS MATERIALIZED (
    SELECT best.id,
           coalesce((SELECT type FROM type_of WHERE type_of.id = best.id), '') AS type,
           round(-best.score, 3) AS score,
           best.score AS bm25,
           best.field,
           coalesce((SELECT text FROM item_text
                     WHERE item_text.id = best.id AND item_text.field = 'title'), '') AS title,
           coalesce((SELECT min(decision) FROM decision_of
                     WHERE decision_of.id = best.id), '') AS decision
    FROM best
)
SELECT found.*,
           CASE WHEN type != 't_option' THEN ''
                ELSE coalesce((SELECT CASE settle.relation WHEN 'r_upholds' THEN 'upheld'
                                                           ELSE 'rejected' END
                               FROM settle WHERE settle.option = found.id), 'open')
           END AS standing,
           coalesce((SELECT group_concat(DISTINCT ruling ORDER BY ruling)
                     FROM settle WHERE settle.decision = found.decision), '') AS ruling,
           coalesce((SELECT group_concat(option, ' ' ORDER BY option)
                     FROM settle
                     WHERE settle.decision = found.decision AND settle.relation = 'r_upholds'),
                    '') AS upheld,
           coalesce((SELECT group_concat(target, ' ' ORDER BY target)
                     FROM primary_edge
                     WHERE source = found.id AND relation = 'r_speaks_for_concern'),
                    '') AS concerns
FROM found
"""

SQL_ITEM          = """
SELECT score, id, type, field, title, decision, standing, ruling, upheld, concerns
FROM described
ORDER BY bm25, id
"""

SQL_DECISION         = """
SELECT round(-min(bm25), 3) AS score, decision, count(*) AS hits,
       (SELECT text FROM item_text
        WHERE item_text.id = described.decision AND item_text.field = 'title') AS title,
       ruling, upheld
FROM described
WHERE decision != ''
GROUP BY decision
ORDER BY min(bm25), decision
"""


# -----------------------------------------------------------------------------
class ErrorText(Exception):
    """
    A text query that cannot be evaluated.

    """


# -----------------------------------------------------------------------------
def rows(map_document: cc_public.graph.extract.Documents) -> list[tuple[str, str, str]]:
    """
    Return a row for each field of prose of each item in map_document:
    the id of the item, the name of the field and its text. An item
    held inside another has rows of its own, and an edge or a list of
    words belongs to the item that holds it.

    """

    set_row = set()

    for (document, _) in map_document.values():
        if cc_public.graph.extract.is_document(document):
            _walk(document, '', '', set_row)

    return sorted(set_row)


# -----------------------------------------------------------------------------
def _walk(node: typing.Any, holder: str, key: str, set_row: set) -> None:
    """
    Add to set_row a row for each string of prose in node, which is
    the value of the field key of the item holder.

    """

    if isinstance(node, dict):
        id_self = node.get(cc_public.graph.extract.KEY_ID_SELF)
        holder  = id_self if isinstance(id_self, str) else holder
        for (key_child, value) in node.items():
            if isinstance(key_child, str) and _is_prose(key_child):
                _walk(value, holder, key_child, set_row)
    elif isinstance(node, list):
        for each in node:
            _walk(each, holder, key, set_row)
    elif isinstance(node, str) and holder and key:
        set_row.add((holder, key, str(node)))


# -----------------------------------------------------------------------------
def _is_prose(key: str) -> bool:
    """
    Return True if a field named key may hold prose to search.

    """

    return key not in SET_KEY_SKIP and not key.startswith(PREFIX_SKIP)


# -----------------------------------------------------------------------------
def match(text: str, list_term: typing.Sequence[str] = ()) -> str:
    """
    Return the FTS5 match expression for the plain query text: each of
    its words, quoted, and each of list_term as a phrase, any of which
    may match.

    """

    list_word = REGEX_WORD.findall(text)

    if not list_word:
        raise ErrorText('The query has no words to search for.')

    list_part = ['"{word}"'.format(word = word) for word in list_word]
    list_part.extend(_phrase(term) for term in list_term if REGEX_WORD.search(term))

    return ' OR '.join(list_part)


# -----------------------------------------------------------------------------
def _phrase(term: str) -> str:
    """
    Return term as an FTS5 phrase: its words, in order, in quotes.

    """

    return '"{words}"'.format(words = ' '.join(REGEX_WORD.findall(term)))


# -----------------------------------------------------------------------------
def terms(map_document: cc_public.graph.extract.Documents) -> list[tuple[str, tuple[str, ...]]]:
    """
    Return the id of each concept in map_document, with its preferred
    and admitted terms.

    """

    list_concept = []

    for (document, _) in map_document.values():
        if cc_public.graph.extract.is_document(document):
            _concepts(document, list_concept)

    return sorted(list_concept)


# -----------------------------------------------------------------------------
def _concepts(node: typing.Any, list_concept: list) -> None:
    """
    Add to list_concept each concept held in node, with its terms.

    """

    if isinstance(node, dict):
        id_self = node.get(cc_public.graph.extract.KEY_ID_SELF)
        if isinstance(id_self, str) and id_self.startswith(PREFIX_CONCEPT):
            list_term = []
            for key in TUPLE_KEY_TERM:
                value = node.get(key)
                list_term.extend([value] if isinstance(value, str) else value or [])
            list_term = [str(term) for term in list_term if term]
            if list_term:
                list_concept.append((id_self, tuple(list_term)))
        for value in node.values():
            _concepts(value, list_concept)
    elif isinstance(node, list):
        for each in node:
            _concepts(each, list_concept)


# -----------------------------------------------------------------------------
def widen(text: str, list_concept: list[tuple[str, tuple[str, ...]]]) -> list[tuple[str, str]]:
    """
    Return each term to add to the plain query text, with its concept:
    the other terms of each concept that text names by one of its
    terms. A term names a concept wherever its words, stemmed, are in
    text in order.

    """

    list_added = []
    connection = sqlite3.connect(':memory:')

    try:
        connection.execute(SQL_QUERY_TEXT)
        connection.execute('INSERT INTO query_text VALUES (?)', (text,))
        for (id_concept, tuple_term) in list_concept:
            set_named = {term for term in tuple_term
                         if REGEX_WORD.search(term) and _is_in(connection, term)}
            if set_named:
                list_added.extend((id_concept, term)
                                  for term in tuple_term if term not in set_named)
    finally:
        connection.close()

    return list_added


# -----------------------------------------------------------------------------
def _is_in(connection: sqlite3.Connection, term: str) -> bool:
    """
    Return True if the query held in connection has the words of term.

    """

    cursor = connection.execute('SELECT count(*) FROM query_text WHERE query_text MATCH ?',
                                (_phrase(term),))
    return cursor.fetchone()[0] > 0


# -----------------------------------------------------------------------------
def search(facts:        cc_public.graph.extract.Facts,
           map_document: cc_public.graph.extract.Documents,
           text:         str,
           is_match:     bool    = False,
           is_decision:  bool = False,
           list_term:    typing.Sequence[str] = ()) -> tuple[tuple[str, ...], list[tuple]]:
    """
    Return the columns and the rows of the items whose prose matches
    text, best first, each with its decision and the standing of what
    settles it. text is a plain query, or an FTS5 match expression if
    is_match. A plain query also matches each of list_term as a
    phrase. With is_decision, return a row for each decision instead, ranked
    by its best match. Raise ErrorText if text cannot be evaluated.

    """

    expression = text if is_match else match(text, list_term)
    connection = cc_public.graph.sql.connect(facts, rows(map_document))

    try:
        connection.execute(SQL_HIT, (expression,))
        connection.execute(SQL_FOUND)
        cursor = connection.execute(SQL_DECISION if is_decision else SQL_ITEM)
        return (tuple(each[0] for each in cursor.description), cursor.fetchall())
    except sqlite3.Error as error:
        raise ErrorText('The match expression cannot be read: {error}'.format(
                            error = error)) from error
    finally:
        connection.close()


# -----------------------------------------------------------------------------
def hits(map_document: cc_public.graph.extract.Documents,
         text:         str,
         is_match:     bool = False,
         list_term:    typing.Sequence[str] = ()) -> set[tuple[str, str, str]]:
    """
    Return a row of text_hit for each item whose prose matches text,
    read as search reads it: the id of the item, the field it matches
    best in, and its rank, from 1 for the best. Raise ErrorText if text
    cannot be evaluated.

    """

    expression = text if is_match else match(text, list_term)
    connection = sqlite3.connect(':memory:')

    try:
        connection.execute(cc_public.graph.sql.SQL_TEXT)
        connection.executemany('INSERT INTO item_text VALUES (?, ?, ?)', rows(map_document))
        connection.execute(SQL_HIT, (expression,))
        return {(id_item, field, str(rank))
                for (rank, (id_item, field, _)) in enumerate(connection.execute(SQL_RANK),
                                                             start = 1)}
    except sqlite3.Error as error:
        raise ErrorText('The match expression cannot be read: {error}'.format(
                            error = error)) from error
    finally:
        connection.close()
