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
                        issue it belongs to, to the determination that
                        settles that issue and the decisions it
                        upholds, to the standing of a decision, and to
                        the concerns an annotation argues for. A grep
                        of the files finds the words; this also says
                        how each argument they appear in was settled.
relation:               []

...
"""


import re
import sqlite3
import typing

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

# Each field that matches, with its BM25 score, lower being better.
# bm25() can be used only in a plain query of the table, so the hits
# are kept in a table of their own, and so is what each hit is.
#
# What each hit is: the item, the field that matched best and its
# title, and what the graph says of it. The issue is the one it belongs
# to, the determination is the one that settles that issue, and upheld
# names the decisions that determination upholds. The standing of a
# decision is upheld, rejected or open. A higher score is a better
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
issue_of AS (
    SELECT id, id AS issue FROM type_of WHERE type = 't_issue'
    UNION
    SELECT source, target FROM primary_edge WHERE relation = 'r_answers'
    UNION
    SELECT edge.source, edge.target
    FROM primary_edge AS edge
    JOIN type_of AS source ON source.id = edge.source AND source.type = 't_annotation'
    JOIN type_of AS target ON target.id = edge.target AND target.type = 't_issue'
    WHERE edge.relation = 'r_is_about'
    UNION
    SELECT settle.source, answer.target
    FROM primary_edge AS settle
    JOIN primary_edge AS answer ON answer.source = settle.target
                               AND answer.relation = 'r_answers'
    WHERE settle.relation IN ('r_upholds', 'r_rejects')
),
settle AS (
    SELECT edge.source AS determination, edge.relation, edge.target AS decision,
           issue_of.issue
    FROM primary_edge AS edge
    JOIN issue_of ON issue_of.id = edge.target
    WHERE edge.relation IN ('r_upholds', 'r_rejects')
),
found AS (
    SELECT best.id,
           coalesce((SELECT type FROM type_of WHERE type_of.id = best.id), '') AS type,
           round(-best.score, 3) AS score,
           best.score AS bm25,
           best.field,
           coalesce((SELECT text FROM item_text
                     WHERE item_text.id = best.id AND item_text.field = 'title'), '') AS title,
           coalesce((SELECT min(issue) FROM issue_of WHERE issue_of.id = best.id), '') AS issue
    FROM best
)
SELECT found.*,
           CASE WHEN type != 't_decision' THEN ''
                ELSE coalesce((SELECT CASE settle.relation WHEN 'r_upholds' THEN 'upheld'
                                                           ELSE 'rejected' END
                               FROM settle WHERE settle.decision = found.id), 'open')
           END AS standing,
           coalesce((SELECT group_concat(DISTINCT determination ORDER BY determination)
                     FROM settle WHERE settle.issue = found.issue), '') AS determination,
           coalesce((SELECT group_concat(decision, ' ' ORDER BY decision)
                     FROM settle
                     WHERE settle.issue = found.issue AND settle.relation = 'r_upholds'),
                    '') AS upheld,
           coalesce((SELECT group_concat(target, ' ' ORDER BY target)
                     FROM primary_edge
                     WHERE source = found.id AND relation = 'r_argues_for_concern'),
                    '') AS concerns
FROM found
"""

SQL_ITEM          = """
SELECT score, id, type, field, title, issue, standing, determination, upheld, concerns
FROM described
ORDER BY bm25, id
"""

SQL_ISSUE         = """
SELECT round(-min(bm25), 3) AS score, issue, count(*) AS hits,
       (SELECT text FROM item_text
        WHERE item_text.id = described.issue AND item_text.field = 'title') AS title,
       determination, upheld
FROM described
WHERE issue != ''
GROUP BY issue
ORDER BY min(bm25), issue
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
def match(text: str) -> str:
    """
    Return the FTS5 match expression for the plain query text: each of
    its words, quoted, any of which may match.

    """

    list_word = REGEX_WORD.findall(text)

    if not list_word:
        raise ErrorText('The query has no words to search for.')

    return ' OR '.join('"{word}"'.format(word = word) for word in list_word)


# -----------------------------------------------------------------------------
def search(facts:        cc_public.graph.extract.Facts,
           map_document: cc_public.graph.extract.Documents,
           text:         str,
           is_match:     bool = False,
           is_issue:     bool = False) -> tuple[tuple[str, ...], list[tuple]]:
    """
    Return the columns and the rows of the items whose prose matches
    text, best first, each with its issue and the standing of what
    settles it. text is a plain query, or an FTS5 match expression if
    is_match. With is_issue, return a row for each issue instead,
    ranked by its best match. Raise ErrorText if text cannot be
    evaluated.

    """

    expression = text if is_match else match(text)
    connection = cc_public.graph.sql.connect(facts, rows(map_document))

    try:
        connection.execute(SQL_HIT, (expression,))
        connection.execute(SQL_FOUND)
        cursor = connection.execute(SQL_ISSUE if is_issue else SQL_ITEM)
        return (tuple(each[0] for each in cursor.description), cursor.fetchall())
    except sqlite3.Error as error:
        raise ErrorText('The match expression cannot be read: {error}'.format(
                            error = error)) from error
    finally:
        connection.close()
