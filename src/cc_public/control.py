"""
---

id_self:                pym_cc_public.control
guid_self:              pym_d3c30505c19c48708b12bc12f946f862
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Control cases
brief:                  |
                        Find the cases with known verdicts that
                        measure an eval, and match a subject against
                        them.
description:            |
                        A control set names the eval it measures. Its
                        cases each hold a subject as the judge would
                        be shown it and the verdict a person holds it
                        to. A subject is matched by its words, so that
                        a change to where its lines break is not a
                        change to what was judged.
relation:               []

...
"""


import hashlib


KEY_CASE      = 'case'
KEY_SUBJECT   = 'subject'
KEY_VERDICT   = 'verdict'
KEY_ORIGIN    = 'origin'
KEY_NOTE      = 'note'
KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_GUID_TGT  = 'guid_target'

REL_MEASURES  = 'r_measures'

ORIGIN_ALL    = ('written', 'mutated', 'suppressed', 'confirmed')

LENGTH_KEY    = 8
LETTER_KEY    = 'c'


# -----------------------------------------------------------------------------
def normalise(text):
    """
    Return text with its whitespace collapsed, which is what is compared.

    """

    return ' '.join(text.split())


# -----------------------------------------------------------------------------
def key_of(text):
    """
    Return the short content key of a subject: a letter, then a prefix
    of the digest of its normalised text. The local name a case is held
    under, and the last segment of its readable id, which is why it must
    begin with a letter.

    """

    digest = hashlib.sha256(normalise(text).encode('utf-8')).hexdigest()

    return LETTER_KEY + digest[:LENGTH_KEY]


# -----------------------------------------------------------------------------
def iter_set(map_document, guid_eval):
    """
    Yield (filepath, document) for every control set measuring the eval.

    """

    for (filepath, document) in sorted(map_document.items()):

        if not isinstance(document, dict) or KEY_CASE not in document:
            continue

        for edge in document.get(KEY_RELATION) or []:
            if (isinstance(edge, dict)
                    and edge.get(KEY_ID_REL) == REL_MEASURES
                    and edge.get(KEY_GUID_TGT) == guid_eval):
                yield (filepath, document)
                break


# -----------------------------------------------------------------------------
def iter_case(map_document, guid_eval):
    """
    Yield (id_set, key, case) for every case measuring the eval.

    """

    for (_, document) in iter_set(map_document, guid_eval):
        for (key, case) in (document.get(KEY_CASE) or {}).items():
            if isinstance(case, dict):
                yield (document.get(KEY_ID_SELF), key, case)


# -----------------------------------------------------------------------------
def map_case(map_document, guid_eval):
    """
    Return {normalised subject: case} for every case measuring the eval.

    """

    return {normalise(case.get(KEY_SUBJECT, '')): case
            for (_, _, case) in iter_case(map_document, guid_eval)}
