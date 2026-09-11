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
                        the impact of a change to one item, and what
                        rests on the files a commit changed. Read by
                        the trace check and by the trace and changed
                        commands, so that they cannot disagree. Prints
                        nothing and writes nothing.
relation:               []

...
"""


import typing

import cc_public.item


KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_RELATION      = 'relation'
KEY_ID_REL        = 'id_relation'
KEY_GUID_TGT      = 'guid_target'
KEY_ID_TGT        = 'id_target'
KEY_STATUS        = 'status'
KEY_VERIFICATION  = 'verification'
KEY_CRITERIA      = 'success_criteria'

KEY_TABLE         = 'table'
KEY_CRITICALITY   = 'criticality'
KEY_DIMENSION     = 'dimension'
KEY_LEVEL         = 'level'
KEY_ID_CRIT       = 'id_criticality'
KEY_RESPONSIBLE   = 'responsibility'
KEY_REQUIRES      = 'requires'
KEY_ID_OBJECTIVE  = 'id_objective'
KEY_CLAIM         = 'claim'

CLAIM_EVIDENTIAL  = 'evidential'
OBJ_VERDICT       = 'obj_verdict_per_requirement'
OBJ_ANALYSIS      = 'obj_coverage_analysed'

PREFIX_REQ        = 'req'
SEPARATOR         = '_'

REL_DERIVED       = 'r_is_derived_from'
REL_IMPLEMENTED   = 'r_is_implemented_by'
REL_VERIFIES      = 'r_verifies'
KEY_DESCRIBES     = 'describes'
KEY_DEPENDENCY    = 'dependency'
KEY_TITLE         = 'title'
PREFIX_RELATION   = 'r'

STATUS_PROPOSED   = 'proposed'
STATUS_ACCEPTED   = 'accepted'
STATUS_DEPRECATED = 'deprecated'

# Read by the evidence check, which distinguishes evidence from a run
# from evidence a person attests to.
#
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

    shared_verdict holds the verifiers this requirement shares with
    another, and is empty where any verifier is this requirement's
    alone. A shared verifier matters only where nothing else observes
    the requirement on its own: a case written for it resolves the
    ambiguity that the shared function leaves.

    demands_verdict says a criticality this requirement declares
    requires that a verdict stand for one requirement. It is read from
    the criticality register, never from this module.

    demands_analysis says the same of the objective that a
    requirement's coverage be analysed and recorded. Whether one
    exists is not said here: reading an analysis means reading source,
    which this module cannot, so the gap for a missing analysis is
    made by the check that can (ddr_coverage_analysis).

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
    shared_verdict: tuple = ()
    demands_verdict: bool = False
    demands_analysis: bool = False
    claim:          str | None = None


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
    map_verifies  = {}

    for (guid, edges) in map_edge.items():
        for edge in edges:
            if edge.get(KEY_ID_REL) == REL_DERIVED and is_requirement(map_by_guid.get(guid)):
                map_children.setdefault(edge.get(KEY_GUID_TGT), []).append(guid)
            if edge.get(KEY_ID_REL) == REL_VERIFIES:
                map_verifier.setdefault(edge.get(KEY_GUID_TGT), []).append(guid)
                map_verifies.setdefault(guid, set()).add(edge.get(KEY_GUID_TGT))

    (map_level, _) = _level(map_document)

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

        # A verifier that observes this requirement alone settles it,
        # whatever else the others also observe.
        #
        list_shared = []
        is_alone    = False
        for verifier in map_verifier.get(guid, []):
            other = map_verifies.get(verifier, set()) - {guid}
            if other:
                list_shared.extend((name(verifier), name(g)) for g in sorted(other))
            else:
                is_alone = True

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
                        gap            = (),
                        shared_verdict = () if is_alone else tuple(list_shared),
                        demands_verdict = _demands(document, map_level,
                                                   OBJ_VERDICT),
                        demands_analysis = _demands(document, map_level,
                                                    OBJ_ANALYSIS),
                        claim          = document.get(KEY_CLAIM))
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
class Changed(typing.NamedTuple):
    """
    One standalone item in a file that changed: what it is, where it
    is, how many items it holds within it, and the decisions that
    decide it.

    """

    id_self:    str
    guid_self:  str
    prefix:     str
    title:      str | None
    location:   str
    held:       int
    decided_by: tuple


# -----------------------------------------------------------------------------
class Dependent(typing.NamedTuple):
    """
    One item outside the changed files that rests on something in them:
    the item, the dependency edge it holds, what that edge reaches, and
    the changed item the chain ends at.

    """

    id_self:     str
    guid_self:   str
    id_relation: str
    id_target:   str
    changed:     str


# -----------------------------------------------------------------------------
def changed(map_document, set_filepath):
    """
    ---

    id_self:                pyf_cc_public.trace.changed
    guid_self:              pyf_1bcd47e36f4244c0931de468dde51e3b
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  What changed and what rests on it
    brief:                  |
                            Return (changed, dependent, suspect): every
                            standalone item in the files named, in
                            location order; every item elsewhere that
                            rests on an item in them by a chain of
                            dependency edges, in id order; and every
                            record that describes one of the items in them
                            and is not itself among them.

                            Every item in a changed file is taken as
                            possibly changed, the entries of a register
                            alike, which is conservative where a change
                            touched one of many. An item resting on two
                            changed items is reported once, with the first
                            chain that reached it.
    description:            |
                            Every standalone item in the files named, with
                            the decisions that decide it, and every item
                            elsewhere reached from one of them by a chain
                            of dependency edges read from target to
                            source. The reverse of the closure the
                            evidence digest follows, over the same
                            declarations.
    relation:               []

    ...
    """

    (map_by_guid, map_edge) = _index(map_document)
    follow        = dependency(map_document)
    map_describer = _describer(map_document, map_by_guid, map_edge)
    set_changed   = set()
    set_suspect   = set()
    list_out      = []

    for (location, document) in sorted(map_document.items()):

        if location.filepath not in set_filepath or not isinstance(document, dict):
            continue

        held = [one.guid_self for one in cc_public.item.iter_item(document)]
        set_changed.update(g for g in held if isinstance(g, str))

        # Every item in the file and not the document alone: an entry
        # is described by the record that introduced it
        # (ddr_record_currency).
        #
        for one in held:
            set_suspect |= map_describer.get(one, set())
        guid = document.get(KEY_GUID_SELF)
        list_out.append(Changed(
                id_self    = document.get(KEY_ID_SELF),
                guid_self  = guid,
                prefix     = str(document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0],
                title      = document.get(KEY_TITLE),
                location   = str(location.filepath),
                held       = max(len(held) - 1, 0),
                decided_by = tuple(sorted(map_describer.get(guid, ())))))

    reverse = {}
    for (guid, edges) in map_edge.items():
        for e in edges:
            if e.get(KEY_ID_REL) in follow and isinstance(e.get(KEY_GUID_TGT), str):
                reverse.setdefault(e[KEY_GUID_TGT], []).append((guid, e[KEY_ID_REL]))

    seen     = set(set_changed)
    pending  = [(g, g) for g in sorted(set_changed,
                                       key = lambda g: _name(g, map_by_guid, []))]
    list_dep = []

    while pending:
        (guid, root) = pending.pop(0)
        for (source, id_relation) in reverse.get(guid, []):
            if source in seen:
                continue
            seen.add(source)
            list_dep.append(Dependent(id_self     = _name(source, map_by_guid, []),
                                      guid_self   = source,
                                      id_relation = id_relation,
                                      id_target   = _name(guid, map_by_guid, []),
                                      changed     = _name(root, map_by_guid, [])))
            pending.append((source, root))

    return (list_out, sorted(list_dep),
            tuple(sorted(set_suspect - {one.id_self for one in list_out})))


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
def _demands(document, map_level, id_objective):
    """
    Return whether a criticality the requirement declares requires the
    named objective.

    Read from the criticality register through map_level, so that
    raising what a level demands is editing an entry rather than
    editing this.

    """

    carried = document.get(KEY_CRITICALITY)

    if not isinstance(carried, dict):
        return False

    for reference in carried.values():
        if not isinstance(reference, dict):
            continue
        entry = map_level.get(reference.get(KEY_ID_CRIT))
        if entry is None:
            continue
        for required in entry.get(KEY_REQUIRES) or []:
            if isinstance(required, dict) \
                    and required.get(KEY_ID_OBJECTIVE) == id_objective:
                return True

    return False


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

    if record.verification and not record.verified_by:
        yield Gap(KEY_VERIFICATION, elsewhere,
                  'Verified by {method}, and nothing names it. A test function '
                  'or a case says what it verifies by an r_verifies edge, or '
                  'the requirement is verified by nothing. A method a person '
                  'carries out needs a case too: the case is where what was '
                  'expected is stated, before anyone '
                  'observes.'.format(method = record.verification))

    if record.shared_verdict:
        (verifier, other) = record.shared_verdict[0]
        yield Gap(KEY_VERIFICATION,
                  SEVERITY_CRITICAL if record.demands_verdict
                  or record.claim == CLAIM_EVIDENTIAL else SEVERITY_ADVISORY,
                  'Every verifier observes another requirement too: {v} also '
                  'verifies {o}. One verdict then stands for two obligations, '
                  'so a failure does not say which was unmet, and an assertion '
                  'removed from {v} leaves both still verified. Divide it, or '
                  'write a case for each requirement it '
                  'observes.'.format(v = verifier, o = other))


# -----------------------------------------------------------------------------
def _index(map_document):
    """
    Return (guid -> item, guid -> its edges) for every identified item
    in the tree, embedded items included.

    """

    map_by_guid = {}
    map_edge    = {}

    for document in map_document.values():
        for held in cc_public.item.iter_item(document):
            item  = held.document
            edges = [e for e in (item.get(KEY_RELATION) or []) if isinstance(e, dict)]
            guid = item.get(KEY_GUID_SELF)
            if isinstance(guid, str):
                map_by_guid[guid] = item
                map_edge[guid]    = edges

    return (map_by_guid, map_edge)


# -----------------------------------------------------------------------------
def is_requirement(document):
    """
    Return whether document is a requirement, by its prefix.

    """

    return cc_public.item.is_type(document, PREFIX_REQ)


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


# -----------------------------------------------------------------------------
class Criticality(typing.NamedTuple):
    """
    The effective criticality of every item a requirement reaches.

    derived holds one entry per item reached, mapping a dimension to
    the greatest level reaching it. base holds the lowest level each
    dimension defines, which is what an item nothing reaches carries.

    The answer is only as closed as the tree it was read from. Where a
    consuming segment holds a requirement that reaches an item here,
    that requirement must be loaded for the item's criticality to be
    right, which is what --closed-world and a second --path are for.

    """

    derived: dict
    base:    dict


# -----------------------------------------------------------------------------
def responsibility(map_document):
    """
    Return the readable ids of every relation declaring that its target
    is responsible for meeting its source.

    Read from the relation register, so a relation a partner brings is
    followed by the same derivation without this module knowing its
    name.

    """

    return _declaring(map_document, KEY_RESPONSIBLE)


# -----------------------------------------------------------------------------
def _describer(map_document, map_by_guid, map_edge):
    """
    Return, by guid, the items that describe each item.

    """

    describe = describing(map_document)
    out      = {}

    for (guid, edges) in map_edge.items():
        for edge in edges:
            if edge.get(KEY_ID_REL) in describe:
                out.setdefault(edge.get(KEY_GUID_TGT), set()).add(
                                    _name(guid, map_by_guid, []))

    return out


# -----------------------------------------------------------------------------
def describing(map_document):
    """
    Return the readable ids of every relation declaring that a change
    to what it points at makes the source suspect
    (ddr_record_currency).

    Read from the relation register, as dependency and responsibility
    are.

    """

    return _declaring(map_document, KEY_DESCRIBES)


# -----------------------------------------------------------------------------
def dependency(map_document):
    """
    Return the readable ids of every relation declaring that following
    it reaches something the source rests on
    (ddr_dependency_closure).

    Read from the relation register, as responsibility is.

    """

    return _declaring(map_document, KEY_DEPENDENCY)


# -----------------------------------------------------------------------------
def _declaring(map_document, key):
    """
    Return the readable ids of every relation register entry that
    declares key.

    """

    out = set()

    for document in map_document.values():

        if not isinstance(document, dict) \
                or not isinstance(document.get(KEY_TABLE), dict):
            continue

        for entry in document[KEY_TABLE].values():
            if isinstance(entry, dict) and entry.get(key) \
                    and isinstance(entry.get(KEY_ID_SELF), str) \
                    and entry[KEY_ID_SELF].split(SEPARATOR, 1)[0] == PREFIX_RELATION:
                out.add(entry[KEY_ID_SELF])

    return out


# -----------------------------------------------------------------------------
def _level(map_document):
    """
    Return (id -> entry, dimension -> lowest level) read from the
    criticality register.

    The entry rather than the pair it declares, since a reader wants
    the objectives it requires as often as the level it sits at.

    """

    map_level = {}

    for document in map_document.values():

        if not isinstance(document, dict) \
                or not isinstance(document.get(KEY_TABLE), dict):
            continue

        for entry in document[KEY_TABLE].values():
            if not isinstance(entry, dict):
                continue
            dimension = entry.get(KEY_DIMENSION)
            level     = entry.get(KEY_LEVEL)
            if isinstance(dimension, str) and isinstance(level, int) \
                    and isinstance(entry.get(KEY_ID_SELF), str):
                map_level[entry[KEY_ID_SELF]] = entry

    base = {}
    for entry in map_level.values():
        (dimension, level) = (entry[KEY_DIMENSION], entry[KEY_LEVEL])
        if dimension not in base or level < base[dimension]:
            base[dimension] = level

    return (map_level, base)


# -----------------------------------------------------------------------------
def _declared(document, map_level):
    """
    Return dimension -> level for what a requirement declares, reading
    the level from the register rather than from the requirement.

    """

    out     = {}
    carried = document.get(KEY_CRITICALITY)

    if not isinstance(carried, dict):
        return out

    for reference in carried.values():
        if not isinstance(reference, dict):
            continue
        entry = map_level.get(reference.get(KEY_ID_CRIT))
        if entry is not None:
            (dimension, level) = (entry[KEY_DIMENSION], entry[KEY_LEVEL])
            out[dimension] = max(level, out.get(dimension, level))

    return out


# -----------------------------------------------------------------------------
def criticality(map_document):
    """
    Return the effective criticality of every item a requirement
    reaches, as a Criticality.

    A requirement declares its own. Everything responsible for meeting
    it takes it, and an item reached by several takes the greatest on
    each dimension separately, so that a critical requirement is never
    diluted by a trivial one sharing the same code.

    Which edges are followed is read from the relation register, not
    written here.

    """

    (map_by_guid, map_edge) = _index(map_document)
    (map_level, base)       = _level(map_document)
    set_relation            = responsibility(map_document)

    derived = {}

    for (guid, item) in map_by_guid.items():

        if not is_requirement(item):
            continue

        declared = _declared(item, map_level)

        if not declared:
            continue

        # Every item the requirement reaches, however far, takes what
        # the requirement declares. A cycle is walked once.
        #
        seen    = {guid}
        pending = [guid]

        while pending:
            for edge in map_edge.get(pending.pop(), ()):
                if edge.get(KEY_ID_REL) not in set_relation:
                    continue
                target = edge.get(KEY_GUID_TGT)
                if not isinstance(target, str) or target in seen:
                    continue
                seen.add(target)
                pending.append(target)
                reached = map_by_guid.get(target)
                if reached is None:
                    continue
                name = reached.get(KEY_ID_SELF)
                if not isinstance(name, str):
                    continue
                held = derived.setdefault(name, {})
                for (dimension, level) in declared.items():
                    held[dimension] = max(level, held.get(dimension, level))

    return Criticality(derived = derived, base = base)
