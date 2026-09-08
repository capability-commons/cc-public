"""
---

id_self:                pym_cc_public.check.relation
guid_self:              pym_02a9a99732d544069897b6f7b090c9c5
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Relation check
brief:                  |
                        Check that every edge runs between the kinds
                        of thing its relation allows, and that the
                        semantics the relation declares hold.
description:            |
                        A relation entry may constrain the types at
                        its two ends, forbid cycles, declare itself
                        transitive, name the relations that may not
                        hold between the same pair, and say how many
                        of its edges one item holds. An edge that
                        breaks a constraint is a critical fault at the
                        edge, and a constraint naming a type or a
                        relation that does not exist is a fault at the
                        entry. An edge of a transitive relation that a
                        chain of its own edges already implies is
                        advisory, since it states nothing false. A
                        minimum cardinality is read against every item
                        the domain names, and is passed over where a
                        relation declares no domain. A target that
                        does not resolve is left to the reference
                        check. An absent constraint says nothing.
relation:               []

...
"""


import collections

import cc_public.check.reference
import cc_public.check.register
import cc_public.check.result
import cc_public.item
import cc_public.path


ID_CHECK       = 'relation'
TITLE          = 'Edges hold between the kinds of thing their relation allows'
NOUN           = 'edge'

KEY_ID_SELF    = 'id_self'
KEY_GUID_SELF  = 'guid_self'
KEY_RELATION   = 'relation'
KEY_ID_REL     = 'id_relation'
KEY_GUID_TGT   = 'guid_target'
KEY_ID_TARGET  = 'id_target'
KEY_TABLE      = 'table'
KEY_DOMAIN     = 'domain'
KEY_RANGE      = 'range'
KEY_ACYCLIC    = 'acyclic'
KEY_TRANSITIVE = 'transitive'
KEY_INCOMPAT   = 'incompatible'
KEY_CARDINAL   = 'cardinality'
KEY_MINIMUM    = 'minimum'
KEY_MAXIMUM    = 'maximum'

ID_TYPE_REL    = 't_relation'
REL_HELD_IN    = 'r_is_held_in_registry'

SEPARATOR      = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every edge that breaks its relation's
    constraints, and every constraint that names no type.

    A relation entry may say what types an edge of it runs from and to,
    and whether its edges may form a cycle. An absent constraint says
    nothing. An edge whose target does not resolve is left to the
    reference check, which reports it.

    """

    map_document       = context.map_document
    (_, document_type) = cc_public.check.register.find_type(map_document)
    map_prefix         = cc_public.check.register.map_prefix(document_type)
    set_type           = {entry[KEY_ID_SELF]
                          for entry in document_type[KEY_TABLE].values()
                          if isinstance(entry, dict) and KEY_ID_SELF in entry}
    map_declaration    = cc_public.check.reference.map_declaration(context)
    (filepath_register, table) = _relation_register(map_document, document_type)

    list_bad = _bad_constraint(filepath_register, table, set_type)
    map_edge = collections.defaultdict(list)
    count    = 0

    for (filepath, document) in sorted(map_document.items()):

        for (path, holder, edge) in _iter_edge(document):

            count += 1
            entry  = table.get(edge.get(KEY_ID_REL))

            if entry is None:
                continue

            id_target   = map_declaration.get(edge.get(KEY_GUID_TGT), (None, None))[1]
            type_holder = _type_of(holder.get(KEY_ID_SELF), map_prefix)
            type_target = _type_of(id_target, map_prefix)

            for (key, actual, end) in ((KEY_DOMAIN, type_holder, 'from'),
                                       (KEY_RANGE,  type_target, 'to')):
                allowed = entry.get(key)
                if allowed and actual is not None and actual not in allowed:
                    list_bad.append(_fault(filepath, path,
                            'An {rel} edge runs {end} {allowed}, and this one '
                            'runs {end} {actual} ({name}).'.format(
                                    rel     = edge.get(KEY_ID_REL),
                                    end     = end,
                                    allowed = _list(allowed),
                                    actual  = actual,
                                    name    = holder.get(KEY_ID_SELF) if end == 'from'
                                              else id_target)))

            map_edge[edge.get(KEY_ID_REL)].append(
                    (holder.get(KEY_GUID_SELF), edge.get(KEY_GUID_TGT),
                     filepath, path))

    for (id_relation, list_edge) in sorted(map_edge.items()):
        entry = table.get(id_relation) or {}
        if entry.get(KEY_ACYCLIC):
            list_bad.extend(_cycle(id_relation, list_edge, map_declaration))
        if entry.get(KEY_TRANSITIVE):
            list_bad.extend(_redundant(id_relation, list_edge, map_declaration))

    list_bad.extend(_incompatible(table, map_edge, map_declaration))
    list_bad.extend(_cardinality(table, map_edge, map_declaration, map_prefix, context))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _relation_register(map_document, document_type):
    """
    Return (filepath, table) of the relation register, found through
    the type register as the tree finds it.

    """

    entry = document_type[KEY_TABLE].get(ID_TYPE_REL) or {}

    for edge in entry.get(KEY_RELATION) or []:
        if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_HELD_IN:
            for (filepath, document) in map_document.items():
                if isinstance(document, dict) \
                        and document.get(KEY_ID_SELF) == edge.get(KEY_ID_TARGET):
                    return (filepath, document.get(KEY_TABLE) or {})

    return (None, {})


# -----------------------------------------------------------------------------
def _bad_constraint(filepath, table, set_type):
    """
    Return a fault for each constraint naming a type or a relation that
    is not one.

    """

    out = []

    for (key_entry, entry) in sorted(table.items()):

        if not isinstance(entry, dict):
            continue

        for (key, known, noun, id_register) in ((KEY_DOMAIN,   set_type,  'type',
                                                 'the type register'),
                                                (KEY_RANGE,    set_type,  'type',
                                                 'the type register'),
                                                (KEY_INCOMPAT, set(table), 'relation',
                                                 'this register')):
            for name in entry.get(key) or []:
                if name not in known:
                    out.append(_fault(filepath,
                            cc_public.path.join(cc_public.path.join(KEY_TABLE, key_entry), key),
                            'Names {name}, which is not a {noun} in {id_register}, so '
                            'nothing could satisfy it.'.format(
                                    name = name, noun = noun, id_register = id_register)))

    return out


# -----------------------------------------------------------------------------
def _iter_edge(node, path = '', holder = None):
    """
    Yield (path, holder, edge) for every edge in node, where holder is
    the nearest item the edge is written on.

    """

    if isinstance(node, dict):

        if isinstance(node.get(KEY_GUID_SELF), str):
            holder = node

        for (key, value) in node.items():
            path_child = cc_public.path.join(path, key)
            if key == KEY_RELATION and isinstance(value, list) and holder is not None:
                for (idx, edge) in enumerate(value):
                    if isinstance(edge, dict) and KEY_ID_REL in edge:
                        yield (cc_public.path.join(path_child, idx), holder, edge)
            else:
                yield from _iter_edge(value, path_child, holder)

    elif isinstance(node, list):

        for (idx, value) in enumerate(node):
            yield from _iter_edge(value, cc_public.path.join(path, idx), holder)


# -----------------------------------------------------------------------------
def _cycle(id_relation, list_edge, map_declaration):
    """
    Return a fault for each cycle the edges of one acyclic relation form,
    reported at the edge that closes it.

    """

    map_out = collections.defaultdict(list)

    for (source, target, filepath, path) in list_edge:
        map_out[source].append((target, filepath, path))

    out   = []
    done  = set()
    stack = []

    def visit(guid):
        stack.append(guid)
        for (target, filepath, path) in map_out.get(guid, []):
            if target in stack:
                cycle = stack[stack.index(target):] + [target]
                out.append(_fault(filepath, path,
                        '{rel} edges may not form a cycle, and this one closes '
                        '{cycle}.'.format(
                            rel   = id_relation,
                            cycle = ' -> '.join(
                                map_declaration.get(g, (None, g))[1] or g
                                for g in cycle))))
            elif target not in done:
                visit(target)
        stack.pop()
        done.add(guid)

    for source in sorted(map_out):
        if source not in done:
            visit(source)

    return out


# -----------------------------------------------------------------------------
def _redundant(id_relation, list_edge, map_declaration):
    """
    Return a question for each asserted edge of a transitive relation
    that a chain of its own edges already implies.

    A transitive relation makes a chain one edge, so the edge alongside
    the chain says what the chain says. It is not false, which is why
    it is advisory.

    """

    map_out = collections.defaultdict(set)

    for (source, target, _, _) in list_edge:
        map_out[source].add(target)

    out = []

    for (source, target, filepath, path) in list_edge:

        if not _reaches(map_out, source, target):
            continue

        out.append(_question(filepath, path,
                '{rel} is transitive, and a chain of its edges runs from {source} to '
                '{target} already, so this edge says what the chain says.'.format(
                        rel    = id_relation,
                        source = _name(map_declaration, source),
                        target = _name(map_declaration, target))))

    return out


# -----------------------------------------------------------------------------
def _reaches(map_out, source, target):
    """
    Return whether target is reachable from source by a chain of two
    edges or more.

    The direct edge is left out of the first step, so what is found is
    a chain and never the edge being asked about.

    """

    seen  = set()
    stack = [node for node in map_out.get(source, ()) if node != target]

    while stack:

        node = stack.pop()

        if node == target:
            return True

        if node in seen:
            continue

        seen.add(node)
        stack.extend(map_out.get(node, ()))

    return False


# -----------------------------------------------------------------------------
def _incompatible(table, map_edge, map_declaration):
    """
    Return a fault for each pair of items two incompatible relations
    both hold between, reported at the edge of the relation that
    declares the incompatibility.

    """

    out = []

    for (id_relation, entry) in sorted(table.items()):

        if not isinstance(entry, dict):
            continue

        for id_other in entry.get(KEY_INCOMPAT) or []:

            held = {frozenset((source, target))
                    for (source, target, _, _) in map_edge.get(id_other, ())}

            for (source, target, filepath, path) in map_edge.get(id_relation, ()):

                if frozenset((source, target)) not in held:
                    continue

                out.append(_fault(filepath, path,
                        '{rel} and {other} may not both hold between a pair, and both hold '
                        'between {source} and {target}.'.format(
                                rel    = id_relation,
                                other  = id_other,
                                source = _name(map_declaration, source),
                                target = _name(map_declaration, target))))

    return out


# -----------------------------------------------------------------------------
def _cardinality(table, map_edge, map_declaration, map_prefix, context):
    """
    Return a fault for each item holding more edges of one relation
    than its entry allows, and for each item in a relation's domain
    holding fewer than it requires.

    A minimum is a claim about every item the relation may run from, so
    it is read only where domain says which items those are.

    """

    out = []

    for (id_relation, entry) in sorted(table.items()):

        if not isinstance(entry, dict):
            continue

        bound = entry.get(KEY_CARDINAL)

        if not isinstance(bound, dict):
            continue

        map_count = collections.defaultdict(list)

        for (source, _, filepath, path) in map_edge.get(id_relation, ()):
            map_count[source].append((filepath, path))

        maximum = bound.get(KEY_MAXIMUM)

        if maximum is not None:
            for (source, list_at) in sorted(map_count.items()):
                if len(list_at) > maximum:
                    (filepath, path) = list_at[maximum]
                    out.append(_fault(filepath, path,
                            'An item holds at most {n} {rel} edge(s), and {name} holds '
                            '{held}.'.format(n = maximum, rel = id_relation,
                                             name = _name(map_declaration, source),
                                             held = len(list_at))))

        minimum = bound.get(KEY_MINIMUM)
        domain  = entry.get(KEY_DOMAIN)

        if minimum:
            for (id_self, location) in _iter_domain(context, domain, map_prefix):
                guid = map_declaration_guid(map_declaration, id_self)
                if len(map_count.get(guid, ())) < minimum:
                    out.append(_fault(location, KEY_RELATION,
                            '{name} holds {held} {rel} edge(s), and an item of its kind '
                            'holds at least {n}.'.format(
                                    name = id_self, held = len(map_count.get(guid, ())),
                                    rel = id_relation, n = minimum)))

    return out


# -----------------------------------------------------------------------------
def map_declaration_guid(map_declaration, id_self):
    """
    Return the guid a readable id declares, or None.

    """

    return next((guid for (guid, (_, name)) in map_declaration.items()
                 if name == id_self), None)


# -----------------------------------------------------------------------------
def _iter_domain(context, domain, map_prefix):
    """
    Yield (id_self, location) for every item whose type the domain
    names. An absent domain yields nothing, since a minimum without one
    is a claim about everything.

    """

    if not domain:
        return

    prefix = {p for (p, entry) in map_prefix.items()
              if isinstance(entry, dict) and entry.get(KEY_ID_SELF) in domain}

    for (location, document) in sorted(context.map_document.items(), key = str):
        for held in cc_public.item.iter_item(document, location):
            if held.id_self and held.id_self.split(SEPARATOR, 1)[0] in prefix:
                yield (held.id_self, location)


# -----------------------------------------------------------------------------
def _name(map_declaration, guid):
    """
    Return the readable id a guid declares, or the guid.

    """

    return map_declaration.get(guid, (None, guid))[1] or guid


# -----------------------------------------------------------------------------
def _type_of(identifier, map_prefix):
    """
    Return the type id an identifier's prefix names, or None.

    """

    if not isinstance(identifier, str) or SEPARATOR not in identifier:
        return None

    entry = map_prefix.get(identifier.split(SEPARATOR, 1)[0])

    return entry.get(KEY_ID_SELF) if isinstance(entry, dict) else None


# -----------------------------------------------------------------------------
def _list(list_type):
    """
    Return the types as prose: a, or a or b.

    """

    return ' or '.join(list_type)


# -----------------------------------------------------------------------------
def _fault(filepath, path, message):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_CRITICAL,
                message  = message)


# -----------------------------------------------------------------------------
def _question(filepath, path, message):
    """
    Return one advisory nonconformity: a question to the author rather
    than a fault.

    """

    return cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_ADVISORY,
                message  = message)
