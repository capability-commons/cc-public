"""
---

id_self:                pym_cc_public.facts
guid_self:              pym_656182344c864fd28b265f23b0fe6527
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Facts
brief:                  |
                        What the tree states, as three tables: every
                        identity, every edge and every containment.
description:            |
                        Derives the facts of a tree from its documents
                        on every use: one item fact per identity with
                        its type prefix, status and location; one edge
                        fact per relation edge, source and target by
                        guid with the advisory id the edge carries;
                        one containment fact per embedded item and its
                        holder. The one source every query reads, so
                        that the projection, the walk and any engine
                        agree on what the graph is. Nothing stores the
                        result.
relation:               []

...
"""


import typing


KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_GUID_TGT  = 'guid_target'
KEY_ID_TGT    = 'id_target'
KEY_STATUS    = 'status'
SEPARATOR     = '_'


# -----------------------------------------------------------------------------
class Item(typing.NamedTuple):
    """
    One identity in the tree: what it is, where it is, and what state it
    says it is in. prefix is the type prefix of its readable id.

    """

    guid:     str
    id_self:  str
    prefix:   str
    status:   str | None
    location: str


# -----------------------------------------------------------------------------
class Edge(typing.NamedTuple):
    """
    One relation edge, from the item that holds it to the item it names.
    id_target is the advisory copy the edge carries; guid_target is what
    resolves.

    """

    guid_source: str
    id_relation: str
    guid_target: str
    id_target:   str | None


# -----------------------------------------------------------------------------
class Containment(typing.NamedTuple):
    """
    One embedded item and the item that holds it.

    """

    guid_holder: str
    guid_held:   str


# -----------------------------------------------------------------------------
class Facts(typing.NamedTuple):
    """
    What the tree states, as three tables: every identity, every edge,
    and every containment. Derived from the documents on every use;
    nothing stores it.

    """

    item:        tuple
    edge:        tuple
    containment: tuple


# -----------------------------------------------------------------------------
def facts(map_document):
    """
    ---

    id_self:                pyf_cc_public.facts.facts
    guid_self:              pyf_126d32e07e7b42d695331b7f091123f4
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Facts of the tree
    brief:                  |
                            Return the Facts of the tree: one Item per
                            identity, one Edge per relation edge, one
                            Containment per embedded item.
    description:            |
                            One Item per identity with its prefix, status
                            and location, one Edge per relation edge, one
                            Containment per embedded item and its holder,
                            derived from the documents on every use.
    relation:               []

    ...
    """

    list_item        = []
    list_edge        = []
    list_containment = []

    for (location, document) in sorted(map_document.items()):
        for (node, guid_holder) in _iter_identified(document, None):
            guid    = node[KEY_GUID_SELF]
            id_self = node.get(KEY_ID_SELF)
            list_item.append(Item(guid     = guid,
                                  id_self  = id_self,
                                  prefix   = str(id_self or '').split(SEPARATOR, 1)[0],
                                  status   = node.get(KEY_STATUS)
                                             if isinstance(node.get(KEY_STATUS), str) else None,
                                  location = str(location)))
            for edge in node.get(KEY_RELATION) or []:
                if isinstance(edge, dict) and isinstance(edge.get(KEY_GUID_TGT), str):
                    list_edge.append(Edge(guid_source = guid,
                                          id_relation = edge.get(KEY_ID_REL),
                                          guid_target = edge[KEY_GUID_TGT],
                                          id_target   = edge.get(KEY_ID_TGT)))
            if guid_holder is not None:
                list_containment.append(Containment(guid_holder = guid_holder,
                                                    guid_held   = guid))

    return Facts(item        = tuple(list_item),
                 edge        = tuple(list_edge),
                 containment = tuple(list_containment))


# -----------------------------------------------------------------------------
def _iter_identified(node, guid_holder):
    """
    Yield (mapping, guid of the nearest identified holder) for every
    mapping in node that declares a guid, outermost first.

    """

    if isinstance(node, dict):
        guid = node.get(KEY_GUID_SELF)
        if isinstance(guid, str):
            yield (node, guid_holder)
            guid_holder = guid
        for value in node.values():
            yield from _iter_identified(value, guid_holder)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_identified(value, guid_holder)
