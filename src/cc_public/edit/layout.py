"""
---

id_self:                pym_cc_public.edit.layout
guid_self:              pym_8b6ad4857bcd47d89fe4caf91581254b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Data item layout
brief:                  |
                        The layout every data item in the repository
                        is written to, as a printer.
description:            |
                        format reads a YAML document and prints it
                        again to the layout: structure indented two
                        per level, values at column 25, lists in block
                        form, and prose in literal blocks filled to
                        column 70. Comments are read from the source
                        and put back before the key they preceded.
                        Blank lines are placed by rule: one sets apart
                        anything written on several lines, and
                        precedes any comment, and scalars pack.

                        format_file lays out the documents a file
                        holds: a YAML file under _data, the docstrings
                        of a python module and of its classes and
                        functions, or the comment header of any other
                        file. The rest of the file is left alone. The
                        document of a class or function keeps the
                        indentation of its docstring.
usage:                  |
                        The layout check, cctool format and every edit
                        use format_file, so that a file is laid out
                        the same way whoever writes it.
note:                   |
                        Formatting is idempotent, and a formatted
                        document reads as the same data as the
                        original, prose differing only in where its
                        lines break. Ported from the printer of the
                        legacy repository, cc-public-legacy-20260918.
relation:               []

...
"""


import ast
import hashlib
import io
import pathlib
import re
import typing

import ruamel.yaml
import ruamel.yaml.comments
import ruamel.yaml.scalarstring
import ruamel.yaml.tokens

import cc_public.graph.extract


COLUMN_VALUE      = 24
GAP_MIN           = 2
INDENT_STEP       = 2
WIDTH_WRAP        = 70
MARK_ITEM         = '- '
REGEX_COMMENT     = re.compile(r'^\s*#')

# A line of prose that opens with a list marker, such as "- " or "2. ",
# begins an item of a list, which is a paragraph of its own.
#
REGEX_LIST_ITEM   = re.compile(r'^(?:[-*+]|[0-9]{1,2}[.)]) ')
INDENT_LIST_ITEM  = '  '

# The lines that open and close a document, and the blank lines that
# frame it inside them.
#
LINE_OPEN         = cc_public.graph.extract.LINE_OPEN
LINE_CLOSE        = cc_public.graph.extract.LINE_CLOSE

# Fields written as prose, in literal blocks, when an edit writes them.
#
SET_KEY_PROSE     = {'brief', 'description', 'usage', 'note'}

# The columns of a row of the layout check, and what it says of a file
# that format_file would change.
#
COLUMNS           = ('file', 'line', 'message')
MESSAGE_LAYOUT    = 'Not laid out as cctool format lays it out.'

# What the layout check found for a file, by its path and the digest of
# its text, so that a file unchanged since the last check is not laid
# out again. Cleared when it holds COUNT_VIOLATION entries.
#
MAP_VIOLATION     = {}
COUNT_VIOLATION   = 4096

YAML              = ruamel.yaml.YAML(typ = 'rt')
YAML.width        = 10 ** 9        # a scalar is never folded across lines
YAML.preserve_quotes = True

Map               = ruamel.yaml.comments.CommentedMap
Seq               = ruamel.yaml.comments.CommentedSeq


# -----------------------------------------------------------------------------
class Unsupported(Exception):
    """
    The document is outside the subset this printer lays out: anchors,
    aliases, tags, comments at the end of a line, nested sequences,
    folded scalars and documents that are not mappings. Refusing is
    better than guessing at a layout for them, or dropping them.

    """


# -----------------------------------------------------------------------------
def violations(root: pathlib.Path, map_document: cc_public.graph.extract.Documents) -> list:
    """
    Return a row for each file under root that holds a document and is
    not laid out: its path, the first line that format_file would
    change, and why.

    """

    list_row = []

    for relative in cc_public.graph.extract.files(map_document):
        text = (root / relative).read_text(encoding = 'utf-8')
        key  = (relative, hashlib.blake2b(text.encode('utf-8'), digest_size = 16).digest())
        if key not in MAP_VIOLATION:
            if len(MAP_VIOLATION) >= COUNT_VIOLATION:
                MAP_VIOLATION.clear()
            MAP_VIOLATION[key] = _violation(relative, text)
        if MAP_VIOLATION[key] is not None:
            list_row.append(MAP_VIOLATION[key])

    return list_row


# -----------------------------------------------------------------------------
def _violation(relative: str, text: str) -> tuple | None:
    """
    Return the row of the layout check for the file at relative, which
    holds text, or None if it is laid out.

    """

    try:
        laid_out = format_file(text, pathlib.Path(relative))
    except Unsupported as error:
        return (relative, '1', str(error))
    if laid_out != text:
        return (relative, str(_first_difference(text, laid_out)), MESSAGE_LAYOUT)

    return None


# -----------------------------------------------------------------------------
def _first_difference(text: str, other: str) -> int:
    """
    Return the first line, counted from 1, at which text and other
    differ.

    """

    for (index, (line, line_other)) in enumerate(zip(text.split('\n'), other.split('\n'),
                                                     strict = False)):
        if line != line_other:
            return index + 1

    return min(len(text.split('\n')), len(other.split('\n'))) + 1


# -----------------------------------------------------------------------------
def format_file(text: str, relative: pathlib.Path) -> str:
    """
    Return text, the content of the file at relative, with the
    documents it holds laid out and the rest of it unchanged.

    """

    if relative.suffix == cc_public.graph.extract.SUFFIX_YAML:
        if cc_public.graph.extract.DIR_DATA not in relative.parts:
            return text
        return format(text)

    list_line = text.split('\n')

    # The documents are laid out from the last up, so that a document
    # laid out on more or fewer lines leaves the spans above it where
    # they were.
    #
    for (first, last, mark, indent) in reversed(_spans(text, relative)):
        list_doc  = [_unmark(line, mark).removeprefix(indent)
                     for line in list_line[first:last + 1]]
        list_body = format('\n'.join(list_doc)).rstrip('\n').split('\n')
        list_new  = [LINE_OPEN, ''] + list_body + ['', LINE_CLOSE]
        list_line[first:last + 1] = [_mark(indent + line if line else '', mark)
                                     for line in list_new]

    return '\n'.join(list_line)


# -----------------------------------------------------------------------------
def spans(text: str, relative: pathlib.Path) -> list[tuple[int, int]]:
    """
    Return the indices of the first and the last line of each document
    in text, the content of the file at relative, in order.

    """

    list_line = text.split('\n')

    if relative.suffix == cc_public.graph.extract.SUFFIX_YAML:
        if cc_public.graph.extract.DIR_DATA not in relative.parts:
            return []
        return [(0, len(list_line) - 1)]

    return [(first, last) for (first, last, _, _) in _spans(text, relative)]


# -----------------------------------------------------------------------------
def _spans(text: str, relative: pathlib.Path) -> list[tuple[int, int, str, str]]:
    """
    Return the indices of the lines that open and close each document
    in text, the content of the file at relative, other than a YAML
    file, with what begins each of its lines: the comment marker of a
    header, and the indentation of the docstring of a class or function.

    """

    list_line = text.split('\n')

    if relative.suffix != cc_public.graph.extract.SUFFIX_PYTHON:
        mark          = cc_public.graph.extract.mark_comment(relative)
        (first, last) = _span_header(list_line, mark)
        return [] if first is None else [(first, last, mark, '')]

    try:
        module = ast.parse(text)
    except SyntaxError:
        return []

    list_span = []

    for node in _documented(module):
        (first, last) = _span(list_line, node.body[0].lineno - 1, node.body[0].end_lineno, '')
        if first is None:
            continue
        line = list_line[first]
        list_span.append((first, last, '', line[:len(line) - len(line.lstrip())]))

    return list_span


# -----------------------------------------------------------------------------
def _documented(module: ast.Module) -> list[ast.AST]:
    """
    Return the module and each class or function in it whose docstring
    holds a document, in the order they are written: those that
    cc_public.graph.extract reads documents from.

    """

    list_node = []

    def visit(node):
        docstring = ast.get_docstring(node)
        if docstring and docstring.startswith(LINE_OPEN):
            list_node.append(node)
        if not isinstance(node, (ast.Module, ast.ClassDef)):
            return
        for child in node.body:
            if type(child) in cc_public.graph.extract.MAP_PREFIX_KIND:
                visit(child)

    visit(module)

    return list_node


# -----------------------------------------------------------------------------
def format(text: str) -> str:
    """
    Return the YAML document text laid out.

    """

    try:
        document = YAML.load(text)
    except ruamel.yaml.YAMLError as error:
        raise Unsupported('The document is not YAML: {error}'.format(
                                    error = ' '.join(str(error).split()))) from error

    if not isinstance(document, Map):
        raise Unsupported('The document is not a mapping.')

    _refuse(document, text.splitlines(), set())

    lead = _lead(text.splitlines())
    out  = []

    _emit_map(document, 0, lead, out, is_item = False)

    return '\n'.join(out).rstrip('\n') + '\n'


# -----------------------------------------------------------------------------
def _refuse(node: typing.Any, list_line: list[str], set_seen: set[int]) -> None:
    """
    Raise Unsupported if node, or anything in it, has an anchor, is an
    alias, has a tag, or has a comment at the end of a line, which the
    printer would expand, keep wrongly or drop. list_line holds the
    lines of the text node was read from.

    """

    anchor = getattr(node, 'anchor', None)
    if anchor is not None and anchor.value:
        raise Unsupported('The document has an anchor, &{name}.'.format(name = anchor.value))
    if isinstance(node, ruamel.yaml.comments.TaggedScalar):
        raise Unsupported('The document has a tag, {tag}.'.format(tag = node.tag.value))
    if not isinstance(node, (Map, Seq)):
        return

    if id(node) in set_seen:
        raise Unsupported('The document has an alias.')
    set_seen.add(id(node))
    if node.tag.value is not None:
        raise Unsupported('The document has a tag, {tag}.'.format(tag = node.tag.value))

    for list_token in node.ca.items.values():
        for token in list_token:
            # A comment token also carries the blank lines and the whole
            # line comments after a value, which the printer keeps. Only
            # one that opens with # on the line of a value is dropped.
            #
            if (isinstance(token, ruamel.yaml.tokens.CommentToken)
                    and token.value.lstrip(' ').startswith('#')):
                (line, column) = (token.start_mark.line, token.start_mark.column)
                if list_line[line][:column].strip():
                    raise Unsupported('The document has a comment at the end of line '
                                      '{line}.'.format(line = line + 1))

    for child in (node.values() if isinstance(node, Map) else node):
        _refuse(child, list_line, set_seen)


# -----------------------------------------------------------------------------
def dump(value: dict | list, indent: int) -> list[str]:
    """
    Return the lines of YAML that write value at indent: a mapping,
    with each prose field as a literal block, or a list. The lines are
    correct YAML, not laid out, and format lays them out.

    """

    if isinstance(value, dict):
        value = {key: _prose(key, each) for (key, each) in value.items()}

    stream = io.StringIO()
    YAML.dump(value, stream)

    return [' ' * indent + line if line else ''
            for line in stream.getvalue().rstrip('\n').split('\n')]


# -----------------------------------------------------------------------------
def _prose(key: str, value: typing.Any) -> typing.Any:
    """
    Return value as a literal block if key names a prose field.

    """

    if key in SET_KEY_PROSE and isinstance(value, str):
        return ruamel.yaml.scalarstring.LiteralScalarString(value.rstrip('\n') + '\n')
    return value


# -----------------------------------------------------------------------------
def _span_header(list_line: list[str], mark: str) -> tuple[int | None, int | None]:
    """
    Return the indices of the lines that open and close the document in
    the comment header the lines open with, or None if there is none. A
    line that names an interpreter may come before the header.

    """

    start = int(bool(list_line) and list_line[0].startswith(
                                            cc_public.graph.extract.MARK_SHEBANG))
    end   = start
    while end < len(list_line) and list_line[end].startswith(mark):
        end += 1

    if end == start or _unmark(list_line[start], mark) != LINE_OPEN:
        return (None, None)

    return _span(list_line, start, end, mark)


# -----------------------------------------------------------------------------
def _span(list_line: list[str], start: int, end: int, mark: str) -> tuple[int | None, int | None]:
    """
    Return the indices of the first line from start that opens a
    document, and of the first after it that closes one, both before
    end, or None if there are not both.

    """

    first = None

    for index in range(start, end):
        text = _unmark(list_line[index], mark).strip()
        if first is None and text == LINE_OPEN:
            first = index
        elif first is not None and text == LINE_CLOSE:
            return (first, index)

    return (None, None)


# -----------------------------------------------------------------------------
def _unmark(line: str, mark: str) -> str:
    """
    Return line without the comment marker that begins it.

    """

    if mark and line.startswith(mark):
        return line[len(mark):].removeprefix(' ')
    return line


# -----------------------------------------------------------------------------
def _mark(line: str, mark: str) -> str:
    """
    Return line with the comment marker put on it.

    """

    if not mark:
        return line
    return mark + (' ' + line if line else '')


# -----------------------------------------------------------------------------
def _lead(list_line: list[str]) -> dict[int, list[str]]:
    """
    Return the comment lines that precede each line in the source,
    keyed by the line they precede.

    Only those at lines where a key or item begins are used. A run
    inside a block scalar lands on a prose line and is ignored. Blank
    lines are not read from the source at all: where they go is a rule.

    """

    lead          = {}
    list_comment  = []

    for (index, line) in enumerate(list_line):
        if not line.strip():
            continue
        if REGEX_COMMENT.match(line):
            list_comment.append(line.strip())
        else:
            if list_comment:
                lead[index] = list_comment
            list_comment = []

    return lead


# -----------------------------------------------------------------------------
def _is_multi(value: typing.Any) -> bool:
    """
    Return whether value is written on the lines beneath its key. A
    non-empty mapping or sequence is. A block scalar is not: it is
    prose, and packs with the scalar keys around it.

    """

    return isinstance(value, (Map, Seq)) and len(value) > 0


# -----------------------------------------------------------------------------
def _emit_lead(line:      int,
               indent:    int,
               lead:      dict[int, list[str]],
               out:       list[str],
               is_multi:  bool,
               was_multi: bool) -> None:
    """
    Write what precedes a key or item: a blank line where the rule
    wants one, and the comments that preceded it in the source.

    The rule: one blank line sets apart anything written on several
    lines from what is beside it, and precedes any comment. Scalars
    pack. Nothing precedes the first line of the document.

    """

    list_comment = lead.get(line, [])

    if out and (is_multi or was_multi or list_comment):
        out.append('')

    out.extend(' ' * indent + comment for comment in list_comment)


# -----------------------------------------------------------------------------
def _emit_map(mapping: Map, indent: int, lead: dict, out: list[str], is_item: bool) -> None:
    """
    Write a mapping with its keys at indent. Where the mapping is an
    item of a sequence, its first key shares the line with the item
    mark, two columns to the left.

    """

    was_multi = False

    for (index, (key, value)) in enumerate(mapping.items()):

        line   = mapping.lc.key(key)[0]
        prefix = ' ' * indent

        if index == 0 and is_item:
            # The lead of the item was written by the sequence.
            prefix = ' ' * (indent - INDENT_STEP) + MARK_ITEM
        else:
            _emit_lead(line, indent, lead, out, _is_multi(value), was_multi)

        head   = prefix + str(key) + ':'
        column = max(COLUMN_VALUE, len(head) + GAP_MIN)

        _emit_value(value, head, column, indent, lead, out)
        was_multi = _is_multi(value)


# -----------------------------------------------------------------------------
def _emit_value(value:  typing.Any,
                head:   str,
                column: int,
                indent: int,
                lead:   dict,
                out:    list[str]) -> None:
    """
    Write one value after its key, on the same line or beneath it.

    """

    if isinstance(value, Map):
        if not value:
            out.append(head.ljust(column) + '{}')
        else:
            out.append(head)
            _emit_map(value, indent + INDENT_STEP, lead, out, is_item = False)
        return

    if isinstance(value, Seq):
        if not value:
            out.append(head.ljust(column) + '[]')
        else:
            out.append(head)
            _emit_seq(value, indent + INDENT_STEP, lead, out)
        return

    # Only what the author wrote as a block scalar is prose, and only
    # prose is refilled. A plain scalar is a datum, such as a URI or a
    # regex with spaces in it, and stays on its line however long it
    # runs, since breaking it would change it.
    #
    if isinstance(value, ruamel.yaml.scalarstring.LiteralScalarString):
        out.append(head.ljust(column) + ('|' if value.endswith('\n') else '|-'))
        out.extend(_body(value, max(COLUMN_VALUE, indent + INDENT_STEP)))
        return

    if isinstance(value, ruamel.yaml.scalarstring.FoldedScalarString):
        raise Unsupported('A folded scalar. Write prose with | instead.')

    out.append(head.ljust(column) + _render(value))


# -----------------------------------------------------------------------------
def _emit_seq(sequence: Seq, indent: int, lead: dict, out: list[str]) -> None:
    """
    Write a sequence in block form, its item marks at indent.

    """

    was_multi = False

    for (index, value) in enumerate(sequence):

        line = sequence.lc.item(index)[0]

        if isinstance(value, Seq):
            raise Unsupported('A sequence directly inside a sequence.')

        # An item that is a mapping of more than one key, or that holds
        # anything on several lines, takes several lines and is set
        # apart.
        #
        is_multi = isinstance(value, Map) and (len(value) > 1
                                               or any(_is_multi(each)
                                                      for each in value.values()))
        _emit_lead(line, indent, lead, out, is_multi, was_multi)

        # An empty mapping has no key to put on the line of the item
        # mark, so it is written as a scalar would be.
        #
        if isinstance(value, Map) and value:
            _emit_map(value, indent + INDENT_STEP, lead, out, is_item = True)
        else:
            out.append(' ' * indent + MARK_ITEM + _render(value))

        was_multi = is_multi


# -----------------------------------------------------------------------------
def _render(value: typing.Any) -> str:
    """
    Return one scalar as YAML would write it, quoted where it must be.
    The library decides, so that the rules for when a plain scalar
    would be read as something else are never restated here.

    """

    stream = io.StringIO()
    YAML.dump(value, stream)
    list_line = stream.getvalue().splitlines()

    if list_line and list_line[-1] == LINE_CLOSE:
        list_line.pop()

    # A scalar that comes back on more than one line would lose its
    # tail here, so it is refused rather than cut. The width set above
    # means the library never folds; a line break is prose, and
    # belongs in a block scalar.
    #
    if len(list_line) != 1:
        raise Unsupported('A scalar that cannot be written on one line: {head}'.format(
                                                                head = list_line[0][:60]))

    return list_line[0]


# -----------------------------------------------------------------------------
def _fill(list_word: list[str], initial: str, subsequent: str) -> list[str]:
    """
    Return the words filled into lines of at most WIDTH_WRAP, the first
    indented by initial and the rest by subsequent, as many on each as
    fit. No line but the first opens with a word that would read as a
    list marker, such as - or 2., since laying the lines out again
    would make it an item of a list: the word before it goes down with
    it, or, if there is none, it stays on the line before.

    """

    list_line = []
    list_now  = []

    for word in list_word:
        pad = subsequent if list_line else initial
        if not list_now or len(pad + ' '.join([*list_now, word])) <= WIDTH_WRAP:
            list_now.append(word)
            continue
        if not REGEX_LIST_ITEM.match(word + ' '):
            list_line.append(pad + ' '.join(list_now))
            list_now = [word]
        elif len(list_now) > 1:
            carry = list_now.pop()
            list_line.append(pad + ' '.join(list_now))
            list_now = [carry, word]
        else:
            list_now.append(word)

    if list_now:
        list_line.append((subsequent if list_line else initial) + ' '.join(list_now))

    return list_line


# -----------------------------------------------------------------------------
def _body(value: str, column: int) -> list[str]:
    """
    Return the lines of the body of a block scalar, indented to column
    and filled to width. A line indented further than the rest of its
    paragraph was laid out on purpose, and is moved with the body but
    not refilled. An item of a list is filled on its own, and the lines
    it goes on to are indented under its text, so they are kept as
    they are when it is laid out again.

    """

    list_out  = []
    list_para = []
    pad       = ' ' * column

    def flush():
        if not list_para:
            return
        more = INDENT_LIST_ITEM if REGEX_LIST_ITEM.match(list_para[0]) else ''
        list_out.extend(_fill(' '.join(list_para).split(), pad, pad + more))
        list_para.clear()

    for line in value.rstrip('\n').split('\n'):
        if not line.strip():
            flush()
            list_out.append('')
        elif line != line.lstrip():
            flush()
            list_out.append(pad + line.rstrip())
        else:
            if REGEX_LIST_ITEM.match(line):
                flush()
            list_para.append(line)

    flush()

    return list_out
