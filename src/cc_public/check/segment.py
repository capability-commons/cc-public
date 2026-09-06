"""
---

id_self:                pym_cc_public.check.segment
guid_self:              pym_9e6451efbd0040629ca2d539bf215321
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Segment check
brief:                  |
                        Every reference runs within its segment or
                        into one that segment consumes.
description:            |
                        A segment is a repository declaring itself
                        with a segment item, whose directory is the
                        one it governs. The check finds the segment of
                        every file and of every guid declared, and
                        refuses a reference that leaves its segment
                        for one the segment does not consume, directly
                        or through those it consumes in turn. A file
                        under no segment is passed over, so a tree
                        that declares none is unaffected and a tree
                        may adopt them one repository at a time.
relation:               []

...
"""


import pathlib

import cc_public.check.identity
import cc_public.check.reference
import cc_public.check.result


ID_CHECK      = 'segment'
TITLE         = 'References run within a segment or into one it consumes'
NOUN          = 'reference'
PREFIX        = 'seg'
DIR_SEGMENT   = 'segment'
REL_CONSUMES  = 'r_consumes'
KEY_ID_SELF   = 'id_self'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_ID_TARGET = 'id_target'
SEPARATOR     = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every reference that leaves its segment for
    one the segment does not consume.

    A segment is a repository declaring itself with a segment item, and
    the direction of dependence is one way: a segment may name what is
    its own, and what belongs to a segment it consumes, directly or
    through those; nothing may name what belongs to a segment below or
    beside it. That is what keeps a core repository free of its
    consumers, and a consumer's own schemas and registers out of the
    core.

    A file under no segment is passed over, so a tree that declares
    none is unaffected and a tree may adopt them one repository at a
    time.

    """

    map_segment = _map_segment(context.map_document)

    if not map_segment:
        return cc_public.check.result.Result(count_item         = 0,
                                             list_nonconformity = [],
                                             list_note          = [])

    reach   = _reach(map_segment)
    map_own = {guid: _segment_of(filepath, map_segment)
               for (filepath, guid) in _iter_declaration(context.map_document)}

    count    = 0
    list_bad = []

    for (location, document) in sorted(context.map_document.items()):

        if not isinstance(document, dict):
            continue

        id_segment = _segment_of(location.filepath, map_segment)

        if id_segment is None:
            continue

        for (path, _key, guid, _id) in cc_public.check.reference.iter_reference(document):

            id_target = map_own.get(guid)

            if id_target is None or id_target == id_segment:
                continue                          # unresolved is the reference check's to say

            count += 1

            if id_target not in reach[id_segment]:
                list_bad.append(_fault(location, path, id_segment, id_target))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _map_segment(map_document):
    """
    Return {id_segment: (root, consumed)} for each segment declared: the
    directory it governs, which is the parent of the directory its item
    sits in, and the segments it names by r_consumes.

    """

    out = {}

    for (location, document) in map_document.items():

        if not isinstance(document, dict):
            continue

        id_self = str(document.get(KEY_ID_SELF, ''))

        if id_self.split(SEPARATOR, 1)[0] != PREFIX:
            continue

        consumed = tuple(edge[KEY_ID_TARGET]
                         for edge in document.get(KEY_RELATION) or []
                         if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_CONSUMES)
        out[id_self] = (pathlib.Path(location.filepath).parent.parent, consumed)

    return out


# -----------------------------------------------------------------------------
def _reach(map_segment):
    """
    Return {id_segment: the segments it may name}: itself and, through
    r_consumes, everything those consume in turn. A cycle is closed
    rather than followed, since the relation check refuses one.

    """

    reach = {}

    for id_segment in map_segment:
        seen  = {id_segment}
        queue = list(map_segment[id_segment][1])
        while queue:
            found = queue.pop()
            if found in seen:
                continue
            seen.add(found)
            queue.extend(map_segment.get(found, (None, ()))[1])
        reach[id_segment] = seen

    return reach


# -----------------------------------------------------------------------------
def _segment_of(filepath, map_segment):
    """
    Return the segment governing a file: the one whose root is the
    longest prefix of its path, so that a segment inside another
    governs what is under it.

    """

    filepath = pathlib.Path(filepath)
    found    = None
    depth    = -1

    for (id_segment, (root, _)) in map_segment.items():
        if filepath.is_relative_to(root) and len(root.parts) > depth:
            (found, depth) = (id_segment, len(root.parts))

    return found


# -----------------------------------------------------------------------------
def _iter_declaration(map_document):
    """
    Yield (filepath, guid) for every identity declared.

    """

    for (location, document) in map_document.items():
        if isinstance(document, dict):
            for (_path, guid) in cc_public.check.identity.iter_declaration(document):
                yield (location.filepath, guid)


# -----------------------------------------------------------------------------
def _fault(location, path, id_segment, id_target):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.Nonconformity(
        filepath = str(location.filepath),
        path     = path,
        message  = ('Names something of {target}, and {segment} does not consume it. A '
                    'segment may name what is its own and what belongs to a segment it '
                    'consumes; the direction of dependence is one way.'.format(
                            target = id_target, segment = id_segment)),
        severity = cc_public.check.result.SEVERITY_CRITICAL)
