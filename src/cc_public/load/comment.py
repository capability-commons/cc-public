"""
---

id_self:                pym_cc_public.load.comment
guid_self:              pym_53c01429c0ea42b4beb0f6a4ec7ac056
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Block comment loader
brief:                  |
                        The data item a stylesheet or a script carries
                        in the first block comment of the file.
description:            |
                        A language whose comments open with an oblique
                        and a star may carry a data item the way a
                        python file carries one in its module
                        docstring: as a YAML document opened by three
                        hyphens and closed by three full stops, inside
                        the first comment of the file. This module
                        reads that document and yields it.

                        It yields nothing where the file opens with no
                        comment, where the first comment holds no
                        document, or where the document is empty. A
                        file carrying none is passed over rather than
                        refused, which is where this differs from the
                        python loader, because a stylesheet or a
                        script may have been vendored from elsewhere
                        and a vendored file is not ours to name. Only
                        the first comment is examined, and only where
                        nothing but space precedes it, so a comment
                        inside a minified file is never mistaken for a
                        document.
relation:               []

...
"""


import typing

import ruamel.yaml


ENCODING_DEFAULT = 'utf-8'

OPEN         = '/*'
CLOSE        = '*/'
MARKER_OPEN  = '---'
MARKER_CLOSE = '...'

# What this loader raises for a defective document. A file carrying no
# document is not defective, so nothing is raised for one.
#
ERROR_LOAD = (ruamel.yaml.YAMLError,)


# -----------------------------------------------------------------------------
class Metadata(typing.NamedTuple):
    """
    The one document a block comment holds, and where it sits.

    first and last delimit the document's lines in the source, half
    open and zero based, excluding the marker lines. indent is the
    column the markers sit at. The shape is the python loader's, so
    that a caller splicing a document back into a file does not have to
    know which language it came from.

    """

    first:  int
    last:   int
    indent: int
    text:   str


# -----------------------------------------------------------------------------
def metadata_at(text):
    """
    Return the Metadata of the document the first block comment holds,
    or None where it holds none.

    """

    list_line = text.splitlines()
    opened    = None

    for (number, line) in enumerate(list_line):

        stripped = line.strip()

        if opened is None and stripped.startswith(MARKER_OPEN) \
                          and _within_comment(list_line, number):
            opened = number
        elif opened is not None and stripped == MARKER_CLOSE:
            body = '\n'.join(line[_indent(list_line[opened]):]
                              for line in list_line[opened : number])
            return Metadata(first  = opened + 1,
                            last   = number,
                            indent = _indent(list_line[opened]),
                            text   = body)

    return None


# -----------------------------------------------------------------------------
def _within_comment(list_line, number):
    """
    Return whether the line numbered belongs to a block comment that
    opens the file, nothing but space preceding it.

    """

    head = '\n'.join(list_line[:number]).strip()

    return head.startswith(OPEN) and CLOSE not in head


# -----------------------------------------------------------------------------
def _indent(line):
    return len(line) - len(line.lstrip())


# -----------------------------------------------------------------------------
def iter_document(data, encoding = None):
    """
    Yield the one document a block comment at the head of the file
    holds, or nothing where it holds none.

    A file of a language whose comments open with an oblique and a star
    may carry a data item in the first comment of the file, opened by
    three hyphens and closed by three full stops, as a python file
    carries one in its module docstring. A file whose first comment
    holds no such document, or which opens with no comment at all, is
    passed over rather than refused, because a stylesheet or a script
    may have been written elsewhere and vendored here, and a vendored
    file is not ours to name.

    """

    found = metadata_at(data.decode(encoding or ENCODING_DEFAULT))

    if found is None:
        return

    document = ruamel.yaml.YAML(typ = 'rt').load(found.text)

    if document is not None:
        yield document

