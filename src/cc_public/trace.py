"""
---

id_self:                pym_cc_public.trace
guid_self:              pym_568452a1258841b5a6aacc4abd66d81f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Trace projection
brief:                  |
                        What each requirement derives from, what
                        implements it, what verifies it, and what it
                        lacks.
description:            |
                        Computes the assurance of every requirement
                        from the documents alone: its status,
                        derivation, children, whether it is a leaf,
                        the code responsible for it, the tests that
                        verify it, what it names that does not
                        resolve, and its gaps with their severities,
                        which follow from its status and from whether
                        the world is closed. Computes the reverse too,
                        the impact of a change to one item. Read by
                        the trace check and by the trace command, so
                        that the two cannot disagree. Prints nothing
                        and writes nothing.
relation:               []

...
"""


import typing


KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_RELATION      = 'relation'
KEY_ID_REL        = 'id_relation'
KEY_GUID_TGT      = 'guid_target'
KEY_ID_TGT        = 'id_target'
KEY_STATUS        = 'status'
KEY_VERIFICATION  = 'verification'
KEY_CRITERIA      = 'success_criteria'

PREFIX_REQ        = 'req'
SEPARATOR         = '_'

REL_DERIVED       = 'r_is_derived_from'
REL_IMPLEMENTED   = 'r_is_implemented_by'
REL_VERIFIES      = 'r_verifies'

STATUS_PROPOSED   = 'proposed'
STATUS_ACCEPTED   = 'accepted'
STATUS_DEPRECATED = 'deprecated'

VERIFICATION_TEST = 'test'

# What follows from a gap. The same two words the checks use, and
# with the same meaning: what must be fixed, and what must be known.
#
SEVERITY_CRITICAL = 'critical'
SEVERITY_ADVISORY = 'advisory'


# -----------------------------------------------------------------------------
class Gap(typing.NamedTuple):
    """
    One thing a requirement's assurance lacks: where in the item, what
    follows from it, and why.

    """

    path:     str
    severity: str
    message:  str


# -----------------------------------------------------------------------------
class Requirement(typing.NamedTuple):
    """
    One requirement's assurance, projected from the tree: what it
    derives from, what derives from it, what implements it, what
    verifies it, and what it lacks.

    Every target is named by readable id where it resolves and by guid
    where it does not, the unresolved guids listed apart. is_leaf says
    no requirement in the tree derives from this one, which in an open
    world is provisional.

    """

    id_self:        str
    guid_self:      str
    status:         str
    verification:   str | None
    has_criteria:   bool
    derives_from:   tuple
    children:       tuple
    is_leaf:        bool
    implemented_by: tuple
    verified_by:    tuple
    unresolved:     tuple
    gap:            tuple


# -----------------------------------------------------------------------------
class Impact(typing.NamedTuple):
    """
    What a change to one item may affect: the requirements it
    implements, the requirements it verifies, and through those, what
    verifies and implements them.

    Potentially affected, from the authored edges alone. Nothing here
    claims the change matters.

    """

    id_self:    str
    guid_self:  str
    implements: tuple
    verifies:   tuple


# -----------------------------------------------------------------------------
def projection(map_document, is_closed_world = False):
    """
    Return one Requirement per requirement in the tree, in id order.

    is_closed_world says the tree holds everything an edge could point
    at, so that a child or an implementation absent from it is absent
    entirely. Where it is not asserted, a leaf may have children
    elsewhere, and what a leaf lacks is advisory rather than critical.

    """

    (map_by_guid, map_edge) = _index(map_document)
    map_children  = {}
    map_verifier  = {}

    for (guid, edges) in map_edge.items():
        for edge in edges:
            if edge.get(KEY_ID_REL) == REL_DERIVED and is_requirement(map_by_guid.get(guid)):
                map_children.setdefault(edge.get(KEY_GUID_TGT), []).append(guid)
            if edge.get(KEY_ID_REL) == REL_VERIFIES:
                map_verifier.setdefault(edge.get(KEY_GUID_TGT), []).append(guid)

    list_out = []

    for (guid, document) in map_by_guid.items():

        if not is_requirement(document):
            continue

        unresolved  = []

        def name(g, unresolved = unresolved):
            return _name(g, map_by_guid, unresolved)

        derives     = tuple(name(e.get(KEY_GUID_TGT)) for e in map_edge.get(guid, [])
                            if e.get(KEY_ID_REL) == REL_DERIVED)
        implemented = tuple(name(e.get(KEY_GUID_TGT)) for e in map_edge.get(guid, [])
                            if e.get(KEY_ID_REL) == REL_IMPLEMENTED)
        children    = tuple(sorted(name(g) for g in map_children.get(guid, [])))
        verifiers   = tuple(sorted(name(g) for g in map_verifier.get(guid, [])))
        status      = document.get(KEY_STATUS) or STATUS_PROPOSED
        record      = Requirement(
                        id_self        = document.get(KEY_ID_SELF),
                        guid_self      = guid,
                        status         = status,
                        verification   = document.get(KEY_VERIFICATION),
                        has_criteria   = bool(str(document.get(KEY_CRITERIA) or '').strip()),
                        derives_from   = derives,
                        children       = children,
                        is_leaf        = not children,
                        implemented_by = implemented,
                        verified_by    = verifiers,
                        unresolved     = tuple(sorted(set(unresolved))),
                        gap            = ())
        list_out.append(record._replace(gap = tuple(_gaps(record, is_closed_world))))

    return sorted(list_out, key = lambda r: r.id_self or '')


# -----------------------------------------------------------------------------
def impact(map_document, name, is_closed_world = False):
    """
    Return the Impact of a change to the item called name, an id or a
    guid, or None where nothing is called that.

    """

    (map_by_guid, _) = _index(map_document)
    guid = name if name in map_by_guid else next(
                (g for (g, d) in map_by_guid.items() if d.get(KEY_ID_SELF) == name), None)

    if guid is None:
        return None

    id_self = map_by_guid[guid].get(KEY_ID_SELF)
    list_req = projection(map_document, is_closed_world)

    return Impact(id_self    = id_self,
                  guid_self  = guid,
                  implements = tuple(r for r in list_req if id_self in r.implemented_by
                                                        or guid in r.implemented_by),
                  verifies   = tuple(r for r in list_req if id_self in r.verified_by
                                                        or guid in r.verified_by))


# -----------------------------------------------------------------------------
def impact_of_files(map_document, set_filepath, is_closed_world = False):
    """
    Return the Impact of every item in the files named that implements
    or verifies a requirement, in id order.

    Every document in a changed file is taken as possibly changed, the
    module's and each definition's alike, which is conservative where a
    change touched one function of many.

    """

    list_out = []

    for (location, document) in sorted(map_document.items()):
        if location.filepath not in set_filepath or not isinstance(document, dict):
            continue
        found = impact(map_document, document.get(KEY_GUID_SELF), is_closed_world)
        if found is not None and (found.implements or found.verifies):
            list_out.append(found)

    return list_out


# -----------------------------------------------------------------------------
class Neighbourhood(typing.NamedTuple):
    """
    One item and every edge at it: those it holds, as (relation, target
    id), and those held by others that point at it, as (source id,
    relation). Targets and sources are named by id where they resolve
    and by guid where they do not.

    """

    id_self:   str
    guid_self: str
    location:  str
    title:     str | None
    brief:     str | None
    outgoing:  tuple
    incoming:  tuple


# -----------------------------------------------------------------------------
def neighbourhood(map_document, name):
    """
    Return the Neighbourhood of the item called name, an id or a guid,
    or None where nothing is called that.

    """

    (map_by_guid, map_edge) = _index(map_document)
    guid = name if name in map_by_guid else next(
                (g for (g, d) in map_by_guid.items() if d.get(KEY_ID_SELF) == name), None)

    if guid is None:
        return None

    item     = map_by_guid[guid]
    location = next((str(loc) for (loc, d) in map_document.items()
                     if isinstance(d, dict) and d.get(KEY_GUID_SELF) == guid), '')
    outgoing = tuple((e.get(KEY_ID_REL), _name(e.get(KEY_GUID_TGT), map_by_guid, []))
                     for e in map_edge.get(guid, []))
    incoming = tuple(sorted((map_by_guid[g].get(KEY_ID_SELF) or g, e.get(KEY_ID_REL))
                            for (g, edges) in map_edge.items()
                            for e in edges if e.get(KEY_GUID_TGT) == guid))

    return Neighbourhood(id_self   = item.get(KEY_ID_SELF),
                         guid_self = guid,
                         location  = location,
                         title     = item.get('title'),
                         brief     = ' '.join(str(item.get('brief') or '').split()) or None,
                         outgoing  = outgoing,
                         incoming  = incoming)


# -----------------------------------------------------------------------------
def _gaps(record, is_closed_world):
    """
    Yield what the requirement lacks, given its status and the world.

    A proposed requirement may be incomplete while it is written, and
    its gaps are advisory. An accepted one has claimed to be complete,
    and a gap in what it claims is critical, except where an open world
    leaves room for the missing thing to exist elsewhere. A deprecated
    requirement is history and lacks nothing.

    """

    if record.status == STATUS_DEPRECATED:
        return

    is_accepted = record.status == STATUS_ACCEPTED
    claimed     = SEVERITY_CRITICAL if is_accepted else SEVERITY_ADVISORY
    elsewhere   = SEVERITY_CRITICAL if is_accepted and is_closed_world \
                  else SEVERITY_ADVISORY

    if not record.derives_from:
        yield Gap(KEY_RELATION, claimed,
                  'Derives from nothing. A requirement traces to a need or a '
                  'higher level requirement by an r_is_derived_from edge, or it '
                  'cannot show it is necessary.')

    if is_accepted and not record.has_criteria:
        yield Gap(KEY_CRITERIA, claimed,
                  'Accepted with no success criteria. What verification must '
                  'show is part of what was accepted.')

    if is_accepted and not record.verification:
        yield Gap(KEY_VERIFICATION, claimed,
                  'Accepted with no verification method. How the requirement '
                  'is shown to be met is part of what was accepted.')

    if record.is_leaf and not record.implemented_by:
        yield Gap(KEY_RELATION, elsewhere,
                  'Nothing derives from it and nothing implements it. A leaf '
                  'requirement names the code responsible for it by an '
                  'r_is_implemented_by edge, or a lower requirement derives '
                  'from it.')

    if record.verification == VERIFICATION_TEST and not record.verified_by:
        yield Gap(KEY_VERIFICATION, elsewhere,
                  'Verified by test, and no test names it. A test says what it '
                  'verifies by an r_verifies edge, or the requirement is '
                  'verified by nothing.')


# -----------------------------------------------------------------------------
def _index(map_document):
    """
    Return (guid -> item, guid -> its edges) for every identified item
    in the tree, embedded items included.

    """

    map_by_guid = {}
    map_edge    = {}

    for document in map_document.values():
        for (item, edges) in _iter_item(document):
            guid = item.get(KEY_GUID_SELF)
            if isinstance(guid, str):
                map_by_guid[guid] = item
                map_edge[guid]    = edges

    return (map_by_guid, map_edge)


# -----------------------------------------------------------------------------
def _iter_item(node):
    """
    Yield (item, its edges) for every mapping declaring an identity in
    node, outermost first.

    """

    if isinstance(node, dict):
        if isinstance(node.get(KEY_GUID_SELF), str):
            yield (node, [e for e in (node.get(KEY_RELATION) or [])
                            if isinstance(e, dict)])
        for value in node.values():
            yield from _iter_item(value)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_item(value)


# -----------------------------------------------------------------------------
def is_requirement(document):
    """
    Return whether document is a requirement, by its prefix.

    """

    return isinstance(document, dict) and str(
                document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] == PREFIX_REQ


# -----------------------------------------------------------------------------
def _name(guid, map_by_guid, unresolved):
    """
    Return the readable id of the item guid names, or the guid itself
    where nothing in the tree carries it, noting it as unresolved.

    """

    item = map_by_guid.get(guid)

    if item is None:
        unresolved.append(guid)
        return guid

    return item.get(KEY_ID_SELF) or guid
