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
                        Render the issue list, the page of an issue,
                        the requirement list and the page of a
                        requirement as HTML.
description:            |
                        The issue list groups the issues by subject,
                        with the size of each argument and whether it
                        is settled. The page of an issue opens with
                        its decision matrix: a column for each
                        decision and a row for each concern, in the
                        order of the Sankey diagram of
                        pym_cc_public.web.sankey. Decisions are read
                        from most supported to most opposed. Each
                        concern row opens to the annotations that
                        argue for it, numbered as the diagram numbers
                        them, an annotation that argues for several
                        concerns under each. An annotation folds to
                        its title, which opens to its brief, which
                        opens to its description, which opens to the
                        annotations that answer it. Opened parts set
                        their text in the text column and their notes
                        in the margin. The decisions, the diagram and
                        the cross-references follow.

                        The requirement list groups the requirements
                        by subject. The page of a requirement reads
                        down its trace: what it comes from, why it is
                        needed, its statement parsed into its slots,
                        the subject it is allocated to with the
                        concerns that drive it, and how it is to be
                        verified. The questions of
                        pym_cc_public.requirement.review and the
                        characteristics it is reviewed against follow.
relation:               []

...
"""


import collections
import typing
import urllib.parse

import htpy

import cc_public.requirement.compose
import cc_public.requirement.review
import cc_public.web.argument
import cc_public.web.description
import cc_public.web.light
import cc_public.web.network
import cc_public.web.restriction
import cc_public.web.sankey


TITLE_SITE        = 'Capability Commons'
PATH_REQUIREMENTS = '/requirements'
LIST_INDEX        = (('Issues', '/'), ('Requirements', PATH_REQUIREMENTS))
PATH_STATIC       = '/static/'
PATH_ISSUE        = '/issue/'
PATH_REQUIREMENT  = '/requirement/'
PATH_ITEM         = '/item/'
FILE_STYLE        = 'review.css'
FILE_SCRIPT       = 'review.js'
CSS_MUTES         = cc_public.web.light.CSS_MUTES
CSS_FADES         = cc_public.web.light.CSS_FADES

MARK_FOR          = cc_public.web.light.MARK_FOR
MARK_AGAINST      = cc_public.web.light.MARK_AGAINST
MARK_NONE         = '·'
MARK_PREVIOUS     = '←'
MARK_NEXT         = '→'

ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
MAP_ROLE          = {cc_public.web.argument.R_SUPPORTS:   ROLE_FOR,
                     cc_public.web.argument.R_CHALLENGES: ROLE_AGAINST}

R_HAS_SUBJECT     = cc_public.requirement.compose.R_HAS_SUBJECT
R_HAS_PROCESS     = cc_public.requirement.compose.R_HAS_PROCESS
R_TO_PARENT       = cc_public.requirement.review.R_TRACES_TO_PARENT
R_TO_SOURCE       = cc_public.requirement.review.R_TRACES_TO_SOURCE

# What each obligation binds the subject to, after ISO/IEC/IEEE 29148.
#
MAP_OBLIGATION    = {'shall':  'binding',
                     'should': 'a preference',
                     'will':   'a statement of fact or purpose',
                     'may':    'an allowance'}

# How each kind of condition reads, as the margin of a statement names
# it.
#
MAP_CONDITION     = {'logic': 'a logical condition',
                     'event': 'an event condition',
                     'time':  'a time condition'}

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

    list_section = [htpy.section[
                        htpy.h2[graph.title(id_subject) if id_subject else 'No subject'],
                        _issue_table(graph, list_group)]
                    for (id_subject, list_group) in _groups(graph)]

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
          set_show:   set[str] | None = None) -> str:
    """
    Return the page that shows an issue and the argument on it, with the
    parts of its diagram in set_toggle opened or closed, the annotation
    in set_show opened in the decision matrix. The Sankey diagram is
    shown and the graph folded away under its caption.

    """

    item         = issue.item
    outline      = cc_public.web.sankey.Outline(graph, issue)
    list_subject = [graph.title(id_subject)
                    for id_subject in item.targets(cc_public.web.argument.R_IS_ABOUT)]

    return _page(item.title,
                 [_lighting(graph, outline),
                  _matrix(graph, issue, outline, set_show or set()),
                  _determinations(graph, issue),
                  _diagram('Argument flow', 'sankey', True,
                           cc_public.web.sankey.figure(graph, outline, set_toggle,
                                                       set_show or set())),
                  _diagram('Argument tree', 'network', False,
                           cc_public.web.network.figure(graph, outline)),
                  _issue_references(graph, issue)],
                 [htpy.h1[item.title],
                  _sequence(graph, issue),
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                 [_facts(graph, issue, list_subject)])


# -----------------------------------------------------------------------------
def _lighting(graph: Graph, outline: cc_public.web.sankey.Outline) -> list:
    """
    Return the rules that light each chain of the argument in outline,
    in the matrix and in both diagrams alike, and an element that pins
    each chain whose name the page does not already hold as an id: the
    matrix holds a decision, each of its roles, and each concern that
    opens to annotations.

    """

    chain    = cc_public.web.light.chain
    set_held = {chain(id_decision, role) for id_decision in outline.list_decision
                for role in (None, ROLE_FOR, ROLE_AGAINST)}
    set_held |= {chain(id_concern) for id_concern in outline.list_concern
                 if outline.map_annotation[id_concern]}
    list_name = list(dict.fromkeys(cc_public.web.sankey.lighting(graph, outline).names()
                                   + cc_public.web.network.names(outline)))
    return [cc_public.web.light.style(list_name),
            cc_public.web.light.pins([name for name in list_name if name not in set_held])]


# -----------------------------------------------------------------------------
def _diagram(caption: str, name: str, is_open: bool, figure: typing.Any) -> typing.Any:
    """
    Return figure folded under a caption that shows or hides it, open
    if is_open. A folded diagram is still lit and pinned, so it opens
    as it would have shown.

    """

    return htpy.details(class_ = 'diagram ' + name, open = is_open)[
        htpy.summary[htpy.span(class_ = 'label')[caption]],
        figure]


# -----------------------------------------------------------------------------
def _matrix(graph:    Graph,
            issue:    Issue,
            outline:  cc_public.web.sankey.Outline,
            set_show: set[str]) -> typing.Any:
    """
    Return the decision matrix of the issue: a column for each decision
    and a row for each concern, in the order of the diagram, each cell
    showing a square for each unit of weight for or against the decision
    for the concern. Each row opens to the annotations that argue for
    its concern; those in set_show are opened. The foot holds the total
    and the standing of each decision and the controls that settle it.
    A driver no annotation argues for is marked, as a determination
    waits on it.

    """

    list_decision = outline.list_decision

    def row(list_label: list, list_cell: list, **map_attribute: str) -> typing.Any:
        css = 'row ' + map_attribute.pop('class_', '')
        return htpy.div(class_ = css.strip(), **map_attribute)[
            htpy.div(class_ = 'label')[list_label],
            [htpy.div(class_ = 'cell')[cell] for cell in list_cell]]

    map_decision = {decision.id: decision for decision in issue.list_decision}
    drawing      = cc_public.web.sankey.lighting(graph, outline)
    list_row     = [row([], [[htpy.a(href   = '#' + id_decision,
                                     class_ = ' '.join([CSS_MUTES,
                                                        *drawing.css_decision(id_decision),
                                                        cc_public.web.light.show(id_decision)]))[
                                  graph.title(id_decision)],
                              htpy.div(class_ = 'total')[
                                  _total(id_decision, outline.units(decision = id_decision),
                                         drawing.css_decision(id_decision))]]
                             for id_decision in list_decision]
                            + [htpy.span(class_ = 'add')[
                                   _pill('+ Decision', '',
                                         'Add a decision that answers this issue')]],
                        class_ = 'head'),
                    _decision_style(list_decision),
                    [htpy.span(class_ = 'decision-role',
                               id     = cc_public.web.light.chain(id_decision, role))
                     for id_decision in list_decision
                     for role in (cc_public.web.light.ROLE_FOR, cc_public.web.light.ROLE_AGAINST)],
                    [_decision(graph, issue, map_decision[id_decision])
                     for id_decision in list_decision]]

    for id_concern in outline.list_concern:
        list_annotation = outline.map_annotation[id_concern]
        list_cell       = [_cell_link(outline, drawing, id_decision, id_concern)
                           for id_decision in list_decision]
        label           = _concern_label(graph, issue, id_concern,
                                             drawing.css_concern(id_concern))
        if not list_annotation:
            list_row.append(row(label, list_cell, class_ = 'concern'))
            continue
        list_row.append(htpy.details(class_ = 'concern', id = id_concern,
                                     open   = _is_within(set_show, id_concern))[
            htpy.summary[row(label, list_cell)],
            htpy.div(class_ = 'drill')[
                [_annotation(graph, outline, drawing, id_annotation,
                             cc_public.web.sankey.DELIM_KEY.join((id_concern, id_annotation)),
                             id_concern, set(), set_show)
                 for id_annotation in list_annotation]]])

    if outline.list_other:
        list_row.append(htpy.details(class_ = 'concern other', id = 'other',
                                     open   = any(_is_within(set_show, id_annotation)
                                                  for id_annotation in outline.list_other))[
            htpy.summary[row([htpy.span(class_ = 'name')['Other annotations']],
                             [None for _ in list_decision])],
            htpy.div(class_ = 'drill')[
                [_annotation(graph, outline, drawing, id_annotation, id_annotation, None, set(),
                             set_show)
                 for id_annotation in outline.list_other]]])

    list_row += [
        row(['Standing'], [_stance(issue.map_stance.get(id_decision,
                                                        cc_public.web.argument.STANCE_OPEN))
                           for id_decision in list_decision], class_ = 'foot standing'),
        row([], [_controls(id_decision) for id_decision in list_decision],
            class_ = 'foot controls')]

    return htpy.section(class_ = 'matrix ' + cc_public.web.light.CSS_REGION,
                        style  = '--decisions: {count}'.format(count = len(list_decision)))[
        list_row]


# -----------------------------------------------------------------------------
def _concern_label(graph:      Graph,
                   issue:      Issue,
                   id_concern: str,
                   list_css:   list[str]) -> list:
    """
    Return the label of the row of id_concern in the decision matrix:
    its name, in the chains of list_css, which lights the chains of the
    concern while it is hovered over, marked if it is a driver no
    annotation argues for.

    """

    name      = cc_public.web.light.chain(id_concern)
    list_show = [cc_public.web.light.show(name)] if list_css else []
    return [htpy.span(class_ = ' '.join(['name', CSS_MUTES, *list_css, *list_show]))[
                graph.title(id_concern)],
            htpy.span(class_ = 'unargued')['not argued']
            if id_concern in set(issue.unspoken()) else None]


# -----------------------------------------------------------------------------
def _cell_link(outline:     cc_public.web.sankey.Outline,
               drawing:     typing.Any,
               id_decision: str,
               id_concern:  str) -> typing.Any:
    """
    Return a cell of the decision matrix, linked to the annotations
    that argue for id_concern on id_decision, all opened in its row and
    the first in view.

    """

    list_unit = outline.units(decision = id_decision, concern = id_concern)
    if not list_unit:
        return _cell(list_unit, drawing)

    set_on   = {unit.annotation for unit in list_unit}
    list_key = [cc_public.web.sankey.DELIM_KEY.join((id_concern, id_annotation))
                for id_annotation in outline.map_annotation[id_concern]
                if id_annotation in set_on]
    href     = '?{query}#{key}'.format(
                   query = urllib.parse.urlencode(
                               [(cc_public.web.sankey.KEY_SHOW, key) for key in list_key]),
                   key   = list_key[0])

    return htpy.a(class_ = 'cell', href = href)[_cell(list_unit, drawing)]


# -----------------------------------------------------------------------------
def _cell(list_unit: list, drawing: typing.Any) -> typing.Any:
    """
    Return what a cell of the decision matrix shows of list_unit, the
    units of weight on one decision for one concern: a disc marked with
    a tick for each unit for, then one marked with a cross for each
    unit against, each in the chains of drawing that the unit is in.

    """

    if not list_unit:
        return htpy.span(class_ = 'none')[MARK_NONE]

    list_for      = [unit for unit in list_unit if unit.is_for()]
    list_against  = [unit for unit in list_unit if not unit.is_for()]
    return htpy.span(class_ = 'units',
                     title  = '{f} for, {a} against'.format(f = len(list_for),
                                                            a = len(list_against)))[
        [htpy.span(class_ = ' '.join(['unit', role, CSS_FADES, *drawing.css_unit(unit)]))[mark]
         for (list_role, role, mark) in ((list_for, ROLE_FOR, MARK_FOR),
                                         (list_against, ROLE_AGAINST, MARK_AGAINST))
         for unit in list_role]]


# -----------------------------------------------------------------------------
def _total(id_decision: str, list_unit: list, list_css: list[str]) -> typing.Any:
    """
    Return the total of list_unit, the units of weight on id_decision,
    in words: how many are for it and how many against, each in the
    chains of list_css. Each count lights the chains that reach the
    decision with that role while it is hovered over, and shows the
    decision and pins them when it is clicked.

    """

    count_for = sum(1 for unit in list_unit if unit.is_for())
    list_link = []
    for (role, count) in ((ROLE_FOR, count_for), (ROLE_AGAINST, len(list_unit) - count_for)):
        name = cc_public.web.light.chain(id_decision, role)
        list_link.append(htpy.a(class_ = ' '.join([role, CSS_FADES, *list_css,
                                                   cc_public.web.light.show(name)]),
                                href   = '#' + name)[
                             '{count} {role}'.format(count = count, role = role)])
    return [list_link[0], ', ', list_link[1]]


# -----------------------------------------------------------------------------
def _controls(id_decision: str) -> typing.Any:
    """
    Return the controls that settle the issue on id_decision: uphold
    it, which rejects the other decisions, or reject it alone. This is
    a mock: the controls send nothing yet.

    """

    return htpy.form(class_ = 'determine', method = 'post', action = '#')[
        htpy.input(type = 'hidden', name = 'decision', value = id_decision),
        _pill('Uphold', ROLE_FOR, 'Uphold this decision and reject the others'),
        _pill('Reject', ROLE_AGAINST, 'Reject this decision')]


# -----------------------------------------------------------------------------
def _pill(label: str, role: str, title: str) -> typing.Any:
    """
    Return a button that changes the data, as a pill: for or against
    in the colours of role, or plain if role is ''. This is a mock: the
    button sends nothing yet.

    """

    return htpy.button(type = 'button', class_ = ' '.join(['pill', role]).strip(),
                       title = title + ' (not yet wired)')[label]


# -----------------------------------------------------------------------------
def _add_answer(id_annotation: str) -> typing.Any:
    """
    Return the controls that add an annotation answering id_annotation,
    in support or in challenge, set in the margin.

    """

    return _block([], [htpy.p(class_ = 'add')[
                           _pill('+ Support', ROLE_FOR, 'Add an annotation that supports this'),
                           ' ',
                           _pill('+ Challenge', ROLE_AGAINST,
                                 'Add an annotation that challenges this')]],
                  class_ = 'add', data_for = id_annotation)


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

    list_issue = _issues_of(graph, item)
    statement  = _statement(graph, item)
    list_prose = (_paragraphs(item.brief) if statement else []) + _paragraphs(item.description)
    list_prose += [htpy.p[[_part(part) for part in sentence]]
                   for sentence in cc_public.web.restriction.sentences(graph, id_item)]
    subtitle   = statement or _prose(item.brief)

    return _page(title,
                 [_block(list_prose, []),
                  _references(graph, list_row, is_open = not item.description)],
                 [htpy.h1[title],
                  htpy.p(class_ = 'subtitle')[subtitle] if subtitle else None],
                 [htpy.table(class_ = 'facts')[htpy.tbody[
                     htpy.tr[htpy.th(scope = 'row')['Issue'],
                             htpy.td[[htpy.span(class_ = 'line')[_link(graph, id_issue)]
                                      for id_issue in list_issue]]] if list_issue else None,
                     htpy.tr[htpy.th(scope = 'row')['Id'], htpy.td[htpy.code[item.id]]]]]])


# -----------------------------------------------------------------------------
def _part(part: cc_public.web.restriction.Part) -> typing.Any:
    """
    Return a part of a sentence: its text, or a link with its text to
    the page of the item it names.

    """

    if isinstance(part, tuple):
        (id_item, text) = part
        return htpy.a(href = _href(id_item))[text]
    return part


# -----------------------------------------------------------------------------
def _statement(graph: Graph, item: Item) -> str:
    """
    Return the statement composed from the slots of item if it is a
    requirement, or an empty string if it is not, or if its slots do
    not compose.

    """

    if not item.id.startswith(cc_public.requirement.compose.PREFIX_REQUIREMENT):
        return ''

    try:
        return cc_public.requirement.compose.statement(item.node, graph.node)
    except cc_public.requirement.compose.ErrorCompose:
        return ''


# -----------------------------------------------------------------------------
def _issues_of(graph: Graph, item: Item) -> list[str]:
    """
    Return the issues the argument item belongs to: those a decision
    answers, an annotation is about, or a determination settles through
    its decisions.

    """

    list_decision = (item.targets(cc_public.web.argument.R_UPHOLDS)
                     + item.targets(cc_public.web.argument.R_REJECTS))
    list_target   = (item.targets(cc_public.web.argument.R_ANSWERS)
                     + item.targets(cc_public.web.argument.R_IS_ABOUT)
                     + [id_issue for id_decision in list_decision
                        if id_decision in graph.map_item
                        for id_issue in graph.map_item[id_decision].targets(
                                            cc_public.web.argument.R_ANSWERS)])

    return [id_target for id_target in dict.fromkeys(list_target)
            if id_target.startswith(cc_public.web.argument.PREFIX_ISSUE)]


# -----------------------------------------------------------------------------
def requirements(graph: Graph) -> str:
    """
    Return the page that lists every requirement, grouped by its subject.

    """

    list_group = _requirement_groups(graph)
    count      = sum(len(list_item) for (_, list_item) in list_group)
    count_bind = sum(1 for (_, list_item) in list_group for each in list_item
                     if each.node.get('obligation') == 'shall')

    list_section = [htpy.section[
                        htpy.h2[graph.title(id_subject) if id_subject else 'No subject'],
                        _requirement_table(graph, list_item)]
                    for (id_subject, list_item) in list_group]

    return _page('Requirements',
                 [htpy.h1['Requirements'],
                  htpy.p(class_ = 'subtitle')[
                      '{count} requirements, {binding} binding'.format(count   = count,
                                                                      binding = count_bind)],
                  list_section])


# -----------------------------------------------------------------------------
def _requirement_groups(graph: Graph) -> list[tuple[str, list[Item]]]:
    """
    Return the requirements grouped by subject, as the index lists
    them: each subject, by title, with its requirements by title. A
    requirement with no subject is grouped under ''.

    """

    map_group = collections.defaultdict(list)
    for item in sorted(graph.map_item.values(), key = lambda item: item.title or item.id):
        if item.id.startswith(cc_public.requirement.compose.PREFIX_REQUIREMENT):
            for id_subject in item.targets(R_HAS_SUBJECT) or ['']:
                map_group[id_subject].append(item)

    return [(id_subject, map_group[id_subject])
            for id_subject in sorted(map_group, key = graph.title)]


# -----------------------------------------------------------------------------
def _requirement_table(graph: Graph, list_item: list[Item]) -> typing.Any:
    """
    Return a table of the requirements in list_item: each with its
    statement under its title, its obligation, how it is verified, and
    what it traces to.

    """

    def traced(item: Item) -> typing.Any:
        list_trace = [name for (name, id_relation) in (('Parent', R_TO_PARENT),
                                                       ('Source', R_TO_SOURCE))
                      if item.targets(id_relation)]
        return ', '.join(list_trace) or htpy.span(class_ = 'gap')['None']

    return htpy.table(class_ = 'requirements')[
        htpy.thead[htpy.tr[htpy.th['Requirement'],
                           htpy.th['Obligation'],
                           htpy.th['Verification'],
                           htpy.th['Traced to']]],
        htpy.tbody[[
            htpy.tr[
                htpy.td[htpy.a(href = _href(item.id))[item.title or item.id],
                        htpy.span(class_ = 'statement')[_statement(graph, item)]],
                htpy.td[item.node.get('obligation', '')],
                htpy.td[str(item.node.get('verification_method', '')).capitalize()],
                htpy.td[traced(item)]]
            for item in list_item]]]


# -----------------------------------------------------------------------------
def requirement(graph: Graph, id_requirement: str) -> str | None:
    """
    Return the page of a requirement, or None if id_requirement names no
    requirement whose slots compose.

    The page reads down the trace of the requirement: what it comes
    from and why it is needed, its statement, the subject it is
    allocated to with the concerns that drive that subject, and how it
    is to be shown to be met. The questions a reviewer asks of it and
    the characteristics it is reviewed against follow.

    """

    item = graph.map_item.get(id_requirement)
    if (item is None
            or not id_requirement.startswith(cc_public.requirement.compose.PREFIX_REQUIREMENT)):
        return None
    try:
        list_part = cc_public.requirement.compose.parts(item.node, graph.node)
    except cc_public.requirement.compose.ErrorCompose:
        return None

    node          = item.node
    process       = next(part.text for part in list_part
                         if part.slot == cc_public.requirement.compose.SLOT_PROCESS)
    list_question = cc_public.requirement.review.questions(node, process)
    list_said     = cc_public.requirement.review.characteristics(
                        node, list_question, item.targets(R_TO_PARENT))

    return _page(item.title,
                 [_block(_paragraphs(item.brief) + _paragraphs(item.description),
                         [htpy.p[htpy.span(class_ = 'label')['In plain words']]]),
                  _trace(graph, item, list_part),
                  _questions(list_question),
                  _characteristics(list_said),
                  _requirement_references(graph, item)],
                 [htpy.h1[item.title],
                  _steps(graph, [each.id for (_, list_item) in _requirement_groups(graph)
                                 for each in list_item],
                         item.id, 'requirement'),
                  htpy.p(class_ = 'subtitle')[_statement(graph, item)]],
                 [_requirement_facts(graph, item, process)])


# -----------------------------------------------------------------------------
def _requirement_facts(graph: Graph, item: Item, process: str) -> typing.Any:
    """
    Return the table of facts that stands beside the statement of a
    requirement: its obligation, subject, process, verification and
    what it traces to.

    """

    def row(label: str, value: typing.Any) -> typing.Any:
        return htpy.tr[htpy.th(scope = 'row')[label], htpy.td[value]]

    node       = item.node
    obligation = node.get('obligation', '')
    list_trace = item.targets(R_TO_PARENT) + item.targets(R_TO_SOURCE)

    return htpy.table(class_ = 'facts')[htpy.tbody[
        row('Obligation',   '{word}, {meaning}'.format(
                                word = obligation, meaning = MAP_OBLIGATION.get(obligation, ''))),
        row('Subject',      [_link(graph, id_subject)
                             for id_subject in item.targets(R_HAS_SUBJECT)]),
        row('Process',      [htpy.a(href = _href(id_process))[process]
                             for id_process in item.targets(R_HAS_PROCESS)]),
        row('Verification', str(node.get('verification_method', '')).capitalize()),
        row('Traced to',    [htpy.span(class_ = 'line')[_link(graph, id_trace)]
                             for id_trace in list_trace]
                            or htpy.span(class_ = 'gap')['Neither parent nor source']),
        row('Id',           htpy.code[item.id])]]


# -----------------------------------------------------------------------------
def _trace(graph: Graph, item: Item, list_part: list) -> typing.Any:
    """
    Return the trace of a requirement as stations down a spine: what it
    comes from, why it is needed, its statement, where it is allocated,
    and how it is to be verified. A station the tree records nothing
    for is drawn hollow and says so.

    """

    node       = item.node
    kind       = node.get('condition_kind')
    obligation = node.get('obligation', '')

    def station(label: str, list_main: list, list_note: list, css: str = '') -> typing.Any:
        css_station = ' '.join(['station', css if list_main else 'gap']).strip()
        return _block(list_main or [htpy.p(class_ = 'gap')['Not recorded.']],
                      [htpy.p[htpy.span(class_ = 'label')[label]], list_note],
                      class_ = css_station)

    def traced(id_relation: str) -> list:
        return [htpy.p[_link(graph, id_target), ' ',
                       htpy.span(class_ = 'gloss')[_prose(graph.map_item[id_target].brief)]
                       if id_target in graph.map_item else None]
                for id_target in item.targets(id_relation)]

    list_subject = item.targets(R_HAS_SUBJECT)
    list_driver  = [id_concern for id_subject in list_subject
                    if id_subject in graph.map_item
                    for id_concern in graph.map_item[id_subject].targets(
                                          cc_public.web.argument.R_IS_DRIVEN_BY)]
    list_note    = [_note_line('Driven by', [
                        [', ' if index else '', _link(graph, id_concern)]
                        for (index, id_concern) in enumerate(list_driver)])]

    return htpy.section(class_ = 'trace')[
        htpy.h2['Trace'],
        station('Source', traced(R_TO_SOURCE),
                [htpy.p['Where it was found: a stakeholder, a document or a standard.']]),
        station('Parent', traced(R_TO_PARENT),
                [htpy.p['The need or requirement it helps to meet.']]),
        station('Rationale', _paragraphs(str(node.get('rationale', ''))),
                [htpy.p['Why it is needed.']]),
        station('Statement', [_anatomy(list_part)],
                [htpy.p['In the SOPHIST MASTER form{condition}.'.format(
                     condition = ', with ' + MAP_CONDITION[kind] if kind in MAP_CONDITION
                                 else '')],
                 htpy.p['‘{word}’ is {meaning}.'.format(
                     word = obligation, meaning = MAP_OBLIGATION.get(obligation, ''))]],
                css = 'statement'),
        station('Subject', [htpy.p[_link(graph, id_subject), ' ',
                                   htpy.span(class_ = 'gloss')[
                                       _prose(graph.map_item[id_subject].brief)]
                                   if id_subject in graph.map_item else None]
                            for id_subject in list_subject],
                list_note),
        station('Verification',
                [htpy.p[htpy.span(class_ = 'run-in')[
                            str(node.get('verification_method', '')).capitalize()], ' ',
                        _prose(str(node.get('verification_approach', '')))]]
                if node.get('verification_method') else [],
                [htpy.p['How it is to be shown to be met.']])]


# -----------------------------------------------------------------------------
def _anatomy(list_part: list) -> typing.Any:
    """
    Return the statement of a requirement with each part over the name
    of the slot it fills, a part that names an item linked to its page.

    """

    list_span = []
    for (index, part) in enumerate(list_part):
        text = part.text[0].upper() + part.text[1:] if index == 0 else part.text
        if index == len(list_part) - 1:
            text += '.'
        words = htpy.a(href = _href(part.id_item))[text] if part.id_item else text
        list_span.append(htpy.span(class_ = 'part part-' + part.slot)[
                             htpy.span(class_ = 'words')[words],
                             htpy.span(class_ = 'slot')[part.slot]])
        list_span.append(' ')

    return htpy.p(class_ = 'anatomy')[list_span[:-1]]


# -----------------------------------------------------------------------------
def _questions(list_question: list) -> typing.Any:
    """
    Return the questions raised of a requirement, under the three
    transformations SOPHIST reads for.

    """

    return htpy.section(class_ = 'questions')[
        htpy.h2['Questions for review'],
        [_block([htpy.ul[[htpy.li[question.text] for question in list_question
                          if question.category == category]]
                 if any(question.category == category for question in list_question)
                 else htpy.p(class_ = 'gap')['None raised.']],
                [htpy.p[htpy.span(class_ = 'label')[name]], htpy.p[gloss]])
         for (category, name, gloss) in cc_public.requirement.review.LIST_CATEGORY]]


# -----------------------------------------------------------------------------
def _characteristics(list_said: list) -> typing.Any:
    """
    Return the characteristics a requirement is reviewed against, each
    with its question and what the tree says towards it.

    """

    return htpy.section(class_ = 'characteristics')[
        htpy.h2['Characteristics'],
        htpy.table(class_ = 'characteristics')[
            htpy.thead[htpy.tr[htpy.th['Characteristic'],
                               htpy.th['From the tree']]],
            htpy.tbody[[
                htpy.tr[htpy.td[htpy.span(class_ = 'run-in')[name], ' ',
                                htpy.span(class_ = 'code')[code], htpy.br, question],
                        htpy.td(class_ = 'said')[said]]
                for (code, name, question, said) in list_said]]]]


# -----------------------------------------------------------------------------
def _requirement_references(graph: Graph, item: Item) -> typing.Any:
    """
    Return the cross-references at the foot of the page of a
    requirement: its subject and process, the other requirements and
    the issues on its subject, and the items that point at it or that
    its prose names.

    """

    list_subject = item.targets(R_HAS_SUBJECT)
    list_same    = sorted({id_other for id_subject in list_subject
                           for id_other in graph.sources(R_HAS_SUBJECT, id_subject)
                           if id_other != item.id})
    list_issue   = sorted({id_other for id_subject in list_subject
                           for id_other in graph.sources(cc_public.web.argument.R_IS_ABOUT,
                                                         id_subject)
                           if id_other.startswith(cc_public.web.argument.PREFIX_ISSUE)},
                          key = graph.title)
    list_cited   = sorted({id_source
                           for ((_, id_target), list_source) in graph.map_source.items()
                           if id_target == item.id
                           for id_source in list_source})

    return _references(graph, [('Subject',          list_subject),
                               ('Process',          item.targets(R_HAS_PROCESS)),
                               ('Same subject',     list_same),
                               ('Issues on subject', list_issue),
                               ('Mentions',         graph.mentions(item.id)),
                               ('Mentioned by',     graph.mentioned_by(item.id)),
                               ('Cited by',         list_cited)])


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
            htpy.link(rel = 'stylesheet', href = PATH_STATIC + FILE_STYLE),
            htpy.script(src = PATH_STATIC + FILE_SCRIPT, defer = True)],
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
def _decision(graph: Graph, issue: Issue, decision: Item) -> typing.Any:
    """
    Return the panel of a decision under the head of the matrix: its
    brief, folded over its description if it has one, with its standing
    in the margin. The panel shows only while it is the target of the
    address, which a click on the title of the decision makes it.

    """

    block = _block([htpy.p[_prose(decision.brief)]],
                   [_stance(issue.map_stance.get(decision.id,
                                                 cc_public.web.argument.STANCE_OPEN)),
                    _id(decision.id),
                    htpy.p(class_ = 'add')[
                        _pill('+ For', ROLE_FOR, 'Add an annotation for this decision'),
                        ' ',
                        _pill('+ Against', ROLE_AGAINST,
                              'Add an annotation against this decision')]])
    if decision.description:
        block = htpy.details(class_ = 'brief')[htpy.summary[block],
                                               _description(graph, decision, decision.id)]
    return htpy.div(class_ = 'drill decision', id = decision.id)[block]


# -----------------------------------------------------------------------------
def _decision_style(list_decision: list[str]) -> typing.Any:
    """
    Return the rules that show the panel of a decision while one of its
    counts is chosen, as it shows while the decision is, and underline
    the chosen count.

    """

    list_rule = []
    for id_decision in list_decision:
        map_id = {'id':      id_decision,
                  'for':     cc_public.web.light.chain(id_decision, ROLE_FOR),
                  'against': cc_public.web.light.chain(id_decision, ROLE_AGAINST)}
        list_rule += [
            ('section.matrix:has(#{for}:target, #{against}:target) #{id} '
             '{{ display: block; }}').format(**map_id),
            ('section.matrix:has(#{for}:target) .row.head a[href=\\#{for}], '
             'section.matrix:has(#{against}:target) .row.head a[href=\\#{against}] '
             '{{ text-decoration: underline; }}').format(**map_id)]
    return htpy.style['\n'.join(list_rule)]


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
def _groups(graph: Graph) -> list[tuple[str, list[Issue]]]:
    """
    Return the issues grouped by subject, as the index lists them: each
    subject, by title, with its issues by title. An issue about no
    subject is grouped under ''.

    """

    map_group = collections.defaultdict(list)
    for issue in graph.list_issue():
        for id_subject in issue.item.targets(cc_public.web.argument.R_IS_ABOUT) or ['']:
            map_group[id_subject].append(issue)

    return [(id_subject, map_group[id_subject])
            for id_subject in sorted(map_group, key = graph.title)]


# -----------------------------------------------------------------------------
def _sequence(graph: Graph, issue: Issue) -> typing.Any:
    """
    Return the links to the issues before and after issue in the order
    of the index, with its place among them.

    """

    list_id = list(dict.fromkeys(each.item.id for (_, list_group) in _groups(graph)
                                 for each in list_group))
    return _steps(graph, list_id, issue.item.id, 'issue')


# -----------------------------------------------------------------------------
def _steps(graph: Graph, list_id: list[str], id_item: str, noun: str) -> typing.Any:
    """
    Return the links to the items before and after id_item in list_id,
    each a noun, with its place among them.

    """

    index = list_id.index(id_item)

    def step(offset: int, mark: str, label: str) -> typing.Any:
        id_other = list_id[(index + offset) % len(list_id)]
        return htpy.a(class_ = 'step', href = _href(id_other), rel = label,
                      title  = '{label} {noun}: {title}'.format(
                                   label = label.capitalize(), noun = noun,
                                   title = graph.title(id_other)))[mark]

    return htpy.nav(class_ = 'sequence')[
        step(-1, MARK_PREVIOUS, 'prev'),
        ' {place} of {count} '.format(place = index + 1, count = len(list_id)),
        step(1, MARK_NEXT, 'next')]


# -----------------------------------------------------------------------------
def _annotation(graph:         Graph,
                outline:       cc_public.web.sankey.Outline,
                drawing:       typing.Any,
                id_annotation: str,
                key:           str,
                id_concern:    str | None,
                set_path:      set[str],
                set_show:      set[str]) -> typing.Any:
    """
    Return an annotation folded to one line: its number, title and what
    it bears on. Open, it shows its brief, which opens to its
    description, which opens to the annotations that answer it, folded
    the same way. key places it in the outline, under id_concern if it
    is not an answer; set_path holds the annotations above it. It is
    opened if a key in set_show is key or lies within it, and opened
    down to its answers if one lies within it. Its own text is in the
    chains of drawing that reach key.

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
    in_concern   = key.partition(cc_public.web.sankey.DELIM_KEY)[0] in outline.list_concern
    list_lit     = drawing.css_path(key) if in_concern else []
    css          = ' '.join([CSS_MUTES, *list_lit])
    css_margin   = ' '.join([CSS_FADES, *list_lit])

    return htpy.details(class_ = 'annotation answer' if set_path else 'annotation',
                        id     = key,
                        open   = _is_within(set_show, key))[
        htpy.summary[_block(
            [htpy.p[htpy.span(class_ = 'number')[
                        '#{number}'.format(number = map_number[id_annotation])],
                    ' ',
                    htpy.span(class_ = 'run-in')[annotation.title]]],
            [htpy.ul(class_ = 'bearing')[list_bearing],
             _summary_note(graph, list_also, len(list_answer))],
            css_main   = css,
            css_margin = css_margin)],
        htpy.div(class_ = 'body')[
            _brief(graph, annotation, key,
                   [None if id_concern
                    else htpy.p(class_ = 'concerns')[_titles(graph, list_concern) or 'fact'],
                    _id(annotation.id)],
                   [_annotation(graph, outline, drawing, id_answer,
                                cc_public.web.sankey.DELIM_KEY.join((key, id_answer)),
                                None, set_path | {id_annotation}, set_show)
                    for id_answer in list_answer],
                   _is_inside(set_show, key),
                   css,
                   css_margin)]]


# -----------------------------------------------------------------------------
def _is_within(set_show: set[str], key: str) -> bool:
    """
    Return True if a key in set_show is key or lies within it.

    """

    return key in set_show or _is_inside(set_show, key)


# -----------------------------------------------------------------------------
def _is_inside(set_show: set[str], key: str) -> bool:
    """
    Return True if a key in set_show lies within key, and is not key.

    """

    return any(key_show.startswith(key + cc_public.web.sankey.DELIM_KEY)
               for key_show in set_show)


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
def _brief(graph:       Graph,
           annotation:  Item,
           key:         str,
           list_margin: list,
           list_answer: list,
           is_open:     bool,
           css_main:    str = '',
           css_margin:  str = '') -> typing.Any:
    """
    Return the brief of the annotation with list_margin beside it,
    folded over its description, which is folded in turn over
    list_answer, the annotations that answer it. A level with nothing
    under it does not fold. The controls that answer the annotation
    come after its last level of prose, before its answers, so they
    show only when it is fully open. is_open opens every level. css_main
    classes the text of the brief and the description, and css_margin
    their margins.

    """

    block = _block([htpy.p[_prose(annotation.brief)]], list_margin,
                   css_main   = css_main,
                   css_margin = css_margin)
    add   = _add_answer(annotation.id)
    if annotation.description:
        under = [_description(graph, annotation, key, css_main, css_margin), add]
        if list_answer:
            under = htpy.details(class_ = 'description', open = is_open)[
                htpy.summary[under[0]], add, htpy.div(class_ = 'answers')[list_answer]]
    elif list_answer:
        under = [add, htpy.div(class_ = 'answers')[list_answer]]
    else:
        return [block, add]
    return htpy.details(class_ = 'brief', open = is_open)[htpy.summary[block], under]


# -----------------------------------------------------------------------------
def _description(graph:      Graph,
                 annotation: Item,
                 key:        str,
                 css_main:   str = '',
                 css_margin: str = '') -> typing.Any:
    """
    Return the description of the annotation as prose with its sources
    numbered in the margin beside it. key makes the ids of the notes
    unique on the page; css_main classes the prose and css_margin the
    sources.

    """

    (list_prose, list_note) = cc_public.web.description.description(graph,
                                                                    annotation.description,
                                                                    key)
    return _block([htpy.p(class_ = 'description')[list_prose]],
                  [htpy.ol(class_ = 'sources')[list_note] if list_note else None],
                  class_     = 'description',
                  css_main   = css_main,
                  css_margin = css_margin)


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
def _references(graph:   Graph,
                list_row: list[tuple[str, list[str]]],
                is_open:  bool = False) -> typing.Any:
    """
    Return the cross-references at the foot of a page, folded unless
    is_open: a row for each label in list_row that has items, each item
    a link.

    """

    list_row = [(label, list_id) for (label, list_id) in list_row if list_id]
    count    = len({id_item for (_, list_id) in list_row for id_item in list_id})

    return htpy.footer(class_ = 'bookend')[htpy.details(open = is_open)[
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
    issue, the requirement page for a requirement, the item page
    otherwise.

    """

    if id_item.startswith(cc_public.web.argument.PREFIX_ISSUE):
        return PATH_ISSUE + id_item
    if id_item.startswith(cc_public.requirement.compose.PREFIX_REQUIREMENT):
        return PATH_REQUIREMENT + id_item
    return PATH_ITEM + id_item


# -----------------------------------------------------------------------------
def _block(list_main:   list,
           list_margin: list,
           css_main:    str = '',
           css_margin:  str = '',
           **map_attribute: str) -> typing.Any:
    """
    Return a block of the page: list_main in the text column, with the
    classes css_main as well, and list_margin beside it in the margin,
    with the classes css_margin.

    """

    css = 'block ' + map_attribute.pop('class_', '')
    return htpy.div(class_ = css.strip(), **map_attribute)[
        htpy.div(class_ = ' '.join(['main', css_main]).strip())[list_main],
        htpy.aside(class_ = ' '.join(['margin', css_margin]).strip())[list_margin]]


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
