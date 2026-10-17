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
                        opposed. The annotations follow the outline of
                        the diagram: grouped by concern in its order,
                        an annotation that argues for several concerns
                        under each, and numbered as the diagram
                        numbers them. Each annotation folds to one
                        line, and opens to its claim, its evidence and
                        the annotations that answer it.
relation:               []

...
"""


import collections
import typing
import urllib.parse

import htpy

import cc_public.web.argument
import cc_public.web.sankey


TITLE_SITE        = 'Capability Commons'
LIST_INDEX        = (('Issues', '/'),)
PATH_STATIC       = '/static/'
PATH_ISSUE        = '/issue/'
PATH_ITEM         = '/item/'
FILE_STYLE        = 'review.css'

MARK_FOR          = '+'
MARK_AGAINST      = '−'
MARK_BOTH         = '±'
MARK_NONE         = '·'
MARK_UNIT         = '■'

# The ways the decision matrix can summarise a cell, chosen by the
# query of the page address: counts for and against, one Pugh mark, or
# one square for each unit of weight.
#
KEY_MATRIX        = 'matrix'
MATRIX_COUNT      = 'count'
MATRIX_PUGH       = 'pugh'
MATRIX_UNIT       = 'unit'
TUPLE_MATRIX      = (MATRIX_COUNT, MATRIX_PUGH, MATRIX_UNIT)

ROLE_FOR          = 'for'
DEPTH_MAX         = 4
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
def issue(graph:      Graph,
          issue:      Issue,
          set_toggle: set[str],
          key_show:   str | None = None,
          matrix:     str = MATRIX_COUNT) -> str:
    """
    Return the page that shows an issue and the argument on it, with the
    parts of its diagram in set_toggle opened or closed, the annotation
    at key_show opened in the list, and the cells of the decision matrix
    drawn as matrix says.

    """

    item         = issue.item
    outline      = cc_public.web.sankey.Outline(graph, issue)
    list_subject = [graph.title(id_subject)
                    for id_subject in item.targets(cc_public.web.argument.R_IS_ABOUT)]

    return _page(item.title,
                 [_matrix(graph, issue, outline, matrix),
                  htpy.section[
                      htpy.h2['Decisions'],
                      [_decision(issue, decision)
                       for decision in cc_public.web.sankey.ordered_decisions(issue)]],
                  _determinations(graph, issue),
                  cc_public.web.sankey.figure(graph, outline, set_toggle, key_show),
                  _argument(graph, outline, key_show),
                  _issue_references(graph, issue)],
                 [htpy.h1[item.title],
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                 [_facts(graph, issue, list_subject)])


# -----------------------------------------------------------------------------
def parse_matrix(query: str) -> str:
    """
    Return how the decision matrix draws its cells, read from the query
    of a page address: MATRIX_COUNT unless the query names another.

    """

    matrix = (urllib.parse.parse_qs(query).get(KEY_MATRIX) or [MATRIX_COUNT])[0]
    return matrix if matrix in TUPLE_MATRIX else MATRIX_COUNT


# -----------------------------------------------------------------------------
def _matrix(graph:   Graph,
            issue:   Issue,
            outline: cc_public.web.sankey.Outline,
            matrix:  str) -> typing.Any:
    """
    Return the decision matrix of the issue: a row for each decision
    and a column for each concern, in the order of the diagram, each
    cell summing what the annotations say for and against the decision
    for the concern, with the standing of each decision and the
    controls that settle it. A driver no annotation argues for is
    marked, as a determination waits on it.

    """

    set_unspoken = set(issue.unspoken())

    def head(id_concern: str) -> typing.Any:
        css = 'concern' if id_concern in issue.list_driver else 'concern other'
        return htpy.th(class_ = css, scope = 'col')[
            htpy.a(href = _href(id_concern))[graph.title(id_concern)],
            htpy.span(class_ = 'unargued')['not argued'] if id_concern in set_unspoken else None]

    return htpy.section(class_ = 'matrix')[
        htpy.h2['Decision matrix'],
        htpy.nav(class_ = 'matrix-style')[
            'Cells: ',
            [[htpy.a(href = '?{key}={value}'.format(key = KEY_MATRIX, value = value),
                     class_ = 'current' if value == matrix else None)[value],
              ' '] for value in TUPLE_MATRIX]],
        htpy.table(class_ = 'matrix matrix-' + matrix)[
            htpy.thead[htpy.tr[
                htpy.th(scope = 'col')['Decision'],
                [head(id_concern) for id_concern in outline.list_concern],
                htpy.th(class_ = 'total', scope = 'col')['All'],
                htpy.th(scope = 'col')['']]],
            htpy.tbody[[
                htpy.tr[
                    htpy.th(scope = 'row')[
                        htpy.a(href = '#' + id_decision)[graph.title(id_decision)],
                        htpy.span(class_ = 'standing')[_stance(issue.map_stance.get(
                            id_decision, cc_public.web.argument.STANCE_OPEN))]],
                    [htpy.td(class_ = 'cell')[_cell(outline.units(decision = id_decision,
                                                                  concern  = id_concern),
                                                    matrix)]
                     for id_concern in outline.list_concern],
                    htpy.td(class_ = 'cell total')[_cell(outline.units(decision = id_decision),
                                                         MATRIX_COUNT)],
                    htpy.td(class_ = 'controls')[_controls(id_decision)]]
                for id_decision in outline.list_decision]]]]


# -----------------------------------------------------------------------------
def _cell(list_unit: list, matrix: str) -> typing.Any:
    """
    Return what a cell of the decision matrix shows of list_unit, the
    units of weight on one decision for one concern, drawn as matrix
    says.

    """

    count_for     = sum(1 for unit in list_unit if unit.is_for())
    count_against = len(list_unit) - count_for

    if not list_unit:
        return htpy.span(class_ = 'none')[MARK_NONE]

    if matrix == MATRIX_PUGH:
        if count_for and count_against:
            return htpy.span(class_ = 'both')[MARK_BOTH]
        if count_for:
            return htpy.span(class_ = 'for')[MARK_FOR]
        return htpy.span(class_ = 'against')[MARK_AGAINST]

    if matrix == MATRIX_UNIT:
        return [htpy.span(class_ = 'for')[MARK_UNIT * count_for] if count_for else None,
                htpy.span(class_ = 'against')[MARK_UNIT * count_against]
                if count_against else None]

    return [htpy.span(class_ = 'for')[MARK_FOR + str(count_for)] if count_for else None,
            ' ' if count_for and count_against else None,
            htpy.span(class_ = 'against')[MARK_AGAINST + str(count_against)]
            if count_against else None]


# -----------------------------------------------------------------------------
def _controls(id_decision: str) -> typing.Any:
    """
    Return the controls that settle the issue on id_decision: uphold
    it, which rejects the other decisions, or reject it alone. This is
    a mock: the controls send nothing yet.

    """

    return htpy.form(class_ = 'determine', method = 'post', action = '#')[
        htpy.input(type = 'hidden', name = 'decision', value = id_decision),
        htpy.button(type = 'button', class_ = 'uphold', disabled = True,
                    title = 'Uphold this decision and reject the others')['Uphold'],
        htpy.button(type = 'button', class_ = 'reject', disabled = True,
                    title = 'Reject this decision')['Reject']]


# -----------------------------------------------------------------------------
def item(graph: Graph, id_item: str) -> str:
    """
    Return the page of any item of the tree: its title, brief and
    description, with its edges in and out, and the items its prose
    names, among the cross-references at its foot.

    """

    item  = graph.map_item[id_item]
    title = item.title or item.id

    list_row = [(_relation(id_relation), list_target)
                for (id_relation, list_target) in sorted(item.map_edge.items())]
    list_row += [('{relation}, from'.format(relation = _relation(id_relation)),
                  graph.sources(id_relation, id_item))
                 for id_relation in sorted({id_relation
                                            for (id_relation, id_target) in graph.map_source
                                            if id_target == id_item})]
    list_row += [('Mentions',     graph.mentions(id_item)),
                 ('Mentioned by', graph.mentioned_by(id_item))]

    return _page(title,
                 [_block(_paragraphs(item.description), []),
                  _references(graph, list_row)],
                 [htpy.h1[title],
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)] if item.brief else None],
                 [htpy.table(class_ = 'facts')[htpy.tbody[
                     htpy.tr[htpy.th(scope = 'row')['Id'], htpy.td[htpy.code[item.id]]]]]])


# -----------------------------------------------------------------------------
def missing(id_item: str) -> str:
    """
    Return the page for an issue or item that the tree does not hold.

    """

    return _page('Not found',
                 [htpy.h1['Not found'],
                  htpy.p['The tree holds no issue ', htpy.code[id_item], '.']])


# -----------------------------------------------------------------------------
def _page(title:       str,
          body:        typing.Any,
          head:        typing.Any = None,
          head_margin: typing.Any = None) -> str:
    """
    Return the HTML of a page with title and body. head follows the
    name of the site and the links to the indexes in the text column,
    with head_margin beside them in the margin, so the margin starts at
    the top of the page.

    """

    return str(htpy.html(lang = 'en')[
        htpy.head[
            htpy.meta(charset = 'utf-8'),
            htpy.meta(name = 'viewport', content = 'width=device-width, initial-scale=1'),
            htpy.title['{title} - {site}'.format(title = title, site = TITLE_SITE)],
            htpy.link(rel = 'stylesheet', href = PATH_STATIC + FILE_STYLE)],
        htpy.body[
            htpy.article[
                _block([htpy.header[TITLE_SITE,
                                    [[htpy.span(class_ = 'bar')['|'],
                                      htpy.a(href = href)[name]]
                                     for (name, href) in LIST_INDEX]],
                        head],
                       [head_margin],
                       class_ = 'masthead ruled' if head_margin else 'masthead'),
                body]]])


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
                           htpy.th(class_ = 'number')['Concerns'],
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
                   _id(decision.id)],
                  id = decision.id)


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
def _argument(graph:    Graph,
              outline:  cc_public.web.sankey.Outline,
              key_show: str | None) -> typing.Any:
    """
    Return the annotations of the outline, grouped by concern in the
    order of the diagram, then those no concern reaches. The annotation
    at key_show is opened, with those it sits within.

    """

    list_group = []
    for id_concern in outline.list_concern:
        list_annotation = outline.map_annotation[id_concern]
        if not list_annotation:
            continue
        list_unit = outline.units(concern = id_concern)
        count_for = sum(1 for unit in list_unit if unit.is_for())
        list_group.append(htpy.section(class_ = 'concern-group')[
            _block([htpy.h3[graph.title(id_concern)]],
                   [htpy.p(class_ = 'tally')[
                        htpy.span(class_ = ROLE_FOR)['+{count}'.format(count = count_for)],
                        ' ',
                        htpy.span(class_ = ROLE_AGAINST)['−{count}'.format(
                                                             count = len(list_unit) - count_for)],
                        ' driving concern' if id_concern in outline.issue.list_driver
                        else None]]),
            [_annotation(graph, outline, id_annotation,
                         cc_public.web.sankey.DELIM_KEY.join((id_concern, id_annotation)),
                         id_concern, set(), key_show)
             for id_annotation in list_annotation]])

    if outline.list_other:
        list_group.append(htpy.section(class_ = 'concern-group')[
            _block([htpy.h3['Other annotations']], []),
            [_annotation(graph, outline, id_annotation, id_annotation, None, set(), key_show)
             for id_annotation in outline.list_other]])

    return htpy.section[htpy.h2['Argument'], list_group]


# -----------------------------------------------------------------------------
def _annotation(graph:         Graph,
                outline:       cc_public.web.sankey.Outline,
                id_annotation: str,
                key:           str,
                id_concern:    str | None,
                set_path:      set[str],
                key_show:      str | None) -> typing.Any:
    """
    Return an annotation folded to one line: its number, title and what
    it bears on. Open, it shows its claim and evidence, then the
    annotations that answer it, folded the same way. key places it in
    the outline, under id_concern if it is not an answer; set_path
    holds the annotations above it. It is opened if key_show is key
    or lies within it.

    """

    annotation = graph.map_item[id_annotation]
    map_number = outline.map_number

    list_bearing = []
    for (id_relation, role) in MAP_ROLE.items():
        for id_target in annotation.targets(id_relation):
            name = ('#{number}'.format(number = map_number[id_target])
                    if id_target in map_number else graph.title(id_target))
            list_bearing.append(htpy.li(class_ = role)[
                MARK_FOR if role == ROLE_FOR else MARK_AGAINST, ' ', name])

    list_concern = annotation.targets(cc_public.web.argument.R_ARGUES_FOR)
    list_also    = [id_other for id_other in list_concern if id_other != id_concern]
    list_answer  = [id_answer for (id_answer, _) in outline.answers(id_annotation)
                    if id_answer not in set_path]

    return htpy.details(class_ = 'annotation depth-{depth}'.format(depth = min(len(set_path),
                                                                                DEPTH_MAX)),
                        id     = key,
                        open   = _is_within(key_show, key))[
        htpy.summary[_block(
            [htpy.p[htpy.span(class_ = 'number')[
                        '#{number}'.format(number = map_number[id_annotation])],
                    ' ',
                    htpy.span(class_ = 'run-in')[annotation.title]]],
            [htpy.ul(class_ = 'bearing')[list_bearing],
             _summary_note(graph, list_also, len(list_answer))])],
        _block([htpy.p[_prose(annotation.brief)], _evidence(annotation)],
               [None if id_concern
                else htpy.p(class_ = 'concerns')[_titles(graph, list_concern) or 'fact'],
                _id(annotation.id)],
               class_ = 'body'),
        [_annotation(graph, outline, id_answer,
                     cc_public.web.sankey.DELIM_KEY.join((key, id_answer)),
                     None, set_path | {id_annotation}, key_show)
         for id_answer in list_answer]]


# -----------------------------------------------------------------------------
def _is_within(key_show: str | None, key: str) -> bool:
    """
    Return True if key_show is key or lies within it.

    """

    return key_show is not None and (key_show == key
                                     or key_show.startswith(key + cc_public.web.sankey.DELIM_KEY))


# -----------------------------------------------------------------------------
def _summary_note(graph: Graph, list_also: list[str], count_answer: int) -> typing.Any:
    """
    Return the note under what a folded annotation bears on: the other
    concerns it sits under, and how many annotations answer it. None if
    there is neither.

    """

    list_part = []
    if list_also:
        list_part.append('also ' + _titles(graph, list_also))
    if count_answer:
        list_part.append('{count} {noun}'.format(count = count_answer,
                                                 noun  = 'answer' if count_answer == 1
                                                         else 'answers'))
    if not list_part:
        return None
    return htpy.p(class_ = 'note')[' · '.join(list_part)]


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
def _facts(graph: Graph, issue: Issue, list_subject: list[str]) -> typing.Any:
    """
    Return the table of facts about an issue that stands beside its
    brief: its standing, its subject, the drivers of its subject and how
    much argument it holds.

    """

    def row(label: str, value: typing.Any) -> typing.Any:
        return htpy.tr[htpy.th(scope = 'row')[label], htpy.td[value]]

    set_unspoken = set(issue.unspoken())
    list_driver  = [htpy.span(class_ = 'line')[
                        htpy.s(title = 'Not argued')[graph.title(id_concern)]
                        if id_concern in set_unspoken else graph.title(id_concern)]
                    for id_concern in issue.list_driver]

    return htpy.table(class_ = 'facts')[htpy.tbody[
        row('Standing', _settlement(graph, issue)),
        row('Subject',  ', '.join(list_subject)) if list_subject else None,
        row('Concerns', list_driver) if list_driver else None,
        row('Argument', '{decisions} decisions, {annotations} annotations'.format(
                            decisions   = len(issue.list_decision),
                            annotations = len(issue.list_annotation)))]]


# -----------------------------------------------------------------------------
def _issue_references(graph: Graph, issue: Issue) -> typing.Any:
    """
    Return the cross-references at the foot of the page of issue: its
    subject and the other issues about it, the concerns argued, and the
    items that point at or are named by what the page shows, beyond
    the page itself.

    """

    is_about     = cc_public.web.argument.R_IS_ABOUT
    list_shown   = ([issue.item] + issue.list_decision + issue.list_annotation
                   + issue.list_determination)
    set_shown    = {shown.id for shown in list_shown}
    list_subject = issue.item.targets(is_about)

    list_same    = sorted({id_other
                           for id_subject in list_subject
                           for id_other in graph.sources(is_about, id_subject)
                           if id_other.startswith(cc_public.web.argument.PREFIX_ISSUE)
                           and id_other != issue.item.id})
    list_concern = sorted(issue.set_spoken, key = graph.title)
    list_mention = sorted({id_named for shown in list_shown
                           for id_named in graph.mentions(shown.id)} - set_shown)
    list_named   = sorted({id_source for shown in list_shown
                           for id_source in graph.mentioned_by(shown.id)} - set_shown)
    list_cited   = sorted({id_source
                           for ((_, id_target), list_source) in graph.map_source.items()
                           if id_target in set_shown
                           for id_source in list_source} - set_shown)

    return _references(graph, [('Subject',         list_subject),
                               ('Same subject',    list_same),
                               ('Concerns argued', list_concern),
                               ('Mentions',        list_mention),
                               ('Mentioned by',    list_named),
                               ('Cited by',        list_cited)])


# -----------------------------------------------------------------------------
def _references(graph: Graph, list_row: list[tuple[str, list[str]]]) -> typing.Any:
    """
    Return the cross-references at the foot of a page, folded: a row
    for each label in list_row that has items, each item a link.

    """

    list_row = [(label, list_id) for (label, list_id) in list_row if list_id]
    count    = len({id_item for (_, list_id) in list_row for id_item in list_id})

    return htpy.footer(class_ = 'bookend')[htpy.details[
        htpy.summary['Cross-references ', htpy.span(class_ = 'note')[str(count)]],
        htpy.table(class_ = 'facts references')[htpy.tbody[
            [htpy.tr[htpy.th(scope = 'row')[label],
                     htpy.td[[htpy.span(class_ = 'line')[_link(graph, id_item)]
                              for id_item in list_id]]]
             for (label, list_id) in list_row]]]]]


# -----------------------------------------------------------------------------
def _relation(id_relation: str) -> str:
    """
    Return the name of the relation id_relation as a label reads it:
    its id as words, without the prefix.

    """

    words = id_relation.removeprefix('r_').replace('_', ' ')
    return words[:1].upper() + words[1:]


# -----------------------------------------------------------------------------
def _link(graph: Graph, id_item: str) -> typing.Any:
    """
    Return a link to the page of id_item, named by its title.

    """

    return htpy.a(href = _href(id_item))[graph.title(id_item)]


# -----------------------------------------------------------------------------
def _href(id_item: str) -> str:
    """
    Return the address of the page of id_item: the issue page for an
    issue, the item page otherwise.

    """

    if id_item.startswith(cc_public.web.argument.PREFIX_ISSUE):
        return PATH_ISSUE + id_item
    return PATH_ITEM + id_item


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

    return htpy.p(class_ = 'id')[htpy.a(href = _href(id_item))[htpy.code[id_item]]]


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
