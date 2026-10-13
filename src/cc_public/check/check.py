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
                        tree, by evaluating check.dl over facts
                        extracted from it.
description:            |
                        This module extracts the facts of the tree,
                        evaluates check.dl over them, and validates
                        each document against its schemas. Each
                        output relation of check.dl is one check, as
                        is schema validation, and each row of a check
                        is one failure.
usage:                  |
                        cctool check [--root DIR]

                        The souffle executable is taken from the
                        SOUFFLE environment variable, or from the
                        PATH.
relation:               []

...
"""


import pathlib

import cc_public.check.schema
import cc_public.graph.datalog
import cc_public.graph.extract


RULES             = pathlib.Path(__file__).with_name('check.dl')

# The checks of check.dl, and one more that is not Datalog: each
# document conforms to the schemas that document_schema names for it.
#
NAME_PAIR         = 'document_schema'
NAME_SCHEMA       = 'schema_violation'

Failures          = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def check(root: pathlib.Path) -> Failures:
    """
    Return the failures of the tree under root, keyed by check, with
    the checks that pass left out.

    """

    return check_documents(cc_public.graph.extract.documents(root))


# -----------------------------------------------------------------------------
def check_documents(map_document: cc_public.graph.extract.Documents) -> Failures:
    """
    Return the failures of the documents, keyed by check, with the
    checks that pass left out. An edit is checked this way before it
    is written, with its documents in place of those it changes.

    """

    facts = cc_public.graph.extract.facts_of(map_document)
    rows  = cc_public.graph.datalog.run(facts,
                                        RULES.read_text(encoding = 'utf-8')
                                        + '\n.output {name}\n'.format(name = NAME_PAIR))

    rows[NAME_SCHEMA] = cc_public.check.schema.violations(map_document,
                                                          facts,
                                                          set(rows.pop(NAME_PAIR)))

    return {name: list_row for (name, list_row) in rows.items() if list_row}


# -----------------------------------------------------------------------------
def columns() -> dict[str, tuple[str, ...]]:
    """
    Return the names of the columns of each check, keyed by check.

    """

    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column)
                  in cc_public.graph.datalog.declared(RULES.read_text(encoding = 'utf-8')).items()}

    map_column[NAME_SCHEMA] = cc_public.check.schema.COLUMNS
    return map_column
