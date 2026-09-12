"""
---

id_self:                pym_cc_public.check.decision
guid_self:              pym_8311b070202c4121be48fde4cd4e35ef
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Decision check
brief:                  |
                        Check that every decision still holds: its
                        subjects unchanged and its expiry not passed.
description:            |
                        This check computes the digest of each subject
                        of every decision and compares it with the
                        digest the decision stamped. A subject that
                        has changed since the decision is reported as
                        advisory, because the decision then speaks of
                        content that no longer exists. A decision
                        whose expiry has passed is reported too. A
                        decision that no longer holds admits nothing.
relation:               []

...
"""


import cc_public.check.result
import cc_public.decision


ID_CHECK = 'decision'
TITLE    = 'Decisions still hold'
NOUN     = 'decision'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every decision whose subject has changed
    since it was made, or whose expiry has passed. Both advisory: the
    decision stays on the record as what was decided then, and what it
    admitted no longer rests on it.

    """

    map_guid = cc_public.decision.index(context.map_document)
    count    = 0
    list_bad = []

    for (location, document) in sorted(context.map_document.items(),
                                       key = lambda kv: str(kv[0])):

        if not cc_public.decision.is_decision(document):
            continue

        count += 1

        for id_item in cc_public.decision.stale(document, map_guid):
            list_bad.append(cc_public.check.result.Nonconformity(
                filepath = str(location.filepath), path = '',
                severity = cc_public.check.result.SEVERITY_ADVISORY,
                message  = ('Decided over {item} as it was, and {item} has changed since, or '
                            'is gone. The decision speaks of content that no longer exists; '
                            'decide again over what is there now, or leave it as the record '
                            'of what was decided then.'.format(item = id_item))))

        if cc_public.decision.is_expired(document):
            list_bad.append(cc_public.check.result.Nonconformity(
                filepath = str(location.filepath), path = '',
                severity = cc_public.check.result.SEVERITY_ADVISORY,
                message  = ('Expired on {day}: it admits nothing now.'.format(
                                day = document.get(cc_public.decision.KEY_EXPIRY)))))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])
