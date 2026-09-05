"""
---

id_self:                pym_cc_public.load.python
guid_self:              pym_db9a9fb33495409c9a6615cb3d58d00d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Python loader
brief:                  |
                        Load the data item embedded in a python source
                        file.
description:            |
                        A python source file is code, and also carries
                        a data item describing itself. That item lives
                        in the module docstring as a YAML document
                        opened by --- and closed by three full stops.

                        The file is read with the abstract syntax
                        tree. Nothing is imported.
relation:               []

...
"""


import ast
import typing

import ruamel.yaml


ENCODING_DEFAULT = 'utf-8'

MARKER_OPEN      = '---'
MARKER_CLOSE     = '...'


# What this loader raises for a defective document.
#
ERROR_LOAD = (SyntaxError, ruamel.yaml.YAMLError)

KIND_MODULE   = 'module'
KIND_CLASS    = 'class'
KIND_FUNCTION = 'function'

NODE_DEFINITION = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


# -----------------------------------------------------------------------------
class ErrorMetadataMissing(Exception):
    """
    Raised for a python file carrying no data item.

    Every python package and module is meant to be identifiable and
    part of the traceability graph, so a file with no metadata is a
    fault rather than a file of a different kind.

    """



# -----------------------------------------------------------------------------
class ErrorEllipsisInProse(Exception):
    """
    Raised where a data item is closed before its author meant it to be.

    The document end marker is three full stops, which is also how an
    ellipsis is written. A description containing one truncates the
    item at that point, and the truncation is silent where what remains
    happens to parse.

    """



# -----------------------------------------------------------------------------
class Metadata(typing.NamedTuple):
    """
    One YAML document found in a docstring, and where it sits.

    kind says what the docstring belongs to. path is the run of
    definition names from the module down to it, empty for the module
    itself. first and last delimit the document's lines in the source,
    half open and zero based, excluding the marker lines. indent is the
    column the markers sit at.

    """

    kind:   str
    path:   tuple
    first:  int
    last:   int
    indent: int
    text:   str


# -----------------------------------------------------------------------------
def iter_metadata(text):
    """
    Yield a Metadata for every docstring in text that holds a document.

    Found by walking the syntax tree rather than by searching the text,
    so that a marker in code or in a string is never mistaken for one,
    and so that each document is known to belong to a definite part of
    the program.

    """

    list_line = text.splitlines()

    yield from _walk(ast.parse(text), (), list_line)


# -----------------------------------------------------------------------------
def _walk(node, path, list_line):
    """
    Yield the documents at node and beneath it.

    """

    if isinstance(node, (ast.Module, *NODE_DEFINITION)):

        found = _document(node, path, list_line)

        if found is not None:
            yield found

    for child in ast.iter_child_nodes(node):

        if isinstance(child, NODE_DEFINITION):
            yield from _walk(child, path + (child.name,), list_line)
        else:
            yield from _walk(child, path, list_line)


# -----------------------------------------------------------------------------
def _document(node, path, list_line):
    """
    Return the Metadata held in node's docstring, or None.

    """

    if not (node.body and isinstance(node.body[0], ast.Expr)
                      and isinstance(node.body[0].value, ast.Constant)
                      and isinstance(node.body[0].value.value, str)):
        return None

    expr  = node.body[0]
    begin = expr.lineno - 1
    end   = expr.end_lineno

    first = next((i for i in range(begin, end)
                    if list_line[i].strip() == MARKER_OPEN), None)

    if first is None:
        return None

    last = next((i for i in range(first + 1, end)
                   if list_line[i].strip() == MARKER_CLOSE), None)

    if last is None:
        return None

    # A second opener, or anything but blank lines, after the close and
    # before the docstring ends means the close was not where the
    # author meant the document to end.
    #
    if any(list_line[i].strip() and not list_line[i].strip().startswith('"')
                                and not list_line[i].strip().startswith("'")
                for i in range(last + 1, end)):
        raise ErrorEllipsisInProse(
            'Text follows the closing {close} of a data item in the '
            'docstring at line {line}. A line holding only three full '
            'stops closes the document.'.format(close = MARKER_CLOSE,
                                                line  = last + 1))

    indent = len(list_line[first]) - len(list_line[first].lstrip())
    kind   = (KIND_MODULE if isinstance(node, ast.Module)
              else KIND_CLASS if isinstance(node, ast.ClassDef)
              else KIND_FUNCTION)

    return Metadata(kind   = kind,
                    path   = path,
                    first  = first + 1,
                    last   = last,
                    indent = indent,
                    text   = _dedent(list_line[first + 1 : last], indent))


# -----------------------------------------------------------------------------
def _dedent(list_line, indent):
    """
    Return the lines joined, with the docstring's own indent removed.

    """

    return '\n'.join(line[indent:] if line[:indent].strip() == '' else line
                     for line in list_line) + '\n'


# -----------------------------------------------------------------------------
class Definition(typing.NamedTuple):
    """
    One class or function in a source file, whether or not its docstring
    holds a document: what it is, the run of names down to it, and its
    syntax tree node.

    """

    kind: str
    path: tuple
    node: typing.Any


# -----------------------------------------------------------------------------
def iter_definition(text):
    """
    Yield a Definition for every class and function in text, outermost
    first.

    """

    yield from _walk_definition(ast.parse(text), ())


# -----------------------------------------------------------------------------
def _walk_definition(node, path):
    """
    Yield the definitions beneath node.

    """

    for child in ast.iter_child_nodes(node):
        if isinstance(child, NODE_DEFINITION):
            kind = KIND_CLASS if isinstance(child, ast.ClassDef) else KIND_FUNCTION
            yield Definition(kind, path + (child.name,), child)
            yield from _walk_definition(child, path + (child.name,))
        else:
            yield from _walk_definition(child, path)


# -----------------------------------------------------------------------------
def iter_document(data: bytes, encoding: str | None = None):
    """
    Yield (kind, path, document) for every docstring document in a
    python source file, the module's first.

    The module must carry one. A class or function carries one only
    where something needs to name it, and each such document is an
    item of its own.

    """

    if encoding is None:
        encoding = ENCODING_DEFAULT

    text       = data.decode(encoding)
    list_found = list(iter_metadata(text))

    if not any(m.kind == KIND_MODULE for m in list_found):
        raise ErrorMetadataMissing(
            'The module docstring holds no data item. Every python package '
            'and module carries one, opened by a line of {open} and closed '
            'by a line of {close}.'.format(open  = MARKER_OPEN,
                                           close = MARKER_CLOSE))

    yaml = ruamel.yaml.YAML(typ = 'safe')

    for found in list_found:
        yield (found.kind, found.path, yaml.load(found.text))


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the data item embedded in a python source file.

    Python source is UTF-8 unless it says otherwise, and the coding
    declaration that says otherwise is not honoured here -- nothing in
    this system is written in anything else, and reading one would mean
    decoding twice.

    The item is the document in the module docstring. Documents in the
    docstrings of classes and functions are located by the same walk
    and are not yet items of their own.

    """

    if encoding is None:
        encoding = ENCODING_DEFAULT

    text  = data.decode(encoding)
    found = next((m for m in iter_metadata(text) if m.kind == KIND_MODULE),
                 None)

    if found is None:
        raise ErrorMetadataMissing(
            'The module docstring holds no data item. Every python package '
            'and module carries one, opened by a line of {open} and closed '
            'by a line of {close}.'.format(open  = MARKER_OPEN,
                                           close = MARKER_CLOSE))

    return ruamel.yaml.YAML(typ = 'safe').load(found.text)
