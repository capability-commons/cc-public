"""
---

id_self:                pym_cc_public.edit.accept
guid_self:              pym_5613885b858f48d9b2cab64bcd46dce3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Accept
brief:                  |
                        Set a requirement to accepted where its
                        assurance is complete, and refuse otherwise.
description:            |
                        Judges the requirement as it would be once
                        accepted, in a closed world, before anything
                        is written: the trace projection must show no
                        gap and the evidence check must find nothing.
                        The only path to accepted, so that the status
                        never names a requirement the checks would
                        refuse.
relation:               []

...
"""


import cc_public.check.evidence
import cc_public.edit.field
import cc_public.edit.tree
import cc_public.trace


KEY_STATUS      = 'status'
STATUS_ACCEPTED = cc_public.trace.STATUS_ACCEPTED


# -----------------------------------------------------------------------------
def accept(tree, name):
    """
    Set the requirement called name to accepted, where its assurance is
    complete, and return its Item. Refuse otherwise, saying what it
    lacks.

    Complete means: as if accepted, in a closed world, the trace
    projection shows no gap and the evidence check finds nothing. The
    status is set only after both say so, so that accepted never names
    a requirement the checks would refuse.

    """

    item     = tree.resolve(name)
    document = tree.context.map_document[item.location]

    if not cc_public.trace.is_requirement(document):
        raise cc_public.edit.tree.ErrorItem(
                '{name} is not a requirement, and only a requirement is '
                'accepted.'.format(name = item.id_self))

    if document.get(KEY_STATUS) == STATUS_ACCEPTED:
        raise cc_public.edit.tree.ErrorItem(
                '{name} is accepted already.'.format(name = item.id_self))

    # Judged as it would be once accepted, before anything is written.
    #
    map_document = dict(tree.context.map_document)
    map_document[item.location] = {**document, KEY_STATUS: STATUS_ACCEPTED}
    context      = tree.context._replace(map_document    = map_document,
                                         is_closed_world = True)

    list_lack = [gap.message
                 for record in cc_public.trace.projection(map_document, True)
                 if record.guid_self == item.guid_self
                 for gap in record.gap]
    list_lack.extend(
        found.message
        for found in cc_public.check.evidence.check(context).list_nonconformity
        if found.filepath == str(item.location))

    if list_lack:
        raise cc_public.edit.tree.ErrorItem(
                '{name} cannot be accepted: {lack}'.format(
                        name = item.id_self, lack = ' '.join(list_lack)))

    cc_public.edit.field.set_field(tree, item.id_self, KEY_STATUS,
                                   value = STATUS_ACCEPTED)

    return item
