"""
---

id_self:                pym_cc_public.web.projection
guid_self:              pym_4648b41ae68b48fbad5110a0305834a7
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Projections
brief:                  |
                        The graph indexed for navigation, the views
                        the tree holds, and what a row shows at each
                        of the three levels it discloses.
description:            |
                        The graph function indexes a reading of the
                        tree once: every item by both of its names and
                        every edge reachable from either end, because
                        a view walks it on every expansion. The views
                        function returns the view items. The roots
                        function returns the rows at the first level
                        of a view, of the types it names, in the order
                        it asks for, narrowed by text. The opened
                        function returns the children of a row,
                        grouped by the relation that reached them,
                        refusing any item already on the path from the
                        root so that a branch cannot re-enter itself.
                        The record function returns one item read in
                        full, each field labelled by its key and
                        described by the property description its
                        schema gives. Nothing here renders and nothing
                        writes.
relation:               []

...
"""


import io
import typing

import ruamel.yaml

import cc_public.check.register
import cc_public.check.schema
import cc_public.facts
import cc_public.item


KEY_TITLE       = 'title'
KEY_BRIEF       = 'brief'
KEY_DESCRIPTION = 'description'
KEY_TABLE       = 'table'
KEY_PREFIX      = 'prefix'
KEY_ROOT        = 'root'
KEY_TRAVERSAL   = 'traversal'
KEY_TYPE        = 'type'
KEY_SORT        = 'sort'
KEY_ID_TYPE     = 'id_type'
KEY_ID_TERM     = 'id_term'
KEY_TERM        = 'term'
KEY_ID_RELATION = 'id_relation'
KEY_DIRECTION   = 'direction'

KEYWORD_PROPERTIES  = 'properties'
KEYWORD_REF         = '$ref'
KEYWORD_DESCRIPTION = 'description'
SUFFIX_SCHEMA       = '.yaml'

PREFIX_VIEW     = 'vw'
PREFIX_RELATION = 'r'

# Most entries of the relation register are titled after the item, as
# Decides relation, where a label wants the edge, as decides.
#
SUFFIX_RELATION = ' relation'

HOLDS         = 'holds'
POINTED_AT_BY = 'pointed_at_by'

SORT_IDENTIFIER = 'identifier'

# Shown by the heading or carried by the tree, so the record does not
# repeat them.
#
KEY_NOT_A_FIELD = ('id_self', 'guid_self', 'copyright', 'license',
                   'protective_mark', 'title', 'brief', 'relation')

KIND_PROSE = 'prose'    # text with a blank line in it, shown as paragraphs
KIND_DATUM = 'datum'    # a scalar, or a structure laid out as yaml
KIND_HELD  = 'held'     # a structure holding items, shown as links


# -----------------------------------------------------------------------------
class Graph(typing.NamedTuple):
    """
    The tree indexed for navigation: every item by both of its names,
    and every edge reachable from either end.

    Built once for a reading of the tree, because a view walks it on
    every expansion and deriving the facts each time would be paid for
    at every keystroke.

    """

    by_id:      dict[str, typing.Any]
    by_guid:    dict[str, typing.Any]
    out:        dict[str, list[tuple[str, str]]]
    inbound:    dict[str, list[tuple[str, str]]]
    map_prefix: dict[str, typing.Any]
    map_schema: dict[str, typing.Any]
    map_type:   dict[str, typing.Any]
    map_term:   dict[str, str]


# -----------------------------------------------------------------------------
class Walk(typing.NamedTuple):
    """
    One entry of a traversal list: a relation and which way it is read.

    """

    id_relation: str
    direction:   str
    label:       str


# -----------------------------------------------------------------------------
class View(typing.NamedTuple):
    """
    A view item as the renderer needs it: what sits at the root, and
    which edges are followed to find the children of a row.

    """

    id_self:   str
    title:     str
    brief:     str | None
    prefix:    tuple[str, ...]
    sort:      str
    traversal: tuple[Walk, ...]


# -----------------------------------------------------------------------------
class Row(typing.NamedTuple):
    """
    One item at one place in the tree. path is every guid from the root
    to this item, which is what stops a branch re-entering itself.

    """

    id_self:   str
    guid_self: str
    prefix:    str
    kind:      str
    title:     str
    brief:     str | None
    path:      tuple[str, ...]
    has_child: bool


# -----------------------------------------------------------------------------
class Group(typing.NamedTuple):
    """
    The children one traversal found, under the label it was reached by.

    """

    label: str
    rows:  tuple[Row, ...]


# -----------------------------------------------------------------------------
class Opened(typing.NamedTuple):
    """
    The children a row has, grouped by the relation that reached them.

    """

    groups: tuple[Group, ...]


# -----------------------------------------------------------------------------
class Field(typing.NamedTuple):
    """
    One field of a record: its key, what its schema says of it, and its
    value by kind. A held value is a tuple of (id_self, title) pairs.

    """

    key:   str
    help:  str | None
    kind:  str
    value: typing.Any


# -----------------------------------------------------------------------------
class Record(typing.NamedTuple):
    """
    One item read in full: what the type adds to the envelope, and
    where it sits.

    """

    id_self:   str
    guid_self: str
    kind:      str
    location:  str
    fields:    tuple[Field, ...]


# -----------------------------------------------------------------------------
def graph(tree: typing.Any) -> Graph:
    """
    Return the Graph of a tree, indexed for navigation.

    """

    index = cc_public.item.index(tree.context.map_document)
    facts = cc_public.facts.facts(tree.context.map_document)

    out     = {}
    inbound = {}

    for edge in facts.edge:
        out.setdefault(edge.guid_source, []).append((edge.id_relation, edge.guid_target))
        inbound.setdefault(edge.guid_target, []).append((edge.id_relation, edge.guid_source))

    map_prefix = cc_public.check.register.map_prefix(tree.type_register())
    map_type   = {entry[KEY_PREFIX]: entry for entry in map_prefix.values()}

    # What a kind is called comes from the glossary the type names,
    # because the type item is called Need type and the thing itself is
    # called a need.
    #
    map_term = {}
    for (prefix, entry) in map_type.items():
        held = index.by_id.get(entry.get(KEY_ID_TERM))
        term = (held.document.get(KEY_TERM) if held else None) \
               or _line(entry.get(KEY_TITLE)) or prefix
        map_term[prefix] = str(term)

    return Graph(by_id      = index.by_id,
                 by_guid    = index.by_guid,
                 out        = out,
                 inbound    = inbound,
                 map_prefix = map_prefix,
                 map_schema = cc_public.check.schema.map_schema(tree.context.map_document),
                 map_type   = map_type,
                 map_term   = map_term)


# -----------------------------------------------------------------------------
def views(graph_: Graph) -> tuple[View, ...]:
    """
    Return every view the tree holds, in identifier order.

    """

    return tuple(_view(graph_, held)
                 for (id_self, held) in sorted(graph_.by_id.items())
                 if  cc_public.item.prefix_of(id_self) == PREFIX_VIEW)


# -----------------------------------------------------------------------------
def roots(graph_: Graph, view: View, text: str = '') -> tuple[Row, ...]:
    """
    Return the rows at the first level of a view: every item of a type
    the view names, in the order the view asks for, narrowed to those
    holding every word of text.

    """

    list_word = text.lower().split()
    found     = []

    for (id_self, held) in graph_.by_id.items():
        if cc_public.item.prefix_of(id_self) not in view.prefix:
            continue
        row      = _row(graph_, held.guid_self, (held.guid_self,), view)
        haystack = ' '.join(filter(None, (row.id_self, row.title))).lower()
        if all(word in haystack for word in list_word):
            found.append(row)

    key = (lambda row: row.id_self) if view.sort == SORT_IDENTIFIER \
          else (lambda row: (row.title.lower(), row.id_self))

    return tuple(sorted(found, key = key))


# -----------------------------------------------------------------------------
def opened(graph_: Graph, view: View, path: tuple[str, ...]) -> Opened | None:
    """
    Return what the row at the end of path shows when it opens: its
    brief, and one Group per traversal that found anything.

    An item already on the path is not entered again, so a branch
    cannot re-enter itself. The same item may still appear in another
    branch.

    """

    held   = graph_.by_guid.get(path[-1])
    groups = []

    if held is None:
        return None

    for walk in view.traversal:
        reached = graph_.out if walk.direction == HOLDS else graph_.inbound
        rows    = tuple(_row(graph_, guid, path + (guid,), view)
                        for (id_relation, guid) in reached.get(path[-1], ())
                        if  id_relation == walk.id_relation
                        and guid not in path
                        and guid in graph_.by_guid)
        if rows:
            groups.append(Group(label = walk.label,
                                rows  = tuple(sorted(rows, key = lambda row: row.id_self))))

    return Opened(groups = tuple(groups))


# -----------------------------------------------------------------------------
def record(graph_: Graph, name: str) -> Record | None:
    """
    Return the Record of the item a readable id or a guid names, read
    in full, or None where nothing is named so.

    """

    held = graph_.by_id.get(name) or graph_.by_guid.get(name)

    if held is None:
        return None

    map_help = _help(graph_, held)

    return Record(id_self   = held.id_self,
                  guid_self = held.guid_self,
                  kind      = _kind(graph_, held.id_self),
                  location  = str(held.location),
                  fields    = tuple(_field(key, value, map_help.get(key), graph_)
                                    for (key, value) in held.document.items()
                                    if  key not in KEY_NOT_A_FIELD))


# -----------------------------------------------------------------------------
def _view(graph_: Graph, held: typing.Any) -> View:
    document = held.document
    root     = document.get(KEY_ROOT) or {}

    prefix = tuple(_prefix_of_type(graph_, one.get(KEY_ID_TYPE))
                   for one in root.get(KEY_TYPE) or ())

    return View(id_self   = held.id_self,
                title     = _line(held.document.get(KEY_TITLE)) or held.id_self,
                brief     = _line(held.document.get(KEY_BRIEF)),
                prefix    = tuple(p for p in prefix if p is not None),
                sort      = root.get(KEY_SORT) or SORT_IDENTIFIER,
                traversal = tuple(_walk(graph_, one)
                                  for one in document.get(KEY_TRAVERSAL) or ()))


# -----------------------------------------------------------------------------
def _walk(graph_: Graph, entry: typing.Mapping[str, typing.Any]) -> Walk:
    """
    Return the Walk one traversal entry describes, labelled from the
    relation register.

    Nothing infers an inverse, so a backward walk is labelled by the
    forward relation and the direction it is read in. That reads
    awkwardly and says exactly what it does; ddr_view defers the
    inverse to the work that adds one to the register.

    """

    id_relation = str(entry.get(KEY_ID_RELATION) or '')
    direction   = str(entry.get(KEY_DIRECTION) or HOLDS)
    held        = graph_.by_id.get(id_relation)
    title       = _line((held.document if held else {}).get(KEY_TITLE)) or id_relation
    edge        = title.removesuffix(SUFFIX_RELATION).lower()

    return Walk(id_relation = id_relation,
                direction   = direction,
                label       = edge if direction == HOLDS else 'pointed at by ' + edge)


# -----------------------------------------------------------------------------
def _row(graph_: Graph, guid: str, path: tuple[str, ...], view: View) -> Row:
    held    = graph_.by_guid[guid]
    id_self = held.id_self

    return Row(id_self   = id_self,
               guid_self = guid,
               prefix    = cc_public.item.prefix_of(id_self),
               kind      = _kind(graph_, id_self),
               title     = _line(held.document.get(KEY_TITLE)) or id_self,
               brief     = _line(held.document.get(KEY_BRIEF)),
               path      = path,
               has_child = _has_child(graph_, guid, path, view))


# -----------------------------------------------------------------------------
def _has_child(graph_: Graph, guid: str, path: tuple[str, ...], view: View) -> bool:
    """
    Return whether opening this row would find anything, so that a row
    can say it has more beneath it without being opened.

    """

    for walk in view.traversal:
        reached = graph_.out if walk.direction == HOLDS else graph_.inbound
        for (id_relation, other) in reached.get(guid, ()):
            if  id_relation == walk.id_relation \
                    and other not in path and other in graph_.by_guid:
                return True

    return False


# -----------------------------------------------------------------------------
def _kind(graph_: Graph, id_self: str) -> str:
    prefix = cc_public.item.prefix_of(id_self)
    return graph_.map_term.get(prefix, prefix)


# -----------------------------------------------------------------------------
def _prefix_of_type(graph_: Graph, id_type: object) -> str | None:
    for (prefix, entry) in graph_.map_type.items():
        if entry.get('id_self') == id_type:
            return prefix
    return None


# -----------------------------------------------------------------------------
def _field(key: str, value: typing.Any, help_: str | None, graph_: Graph) -> Field:
    """
    Return the Field for one key of a document, its value by kind.

    """

    list_held = [(one.id_self, _line(one.document.get(KEY_TITLE)))
                 for one in cc_public.item.iter_item(value)
                 if  one.id_self is not None and one.id_self in graph_.by_id]

    if list_held:
        return Field(key = key, help = help_, kind = KIND_HELD, value = tuple(list_held))

    if isinstance(value, str) and '\n' in value.strip():
        return Field(key = key, help = help_, kind = KIND_PROSE, value = value)

    if isinstance(value, (dict, list)):
        stream = io.StringIO()
        ruamel.yaml.YAML(typ = 'rt').dump(value, stream)
        return Field(key = key, help = help_, kind = KIND_DATUM, value = stream.getvalue())

    return Field(key = key, help = help_, kind = KIND_DATUM, value = _line(value))


# -----------------------------------------------------------------------------
def _help(graph_: Graph, held: typing.Any) -> dict[str, str | None]:
    """
    Return a key to description map from the schema the item's type
    names, through every schema it composes; empty where it names none.

    """

    (id_schema, _reason) = cc_public.check.schema.select_schema(
                                    held.document, graph_.map_prefix,
                                    is_embedded = bool(held.path))
    return _described(graph_.map_schema.get(id_schema), graph_.map_schema, set())


# -----------------------------------------------------------------------------
def _described(node:       typing.Any,
               map_schema: dict[str, typing.Any],
               seen:       set[str]) -> dict[str, str | None]:
    """
    Return every property name a schema declares with its description,
    anywhere in it and in the schemas it refers to.

    """

    out = {}

    if isinstance(node, list):
        for one in node:
            out.update(_described(one, map_schema, seen))
        return out

    if not isinstance(node, dict):
        return out

    for (key, value) in node.items():

        if key == KEYWORD_PROPERTIES and isinstance(value, dict):
            for (name, subschema) in value.items():
                if isinstance(subschema, dict) and name not in out:
                    out[name] = _line(subschema.get(KEYWORD_DESCRIPTION))
        elif key == KEYWORD_REF and isinstance(value, str) and value not in seen:
            seen.add(value)
            out.update(_described(map_schema.get(value.rsplit('/', 1)[-1]
                                                      .removesuffix(SUFFIX_SCHEMA)),
                                  map_schema, seen))
        else:
            out.update(_described(value, map_schema, seen))

    return out


# -----------------------------------------------------------------------------
def _line(value: object) -> str | None:
    """
    Return a value as one line of text, or None where there is none.

    """

    if value is None:
        return None

    return ' '.join(str(value).split()) or None
