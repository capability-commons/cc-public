"""
---

id_self:                pym_cc_public.check.rights
guid_self:              pym_050b455ef33c40baad180a0ede3e9216
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  |
                        Rights check
brief:                  |
                        Reports an item whose copyright or licence
                        disagrees with the rest of its segment.
description:            |
                        A segment is one body of work under one set of
                        rights. Nothing declares those rights, so the
                        check takes them to be what the segment's
                        items agree on, and reports the item that
                        disagrees.

                        It exists because two ways were found for an
                        item to be written into a tree and given the
                        rights of another. A command writing outside
                        every root took the rights of the root, and a
                        command whose type named no home wrote a
                        consumer's item into the core carrying the
                        consumer's licence. Both are refused now, at
                        the point of writing. This is what says so
                        afterwards, whatever wrote the file and
                        whether or not it came through the tool.

                        A file under no segment is passed over, as it
                        is by the segment check. A segment whose items
                        do not agree by a majority reports nothing,
                        since there is then nothing to disagree with.
relation:               []

...
"""


import collections

import cc_public.check.result
import cc_public.check.segment


ID_CHECK = 'rights'
TITLE    = 'Items agree with their segment about rights'
NOUN     = 'item'

KEY_COPYRIGHT = 'copyright'
KEY_LICENSE   = 'license'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every item whose rights differ from those the
    rest of its segment carries.

    A segment is one body of work under one set of rights. What those
    rights are is nowhere declared, so what the segment's items agree
    on stands for them. That is weaker than a declaration and it needs
    no convention of any consumer, which is why it is done this way
    (ddr_edit_commands).

    The protective mark is not read. A mark says who may see one item
    and properly differs between items of one segment; a copyright and
    a licence say who owns the work and do not.

    """

    segments = cc_public.check.segment.map_segment(context.map_document)

    if not segments:
        return cc_public.check.result.Result(count_item         = 0,
                                             list_nonconformity = [],
                                             list_note          = [])

    held = collections.defaultdict(list)

    for (location, document) in sorted(context.map_document.items()):

        if not isinstance(document, dict):
            continue

        if KEY_COPYRIGHT not in document and KEY_LICENSE not in document:
            continue

        id_segment = cc_public.check.segment.segment_of(location.filepath,
                                                        segments)
        if id_segment is None:
            continue

        held[id_segment].append((location, (document.get(KEY_COPYRIGHT),
                                            document.get(KEY_LICENSE))))

    count    = 0
    list_bad = []

    for (id_segment, list_held) in sorted(held.items()):

        count += len(list_held)
        agreed = _agreed([rights for (_location, rights) in list_held])

        if agreed is None:
            continue

        for (location, rights) in list_held:
            if rights != agreed:
                list_bad.append(_fault(location, id_segment, rights, agreed))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _agreed(list_rights):
    """
    Return the rights the segment agrees on, or None where it does not.

    A majority is agreement. Anything less is a segment that has not
    settled what it is, and nothing there is the odd one out.

    """

    (rights, count) = collections.Counter(list_rights).most_common(1)[0]

    return rights if count * 2 > len(list_rights) else None


# -----------------------------------------------------------------------------
def _fault(location, id_segment, rights, agreed):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.Nonconformity(
        filepath = str(location.filepath),
        path     = '',
        message  = ('Carries {held}, where the rest of {segment} carries {agreed}. An '
                    'item takes the rights of the segment it is in, and one that does '
                    'not was written into a tree it does not belong to.'.format(
                            held    = _say(rights),
                            segment = id_segment,
                            agreed  = _say(agreed))),
        severity = cc_public.check.result.SEVERITY_CRITICAL)


# -----------------------------------------------------------------------------
def _say(rights):
    """
    Return one pair of rights as a phrase.

    """

    (copyright_, license_) = rights

    return '{copyright} under {license}'.format(
                            copyright = copyright_ or 'no copyright',
                            license   = license_   or 'no licence')
