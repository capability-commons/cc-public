"""
---

id_self:                pym_cc_public.check.trace
guid_self:              pym_0a9202d4cae34168a6520c00d544ebcb
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Trace check
brief:                  |
                        Check what every requirement lacks of what
                        derives from it, implements it and verifies
                        it.
description:            |
                        The rules and their severities are the trace
                        projection's, which the trace command reads
                        too. A proposed requirement may be incomplete
                        while it is written and its gaps are advisory;
                        an accepted one has claimed to be complete and
                        a gap in what it claims is critical, except
                        where an open world leaves room for the
                        missing thing to exist elsewhere. Beside the
                        projection this reads what a coverage analysis
                        says. A requirement whose declared criticality
                        requires that its coverage be analysed, with
                        no current analysis naming it, is a gap; a
                        current reading whose verdict is unmet is
                        reported here rather than as a gap, and is
                        advisory whatever the requirement's status
                        (ddr_coverage_analysis).

relation:

  - id_relation:        r_satisfies
    guid_relation:      r_0a4f8ded2f2c4b138bcdfbed9e83ecd4
    id_target:          obj_verification_per_requirement
    guid_target:        obj_daff88a03d004002864bc8dc94d271b2

  - id_relation:        r_satisfies
    guid_relation:      r_0a4f8ded2f2c4b138bcdfbed9e83ecd4
    id_target:          obj_expected_result_stated
    guid_target:        obj_a055d8642b5a4688820e3f05c98d333a

  - id_relation:        r_satisfies
    guid_relation:      r_0a4f8ded2f2c4b138bcdfbed9e83ecd4
    id_target:          obj_verdict_per_requirement
    guid_target:        obj_26b7e105da03488db6031facc7422c0e

...
"""


import hashlib
import json

import cc_public.check.result
import cc_public.item
import cc_public.load.python
import cc_public.testing
import cc_public.trace


LENGTH_DIGEST = 8


ID_CHECK  = 'trace'
TITLE     = 'Requirements trace to what derives, implements and verifies them'
NOUN      = 'requirement'

PREFIX_ANALYSIS = 'cva'
SUFFIX_PYTHON   = '.py'

# What joins a definition to the surroundings it was read with, so the
# digest covers both and neither can be mistaken for the other.
#
SEPARATOR_CONTEXT = '\n# --- module ---\n'

KEY_ID_SELF     = 'id_self'
KEY_ANALYSIS    = 'analysis'
KEY_CRITERIA    = 'success_criteria'
KEY_GUID_REQ    = 'guid_requirement'
KEY_ID_VERIFIER = 'id_verifier'
KEY_DIGEST      = 'digest'
KEY_VERDICT     = 'verdict'
VERDICT_UNMET   = 'unmet'
KEY_JUDGE       = 'judge'
KEY_FEEDBACK    = 'feedback'
KEY_CONFIDENCE  = 'confidence'
KEY_FALSE_POSITIVE = 'false_positive'
KEY_FALSE_NEGATIVE = 'false_negative'
KEY_RELATION    = 'relation'
KEY_ID_REL      = 'id_relation'
KEY_GUID_TARGET = 'guid_target'
REL_IMPLEMENTED = 'r_is_implemented_by'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming what every requirement lacks, as the trace
    projection finds it.

    The rules and their severities live in the projection, which the
    trace command reads too, so that what the check reports and what
    the command shows cannot differ. A proposed requirement's gaps are
    advisory; an accepted one's are critical, except where an open
    world leaves room for the missing thing to exist elsewhere.

    """

    map_location = {d.get(cc_public.trace.KEY_GUID_SELF): location
                    for (location, d) in context.map_document.items()
                    if isinstance(d, dict)}
    list_bad     = []
    list_record  = cc_public.trace.projection(context.map_document,
                                              context.is_closed_world)
    set_analysed = analysed(context.map_document)

    for record in list_record:
        for gap in list(record.gap) + missing_analysis(record, set_analysed):
            list_bad.append(cc_public.check.result.Nonconformity(
                    filepath = str(map_location.get(record.guid_self, record.id_self)),
                    path     = gap.path,
                    severity = gap.severity,
                    message  = gap.message))

    list_bad.extend(_unmet(context.map_document, map_location))

    return cc_public.check.result.Result(count_item         = len(list_record),
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _unmet(map_document, map_location):
    """
    Return a finding for each current analysis whose verdict is unmet.

    Reported here and not among the projection's gaps, because this is
    not something a requirement lacks. It is what a judge answered, and
    it is advisory whatever the requirement's status or criticality,
    since a judge is not a check. What it rests on is written beside
    it: the judge, and the rates it was measured at.

    """

    map_item = cc_public.item.index(map_document).by_guid

    return [cc_public.check.result.Nonconformity(
                    filepath = str(map_location.get(row.get(KEY_GUID_REQ), '')),
                    path     = KEY_ANALYSIS,
                    severity = cc_public.trace.SEVERITY_ADVISORY,
                    message  = _said(document, row))
            for document in map_document.values() if _is_analysis(document)
            for row in (document.get(KEY_ANALYSIS) or {}).values()
            if isinstance(row, dict) and row.get(KEY_VERDICT) == VERDICT_UNMET
            and _is_current(row, map_document, map_item)]


# -----------------------------------------------------------------------------
def _said(document, row):
    """
    Return what to report of one unmet reading, with what it rests on.

    """

    return ('{judge} read {verifier} against these criteria and found the test could '
            'pass while something they require is untrue. {feedback} It was measured '
            'on this eval at {rate}.'.format(
                    judge    = document.get(KEY_JUDGE),
                    verifier = row.get(KEY_ID_VERIFIER),
                    feedback = (row.get(KEY_FEEDBACK) or '').strip(),
                    rate     = _rate(document.get(KEY_CONFIDENCE))))


# -----------------------------------------------------------------------------
def _rate(confidence):
    """
    Return the rates a judge was measured at, in words, or that it was
    never measured.

    """

    if not isinstance(confidence, dict):
        return 'no measured rate at all, so nothing says how often it is wrong'

    return ('a false positive rate of {fp} and a false negative rate of {fn}'.format(
                    fp = confidence.get(KEY_FALSE_POSITIVE),
                    fn = confidence.get(KEY_FALSE_NEGATIVE)))


# -----------------------------------------------------------------------------
def missing_analysis(record, set_analysed):
    """
    Return the gap for a requirement whose criticality requires a
    coverage analysis and which no current analysis names.

    Made here and not in the projection, because whether an analysis
    is current is decided by reading source and the projection reads
    documents. The projection then answers one way for every caller
    (ddr_coverage_analysis).

    """

    if not record.demands_analysis or record.guid_self in set_analysed:
        return []

    return [cc_public.trace.Gap(
                cc_public.trace.KEY_VERIFICATION,
                cc_public.trace.SEVERITY_CRITICAL
                if record.status == cc_public.trace.STATUS_ACCEPTED
                else cc_public.trace.SEVERITY_ADVISORY,
                'Its criticality requires that the coverage of its criteria be '
                'analysed and recorded, and no current analysis names it. That a test '
                'verifies a requirement does not say the test would fail if what the '
                'requirement requires were untrue, and only reading the two together '
                'says it.')]


# -----------------------------------------------------------------------------
def digest_of(document, text, around = None):
    """
    Return the digest a coverage analysis stamps on what it read: the
    success criteria of the requirement, the source of the verifier it
    was read against, and the module around that source.

    Narrow on purpose. A reading stops standing when what was read
    changes and not when something else the requirement depends on
    moves, since an analysis going stale for an unrelated reason
    teaches a reader to renew it without reading it.

    """

    held = json.dumps([str(document.get(KEY_CRITERIA) or ''), text, around],
                      sort_keys = True)

    return hashlib.sha256(held.encode('utf-8')).hexdigest()[:LENGTH_DIGEST]


# -----------------------------------------------------------------------------
def analysed(map_document):
    """
    Return the guids of the requirements a current coverage analysis
    names.

    Current means the digest the row carries is the digest of what it
    says it read, now. A row naming a verifier this tree does not hold
    or cannot read is not current, since nothing shows what was read.

    """

    map_item = cc_public.item.index(map_document).by_guid
    out      = set()

    for document in map_document.values():

        if not _is_analysis(document):
            continue

        for row in (document.get(KEY_ANALYSIS) or {}).values():
            if isinstance(row, dict) and _is_current(row, map_document, map_item):
                out.add(row.get(KEY_GUID_REQ))

    return out


# -----------------------------------------------------------------------------
def _is_analysis(document):
    """
    Return whether document is a coverage analysis.

    """

    return isinstance(document, dict) \
       and cc_public.item.prefix_of(document.get(KEY_ID_SELF)) == PREFIX_ANALYSIS


# -----------------------------------------------------------------------------
def _is_current(row, map_document, map_item):
    """
    Return whether one row still describes what it says it read.

    """

    held           = map_item.get(row.get(KEY_GUID_REQ))
    (text, around) = cc_public.testing.source_of(map_document,
                                                 row.get(KEY_ID_VERIFIER))

    if held is None or text is None:
        return False

    return digest_of(held.document, text, around) == row.get(KEY_DIGEST)
