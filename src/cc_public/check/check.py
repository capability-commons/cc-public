"""
---

id_self:                pym_cc_public.check.check
guid_self:              pym_56d08447c0cf432dbe39760c22730116
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Check
brief:                  |
                        Check the graph of data items held in the
                        tree, by evaluating check.lp over facts
                        extracted from it.
description:            |
                        This module extracts the facts of the tree,
                        evaluates check.lp over them, and validates
                        each document against its schemas. Each shown
                        relation of check.lp is one check, as is
                        schema validation, and each row of a check is
                        one failure.

                        advise.lp is evaluated in the same program.
                        Each of its shown relations is one kind of
                        advice. cctool check reports advice, but
                        advice is not a failure, so it neither fails
                        the check nor refuses an edit.
usage:                  |
                        cctool check [--root DIR]
relation:               []

...
"""


import pathlib

import cc_public.check.schema
import cc_public.edit.layout
import cc_public.graph.datalog
import cc_public.graph.extract


RULES             = pathlib.Path(__file__).with_name('check.lp')
ADVICE            = pathlib.Path(__file__).with_name('advise.lp')

# The checks of check.lp, and one more that is not Datalog: each
# document conforms to the schemas that document_schema names for it.
#
NAME_PAIR         = 'document_schema'
NAME_SCHEMA       = 'schema_violation'

# One more again: each document is laid out as cctool format lays it
# out. An edit lays out every file it writes, so this is checked over
# the files of a tree, and not over the documents of an edit.
#
NAME_LAYOUT       = 'unformatted_file'

Failures          = dict[str, list[tuple[str, ...]]]

# What validation against the schemas has found, kept between checks
# in one process, for the documents that are the same objects as the
# last time they were read.
#
CACHE_SCHEMA      = {}


# -----------------------------------------------------------------------------
def check(root: pathlib.Path) -> Failures:
    """
    Return the failures of the tree under root, keyed by check, with
    the checks that pass left out.

    """

    return review(root)[0]


# -----------------------------------------------------------------------------
def review(root: pathlib.Path) -> tuple[Failures, Failures]:
    """
    Return the failures and the advice of the tree under root, each
    keyed by check, with the checks that find nothing left out.

    """

    map_document       = cc_public.graph.extract.documents(root)
    (failures, advice) = review_documents(map_document, CACHE_SCHEMA)
    list_row           = cc_public.edit.layout.violations(root, map_document)

    if list_row:
        failures[NAME_LAYOUT] = list_row

    return (failures, advice)


# -----------------------------------------------------------------------------
def check_documents(map_document: cc_public.graph.extract.Documents,
                    cache:        dict | None = None) -> Failures:
    """
    Return the failures of the documents, keyed by check, with the
    checks that pass left out. An edit is checked this way before it
    is written, with its documents in place of those it changes, and
    with one cache for both checks, so that a document the edit leaves
    as it was is not validated against its schema again.

    """

    return review_documents(map_document, cache)[0]


# -----------------------------------------------------------------------------
def review_documents(map_document: cc_public.graph.extract.Documents,
                     cache:        dict | None = None) -> tuple[Failures, Failures]:
    """
    Return the failures and the advice of the documents, each keyed by
    check, with the checks that find nothing left out. check.lp and
    advise.lp are evaluated as one program.

    """

    text_advice = ADVICE.read_text(encoding = 'utf-8')
    facts       = cc_public.graph.extract.facts_of(map_document)
    rows        = cc_public.graph.datalog.run(facts,
                                              RULES.read_text(encoding = 'utf-8') + '\n'
                                              + text_advice + '\n'
                                              + cc_public.graph.datalog.show(
                                                    NAME_PAIR,
                                                    cc_public.graph.datalog.derived()))

    rows[NAME_SCHEMA] = cc_public.check.schema.violations(map_document,
                                                          facts,
                                                          set(rows.pop(NAME_PAIR)),
                                                          cache)

    set_advice = set(cc_public.graph.datalog.declared(text_advice))
    failures   = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name not in set_advice}
    advice     = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name in set_advice}
    return (failures, advice)


# -----------------------------------------------------------------------------
def columns() -> dict[str, tuple[str, ...]]:
    """
    Return the names of the columns of each check, keyed by check.

    """

    text       = RULES.read_text(encoding = 'utf-8') + '\n' + ADVICE.read_text(encoding = 'utf-8')
    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column)
                  in cc_public.graph.datalog.declared(text).items()}

    map_column[NAME_SCHEMA] = cc_public.check.schema.COLUMNS
    map_column[NAME_LAYOUT] = cc_public.edit.layout.COLUMNS
    return map_column
