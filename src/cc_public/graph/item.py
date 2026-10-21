"""
---

id_self:                pym_cc_public.graph.item
guid_self:              pym_09be959b84aa42e9a5ac1a9be9d2b463
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Items of the graph
brief:                  |
                        Read each item of the graph of data items with
                        its fields, references and primary edges, for
                        an export or a query to use.
description:            |
                        This module gives each item its type, its
                        holder, its file and line, the fields of its
                        own node that are scalars or lists of scalars,
                        the items it names in id_ and guid_ pairs, and
                        the primary edges from it. The type and the
                        primary edges are the derived predicates
                        has_type and primary_edge, computed by clingo
                        from derive.lp. It also words an edge as a
                        sentence, from the brief of its relation, and
                        finds the ids that prose mentions.
edge:                   []

...
"""


import pathlib
import typing

import cc_public.graph.logic
import cc_public.graph.extract


KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_TITLE         = 'title'
KEY_BRIEF         = 'brief'
PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
PREFIX_TYPE       = 'type_'
NAME_NO_TYPE      = 'Item'
MARK_SOURCE       = 'SOURCE'
MARK_TARGET       = 'TARGET'

# The fields of an edge, which are read as the edge and not as
# references.
#
SET_FIELD_EDGE    = {'relation', 'target'}

# The derived predicates an Item needs, computed by clingo from derive.lp,
# as every other program over the graph computes them.
#
TUPLE_DERIVED     = ('has_type', 'primary_edge')

Scalar            = str | int | float | bool


# -----------------------------------------------------------------------------
class Item(typing.NamedTuple):
    """
    One item of the graph, with what an export or a query needs of it.

    map_field holds each field of the item's own node whose value is a
    scalar, or a list of scalars, in the order the node writes them;
    the ids and guids of references are left out, since list_reference
    holds them. list_reference holds each (field, id) the item names
    in a pair of id_ and guid_ fields, and list_edge each (relation,
    target) of the primary edges from it, in order.

    """

    id:             str
    guid:           str
    type:           str
    holder:         str
    file:           str
    line:           int
    map_field:      dict[str, Scalar | list[Scalar]]
    list_reference: list[tuple[str, str]]
    list_edge:      list[tuple[str, str]]


# -----------------------------------------------------------------------------
def read(root: pathlib.Path) -> dict[str, Item]:
    """
    Return each item of the tree under root, keyed by id, in the order
    of the files that hold them.

    """

    map_document = cc_public.graph.extract.documents(root)

    return items(map_document, cc_public.graph.extract.facts_of(map_document))


# -----------------------------------------------------------------------------
def items(map_document: cc_public.graph.extract.Documents,
          facts:        cc_public.graph.extract.Facts) -> dict[str, Item]:
    """
    Return each item of map_document, whose facts are facts, keyed by
    id, in the order of the files that hold them.

    """

    map_derive   = cc_public.graph.logic.derived()
    rules        = ''.join(cc_public.graph.logic.show(name, map_derive)
                           for name in TUPLE_DERIVED)
    rows         = cc_public.graph.logic.run(facts, rules)
    map_type     = dict(rows['has_type'])
    map_node     = {}

    for (document, _) in map_document.values():
        if cc_public.graph.extract.is_document(document):
            _collect(document, map_node)

    map_edge = {}
    for (source, relation, target) in sorted(rows['primary_edge']):
        map_edge.setdefault(source, []).append((relation, target))

    map_reference = {}
    for (holder, field, id_item, _, _, _) in sorted(facts['reference'],
                                                       key = lambda row: (row[0], int(row[5]))):
        if field not in SET_FIELD_EDGE:
            map_reference.setdefault(holder, []).append((field, id_item))

    list_row = sorted(facts['item'], key = lambda row: (row[3], int(row[4])))

    return {id_item: Item(id             = id_item,
                          guid           = guid,
                          type           = map_type.get(id_item, ''),
                          holder         = holder,
                          file           = file,
                          line           = int(line),
                          map_field      = _fields(map_node.get(id_item, {})),
                          list_reference = map_reference.get(id_item, []),
                          list_edge      = map_edge.get(id_item, []))
            for (id_item, guid, holder, file, line) in list_row}


# -----------------------------------------------------------------------------
def title(map_item: dict[str, Item], id_item: str) -> str:
    """
    Return the title of the item id_item, or its id if it has none.

    """

    item = map_item.get(id_item)
    if item is None or not isinstance(item.map_field.get(KEY_TITLE), str):
        return id_item

    return item.map_field[KEY_TITLE].strip()


# -----------------------------------------------------------------------------
def type_name(map_item: dict[str, Item], id_type: str) -> str:
    """
    Return the name of the type id_type: its title without the word
    type, such as Annotation for type_annotation, or Item if id_type is
    empty.

    """

    if not id_type:
        return NAME_NO_TYPE

    return title(map_item, id_type).removesuffix(' type') or id_type


# -----------------------------------------------------------------------------
def folder(id_type: str) -> str:
    """
    Return the name of the folder an export puts the items of the type
    id_type in: the type id without its prefix, or other if it has no
    type.

    """

    return id_type.removeprefix(PREFIX_TYPE) or 'other'


# -----------------------------------------------------------------------------
def sentence(map_item:    dict[str, Item],
             relation:    str,
             text_source: str,
             text_target: str) -> str:
    """
    Return the sentence that an edge of relation states, from the brief
    of the relation, with SOURCE and TARGET replaced by text_source and
    text_target.
    Without such a brief, the sentence names the relation.

    """

    item  = map_item.get(relation)
    brief = item.map_field.get(KEY_BRIEF) if item else None

    if isinstance(brief, str) and MARK_SOURCE in brief and MARK_TARGET in brief:
        text = ' '.join(brief.split())
        text = text.replace(MARK_SOURCE, '\0').replace(MARK_TARGET, text_target)
        return text.replace('\0', text_source).rstrip('.') + '.'

    return '{source} {relation} {target}.'.format(source   = text_source,
                                                  relation  = relation,
                                                  target    = text_target)


# -----------------------------------------------------------------------------
def paragraphs(text: str) -> list[str]:
    """
    Return the paragraphs of the prose text, each on one line. Prose is
    written wrapped, and a blank line ends a paragraph.

    """

    return [' '.join(block.split()) for block in text.split('\n\n') if block.strip()]


# -----------------------------------------------------------------------------
def mentions(text: str, map_item: dict[str, Item], link: typing.Callable[[str], str]) -> str:
    """
    Return text with each id of an item in map_item that it mentions
    replaced by link of that id.

    """

    def _replace(match):
        id_item = match.group(0)
        return link(id_item) if id_item in map_item else id_item

    return cc_public.graph.extract.REGEX_MENTION.sub(_replace, text)


# -----------------------------------------------------------------------------
def _collect(node: typing.Any, map_node: dict[str, dict]) -> None:
    """
    Add to map_node the node of each item in node, keyed by its id.

    """

    if isinstance(node, list):
        for value in node:
            _collect(value, map_node)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)
    if isinstance(id_self, str):
        map_node[id_self] = node

    for value in node.values():
        _collect(value, map_node)


# -----------------------------------------------------------------------------
def _fields(node: dict) -> dict[str, Scalar | list[Scalar]]:
    """
    Return the fields of node whose value is a scalar or a list of
    scalars, other than its id and guid and the pairs of a reference.

    """

    map_field = {}

    for (key, value) in node.items():
        if key in (KEY_ID_SELF, KEY_GUID_SELF) or key.startswith((PREFIX_ID, PREFIX_GUID)):
            continue
        if _is_scalar(value):
            map_field[key] = _scalar(value)
        elif isinstance(value, list) and value and all(map(_is_scalar, value)):
            map_field[key] = [_scalar(each) for each in value]

    return map_field


# -----------------------------------------------------------------------------
def _is_scalar(value: typing.Any) -> bool:
    """
    Return True if value is text, a number or a truth value, or a value
    YAML reads that JSON has no type for, such as a date.

    """

    return value is not None and not isinstance(value, (dict, list))


# -----------------------------------------------------------------------------
def _scalar(value: typing.Any) -> Scalar:
    """
    Return value as text, a number or a truth value. Text loses the
    newline YAML ends a block with, and a date becomes text.

    """

    if isinstance(value, str):
        return str(value).rstrip()
    if isinstance(value, (bool, int, float)):
        return value

    return str(value)
