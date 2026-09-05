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


ID_CHECK         = 'trace'
TITLE            = 'Requirements trace to what they derive from and what verifies them'
NOUN             = 'requirement'

KEY_ID_SELF      = 'id_self'
KEY_GUID_SELF    = 'guid_self'
KEY_RELATION     = 'relation'
KEY_ID_REL       = 'id_relation'
KEY_GUID_TGT     = 'guid_target'
KEY_VERIFICATION = 'verification'
PREFIX_REQ       = 'req'
REL_DERIVED      = 'r_is_derived_from'
REL_VERIFIES     = 'r_verifies'
VERIFICATION_TEST = 'test'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every requirement with no derivation edge,
    and every requirement verified by test that no test names.

    Both are advisory. A requirement may be written before its need is,
    and before its test is, but not left so.

    """

    list_bad = []
    count    = 0
    verified = _verified(context.map_document)

    for (filepath, document) in sorted(context.map_document.items()):

        if not isinstance(document, dict) or \
                str(document.get(KEY_ID_SELF, '')).split('_', 1)[0] != PREFIX_REQ:
            continue

        count += 1

        if not any(isinstance(e, dict) and e.get(KEY_ID_REL) == REL_DERIVED
                   for e in document.get(KEY_RELATION) or []):
            list_bad.append(_advisory(filepath, KEY_RELATION,
                    'Derives from nothing. A requirement traces to a need, a '
                    'source or a higher level requirement by an '
                    'r_is_derived_from edge, or it cannot show it is necessary.'))

        if document.get(KEY_VERIFICATION) == VERIFICATION_TEST \
                and document.get(KEY_GUID_SELF) not in verified:
            list_bad.append(_advisory(filepath, KEY_VERIFICATION,
                    'Verified by test, and no test names it. A test module '
                    'says what it verifies by an r_verifies edge, or the '
                    'requirement is verified by nothing.'))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _verified(map_document):
    """
    Return the guids every r_verifies edge in the tree points at.

    """

    return {edge.get(KEY_GUID_TGT)
            for document in map_document.values() if isinstance(document, dict)
            for edge in document.get(KEY_RELATION) or []
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_VERIFIES}


# -----------------------------------------------------------------------------
def _advisory(filepath, path, message):
    """
    Return one advisory nonconformity.

    """

    return cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_ADVISORY,
                message  = message)
