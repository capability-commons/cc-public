"""
---

id_self:                pym_cctool.check.friction
guid_self:              pym_ced3c105793c493a99230ea72c3800aa
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Friction report
brief:                  |
                        Report the signals of friction in a tree: the
                        rows of friction.lp, and the count of each
                        kind of advice that cctool check gives.
description:            |
                        Friction is the first sensing mechanism of
                        continual improvement after the checks. It
                        looks for the traces that a bent design
                        leaves, so that the scheduled reviews can find
                        tensions early, while they are cheap to
                        resolve.
usage:                  |
                        Run by cctool friction.
edge:                   []

...
"""


import pathlib

import cctool.check.check
import cctool.graph.extract
import cctool.graph.logic


RULES             = pathlib.Path(__file__).with_name('friction.lp')

# The name under which the report gives the count of each kind of
# advice that cctool check gives.
#
NAME_ADVICE       = 'advice'

Report            = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def friction(root: pathlib.Path) -> Report:
    """
    Return the signals of friction in the tree under root, keyed by
    signal, each with its rows, and the count of each kind of advice
    that cctool check gives, under NAME_ADVICE.

    """

    map_document = cctool.graph.extract.documents(root)
    (_, advice)  = cctool.check.check.review_documents(map_document,
                                                         cctool.check.check.CACHE_SCHEMA)
    rows         = cctool.graph.logic.run(cctool.graph.extract.facts_of(map_document),
                                          RULES.read_text(encoding = 'utf-8'))

    rows[NAME_ADVICE] = sorted((name, str(len(list_row)))
                               for (name, list_row) in advice.items())
    return rows


# -----------------------------------------------------------------------------
def columns() -> dict[str, tuple[str, ...]]:
    """
    Return the names of the columns of each signal, keyed by signal.

    """

    text       = RULES.read_text(encoding = 'utf-8')
    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column)
                  in cctool.graph.logic.declared(text).items()}

    map_column[NAME_ADVICE] = ('kind', 'count')
    return map_column


# -----------------------------------------------------------------------------
def wording() -> dict[str, dict[str, str]]:
    """
    Return what a row of each signal records, and what to decide about
    it, keyed by signal.

    """

    map_wording = cctool.graph.logic.worded(RULES.read_text(encoding = 'utf-8'))

    map_wording[NAME_ADVICE] = {'did':  'cctool check gives {count} rows of the advice {kind}.',
                                'fix':  'Read the advice. A kind that keeps growing may be '
                                        'a rule worth changing.'}
    return map_wording
