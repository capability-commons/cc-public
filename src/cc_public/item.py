"""
---

id_self:                pym_cc_public.item
guid_self:              pym_7166309f54fc4dffb1b47a4d97c8a0d0
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Items of a tree
brief:                  |
                        Walk the documents of a tree for the items
                        they declare, and index them by readable id
                        and by guid.
description:            |
                        An item is a mapping declaring an identity. A
                        document is one, and it may hold others: a
                        register entry, a port, a question, an
                        interface member. One walk finds them all, and
                        carries what a caller needs beside each: where
                        it sits, the path within its document, and the
                        nearest item holding it.

                        Every module that walks the tree for the items
                        it declares reads this: the facts a query runs
                        over, the trace projection, the identifier
                        check and the tree loader through it. The tree
                        is walked one way, so what counts as an item
                        cannot differ by who is asking.
relation:               []

...
"""


import typing


KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_TABLE     = 'table'
DELIM         = '.'
SEPARATOR     = '_'


# -----------------------------------------------------------------------------
class Held(typing.NamedTuple):
    """
    One item, and where it was found.

    location is the document's location, which for an item held within
    another is the location of the document holding it. path is the
    dot path to it within that document, and is empty for the document
    itself. guid_holder is the nearest item holding it, and is None for
    the document itself.

    """

    id_self:     str
    guid_self:   str
    location:    typing.Any
    path:        str
    document:    dict
    guid_holder: str | None


# -----------------------------------------------------------------------------
class Index(typing.NamedTuple):
    """
    Every item of a tree, by readable id and by guid.

    """

    by_id:   dict
    by_guid: dict


# -----------------------------------------------------------------------------
def prefix_of(id_self):
    """
    Return the type prefix of a readable id: what stands before the
    first separator.

    """

    return str(id_self or '').split(SEPARATOR, 1)[0]


# -----------------------------------------------------------------------------
def is_type(document, prefix):
    """
    Return whether a document declares an identity of the type the
    prefix names.

    """

    return isinstance(document, dict) \
                and prefix_of(document.get(KEY_ID_SELF)) == prefix


# -----------------------------------------------------------------------------
def iter_entry(map_document, prefix):
    """
    Yield every entry of every register in the tree whose id carries
    the prefix.

    """

    for document in map_document.values():

        if not isinstance(document, dict) \
                or not isinstance(document.get(KEY_TABLE), dict):
            continue

        for entry in document[KEY_TABLE].values():
            if isinstance(entry, dict) \
                    and prefix_of(entry.get(KEY_ID_SELF)) == prefix:
                yield entry


# -----------------------------------------------------------------------------
def index(map_document):
    """
    Return an Index over every item the tree declares, the items held
    within another included.

    """

    by_id   = {}
    by_guid = {}

    for (location, document) in map_document.items():
        for held in iter_item(document, location):
            if held.id_self is not None:
                by_id[held.id_self] = held
            if held.guid_self is not None:
                by_guid[held.guid_self] = held

    return Index(by_id = by_id, by_guid = by_guid)


# -----------------------------------------------------------------------------
def iter_item(node, location = None, path = '', guid_holder = None):
    """
    Yield a Held for the node and for every item held anywhere within
    it, outermost first.

    """

    if isinstance(node, dict):

        if isinstance(node.get(KEY_ID_SELF), str) \
                or isinstance(node.get(KEY_GUID_SELF), str):

            yield Held(id_self     = node.get(KEY_ID_SELF),
                       guid_self   = node.get(KEY_GUID_SELF),
                       location    = location,
                       path        = path,
                       document    = node,
                       guid_holder = guid_holder)

            guid_holder = node.get(KEY_GUID_SELF) or guid_holder

        for (key, value) in node.items():
            yield from iter_item(value, location, _join(path, key), guid_holder)

    elif isinstance(node, list):

        for (position, value) in enumerate(node):
            yield from iter_item(value, location, _join(path, position), guid_holder)


# -----------------------------------------------------------------------------
def _join(path, step):
    """
    Return the path within a document, one step further down.

    """

    return '{path}{delim}{step}'.format(path = path, delim = DELIM,
                                        step = step) if path else str(step)
