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
                        of thing its relation allows.
description:            |
                        A relation entry may constrain the types at
                        its two ends and forbid cycles. An edge that
                        breaks a constraint is a critical fault at the
                        edge, and a constraint naming a type that does
                        not exist is a fault at the entry. A target
                        that does not resolve is left to the reference
                        check. An absent constraint says nothing.

...
"""


import collections

import cc_public.check.reference
import cc_public.check.register
import cc_public.check.result
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

    list_bad  = _bad_constraint(filepath_register, table, set_type)
    map_graph = collections.defaultdict(list)
    count     = 0

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

            if entry.get(KEY_ACYCLIC):
                map_graph[edge.get(KEY_ID_REL)].append(
                        (holder.get(KEY_GUID_SELF), edge.get(KEY_GUID_TGT),
                         filepath, path))

    for (id_relation, list_edge) in sorted(map_graph.items()):
        list_bad.extend(_cycle(id_relation, list_edge, map_declaration))

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
    Return a fault for each constraint naming a type that is not one.

    """

    out = []

    for (key_entry, entry) in sorted(table.items()):
        if not isinstance(entry, dict):
            continue
        for key in (KEY_DOMAIN, KEY_RANGE):
            for id_type in entry.get(key) or []:
                if id_type not in set_type:
                    out.append(_fault(filepath,
                            cc_public.path.join(cc_public.path.join(KEY_TABLE, key_entry), key),
                            'Names {id_type}, which is not a type in the type '
                            'register, so nothing could satisfy it.'.format(
                                                            id_type = id_type)))

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
