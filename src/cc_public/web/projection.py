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
                        What a page shows, as plain values read from
                        the tree: the index of items, and one item
                        with its fields, their descriptions, and its
                        edges.
description:            |
                        Three functions. kinds counts the items of
                        each type, named by the type register. listing
                        selects items by type and by a query over
                        identifier, title and brief. detail returns
                        one item: its identity and type, where it
                        sits, every field it holds other than
                        identity, rights and edges, each labelled by
                        its key and described by the property
                        description its schema gives, held as prose,
                        as a datum laid out as YAML, or as links to
                        the items held within it, and the edges it
                        holds and the edges that name it, from the
                        trace neighbourhood. A page renders what these
                        return and asks the tree for nothing else.
relation:               []

...
"""


import io
import typing

import ruamel.yaml

import cc_public.check.register
import cc_public.check.schema
import cc_public.item
import cc_public.trace


KEY_TITLE           = 'title'
KEY_BRIEF           = 'brief'
KEY_ID_SELF         = 'id_self'
KEY_GUID_SELF       = 'guid_self'
KEYWORD_PROPERTIES  = 'properties'
KEYWORD_REF         = '$ref'
KEYWORD_DESCRIPTION = 'description'
SUFFIX_SCHEMA       = '.yaml'

# What the heading and the edges show, so the fields do not show it
# again.
#
KEY_NOT_A_FIELD = ('id_self', 'guid_self', 'copyright', 'license',
                   'protective_mark', 'relation')

KIND_PROSE  = 'prose'    # text with a line break in it, shown as paragraphs
KIND_DATUM  = 'datum'    # a scalar, or a structure laid out as yaml
KIND_HELD   = 'held'     # a structure holding items, shown as links


# -----------------------------------------------------------------------------
class Kind(typing.NamedTuple):
    """
    One type of item, and how many the tree holds.

    """

    prefix: str
    title:  str
    count:  int


# -----------------------------------------------------------------------------
class Entry(typing.NamedTuple):
    """
    One item as a listing shows it.

    """

    id_self:   str
    guid_self: str
    prefix:    str
    title:     str | None
    brief:     str | None


# -----------------------------------------------------------------------------
class Listing(typing.NamedTuple):
    """
    What a listing shows: the kinds, the entries selected, and how the
    selection was made.

    """

    kinds:   tuple
    entries: tuple
    query:   str
    prefix:  str | None
    total:   int


# -----------------------------------------------------------------------------
class Field(typing.NamedTuple):
    """
    One field of an item: its key, what its schema says of it, and its
    value by kind. A held value is a tuple of (id_self, title) pairs.

    """

    key:   str
    help:  str | None
    kind:  str
    value: typing.Any


# -----------------------------------------------------------------------------
class Detail(typing.NamedTuple):
    """
    One item in full.

    """

    id_self:    str
    guid_self:  str
    prefix:     str
    kind:       str
    title:      str | None
    location:   str
    path:       str
    fields:     tuple
    outgoing:   tuple
    incoming:   tuple


# -----------------------------------------------------------------------------
def kinds(tree):
    """
    Return one Kind per type prefix the tree holds items of, in the
    order of the type register, with types nothing is of left out.

    """

    map_prefix = _map_prefix(tree)
    count      = {}

    for held in cc_public.item.index(tree.context.map_document).by_id.values():
        prefix = cc_public.item.prefix_of(held.id_self)
        count[prefix] = count.get(prefix, 0) + 1

    return tuple(Kind(prefix = prefix,
                      title  = str(entry.get(KEY_TITLE) or prefix),
                      count  = count[prefix])
                 for (prefix, entry) in map_prefix.items() if prefix in count)


# -----------------------------------------------------------------------------
def listing(tree, query = '', prefix = None, limit = 200):
    """
    Return the Listing of items whose identifier, title or brief holds
    every word of the query, of the type the prefix names where one
    is given, at most limit of them, in identifier order.

    """

    list_word = query.lower().split()
    selected  = []

    for held in sorted(cc_public.item.index(tree.context.map_document).by_id.values(),
                       key = lambda held: held.id_self):
        entry = _entry(held)
        if prefix is not None and entry.prefix != prefix:
            continue
        text = ' '.join(filter(None, (entry.id_self, entry.title, entry.brief))).lower()
        if all(word in text for word in list_word):
            selected.append(entry)

    return Listing(kinds   = kinds(tree),
                   entries = tuple(selected[:limit]),
                   query   = query,
                   prefix  = prefix,
                   total   = len(selected))


# -----------------------------------------------------------------------------
def detail(tree, name):
    """
    Return the Detail of the item a readable id or a guid names, or
    None where nothing is named so.

    """

    index = cc_public.item.index(tree.context.map_document)
    held  = index.by_id.get(name) or index.by_guid.get(name)

    if held is None:
        return None

    map_prefix    = _map_prefix(tree)
    prefix        = cc_public.item.prefix_of(held.id_self)
    map_help      = _help(held, map_prefix, tree)
    neighbourhood = cc_public.trace.neighbourhood(tree.context.map_document, held.guid_self)

    return Detail(id_self   = held.id_self,
                  guid_self = held.guid_self,
                  prefix    = prefix,
                  kind      = str((map_prefix.get(prefix) or {}).get(KEY_TITLE) or prefix),
                  title     = _line(held.document.get(KEY_TITLE)),
                  location  = str(held.location),
                  path      = held.path,
                  fields    = tuple(_field(key, value, map_help.get(key), index)
                                    for (key, value) in held.document.items()
                                    if  key not in KEY_NOT_A_FIELD),
                  outgoing  = neighbourhood.outgoing if neighbourhood else (),
                  incoming  = neighbourhood.incoming if neighbourhood else ())


# -----------------------------------------------------------------------------
def _entry(held):
    return Entry(id_self   = held.id_self,
                 guid_self = held.guid_self,
                 prefix    = cc_public.item.prefix_of(held.id_self),
                 title     = _line(held.document.get(KEY_TITLE)),
                 brief     = _line(held.document.get(KEY_BRIEF)))


# -----------------------------------------------------------------------------
def _field(key, value, help_, index):
    """
    Return the Field for one key of a document, its value by kind.

    """

    list_held = [(one.id_self, _line(one.document.get(KEY_TITLE)))
                 for one in cc_public.item.iter_item(value)
                 if  one.id_self is not None and one.id_self in index.by_id]

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
def _help(held, map_prefix, tree):
    """
    Return a key to description map from the schema the item's type
    names, through every schema it composes; empty where it names none.

    """

    map_schema            = cc_public.check.schema.map_schema(tree.context.map_document)
    (id_schema, _reason)  = cc_public.check.schema.select_schema(
                                        held.document, map_prefix,
                                        is_embedded = bool(held.path))
    return _described(map_schema.get(id_schema), map_schema, set())


# -----------------------------------------------------------------------------
def _described(node, map_schema, seen):
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
def _map_prefix(tree):
    return cc_public.check.register.map_prefix(tree.type_register())


# -----------------------------------------------------------------------------
def _line(value):
    """
    Return a value as one line of text, or None where there is none.

    """

    if value is None:
        return None

    return ' '.join(str(value).split()) or None
