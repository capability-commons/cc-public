"""
---

id_self:                pym_cc_public.web.page
guid_self:              pym_f20ba79bd0d44614ab802b073339061c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review page rendering
brief:                  |
                        Render the issue list and the page of an issue
                        as HTML.
description:            |
                        The issue list groups the issues by subject,
                        with the size of each argument and whether it
                        is settled. The page of an issue opens with
                        the Sankey diagram of
                        pym_cc_public.web.sankey, then sets each
                        decision and each annotation in the text
                        column, with its standing, what it bears on
                        and the concerns it argues for in the margin.
                        Decisions are read from most supported to most
                        opposed, and annotations in that order: those
                        on the first decision, each followed by those
                        that answer it, then the next.
relation:               []

...
"""


import collections
import typing

import htpy

import cc_public.web.argument
import cc_public.web.sankey


TITLE_SITE        = 'Capability Commons'
PATH_STATIC       = '/static/'
PATH_ISSUE        = '/issue/'
FILE_STYLE        = 'review.css'

MARK_FOR          = '+'
MARK_AGAINST      = '−'

ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
MAP_ROLE          = {cc_public.web.argument.R_SUPPORTS:   ROLE_FOR,
                     cc_public.web.argument.R_CHALLENGES: ROLE_AGAINST}

Graph             = cc_public.web.argument.Graph
Issue             = cc_public.web.argument.Issue
Item              = cc_public.web.argument.Item


# -----------------------------------------------------------------------------
def index(graph: Graph) -> str:
    """
    Return the page that lists every issue, grouped by its subject.

    """

    list_issue = graph.list_issue()
    count_open = sum(1 for issue in list_issue if issue.is_open())

    map_group = collections.defaultdict(list)
    for issue in list_issue:
        for id_subject in issue.item.targets(cc_public.web.argument.R_IS_ABOUT) or ['']:
            map_group[id_subject].append(issue)

    list_section = [htpy.section[
                        htpy.h2[graph.title(id_subject) if id_subject else 'No subject'],
                        _issue_table(graph, map_group[id_subject])]
                    for id_subject in sorted(map_group, key = graph.title)]

    return _page('Issues',
                 [htpy.h1['Issues'],
                  htpy.p(class_ = 'subtitle')[
                      '{count} issues, {open} open'.format(count = len(list_issue),
                                                          open  = count_open)],
                  list_section])


# -----------------------------------------------------------------------------
def issue(graph: Graph, issue: Issue, set_toggle: set[str]) -> str:
    """
    Return the page that shows an issue and the argument on it, with the
    parts of its diagram in set_toggle opened or closed.

    """

    item         = issue.item
    map_number   = {annotation.id: index + 1
                    for (index, annotation) in enumerate(_ordered(graph, issue))}
    list_subject = [graph.title(id_subject)
                    for id_subject in item.targets(cc_public.web.argument.R_IS_ABOUT)]

    return _page(item.title,
                 [htpy.nav[htpy.a(href = '/')['Issues']],
                  htpy.h1[item.title],
                  _block([htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                         [_note_line('Subject', ', '.join(list_subject)),
                          _note_line('Drivers', _drivers(graph, issue)),
                          _id(item.id)]),
                  cc_public.web.sankey.figure(graph, issue, map_number, set_toggle),
                  htpy.section[
                      htpy.h2['Decisions'],
                      [_decision(issue, decision)
                       for decision in cc_public.web.sankey.ordered_decisions(issue)]],
                  _determinations(graph, issue),
                  htpy.section[
                      htpy.h2['Argument'],
                      [_annotation(graph, annotation, map_number)
                       for annotation in _ordered(graph, issue)]]])


# -----------------------------------------------------------------------------
def missing(id_item: str) -> str:
    """
    Return the page for an issue that the tree does not hold.

    """

    return _page('Not found',
                 [htpy.nav[htpy.a(href = '/')['Issues']],
                  htpy.h1['Not found'],
                  htpy.p['The tree holds no issue ', htpy.code[id_item], '.']])


# -----------------------------------------------------------------------------
def _page(title: str, body: typing.Any) -> str:
    """
    Return the HTML of a page with title and body.

    """

    return str(htpy.html(lang = 'en')[
        htpy.head[
            htpy.meta(charset = 'utf-8'),
            htpy.meta(name = 'viewport', content = 'width=device-width, initial-scale=1'),
            htpy.title['{title} - {site}'.format(title = title, site = TITLE_SITE)],
            htpy.link(rel = 'stylesheet', href = PATH_STATIC + FILE_STYLE)],
        htpy.body[
            htpy.header[TITLE_SITE],
            htpy.article[body]]])


# -----------------------------------------------------------------------------
def _issue_table(graph: Graph, list_issue: list[Issue]) -> typing.Any:
    """
    Return a table of the issues in list_issue: what each asks, how much
    argument it holds, and whether it is settled.

    """

    return htpy.table[
        htpy.thead[htpy.tr[htpy.th['Issue'],
                           htpy.th(class_ = 'number')['Decisions'],
                           htpy.th(class_ = 'number')['Annotations'],
                           htpy.th(class_ = 'number')['Drivers argued'],
                           htpy.th['Determined']]],
        htpy.tbody[[
            htpy.tr[
                htpy.td[htpy.a(href = PATH_ISSUE + issue.item.id)[issue.item.title]],
                htpy.td(class_ = 'number')[str(len(issue.list_decision))],
                htpy.td(class_ = 'number')[str(len(issue.list_annotation))],
                htpy.td(class_ = 'number')[
                    '{spoken} of {count}'.format(
                        spoken = len(issue.list_driver) - len(issue.unspoken()),
                        count  = len(issue.list_driver))],
                htpy.td[_settlement(graph, issue)]]
            for issue in list_issue]]]


# -----------------------------------------------------------------------------
def _settlement(graph: Graph, issue: Issue) -> typing.Any:
    """
    Return the decision the issue was settled on, or a mark that it is
    open.

    """

    list_upheld = [id_decision for (id_decision, stance) in issue.map_stance.items()
                   if stance == cc_public.web.argument.STANCE_UPHELD]
    if not list_upheld:
        return _stance(cc_public.web.argument.STANCE_OPEN)
    return [_stance(cc_public.web.argument.STANCE_UPHELD), ' ',
            ', '.join(graph.title(id_decision) for id_decision in list_upheld)]


# -----------------------------------------------------------------------------
def _decision(issue: Issue, decision: Item) -> typing.Any:
    """
    Return a decision: its title and statement, with its standing in
    the margin.

    """

    return _block([htpy.p[htpy.span(class_ = 'run-in')[decision.title], ' ',
                          _prose(decision.brief)]],
                  [_stance(issue.map_stance.get(decision.id,
                                                cc_public.web.argument.STANCE_OPEN)),
                   _id(decision.id)])


# -----------------------------------------------------------------------------
def _determinations(graph: Graph, issue: Issue) -> typing.Any:
    """
    Return the determinations on the issue, or None if it has none.

    """

    if not issue.list_determination:
        return None

    set_current = {determination.id for determination in issue.current()}

    return htpy.section[
        htpy.h2['Determination'],
        [_block([htpy.p[htpy.span(class_ = 'run-in')[determination.title], ' ',
                        _prose(determination.brief)]],
                [None if determination.id in set_current
                 else htpy.p(class_ = 'superseded')['Superseded'],
                 _note_line('Upholds', _titles(graph, determination.targets(
                                                   cc_public.web.argument.R_UPHOLDS))),
                 _note_line('Rejects', _titles(graph, determination.targets(
                                                   cc_public.web.argument.R_REJECTS))),
                 _id(determination.id)])
         for determination in issue.list_determination]]


# -----------------------------------------------------------------------------
def _ordered(graph: Graph, issue: Issue) -> list[Item]:
    """
    Return the annotations on the issue in reading order: those that
    bear on the first decision, then the next, each followed at once
    by the annotations that answer it, and last any not reached so.

    """

    map_annotation = {annotation.id: annotation for annotation in issue.list_annotation}
    list_ordered   = []
    set_seen       = set()

    def visit(id_item: str) -> None:
        for id_relation in MAP_ROLE:
            for id_source in graph.sources(id_relation, id_item):
                if id_source in map_annotation and id_source not in set_seen:
                    set_seen.add(id_source)
                    list_ordered.append(map_annotation[id_source])
                    visit(id_source)

    for decision in cc_public.web.sankey.ordered_decisions(issue):
        visit(decision.id)
    for annotation in issue.list_annotation:
        if annotation.id not in set_seen:
            set_seen.add(annotation.id)
            list_ordered.append(annotation)
            visit(annotation.id)

    return list_ordered


# -----------------------------------------------------------------------------
def _annotation(graph:      Graph,
                annotation: Item,
                map_number: dict[str, int]) -> typing.Any:
    """
    Return an annotation: its number, title, claim and evidence, with
    what it bears on and the concerns it argues for in the margin.

    """

    list_bearing = []
    for (id_relation, role) in MAP_ROLE.items():
        for id_target in annotation.targets(id_relation):
            name = ('#{number}'.format(number = map_number[id_target])
                    if id_target in map_number else graph.title(id_target))
            list_bearing.append(htpy.li(class_ = role)[
                MARK_FOR if role == ROLE_FOR else MARK_AGAINST, ' ', name])

    list_concern = annotation.targets(cc_public.web.argument.R_ARGUES_FOR)
    is_answer    = any(id_target.startswith(cc_public.web.argument.PREFIX_ANNOTATION)
                       for id_relation in MAP_ROLE
                       for id_target in annotation.targets(id_relation))

    return _block([htpy.p[htpy.span(class_ = 'number')[
                              '#{number}'.format(number = map_number[annotation.id])],
                          ' ',
                          htpy.span(class_ = 'run-in')[annotation.title], ' ',
                          _prose(annotation.brief)],
                   _evidence(annotation)],
                  [htpy.ul(class_ = 'bearing')[list_bearing],
                   htpy.p(class_ = 'concerns')[_titles(graph, list_concern)
                                               or ('fact' if is_answer else None)],
                   _id(annotation.id)],
                  class_ = 'annotation answer' if is_answer else 'annotation',
                  id     = annotation.id)


# -----------------------------------------------------------------------------
def _evidence(annotation: Item) -> typing.Any:
    """
    Return the description of the annotation, folded away, or None if
    it has none.

    """

    if not annotation.description:
        return None
    return htpy.details[htpy.summary['Evidence'], _paragraphs(annotation.description)]


# -----------------------------------------------------------------------------
def _drivers(graph: Graph, issue: Issue) -> typing.Any:
    """
    Return the driver concerns of the issue's subject, with those that
    no annotation argues for struck through.

    """

    set_unspoken = set(issue.unspoken())
    list_part    = []

    for id_concern in issue.list_driver:
        if list_part:
            list_part.append(', ')
        name = graph.title(id_concern)
        list_part.append(htpy.s(title = 'Not argued')[name] if id_concern in set_unspoken
                         else name)

    return list_part


# -----------------------------------------------------------------------------
def _block(list_main: list, list_margin: list, **map_attribute: str) -> typing.Any:
    """
    Return a block of the page: list_main in the text column, and
    list_margin beside it in the margin.

    """

    css = 'block ' + map_attribute.pop('class_', '')
    return htpy.div(class_ = css.strip(), **map_attribute)[
        htpy.div(class_ = 'main')[list_main],
        htpy.aside(class_ = 'margin')[list_margin]]


# -----------------------------------------------------------------------------
def _note_line(label: str, value: typing.Any) -> typing.Any:
    """
    Return a line of a margin note, or None if value is empty.

    """

    if not value:
        return None
    return htpy.p[htpy.span(class_ = 'label')[label], ' ', value]


# -----------------------------------------------------------------------------
def _stance(stance: str) -> typing.Any:
    """
    Return the mark of the stance of a decision.

    """

    return htpy.span(class_ = 'stance stance-' + stance)[stance]


# -----------------------------------------------------------------------------
def _titles(graph: Graph, list_id: list[str]) -> str:
    """
    Return the titles of the items list_id, joined by commas.

    """

    return ', '.join(graph.title(id_item) for id_item in list_id)


# -----------------------------------------------------------------------------
def _id(id_item: str) -> typing.Any:
    """
    Return the id of an item, as the margin shows it.

    """

    return htpy.p(class_ = 'id')[htpy.code[id_item]]


# -----------------------------------------------------------------------------
def _prose(text: str) -> str:
    """
    Return text as one run of prose, with its line breaks as spaces.

    """

    return ' '.join(text.split())


# -----------------------------------------------------------------------------
def _paragraphs(text: str) -> list:
    """
    Return text as paragraphs, split at its blank lines.

    """

    return [htpy.p[_prose(part)] for part in text.split('\n\n') if part.strip()]
