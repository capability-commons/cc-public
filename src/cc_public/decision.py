"""
---

id_self:                pym_cc_public.decision
guid_self:              pym_2e9284922cd94cf69ccebc60ccc452df
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Decision
brief:                  |
                        What a decision binds: the digest of an item
                        as it was, and whether a decision still holds.
description:            |
                        A decision is an act over exact content. This
                        module computes the digest a decision stamps
                        on each subject, the whole document of the
                        item as loaded, so that any edit changes it,
                        and says whether a decision is current, its
                        subjects unchanged and its expiry not passed.
                        The foundation for the decide command, the
                        decision check and the promotion gate.
relation:               []

...
"""


import datetime
import hashlib
import json

import cc_public.item


KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_SUBJECT   = 'subject'
KEY_ID_ITEM   = 'id_item'
KEY_GUID_ITEM = 'guid_item'
KEY_DIGEST    = 'digest'
KEY_OUTCOME   = 'outcome'
KEY_EXPIRY    = 'expiry'
PREFIX        = 'dcn'
SEPARATOR     = '_'
LENGTH_DIGEST = 8            # the length the control cases and confidence rows use

OUTCOME_WAIVE  = 'waive'
OUTCOME_SELECT = 'select'
OUTCOME_ACCEPT = 'accept'
OUTCOME_LEAD   = 'lead'


# -----------------------------------------------------------------------------
def digest_of(document):
    """
    Return the digest a decision stamps on a subject: over the whole
    document as loaded, so that any edit to it, prose or edge, changes
    the digest and stales the decision.

    """

    text = json.dumps(document, sort_keys = True, default = str)

    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:LENGTH_DIGEST]


# -----------------------------------------------------------------------------
def is_decision(document):
    """
    Return whether document is a decision.

    """

    return (isinstance(document, dict)
            and str(document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] == PREFIX)


# -----------------------------------------------------------------------------
def index(map_document):
    """
    Return {guid: document} for every identity declared in the tree,
    embedded ones included, so that a subject can be found by guid.

    """

    return {guid: held.document
            for (guid, held) in cc_public.item.index(map_document).by_guid.items()}


# -----------------------------------------------------------------------------
def stale(decision, map_guid):
    """
    Return the id of every subject of the decision whose content has
    changed since the decision was made, or which cannot be found.

    """

    out = []

    for subject in decision.get(KEY_SUBJECT) or []:
        document = map_guid.get(subject.get(KEY_GUID_ITEM))
        if document is None or digest_of(document) != subject.get(KEY_DIGEST):
            out.append(subject.get(KEY_ID_ITEM))

    return out


# -----------------------------------------------------------------------------
def is_expired(decision, today = None):
    """
    Return whether the decision's expiry, where it has one, has passed.

    """

    expiry = decision.get(KEY_EXPIRY)

    if not expiry:
        return False

    today = today or datetime.datetime.now(datetime.UTC).date()

    return datetime.date.fromisoformat(str(expiry)) < today


# -----------------------------------------------------------------------------
def holds(decision, map_guid, today = None):
    """
    Return whether the decision still holds: no subject stale and not
    expired.

    """

    return not stale(decision, map_guid) and not is_expired(decision, today)
