"""
---

id_self:                pym_cc_public.web.description
guid_self:              pym_57836da700d44f0c923eb652e5f4fb28
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Description of an annotation
brief:                  |
                        Lay out the description of an annotation as
                        prose with its sources in the margin.
description:            |
                        The description of an annotation is one run of
                        prose that cites its sources in brackets: a
                        file and its lines, a commit, a date, a web
                        address, or a statement by the owner. Each
                        such bracket is taken out of the prose and set
                        as a numbered note in the margin, so the prose
                        reads as an argument and the sources stay
                        beside it. An assumption, marked ASSUMPTION,
                        is set apart from what was checked, and each
                        id the prose names links to its item, shown by
                        its title.
relation:               []

...
"""


import re

import htpy

import cc_public.web.argument


# A bracket that cites a source: a file or its lines, a commit, a date,
# a web address, or a statement. Any other bracket stays in the prose.
#
REGEX_BRACKET     = re.compile(r' ?\(([^()]*)\)')
REGEX_SOURCE      = re.compile(r'\.(?:py|lp|yaml|json|md|toml|txt|css|html)\b|\blines? [0-9]'
                               r'|\b[0-9a-f]{7,40}\b|\b20[0-9]{2}-[0-9]{2}-[0-9]{2}'
                               r'|https?://|\bstatement\b|\bclause [0-9]|\bpage [0-9]')
REGEX_URL         = re.compile(r'https?://[^\s,;]+[^\s,;.)]')
REGEX_ASSUMPTION  = re.compile(r'\(?ASSUMPTIONS?: ?')
MARK_ASSUMPTION   = 'assumption'
REGEX_END         = re.compile(r'\)|\.(?=\s+[A-Z(]|$)')

Graph             = cc_public.web.argument.Graph


# -----------------------------------------------------------------------------
def description(graph: Graph, text: str, prefix: str) -> tuple[list, list]:
    """
    Return the description text as prose and its sources as margin notes.
    The prose cites each note by its number; prefix makes the ids of
    the notes unique on the page.

    """

    list_prose = []
    list_note  = []
    position   = 0
    text       = ' '.join(text.split())

    for match in REGEX_BRACKET.finditer(text):
        inside = match.group(1)
        if not REGEX_SOURCE.search(inside) or REGEX_ASSUMPTION.match(inside):
            continue
        list_prose.extend(_runs(graph, text[position:match.start()]))
        number = len(list_note) + 1
        key    = '{prefix}-note-{number}'.format(prefix = prefix, number = number)
        list_prose.append(htpy.sup(class_ = 'cite')[
                              htpy.a(href = '#' + key)[str(number)]])
        list_note.append(htpy.li(id = key, value = str(number))[_source(graph, inside)])
        position = match.end()

    list_prose.extend(_runs(graph, text[position:]))

    return (list_prose, list_note)


# -----------------------------------------------------------------------------
def _runs(graph: Graph, text: str) -> list:
    """
    Return text as runs of prose: each assumption set apart, from its
    mark to the end of its sentence or bracket, and each id it names
    linked to its item.

    """

    list_run = []
    position = 0

    for match in REGEX_ASSUMPTION.finditer(text):
        if match.start() < position:
            continue
        end      = REGEX_END.search(text, match.end())
        stop     = end.start() if end else len(text)
        list_run.extend(_linked(graph, text[position:match.start()]))
        list_run.append(htpy.span(class_ = 'assumption')[
                            htpy.span(class_ = 'label')[MARK_ASSUMPTION], ' ',
                            _linked(graph, text[match.end():stop])])
        position = stop + (1 if end and end.group(0) == ')' and match.group(0)[0] == '(' else 0)

    list_run.extend(_linked(graph, text[position:]))

    return list_run


# -----------------------------------------------------------------------------
def _linked(graph: Graph, text: str) -> list:
    """
    Return text with each id in the tree it names linked to its item
    and shown by its title.

    """

    list_run = []
    position = 0

    for match in graph.re_id.finditer(text):
        id_item = match.group(0)
        if id_item not in graph.map_item:
            continue
        list_run.append(text[position:match.start()])
        list_run.append(htpy.a(class_ = 'mention', href = '/item/' + id_item,
                               title  = id_item)[graph.title(id_item)])
        position = match.end()

    list_run.append(text[position:])

    return list_run


# -----------------------------------------------------------------------------
def _source(graph: Graph, text: str) -> list:
    """
    Return the content of a margin note that cites a source: web
    addresses as links, ids as links to their items.

    """

    list_run = []
    position = 0

    for match in REGEX_URL.finditer(text):
        list_run.extend(_linked(graph, text[position:match.start()]))
        url = match.group(0)
        list_run.append(htpy.a(href = url)[re.sub(r'^https?://(www\.)?', '', url)])
        position = match.end()

    list_run.extend(_linked(graph, text[position:]))

    return list_run
