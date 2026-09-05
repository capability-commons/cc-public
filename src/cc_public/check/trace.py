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
                        Check that every requirement traces to what it
                        derives from.
description:            |
                        A requirement with no r_is_derived_from edge
                        cannot show it is necessary, which is the
                        first characteristic the INCOSE guide asks of
                        it. The finding is advisory: a requirement may
                        be written before its need is, but not left
                        so.
relation:               []

...
"""


import cc_public.check.result
import cc_public.trace


ID_CHECK  = 'trace'
TITLE     = 'Requirements trace to what derives, implements and verifies them'
NOUN      = 'requirement'


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

    for record in list_record:
        for gap in record.gap:
            list_bad.append(cc_public.check.result.Nonconformity(
                    filepath = str(map_location.get(record.guid_self, record.id_self)),
                    path     = gap.path,
                    severity = gap.severity,
                    message  = gap.message))

    return cc_public.check.result.Result(count_item         = len(list_record),
                                         list_nonconformity = list_bad,
                                         list_note          = [])
