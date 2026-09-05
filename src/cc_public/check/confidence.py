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


import hashlib
import json

import cc_public.check.result
import cc_public.control


ID_CHECK       = 'confidence'
TITLE          = 'Confidence describes the eval it is on'
NOUN           = 'confidence row'

KEY_ID_SELF    = 'id_self'
KEY_CONFIDENCE = 'confidence'
PREFIX_EVAL    = 'evl'
SEPARATOR      = '_'

KEY_DIGEST    = 'digest'
KEY_MODEL     = 'model'

# The eval's fields that shape a judgement. A change to any of them is
# a change to what the confidence was measured about.
#
FIELD_JUDGED  = ('criterion', 'example', 'scope')

LENGTH_DIGEST = cc_public.control.LENGTH_KEY


# -----------------------------------------------------------------------------
def digest(document_eval, map_document):
    """
    Return a short digest of everything a measurement of this eval
    depends on: the fields that shape a judgement, and every control
    case measuring it as (subject, verdict, origin).

    A confidence row carries the digest at the time it was measured, and
    a row whose digest is not the eval's now was measured about
    something else.

    """

    cases = sorted(
        (cc_public.control.normalise(case.get(cc_public.control.KEY_SUBJECT, '')),
         case.get(cc_public.control.KEY_VERDICT),
         case.get(cc_public.control.KEY_ORIGIN))
        for (_, _, case) in cc_public.control.iter_case(
                    map_document, document_eval[cc_public.control.KEY_GUID_SELF]))

    content = {field: _plain(document_eval.get(field)) for field in FIELD_JUDGED}
    content['case'] = cases
    text = json.dumps(content, sort_keys = True, ensure_ascii = True,
                      separators = (',', ':'))

    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:LENGTH_DIGEST]


# -----------------------------------------------------------------------------
def is_current(row, document_eval, map_document):
    """
    Return whether a confidence row describes the eval as it is now.

    """

    return row.get(KEY_DIGEST) == digest(document_eval, map_document)


# -----------------------------------------------------------------------------
def _plain(node):
    """
    Return node as plain python with its prose whitespace collapsed, so
    that a refilled paragraph is the same content.

    """

    if isinstance(node, dict):
        return {str(k): _plain(v) for (k, v) in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    if isinstance(node, str):
        return cc_public.control.normalise(node)
    return node




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

        stamp = digest(document, context.map_document)
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
