"""
---

id_self:                pym_cc_public.check.result
guid_self:              pym_268d7956e68d4669a7737fdc7335b8b3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Check result shapes
brief:                  |
                        The shapes a check is given and returns.
description:            |
                        Context, Nonconformity, Note and Result,
                        together with the two severity values and what
                        they mean. A module of its own, depended on by
                        the driver and by each check.

...
"""


import typing


# Severity says what FOLLOWS from a finding, and nothing else. Not how
# certain the finding is, not whether it was reached deterministically
# or by judgement, and not how it was arrived at -- a consumer wanting
# any of that reads the id_check the finding was reported under.
#
# The same two values carry the same two meanings for an eval, where
# they say what follows from a verdict of UNMET.

# Must be fixed. The system does not work correctly until it is.
#
SEVERITY_CRITICAL = 'critical'

# Must be known about, but need not be acted on.
#
# Note that this is a statement about consequence rather than about
# certainty or scope. A reference that does not resolve is advisory
# because the target may lie behind a sharing boundary; a reference
# whose readable id has gone stale is advisory for an unrelated reason,
# being declared harmless by sch_relation. Different causes, one
# consequence, and it is the consequence that the value names.
#
SEVERITY_ADVISORY = 'advisory'

SEVERITY_ALL      = (SEVERITY_CRITICAL, SEVERITY_ADVISORY)



# -----------------------------------------------------------------------------
class Context(typing.NamedTuple):
    """
    Everything a check needs, gathered once and shared by all of them.

    Files are walked and loaded a single time. A check that needs the
    content of a file reads it from map_document rather than loading it
    again, and a file that failed to load is absent from map_document
    and present in list_failure_load.

    is_closed_world carries an assertion made by the caller rather than
    anything read from the data, and changes what some findings mean.

    """

    list_filepath:     list
    map_document:      dict
    list_failure_load: list

    # Whether the caller asserts that the paths given hold everything
    # a reference could resolve to. Where they do, a reference that
    # does not resolve is a fault rather than a boundary.
    #
    is_closed_world:   bool = False

    # What the caller asked of the evals, and what should run them.
    # Loosely typed on purpose: the eval package depends on the checks,
    # so naming its types here would close a cycle. None for either
    # means the caller did not ask for evals at all.
    #
    selector_eval:     typing.Any = None
    runner_eval:       typing.Any = None

    # Over how many judgements an adverse verdict is confirmed. One
    # means the screen alone is believed.
    #
    count_confirm:     int = 1


# -----------------------------------------------------------------------------
class Nonconformity(typing.NamedTuple):
    """
    One way in which the data does not conform.

    path locates the fault within the document, and is empty where the
    fault is the document as a whole.

    severity separates what must be fixed from what must merely be
    known -- see SEVERITY_CRITICAL and SEVERITY_ADVISORY above.

    """

    filepath: str
    path:     str
    message:  str
    severity: str = SEVERITY_CRITICAL


# -----------------------------------------------------------------------------
class Note(typing.NamedTuple):
    """
    Something a check wants reported that is not a nonconformity.

    Used to make coverage visible -- a check that silently examined
    nothing must not be mistaken for a check that passed.

    """

    filepath: str
    message:  str


# -----------------------------------------------------------------------------
class Result(typing.NamedTuple):
    """
    What one check returns.

    count_item is whatever that check counts -- files, declarations,
    documents validated -- and is reported alongside its name.

    detail carries anything true of the RUN rather than of any one
    finding, and is merged into the check's entry in the report. What
    model reached a verdict is the case it was added for: a judged
    finding means little without knowing what judged it, and repeating
    that on every finding would say one thing many times.

    """

    count_item:         int
    list_nonconformity: list
    list_note:          list
    detail:             dict = None
