"""
---

id_self:                pym_cc_public.layout
guid_self:              pym_10b0403d86c748219ef9db9500ea2a2b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Layout convention
brief:                  |
                        The layout every YAML document in the
                        repository is written to, as a printer.
description:            |
                        Parses a document and prints it again to the
                        convention: structure indented two per level,
                        values at the common column, lists in block
                        form, prose in block scalars filled to width.
                        Comments are read from the source and put back
                        before the key they preceded. Blank lines are
                        placed by rule.
usage:                  |
                        format lays out a YAML document.
                        format_metadata lays out the document held in
                        a python docstring and leaves the code alone.
                        The layout check is the comparison of a file
                        with its own formatting.
note:                   |
                        Formatting is idempotent, and a formatted
                        document parses to the same data as the
                        original, prose differing only in where its
                        lines break.
relation:               []

...
"""


import io
import re
import textwrap

import ruamel.yaml
import ruamel.yaml.comments
import ruamel.yaml.scalarstring

import cc_public.load.python


COLUMN_VALUE  = 24
GAP_MIN       = 2
INDENT_STEP   = 2
WIDTH_WRAP    = 70
WIDTH_MAX     = 80

SUFFIX_YAML   = '.yaml'
SUFFIX_PYTHON = '.py'

REGEX_COMMENT = re.compile(r'^\s*#')

_YAML         = ruamel.yaml.YAML(typ = 'rt')
_YAML.width = 10 ** 9              # a scalar is never folded across lines
_YAML.preserve_quotes = True

Map = ruamel.yaml.comments.CommentedMap
Seq = ruamel.yaml.comments.CommentedSeq


# -----------------------------------------------------------------------------
class Unsupported(Exception):
    """
    Raised for a document outside the subset this printer lays out.

    Anchors, tags, nested sequences and non mapping documents are not
    handled. Refusing is better than guessing at a layout for them.

    """



# -----------------------------------------------------------------------------
def format(text):
    """
    Return text laid out to the convention.

    """

    document = _YAML.load(text)

    if not isinstance(document, Map):
        raise Unsupported('The document is not a mapping.')

    lead = _lead(text.splitlines())
    out  = []

    _emit_map(document, 0, lead, out, is_item = False)

    return '\n'.join(out).rstrip('\n') + '\n'


# -----------------------------------------------------------------------------
def _lead(list_line):
    """
    Return {line: comment lines} for every line a comment block precedes
    in the source.

    Only the entries at lines where a key or item begins are used. A run
    inside a block scalar lands on a prose line and is ignored. Blank
    lines are not read from the source at all: where they go is a rule.

    """

    lead     = {}
    comments = []

    for (index, line) in enumerate(list_line):

        if not line.strip():
            continue
        if REGEX_COMMENT.match(line):
            comments.append(line.strip())
        else:
            if comments:
                lead[index] = comments
            comments = []

    return lead


# -----------------------------------------------------------------------------
def _is_multi(value):
    """
    Return whether a value is emitted on the lines beneath its key.

    A non empty mapping or sequence is. A block scalar is not: it is
    prose, and packs with the scalar keys around it.

    """

    return isinstance(value, (Map, Seq)) and len(value) > 0


# -----------------------------------------------------------------------------
def _emit_lead(line, indent, lead, out, is_multi, was_multi):
    """
    Emit what precedes a key or item: a blank line where the rule wants
    one, and the comment block that preceded it in the source.

    The rule: one blank line separates anything emitted on several lines
    from what is beside it, and precedes any comment block. Scalars pack.
    Nothing precedes the first line of the document.

    """

    comments = lead.get(line, [])

    if out and (is_multi or was_multi or comments):
        out.append('')

    out.extend(' ' * indent + comment for comment in comments)


# -----------------------------------------------------------------------------
def _emit_map(mapping, indent, lead, out, is_item):
    """
    Emit a mapping with its keys at indent.

    Where the mapping is an item of a sequence, its first key shares
    the line with the dash, two columns to the left.

    """

    was_multi = False

    for (index, (key, value)) in enumerate(mapping.items()):

        line   = mapping.lc.key(key)[0]
        prefix = ' ' * indent

        if index == 0 and is_item:
            # The item's own lead was emitted by the sequence.
            prefix = ' ' * (indent - INDENT_STEP) + '- '
        else:
            _emit_lead(line, indent, lead, out, _is_multi(value), was_multi)

        head   = prefix + str(key) + ':'
        column = max(COLUMN_VALUE, len(head) + GAP_MIN)

        _emit_value(value, head, column, indent, lead, out)
        was_multi = _is_multi(value)


# -----------------------------------------------------------------------------
def _emit_value(value, head, column, indent, lead, out):
    """
    Emit one value after its key, on the same line or beneath it.

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
    # prose is refilled. A plain scalar is a datum -- a URI, a regex
    # with spaces in it -- and stays on its line however long it runs,
    # since breaking it would change it.
    #
    if isinstance(value, ruamel.yaml.scalarstring.LiteralScalarString):
        out.append(head.ljust(column) + ('|' if value.endswith('\n') else '|-'))
        out.extend(_body(value, max(COLUMN_VALUE, indent + INDENT_STEP)))
        return

    if isinstance(value, ruamel.yaml.scalarstring.FoldedScalarString):
        raise Unsupported('A folded scalar. Write prose with | instead.')

    out.append(head.ljust(column) + _render(value))


# -----------------------------------------------------------------------------
def _emit_seq(sequence, indent, lead, out):
    """
    Emit a sequence in block form, its dashes at indent.

    """

    was_multi = False

    for (index, value) in enumerate(sequence):

        line = sequence.lc.item(index)[0]

        if isinstance(value, Seq):
            raise Unsupported('A sequence directly inside a sequence.')

        # An item that is a mapping of more than one key, or holding
        # anything multi line, takes several lines and is set apart.
        #
        is_multi = isinstance(value, Map) and (len(value) > 1
                                               or any(_is_multi(v)
                                                      for v in value.values()))
        _emit_lead(line, indent, lead, out, is_multi, was_multi)

        if isinstance(value, Map):
            _emit_map(value, indent + INDENT_STEP, lead, out, is_item = True)
        else:
            out.append(' ' * indent + '- ' + _render(value))

        was_multi = is_multi


# -----------------------------------------------------------------------------
def _render(value):
    """
    Return one scalar as YAML would write it, quoted where it must be.

    Delegated to the library, so that the rules for when a plain
    scalar would be read as something else are never restated here.

    """

    stream = io.StringIO()
    _YAML.dump(value, stream)
    lines = stream.getvalue().splitlines()

    if lines and lines[-1] == '...':            # the document end marker
        lines.pop()

    # A scalar that comes back on more than one line would lose its
    # tail here, so it is refused rather than truncated. The width set
    # above means the library never folds; a genuine line break is
    # prose and belongs in a block scalar.
    #
    if len(lines) != 1:
        raise Unsupported('A scalar that cannot be written on one line: '
                          '{head}'.format(head = lines[0][:60]))

    return lines[0]


# -----------------------------------------------------------------------------
def _body(value, column):
    """
    Return the lines of a block scalar body, indented to column and
    filled to width.

    A line indented further than the rest of its paragraph was laid
    out on purpose and is moved with the body but not refilled.

    """

    list_out  = []
    list_para = []
    pad       = ' ' * column

    def flush():
        if not list_para:
            return
        text = ' '.join(' '.join(line.split()) for line in list_para)
        list_out.extend(textwrap.wrap(text, WIDTH_WRAP,
                                      initial_indent    = pad,
                                      subsequent_indent = pad,
                                      break_long_words  = False,
                                      break_on_hyphens  = False))
        list_para.clear()

    for line in value.rstrip('\n').split('\n'):

        if not line.strip():
            flush()
            list_out.append('')
        elif line != line.lstrip():
            flush()
            list_out.append(pad + line.rstrip())
        else:
            list_para.append(line)

    flush()

    return list_out


# -----------------------------------------------------------------------------
def format_metadata(text):
    """
    Return a python source file with every docstring document laid out.

    The documents are found by walking the syntax tree, so one in the
    docstring of a class or a function is laid out as the module's is,
    at its own indent. The code is not touched. Later documents are
    replaced first, so that earlier line numbers stay true.

    """

    list_line = text.splitlines()
    list_doc  = sorted(cc_public.load.python.iter_metadata(text),
                       key = lambda m: -m.first)

    for m in list_doc:

        pad  = ' ' * m.indent
        body = [pad + line if line else '' for line in format(m.text).splitlines()]

        # The document sits inside its markers with a blank line on
        # either side, so that the markers read as a frame.
        #
        list_line[m.first : m.last] = [''] + body + ['']

    return '\n'.join(list_line) + ('\n' if text.endswith('\n') else '')


# -----------------------------------------------------------------------------
def format_source(text, suffix):
    """
    Return text laid out, according to what kind of file it came from.

    """

    if suffix == SUFFIX_PYTHON:
        return format_metadata(text)

    if suffix == SUFFIX_YAML:
        return format(text)

    return text
