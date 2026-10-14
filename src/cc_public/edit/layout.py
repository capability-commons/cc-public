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
                        Write the fields of a data item as YAML lines
                        in the layout of the repository.
description:            |
                        Each value starts at column 25, whatever the
                        indentation of its key. Prose fields are
                        literal blocks, wrapped at 46 columns so that
                        they end by column 70. An empty list is
                        written [], and a list of mappings has a
                        blank line before it and after each mapping.
relation:               []

...
"""


import io
import textwrap
import typing

import ruamel.yaml


COLUMN_VALUE      = 24
WIDTH_PROSE       = 46
INDENT_STEP       = 2
SET_KEY_PROSE     = {'brief', 'description', 'usage', 'note'}
MARK_BLOCK        = '|'
MARK_ITEM         = '- '
DELIM_PARAGRAPH   = '\n\n'

# Scalars are written one at a time, each on a line of its own.
#
YAML                    = ruamel.yaml.YAML(typ = 'safe')
YAML.width              = 4096
YAML.default_flow_style = False


# -----------------------------------------------------------------------------
def lines_of_fields(map_field: dict[str, typing.Any], indent: int) -> list[str]:
    """
    Return the lines that write each field of map_field as a key at
    indent. A non-empty list has a blank line after it, and a list of
    mappings has one before it too, except at the start.

    """

    list_line = []

    for (key, value) in map_field.items():
        if _is_mappings(value) and list_line and list_line[-1]:
            list_line.append('')
        list_line.extend(lines_of_field(key, value, indent))
        if isinstance(value, list) and value:
            list_line.append('')

    while list_line and not list_line[-1]:
        list_line.pop()

    return list_line


# -----------------------------------------------------------------------------
def lines_of_field(key: str, value: typing.Any, indent: int) -> list[str]:
    """
    Return the lines that write one field as a key at indent, with no
    blank line at either end.

    """

    head = ' ' * indent + key + ':'

    if isinstance(value, list) and not value:
        return [_pad(head) + '[]']

    if _is_mappings(value):
        list_line = [head, '']
        for mapping in value:
            list_line.extend(lines_of_mapping(mapping, indent + INDENT_STEP))
            list_line.append('')
        return list_line[:-1]

    if isinstance(value, list):
        return [head] + [' ' * (indent + INDENT_STEP) + MARK_ITEM + scalar(item)
                         for item in value]

    if key in SET_KEY_PROSE:
        return [_pad(head) + MARK_BLOCK] + [' ' * COLUMN_VALUE + line if line else ''
                                            for line in wrap(value)]

    return [_pad(head) + scalar(value)]


# -----------------------------------------------------------------------------
def lines_of_mapping(mapping: dict[str, typing.Any], indent: int) -> list[str]:
    """
    Return the lines that write mapping as an item of a list at indent:
    its first key follows the item mark, and the others line up under
    it.

    """

    list_line = lines_of_fields(mapping, indent + len(MARK_ITEM))
    if list_line:
        list_line[0] = ' ' * indent + MARK_ITEM + list_line[0][indent + len(MARK_ITEM):]
    return list_line


# -----------------------------------------------------------------------------
def wrap(text: str) -> list[str]:
    """
    Return the lines of text wrapped at the width of prose, with its
    paragraphs kept apart by a blank line.

    """

    list_line = []

    for paragraph in text.strip().split(DELIM_PARAGRAPH):
        if list_line:
            list_line.append('')
        list_line.extend(textwrap.wrap(' '.join(paragraph.split()),
                                       width            = WIDTH_PROSE,
                                       break_long_words = False,
                                       break_on_hyphens = False))

    return list_line


# -----------------------------------------------------------------------------
def scalar(value: typing.Any) -> str:
    """
    Return value as a YAML scalar on one line: plain where YAML reads
    it back unchanged, and quoted otherwise.

    """

    stream = io.StringIO()
    YAML.dump({'k': value}, stream)
    text   = stream.getvalue().strip()[len('k: '):]

    if '\n' in text:
        raise ValueError('A value on one line cannot be written: {value!r}'.format(
                                                                        value = value))

    return text


# -----------------------------------------------------------------------------
def _pad(head: str) -> str:
    """
    Return head padded so that the value after it starts at the column
    of values, with at least one space between.

    """

    return head.ljust(COLUMN_VALUE - 1) + ' '


# -----------------------------------------------------------------------------
def _is_mappings(value: typing.Any) -> bool:
    """
    Return whether value is a non-empty list of mappings.

    """

    return (isinstance(value, list)
            and bool(value)
            and all(isinstance(item, dict) for item in value))
