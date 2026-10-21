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
                        each YAML document against its schemas. Each
                        shown predicate of check.lp is one check, as
                        is schema validation, and each row of a check
                        is one failure.

                        advise.lp is evaluated in the same program.
                        Each of its shown predicates is one kind of
                        advice. cctool check reports advice, but
                        advice is not a failure, so it neither fails
                        the check nor refuses an edit.
usage:                  |
                        cctool check [--root DIR]

edge:

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          icm_cc_public_check.module
    guid_target:        icm_22b81d93a0e54bc5aff823ef45a696fa

...
"""


import pathlib

import cc_public.check.schema
import cc_public.edit.layout
import cc_public.graph.logic
import cc_public.graph.extract


RULES             = pathlib.Path(__file__).with_name('check.lp')
ADVICE            = pathlib.Path(__file__).with_name('advise.lp')

# The checks of check.lp, and one more that is not a logic program rule: each
# YAML document conforms to the schemas that document_schema names for it.
#
NAME_PAIR         = 'document_schema'
NAME_SCHEMA       = 'schema_violation'

# One more again: each YAML document is laid out as cctool format lays
# it out. An edit lays out every file it writes, so this is checked over
# the files of a tree, and not over the documents of an edit.
#
NAME_LAYOUT       = 'unformatted_file'

# The wording of the two checks that are not logic program rules. The checks of
# check.lp are worded there, after their declarations.
#
WORDING_SCHEMA    = {'did': '{id} breaks {schema} at {path}: {message}',
                     'fix': 'Correct the field to what the schema asks. cctool set refuses '
                            'an edit that adds a failure, so it shows whether a value fits.'}
WORDING_LAYOUT    = {'did': '{file} is not laid out as cctool format lays it out.',
                     'fix': 'Run cctool format.'}

Failures          = dict[str, list[tuple[str, ...]]]

# What validation against the schemas has found, kept between checks in
# one process, for the YAML documents that are the same objects as the
# last time they were read.
#
CACHE_SCHEMA      = {}

# The failures and advice of the last reviews, kept in one process and
# keyed by the YAML documents reviewed, as objects, and by the rules.
# The review before an edit is that of the tree as it was last checked,
# so it is found here. It is emptied when it holds this many.
#
CACHE_REVIEW      = {}
COUNT_REVIEW      = 8


# -----------------------------------------------------------------------------
def check(root: pathlib.Path) -> Failures:
    """
    ---

    id_self:                pyf_cc_public.check.check.check
    guid_self:              pyf_c63c877eea1a48bfb953c1c7f5f94a39
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Check a tree
    brief:                  |
                            Return the failures of the tree under root,
                            keyed by check, with the checks that pass left
                            out.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.check
        guid_target:        icm_987ceb8fcb464178a5206e8cfddf4ad2

    ...
    """

    return review(root)[0]


# -----------------------------------------------------------------------------
def review(root: pathlib.Path) -> tuple[Failures, Failures]:
    """
    ---

    id_self:                pyf_cc_public.check.check.review
    guid_self:              pyf_1b0b7142ed6d4538b16ff1bb6efdfd79
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Review a tree
    brief:                  |
                            Return the failures and the advice of the tree
                            under root, each keyed by check, with the
                            checks that find nothing left out.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.review
        guid_target:        icm_c89919b74bcc45469035be90dc9682ec

    ...
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
    ---

    id_self:                pyf_cc_public.check.check.check_documents
    guid_self:              pyf_eaf505a870ba42269c57466a0a70e459
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Check YAML documents
    brief:                  |
                            Return the failures of the documents, keyed by
                            check, with the checks that pass left out. An
                            edit is checked this way before it is written,
                            with its documents in place of those it
                            changes, and with one cache for both checks,
                            so that a document the edit leaves as it was
                            is not validated against its schema again.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.check_documents
        guid_target:        icm_9774a75d938f498eb8cb82fb00b00039

    ...
    """

    return review_documents(map_document, cache)[0]


# -----------------------------------------------------------------------------
def review_documents(map_document: cc_public.graph.extract.Documents,
                     cache:        dict | None = None) -> tuple[Failures, Failures]:
    """
    ---

    id_self:                pyf_cc_public.check.check.review_documents
    guid_self:              pyf_eb7ba3af22ab416491c04825db3f855a
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Review YAML documents
    brief:                  |
                            Return the failures and the advice of the YAML
                            documents, each keyed by check, with the
                            checks that find nothing left out. check.lp
                            and advise.lp are evaluated as one program.
                            Documents that are the same objects as at an
                            earlier review, under the same rules, are not
                            reviewed again.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.review_documents
        guid_target:        icm_b2c517792fd94ff598ebf76c7079f81c

    ...
    """

    text_advice = ADVICE.read_text(encoding = 'utf-8')
    text_rules  = RULES.read_text(encoding = 'utf-8')
    key         = (text_rules,
                   text_advice,
                   cc_public.graph.logic.PATH_DERIVE.read_text(encoding = 'utf-8'),
                   tuple((relative, id(document), line)
                         for (relative, (document, line)) in sorted(map_document.items())))

    if key not in CACHE_REVIEW:
        if len(CACHE_REVIEW) >= COUNT_REVIEW:
            CACHE_REVIEW.clear()
        CACHE_REVIEW[key] = _review(map_document, cache, text_rules, text_advice)

    (failures, advice) = CACHE_REVIEW[key]
    return ({name: list(list_row) for (name, list_row) in failures.items()},
            {name: list(list_row) for (name, list_row) in advice.items()})


# -----------------------------------------------------------------------------
def _review(map_document: cc_public.graph.extract.Documents,
            cache:        dict | None,
            text_rules:   str,
            text_advice:  str) -> tuple[Failures, Failures]:
    """
    Return the failures and the advice of the YAML documents, as
    review_documents does, evaluated afresh.

    """

    facts       = cc_public.graph.extract.facts_of(map_document)
    rows        = cc_public.graph.logic.run(facts,
                                              text_rules + '\n'
                                              + text_advice + '\n'
                                              + cc_public.graph.logic.show(
                                                    NAME_PAIR,
                                                    cc_public.graph.logic.derived()))

    rows[NAME_SCHEMA] = cc_public.check.schema.violations(map_document,
                                                          facts,
                                                          set(rows.pop(NAME_PAIR)),
                                                          cache)

    set_advice = set(cc_public.graph.logic.declared(text_advice))
    failures   = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name not in set_advice}
    advice     = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name in set_advice}
    return (failures, advice)


# -----------------------------------------------------------------------------
def columns() -> dict[str, tuple[str, ...]]:
    """
    ---

    id_self:                pyf_cc_public.check.check.columns
    guid_self:              pyf_3844de097e36427c9a993343bd9325e2
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Columns of the checks
    brief:                  |
                            Return the names of the columns of each check,
                            keyed by check.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.columns
        guid_target:        icm_29a8333e7f0847f5a04103b33d61dac2

    ...
    """

    text       = RULES.read_text(encoding = 'utf-8') + '\n' + ADVICE.read_text(encoding = 'utf-8')
    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column)
                  in cc_public.graph.logic.declared(text).items()}

    map_column[NAME_SCHEMA] = cc_public.check.schema.COLUMNS
    map_column[NAME_LAYOUT] = cc_public.edit.layout.COLUMNS
    return map_column


# -----------------------------------------------------------------------------
def wording() -> dict[str, dict[str, str]]:
    """
    ---

    id_self:                pyf_cc_public.check.check.wording
    guid_self:              pyf_c9909ed20c204889b5a1402537073e72
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Wording of the checks
    brief:                  |
                            Return what a row of each check records, and
                            what to do about it, keyed by check.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cc_public_check.wording
        guid_target:        icm_6a67c1a8b79d4e739b9662e75b4bd3aa

    ...
    """

    text        = RULES.read_text(encoding = 'utf-8') + '\n' + ADVICE.read_text(encoding = 'utf-8')
    map_wording = cc_public.graph.logic.worded(text)

    map_wording[NAME_SCHEMA] = WORDING_SCHEMA
    map_wording[NAME_LAYOUT] = WORDING_LAYOUT
    return map_wording
