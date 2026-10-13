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
                        This module extracts the facts of the tree and
                        evaluates check.dl over them. Each output
                        relation of check.dl is one check, and each
                        row of it is one failure.
usage:                  |
                        cctool check [--root DIR]

                        The souffle executable is taken from the
                        SOUFFLE environment variable, or from the
                        PATH.
relation:               []

...
"""


import pathlib

import cc_public.graph.datalog
import cc_public.graph.extract


RULES             = pathlib.Path(__file__).with_name('check.dl')

Failures          = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def check(root: pathlib.Path) -> Failures:
    """
    Return the failures of the tree under root, keyed by check, with
    the checks that pass left out.

    """

    rows = cc_public.graph.datalog.run(cc_public.graph.extract.extract(root),
                                       RULES.read_text(encoding = 'utf-8'))

    return {name: list_row for (name, list_row) in rows.items() if list_row}
