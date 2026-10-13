"""
---

id_self:                pym_cc_public.graph.extract
guid_self:              pym_067145ba52314db69f64c5605d575451
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Fact extraction
brief:                  |
                        Extract the facts of the graph of data items
                        held in a tree.
description:            |
                        This module reads every item in the tree: the
                        YAML files under a _data directory, the module
                        docstrings of python modules, and the comment
                        headers of other files. It returns the facts
                        they hold, one set of rows for each base
                        relation. RELATION names each base relation,
                        its columns and what a row of it means, and is
                        the one place they are declared, for Datalog
                        and for SQL alike.
relation:               []

...
"""


import ast
import pathlib
import typing

import ruamel.yaml


# Round trip loading keeps the line and column of every key and value,
# so that a fact can later be traced to where it is written.
#
YAML              = ruamel.yaml.YAML(typ = 'rt')

KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_ID_RELATION   = 'id_relation'
KEY_ID_TARGET     = 'id_target'
KEY_TABLE         = 'table'
KEY_PREFIX        = 'prefix'
KEY_REGEX_ID      = 'regex_id'
KEY_INVERSE       = 'inverse'

PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
DIR_DATA          = '_data'
SUFFIX_YAML       = '.yaml'
SUFFIX_PYTHON     = '.py'

# A document opens with this line and closes with the next. In a
# comment header each line also begins with the comment marker.
#
LINE_OPEN         = '---'
LINE_CLOSE        = '...'
MARK_COMMENT      = '#'

# Directories that hold no items: version control, environments,
# caches and local tools.
#
SET_DIR_SKIP      = {'.git', '.pixi', '.venv', '__pycache__', '_tools'}

# Each base relation: its columns, and what one row of it states. A
# column is a symbol unless its name is followed by :number. A line
# is the line of the file, counted from 1, that the key of the field
# is on: id_self for an item, and id_<role> for a reference.
#
TYPE_SYMBOL       = 'symbol'
DELIM_TYPE        = ':'

RELATION          = {
    'item':             (('id', 'guid', 'holder', 'file', 'line:number'),
                         'The item id, with guid, is written in file at line. holder '
                         'is the id of the item that contains it, or empty if none '
                         'does.'),
    'reference':        (('holder', 'role', 'id', 'guid', 'file', 'line:number'),
                         'The item holder names the item id, with guid, in a pair '
                         'of fields id_<role> and guid_<role>, written in file at '
                         'line.'),
    'edge':             (('source', 'relation', 'target'),
                         'The item source records an edge of relation to target, '
                         'as written. primary_edge reads edges through inverses.'),
    'type_prefix':      (('type', 'prefix', 'regex'),
                         'The type has the id prefix, and its ids match regex.'),
    'relation_domain':  (('relation', 'type'),
                         'The source of an edge of relation may be of type.'),
    'relation_range':   (('relation', 'type'),
                         'The target of an edge of relation may be of type.'),
    'relation_inverse': (('inverse', 'relation'),
                         'An edge of inverse is an edge of relation, reversed.'),
    'entry_key':        (('register', 'key', 'id'),
                         'The register holds, under key, an entry with id.'),
    'module_name':      (('id', 'expected'),
                         'A python module or package holds the item id, and its '
                         'place in the tree calls for the id expected.'),
}

# Python modules are imported with src as the root of the path. The
# item of a package is held in the docstring of its __init__ module.
#
DIR_IMPORT_ROOT   = 'src'
PREFIX_MODULE     = 'pym_'
PREFIX_PACKAGE    = 'pyp_'
NAME_PACKAGE      = '__init__'
DELIM_MODULE      = '.'

Facts             = dict[str, set[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def extract(root: pathlib.Path) -> Facts:
    """
    Return the facts of the tree under root, keyed by relation.

    Items are read from YAML files under a _data directory, from the
    module docstring of a python module, and from the comment header
    of any other file.

    """

    facts = {name: set() for name in RELATION}

    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if SET_DIR_SKIP.intersection(relative.parts) or not path.is_file():
            continue
        (document, base) = _read(path, relative)
        if document is None:
            continue
        _walk(document, '', (str(relative), base), facts)
        if path.suffix == SUFFIX_PYTHON and isinstance(document, dict):
            facts['module_name'].add((str(document.get(KEY_ID_SELF)),
                                      _module_name(relative)))

    return facts


# -----------------------------------------------------------------------------
def column(spec: str) -> tuple[str, str]:
    """
    Return the name and the type of the column that spec declares.

    """

    (name, _, type_column) = spec.partition(DELIM_TYPE)
    return (name.strip(), type_column.strip() or TYPE_SYMBOL)


# -----------------------------------------------------------------------------
def _module_name(relative: pathlib.Path) -> str:
    """
    Return the id that names the python module at relative: the prefix
    and the dotted name it is imported under, in lower case. An
    __init__ module is named for its package.

    """

    list_part = list(relative.with_suffix('').parts)
    prefix    = PREFIX_MODULE

    if list_part and list_part[0] == DIR_IMPORT_ROOT:
        list_part = list_part[1:]

    if list_part and list_part[-1] == NAME_PACKAGE:
        list_part = list_part[:-1]
        prefix    = PREFIX_PACKAGE

    return prefix + DELIM_MODULE.join(list_part).lower()


# -----------------------------------------------------------------------------
def _read(path: pathlib.Path, relative: pathlib.Path) -> tuple[typing.Any, int]:
    """
    Return the document that the file at path holds, or None if it
    holds none, and the line of the file that its first line is on.

    """

    if path.suffix == SUFFIX_YAML:
        if DIR_DATA not in relative.parts:
            return (None, 1)
        with open(path, encoding = 'utf-8') as file:
            return (YAML.load(file), 1)

    if path.suffix == SUFFIX_PYTHON:
        return _docstring(path)

    return (_header(path), 1)


# -----------------------------------------------------------------------------
def _docstring(path: pathlib.Path) -> tuple[typing.Any, int]:
    """
    Return the document in the module docstring of the python module at
    path, or None if it holds none, and the line of the file that its
    first line is on.

    """

    module    = ast.parse(path.read_text(encoding = 'utf-8'))
    docstring = ast.get_docstring(module)

    if not (docstring and docstring.startswith(LINE_OPEN)):
        return (None, 1)

    # The docstring is cleaned of the blank lines that open it, so its
    # first line is that many lines below the opening quotes.
    #
    raw     = module.body[0].value.value
    leading = raw[:len(raw) - len(raw.lstrip())].count('\n')

    return (YAML.load(docstring), module.body[0].lineno + leading)


# -----------------------------------------------------------------------------
def _header(path: pathlib.Path) -> typing.Any:
    """
    Return the document in the comment header of the file at path, or
    None if the file does not open with one.

    """

    list_line = []

    try:
        with open(path, encoding = 'utf-8') as file:
            for line in file:
                text = line.rstrip('\n')
                if not text.startswith(MARK_COMMENT):
                    return None
                text = text[len(MARK_COMMENT):].removeprefix(' ')
                if (not list_line) and text != LINE_OPEN:
                    return None
                list_line.append(text)
                if text == LINE_CLOSE:
                    return YAML.load('\n'.join(list_line))
    except UnicodeDecodeError:
        return None

    return None


# -----------------------------------------------------------------------------
def _walk(node: typing.Any, holder: str, location: tuple[str, int], facts: Facts) -> None:
    """
    Add the facts held by node, whose nearest enclosing item is holder.
    location is the file that holds node, and the line of the file that
    the first line of its document is on.

    """

    if isinstance(node, list):

        for value in node:
            _walk(value, holder, location, facts)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)

    if isinstance(id_self, str):

        facts['item'].add((id_self,
                           str(node.get(KEY_GUID_SELF, '')),
                           holder,
                           location[0],
                           _line(node, KEY_ID_SELF, location)))
        _signature(id_self, node, facts)
        holder = id_self

    _reference(node, holder, location, facts)

    table = node.get(KEY_TABLE)

    if isinstance(id_self, str) and isinstance(table, dict):
        for (key, entry) in table.items():
            if isinstance(entry, dict):
                facts['entry_key'].add((id_self,
                                        str(key),
                                        str(entry.get(KEY_ID_SELF))))

    for value in node.values():
        _walk(value, holder, location, facts)


# -----------------------------------------------------------------------------
def _reference(node:     dict[str, typing.Any],
               holder:   str,
               location: tuple[str, int],
               facts:    Facts) -> None:
    """
    Add a fact for each reference that node makes, and for the edge
    that node is, if it is one.

    """

    for (key, value) in node.items():
        if key.startswith(PREFIX_ID) and key != KEY_ID_SELF and isinstance(value, str):
            role = key[len(PREFIX_ID):]
            guid = str(node.get(PREFIX_GUID + role, ''))
            facts['reference'].add((holder, role, value, guid, location[0],
                                    _line(node, key, location)))

    if isinstance(node.get(KEY_ID_RELATION), str):
        facts['edge'].add((holder,
                           node[KEY_ID_RELATION],
                           str(node.get(KEY_ID_TARGET))))


# -----------------------------------------------------------------------------
def _line(node: dict[str, typing.Any], key: str, location: tuple[str, int]) -> str:
    """
    Return the line of the file that key is on in node, or 0 if the
    loader did not record it.

    """

    lc = getattr(node, 'lc', None)

    if lc is None:
        return '0'

    return str(location[1] + lc.key(key)[0])


# -----------------------------------------------------------------------------
def _signature(id_self: str, node: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add the type and relation facts that an entry declares.

    """

    prefix   = node.get(KEY_PREFIX)
    regex_id = node.get(KEY_REGEX_ID)

    if isinstance(prefix, str) and isinstance(regex_id, str):
        facts['type_prefix'].add((id_self, prefix, regex_id))

    for name in ('domain', 'range'):
        for id_type in _list_str(node.get(name)):
            facts['relation_' + name].add((id_self, id_type))

    inverse = node.get(KEY_INVERSE)

    if isinstance(inverse, dict) and isinstance(inverse.get(KEY_ID_SELF), str):
        facts['relation_inverse'].add((inverse[KEY_ID_SELF], id_self))


# -----------------------------------------------------------------------------
def _list_str(value: typing.Any) -> list[str]:
    """
    Return value if it is a list of strings, and an empty list if not.

    """

    if isinstance(value, list) and all(isinstance(each, str) for each in value):
        return value
    return []
