"""
---

id_self:                pym_cctool.check.check
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
                        is one failure. The ids that the comments of
                        python modules mention are checked as dangling
                        mentions too, by pym_cctool.check.comment.

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
    id_target:          icm_cctool_check.module
    guid_target:        icm_22b81d93a0e54bc5aff823ef45a696fa

...
"""


import pathlib

import cctool.check.citation
import cctool.check.comment
import cctool.check.layout
import cctool.check.release_record
import cctool.check.schema
import cctool.check.segment
import cctool.graph.extract
import cctool.graph.logic


RULES             = pathlib.Path(__file__).with_name('check.lp')
ADVICE            = pathlib.Path(__file__).with_name('advise.lp')

# The checks of check.lp, and one more that is not a logic program rule: each
# YAML document conforms to the schemas that document_schema names for it.
#
NAME_PAIR         = 'document_schema'
NAME_SCHEMA       = 'schema_violation'

# One more again: each YAML document is laid out as cctool format lays
# it out. This reads the text of each file, and not only its documents,
# so it is checked over the files of a tree, by check_files. An edit
# checks it too, over the files it writes as it leaves them.
#
NAME_LAYOUT       = 'unformatted_file'

# And one more: the version module holds the version of the newest
# release item, since the release step writes both. This reads a file
# beside the documents, so it too is checked by check_files.
#
NAME_VERSION      = 'version_disagreement'

# And one more: a segment item names the newest release item of each tree
# it consumes. Its rows are failures while that tree is an installed
# release, and notices while it is a checkout. This is the one check
# that an edit leaves out, as WTP chose on 2026-10-29, since its rows
# follow from which release of each consumed tree is installed, which no
# edit of this tree changes.
#
NAME_CONSUMED     = 'consumed_release_disagreement'

# And two more: prose cites a file of the tree by the part it means, not
# by line number, and the cited file holds the part it names. These read
# the cited files, so they too are checked by check_files.
#
NAME_LINE_CITE    = 'line_citation'
NAME_NAME_CITE    = 'unresolved_citation'

# The comments of a python module are not data items, so the ids they
# mention are read from the files too, by check_files, and checked as
# dangling mentions.
#
NAME_DANGLING     = 'dangling_mention'

# The wording of the checks that are not logic program rules. The checks of
# check.lp are worded there, in the item before each declaration.
#
WORDING_SCHEMA    = {'did': '{id} breaks {schema} at {path}: {message}',
                     'fix': 'Correct the field to what the schema asks. cctool set refuses '
                            'an edit that adds a failure, so it shows whether a value fits.'}
WORDING_LAYOUT    = {'did': '{file}: {message}',
                     'fix': 'Run cctool format, which lays the file out. Where the file '
                            'cannot be laid out, as when it is not YAML, is not a mapping or '
                            'holds what the layout does not keep, such as an anchor or a '
                            'tab, correct what the message names by hand first.'}
WORDING_VERSION   = {'did': '{id}, the newest release item, records the version {version}, '
                            'and the version module holds {module}.',
                     'fix': 'Let cctool release prepare write the version module and the '
                            'release item together. Do not edit the version by hand.'}

WORDING_CONSUMED  = {'did': '{id} consumes {release}, but the {place} of the tree it '
                            'consumes holds the newer release {newest}.',
                     'fix': 'Change the edge of relation_consumes of the segment item to '
                            'the newest release, or install the release that it names.'}

WORDING_LINE_CITE = {'did': '{id} cites {citation} by line number, which goes stale as the '
                            'lines of the file move.',
                     'fix': 'Cite the part that holds the line: within NAME for a function, '
                            'Class.method, constant or predicate of code; at KEY.PATH for a '
                            'field of a configuration or data file, or just after KEY.PATH for '
                            'a line that is not a field; FILE#anchor for a section of markdown. '
                            'Write REV:PATH where the lines of one commit are meant.'}
WORDING_NAME_CITE = {'did': '{id} cites {name} in {cited}, which holds no such part.',
                     'fix': 'Name the part as the cited file now holds it. If the part is '
                            'gone, correct the claim that rests on it, or cite the commit that '
                            'held it as REV:PATH.'}

# The severity of a check: a row of it is a failure, or advice.
#
SEVERITY_FAILURE  = 'failure'
SEVERITY_ADVICE   = 'advice'

Failures          = dict[str, list[tuple[str, ...]]]

# What validation against the schemas has found, kept between checks in
# one OS process, for the YAML documents that are the same objects as the
# last time they were read.
#
CACHE_SCHEMA      = {}

# The failures and advice of the last reviews, kept in one OS process and
# keyed by the YAML documents reviewed, as objects, and by the rules.
# The review before an edit is that of the tree as it was last checked,
# so it is found here. It is emptied when it holds this many. Each
# review keeps its documents, so that no other document can take the id
# of one while the review is kept.
#
CACHE_REVIEW      = {}
COUNT_REVIEW      = 8


# -----------------------------------------------------------------------------
def check(root: pathlib.Path) -> Failures:
    """
    ---

    id_self:                pyf_cctool.check.check.check
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
        id_target:          icm_cctool_check.check
        guid_target:        icm_987ceb8fcb464178a5206e8cfddf4ad2

    ...
    """

    return review(root)[0]


# -----------------------------------------------------------------------------
def review(root: pathlib.Path) -> tuple[Failures, Failures, Failures]:
    """
    ---

    id_self:                pyf_cctool.check.check.review
    guid_self:              pyf_1b0b7142ed6d4538b16ff1bb6efdfd79
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Review a tree
    brief:                  |
                            Return the failures, the advice and the
                            notices of the tree under root, each keyed by
                            check, with the checks that find nothing left
                            out.
    description:            |
                            The trees that the segment item of the tree
                            consumes are read and checked with it. A row
                            that names only their items and files is a
                            notice, and not a failure, and advice about
                            them is left out.

    edge:

      - id_relation:        relation_realizes
        guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
        id_target:          icm_cctool_check.review
        guid_target:        icm_c89919b74bcc45469035be90dc9682ec

    ...
    """

    map_own                         = cctool.graph.extract.documents(root)
    (map_consumed, failing, noticed) = cctool.check.segment.consumed(root, map_own)
    map_document                    = {**map_own, **map_consumed}
    (failures, advice)              = do_review_documents(map_document, CACHE_SCHEMA)
    notices                         = {}

    if map_consumed:
        facts               = cctool.graph.extract.facts_of(map_document)
        (failures, notices) = cctool.check.segment.attribute(failures, facts)
        (advice, _)         = cctool.check.segment.attribute(advice, facts)

    failures = merged(failures,
                      check_files(root, map_own, cctool.graph.extract.facts_of(map_document)))

    for (list_row, found) in ((failing, failures), (noticed, notices)):
        if list_row:
            found[NAME_CONSUMED] = list_row

    return (failures, advice, notices)


# -----------------------------------------------------------------------------
def check_files(root:        pathlib.Path,
                map_own:     cctool.graph.extract.Documents,
                facts:       cctool.graph.extract.Facts,
                map_text:    cctool.check.citation.Texts | None = None,
                set_changed: set[str] | None = None) -> Failures:
    """
    Return the failures of the checks that read the files of the tree at
    root, and not only its documents map_own: the citations in prose,
    the ids that python comments mention, the layout of each file, and
    the version module. facts are those of every document read with the
    tree, those of the trees it consumes too.

    An edit is checked as it leaves the tree, so a file that map_text
    holds is read from there, and not from the disk: its text, or None
    if the edit removes it. If set_changed is given, only the files it
    names, and the documents that may cite one, are checked for layout
    and citations, since the rows of every other file are the same
    before the edit and after it.

    """

    if set_changed is None:
        map_cite    = map_own
        list_layout = cctool.check.layout.violations(root, map_own)
    else:
        map_cite    = cctool.check.citation.citing(map_own, set_changed)
        list_layout = cctool.check.layout.violations_of_files(root, map_own,
                                                              set_changed, map_text)

    (list_line, list_name) = cctool.check.citation.violations(root, map_cite, map_text)
    failures               = {}

    for (name, list_row) in ((NAME_DANGLING,
                              cctool.check.comment.violations(root, map_own, facts, map_text)),
                             (NAME_LINE_CITE, list_line),
                             (NAME_NAME_CITE, list_name),
                             (NAME_LAYOUT,    list_layout),
                             (NAME_VERSION,
                              cctool.check.release_record.disagreements(root, map_own, map_text))):
        if list_row:
            failures[name] = list_row

    return failures


# -----------------------------------------------------------------------------
def merged(failures: Failures, more: Failures) -> Failures:
    """
    Return failures with the rows of more added, each row once.

    """

    found = dict(failures)

    for (name, list_row) in more.items():
        found[name] = sorted(set(found[name]) | set(list_row)) if name in found else list_row

    return found


# -----------------------------------------------------------------------------
def check_documents(map_document: cctool.graph.extract.Documents,
                    cache:        dict | None = None) -> Failures:
    """
    ---

    id_self:                pyf_cctool.check.check.check_documents
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
        id_target:          icm_cctool_check.check_documents
        guid_target:        icm_9774a75d938f498eb8cb82fb00b00039

    ...
    """

    return do_review_documents(map_document, cache)[0]


# -----------------------------------------------------------------------------
def do_review_documents(map_document: cctool.graph.extract.Documents,
                     cache:        dict | None = None) -> tuple[Failures, Failures]:
    """
    ---

    id_self:                pyf_cctool.check.check.do_review_documents
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
        id_target:          icm_cctool_check.do_review_documents
        guid_target:        icm_b2c517792fd94ff598ebf76c7079f81c

    ...
    """

    text_advice = ADVICE.read_text(encoding = 'utf-8')
    text_rules  = RULES.read_text(encoding = 'utf-8')
    key         = (text_rules,
                   text_advice,
                   cctool.graph.logic.PATH_DERIVE.read_text(encoding = 'utf-8'),
                   tuple((relative, id(document), line)
                         for (relative, (document, line)) in sorted(map_document.items())))

    if key not in CACHE_REVIEW:
        if len(CACHE_REVIEW) >= COUNT_REVIEW:
            CACHE_REVIEW.clear()
        CACHE_REVIEW[key] = (tuple(map_document.values()),
                             _review(map_document, cache, text_rules, text_advice))

    (_, (failures, advice)) = CACHE_REVIEW[key]
    return ({name: list(list_row) for (name, list_row) in failures.items()},
            {name: list(list_row) for (name, list_row) in advice.items()})


# -----------------------------------------------------------------------------
def _review(map_document: cctool.graph.extract.Documents,
            cache:        dict | None,
            text_rules:   str,
            text_advice:  str) -> tuple[Failures, Failures]:
    """
    Return the failures and the advice of the YAML documents, as
    do_review_documents does, evaluated afresh.

    """

    facts       = cctool.graph.extract.facts_of(map_document)
    rows        = cctool.graph.logic.run(facts,
                                              text_rules + '\n'
                                              + text_advice + '\n'
                                              + cctool.graph.logic.show(
                                                    NAME_PAIR,
                                                    cctool.graph.logic.derived()))

    rows[NAME_SCHEMA] = cctool.check.schema.violations(map_document,
                                                       facts,
                                                       set(rows.pop(NAME_PAIR)),
                                                       cache)

    set_advice = set(cctool.graph.logic.declared(text_advice))
    failures   = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name not in set_advice}
    advice     = {name: list_row for (name, list_row) in rows.items()
                  if list_row and name in set_advice}
    return (failures, advice)


# -----------------------------------------------------------------------------
def columns() -> dict[str, tuple[str, ...]]:
    """
    ---

    id_self:                pyf_cctool.check.check.columns
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
        id_target:          icm_cctool_check.columns
        guid_target:        icm_29a8333e7f0847f5a04103b33d61dac2

    ...
    """

    text       = RULES.read_text(encoding = 'utf-8') + '\n' + ADVICE.read_text(encoding = 'utf-8')
    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column)
                  in cctool.graph.logic.declared(text).items()}

    map_column[NAME_SCHEMA]    = cctool.check.schema.COLUMNS
    map_column[NAME_LAYOUT]    = cctool.check.layout.COLUMNS
    map_column[NAME_VERSION]   = cctool.check.release_record.COLUMNS
    map_column[NAME_CONSUMED]  = cctool.check.segment.COLUMNS
    map_column[NAME_LINE_CITE] = cctool.check.citation.COLUMNS_LINE
    map_column[NAME_NAME_CITE] = cctool.check.citation.COLUMNS_NAME
    return map_column


# -----------------------------------------------------------------------------
def severities() -> dict[str, str]:
    """
    Return the severity of each check, failure or advice, keyed by
    check: advice for each shown predicate of advise.lp, and failure for
    every other check that wording words, so that a check written in
    python has its severity as soon as it has its wording.

    """

    map_severity = {name: SEVERITY_FAILURE for name in wording()}

    map_severity.update({name: SEVERITY_ADVICE for name in
                         cctool.graph.logic.output(ADVICE.read_text(encoding = 'utf-8'))})
    return map_severity


# -----------------------------------------------------------------------------
def wording() -> dict[str, dict[str, str]]:
    """
    ---

    id_self:                pyf_cctool.check.check.wording
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
        id_target:          icm_cctool_check.wording
        guid_target:        icm_6a67c1a8b79d4e739b9662e75b4bd3aa

    ...
    """

    text        = RULES.read_text(encoding = 'utf-8') + '\n' + ADVICE.read_text(encoding = 'utf-8')
    map_wording = cctool.graph.logic.worded(text)

    map_wording[NAME_SCHEMA]    = WORDING_SCHEMA
    map_wording[NAME_LAYOUT]    = WORDING_LAYOUT
    map_wording[NAME_VERSION]   = WORDING_VERSION
    map_wording[NAME_CONSUMED]  = WORDING_CONSUMED
    map_wording[NAME_LINE_CITE] = WORDING_LINE_CITE
    map_wording[NAME_NAME_CITE] = WORDING_NAME_CITE
    return map_wording
