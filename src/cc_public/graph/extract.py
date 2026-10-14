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
import hashlib
import pathlib
import re
import typing

import ruamel.yaml
import ruamel.yaml.scalarstring


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
KEY_ALIAS         = 'alias'
KEY_ACYCLIC       = 'acyclic'
KEY_REF           = '$ref'

# Fields whose text names no item: identity, aliases, which name what
# no longer exists, and patterns. A field named id_<role> or
# guid_<role> is a reference, and is read as one.
#
SET_KEY_UNNAMED   = {'id_self', 'guid_self', 'alias', 'prefix', 'regex_id', 'pattern',
                     '$id', '$schema', '$ref'}

# A word shaped like an id, not part of a path or of a longer word. A
# file name is read as the id it is named for, and a word that a * ends
# is a pattern, not a mention.
#
REGEX_MENTION     = re.compile(r'(?<![A-Za-z0-9_$./-])[a-z]{1,8}_[a-z0-9][a-z0-9_]*'
                               r'(?:\.[a-z0-9_][a-z0-9_]*)*')
REGEX_SUFFIX      = re.compile(r'\.(?:yaml|py|dl|toml|json|md)$')
MARK_GLOB         = '*'
REGEX_REF         = re.compile(r'/(sch_[a-z0-9_]+)\.yaml')

PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
DIR_DATA          = '_data'
SUFFIX_YAML       = '.yaml'
SUFFIX_PYTHON     = '.py'
SUFFIX_DATALOG    = '.dl'

# A document opens with this line and closes with the next. In a
# comment header each line also begins with the comment marker: # in
# most files, and // in Datalog.
#
LINE_OPEN         = '---'
LINE_CLOSE        = '...'
MARK_COMMENT      = '#'
MAP_MARK_COMMENT  = {SUFFIX_DATALOG: '//'}

# A script may open with a line that names its interpreter. Its comment
# header then opens on the line after.
#
MARK_SHEBANG      = '#!'

# Directories that hold no items: version control, environments,
# caches and local tools.
#
SET_DIR_SKIP      = {'.git', '.pixi', '.venv', '__pycache__', '_tools'}

# The documents read so far, keyed by the path and the digest of the
# file that holds each. It is emptied when it holds this many.
#
MAP_READ          = {}
COUNT_READ        = 4096

# Each base relation: its columns, and what one row of it states. A
# column is a symbol unless its name is followed by :number. A line
# is the line of the file, counted from 1, that the key of the field
# is on: id_self for an item, and id_<role> for a reference.
#
TYPE_SYMBOL       = 'symbol'
DELIM_TYPE        = ':'

RELATION          = {
    'item':               (('id', 'guid', 'holder', 'file', 'line:number'),
                           'The item id, with guid, is written in file at line. holder '
                           'is the id of the item that contains it, or empty if none '
                           'does.'),
    'reference':          (('holder', 'role', 'id', 'guid', 'file', 'line:number'),
                           'The item holder names the item id, with guid, in a pair '
                           'of fields id_<role> and guid_<role>, written in file at '
                           'line.'),
    'edge':               (('source', 'relation', 'target'),
                           'The item source records an edge of relation to target, '
                           'as written. primary_edge reads edges through inverses.'),
    'type_prefix':        (('type', 'prefix', 'regex'),
                           'The type has the id prefix, and its ids match regex.'),
    'relation_domain':    (('relation', 'type'),
                           'The source of an edge of relation may be of type.'),
    'relation_range':     (('relation', 'type'),
                           'The target of an edge of relation may be of type.'),
    'relation_inverse':   (('inverse', 'relation'),
                           'An edge of inverse is an edge of relation, reversed.'),
    'register_entry_key': (('register', 'key', 'id'),
                           'The register holds, under key, a register entry with id.'),
    'module_name':        (('id', 'expected'),
                           'A python module or package, or a Datalog source file, '
                           'holds the item id, and its place in the tree calls for the '
                           'id expected.'),
    'tree_file':          (('file',),
                           'The tree holds file, whether or not the file holds an '
                           'item.'),
    'mention':            (('holder', 'id', 'file', 'line:number'),
                           'The text of a field of the item holder names id, in file '
                           'at line. Any word shaped like an id is a mention, but only '
                           'one with the prefix of a known type need name an item.'),
    'alias':              (('id', 'alias'),
                           'The item id was once named alias.'),
    'relation_acyclic':   (('relation',),
                           'No chain of edges of relation may lead from an item back '
                           'to itself.'),
    'schema_ref':         (('holder', 'schema', 'file', 'line:number'),
                           'The schema holder refers to the schema with a $ref, in '
                           'file at line.'),
}

# Python modules are imported with src as the root of the path. The
# item of a package is held in the docstring of its __init__ module.
# A Datalog source file is named in the same way as a python module.
#
DIR_IMPORT_ROOT   = 'src'
MAP_PREFIX_MODULE = {SUFFIX_PYTHON: 'pym_', SUFFIX_DATALOG: 'dls_'}
PREFIX_PACKAGE    = 'pyp_'
NAME_PACKAGE      = '__init__'
DELIM_MODULE      = '.'

Facts             = dict[str, set[tuple[str, ...]]]
Documents         = dict[str, tuple[typing.Any, int]]


# -----------------------------------------------------------------------------
def extract(root: pathlib.Path) -> Facts:
    """
    Return the facts of the tree under root, keyed by relation.

    """

    return facts_of(documents(root))


# -----------------------------------------------------------------------------
def documents(root: pathlib.Path) -> Documents:
    """
    Return each document in the tree under root, with the line of its
    file that its first line is on, keyed by the file's path relative
    to root.

    Documents are read from YAML files under a _data directory, from
    the module docstring of a python module, and from the comment
    header of any other file. A file that holds no document is kept,
    with None in its place, so that the tree's files are known.

    """

    map_document = {}

    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if SET_DIR_SKIP.intersection(relative.parts) or not path.is_file():
            continue
        map_document[str(relative)] = read(path, relative)

    return map_document


# -----------------------------------------------------------------------------
def facts_of(map_document: Documents) -> Facts:
    """
    Return the facts that the documents hold, keyed by relation.

    """

    facts = {name: set() for name in RELATION}

    for (file, (document, base)) in map_document.items():
        facts['tree_file'].add((file,))
        if document is None:
            continue
        _walk(document, '', (file, base), facts)
        if pathlib.Path(file).suffix in MAP_PREFIX_MODULE and isinstance(document, dict):
            facts['module_name'].add((str(document.get(KEY_ID_SELF)),
                                      module_name(pathlib.Path(file))))

    return facts


# -----------------------------------------------------------------------------
def column(spec: str) -> tuple[str, str]:
    """
    Return the name and the type of the column that spec declares.

    """

    (name, _, type_column) = spec.partition(DELIM_TYPE)
    return (name.strip(), type_column.strip() or TYPE_SYMBOL)


# -----------------------------------------------------------------------------
def module_name(relative: pathlib.Path) -> str:
    """
    Return the id that names the python module or Datalog source file
    at relative: the prefix and the dotted name it would be imported
    under, in lower case. An __init__ module is named for its package.

    """

    list_part = list(relative.with_suffix('').parts)
    prefix    = MAP_PREFIX_MODULE[relative.suffix]

    if list_part and list_part[0] == DIR_IMPORT_ROOT:
        list_part = list_part[1:]

    if list_part and list_part[-1] == NAME_PACKAGE:
        list_part = list_part[:-1]
        prefix    = PREFIX_PACKAGE

    return prefix + DELIM_MODULE.join(list_part).lower()


# -----------------------------------------------------------------------------
def read(path: pathlib.Path, relative: pathlib.Path) -> tuple[typing.Any, int]:
    """
    Return the document that the file at path holds, or None if it
    holds none, and the line of the file that its first line is on.
    relative is the path of the file relative to the root of the tree.

    A YAML file or python module that holds what it held when it was
    last read gives the same document as then, the same object, so
    that what was found by checking it can be reused. A document is
    never changed once read.

    """

    if path.suffix in (SUFFIX_YAML, SUFFIX_PYTHON):
        data = path.read_bytes()
        key  = (str(relative), hashlib.blake2b(data, digest_size = 16).digest())
        if key not in MAP_READ:
            if len(MAP_READ) >= COUNT_READ:
                MAP_READ.clear()
            MAP_READ[key] = parse(data.decode('utf-8'), relative)
        return MAP_READ[key]

    # Any other file may be large, or not text, so only its head is
    # read, and only as far as a comment header could go.
    #
    return _header(_line_of_file(path), mark_comment(relative))


# -----------------------------------------------------------------------------
def parse(text: str, relative: pathlib.Path) -> tuple[typing.Any, int]:
    """
    Return the document that text holds, as the content of the file at
    relative, or None if it holds none, and the line of the file that
    its first line is on.

    """

    if relative.suffix == SUFFIX_YAML:
        if DIR_DATA not in relative.parts:
            return (None, 1)
        return (YAML.load(text), 1)

    if relative.suffix == SUFFIX_PYTHON:
        return _docstring(text)

    return _header(iter(text.splitlines()), mark_comment(relative))


# -----------------------------------------------------------------------------
def _docstring(text: str) -> tuple[typing.Any, int]:
    """
    Return the document in the module docstring of the python module
    text, or None if it holds none, and the line of the file that its
    first line is on.

    """

    module    = ast.parse(text)
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
def _line_of_file(path: pathlib.Path) -> typing.Iterator[str]:
    """
    Yield the lines of the file at path, and stop at the first that is
    not text.

    """

    try:
        with open(path, encoding = 'utf-8') as file:
            yield from file
    except UnicodeDecodeError:
        return


# -----------------------------------------------------------------------------
def mark_comment(relative: pathlib.Path) -> str:
    """
    Return the marker that begins a comment line in the file at
    relative.

    """

    return MAP_MARK_COMMENT.get(relative.suffix, MARK_COMMENT)


# -----------------------------------------------------------------------------
def _header(iter_line: typing.Iterator[str], mark: str) -> tuple[typing.Any, int]:
    """
    Return the document in the comment header that the lines open
    with, each line beginning with mark, or None if they do not open
    with one, and the line of the file that its first line is on. A
    line that names an interpreter may come before the header.

    """

    list_line = []
    base      = 1

    for line in iter_line:
        text = line.rstrip('\n')
        if base == 1 and (not list_line) and text.startswith(MARK_SHEBANG):
            base = 2
            continue
        if not text.startswith(mark):
            return (None, 1)
        text = text[len(mark):].removeprefix(' ')
        if (not list_line) and text != LINE_OPEN:
            return (None, 1)
        list_line.append(text)
        if text == LINE_CLOSE:
            return (YAML.load('\n'.join(list_line)), base)

    return (None, 1)


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
        for alias in _list_str(node.get(KEY_ALIAS)):
            facts['alias'].add((id_self, alias))
        holder = id_self

    _reference(node, holder, location, facts)
    _text(node, holder, location, facts)

    table = node.get(KEY_TABLE)

    if isinstance(id_self, str) and isinstance(table, dict):
        for (key, entry) in table.items():
            if isinstance(entry, dict):
                facts['register_entry_key'].add((id_self,
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
def _text(node:     dict[str, typing.Any],
          holder:   str,
          location: tuple[str, int],
          facts:    Facts) -> None:
    """
    Add a fact for each id that the text of a field of node mentions,
    and for each schema that node refers to with a $ref.

    """

    for (key, value) in node.items():
        if key == KEY_REF and isinstance(value, str):
            for match in REGEX_REF.finditer(value):
                facts['schema_ref'].add((holder, match.group(1), location[0],
                                         _line(node, key, location)))
        if key in SET_KEY_UNNAMED or key.startswith((PREFIX_ID, PREFIX_GUID)):
            continue
        if isinstance(value, str):
            _mention(value, holder, location[0], int(_line(node, key, location)), facts)
        elif isinstance(value, list):
            for (index, each) in enumerate(value):
                if isinstance(each, str):
                    _mention(each, holder, location[0],
                             int(_line_item(value, index, location)), facts)


# -----------------------------------------------------------------------------
def _mention(text: str, holder: str, file: str, line: int, facts: Facts) -> None:
    """
    Add a fact for each id that text mentions. line is the line of the
    file that the field holding text is on. The text of a block scalar
    begins on the line below its key.

    """

    offset = 1 if isinstance(text, ruamel.yaml.scalarstring.LiteralScalarString) else 0

    for match in REGEX_MENTION.finditer(text):
        if text.startswith(MARK_GLOB, match.end()):
            continue
        word = REGEX_SUFFIX.sub('', match.group(0))
        facts['mention'].add((holder, word, file,
                              str(line + offset + text.count('\n', 0, match.start()))))


# -----------------------------------------------------------------------------
def _line_item(node: list[typing.Any], index: int, location: tuple[str, int]) -> str:
    """
    Return the line of the file that item index of node is on, or 0 if
    the loader did not record it.

    """

    lc = getattr(node, 'lc', None)

    if lc is None:
        return '0'

    return str(location[1] + lc.item(index)[0])


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

    if node.get(KEY_ACYCLIC) is True:
        facts['relation_acyclic'].add((id_self,))

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
