"""
---

id_self:                pym_cctool.check.citation
guid_self:              pym_d64fb797adf84ca2b7348786859f0ca1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Citations of the tree
brief:                  |
                        Check that prose cites a file of the tree by
                        the part it means, and that the cited file
                        holds that part.
description:            |
                        WTP ruled on 2026-10-25 that prose cites code
                        and configuration by name, not by line number,
                        since a line number goes stale when the file
                        changes. A citation names a function, class
                        and method, constant or predicate of code with
                        within, a field of a configuration or data
                        file with at, a line that is not a field with
                        just after, and a section of markdown with
                        FILE#anchor. A citation by line of a file of
                        the tree is a failure, and so is a named part
                        that the cited file does not hold. A path
                        written as REV:PATH means the file in that
                        commit, and is not read.
edge:                   []

...
"""


import ast
import json
import os
import pathlib
import re
import tomllib
import typing

import ruamel.yaml

import cctool.graph.extract


# A citation names a file of the tree and the part of it that it means:
# within NAME for a function, class and method, constant or predicate of
# code; at KEY.PATH for a field of a configuration or data file, or just
# after KEY.PATH for a line that is not a field; FILE#anchor for a
# section of markdown. A part is named, not numbered, so that the
# citation holds while the lines of the file move. A citation of the
# lines of one commit names the commit, as REV:PATH, and is left alone.
#
COLUMNS_LINE      = ('file', 'line', 'id', 'citation')
COLUMNS_NAME      = ('file', 'line', 'id', 'cited', 'name')

# The files a citation may name, and the folders left out of them.
#
SET_DIR_SKIPPED   = {'.git', '.pixi', '_tools', '__pycache__', '.pytest_cache',
                     '.ruff_cache', 'node_modules', 'build', 'dist'}

# A path in prose, a citation by line after it, a named part after it, and
# a further name in a list of parts. A path just after a colon is the
# path of a file in a commit, REV:PATH, and is not read. A name that is a
# commit, a version or a plain word is taken as prose, not as a part,
# unless the cited file holds it.
#
REGEX_PATH        = re.compile(r'(?<![\w/.$:-])([\w.][\w./-]*[\w])')
REGEX_BY_LINE     = re.compile(r'(?:,? +lines? +\d+(?:-\d+)?|:\d+\b)')
REGEX_NAMED       = re.compile(r' +(within|at|just after) +([\w$][\w$.-]*[\w$]|[\w$])')
REGEX_ANCHOR      = re.compile(r'#([\w-]+)')
REGEX_MORE        = re.compile(r'(?:,| +and) +(?:within +|at +)?([\w$][\w$.-]*[\w$]|[\w$])')
REGEX_CODELIKE    = re.compile(r'[_.$A-Z0-9-]')
REGEX_PROSE       = re.compile(r'^(?:[0-9a-f]{7,40}|HEAD|\d[\w.]*)$')

# The definitions of a logic program: the head of a rule, a declaration
# in a comment, and a show statement.
#
REGEX_PREDICATE   = re.compile(r'^(?:% decl +|#show +)?([a-z_]\w*) *[(/]', re.MULTILINE)
REGEX_SHELL       = re.compile(r'^(\w+) *\( *\)', re.MULTILINE)
REGEX_HEADING     = re.compile(r'^#+ +(.+?) *#* *$', re.MULTILINE)

# The names of the parts of each file read, kept in one OS process and
# keyed by its path, mtime and size. It is emptied when it holds this
# many.
#
CACHE_PARTS       = {}
COUNT_PARTS       = 1024


# -----------------------------------------------------------------------------
def violations(root:         pathlib.Path,
               map_document: cctool.graph.extract.Documents) -> tuple[list, list]:
    """
    Return the rows of the two checks of citations in the prose of the
    documents of the tree at root: each citation of a file of the tree
    by line number, and each named part that the cited file does not
    hold. A row gives the file and line of the document, the id of the
    item, and the citation.

    """

    map_file   = files(root)
    list_line  = []
    list_name  = []

    for (key, (document, line)) in sorted(map_document.items()):
        file = cctool.graph.extract.file_of(key)
        for (id_item, text) in _texts(document, None):
            for (kind, citation, cited, name) in citations(text, root, map_file):
                if kind == 'line':
                    list_line.append((file, str(line), id_item or file, citation))
                elif not holds(root, cited, name):
                    list_name.append((file, str(line), id_item or file, cited, name))

    return (sorted(set(list_line)), sorted(set(list_name)))


# -----------------------------------------------------------------------------
def citations(text:     str,
              root:     pathlib.Path,
              map_file: dict[str, str]) -> list[tuple[str, str, str, str]]:
    """
    Return each citation of a file of the tree in text, as its kind
    (line or name), the citation as written, the cited file, and the
    part named, which is empty for a citation by line. map_file maps
    each way of writing the path of a file of the tree at root to the
    file.

    """

    text      = ' '.join(text.split())
    list_cite = []

    for match in REGEX_PATH.finditer(text):
        cited = map_file.get(match.group(1))
        if cited is None:
            continue
        rest = text[match.end():]
        found = REGEX_BY_LINE.match(rest)
        if found:
            list_cite.append(('line', match.group(1) + found.group(0), cited, ''))
            continue
        found = REGEX_ANCHOR.match(rest)
        if found and cited.endswith('.md'):
            list_cite.append(('name', match.group(1) + found.group(0), cited, found.group(1)))
            continue
        found = REGEX_NAMED.match(rest)
        if not found or REGEX_PROSE.match(found.group(2)):
            continue
        name = found.group(2)
        if REGEX_CODELIKE.search(name) or name in parts(root, cited):
            list_cite.append(('name', match.group(1) + found.group(0), cited, name))
        rest = rest[found.end():]
        while (found := REGEX_MORE.match(rest)) and found.group(1) in parts(root, cited):
            list_cite.append(('name', found.group(0).strip(), cited, found.group(1)))
            rest = rest[found.end():]

    return list_cite


# -----------------------------------------------------------------------------
def holds(root: pathlib.Path, cited: str, name: str) -> bool:
    """
    Return True if the file cited, a path relative to root, holds the
    part name.

    """

    return name in parts(root, cited)


# -----------------------------------------------------------------------------
def parts(root: pathlib.Path, cited: str) -> frozenset[str]:
    """
    Return the names of the parts of the file cited, a path relative to
    root, that a citation may name.

    """

    path = root / cited
    try:
        stat = path.stat()
    except OSError:
        return frozenset()
    return _parts(str(path), stat.st_mtime_ns, stat.st_size)


# -----------------------------------------------------------------------------
def _parts(path: str, mtime: int, size: int) -> frozenset[str]:
    """
    Return the names of the parts of the file at path, read once for
    each mtime and size.

    """

    key = (path, mtime, size)
    if key not in CACHE_PARTS:
        if len(CACHE_PARTS) >= COUNT_PARTS:
            CACHE_PARTS.clear()
        try:
            text  = pathlib.Path(path).read_text(encoding = 'utf-8')
            names = MAP_PARSER.get(pathlib.PurePosixPath(path).suffix, _names_shell)(text)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError, IndexError,
                ruamel.yaml.YAMLError):
            names = ()
        CACHE_PARTS[key] = frozenset(names)
    return CACHE_PARTS[key]


# -----------------------------------------------------------------------------
def _names_yaml(text: str) -> typing.Iterator[str]:
    """
    Yield the dotted path of each key of the first YAML document in
    text.

    """

    return _keys(next(iter(ruamel.yaml.YAML(typ = 'safe').load_all(text))), '')


# -----------------------------------------------------------------------------
def _names_shell(text: str) -> list[str]:
    """
    Return the name of each function of the shell script text.

    """

    return REGEX_SHELL.findall(text)


# -----------------------------------------------------------------------------
def anchor(heading: str) -> str:
    """
    Return the anchor of a markdown heading, as GitHub makes it: lower
    case, with punctuation dropped and spaces made hyphens.

    """

    return re.sub(r'[^\w -]', '', heading.strip().lower()).replace(' ', '-')


# -----------------------------------------------------------------------------
def _names_python(list_node: list, prefix: str) -> typing.Iterator[str]:
    """
    Yield the dotted name of each function, class and assigned name in
    list_node, and of those nested in its functions and classes.

    """

    for node in list_node:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = prefix + node.name
            yield name
            yield from _names_python(node.body, name + '.')
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                for item in ast.walk(target):
                    if isinstance(item, ast.Name):
                        yield prefix + item.id


# -----------------------------------------------------------------------------
def _keys(value: typing.Any, prefix: str) -> typing.Iterator[str]:
    """
    Yield the dotted path of each key of value, and of each item of its
    lists, by index.

    """

    if isinstance(value, dict):
        pairs = value.items()
    elif isinstance(value, list):
        pairs = enumerate(value)
    else:
        return
    for (key, item) in pairs:
        path = '{prefix}{key}'.format(prefix = prefix, key = key)
        yield path
        yield from _keys(item, path + '.')


# -----------------------------------------------------------------------------
def _texts(value: typing.Any, id_item: str | None) -> typing.Iterator[tuple[str | None, str]]:
    """
    Yield each string in value, with the id of the innermost item that
    holds it.

    """

    if isinstance(value, dict):
        id_here = value.get(cctool.graph.extract.KEY_ID_SELF)
        id_item = id_here if isinstance(id_here, str) else id_item
        for item in value.values():
            yield from _texts(item, id_item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item, id_item)
    elif isinstance(value, str):
        yield (id_item, value)


# -----------------------------------------------------------------------------
def files(root: pathlib.Path) -> dict[str, str]:
    """
    Return a map from each way prose may write the path of a file of the
    tree at root to its path: the path itself, and each tail of it after
    a slash that no other file shares.

    """

    list_file = []
    for (dir_here, list_dir, list_name) in os.walk(root):
        list_dir[:] = [name for name in list_dir
                       if name not in SET_DIR_SKIPPED and not name.endswith('.egg-info')]
        for name in list_name:
            relative = os.path.relpath(os.path.join(dir_here, name), root)
            list_file.append(relative.replace(os.sep, '/'))

    map_file  = {file: file for file in list_file}
    map_count = {}
    for file in list_file:
        list_part = file.split('/')
        for index in range(1, len(list_part)):
            tail = '/'.join(list_part[index:])
            map_count.setdefault(tail, set()).add(file)
    for (tail, set_file) in map_count.items():
        if len(set_file) == 1 and tail not in map_file:
            map_file[tail] = next(iter(set_file))

    return map_file


# How the names of the parts of a file are read, by its suffix. A file of
# another kind is read as a shell script.
#
MAP_PARSER        = {'.py':   lambda text: _names_python(ast.parse(text).body, ''),
                     '.lp':   REGEX_PREDICATE.findall,
                     '.yaml': _names_yaml,
                     '.yml':  _names_yaml,
                     '.lock': _names_yaml,
                     '.toml': lambda text: _keys(tomllib.loads(text), ''),
                     '.json': lambda text: _keys(json.loads(text), ''),
                     '.md':   lambda text: [anchor(heading)
                                            for heading in REGEX_HEADING.findall(text)]}
