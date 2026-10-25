"""
---

id_self:                pym_cctool.edit.edit
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
                        laid out by pym_cctool.edit.layout. A tree
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
                        pym_cctool.cli.editing.
edge:                   []

...
"""


import ast
import collections
import io
import os
import pathlib
import re
import tokenize
import typing
import uuid

import ruamel.yaml
import ruamel.yaml.scalarstring

import cctool.check.check
import cctool.check.segment
import cctool.edit.layout
import cctool.graph.extract
import cctool.graph.prefix


KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_EDGE          = 'edge'
KEY_ALIAS         = 'alias'
KEY_ENTRIES       = 'entries'
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
KEY_MOVE          = 'move'
SUFFIX_STAGED     = '.cctool-staged'
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
# and aliases are lists that other commands keep. Each says what does
# change it, so that a refusal says what to do instead.
#
MAP_KEY_FIXED     = {KEY_ID_SELF:   'cctool rename changes an id',
                     KEY_GUID_SELF: 'a guid never changes',
                     KEY_EDGE:  'cctool link and cctool unlink change edges',
                     KEY_ALIAS:     'cctool rename keeps the old id as an alias'}
SET_KEY_FIXED     = set(MAP_KEY_FIXED)

# A standalone item takes its rights from the segment item of the tree,
# which gives the default rights and protective marks of its federated
# segment.
#
TUPLE_KEY_RIGHTS  = ('copyright', 'license', 'protective_mark')

# A type is held in a register when it has this edge to one. A type
# with one of these prefixes has its items in source files, where the
# name of the file gives the id, so new does not make them.
#
RELATION_HAS_ITEMS_HELD_IN_REGISTER = 'relation_has_items_held_in_register'
SET_PREFIX_SOURCE                   = {cctool.graph.prefix.MAP_PREFIX[id_type]
                                       for id_type in ('type_python_module',
                                                       'type_python_package',
                                                       'type_python_class',
                                                       'type_python_function',
                                                       'type_logic_program_file',
                                                       'type_logic_program_predicate',
                                                       'type_file',
                                                       'type_shell_script')}

# A file of any other type takes its item in a header: a python module
# in its module docstring, and any other file in a comment header. A
# YAML file is a YAML document already, and JSON and Markdown have no
# comment for a header.
#
SET_SUFFIX_BARE   = {'.yaml', '.json', '.md'}
QUOTE_DOCSTRING   = '"""'

# Above the declaration of a predicate, a comment that says what it is,
# set off from what comes before by a rule of hyphens.
#
LINE_RULE         = '-----'

# A new file is first written in the folder of its type. Where the
# check says it belongs elsewhere, as an item of a decision belongs in
# the folder of the decision, apply moves it there.
#
NAME_MISPLACED    = 'misplaced_document'

DIR_DATA          = '_data'
SUFFIX_YAML       = '.yaml'
LENGTH_BANNER     = 79
DELIM_PREFIX      = '_'
PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
MARK_COMMENT      = '#'
DELIM_PATH        = '.'

# An embedded item, such as an interface member, has the id of what
# holds it, a full stop and a name of its own.
#
DELIM_NAME        = '.'

# An id as a word of its own, and as the name of a file: not inside a
# longer id, and not part of a dotted name.
#
PATTERN_WHOLE_ID  = r'(?<![A-Za-z0-9_$.-]){id}(?![A-Za-z0-9_])'

# A dotted name as a word of its own, as python code writes the name
# of a module: not the tail of a longer name, and not the head of a
# longer word.
#
PATTERN_DOTTED    = r'(?<![A-Za-z0-9_.]){name}(?![A-Za-z0-9_])'
DIR_CACHE         = '__pycache__'

# The line of a YAML document that spells a type as code does, such as
# the type of a member of an interface, with its key and its value.
#
REGEX_SPELLING    = re.compile(r'^(\s*(?:- )?spelling:\s+)(.*)$', re.MULTILINE)

# The text of a file, or its bytes when it is not text, such as a font
# that a move carries along. None removes the file.
#
Edit              = dict[str, str | bytes | None]
YAML              = ruamel.yaml.YAML(typ = 'rt')


# -----------------------------------------------------------------------------
class ErrorEdit(Exception):
    """
    The edit asked for cannot be made. The message says why.

    """


# -----------------------------------------------------------------------------
class Tree:
    """
    The YAML documents of a tree and the facts they hold, read once for
    an edit, with the texts of the edits made so far in place of those
    they change.

    """

    # -------------------------------------------------------------------------
    def __init__(self, root: pathlib.Path) -> None:
        """
        Read the tree under root, with the trees that its segment item
        consumes, so that an edit may name their items. Only the tree
        under root is ever written.

        """

        self.root         = root
        self.map_original = cctool.check.segment.union(root)
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
            _refuse_consumed(relative)
            for key in [key for key in self.map_document
                        if cctool.graph.extract.file_of(key) == relative]:
                del self.map_document[key]
            if text is None or isinstance(text, bytes):
                self.edit[relative] = text
                continue
            try:
                self.map_document.update(cctool.graph.extract.parse_all(
                                                            text, pathlib.Path(relative)))
            except cctool.graph.extract.ErrorRead as error:
                raise ErrorEdit('The edit leaves {file} unreadable: {error}'.format(
                                                    file = relative, error = error)) from error
            self.edit[relative] = text

        self._index()

    # -------------------------------------------------------------------------
    def _index(self) -> None:
        """
        Find the facts of the YAML documents, and index the items by id.

        """

        self.facts    = cctool.graph.extract.facts_of(self.map_document)
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

        _refuse_consumed(relative)
        if relative in self.edit and self.edit[relative] is None:
            raise ErrorEdit('The file {file} is removed.'.format(file = relative))

        if relative in self.edit:
            return self.edit[relative]
        return (self.root / relative).read_text(encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _refuse_consumed(relative: str) -> None:
    """
    Raise ErrorEdit if relative is the key of a file of a consumed tree,
    which the tree being edited cannot change.

    """

    segment = cctool.graph.extract.consumer(relative)
    if segment is not None:
        raise ErrorEdit('{file} is held by {segment}, a segment that this tree consumes, so '
                        'it cannot be changed here.'.format(
                            file    = cctool.graph.extract.in_tree(relative),
                            segment = segment))


# -----------------------------------------------------------------------------
def new(tree:       Tree,
        id_self:    str,
        list_field: list[tuple[str, typing.Any]],
        list_link:  list[tuple[str, str]]) -> Edit:
    """
    Return the edit that makes a new item with id_self, the fields in
    list_field, and an edge for each relation and target in list_link.
    A type held in a register gets an entry at the end of the entries of
    its register. Any other gets a file of its own under _data.

    """

    (prefix, _, _) = id_self.partition(DELIM_PREFIX)
    map_type       = {row[1]: row[0] for row in tree.facts['type_prefix']}

    if prefix not in map_type:
        raise ErrorEdit('No type has the prefix {prefix}. reg_data_item_type.yaml lists '
                        'the types.'.format(prefix = prefix))
    if prefix in SET_PREFIX_SOURCE:
        raise ErrorEdit('An item of {type} is written in the file it names: give the file '
                        'its item with header.'.format(type = map_type[prefix]))

    id_type   = map_type[prefix]
    register  = _register(tree, id_type)
    map_field = _fields(tree, id_self, list_field, list_link, register)

    if register is None:
        relative = '{dir}/{folder}/{id}{suffix}'.format(
                                    dir    = DIR_DATA,
                                    folder = id_type.partition(DELIM_PREFIX)[2],
                                    id     = id_self,
                                    suffix = SUFFIX_YAML)
        if relative in tree.map_document:
            raise ErrorEdit('The file {file} exists.'.format(file = relative))
        text = '\n'.join(cctool.edit.layout.dump(map_field, 0)) + '\n'
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
    comment header if not, after any line that names an interpreter or
    opens a comment block.
    The file is made if there is none.

    The id of a python module or logic program file follows from its
    path, so id_self may be None for one. Any other file needs it.

    """

    path = pathlib.Path(relative)

    if path.suffix in SET_SUFFIX_BARE:
        raise ErrorEdit('{file} cannot hold a header. A YAML, JSON or Markdown file is '
                        'a document: make its items with cctool new.'.format(file = relative))

    if path.suffix in cctool.graph.extract.MAP_PREFIX_MODULE:
        expected = cctool.graph.extract.module_name(path)
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
        raise ErrorEdit('No type has the prefix {prefix}. reg_data_item_type.yaml lists '
                        'the types.'.format(prefix = prefix))

    map_field = _fields(tree, id_self, list_field, list_link, None)
    list_doc  = [cctool.graph.extract.LINE_OPEN, '',
                 *cctool.edit.layout.dump(map_field, 0),
                 '', cctool.graph.extract.LINE_CLOSE]
    text      = tree.text(relative) if relative in tree.map_document else ''

    if path.suffix == cctool.graph.extract.SUFFIX_PYTHON:
        _refuse_docstring(text, relative)

    return {relative: _format('\n'.join(_with_header(path, list_doc, text)), relative)}


# -----------------------------------------------------------------------------
def _with_header(path: pathlib.Path, list_doc: list[str], text: str) -> list[str]:
    """
    Return the lines of text, the file at path, with the lines of the
    YAML document list_doc as its header, laid out as header says.

    """

    list_line = text.split('\n') if text else []
    list_head = []

    if list_line and cctool.graph.extract.is_lead(list_line[0]):
        list_head = [list_line.pop(0)]
    while list_line and not list_line[0].strip():
        list_line.pop(0)

    # A module docstring is set apart from the code by two blank lines,
    # as a definition is, and a comment header by one.
    #
    if path.suffix == cctool.graph.extract.SUFFIX_PYTHON:
        list_new   = [QUOTE_DOCSTRING, *list_doc, QUOTE_DOCSTRING]
        list_blank = ['', '']
    else:
        mark       = cctool.graph.extract.mark_comment(path)
        list_new   = [mark + (' ' + line if line else '') for line in list_doc]
        list_blank = ['']

    # A style sheet holds its header in a comment block: in the block it
    # opens with, set apart from the rest of it by a bare marker, or in a
    # block of its own.
    #
    if path.suffix == cctool.graph.extract.SUFFIX_STYLE:
        if list_head:
            list_blank = [mark]
        else:
            list_head  = [cctool.graph.extract.LINE_BLOCK_OPEN]
            list_new  += [cctool.graph.extract.LINE_BLOCK_CLOSE]

    return [*list_head, *list_new, *([*list_blank, *list_line] if list_line else [''])]


# -----------------------------------------------------------------------------
def header_definition(tree:       Tree,
                      key:        str,
                      id_self:    str | None,
                      list_field: list[tuple[str, typing.Any]],
                      list_link:  list[tuple[str, str]]) -> Edit:
    """
    Return the edit that gives the class or function key, such as
    src/cctool/graph/jq.py::query, a new item in its docstring, or
    the predicate key of a logic program, as header_predicate does. Its
    id follows from key. The text the docstring held becomes the brief,
    unless a brief is given, so that what the code says of itself is
    said once.

    """

    relative  = cctool.graph.extract.file_of(key)
    list_name = key.split(cctool.graph.extract.DELIM_DEFINITION)[1:]

    if pathlib.Path(relative).suffix == cctool.graph.extract.SUFFIX_PROGRAM:
        return header_predicate(tree, key, id_self, list_field, list_link)
    if pathlib.Path(relative).suffix != cctool.graph.extract.SUFFIX_PYTHON:
        raise ErrorEdit('{file} is not a python module or a logic program.'.format(
                                                                            file = relative))
    if relative not in tree.map_document:
        raise ErrorEdit('There is no file {file}.'.format(file = relative))
    if key in tree.map_document:
        raise ErrorEdit('{key} already holds an item.'.format(key = key))

    text     = tree.text(relative)
    node     = _definition(text, relative, list_name)
    expected = cctool.graph.extract.definition_id(pathlib.Path(relative), list_name, node)

    if id_self not in (None, expected):
        raise ErrorEdit('The item of {key} has the id {expected}, not {id}.'.format(
                                                    key = key, expected = expected, id = id_self))

    docstring = ast.get_docstring(node)
    if docstring and not any(name == 'brief' for (name, _) in list_field):
        list_field = [*list_field, ('brief', ruamel.yaml.scalarstring.LiteralScalarString(
                                                                        docstring + '\n'))]

    map_field = _fields(tree, expected, list_field, list_link, None)
    first     = node.body[0]
    indent    = ' ' * first.col_offset
    list_doc  = [QUOTE_DOCSTRING, cctool.graph.extract.LINE_OPEN, '',
                 *cctool.edit.layout.dump(map_field, 0),
                 '', cctool.graph.extract.LINE_CLOSE, QUOTE_DOCSTRING]
    list_new  = [indent + line if line else '' for line in list_doc]
    list_line = text.split('\n')

    if docstring is None:
        list_line[first.lineno - 1:first.lineno - 1] = [*list_new, '']
    else:
        list_line[first.lineno - 1:first.end_lineno] = list_new

    return {relative: _format('\n'.join(list_line), relative)}


# -----------------------------------------------------------------------------
def header_predicate(tree:       Tree,
                     key:        str,
                     id_self:    str | None,
                     list_field: list[tuple[str, typing.Any]],
                     list_link:  list[tuple[str, str]]) -> Edit:
    """
    Return the edit that gives the predicate key of a logic program,
    such as src/cctool/check/check.lp::bad_id, a new item in a
    comment before its declaration. Its id follows from key. The comment
    above the declaration becomes the brief, unless one is given, so
    that what the program says of the predicate is said once. The title
    is made from the name if none is given.

    """

    relative = cctool.graph.extract.file_of(key)
    name     = key.rsplit(cctool.graph.extract.DELIM_DEFINITION, 1)[-1]
    path     = pathlib.Path(relative)
    mark     = cctool.graph.extract.mark_comment(path)

    if relative not in tree.map_document:
        raise ErrorEdit('There is no file {file}.'.format(file = relative))
    if key in tree.map_document:
        raise ErrorEdit('{key} already holds an item.'.format(key = key))

    expected = cctool.graph.extract.predicate_id(path, name)
    if id_self not in (None, expected):
        raise ErrorEdit('The item of {key} has the id {expected}, not {id}.'.format(
                                                    key = key, expected = expected, id = id_self))

    list_line = tree.text(relative).split('\n')
    list_decl = [index for (index, line) in enumerate(list_line)
                 if (match := cctool.graph.extract.REGEX_DECL_NAME.match(line))
                 and match.group(1) == name]
    if not list_decl:
        raise ErrorEdit('{file} declares no predicate {name}.'.format(file = relative, name = name))

    decl  = list_decl[0]
    first = decl
    while (first > 0 and list_line[first - 1].startswith(mark)
           and not list_line[first - 1].startswith(mark + ' ' + LINE_RULE)):
        first -= 1

    list_prose = [_unmark(line, mark).strip() for line in list_line[first:decl]]
    prose      = '\n\n'.join(' '.join(paragraph.split())
                               for paragraph in '\n'.join(list_prose).split('\n\n')
                               if paragraph.strip())

    map_given  = dict(list_field)
    list_field = list(list_field)

    if 'title' not in map_given:
        list_field.insert(0, ('title', name.replace('_', ' ').capitalize()))
    if prose and 'brief' not in map_given:
        list_field.append(('brief', ruamel.yaml.scalarstring.LiteralScalarString(prose + '\n')))

    map_field = _fields(tree, expected, list_field, list_link, None)
    list_doc  = [cctool.graph.extract.LINE_OPEN, '',
                 *cctool.edit.layout.dump(map_field, 0),
                 '', cctool.graph.extract.LINE_CLOSE, '']
    list_new  = [mark + (' ' + line if line else '') for line in list_doc]

    return {relative: _format('\n'.join([*list_line[:first], *list_new, *list_line[decl:]]),
                              relative)}


# -----------------------------------------------------------------------------
def _unmark(line: str, mark: str) -> str:
    """
    Return line without the comment marker that begins it.

    """

    return line[len(mark):].removeprefix(' ') if line.startswith(mark) else line


# -----------------------------------------------------------------------------
def _definition(text: str, relative: str, list_name: list[str]) -> ast.AST:
    """
    Return the class or function that list_name names, down from the
    top of the python module text at relative. Refuse one that is not
    there, or whose body shares the line of its definition.

    """

    try:
        node = ast.parse(text)
    except SyntaxError as error:
        raise ErrorEdit('{file} is not python: {error}'.format(
                                                file = relative, error = error)) from error

    for name in list_name:
        list_child = [child for child in getattr(node, 'body', [])
                      if type(child) in cctool.graph.extract.MAP_PREFIX_KIND
                      and child.name == name
                      and isinstance(node, (ast.Module, ast.ClassDef))]
        if not list_child:
            raise ErrorEdit('{file} has no class or function {name} there.'.format(
                                                                file = relative, name = name))
        node = list_child[-1]

    if node.body[0].lineno == node.lineno:
        raise ErrorEdit('The body of {name} is on the line that defines it. Put the body '
                        'on a line of its own, then add the header.'.format(
                                                                        name = list_name[-1]))

    return node


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
    None, takes its rights from the segment item of the tree; a register
    entry gets an empty alias list.

    """

    if id_self in tree.map_item:
        raise ErrorEdit('An item with the id {id} exists.'.format(id = id_self))

    map_given = dict(list_field)
    map_field = {key: map_given.pop(key) for key in TUPLE_KEY_LEAD if key in map_given}

    map_field[KEY_ID_SELF]   = id_self
    map_field[KEY_GUID_SELF] = _guid(id_self)

    if register is None:
        map_field.update(_rights(tree))

    map_field.update(_referenced(tree, _minted(_ordered(list(map_given.items())))))

    if register is not None:
        map_field[KEY_ALIAS] = []
    map_field[KEY_EDGE] = [_edge(tree, id_relation, id_target)
                               for (id_relation, id_target) in list_link]

    return map_field


# -----------------------------------------------------------------------------
def link(tree: Tree, id_source: str, id_relation: str, id_target: str) -> Edit:
    """
    Return the edit that adds an edge of id_relation from id_source to
    id_target, at the end of the edge field of id_source.

    """

    edge = _edge(tree, id_relation, id_target)
    item = _Item(tree, id_source)

    if KEY_EDGE not in item.node:
        raise ErrorEdit('{id} has no edge field.'.format(id = id_source))

    list_edge = item.node[KEY_EDGE]
    if any(dict(each) == edge for each in list_edge):
        raise ErrorEdit('{id} already has that edge.'.format(id = id_source))

    (start, end) = item.extent(KEY_EDGE)
    column       = item.column(KEY_EDGE)

    if list_edge:
        return item.replace(end, end, cctool.edit.layout.dump([edge], column + 2))

    return item.replace(start, end, cctool.edit.layout.dump({KEY_EDGE: [edge]}, column))


# -----------------------------------------------------------------------------
def unlink(tree: Tree, id_source: str, id_relation: str, id_target: str) -> Edit:
    """
    Return the edit that takes the edge of id_relation from id_source
    to id_target out of the edge field of id_source.

    """

    item      = _Item(tree, id_source)
    list_edge = [_plain(edge) for edge in item.node.get(KEY_EDGE) or []]
    pair      = (id_relation, id_target)
    list_keep = [edge for edge in list_edge
                 if (edge.get(KEY_ID_RELATION), edge.get(KEY_ID_TARGET)) != pair]

    if len(list_keep) == len(list_edge):
        raise ErrorEdit('{id} has no edge of {relation} to {target}.'.format(
                                    id = id_source, relation = id_relation, target = id_target))

    return _put_field(item, KEY_EDGE, list_keep)


# -----------------------------------------------------------------------------
def set_field(tree: Tree, id_self: str, path: str, value: typing.Any) -> Edit:
    """
    Return the edit that sets the field at path in the item id_self to
    value, in place if the item has the field, and among the fields it
    is ordered with if not.

    A path is a field name, or a dotted path into the value of one, in
    which a number picks an element of a list. A field id_<field> that
    names an item is given guid_<field> beside it.

    """

    (key, list_part) = _path(path)
    item             = _Item(tree, id_self)

    if not list_part:
        edit = _put_field(item, key, _styled(key, _minted(value), item.node.get(key)))
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
    id_self, with guid_<field> if the field is id_<field>.

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
        raise ErrorEdit('The field {key} is not set this way: {how}.'.format(
                                key = key, how = MAP_KEY_FIXED[key]))
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
        return item.replace(start, end, cctool.edit.layout.dump({key: value}, item.column(key)))

    after    = _after(list(item.node.keys()), key)
    (_, end) = item.extent(after)

    return item.replace(end, end, cctool.edit.layout.dump({key: value}, item.column(after)))


# -----------------------------------------------------------------------------
def _put(tree: Tree, node: typing.Any, list_part: list[str], value: typing.Any) -> typing.Any:
    """
    Return node with value put at the path list_part into it. A missing
    mapping on the way is made, and a field id_<field> that names an
    item is given guid_<field> after it.

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

    node[part] = _styled(part, _minted(value), node.get(part))
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
def _styled(key: str, value: typing.Any, old: typing.Any) -> typing.Any:
    """
    Return value, put in place of old as the field key, as a block if
    it is text and the field is prose: if key names a prose field, or
    old was written as a block.

    """

    is_prose = (key in cctool.edit.layout.SET_KEY_PROSE
                or isinstance(old, ruamel.yaml.scalarstring.LiteralScalarString))

    if is_prose and isinstance(value, str):
        return ruamel.yaml.scalarstring.LiteralScalarString(value.rstrip('\n') + '\n')
    return value


# -----------------------------------------------------------------------------
def _drop(node: typing.Any, list_part: list[str], path: str, id_self: str) -> None:
    """
    Take the value at the path list_part out of node, with guid_<field>
    if it is id_<field>.

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
    Return guid_<field> for the field id_<field>.

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

    if holder and not any(row[2] == id_item for row in tree.facts['register_entry_key']):
        raise ErrorEdit('{id} is embedded in {holder} and is not one of its entries, so '
                        'take it out of {holder} with cctool unset.'.format(
                                                                id = id_item, holder = holder))

    if not holder:
        if pathlib.Path(relative).stem != id_item:
            raise ErrorEdit('{file} holds more than {id}, so it is not removed.'.format(
                                                                file = relative, id = id_item))
        return {relative: None}

    item         = _Item(tree, holder)
    item.node    = item.node[KEY_ENTRIES]
    (start, end) = item.extent(id_item)

    while start > 0 and item.line(start - 1).strip().startswith(MARK_COMMENT):
        start -= 1
    while start > 0 and not item.line(start - 1).strip():
        start -= 1

    return item.replace(start, end, [])


# -----------------------------------------------------------------------------
def rename(tree: Tree, id_old: str, id_new: str) -> Edit:
    """
    Return the edit that gives the item id_old the id id_new, and gives
    each item whose id is made from id_old an id made from id_new in the
    same way.

    An interface control document or a dataflow graph holds members or
    nodes whose ids are its own name after a prefix of theirs, a full
    stop and a name, so they are renamed with it, and the members a
    member holds are renamed with that member. Each keeps its guid.

    """

    _refuse_source(tree, id_old)
    _Item(tree, id_old)

    if id_new.partition(DELIM_PREFIX)[0] != id_old.partition(DELIM_PREFIX)[0]:
        raise ErrorEdit('A rename keeps the type, so {new} must have the prefix of {old}.'.format(
                                                                    new = id_new, old = id_old))

    list_pair = [*_derived(tree, id_old, id_new), (id_old, id_new)]
    edit      = {}

    for (_, id_to) in list_pair:
        if id_to in tree.map_item:
            raise ErrorEdit('An item with the id {id} exists.'.format(id = id_to))

    for (id_from, id_to) in list_pair:
        edit_one = _rename_one(tree, id_from, id_to)
        tree.update(edit_one)
        edit.update(edit_one)

    return edit


# -----------------------------------------------------------------------------
def _derived(tree: Tree, id_old: str, id_new: str) -> list[tuple[str, str]]:
    """
    Return each item that id_old holds, at any depth, whose id is made
    from id_old: a prefix of its own, the name of id_old after its
    prefix, a full stop and a name. Each is paired with the id made the
    same way from id_new, the longest ids first, so that no id is
    renamed after a shorter one that it starts with.

    """

    name_old   = id_old.partition(DELIM_PREFIX)[2] + DELIM_NAME
    name_new   = id_new.partition(DELIM_PREFIX)[2] + DELIM_NAME
    map_holder = {row[0]: row[2] for row in tree.facts['item']}
    list_pair  = []

    for (id_item, id_holder) in map_holder.items():
        (prefix, _, name) = id_item.partition(DELIM_PREFIX)
        if not name.startswith(name_old):
            continue
        holder = id_holder
        while holder and holder != id_old:
            holder = map_holder.get(holder, '')
        if holder == id_old:
            list_pair.append((id_item, prefix + DELIM_PREFIX + name_new + name[len(name_old):]))

    return sorted(list_pair, key = lambda pair: (-len(pair[0]), pair[0]))


# -----------------------------------------------------------------------------
def _rename_one(tree: Tree, id_old: str, id_new: str) -> Edit:
    """
    Return the edit that gives the item id_old the id id_new: in its own
    YAML document, in every reference and mention of it in a document,
    in every string of a logic program that is id_old, and in the name
    of its file, or of its folder, if it is named for it. A register
    entry keeps id_old in its alias list. A dataflow node is filed
    under the last part of its id, so its key changes with it.

    An item embedded in another, such as an interface member, keeps no
    alias: its schema allows none, and whatever refers to it carries
    its guid, which does not change.

    The rules match items by id, in strings such as "relation_is_option_for". Left
    as they were, the rules that name id_old would match nothing, and
    so pass without a word.

    """

    (_, _, holder, relative, _) = tree.map_item[id_old]
    is_entry                    = any(row[2] == id_old for row in tree.facts['register_entry_key'])
    list_node                   = [(row[0], row[1]) for row in tree.facts['dataflow_node']
                                   if row[2] == id_old]
    edit                        = _renamed_documents(tree, id_old, id_new)

    for file in tree.map_document:
        if pathlib.Path(file).suffix != cctool.graph.extract.SUFFIX_PROGRAM:
            continue
        text    = edit.get(file) or tree.text(file)
        renamed = text.replace('"{id}"'.format(id = id_old), '"{id}"'.format(id = id_new))
        if renamed != text:
            edit[file] = renamed

    path = pathlib.Path(relative)
    if not holder and path.stem == id_old:
        edit[str(path.with_name(id_new + path.suffix))] = edit.pop(relative)
        edit[relative] = None
    if not holder and path.parent.name == id_old:
        _move_folder(tree, edit, path.parent, id_new)

    tree.update(edit)

    if is_entry:
        item          = _Item(tree, id_new)
        (start, end)  = item.extent(KEY_ALIAS)
        list_alias    = [str(alias) for alias in item.node.get(KEY_ALIAS) or []]
        edit.update(item.replace(start, end, cctool.edit.layout.dump(
                                    {KEY_ALIAS: [*list_alias, id_old]}, item.column(KEY_ALIAS))))

    key_new = id_new.rpartition(DELIM_NAME)[2]
    for (graph, key) in list_node:
        if key == key_new:
            continue
        item       = _Item(tree, graph)
        item.node  = item.node[cctool.graph.extract.KEY_NODE]
        index      = item.base + item.node.lc.key(key)[0]
        text       = item.line(index)
        edit.update(item.replace(index, index + 1, [text.replace(key + ':', key_new + ':', 1)]))

    return edit


# -----------------------------------------------------------------------------
def _renamed_documents(tree: Tree, id_old: str, id_new: str) -> Edit:
    """
    Return the edit that gives id_old the id id_new in every YAML
    document that names it.

    """

    regex = re.compile(PATTERN_WHOLE_ID.format(id = re.escape(id_old)))
    edit  = {}

    for file in cctool.graph.extract.files(tree.map_document):
        text      = tree.text(file)
        list_line = text.split('\n')
        for (first, last) in cctool.edit.layout.spans(text, pathlib.Path(file)):
            list_line[first:last + 1] = [regex.sub(id_new, line)
                                         for line in list_line[first:last + 1]]
        renamed = '\n'.join(list_line)
        if renamed != text:
            edit[file] = _format(renamed, file)

    return edit


# -----------------------------------------------------------------------------
def _move_folder(tree: Tree, edit: Edit, dir_old: pathlib.Path, id_new: str) -> None:
    """
    Add to edit the move of every file in dir_old, as edit leaves it,
    to a folder named id_new beside it. An item that gathers others, as
    a decision gathers its deliberation, is kept in a folder named for it,
    and the folder moves with it.

    """

    dir_new = dir_old.with_name(id_new)

    set_file = {cctool.graph.extract.file_of(key) for key in tree.map_document}

    for file in sorted(set_file | set(edit)):
        moved = pathlib.Path(file)
        if dir_old not in moved.parents:
            continue
        text = edit[file] if file in edit else tree.text(file)
        if text is None:
            continue
        edit[str(dir_new / moved.relative_to(dir_old))] = text
        edit[file] = None


# -----------------------------------------------------------------------------
def move(tree: Tree, path_old: str, path_new: str) -> Edit:
    """
    Return the edit that moves the file or folder at path_old to
    path_new, with what follows from the place of each file it holds.

    An item that lives in the file it names, such as a python module or
    a logic program file, takes its id from the place of its file, and
    so do the classes, functions and predicates it holds. Each gets the
    id its new place gives it, and keeps its guid, in every YAML
    document that names it and in the strings of the logic programs.
    A python module or package under src is imported by a dotted name
    that follows from its place too, so that name is changed in the
    code of every python module of the tree, and in the spelling of
    each type that a YAML document spells as code does.

    Text outside these, such as a path written in prose or the name of
    a module in a manifest, is not changed.

    """

    old      = pathlib.PurePosixPath(path_old)
    new      = pathlib.PurePosixPath(path_new)
    set_file = {cctool.graph.extract.file_of(key) for key in tree.map_document}
    set_file = {file for file in set_file | set(tree.edit) if tree.edit.get(file, '') is not None}
    map_move = _moves(set_file, old, new)
    map_id   = _moved_ids(tree, map_move)

    for id_new in map_id.values():
        if id_new in tree.map_item:
            raise ErrorEdit('An item with the id {id} exists.'.format(id = id_new))

    edit = _renamed_ids(tree, map_id)
    tree.update(edit)
    edit.update(_redotted(tree, set_file, dotted(old), dotted(new)))
    tree.update(edit)

    edit_move = {}
    for (file_old, file_new) in map_move.items():
        edit_move[file_new] = edit[file_old] if file_old in edit else _content(tree, file_old)
        edit_move[file_old] = None
    edit.update(edit_move)

    return edit


# -----------------------------------------------------------------------------
def _moves(set_file: set[str],
           old:      pathlib.PurePosixPath,
           new:      pathlib.PurePosixPath) -> dict[str, str]:
    """
    Return the new path of each file of set_file that a move of old to
    new moves, keyed by its old path. Refuse a move of nothing, and one
    onto a file that is there.

    """

    map_move = {}

    for file in sorted(set_file):
        path = pathlib.PurePosixPath(file)
        if path == old:
            map_move[file] = str(new)
        elif old in path.parents:
            map_move[file] = str(new / path.relative_to(old))

    if not map_move:
        raise ErrorEdit('No file of the tree is at {path}.'.format(path = old))
    for file in map_move.values():
        if file in set_file:
            raise ErrorEdit('A file is at {path} already.'.format(path = file))

    return map_move


# -----------------------------------------------------------------------------
def _redotted(tree: Tree, set_file: set[str], dotted_old: str, dotted_new: str) -> Edit:
    """
    Return the edit that writes dotted_new for the dotted name
    dotted_old, wherever it stands as a name of its own, in the code of
    each python module of set_file, and in the spelling of a type in
    each other file, such as that of an interface member.

    """

    edit = {}

    if not dotted_old or not dotted_new or dotted_old == dotted_new:
        return edit

    regex = re.compile(PATTERN_DOTTED.format(name = re.escape(dotted_old)))
    for file in sorted(set_file):
        text = _content(tree, file)
        if isinstance(text, bytes) or not regex.search(text):
            continue
        if pathlib.PurePosixPath(file).suffix == cctool.graph.extract.SUFFIX_PYTHON:
            edit[file] = _realigned(text, regex, dotted_new)
            continue
        text_new = REGEX_SPELLING.sub(lambda match: match.group(1) + regex.sub(dotted_new,
                                                                             match.group(2)),
                                      text)
        if text_new != text:
            edit[file] = text_new

    return edit


# -----------------------------------------------------------------------------
def _realigned(text: str, regex: re.Pattern, replacement: str) -> str:
    """
    Return text with each match of regex replaced by replacement, and
    each line that continues a bracket, and was aligned just inside it,
    moved as far as the bracket moves, so that the alignment holds.

    """

    list_old   = text.split('\n')
    list_new   = [regex.sub(replacement, line) for line in list_old]
    list_shift = [[(match.end(), len(replacement) - len(match.group(0)))
                   for match in regex.finditer(line)] for line in list_old]
    map_indent = {}

    for (row, column, row_close) in _brackets(text):
        column_new = column + map_indent.get(row, 0) + sum(
                        delta for (end, delta) in list_shift[row] if end <= column)
        for row_inner in range(row + 1, row_close + 1):
            line = list_old[row_inner]
            if line.strip() and len(line) - len(line.lstrip(' ')) == column + 1:
                map_indent.setdefault(row_inner, column_new - column)

    for (row, delta) in map_indent.items():
        line = list_new[row]
        if delta > 0:
            list_new[row] = ' ' * delta + line
        elif delta < 0 and not line[:-delta].strip():
            list_new[row] = line[-delta:]

    return '\n'.join(list_new)


# -----------------------------------------------------------------------------
def _brackets(text: str) -> list[tuple[int, int, int]]:
    """
    Return each bracket of the python code text that is closed on a
    later line than it opens on, as the line and column it opens at and
    the line it closes on, counted from 0, in the order they open. Code
    that cannot be read gives none.

    """

    list_open    = []
    list_bracket = []

    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.OP:
                continue
            if token.string in '([{':
                list_open.append(token.start)
            elif token.string in ')]}' and list_open:
                (row, column) = list_open.pop()
                if token.end[0] > row:
                    list_bracket.append((row - 1, column, token.end[0] - 1))
    except (tokenize.TokenError, SyntaxError):
        return []

    return sorted(list_bracket)


# -----------------------------------------------------------------------------
def _moved_ids(tree: Tree, map_move: dict[str, str]) -> dict[str, str]:
    """
    Return the new id of each item that takes its id from the place of
    a file map_move moves, keyed by its old id: the item of a python
    module or logic program file, and each item it holds whose id is
    the name of the module, a full stop and a name of its own.

    """

    map_id   = {}
    map_name = {}

    for (file_old, file_new) in map_move.items():
        suffix = pathlib.PurePosixPath(file_old).suffix
        if suffix not in cctool.graph.extract.MAP_PREFIX_MODULE:
            continue
        name_old = cctool.graph.extract.module_name(pathlib.Path(file_old))
        name_new = cctool.graph.extract.module_name(pathlib.Path(file_new))
        map_name[file_old] = (name_old.partition(DELIM_PREFIX)[2],
                              name_new.partition(DELIM_PREFIX)[2])

    for (id_item, row) in tree.map_item.items():
        file = cctool.graph.extract.file_of(row[3])
        if file not in map_name:
            continue
        (prefix, _, name) = id_item.partition(DELIM_PREFIX)
        if prefix not in SET_PREFIX_SOURCE:
            continue
        (name_old, name_new) = map_name[file]
        if name_old == name_new:
            continue
        if name == name_old or name.startswith(name_old + DELIM_NAME):
            map_id[id_item] = prefix + DELIM_PREFIX + name_new + name[len(name_old):]

    return map_id


# -----------------------------------------------------------------------------
def _renamed_ids(tree: Tree, map_id: dict[str, str]) -> Edit:
    """
    Return the edit that gives each item named in map_id its new id in
    every YAML document that names it, in every string of a logic
    program that is its id, and anywhere in the code of a python module,
    as a test names the item it reads, all in one pass, the longest ids
    first.

    """

    if not map_id:
        return {}

    alternation = '|'.join(re.escape(id_old) for id_old in sorted(map_id, key = len,
                                                                   reverse = True))
    regex       = re.compile(PATTERN_WHOLE_ID.format(id = '(?:' + alternation + ')'))
    regex_rule  = re.compile('"(' + alternation + ')"')
    edit        = {}

    for file in cctool.graph.extract.files(tree.map_document):
        text      = tree.text(file)
        list_line = text.split('\n')
        list_span = cctool.edit.layout.spans(text, pathlib.Path(file))
        if pathlib.Path(file).suffix == cctool.graph.extract.SUFFIX_PYTHON:
            list_span = [(0, len(list_line) - 1)]
        for (first, last) in list_span:
            list_line[first:last + 1] = [regex.sub(lambda match: map_id[match.group(0)], line)
                                         for line in list_line[first:last + 1]]
        renamed = '\n'.join(list_line)
        if pathlib.Path(file).suffix == cctool.graph.extract.SUFFIX_PROGRAM:
            renamed = regex_rule.sub(lambda match: '"' + map_id[match.group(1)] + '"', renamed)
        if renamed != text:
            edit[file] = _format(renamed, file)

    return edit


# -----------------------------------------------------------------------------
def dotted(path: pathlib.PurePosixPath) -> str:
    """
    Return the dotted name that python imports the module or package at
    path by, or an empty string if path is not under src.

    """

    is_module = path.suffix == cctool.graph.extract.SUFFIX_PYTHON
    list_part = list(path.with_suffix('').parts if is_module else path.parts)
    if len(list_part) < 2 or list_part[0] != cctool.graph.extract.DIR_IMPORT_ROOT:
        return ''
    if list_part[-1] == cctool.graph.extract.NAME_PACKAGE:
        list_part = list_part[:-1]
    return '.'.join(list_part[1:])


# -----------------------------------------------------------------------------
def _content(tree: Tree, relative: str) -> str | bytes:
    """
    Return the text of the file at relative, or its bytes if it is not
    text.

    """

    if relative in tree.edit:
        return tree.edit[relative]
    data = (tree.root / relative).read_bytes()
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return data


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

        header: PATH, or PATH::CLASS::FUNCTION
        id:     ID
        field:  {NAME: VALUE, ...}
        link:   [[RELATION, TARGET], ...]

        link:   [SOURCE, RELATION, TARGET]

        unlink: [SOURCE, RELATION, TARGET]

        set:    [ID, PATH, VALUE]

        unset:  [ID, PATH]

        remove: ID

        rename: [OLD, NEW]

        move:   [OLDPATH, NEWPATH]

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

    # A header on a class or function, keyed as
    # cctool.graph.extract.file_of says, goes in its docstring.
    #
    if isinstance(operation, dict) and isinstance(operation.get(KEY_HEADER), str):
        function = (header_definition
                    if cctool.graph.extract.DELIM_DEFINITION in operation[KEY_HEADER]
                    else header)
        return function(tree,
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
                                   (KEY_UNSET, unset_field, 2), (KEY_RENAME, rename, 2),
                                   (KEY_MOVE, move, 2)):
        if isinstance(operation, dict) and set(operation) == {key}:
            list_arg = operation[key]
            if isinstance(list_arg, list) and len(list_arg) == count:
                return function(tree, *map(str, list_arg))

    raise ErrorEdit('An operation of a batch is not one of new, header, link, unlink, set, '
                    'unset, remove, rename or move: {operation}'.format(operation = operation))


# -----------------------------------------------------------------------------
def apply(tree: Tree, is_written: bool = True) -> cctool.check.check.Failures:
    """
    Check the tree with the edits made so far in place, and return the
    failures they add. Write them only if they add none and is_written.

    A failure is compared without its line, since an edit moves the
    lines below it.

    """

    cache  = cctool.check.check.CACHE_SCHEMA
    before = cctool.check.check.check_documents(tree.map_original, cache)
    after  = cctool.check.check.check_documents(tree.map_document, cache)

    if _place(tree, after):
        after = cctool.check.check.check_documents(tree.map_document, cache)

    added  = _added(before, after)

    if is_written and not added:
        _write(tree)

    return added


# -----------------------------------------------------------------------------
def _place(tree: Tree, failures: cctool.check.check.Failures) -> bool:
    """
    Move each file the edits of tree make, and that failures say is in
    the wrong place, to where it belongs. Return True if any moved.

    """

    edit = {}

    for (_, relative, expected) in failures.get(NAME_MISPLACED, []):
        is_new = relative not in tree.map_original and tree.edit.get(relative) is not None
        if is_new and expected not in tree.map_document:
            edit[expected] = tree.edit.pop(relative)
            tree.map_document.pop(relative)

    if edit:
        tree.update(edit)

    return bool(edit)


# -----------------------------------------------------------------------------
def _write(tree: Tree) -> None:
    """
    Write the edits of tree, all or none. Each new text is written
    beside its file first, and only once every one is written does any
    take the place of its file, so that a write that fails leaves the
    tree as it was. Raise ErrorEdit if one fails.

    """

    list_staged = []

    try:
        for (relative, text) in tree.edit.items():
            if text is None:
                continue
            path   = tree.root / relative
            staged = path.with_name(path.name + SUFFIX_STAGED)
            path.parent.mkdir(parents = True, exist_ok = True)
            list_staged.append((staged, path))
            if isinstance(text, bytes):
                staged.write_bytes(text)
            else:
                staged.write_text(text, encoding = 'utf-8')
    except OSError as error:
        for (staged, _) in list_staged:
            staged.unlink(missing_ok = True)
        raise ErrorEdit('The edit could not be written, so nothing was changed: '
                        '{error}'.format(error = error)) from error

    for (staged, path) in list_staged:
        os.replace(staged, path)

    for (relative, text) in tree.edit.items():
        if text is None:
            (tree.root / relative).unlink(missing_ok = True)
            _prune(tree.root, (tree.root / relative).parent)


# -----------------------------------------------------------------------------
def _prune(root: pathlib.Path, path: pathlib.Path) -> None:
    """
    Remove the folder at path, and each folder above it below root, for
    as long as it holds nothing but a cache of compiled python, as a
    move or a removal can leave it.

    """

    while path != root and root in path.parents and path.is_dir():
        list_name = [child.name for child in path.iterdir()]
        if any(name != DIR_CACHE for name in list_name):
            return
        if DIR_CACHE in list_name:
            for child in (path / DIR_CACHE).iterdir():
                child.unlink()
            (path / DIR_CACHE).rmdir()
        path.rmdir()
        path = path.parent


# -----------------------------------------------------------------------------
def _added(before: cctool.check.check.Failures,
           after:  cctool.check.check.Failures) -> cctool.check.check.Failures:
    """
    Return the failures in after that are not in before, compared
    without their lines.

    """

    map_column = cctool.check.check.columns()
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

    set_inverse = {row[0] for row in tree.facts['inverse_relation']
                   if row[1] == RELATION_HAS_ITEMS_HELD_IN_REGISTER}

    for (source, relation, target) in sorted(tree.facts['edge']):
        if source == id_type and relation == RELATION_HAS_ITEMS_HELD_IN_REGISTER:
            return target
        if target == id_type and relation in set_inverse:
            return source

    return None


# -----------------------------------------------------------------------------
def _rights(tree: Tree) -> dict:
    """
    Return the rights fields of the segment item of the tree, and not of
    a tree it consumes.

    """

    list_file = [row[3] for (id_self, row) in tree.map_item.items()
                 if id_self.startswith(cctool.graph.extract.PREFIX_SEGMENT)
                 and cctool.graph.extract.consumer(row[3]) is None]

    if len(list_file) != 1:
        raise ErrorEdit('The tree holds {count} segment items, not 1, so none gives the rights '
                        'of a new item.'.format(count = len(list_file)))

    (document, _) = tree.map_document[list_file[0]]

    return {key: _plain(document[key]) for key in TUPLE_KEY_RIGHTS if key in document}


# -----------------------------------------------------------------------------
def _plain(value):
    """
    Return value with the mappings and lists that YAML read it into
    made plain. Text written as a block keeps its style, since that is
    what marks it as prose.

    """

    if isinstance(value, dict):
        return {key: _plain(each) for (key, each) in value.items()}
    if isinstance(value, list):
        return [_plain(each) for each in value]
    if isinstance(value, ruamel.yaml.scalarstring.LiteralScalarString):
        return value
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
            raise ErrorEdit('The field {key} is not set this way: {how}.'.format(
                                key = key, how = MAP_KEY_FIXED[key]))

    return ({key: map_field[key] for key in TUPLE_KEY_PROSE if key in map_field}
            | {key: value for (key, value) in map_field.items() if key not in TUPLE_KEY_PROSE})


# -----------------------------------------------------------------------------
def _minted(value: typing.Any) -> typing.Any:
    """
    Return value with a new guid_self after each id_self in it that has
    none, so that an embedded item given in a field, such as a member
    of an interface control document, gets its guid as a new item does.

    """

    if isinstance(value, list):
        return [_minted(each) for each in value]
    if not isinstance(value, dict):
        return value

    map_new = {}

    for (key, each) in value.items():
        map_new[key] = _minted(each)
        if key == KEY_ID_SELF and isinstance(each, str) and KEY_GUID_SELF not in value:
            map_new[KEY_GUID_SELF] = _guid(each)

    return map_new


# -----------------------------------------------------------------------------
def _guid(id_self: str) -> str:
    """
    Return a new guid for the item id_self: the prefix of its type and
    32 hex digits.

    """

    (prefix, _, _) = id_self.partition(DELIM_PREFIX)
    return '{prefix}_{hex}'.format(prefix = prefix, hex = uuid.uuid4().hex)


# -----------------------------------------------------------------------------
def _referenced(tree: Tree, map_field: dict) -> dict:
    """
    Return the fields of map_field, with the guid of each item that a
    field id_<field> names put after it as guid_<field>, unless given.
    A field at any depth is filled, so that the edges of an embedded
    item and the ends of an edge get their guids. An item that the
    fields themselves hold is named by the guid it is given there.

    """

    map_guid = dict(_held(map_field))

    def filled(value: typing.Any) -> typing.Any:
        if isinstance(value, list):
            return [filled(each) for each in value]
        if not isinstance(value, dict):
            return value
        map_new = {}
        for (key, each) in value.items():
            map_new[key] = filled(each)
            if not (key.startswith(PREFIX_ID) and key != KEY_ID_SELF and isinstance(each, str)):
                continue
            key_guid = PREFIX_GUID + key[len(PREFIX_ID):]
            if key_guid not in value:
                map_new[key_guid] = map_guid.get(each) or tree.guid(each)
        return map_new

    return filled(map_field)


# -----------------------------------------------------------------------------
def _held(value: typing.Any) -> typing.Iterator[tuple[str, str]]:
    """
    Yield the id and guid of each item that value holds at any depth.

    """

    if isinstance(value, list):
        for each in value:
            yield from _held(each)
    elif isinstance(value, dict):
        if isinstance(value.get(KEY_ID_SELF), str) and isinstance(value.get(KEY_GUID_SELF), str):
            yield (value[KEY_ID_SELF], value[KEY_GUID_SELF])
        for each in value.values():
            yield from _held(each)


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
    the last field before the aliases and edges. A field guid_<field>
    goes after id_<field>.

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

    list_before = [each for each in list_key if each not in (KEY_ALIAS, KEY_EDGE)]
    list_tail   = [each for each in list_key if each in (KEY_ALIAS, KEY_EDGE)]
    if list_tail:
        list_before = list_key[:list_key.index(list_tail[0])]
    return list_before[-1]


# -----------------------------------------------------------------------------
def _format(text: str, relative: str) -> str:
    """
    Return text, the new content of the file at relative, laid out.

    """

    try:
        return cctool.edit.layout.format_file(text, pathlib.Path(relative))
    except cctool.edit.layout.Unsupported as error:
        raise ErrorEdit('The edit leaves {file} unlaid: {error}'.format(
                                                file = relative, error = error)) from error


# -----------------------------------------------------------------------------
def _append_entry(tree: Tree, id_register: str, map_field: dict) -> Edit:
    """
    Return the edit that adds an entry with map_field at the end of the
    entries of the register id_register, under a banner. Empty entries
    are written out in full with the entry as their first.

    """

    item      = _Item(tree, id_register)
    map_entry = item.node.get(KEY_ENTRIES)

    if not isinstance(map_entry, dict):
        raise ErrorEdit('{id} has no entries to add to.'.format(id = id_register))

    if map_entry:
        item.node    = map_entry
        (_, end)     = item.extent(list(map_entry.keys())[-1])
        column       = item.column(list(map_entry.keys())[-1])
        start        = end
        list_line    = ['']
    else:
        (start, end) = item.extent(KEY_ENTRIES)
        column       = item.column(KEY_ENTRIES) + 2
        list_line    = [' ' * (column - 2) + KEY_ENTRIES + ':']

    id_self     = map_field[KEY_ID_SELF]
    head        = ' ' * column + '# '
    list_line  += [head + '-' * (LENGTH_BANNER - len(head)),
                   head + '{id} -- {title}'.format(id    = id_self,
                                                   title = map_field.get('title', '')),
                   head.rstrip(),
                   ' ' * column + id_self + ':']

    list_line += cctool.edit.layout.dump(map_field, column + 2)

    return item.replace(start, end, list_line)


# -----------------------------------------------------------------------------
def _node(node: typing.Any, id_item: str) -> typing.Any:
    """
    Return the mapping within node whose id_self is id_item: a register
    entry among its entries, or an item embedded at any depth, such as an
    interface member or a dataflow node. Return None if there is none.

    """

    if isinstance(node, dict) and node.get(KEY_ID_SELF) == id_item:
        return node

    if isinstance(node, dict):
        node = list(node.values())
    if not isinstance(node, list):
        return None

    for value in node:
        found = _node(value, id_item)
        if found is not None:
            return found
    return None


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

        (_, _, holder, key, _) = tree.map_item[id_item]
        relative               = cctool.graph.extract.file_of(key)
        path                   = pathlib.Path(relative)

        text             = tree.text(relative)
        (document, base) = cctool.graph.extract.parse_all(text, path)[key]

        # The YAML document of a class or function is indented as its
        # docstring is, and the lines of the document are read and
        # written without that indentation.
        #
        self.relative  = relative
        self.list_line = text.split('\n')
        self.base      = base - 1
        self.mark      = ('' if path.suffix in (cctool.graph.extract.SUFFIX_YAML,
                                                cctool.graph.extract.SUFFIX_PYTHON)
                          else cctool.graph.extract.mark_comment(path))
        line_open      = self.list_line[self.base]
        self.indent    = line_open[:len(line_open) - len(line_open.lstrip())]

        self.node = _node(document, id_item) if holder else document

        if self.node is None:
            raise ErrorEdit('{id} is not found in {file}.'.format(id = id_item, file = relative))

    # -------------------------------------------------------------------------
    def line(self, index: int) -> str:
        """
        Return the line of the file at index, without its comment
        marker.

        """

        text = self.list_line[index]
        if self.mark and text.startswith(self.mark):
            text = text[len(self.mark):].removeprefix(' ')
        return text.removeprefix(self.indent)

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

        if self.indent:
            return self.indent + text if text else ''
        if not self.mark:
            return text
        return self.mark + (' ' + text if text else '')
