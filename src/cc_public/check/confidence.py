"""
---

id_self:                pym_cc_public.check.confidence
guid_self:              pym_deab1d80c47245f983f8754b7f94d615
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Confidence check
brief:                  |
                        Check that the confidence an eval carries was
                        measured about the eval as it is now.
description:            |
                        A confidence row carries the digest of what
                        its measurement depended on. A row whose
                        digest is not the eval's now is advisory,
                        since its rates describe something that has
                        changed; a row with no digest is a note, since
                        nothing is known either way. Costs nothing and
                        runs always, so that stale confidence is seen
                        without judging anything.
relation:               []

...
"""


import cc_public.check.result
import cc_public.eval.measure


ID_CHECK       = 'confidence'
TITLE          = 'Confidence describes the eval it is on'
NOUN           = 'confidence row'

KEY_ID_SELF    = 'id_self'
KEY_CONFIDENCE = 'confidence'
KEY_DIGEST     = cc_public.eval.measure.KEY_DIGEST
KEY_MODEL      = cc_public.eval.measure.KEY_MODEL
PREFIX_EVAL    = 'evl'
SEPARATOR      = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every confidence row that was measured about
    something other than the eval as it is now.

    A row whose digest differs from the eval's is advisory: its rates
    describe a criterion, an example set, a scope or a set of cases
    that has since changed, and the eval wants measuring again. A row
    with no digest was recorded before rows carried one, and is a note:
    nothing is known about whether it still applies.

    """

    list_bad  = []
    list_note = []
    count     = 0

    for (filepath, document) in sorted(context.map_document.items()):

        if not isinstance(document, dict) or str(
                document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] != PREFIX_EVAL:
            continue

        list_row = document.get(KEY_CONFIDENCE) or []

        if not list_row:
            continue

        stamp = cc_public.eval.measure.digest(document, context.map_document)
        stale = sorted({row.get(KEY_MODEL) for row in list_row
                        if isinstance(row, dict)
                        and row.get(KEY_DIGEST) not in (None, stamp)})
        blank = sorted({row.get(KEY_MODEL) for row in list_row
                        if isinstance(row, dict) and row.get(KEY_DIGEST) is None})
        count += len(list_row)

        if stale:
            list_bad.append(cc_public.check.result.Nonconformity(
                    filepath = str(filepath),
                    path     = KEY_CONFIDENCE,
                    severity = cc_public.check.result.SEVERITY_ADVISORY,
                    message  = 'Measured for {models} about a criterion, examples, '
                               'scope or cases that have since changed. Measure '
                               'again before weighing a finding by it.'.format(
                                                    models = ', '.join(stale))))

        if blank:
            list_note.append(cc_public.check.result.Note(
                    filepath = str(filepath),
                    message  = 'Confidence for {models} was recorded before rows '
                               'carried a digest, so whether it still describes '
                               'this eval is not known.'.format(
                                                    models = ', '.join(blank))))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = list_note)
