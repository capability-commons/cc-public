"""
---

id_self:                pym_cc_public.edit.edit
guid_self:              pym_91cd5af6b2164bd483c8422e09416896
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Edit
brief:                  |
                        Edit the data items in a tree, and keep only
                        the edits that add no failure.
description:            |
                        An edit is a set of new texts for files, in
                        which None removes a file. new, header, link,
                        unlink, set_field, unset_field, remove and
                        rename each return one, written as small
                        changes to the text, after which the file is
                        laid out by pym_cc_public.edit.layout. A tree
                        holds the edits made so far, and each edit is
                        made on top of them. apply checks the tree
                        with the edits in place, and writes them only
                        if they add no failure to those the tree
                        already has.

                        batch makes a list of operations in one go, so
                        that items that need each other, such as a
                        concept and the item that names it, are made
                        together.
usage:                  |
                        Called by the commands of
                        pym_cc_public.cli.editing.
relation:               []

...
"""


import ast
import collections
import pathlib
import re
import typing
import uuid

import ruamel.yaml

import cc_public.check.check
import cc_public.edit.layout
import cc_public.graph.extract


KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_RELATION      = 'relation'
KEY_ALIAS         = 'alias'
KEY_TABLE         = 'table'
KEY_ID_RELATION   = 'id_relation'
KEY_GUID_RELATION = 'guid_relation'
KEY_ID_TARGET     = 'id_target'
KEY_GUID_TARGET   = 'guid_target'
KEY_NEW           = 'new'
KEY_HEADER        = 'header'
KEY_ID            = 'id'
KEY_FIELD         = 'field'
KEY_LINK          = 'link'
KEY_UNLINK        = 'unlink'
KEY_SET           = 'set'
KEY_UNSET         = 'unset'
KEY_REMOVE        = 'remove'
KEY_RENAME        = 'rename'
COLUMN_LINE       = 'line'

# The descriptive fields, in the order they are written. A new field
# that is not one of them goes after them.
#
TUPLE_KEY_PROSE   = ('title', 'brief', 'description', 'usage', 'note')

# A schema opens with the fields that name its dialect and itself,
# before its identity.
#
TUPLE_KEY_LEAD    = ('$schema', '$id')

# Fields that set_field does not change: identity is fixed, and edges
# and aliases are lists that other commands keep.
#
SET_KEY_FIXED     = {KEY_ID_SELF, KEY_GUID_SELF, KEY_RELATION, KEY_ALIAS}

# A standalone item takes its rights from the item of the project.
#
ID_RIGHTS         = 'file_pyproject'
TUPLE_KEY_RIGHTS  = ('copyright', 'license', 'protective_mark')

# A type is held in a register when it has this edge to one. A type
# with one of these prefixes has its items in source files, where the
# name of the file gives the id, so new does not make them.
#
ID_HELD           = 'r_has_items_held_in_register'
SET_PREFIX_SOURCE = {'pym', 'pyp', 'dls', 'file'}

# A file of any other type takes its item in a header: a python module
# in its module docstring, and any other file in a comment header. A
# YAML file is a document already, and JSON and Markdown have no
# comment for a header.
#
SET_SUFFIX_BARE   = {'.yaml', '.json', '.md'}
QUOTE_DOCSTRING   = '"""'

DIR_DATA          = '_data'
SUFFIX_YAML       = '.yaml'
LENGTH_BANNER     = 79
DELIM_PREFIX      = '_'
PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
MARK_COMMENT      = '#'
DELIM_PATH        = '.'

# An id as a word of its own, and as the name of a file: not inside a
# longer id, and not part of a dotted name.
#
PATTERN_WHOLE_ID  = r'(?<![A-Za-z0-9_$.-]){id}(?![A-Za-z0-9_])'

Edit              = dict[str, str | None]
YAML              = ruamel.yaml.YAML(typ = 'rt')


# -----------------------------------------------------------------------------
class ErrorEdit(Exception):
    """
    The edit asked for cannot be made. The message says why.

    """


# -----------------------------------------------------------------------------
class Tree:
    """
    The documents of a tree and the facts they hold, read once for an
    edit, with the texts of the edits made so far in place of those
    they change.

    """

    # -------------------------------------------------------------------------
    def __init__(self, root: pathlib.Path) -> None:
        """
        Read the tree under root.

        """

        self.root         = root
        self.map_original = cc_public.graph.extract.documents(root)
        self.map_document = dict(self.map_original)
        self.edit         = {}
        self._index()

    # -------------------------------------------------------------------------
    def update(self, edit: Edit) -> None:
        """
        Put the texts of edit in place, so that a later edit is made on
        top of it.

        """

        for (relative, text) in edit.items():
            if text is None:
                self.map_document.pop(relative, None)
                self.edit[relative] = None
                continue
            try:
                self.map_document[relative] = cc_public.graph.extract.parse(
                                                            text, pathlib.Path(relative))
            except ruamel.yaml.YAMLError as error:
                raise ErrorEdit('The edit leaves {file} unreadable: {error}'.format(
                                                    file = relative, error = error)) from error
            self.edit[relative] = text

        self._index()

    # -------------------------------------------------------------------------
    def _index(self) -> None:
        """
        Find the facts of the documents, and index the items by id.

        """

        self.facts    = cc_public.graph.extract.facts_of(self.map_document)
        self.map_item = {row[0]: row for row in self.facts['item']}

    # -------------------------------------------------------------------------
    def guid(self, id_item: str) -> str:
        """
        Return the guid of the item id_item.

        """

        if id_item not in self.map_item:
            raise ErrorEdit('No item has the id {id}.'.format(id = id_item))
        return self.map_item[id_item][1]

    # -------------------------------------------------------------------------
    def text(self, relative: str) -> str:
        """
        Return the text of the file at relative.

        """

        if relative in self.edit and self.edit[relative] is None:
            raise ErrorEdit('The file {file} is removed.'.format(file = relative))

        if relative in self.edit:
            return self.edit[relative]
        return (self.root / relative).read_text(encoding = 'utf-8')


# -----------------------------------------------------------------------------
def new(tree:       Tree,
        id_self:    str,
        list_field: list[tuple[str, typing.Any]],
        list_link:  list[tuple[str, str]]) -> Edit:
    """
    Return the edit that makes a new item with id_self, the fields in
    list_field, and an edge for each relation and target in list_link.
    A type held in a register gets an entry at the end of the table of
    its register. Any other gets a file of its own under _data.

    """

    (prefix, _, _) = id_self.partition(DELIM_PREFIX)
    map_type       = {row[1]: row[0] for row in tree.facts['type_prefix']}

    if prefix not in map_type:
        raise ErrorEdit('No type has the prefix {prefix}.'.format(prefix = prefix))
    if prefix in SET_PREFIX_SOURCE:
        raise ErrorEdit('An item of {type} is written in the file it names: give the file '
                        'its item with header.'.format(type = map_type[prefix]))

    id_type   = map_type[prefix]
    register  = _register(tree, id_type)
    map_field = _fields(tree, id_self, list_field, list_link, register)

    if register is None:
        relative = '{dir}/{stem}/{id}{suffix}'.format(dir    = DIR_DATA,
                                                      stem   = id_type[2:],
                                                      id     = id_self,
                                                      suffix = SUFFIX_YAML)
        if relative in tree.map_document:
            raise ErrorEdit('The file {file} exists.'.format(file = relative))
        text = '\n'.join(cc_public.edit.layout.dump(map_field, 0)) + '\n'
        return {relative: _format(text, relative)}

    return _append_entry(tree, register, map_field)


# -----------------------------------------------------------------------------
def header(tree:       Tree,
           relative:   str,
           id_self:    str | None,
           list_field: list[tuple[str, typing.Any]],
           list_link:  list[tuple[str, str]]) -> Edit:
    """
    Return the edit that gives the file at relative a new item, at its
    head: in its module docstring if it is a python module, and in a
    comment header if not, after any line that names an interpreter.
    The file is made if there is none.

    The id of a python module or Datalog source file follows from its
    path, so id_self may be None for one. Any other file needs it.

    """

    path = pathlib.Path(relative)

    if path.suffix in SET_SUFFIX_BARE:
        raise ErrorEdit('{file} cannot hold a header.'.format(file = relative))

    if path.suffix in cc_public.graph.extract.MAP_PREFIX_MODULE:
        expected = cc_public.graph.extract.module_name(path)
        if id_self not in (None, expected):
            raise ErrorEdit('The item of {file} has the id {expected}, not {id}.'.format(
                                                file = relative, expected = expected, id = id_self))
        id_self = expected
    elif id_self is None:
        raise ErrorEdit('Give the id of the item of {file}.'.format(file = relative))

    if relative in tree.map_document and tree.map_document[relative][0] is not None:
        raise ErrorEdit('{file} already holds an item.'.format(file = relative))

    (prefix, _, _) = id_self.partition(DELIM_PREFIX)
    if prefix not in {row[1] for row in tree.facts['type_prefix']}:
        raise ErrorEdit('No type has the prefix {prefix}.'.format(prefix = prefix))

    map_field = _fields(tree, id_self, list_field, list_link, None)
    list_doc  = [cc_public.graph.extract.LINE_OPEN, '',
                 *cc_public.edit.layout.dump(map_field, 0),
                 '', cc_public.graph.extract.LINE_CLOSE]
    text      = tree.text(relative) if relative in tree.map_document else ''
    list_line = text.split('\n') if text else []
    list_head = []

    if list_line and list_line[0].startswith(cc_public.graph.extract.MARK_SHEBANG):
        list_head = [list_line.pop(0)]
    while list_line and not list_line[0].strip():
        list_line.pop(0)

    if path.suffix == cc_public.graph.extract.SUFFIX_PYTHON:
        _refuse_docstring(text, relative)
        list_new = [QUOTE_DOCSTRING, *list_doc, QUOTE_DOCSTRING]
    else:
        mark     = cc_public.graph.extract.mark_comment(path)
        list_new = [mark + (' ' + line if line else '') for line in list_doc]

    list_new = [*list_head, *list_new, *(['', '', *list_line] if list_line else [''])]

    return {relative: _format('\n'.join(list_new), relative)}


# -----------------------------------------------------------------------------
def _refuse_docstring(text: str, relative: str) -> None:
    """
    Refuse a python module that cannot be parsed, or that has a module
    docstring already, which the item would take the place of.

    """

    try:
        module = ast.parse(text)
    except SyntaxError as error:
        raise ErrorEdit('{file} is not python: {error}'.format(
                                                file = relative, error = error)) from error

    if ast.get_docstring(module) is not None:
        raise ErrorEdit('{file} has a module docstring that is not an item. Take it out, and '
                        'give its text to the item as a field.'.format(file = relative))


# -----------------------------------------------------------------------------
def _fields(tree:       Tree,
            id_self:    str,
            list_field: list[tuple[str, typing.Any]],
            list_link:  list[tuple[str, str]],
            register:   str | None) -> dict:
    """
    Return the fields of a new item with id_self, the fields in
    list_field, and an edge for each relation and target in list_link,
    in the order they are written. A standalone item, whose register is
    None, takes its rights from the item of the project; a register
    entry gets an empty alias list.

    """

    if id_self in tree.map_item:
        raise ErrorEdit('An item with the id {id} exists.'.format(id = id_self))

    (prefix, _, _) = id_self.partition(DELIM_PREFIX)
    map_given      = dict(list_field)
    map_field      = {key: map_given.pop(key) for key in TUPLE_KEY_LEAD if key in map_given}

    map_field[KEY_ID_SELF]   = id_self
    map_field[KEY_GUID_SELF] = '{prefix}_{hex}'.format(prefix = prefix, hex = uuid.uuid4().hex)

    if register is None:
        map_field.update(_rights(tree))

    map_field.update(_referenced(tree, _ordered(list(map_given.items()))))

    if register is not None:
        map_field[KEY_ALIAS] = []
    map_field[KEY_RELATION] = [_edge(tree, id_relation, id_target)
                               for (id_relation, id_target) in list_link]

    return map_field


# -----------------------------------------------------------------------------
def link(tree: Tree, id_source: str, id_relation: str, id_target: str) -> Edit:
    """
    Return the edit that adds an edge of id_relation from id_source to
    id_target, at the end of the relation field of id_source.

    """

    edge = _edge(tree, id_relation, id_target)
    item = _Item(tree, id_source)

    if KEY_RELATION not in item.node:
        raise ErrorEdit('{id} has no relation field.'.format(id = id_source))

    list_edge = item.node[KEY_RELATION]
    if any(dict(each) == edge for each in list_edge):
        raise ErrorEdit('{id} already has that edge.'.format(id = id_source))

    (start, end) = item.extent(KEY_RELATION)
    column       = item.column(KEY_RELATION)

    if list_edge:
        return item.replace(end, end, cc_public.edit.layout.dump([edge], column + 2))

    return item.replace(start, end, cc_public.edit.layout.dump({KEY_RELATION: [edge]}, column))


# -----------------------------------------------------------------------------
def unlink(tree: Tree, id_source: str, id_relation: str, id_target: str) -> Edit:
    """
    Return the edit that takes the edge of id_relation from id_source
    to id_target out of the relation field of id_source.

    """

    item      = _Item(tree, id_source)
    list_edge = [_plain(edge) for edge in item.node.get(KEY_RELATION) or []]
    pair      = (id_relation, id_target)
    list_keep = [edge for edge in list_edge
                 if (edge.get(KEY_ID_RELATION), edge.get(KEY_ID_TARGET)) != pair]

    if len(list_keep) == len(list_edge):
        raise ErrorEdit('{id} has no edge of {relation} to {target}.'.format(
                                    id = id_source, relation = id_relation, target = id_target))

    return _put_field(item, KEY_RELATION, list_keep)


# -----------------------------------------------------------------------------
def set_field(tree: Tree, id_self: str, path: str, value: typing.Any) -> Edit:
    """
    Return the edit that sets the field at path in the item id_self to
    value, in place if the item has the field, and among the fields it
    is ordered with if not.

    A path is a field name, or a dotted path into the value of one, in
    which a number picks an element of a list. A field id_<role> that
    names an item is given guid_<role> beside it.

    """

    (key, list_part) = _path(path)
    item             = _Item(tree, id_self)

    if not list_part:
        edit = _put_field(item, key, value)
        if _is_reference(key, value):
            tree.update(edit)
            edit.update(_put_field(_Item(tree, id_self), _key_guid(key), tree.guid(value)))
        return edit

    whole = _plain(item.node[key]) if key in item.node else {}
    return _put_field(item, key, _put(tree, whole, list_part, value))


# -----------------------------------------------------------------------------
def unset_field(tree: Tree, id_self: str, path: str) -> Edit:
    """
    Return the edit that takes the field at path out of the item
    id_self, with guid_<role> if the field is id_<role>.

    """

    (key, list_part) = _path(path)
    item             = _Item(tree, id_self)

    if key not in item.node:
        raise ErrorEdit('{id} has no field {path}.'.format(id = id_self, path = path))

    if list_part:
        whole = _plain(item.node[key])
        _drop(whole, list_part, path, id_self)
        return _put_field(item, key, whole)

    (start, end) = item.extent(key)
    edit         = item.replace(start, end, [])
    key_guid     = _key_guid(key)

    if key.startswith(PREFIX_ID) and key_guid in item.node:
        tree.update(edit)
        item         = _Item(tree, id_self)
        (start, end) = item.extent(key_guid)
        edit.update(item.replace(start, end, []))

    return edit


# -----------------------------------------------------------------------------
def _path(path: str) -> tuple[str, list[str]]:
    """
    Return the field that path starts with, and the parts of the path
    into its value. A field that other commands keep is refused.

    """

    (key, *list_part) = path.split(DELIM_PATH)

    if key in SET_KEY_FIXED:
        raise ErrorEdit('The field {key} is not set this way.'.format(key = key))
    if not all([key, *list_part]):
        raise ErrorEdit('The path {path} has an empty part.'.format(path = path))

    return (key, list_part)


# -----------------------------------------------------------------------------
def _put_field(item: '_Item', key: str, value: typing.Any) -> Edit:
    """
    Return the edit that writes the field key of item with value, in
    place of the field if the item has it, and among the fields it is
    ordered with if not.

    """

    if key in item.node:
        (start, end) = item.extent(key)
        return item.replace(start, end, cc_public.edit.layout.dump({key: value}, item.column(key)))

    after    = _after(list(item.node.keys()), key)
    (_, end) = item.extent(after)

    return item.replace(end, end, cc_public.edit.layout.dump({key: value}, item.column(after)))


# -----------------------------------------------------------------------------
def _put(tree: Tree, node: typing.Any, list_part: list[str], value: typing.Any) -> typing.Any:
    """
    Return node with value put at the path list_part into it. A missing
    mapping on the way is made, and a field id_<role> that names an
    item is given guid_<role> after it.

    """

    (part, rest) = (list_part[0], list_part[1:])

    if isinstance(node, list):
        index       = _index(node, part)
        node[index] = _put(tree, node[index], rest, value) if rest else value
        return node

    if not isinstance(node, dict):
        raise ErrorEdit('The path goes into {value}, which has no fields.'.format(value = node))

    if rest:
        node[part] = _put(tree, node.get(part, {}), rest, value)
        return node

    node[part] = value
    if not _is_reference(part, value):
        return node

    key_guid = _key_guid(part)
    guid     = tree.guid(value)
    if key_guid in node:
        node[key_guid] = guid
        return node

    map_new = {}
    for (key, each) in node.items():
        map_new[key] = each
        if key == part:
            map_new[key_guid] = guid
    return map_new


# -----------------------------------------------------------------------------
def _drop(node: typing.Any, list_part: list[str], path: str, id_self: str) -> None:
    """
    Take the value at the path list_part out of node, with guid_<role>
    if it is id_<role>.

    """

    (part, rest) = (list_part[0], list_part[1:])

    if isinstance(node, list):
        index = _index(node, part)
        if rest:
            _drop(node[index], rest, path, id_self)
        else:
            del node[index]
        return

    if not (isinstance(node, dict) and part in node):
        raise ErrorEdit('{id} has no field {path}.'.format(id = id_self, path = path))

    if rest:
        _drop(node[part], rest, path, id_self)
        return

    del node[part]
    if part.startswith(PREFIX_ID):
        node.pop(_key_guid(part), None)


# -----------------------------------------------------------------------------
def _index(list_value: list, part: str) -> int:
    """
    Return the index into list_value that part gives.

    """

    if not (part.isdigit() and int(part) < len(list_value)):
        raise ErrorEdit('{part} is not the index of an element of a list of {count}.'.format(
                                                            part = part, count = len(list_value)))
    return int(part)


# -----------------------------------------------------------------------------
def _is_reference(key: str, value: typing.Any) -> bool:
    """
    Return True if the field key with value names an item.

    """

    return key.startswith(PREFIX_ID) and isinstance(value, str)


# -----------------------------------------------------------------------------
def _key_guid(key: str) -> str:
    """
    Return guid_<role> for the field id_<role>.

    """

    return PREFIX_GUID + key.removeprefix(PREFIX_ID)


# -----------------------------------------------------------------------------
def remove(tree: Tree, id_item: str) -> Edit:
    """
    Return the edit that removes the item id_item: the file of a
    standalone item, or the entry of a register entry with its banner.

    """

    _refuse_source(tree, id_item)
    _Item(tree, id_item)

    (_, _, holder, relative, _) = tree.map_item[id_item]

    if not holder:
        if pathlib.Path(relative).stem != id_item:
            raise ErrorEdit('{file} holds more than {id}, so it is not removed.'.format(
                                                                file = relative, id = id_item))
        return {relative: None}

    item         = _Item(tree, holder)
    item.node    = item.node[KEY_TABLE]
    (start, end) = item.extent(id_item)

    while start > 0 and item.line(start - 1).strip().startswith(MARK_COMMENT):
        start -= 1
    while start > 0 and not item.line(start - 1).strip():
        start -= 1

    return item.replace(start, end, [])


# -----------------------------------------------------------------------------
def rename(tree: Tree, id_old: str, id_new: str) -> Edit:
    """
    Return the edit that gives the item id_old the id id_new: in its
    own document, in every reference and mention of it in a document,
    and in the name of its file if it is named for it. A register entry
    keeps id_old in its alias list.

    """

    _refuse_source(tree, id_old)
    _Item(tree, id_old)

    if id_new.partition(DELIM_PREFIX)[0] != id_old.partition(DELIM_PREFIX)[0]:
        raise ErrorEdit('A rename keeps the type, so {new} must have the prefix of {old}.'.format(
                                                                    new = id_new, old = id_old))
    if id_new in tree.map_item:
        raise ErrorEdit('An item with the id {id} exists.'.format(id = id_new))

    (_, _, holder, relative, _) = tree.map_item[id_old]
    regex                       = re.compile(PATTERN_WHOLE_ID.format(id = re.escape(id_old)))
    edit                        = {}

    for (file, (document, _)) in tree.map_document.items():
        if document is None:
            continue
        text = tree.text(file)
        (first, last) = cc_public.edit.layout.span(text, pathlib.Path(file))
        list_line     = text.split('\n')
        list_line[first:last + 1] = [regex.sub(id_new, line)
                                     for line in list_line[first:last + 1]]
        renamed = '\n'.join(list_line)
        if renamed != text:
            edit[file] = _format(renamed, file)

    path = pathlib.Path(relative)
    if not holder and path.stem == id_old:
        edit[str(path.with_name(id_new + path.suffix))] = edit.pop(relative)
        edit[relative] = None

    tree.update(edit)

    if holder:
        item          = _Item(tree, id_new)
        (start, end)  = item.extent(KEY_ALIAS)
        list_alias    = [str(alias) for alias in item.node.get(KEY_ALIAS) or []]
        edit.update(item.replace(start, end, cc_public.edit.layout.dump(
                                    {KEY_ALIAS: [*list_alias, id_old]}, item.column(KEY_ALIAS))))

    return edit


# -----------------------------------------------------------------------------
def _refuse_source(tree: Tree, id_item: str) -> None:
    """
    Refuse an item that is written in the file it names, whose id
    follows from the place of the file.

    """

    (prefix, _, _) = id_item.partition(DELIM_PREFIX)
    if prefix in SET_PREFIX_SOURCE:
        map_type = {row[1]: row[0] for row in tree.facts['type_prefix']}
        raise ErrorEdit('An item of {type} lives in the file it names, so move or remove '
                        'the file by hand.'.format(type = map_type.get(prefix, prefix)))


# -----------------------------------------------------------------------------
def batch(tree: Tree, list_operation: list) -> None:
    """
    Make each operation of list_operation on the tree, in order. An
    operation is a mapping with one of these forms:

        new:   ID
        field: {NAME: VALUE, ...}
        link:  [[RELATION, TARGET], ...]

        header: PATH
        id:     ID
        field:  {NAME: VALUE, ...}
        link:   [[RELATION, TARGET], ...]

        link:   [SOURCE, RELATION, TARGET]

        unlink: [SOURCE, RELATION, TARGET]

        set:    [ID, PATH, VALUE]

        unset:  [ID, PATH]

        remove: ID

        rename: [OLD, NEW]

    """

    if not isinstance(list_operation, list):
        raise ErrorEdit('A batch is a list of operations.')

    for operation in list_operation:
        tree.update(_operation(tree, operation))


# -----------------------------------------------------------------------------
def _operation(tree: Tree, operation: typing.Any) -> Edit:
    """
    Return the edit that one operation of a batch makes.

    """

    if isinstance(operation, dict) and isinstance(operation.get(KEY_NEW), str):
        return new(tree,
                   operation[KEY_NEW],
                   [(str(key), _plain(value)) for (key, value)
                    in (operation.get(KEY_FIELD) or {}).items()],
                   [tuple(map(str, pair)) for pair in operation.get(KEY_LINK) or []])

    if isinstance(operation, dict) and isinstance(operation.get(KEY_HEADER), str):
        return header(tree,
                      operation[KEY_HEADER],
                      None if operation.get(KEY_ID) is None else str(operation[KEY_ID]),
                      [(str(key), _plain(value)) for (key, value)
                       in (operation.get(KEY_FIELD) or {}).items()],
                      [tuple(map(str, pair)) for pair in operation.get(KEY_LINK) or []])

    if isinstance(operation, dict) and set(operation) == {KEY_REMOVE}:
        return remove(tree, str(operation[KEY_REMOVE]))

    if isinstance(operation, dict) and set(operation) == {KEY_SET}:
        list_arg = operation[KEY_SET]
        if isinstance(list_arg, list) and len(list_arg) == 3:
            return set_field(tree, str(list_arg[0]), str(list_arg[1]), _plain(list_arg[2]))

    for (key, function, count) in ((KEY_LINK, link, 3), (KEY_UNLINK, unlink, 3),
                                   (KEY_UNSET, unset_field, 2), (KEY_RENAME, rename, 2)):
        if isinstance(operation, dict) and set(operation) == {key}:
            list_arg = operation[key]
            if isinstance(list_arg, list) and len(list_arg) == count:
                return function(tree, *map(str, list_arg))

    raise ErrorEdit('An operation of a batch is not one of new, header, link, unlink, set, '
                    'unset, remove or rename: {operation}'.format(operation = operation))


# -----------------------------------------------------------------------------
def apply(tree: Tree, is_written: bool = True) -> cc_public.check.check.Failures:
    """
    Check the tree with the edits made so far in place, and return the
    failures they add. Write them only if they add none and is_written.

    A failure is compared without its line, since an edit moves the
    lines below it.

    """

    before = cc_public.check.check.check_documents(tree.map_original)
    after  = cc_public.check.check.check_documents(tree.map_document)
    added  = _added(before, after)

    if is_written and not added:
        for (relative, text) in tree.edit.items():
            path = tree.root / relative
            if text is None:
                path.unlink(missing_ok = True)
                continue
            path.parent.mkdir(parents = True, exist_ok = True)
            path.write_text(text, encoding = 'utf-8')

    return added


# -----------------------------------------------------------------------------
def _added(before: cc_public.check.check.Failures,
           after:  cc_public.check.check.Failures) -> cc_public.check.check.Failures:
    """
    Return the failures in after that are not in before, compared
    without their lines.

    """

    map_column = cc_public.check.check.columns()
    added      = {}

    for (name, list_row) in after.items():
        tuple_keep = tuple(index for (index, column) in enumerate(map_column[name])
                           if column != COLUMN_LINE)
        counter    = collections.Counter(tuple(row[index] for index in tuple_keep)
                                         for row in before.get(name, []))
        for row in list_row:
            key = tuple(row[index] for index in tuple_keep)
            if counter[key]:
                counter[key] -= 1
            else:
                added.setdefault(name, []).append(row)

    return added


# -----------------------------------------------------------------------------
def _register(tree: Tree, id_type: str) -> str | None:
    """
    Return the id of the register that holds the items of id_type, or
    None if they are standalone.

    """

    set_inverse = {row[0] for row in tree.facts['relation_inverse'] if row[1] == ID_HELD}

    for (source, relation, target) in sorted(tree.facts['edge']):
        if source == id_type and relation == ID_HELD:
            return target
        if target == id_type and relation in set_inverse:
            return source

    return None


# -----------------------------------------------------------------------------
def _rights(tree: Tree) -> dict:
    """
    Return the rights fields of the item of the project.

    """

    if ID_RIGHTS not in tree.map_item:
        raise ErrorEdit('No item {id} gives the rights of a new item.'.format(id = ID_RIGHTS))

    (document, _) = tree.map_document[tree.map_item[ID_RIGHTS][3]]

    return {key: _plain(document[key]) for key in TUPLE_KEY_RIGHTS if key in document}


# -----------------------------------------------------------------------------
def _plain(value):
    """
    Return value with the mappings and lists that YAML read it into
    made plain.

    """

    if isinstance(value, dict):
        return {key: _plain(each) for (key, each) in value.items()}
    if isinstance(value, list):
        return [_plain(each) for each in value]
    return str(value) if isinstance(value, str) else value


# -----------------------------------------------------------------------------
def _ordered(list_field: list[tuple[str, typing.Any]]) -> dict:
    """
    Return the fields of list_field, the descriptive ones first and in
    their order, then the others in the order given.

    """

    map_field = dict(list_field)
    for key in SET_KEY_FIXED:
        if key in map_field:
            raise ErrorEdit('The field {key} is not set this way.'.format(key = key))

    return ({key: map_field[key] for key in TUPLE_KEY_PROSE if key in map_field}
            | {key: value for (key, value) in map_field.items() if key not in TUPLE_KEY_PROSE})


# -----------------------------------------------------------------------------
def _referenced(tree: Tree, map_field: dict) -> dict:
    """
    Return the fields of map_field, with the guid of each item that a
    field id_<role> names put after it as guid_<role>, unless given.

    """

    map_new = {}

    for (key, value) in map_field.items():
        map_new[key] = value
        if not (key.startswith(PREFIX_ID) and isinstance(value, str)):
            continue
        key_guid = PREFIX_GUID + key[len(PREFIX_ID):]
        if key_guid not in map_field:
            map_new[key_guid] = tree.guid(value)

    return map_new


# -----------------------------------------------------------------------------
def _edge(tree: Tree, id_relation: str, id_target: str) -> dict[str, str]:
    """
    Return an edge of id_relation to id_target, with their guids.

    """

    return {KEY_ID_RELATION:   id_relation,
            KEY_GUID_RELATION: tree.guid(id_relation),
            KEY_ID_TARGET:     id_target,
            KEY_GUID_TARGET:   tree.guid(id_target)}


# -----------------------------------------------------------------------------
def _after(list_key: list[str], key: str) -> str:
    """
    Return the field of list_key that a new field key goes after: the
    last descriptive field before it in order, or for any other field
    the last field before the aliases and edges. A field guid_<role>
    goes after id_<role>.

    """

    key_id = PREFIX_ID + key.removeprefix(PREFIX_GUID)
    if key.startswith(PREFIX_GUID) and key_id in list_key:
        return key_id

    if key in TUPLE_KEY_PROSE:
        tuple_before = TUPLE_KEY_PROSE[:TUPLE_KEY_PROSE.index(key)]
        list_before  = [each for each in list_key if each in tuple_before]
        if list_before:
            return list_before[-1]
        return KEY_GUID_SELF if KEY_GUID_SELF in list_key else list_key[0]

    list_before = [each for each in list_key if each not in (KEY_ALIAS, KEY_RELATION)]
    list_tail   = [each for each in list_key if each in (KEY_ALIAS, KEY_RELATION)]
    if list_tail:
        list_before = list_key[:list_key.index(list_tail[0])]
    return list_before[-1]


# -----------------------------------------------------------------------------
def _format(text: str, relative: str) -> str:
    """
    Return text, the new content of the file at relative, laid out.

    """

    try:
        return cc_public.edit.layout.format_file(text, pathlib.Path(relative))
    except cc_public.edit.layout.Unsupported as error:
        raise ErrorEdit('The edit leaves {file} unlaid: {error}'.format(
                                                file = relative, error = error)) from error


# -----------------------------------------------------------------------------
def _append_entry(tree: Tree, id_register: str, map_field: dict) -> Edit:
    """
    Return the edit that adds an entry with map_field at the end of the
    table of the register id_register, under a banner.

    """

    item = _Item(tree, id_register)

    if not item.node.get(KEY_TABLE):
        raise ErrorEdit('{id} has no entries to add to.'.format(id = id_register))

    table       = item.node[KEY_TABLE]
    item.node   = table
    (_, end)    = item.extent(list(table.keys())[-1])
    column      = item.column(list(table.keys())[-1])
    id_self     = map_field[KEY_ID_SELF]
    head        = ' ' * column + '# '
    list_line   = ['',
                   head + '-' * (LENGTH_BANNER - len(head)),
                   head + '{id} -- {title}'.format(id    = id_self,
                                                   title = map_field.get('title', '')),
                   head.rstrip(),
                   ' ' * column + id_self + ':']

    list_line += cc_public.edit.layout.dump(map_field, column + 2)

    return item.replace(end, end, list_line)


# -----------------------------------------------------------------------------
class _Item:
    """
    An item in the text of its file: its node as YAML reads it, and the
    lines of the file, with the comment marker taken off the lines of
    a comment header.

    """

    # -------------------------------------------------------------------------
    def __init__(self, tree: Tree, id_item: str) -> None:
        """
        Find the item id_item in the text of its file.

        """

        if id_item not in tree.map_item:
            raise ErrorEdit('No item has the id {id}.'.format(id = id_item))

        (_, _, holder, relative, _) = tree.map_item[id_item]
        path                        = pathlib.Path(relative)

        text             = tree.text(relative)
        (document, base) = cc_public.graph.extract.parse(text, path)

        self.relative  = relative
        self.list_line = text.split('\n')
        self.base      = base - 1
        self.mark      = ('' if path.suffix in (cc_public.graph.extract.SUFFIX_YAML,
                                                cc_public.graph.extract.SUFFIX_PYTHON)
                          else cc_public.graph.extract.mark_comment(path))

        if holder:
            if not (isinstance(document.get(KEY_TABLE), dict) and id_item in document[KEY_TABLE]):
                raise ErrorEdit('{id} is not an entry of the table of {holder}.'.format(
                                                                    id = id_item, holder = holder))
            self.node = document[KEY_TABLE][id_item]
        else:
            self.node = document

    # -------------------------------------------------------------------------
    def line(self, index: int) -> str:
        """
        Return the line of the file at index, without its comment
        marker.

        """

        text = self.list_line[index]
        if self.mark and text.startswith(self.mark):
            text = text[len(self.mark):].removeprefix(' ')
        return text

    # -------------------------------------------------------------------------
    def column(self, key: str) -> int:
        """
        Return the column that the field key starts at.

        """

        return self.node.lc.key(key)[1]

    # -------------------------------------------------------------------------
    def extent(self, key: str) -> tuple[int, int]:
        """
        Return the first line of the field key, and the line after its
        last, leaving out the blank lines after it.

        """

        start  = self.base + self.node.lc.key(key)[0]
        column = self.column(key)
        end    = start + 1

        while end < len(self.list_line):
            text = self.line(end)
            if text.strip() and (len(text) - len(text.lstrip())) <= column:
                break
            end += 1

        while end > start + 1 and not self.line(end - 1).strip():
            end -= 1

        return (start, end)

    # -------------------------------------------------------------------------
    def replace(self, start: int, end: int, list_line: list[str]) -> Edit:
        """
        Return the edit that puts list_line in place of the lines from
        start to end, with the comment marker on each, and the file laid
        out.

        """

        list_marked = [self._marked(text) for text in list_line]
        list_new    = self.list_line[:start] + list_marked + self.list_line[end:]
        return {self.relative: _format('\n'.join(list_new), self.relative)}

    # -------------------------------------------------------------------------
    def _marked(self, text: str) -> str:
        """
        Return text with the comment marker of the file put back on.

        """

        if not self.mark:
            return text
        return self.mark + (' ' + text if text else '')
