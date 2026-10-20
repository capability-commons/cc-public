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
                        Render the index of every type, the lists and
                        pages it leads to, the decision list, the page
                        of a decision, the requirement list, the page
                        of a requirement, the list of interface
                        control documents and the page of one as HTML.
description:            |
                        The index lists every type, grouped as
                        pym_cc_public.web.catalogue groups them, with
                        how many items each has. Each type leads to
                        the list of its items, which a few words
                        filter, or to a fuller list of its own for
                        decisions, requirements and interface control
                        documents. The subjects page lists the logical
                        components, and the page of each gathers the
                        items about it by type. A search box in the
                        masthead of every page finds items by the
                        words of their id, title or brief.

                        The decision list folds each decision to its
                        title and standing, grouped by subject under
                        the concerns that drive it, or in another
                        order. A decision opens to its question and
                        the options that answer it, each with its mark
                        and how much argument is for and against it. A
                        filter keeps and opens the decisions it finds.
                        The page of a decision opens with its decision
                        matrix: a column for each option and a row for
                        each concern, in the order of the Sankey
                        diagram of pym_cc_public.web.sankey. Options
                        are read from most supported to most opposed.
                        Each concern row opens to the annotations that
                        argue for it, numbered as the diagram numbers
                        them, an annotation that argues for several
                        concerns under each. An annotation folds to
                        its title, which opens to its brief, which
                        opens to its description, which opens to the
                        annotations that answer it. Opened parts set
                        their text in the text column and their notes
                        in the margin. The options, the diagram and
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

                        The list of interface control documents gives
                        each with its version, the forms of its
                        surface, and how many of its members code
                        realizes. The page of an interface control
                        document opens with its contract, read by
                        pym_cc_public.web.contract: a row for each
                        member and a column for each part of a
                        signature, marking whether the code agrees
                        with what the member states. Each row opens to
                        the member, its parameters, and what it
                        returns. A dataflow step follows as a drawing
                        of pym_cc_public.web.step and a table of its
                        ports, and artifacts as a block each; then
                        each part of the semantics of the surface,
                        those it leaves unstated drawn hollow.

                        The pills of the page of a decision lead to
                        the forms that add to its argument or settle
                        it, which edit renders: an option, an
                        annotation for or against an option, an answer
                        to an annotation, and the upholding or
                        rejecting of an option with a reason. Uphold
                        waits, greyed, while a driver of the decision
                        is unargued.
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
import cc_public.web.catalogue
import cc_public.web.contract
import cc_public.web.description
import cc_public.web.light
import cc_public.web.network
import cc_public.web.request
import cc_public.web.restriction
import cc_public.web.sankey
import cc_public.web.step


TITLE_SITE        = 'Capability Commons'
PATH_HOME         = '/'
PATH_DECISIONS    = '/decisions'
PATH_REQUIREMENTS = '/requirements'
PATH_INTERFACES   = '/interfaces'
PATH_SUBJECTS     = '/subjects'
PATH_SUBJECT      = '/subject/'
PATH_TYPE         = '/type/'
PATH_SEARCH       = '/search'
LIST_INDEX        = (('Index',    PATH_HOME),
                     ('Subjects', PATH_SUBJECTS))
KEY_QUERY         = 'q'
KEY_CONCEPT       = 'id_concept'

# The types whose items have a list of their own, richer than the list
# of a type page, which the index leads to instead.
#
MAP_TYPE_LIST     = {'t_decision':                      PATH_DECISIONS,
                     't_requirement':                PATH_REQUIREMENTS,
                     't_interface_control_document': PATH_INTERFACES}
PATH_STATIC       = '/static/'
PATH_DECISION     = '/decision/'
PATH_REQUIREMENT  = '/requirement/'
PATH_INTERFACE    = '/interface/'
PATH_ITEM         = '/item/'
PATH_EDIT         = '/edit'
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
R_SUPERSEDES      = 'r_supersedes'
COLUMN_REALIZED   = cc_public.web.contract.COLUMN_REALIZED
COLUMN_RETURNS    = cc_public.web.contract.COLUMN_RETURNS
AGREES            = cc_public.web.contract.AGREES

# How the mark of each verdict of the contract reads.
#
MAP_VERDICT       = {cc_public.web.contract.AGREES:     'Agrees with the code',
                     cc_public.web.contract.DIFFERS:    'Differs from the code',
                     cc_public.web.contract.UNSTATED:   'Not stated, so not compared',
                     cc_public.web.contract.UNREALIZED: 'No code realizes it'}

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

# How the decision list shows its decisions and the orders it can take, the
# first of each the default.
#
KEY_LAYOUT        = 'show'
KEY_SORT          = 'sort'
LAYOUT_FOLDED     = 'folded'
LAYOUT_OPEN       = 'open'
LAYOUT_COUNTS     = 'counts'
LIST_LAYOUT       = [LAYOUT_FOLDED, LAYOUT_OPEN, LAYOUT_COUNTS]
MAP_LAYOUT_NAME   = {LAYOUT_FOLDED: 'Titles',
                     LAYOUT_OPEN:   'Questions and answers',
                     LAYOUT_COUNTS: 'Before'}
SORT_SUBJECT      = 'subject'
SORT_STANDING     = 'standing'
SORT_SIZE         = 'size'
SORT_TITLE        = 'title'
LIST_SORT         = [SORT_SUBJECT, SORT_STANDING, SORT_SIZE, SORT_TITLE]
MAP_SORT_NAME     = {SORT_SUBJECT:  'Subject',
                     SORT_STANDING: 'Standing',
                     SORT_SIZE:     'Most argued',
                     SORT_TITLE:    'Title'}
STANCE_UPHELD     = cc_public.web.argument.STANCE_UPHELD
STANCE_REJECTED   = cc_public.web.argument.STANCE_REJECTED
STANCE_OPEN       = cc_public.web.argument.STANCE_OPEN
MAP_STANCE_MARK   = {STANCE_UPHELD:   '✓',
                     STANCE_REJECTED: '✗',
                     STANCE_OPEN:     '○'}
STANDING_OPEN     = 'open'
STANDING_NARROWED = 'narrowed'
STANDING_SETTLED  = 'settled'
LIST_STANDING     = [STANDING_OPEN, STANDING_NARROWED, STANDING_SETTLED]
MAP_STANDING_STANCE = {STANDING_OPEN:     STANCE_OPEN,
                       STANDING_NARROWED: STANCE_OPEN,
                       STANDING_SETTLED:  STANCE_UPHELD}
MAP_SORT_KEY      = {
    SORT_STANDING: lambda summary: (LIST_STANDING.index(summary.standing),
                                    summary.decision.item.title),
    SORT_SIZE:     lambda summary: (-summary.size(), summary.decision.item.title),
    SORT_TITLE:    lambda summary: summary.decision.item.title}
R_IS_DRIVEN_BY    = 'r_is_driven_by'

KIND_OPTION       = cc_public.web.request.KIND_OPTION
KIND_ARGUMENT     = cc_public.web.request.KIND_ARGUMENT
KIND_ANSWER       = cc_public.web.request.KIND_ANSWER
KIND_DETERMINE    = cc_public.web.request.KIND_DETERMINE
ROLE_UPHOLD       = cc_public.web.request.ROLE_UPHOLD
ROLE_REJECT       = cc_public.web.request.ROLE_REJECT
KEY_KIND          = cc_public.web.request.KEY_KIND
KEY_TARGET        = cc_public.web.request.KEY_TARGET
KEY_ROLE          = cc_public.web.request.KEY_ROLE
KEY_AT            = cc_public.web.request.KEY_AT
KEY_ID            = cc_public.web.request.KEY_ID
KEY_TITLE         = cc_public.web.request.KEY_TITLE
KEY_BRIEF         = cc_public.web.request.KEY_BRIEF
KEY_DESCRIPTION   = cc_public.web.request.KEY_DESCRIPTION
KEY_REASON        = cc_public.web.request.KEY_REASON
KEY_CONCERN       = cc_public.web.request.KEY_CONCERN

# The heading of the form of each kind and role.
#
MAP_HEADING       = {(KIND_OPTION,  ''):           'Add an option',
                     (KIND_ARGUMENT,  ROLE_FOR):     'Add an annotation for',
                     (KIND_ARGUMENT,  ROLE_AGAINST): 'Add an annotation against',
                     (KIND_ANSWER,    ROLE_FOR):     'Support',
                     (KIND_ANSWER,    ROLE_AGAINST): 'Challenge',
                     (KIND_DETERMINE, ROLE_UPHOLD):  'Uphold',
                     (KIND_DETERMINE, ROLE_REJECT):  'Reject'}

Graph             = cc_public.web.argument.Graph
Decision          = cc_public.web.argument.Decision
Item              = cc_public.web.argument.Item
Contract          = cc_public.web.contract.Contract
Member            = cc_public.web.contract.Member
Parameter         = cc_public.web.contract.Parameter
Surface           = cc_public.web.contract.Surface
Facts             = cc_public.web.contract.Facts
Request           = cc_public.web.request.Request


# -----------------------------------------------------------------------------
def home(graph: Graph) -> str:
    """
    Return the index of every item: each type, in the groups of the
    catalogue, with how many items it has and what it is, leading to
    the list of its items.

    """

    catalogue = cc_public.web.catalogue.Catalogue(graph)
    list_type = [id_type for (_, list_group) in catalogue.groups() for id_type in list_group]

    def row(id_type: str) -> typing.Any:
        count = len(catalogue.items(id_type))
        return htpy.tr(class_ = None if count else 'empty')[
            htpy.td[htpy.a(href = _type_href(id_type))[_type_name(graph, id_type)],
                    htpy.span(class_ = 'statement')[_prose(_type_brief(graph, id_type))]],
            htpy.td(class_ = 'number')[str(count)]]

    return _page('Index',
                 [[htpy.section[
                       htpy.h2[name],
                       htpy.table(class_ = 'catalogue')[
                           htpy.thead[htpy.tr[htpy.th['Type'],
                                              htpy.th(class_ = 'number')['Items']]],
                           htpy.tbody[[row(id_type) for id_type in list_group]]]]
                   for (name, list_group) in catalogue.groups()]],
                 [htpy.h1['Index'],
                  htpy.p(class_ = 'subtitle')[
                      '{count} items of {types} types'.format(
                          count = sum(len(catalogue.items(id_type)) for id_type in list_type),
                          types = len(list_type))]])


# -----------------------------------------------------------------------------
def type_list(graph: Graph, id_type: str, text: str = '') -> str | None:
    """
    Return the list of the items of the type id_type, those whose words
    hold text if it is given, or None if the tree has no such type.

    """

    if not id_type.startswith(cc_public.web.catalogue.PREFIX_TYPE) \
            or id_type not in graph.map_item:
        return None

    catalogue = cc_public.web.catalogue.Catalogue(graph)
    list_item = catalogue.items(id_type)
    if text:
        set_found = set(catalogue.search(text))
        list_item = [id_item for id_item in list_item if id_item in set_found]

    list_other = []
    if id_type in MAP_TYPE_LIST:
        list_other = [htpy.p['A fuller list is ',
                             htpy.a(href = MAP_TYPE_LIST[id_type])['on its own page'], '.']]

    return _page(_type_name(graph, id_type),
                 [list_other,
                  _search_form(text, PATH_TYPE + id_type, 'Filter'),
                  _item_table(graph, list_item)],
                 [htpy.h1[_type_name(graph, id_type)],
                  htpy.p(class_ = 'subtitle')[_prose(_type_brief(graph, id_type))]],
                 [htpy.table(class_ = 'facts')[htpy.tbody[
                     htpy.tr[htpy.th(scope = 'row')['Items'],
                             htpy.td[str(len(catalogue.items(id_type)))]],
                     htpy.tr[htpy.th(scope = 'row')['Prefix'],
                             htpy.td[htpy.code[str(graph.map_item[id_type].node.get(
                                 cc_public.web.catalogue.KEY_PREFIX, ''))]]],
                     htpy.tr[htpy.th(scope = 'row')['Defined'],
                             htpy.td[htpy.a(href = PATH_ITEM + id_type)[id_type]]]]]])


# -----------------------------------------------------------------------------
def subjects(graph: Graph) -> str:
    """
    Return the list of the subjects, the logical components, each with
    the concerns that drive it and how many items are about it.

    """

    catalogue = cc_public.web.catalogue.Catalogue(graph)

    def row(id_subject: str) -> typing.Any:
        subject = graph.map_item[id_subject]
        return htpy.tr[
            htpy.td[htpy.a(href = PATH_SUBJECT + id_subject)[subject.title or id_subject],
                    htpy.span(class_ = 'statement')[_prose(subject.brief)]],
            htpy.td[_titles(graph, subject.targets(cc_public.web.argument.R_IS_DRIVEN_BY))],
            htpy.td(class_ = 'number')[
                str(sum(len(list_item) for (_, list_item) in catalogue.about(id_subject)))]]

    return _page('Subjects',
                 [htpy.table(class_ = 'catalogue subjects')[
                      htpy.thead[htpy.tr[htpy.th['Subject'],
                                         htpy.th['Driving concerns'],
                                         htpy.th(class_ = 'number')['Items']]],
                      htpy.tbody[[row(id_subject) for id_subject in catalogue.subjects()]]]],
                 [htpy.h1['Subjects'],
                  htpy.p(class_ = 'subtitle')[
                      'The logical components, and what is about each.']])


# -----------------------------------------------------------------------------
def subject(graph: Graph, id_subject: str) -> str | None:
    """
    Return the page of the subject id_subject: the items about it,
    gathered by type, with the concerns that drive it beside its head,
    or None if the tree has no such subject.

    """

    catalogue = cc_public.web.catalogue.Catalogue(graph)
    if id_subject not in catalogue.subjects():
        return None

    item = graph.map_item[id_subject]

    def listed(id_type: str, list_id: list[str]) -> typing.Any:
        if id_type == 't_decision':
            return _decision_table(graph, [graph.decision(id_item) for id_item in list_id])
        if id_type == 't_requirement':
            return _requirement_table(graph, [graph.map_item[id_item] for id_item in list_id])
        return _item_table(graph, list_id)

    return _page(item.title or id_subject,
                 [[htpy.section[htpy.h2[_type_name(graph, id_type)], listed(id_type, list_id)]
                   for (id_type, list_id) in catalogue.about(id_subject)]
                  or htpy.p['Nothing is about this subject yet.']],
                 [htpy.h1[item.title or id_subject],
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                 [htpy.table(class_ = 'facts')[htpy.tbody[
                     htpy.tr[htpy.th(scope = 'row')['Concerns'],
                             htpy.td[[htpy.span(class_ = 'line')[graph.title(id_concern)]
                                      for id_concern in item.targets(
                                          cc_public.web.argument.R_IS_DRIVEN_BY)]]],
                     htpy.tr[htpy.th(scope = 'row')['Id'],
                             htpy.td[htpy.a(href = PATH_ITEM + id_subject)[id_subject]]]]]])


# -----------------------------------------------------------------------------
def search(graph: Graph, text: str) -> str:
    """
    Return the items whose words hold text, with the type of each, those
    that match by id or title first.

    """

    catalogue = cc_public.web.catalogue.Catalogue(graph)
    list_item = catalogue.search(text)

    if not text.strip():
        subtitle = 'Type words from an id, a title or a brief.'
    elif not list_item:
        subtitle = 'No item holds those words.'
    elif len(list_item) >= cc_public.web.catalogue.COUNT_FOUND:
        subtitle = 'The first {count} items that hold those words.'.format(count = len(list_item))
    else:
        subtitle = '{count} item{s} hold{verb} those words.'.format(
                       count = len(list_item),
                       s     = '' if len(list_item) == 1 else 's',
                       verb  = 's' if len(list_item) == 1 else '')

    return _page('Search',
                 [_item_table(graph, list_item, catalogue) if list_item else None],
                 [htpy.h1['Search'],
                  htpy.p(class_ = 'subtitle')[subtitle]],
                 text_search = text)


# -----------------------------------------------------------------------------
def _item_table(graph:     Graph,
                list_id:   list[str],
                catalogue: cc_public.web.catalogue.Catalogue | None = None) -> typing.Any:
    """
    Return a table of the items list_id: each with its brief under its
    title and its id and file under that, and its type beside it if
    catalogue is given.

    """

    def row(id_item: str) -> typing.Any:
        item = graph.map_item[id_item]
        return htpy.tr[
            htpy.td[htpy.a(href = _href(id_item))[item.title or id_item],
                    htpy.span(class_ = 'statement')[_prose(item.brief)],
                    htpy.span(class_ = 'where')[htpy.code[id_item],
                                                [htpy.span(class_ = 'bar')['|'], item.file]
                                                if item.file else None]],
            htpy.td[_type_name(graph, catalogue.type_of(id_item))] if catalogue else None]

    return htpy.table(class_ = 'catalogue items')[
        htpy.thead[htpy.tr[htpy.th['Item'],
                           htpy.th['Type'] if catalogue else None]],
        htpy.tbody[[row(id_item) for id_item in list_id]]]


# -----------------------------------------------------------------------------
def _search_form(text:   str,
                 action: str = PATH_SEARCH,
                 label:  str = 'Search',
                 css:    str = 'search') -> typing.Any:
    """
    Return the form that finds items by their words, sent to action,
    holding text, with label on its button and the classes css. The
    box in the masthead is too narrow to say what to type.

    """

    placeholder = '' if 'masthead' in css else 'Words from an id, a title or a brief'

    return htpy.form(class_ = css, method = 'get', action = action)[
        htpy.input(type        = 'search',
                   name        = KEY_QUERY,
                   value       = text,
                   placeholder = placeholder,
                   aria_label  = label),
        ' ',
        htpy.button(type = 'submit', class_ = 'plain')[label]]


# -----------------------------------------------------------------------------
def _type_href(id_type: str) -> str:
    """
    Return the address of the list of the items of the type id_type.

    """

    return MAP_TYPE_LIST.get(id_type, PATH_TYPE + id_type)


# -----------------------------------------------------------------------------
def _type_brief(graph: Graph, id_type: str) -> str:
    """
    Return what the items of the type id_type are: the brief of the
    concept the type names, or else the brief of the type.

    """

    item       = graph.map_item[id_type]
    id_concept = str(item.node.get(KEY_CONCEPT, ''))
    if id_concept in graph.map_item and graph.map_item[id_concept].brief:
        return graph.map_item[id_concept].brief
    return item.brief


# -----------------------------------------------------------------------------
def _type_name(graph: Graph, id_type: str) -> str:
    """
    Return the name of the type id_type, its title without the word
    type, or Item if id_type is ''.

    """

    if not id_type:
        return 'Item'
    return graph.title(id_type).removesuffix(' type') or id_type


# -----------------------------------------------------------------------------
def decisions(graph: Graph, query: str = '') -> str:
    """
    Return the page that lists every decision, laid out, sorted and
    filtered as query asks.

    Each decision folds to a line of its title and standing, which opens
    to its question and the options that answer it; a filter opens
    the decisions it finds. The layouts are
    prototypes to compare: every decision folded, every decision open, and
    the table of counts the page had before.

    """

    map_query     = urllib.parse.parse_qs(query)
    layout        = _choice(map_query, KEY_LAYOUT, LIST_LAYOUT)
    sort          = _choice(map_query, KEY_SORT, LIST_SORT)
    text          = map_query.get(KEY_QUERY, [''])[0]
    list_decision = graph.list_decision()
    count_open    = sum(1 for decision in list_decision if decision.is_open())
    list_found    = [Summary(graph, decision) for decision in list_decision
                  if _holds(decision, text)]

    def render(list_summary: list[Summary]) -> typing.Any:
        if layout == LAYOUT_COUNTS:
            return _decision_table(graph, [summary.decision for summary in list_summary])
        return _decision_answers(list_summary,
                              show_subject = sort != SORT_SUBJECT,
                              is_open      = layout == LAYOUT_OPEN or bool(text))

    if sort == SORT_SUBJECT:
        map_found = {summary.decision.item.id: summary for summary in list_found}
        list_body = [htpy.section[
                         htpy.h2[graph.title(id_subject) if id_subject else 'No subject',
                                 htpy.span(class_ = 'drivers')[
                                     _drivers(graph, id_subject)]],
                         render([map_found[decision.item.id] for decision in list_group
                                 if decision.item.id in map_found])]
                     for (id_subject, list_group) in _groups(graph)
                     if any(decision.item.id in map_found for decision in list_group)]
    else:
        list_body = [render(sorted(list_found, key = MAP_SORT_KEY[sort]))]

    return _page('Decisions',
                 [_decision_controls(layout, sort, text),
                  list_body],
                 [htpy.h1['Decisions'],
                  htpy.p(class_ = 'subtitle')[
                      '{count} decisions, {open} open'.format(count = len(list_decision),
                                                          open  = count_open)]])


# -----------------------------------------------------------------------------
class Summary:
    """
    What the list of decisions says about one decision: its options, most
    supported first, the standing of each, how many units of argument
    are for and against each, and the standing of the decision.

    """

    # -------------------------------------------------------------------------
    def __init__(self, graph: Graph, decision: Decision) -> None:
        """
        Summarise decision.

        """

        self.decision      = decision
        self.list_option   = cc_public.web.sankey.ordered_options(decision)
        self.map_for       = {option.id: 0 for option in decision.list_option}
        self.map_against   = dict(self.map_for)
        for unit in cc_public.web.sankey.units(decision):
            if unit.is_for():
                self.map_for[unit.option] += 1
            else:
                self.map_against[unit.option] += 1
        self.subject = ', '.join(graph.title(id_subject) for id_subject
                                 in decision.item.targets(cc_public.web.argument.R_IS_ABOUT))
        list_stance  = list(decision.map_stance.values())
        if STANCE_UPHELD in list_stance:
            self.standing = STANDING_SETTLED
        elif STANCE_REJECTED in list_stance:
            self.standing = STANDING_NARROWED
        else:
            self.standing = STANDING_OPEN

    # -------------------------------------------------------------------------
    def stance(self, id_option: str) -> str:
        """
        Return the standing of the option id_option.

        """

        return self.decision.map_stance.get(id_option, STANCE_OPEN)

    # -------------------------------------------------------------------------
    def size(self) -> int:
        """
        Return how many units of argument the decision holds.

        """

        return sum(self.map_for.values()) + sum(self.map_against.values())


# -----------------------------------------------------------------------------
def _choice(map_query: dict, key: str, list_value: list[str]) -> str:
    """
    Return the value of key in map_query if it is one of list_value, or
    else the first of list_value.

    """

    value = map_query.get(key, [''])[0]
    return value if value in list_value else list_value[0]


# -----------------------------------------------------------------------------
def _holds(decision: Decision, text: str) -> bool:
    """
    Return True if every word of text is in the title or brief of the
    decision or of one of its options.

    """

    words = ' '.join([decision.item.title, decision.item.brief]
                     + [part for option in decision.list_option
                        for part in (option.title, option.brief)]).lower()
    return all(word in words for word in text.lower().split())


# -----------------------------------------------------------------------------
def _drivers(graph: Graph, id_subject: str) -> str:
    """
    Return the concerns that drive the subject id_subject, as the head of
    its group says them once for all its decisions.

    """

    if not id_subject or id_subject not in graph.map_item:
        return ''
    list_concern = graph.map_item[id_subject].targets(R_IS_DRIVEN_BY)
    if not list_concern:
        return ''
    return 'Driven by ' + ', '.join(graph.title(id_concern).lower()
                                    for id_concern in list_concern)


# -----------------------------------------------------------------------------
def _decision_controls(layout: str, sort: str, text: str) -> typing.Any:
    """
    Return the controls above the list: the layouts, the orders and the
    filter, each link keeping the other choices.

    """

    def href(**map_change: str) -> str:
        map_value = {KEY_LAYOUT: layout, KEY_SORT: sort, KEY_QUERY: text}
        map_value.update(map_change)
        return PATH_DECISIONS + '?' + urllib.parse.urlencode(
            {key: value for (key, value) in map_value.items() if value})

    def choices(label: str, key: str, chosen: str, map_name: dict) -> typing.Any:
        list_link = []
        for (value, name) in map_name.items():
            if list_link:
                list_link.append(htpy.span(class_ = 'bar')['|'])
            list_link.append(htpy.span(class_ = 'chosen')[name] if value == chosen
                             else htpy.a(href = href(**{key: value}))[name])
        return htpy.p[htpy.span(class_ = 'label')[label], ' ', list_link]

    return htpy.div(class_ = 'decision-controls')[
        choices('Show', KEY_LAYOUT, layout, MAP_LAYOUT_NAME),
        choices('Order', KEY_SORT, sort, MAP_SORT_NAME),
        htpy.form(class_ = 'search', method = 'get', action = PATH_DECISIONS)[
            htpy.input(type = 'hidden', name = KEY_LAYOUT, value = layout),
            htpy.input(type = 'hidden', name = KEY_SORT, value = sort),
            htpy.input(type        = 'search',
                       name        = KEY_QUERY,
                       value       = text,
                       placeholder = 'Words from a decision or its options',
                       aria_label  = 'Filter'),
            ' ',
            htpy.button(type = 'submit', class_ = 'plain')['Filter']]]


# -----------------------------------------------------------------------------
def _mark(stance: str) -> typing.Any:
    """
    Return the mark of the standing of an option: a tick if upheld, a
    cross if rejected, an open circle if open.

    """

    return htpy.span(class_ = 'mark mark-' + stance,
                     title  = stance)[MAP_STANCE_MARK[stance]]


# -----------------------------------------------------------------------------
def _standing(summary: Summary) -> typing.Any:
    """
    Return the standing of the decision, as a word in the colour of the
    standing of an option.

    """

    return htpy.span(class_ = 'stance stance-' + MAP_STANDING_STANCE[summary.standing])[
        summary.standing]


# -----------------------------------------------------------------------------
def _counts(summary: Summary, id_option: str) -> typing.Any:
    """
    Return how many units of argument are for and against id_option.

    """

    return htpy.span(class_ = 'counts')[
        htpy.span(class_ = 'for')[str(summary.map_for[id_option]), MARK_FOR], ' ',
        htpy.span(class_ = 'against')[str(summary.map_against[id_option]), MARK_AGAINST]]


# -----------------------------------------------------------------------------
def _decision_answers(list_summary: list[Summary],
                   show_subject: bool,
                   is_open:      bool) -> typing.Any:
    """
    Return the decisions of list_summary, each folded to a line of its
    title, with its standing in the margin, unless is_open. Each opens
    to its question and the options that answer it, in full: each
    option with its mark hung before it, its title run in and linked
    to the option on the page of the decision, and its counts in the
    margin. A link after the options leads to the page of the decision.

    """

    def answer(summary: Summary, option: Item) -> typing.Any:
        stance = summary.stance(option.id)
        return _block([htpy.p[_mark(stance),
                              htpy.a(class_ = 'run-in',
                                     href   = PATH_DECISION + summary.decision.item.id
                                              + '#' + option.id)[option.title],
                              ' ', _prose(option.brief)]],
                      [_counts(summary, option.id)],
                      class_ = 'answer answer-' + stance)

    def entry(summary: Summary) -> typing.Any:
        item = summary.decision.item
        return htpy.details(class_ = 'decision-entry', id = item.id, open = is_open)[
            htpy.summary[_block([htpy.span(class_ = 'title')[item.title]],
                                [_standing(summary),
                                 htpy.span(class_ = 'subject')[summary.subject]
                                 if show_subject else None])],
            _block([htpy.p(class_ = 'question')[_prose(item.brief)]], []),
            [answer(summary, option) for option in summary.list_option],
            _block([htpy.p(class_ = 'onward')[
                        htpy.a(href = PATH_DECISION + item.id)['Decision matrix'],
                        ' ', MARK_NEXT]], [])]

    return htpy.div(class_ = 'decision-answers')[[entry(summary) for summary in list_summary]]


# -----------------------------------------------------------------------------
def decision(graph:      Graph,
          decision:   Decision,
          set_toggle: set[str],
          set_show:   set[str] | None = None) -> str:
    """
    Return the page that shows a decision and the argument on it, with the
    parts of its diagram in set_toggle opened or closed, the annotation
    in set_show opened in the decision matrix. The Sankey diagram is
    shown and the graph folded away under its caption.

    """

    item         = decision.item
    outline      = cc_public.web.sankey.Outline(graph, decision)
    list_subject = [graph.title(id_subject)
                    for id_subject in item.targets(cc_public.web.argument.R_IS_ABOUT)]

    return _page(item.title,
                 [_lighting(graph, outline),
                  _matrix(graph, decision, outline, set_show or set()),
                  _determinations(graph, decision),
                  _diagram('Flow', 'sankey', True,
                           cc_public.web.sankey.figure(graph, outline, set_toggle,
                                                       set_show or set())),
                  _diagram('Tree', 'network', False,
                           cc_public.web.network.figure(graph, outline)),
                  _decision_references(graph, decision)],
                 [htpy.h1[item.title],
                  _sequence(graph, decision),
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                 [_facts(graph, decision, list_subject)])


# -----------------------------------------------------------------------------
def _lighting(graph: Graph, outline: cc_public.web.sankey.Outline) -> list:
    """
    Return the rules that light each chain of the argument in outline,
    in the matrix and in both diagrams alike, and an element that pins
    each chain whose name the page does not already hold as an id: the
    matrix holds an option, each of its roles, and each concern that
    opens to annotations.

    """

    chain    = cc_public.web.light.chain
    set_held = {chain(id_option, role) for id_option in outline.list_option
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
            decision: Decision,
            outline:  cc_public.web.sankey.Outline,
            set_show: set[str]) -> typing.Any:
    """
    Return the decision matrix of the decision: a column for each option
    and a row for each concern, in the order of the diagram, each cell
    showing a square for each unit of weight for or against the option
    for the concern. Each row opens to the annotations that argue for
    its concern; those in set_show are opened. The foot holds the total
    and the standing of each option and the controls that settle it.
    A driver no annotation argues for is marked, as a determination
    waits on it.

    """

    list_option = outline.list_option

    def row(list_label: list, list_cell: list, **map_attribute: str) -> typing.Any:
        css = 'row ' + map_attribute.pop('class_', '')
        return htpy.div(class_ = css.strip(), **map_attribute)[
            htpy.div(class_ = 'label')[list_label],
            [htpy.div(class_ = 'cell')[cell] for cell in list_cell]]

    map_option   = {option.id: option for option in decision.list_option}
    drawing      = cc_public.web.sankey.lighting(graph, outline)
    list_row     = [row([], [[htpy.a(href   = '#' + id_option,
                                     class_ = ' '.join([CSS_MUTES,
                                                        *drawing.css_option(id_option),
                                                        cc_public.web.light.show(id_option)]))[
                                  graph.title(id_option)],
                              htpy.div(class_ = 'total')[
                                  _total(id_option, outline.units(option = id_option),
                                         drawing.css_option(id_option))]]
                             for id_option in list_option]
                            + [htpy.span(class_ = 'add')[
                                   _pill('+ Option', '',
                                         'Add an option that answers this decision',
                                         _edit_href(KIND_OPTION,
                                                    decision.item.id))]],
                        class_ = 'head'),
                    _option_style(list_option),
                    [htpy.span(class_ = 'option-role',
                               id     = cc_public.web.light.chain(id_option, role))
                     for id_option in list_option
                     for role in (cc_public.web.light.ROLE_FOR, cc_public.web.light.ROLE_AGAINST)],
                    [_option(graph, decision, map_option[id_option])
                     for id_option in list_option]]

    for id_concern in outline.list_concern:
        list_annotation = outline.map_annotation[id_concern]
        list_cell       = [_cell_link(outline, drawing, id_option, id_concern)
                           for id_option in list_option]
        label           = _concern_label(graph, decision, id_concern,
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
                             [None for _ in list_option])],
            htpy.div(class_ = 'drill')[
                [_annotation(graph, outline, drawing, id_annotation, id_annotation, None, set(),
                             set_show)
                 for id_annotation in outline.list_other]]])

    list_row += [
        row(['Standing'], [_stance(decision.map_stance.get(id_option,
                                                        cc_public.web.argument.STANCE_OPEN))
                           for id_option in list_option], class_ = 'foot standing'),
        row([], [_controls(graph, decision, id_option) for id_option in list_option],
            class_ = 'foot controls')]

    return htpy.section(class_ = 'matrix ' + cc_public.web.light.CSS_REGION,
                        style  = '--options: {count}'.format(count = len(list_option)))[
        list_row]


# -----------------------------------------------------------------------------
def _concern_label(graph:      Graph,
                   decision:   Decision,
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
            if id_concern in set(decision.unspoken()) else None]


# -----------------------------------------------------------------------------
def _cell_link(outline:     cc_public.web.sankey.Outline,
               drawing:     typing.Any,
               id_option:   str,
               id_concern:  str) -> typing.Any:
    """
    Return a cell of the decision matrix, linked to the annotations
    that argue for id_concern on id_option, all opened in its row and
    the first in view.

    """

    list_unit = outline.units(option = id_option, concern = id_concern)
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
    units of weight on one option for one concern: a disc marked with
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
def _total(id_option: str, list_unit: list, list_css: list[str]) -> typing.Any:
    """
    Return the total of list_unit, the units of weight on id_option,
    in words: how many are for it and how many against, each in the
    chains of list_css. Each count lights the chains that reach the
    option with that role while it is hovered over, and shows the
    option and pins them when it is clicked.

    """

    count_for = sum(1 for unit in list_unit if unit.is_for())
    list_link = []
    for (role, count) in ((ROLE_FOR, count_for), (ROLE_AGAINST, len(list_unit) - count_for)):
        name = cc_public.web.light.chain(id_option, role)
        list_link.append(htpy.a(class_ = ' '.join([role, CSS_FADES, *list_css,
                                                   cc_public.web.light.show(name)]),
                                href   = '#' + name)[
                             '{count} {role}'.format(count = count, role = role)])
    return [list_link[0], ', ', list_link[1]]


# -----------------------------------------------------------------------------
def _controls(graph: Graph, decision: Decision, id_option: str) -> typing.Any:
    """
    Return the controls that settle the decision on id_option: uphold it
    or reject it, each in the one determination of the decision, leaving
    the other options as they stand. Uphold waits, greyed, while a
    driver of the decision is unargued, as unargued_driver would refuse it;
    reject never waits, as a rejection needs no driver argued.

    """

    kind          = KIND_DETERMINE
    list_unspoken = decision.unspoken()
    if list_unspoken:
        uphold = htpy.span(class_ = 'pill for waiting',
                           title  = 'Uphold waits until an annotation argues for {list}'.format(
                                        list = _titles(graph, list_unspoken)))['Uphold']
    else:
        uphold = _pill('Uphold', ROLE_FOR, 'Uphold this option',
                       _edit_href(kind, id_option, ROLE_UPHOLD))
    return htpy.div(class_ = 'determine')[
        uphold,
        _pill('Reject', ROLE_AGAINST, 'Reject this option',
              _edit_href(kind, id_option, ROLE_REJECT))]


# -----------------------------------------------------------------------------
def _pill(label: str, role: str, title: str, href: str) -> typing.Any:
    """
    Return a control that changes the data, as a pill that leads to its
    form at href: for or against in the colours of role, or plain if
    role is ''.

    """

    return htpy.a(class_ = ' '.join(['pill', role]).strip(), title = title, href = href)[label]


# -----------------------------------------------------------------------------
def _edit_href(kind: str, target: str, role: str = '', at: str = '') -> str:
    """
    Return the address of the form of kind that acts on target in role,
    from the key at on the decision page.

    """

    return '{path}?{query}'.format(path  = PATH_EDIT,
                                   query = cc_public.web.request.query(kind, target, role, at))


# -----------------------------------------------------------------------------
def _add_answer(id_annotation: str, key: str) -> typing.Any:
    """
    Return the controls that add an annotation answering id_annotation,
    at key on the page, in support or in challenge, set in the margin.

    """

    kind = KIND_ANSWER
    return _block([], [htpy.p(class_ = 'add')[
                           _pill('+ Support', ROLE_FOR, 'Add an annotation that supports this',
                                 _edit_href(kind, id_annotation, ROLE_FOR, key)),
                           ' ',
                           _pill('+ Challenge', ROLE_AGAINST,
                                 'Add an annotation that challenges this',
                                 _edit_href(kind, id_annotation, ROLE_AGAINST, key))]],
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

    list_decision = _decisions_of(graph, item)
    statement     = _statement(graph, item)
    list_prose    = (_paragraphs(item.brief) if statement else []) + _paragraphs(item.description)
    list_prose += [htpy.p[[_part(part) for part in sentence]]
                   for sentence in cc_public.web.restriction.sentences(graph, id_item)]
    subtitle   = statement or _prose(item.brief)

    return _page(title,
                 [_block(list_prose, []),
                  _references(graph, list_row, is_open = not item.description)],
                 [htpy.h1[title],
                  htpy.p(class_ = 'subtitle')[subtitle] if subtitle else None],
                 [htpy.table(class_ = 'facts')[htpy.tbody[
                     htpy.tr[htpy.th(scope = 'row')['Decision'],
                             htpy.td[[htpy.span(class_ = 'line')[_link(graph, id_decision)]
                                      for id_decision in list_decision]]]
                     if list_decision else None,
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
def _decisions_of(graph: Graph, item: Item) -> list[str]:
    """
    Return the decisions the argument item belongs to: those an option
    answers, an annotation is about, or a determination settles through
    its options.

    """

    list_option = (item.targets(cc_public.web.argument.R_UPHOLDS)
                     + item.targets(cc_public.web.argument.R_REJECTS))
    list_target   = (item.targets(cc_public.web.argument.R_IS_OPTION_FOR)
                     + item.targets(cc_public.web.argument.R_IS_ABOUT)
                     + [id_decision for id_option in list_option
                        if id_option in graph.map_item
                        for id_decision in graph.map_item[id_option].targets(
                                            cc_public.web.argument.R_IS_OPTION_FOR)])

    return [id_target for id_target in dict.fromkeys(list_target)
            if id_target.startswith(cc_public.web.argument.PREFIX_DECISION)]


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
    the decisions on its subject, and the items that point at it or that
    its prose names.

    """

    list_subject = item.targets(R_HAS_SUBJECT)
    list_same    = sorted({id_other for id_subject in list_subject
                           for id_other in graph.sources(R_HAS_SUBJECT, id_subject)
                           if id_other != item.id})
    list_decision   = sorted({id_other for id_subject in list_subject
                           for id_other in graph.sources(cc_public.web.argument.R_IS_ABOUT,
                                                         id_subject)
                           if id_other.startswith(cc_public.web.argument.PREFIX_DECISION)},
                          key = graph.title)
    list_cited   = sorted({id_source
                           for ((_, id_target), list_source) in graph.map_source.items()
                           if id_target == item.id
                           for id_source in list_source})

    return _references(graph, [('Subject',          list_subject),
                               ('Process',          item.targets(R_HAS_PROCESS)),
                               ('Same subject',     list_same),
                               ('Decisions on subject', list_decision),
                               ('Mentions',         graph.mentions(item.id)),
                               ('Mentioned by',     graph.mentioned_by(item.id)),
                               ('Cited by',         list_cited)])


# -----------------------------------------------------------------------------
def interfaces(graph: Graph) -> str:
    """
    Return the page that lists every interface control document, by
    title.

    """

    list_item = cc_public.web.contract.interfaces(graph)
    count     = sum(len(cc_public.web.contract.members(item.node)) for item in list_item)

    return _page('Interface control documents',
                 [htpy.h1['Interface control documents'],
                  htpy.p(class_ = 'subtitle')[
                      '{count} {noun}, {member} members'.format(
                          count  = len(list_item),
                          noun   = 'document' if len(list_item) == 1 else 'documents',
                          member = count)],
                  htpy.section[_interface_table(graph, list_item)]])


# -----------------------------------------------------------------------------
def _interface_table(graph: Graph, list_item: list[Item]) -> typing.Any:
    """
    Return a table of the interface control documents in list_item:
    each with its brief under its title, its version, the forms of its
    surface, and how many of its members code realizes.

    """

    def realized(item: Item) -> typing.Any:
        list_member = cc_public.web.contract.members(item.node)
        count       = sum(1 for id_member in list_member
                          if graph.sources(cc_public.web.contract.R_REALIZES, id_member))
        text        = '{count} of {total}'.format(count = count, total = len(list_member))
        return text if count == len(list_member) else htpy.span(class_ = 'gap')[text]

    return htpy.table(class_ = 'requirements')[
        htpy.thead[htpy.tr[htpy.th['Interface'],
                           htpy.th['Version'],
                           htpy.th['Surface'],
                           htpy.th(class_ = 'number')['Realized']]],
        htpy.tbody[[
            htpy.tr[
                htpy.td[htpy.a(href = _href(item.id))[item.title or item.id],
                        htpy.span(class_ = 'statement')[item.brief]],
                htpy.td[str(item.node.get('version_interface', ''))],
                htpy.td[_surface(item)],
                htpy.td(class_ = 'number')[realized(item)]]
            for item in list_item]]]


# -----------------------------------------------------------------------------
def _surface(item: Item) -> str:
    """
    Return the forms of the surface of an interface control document,
    each named by its language where it has one.

    """

    list_form = []
    for value in (item.node.get('surface') or {}).values():
        if not isinstance(value, dict) or not value:
            continue
        form = next(iter(value))
        body = value[form] if isinstance(value[form], dict) else {}
        name = cc_public.web.contract.MAP_FORM.get(form, (form.replace('_', ' '),))[0]
        list_form.append(str(body.get('language') or name).capitalize())
    return ', '.join(dict.fromkeys(list_form))


# -----------------------------------------------------------------------------
def interface(graph: Graph, facts: Facts, id_interface: str) -> str | None:
    """
    Return the page of an interface control document, or None if
    id_interface names none.

    The page opens with the contract: a row for each member, grouped by
    kind, and a column for each part of a signature, each cell marking
    whether the code that realizes the member agrees with what it
    states. Each row opens to the member: its signature, what it
    promises, and its parameters with what the code says of each. What
    the interface is for and the cross-references follow.

    """

    contract = cc_public.web.contract.contract(graph, facts, id_interface)
    if contract is None:
        return None

    item = contract.item
    return _page(item.title,
                 [_contract(graph, contract) if contract.members() else None,
                  [_surface_section(graph, contract, surface)
                   for surface in contract.list_surface],
                  htpy.section(class_ = 'use')[
                      _block(_paragraphs(item.description),
                             [htpy.p[htpy.span(class_ = 'label')['In use']]])],
                  _interface_references(graph, contract)],
                 [htpy.h1[item.title],
                  _steps(graph, [each.id for each in cc_public.web.contract.interfaces(graph)],
                         item.id, 'interface'),
                  htpy.p(class_ = 'subtitle')[_prose(item.brief)]],
                 [_interface_facts(contract)])


# -----------------------------------------------------------------------------
def _interface_facts(contract: Contract) -> typing.Any:
    """
    Return the table of facts that stands beside the brief of an
    interface control document: its version, its surface, its members
    and how far the code realizes and agrees with them.

    """

    def row(label: str, value: typing.Any) -> typing.Any:
        return htpy.tr[htpy.th(scope = 'row')[label], htpy.td[value]]

    list_member = contract.every_member()
    count_real  = sum(1 for member in list_member
                      if member.map_verdict.get(COLUMN_REALIZED) == AGREES)
    count_diff  = sum(1 for member in list_member
                      if cc_public.web.contract.DIFFERS in member.map_verdict.values())
    is_compared = any(member.is_function() for member in contract.members())
    native      = next((value.get('native') for value in
                        (contract.item.node.get('surface') or {}).values()
                        if isinstance(value, dict) and isinstance(value.get('native'), dict)),
                       {})
    list_stated = [htpy.span(class_ = 'line')['{key}: {stated} of {count} stated'.format(
                       key = surface.key, stated = surface.stated(),
                       count = len(surface.list_semantics))]
                   for surface in contract.list_surface]

    return htpy.table(class_ = 'facts')[htpy.tbody[
        row('Version',   str(contract.item.node.get('version_interface', ''))),
        row('Surface',   ', '.join(filter(None, [_surface(contract.item),
                                                 str(native.get('dialect', ''))]))),
        row('Members',   str(len(list_member))),
        row('Realized',  '{count} of {total}'.format(count = count_real,
                                                     total = len(list_member))),
        row('Semantics', list_stated) if list_stated else None,
        None if not is_compared else
        row('Agreement', htpy.span(class_ = 'gap')[
                             'The code differs for {count} of {total} members'.format(
                                 count = count_diff, total = len(list_member))]
                         if count_diff else 'The code agrees with what is stated')]]


# -----------------------------------------------------------------------------
def _contract(graph: Graph, contract: Contract) -> typing.Any:
    """
    Return the contract matrix of an interface control document: a
    column for each part of a signature, and a row for each member under
    the name of its group. Each row of a member opens to the member. The
    foot counts what agrees in each column.

    """

    list_column = cc_public.web.contract.LIST_COLUMN
    if not any(member.is_function() for member in contract.members()):
        list_column = list_column[:1]

    def row(list_label: list, list_cell: list, **map_attribute: str) -> typing.Any:
        css = 'row ' + map_attribute.pop('class_', '')
        return htpy.div(class_ = css.strip(), **map_attribute)[
            htpy.div(class_ = 'label')[list_label],
            [htpy.div(class_ = 'cell')[cell] for cell in list_cell]]

    list_row = [row([], [htpy.span(class_ = 'column')[label] for (_, label, _) in list_column],
                    class_ = 'head')]

    for (group, list_member) in contract.list_group:
        list_row.append(row([cc_public.web.contract.group_name(group)],
                            [None for _ in list_column], class_ = 'group'))
        for member in list_member:
            list_row.append(htpy.details(class_ = 'concern member', id = member.id)[
                htpy.summary[row([htpy.code(class_ = 'name')[member.name]],
                                 [_verdict(graph, member, column)
                                  for (column, _, _) in list_column])],
                htpy.div(class_ = 'drill')[_member(graph, member)]])

    list_row.append(row(['All'], [_tally(contract, column) for (column, _, _) in list_column],
                        class_ = 'foot'))

    return htpy.section(class_ = 'matrix contract',
                        style  = '--options: {count}'.format(count = len(list_column)))[
        list_row]


# -----------------------------------------------------------------------------
def _verdict(graph: Graph, member: Member, column: str) -> typing.Any:
    """
    Return the mark of the verdict of column on member, or nothing where
    the column does not apply to it. The mark of the realized column
    links to the code that realizes the member.

    """

    verdict = member.map_verdict.get(column)
    if verdict is None:
        return htpy.span(class_ = 'none')[MARK_NONE]

    title = MAP_VERDICT[verdict]
    if column == COLUMN_REALIZED and member.list_realizer:
        title = 'Realized by {title}, {location}'.format(
                    title = graph.title(member.list_realizer[0]), location = member.location)
        return htpy.a(class_ = 'cell', href = _href(member.list_realizer[0]), title = title)[
            htpy.span(class_ = 'verdict ' + verdict)[title]]
    if column == COLUMN_REALIZED:
        title = 'Not realized: nothing records an edge r_realizes to it'
    return htpy.span(class_ = 'verdict ' + verdict, title = title)[title]


# -----------------------------------------------------------------------------
def _tally(contract: Contract, column: str) -> str:
    """
    Return what the members of contract show in column, in words.

    """

    list_verdict = [member.map_verdict.get(column) for member in contract.members()
                    if member.map_verdict.get(column) is not None]
    if column == COLUMN_REALIZED:
        return '{count} of {total}'.format(count = list_verdict.count(AGREES),
                                           total = len(list_verdict))
    list_word = ['{count} {word}'.format(count = list_verdict.count(verdict), word = word)
                 for (verdict, word) in ((cc_public.web.contract.AGREES,     'agree'),
                                         (cc_public.web.contract.DIFFERS,    'differ'),
                                         (cc_public.web.contract.UNSTATED,   'unstated'))
                 if verdict in list_verdict]
    return ', '.join(list_word)


# -----------------------------------------------------------------------------
def _member(graph: Graph, member: Member) -> list:
    """
    Return what the row of a member opens to: its signature as stated,
    its brief and what it promises, and its parameters and what it
    returns, each beside what the code says where they differ.

    """

    node      = member.node
    list_note = [_note_line('Realized by', [htpy.span(class_ = 'line')[_link(graph, id_item)]
                                            for id_item in member.list_realizer]),
                 htpy.p(class_ = 'location')[member.location] if member.location else None,
                 _id(member.id)]
    if not member.list_realizer:
        list_note[0] = htpy.p(class_ = 'gap')['Not realized']

    list_main = [htpy.p(class_ = 'signature')[htpy.code[_signature(member)]]
                 if member.is_function() else None,
                 _paragraphs(_text(node.get('brief'))),
                 _paragraphs(_text(node.get('shape')))]

    list_block = [_block(list_main, list_note, class_ = 'member-head')]
    if _text(node.get('obligation')):
        list_block.append(_block(_paragraphs(_text(node.get('obligation'))),
                                 [htpy.p[htpy.span(class_ = 'label')['Obligation']]]))
    if member.list_parameter or member.list_extra:
        list_block.append(_block([_parameters(member)],
                                 [htpy.p[htpy.span(class_ = 'label')['Parameters']]]))
    if member.returns is not None:
        returns = node.get('returns') or {}
        list_block.append(_block(
            [htpy.p[htpy.code[_stated(member.returns,
                                      None if member.map_verdict.get(COLUMN_RETURNS)
                                      != cc_public.web.contract.DIFFERS
                                      else member.returns_code)], ' ',
                    _prose(_text(returns.get('brief')))]],
            [htpy.p[htpy.span(class_ = 'label')['Returns']]]))
    return list_block


# -----------------------------------------------------------------------------
def _parameters(member: Member) -> typing.Any:
    """
    Return the table of the parameters of a member: each with its brief
    under its name, its type, its default and its mode, a part the code
    says otherwise of marked with what the code says. A parameter the
    code takes that the member does not state ends the table.

    """

    def part(parameter: Parameter, name: str) -> typing.Any:
        stated = parameter.map_part.get(name)
        if stated is None:
            return htpy.span(class_ = 'none')[MARK_NONE]
        code = parameter.map_code.get(name, '') if parameter.differs(name) else None
        return _stated(stated, code)

    list_row = [htpy.tr[
                    htpy.td[htpy.code[_stated(parameter.name,
                                              parameter.map_code.get('name')
                                              if parameter.map_code is not None
                                              and parameter.map_code.get('name')
                                              != parameter.name else None)],
                            htpy.span(class_ = 'statement')[
                                _prose(_text(parameter.node.get('brief')))],
                            [htpy.span(class_ = 'statement obligation')[_prose(text)]
                             for text in [_text(parameter.node.get('obligation'))] if text]],
                    htpy.td[htpy.code[part(parameter, 'type')]],
                    htpy.td[htpy.code[part(parameter, 'default')]],
                    htpy.td[str(parameter.node.get('mode', '')).replace('_', ' ')]]
                for parameter in member.list_parameter]
    list_row += [htpy.tr(class_ = 'extra')[
                     htpy.td[htpy.code[name],
                             htpy.span(class_ = 'statement differs')['Taken by the code, '
                                                                     'not stated']],
                     htpy.td, htpy.td, htpy.td]
                 for name in member.list_extra]

    return htpy.table(class_ = 'parameters')[
        htpy.thead[htpy.tr[htpy.th['Parameter'], htpy.th['Type'], htpy.th['Default'],
                           htpy.th['Mode']]],
        htpy.tbody[list_row]]


# -----------------------------------------------------------------------------
def _stated(stated: str, code: str | None) -> typing.Any:
    """
    Return what a member states, and beside it what the code says if
    code is not None, as a difference.

    """

    if code is None:
        return stated
    return [htpy.span(class_ = 'stated differs')[stated],
            htpy.span(class_ = 'code-says',
                      title  = 'What the code says')[code or 'nothing']]


# -----------------------------------------------------------------------------
def _signature(member: Member) -> str:
    """
    Return the signature of a function member as python writes it, from
    what the member states.

    """

    list_part = []
    for parameter in member.list_parameter:
        text = parameter.name
        if parameter.map_part.get('variadic') == 'true':
            text = '*' + text
        if 'type' in parameter.map_part:
            text += ': ' + parameter.map_part['type']
        if 'default' in parameter.map_part:
            text += ' = ' + parameter.map_part['default']
        list_part.append(text)
    returns = ' -> ' + member.returns if member.returns is not None else ''
    return '{name}({parts}){returns}'.format(name = member.name, parts = ', '.join(list_part),
                                             returns = returns)


# -----------------------------------------------------------------------------
def _interface_references(graph: Graph, contract: Contract) -> typing.Any:
    """
    Return the cross-references at the foot of the page of an interface
    control document: the code that realizes its members, the documents
    it supersedes or that supersede it, and the items that point at it or
    that its prose names.

    """

    item         = contract.item
    list_realize = sorted({id_item for member in contract.members()
                           for id_item in member.list_realizer})
    list_cited   = sorted({id_source
                           for ((_, id_target), list_source) in graph.map_source.items()
                           if id_target == item.id
                           for id_source in list_source})

    return _references(graph, [('Realized by',   list_realize),
                               ('Supersedes',    item.targets(R_SUPERSEDES)),
                               ('Superseded by', graph.sources(R_SUPERSEDES, item.id)),
                               ('Mentions',      graph.mentions(item.id)),
                               ('Mentioned by',  graph.mentioned_by(item.id)),
                               ('Cited by',      list_cited)])


# -----------------------------------------------------------------------------
def _surface_section(graph: Graph, contract: Contract, surface: Surface) -> typing.Any:
    """
    Return the section of a surface that is not native: a dataflow step
    drawn and its ports, or its artifacts; then each part of its
    semantics.

    """

    if surface.form == cc_public.web.contract.FORM_DATAFLOW:
        list_body = [cc_public.web.step.figure(contract.item.title, surface),
                     _ports(graph, surface)]
    else:
        list_body = [_artifact(graph, member) for (_, list_member) in surface.list_group
                     for member in list_member]

    return htpy.section(class_ = 'surface ' + surface.form.replace('_', '-'),
                        id     = 'surface-' + surface.key)[
        htpy.h2[surface.label, ' ', htpy.span(class_ = 'key')[surface.key]],
        list_body,
        _semantics(surface)]


# -----------------------------------------------------------------------------
def _ports(graph: Graph, surface: Surface) -> typing.Any:
    """
    Return the table of the ports of a dataflow step, by direction:
    each with its brief under its name, the type it carries, whether a
    step may run with no value there, and the code that realizes it.

    """

    list_row = []
    for (group, list_member) in surface.list_group:
        list_row.append(htpy.tr(class_ = 'group')[
            htpy.th(colspan = '4')[cc_public.web.contract.group_name(group)]])
        list_row += [
            htpy.tr(id = 'port-' + member.id)[
                htpy.td[htpy.code[member.name],
                        htpy.span(class_ = 'statement')[_prose(_text(member.node.get('brief')))]],
                htpy.td[htpy.code[_type(member.node)]],
                htpy.td['optional' if member.node.get('optional') else ''],
                htpy.td[[htpy.span(class_ = 'line')[_link(graph, id_item)]
                         for id_item in member.list_realizer]
                        or htpy.span(class_ = 'gap')['Not realized']]]
            for member in list_member]

    return htpy.table(class_ = 'parameters ports')[
        htpy.thead[htpy.tr[htpy.th['Port'], htpy.th['Type'], htpy.th['Value'],
                           htpy.th['Realized by']]],
        htpy.tbody[list_row]]


# -----------------------------------------------------------------------------
def _artifact(graph: Graph, member: Member) -> typing.Any:
    """
    Return the block of an artifact: what one instance carries, the
    schema of its payload, how it is written down, what a reader needs
    to read it rightly, and how an instance is named; the code that
    realizes it in the margin.

    """

    node    = member.node
    payload = node.get('payload') or {}
    schema  = ' '.join(filter(None, [str(payload.get('spelling') or payload.get('declaration')
                                         or ''),
                                     'version ' + str(payload['version'])
                                     if payload.get('version') else '']))

    def part(label: str, text: str) -> typing.Any:
        return htpy.p[htpy.span(class_ = 'run-in')[label], ' ', _prose(text)] if text else None

    return _block([htpy.p[htpy.span(class_ = 'run-in artifact-name')[member.name], ' ',
                          _prose(_text(node.get('content')))],
                   part('Payload',    schema),
                   part('Encoding',   _text(node.get('encoding'))),
                   part('Convention', _text(node.get('convention'))),
                   part('Identity',   _text(node.get('identity')))],
                  [_note_line('Realized by', [htpy.span(class_ = 'line')[_link(graph, id_item)]
                                              for id_item in member.list_realizer])
                   or htpy.p(class_ = 'gap')['Not realized'],
                   _id(member.id)],
                  class_ = 'artifact')


# -----------------------------------------------------------------------------
def _semantics(surface: Surface) -> typing.Any:
    """
    Return the semantics of a surface: each part the schema names, with
    its question in the margin and what the surface states of it, or a
    hollow mark where it states nothing, since compatibility depends on
    every part.

    """

    return htpy.div(class_ = 'semantics')[
        htpy.h3['Semantics ', htpy.span(class_ = 'note')[
            '{stated} of {count} stated'.format(stated = surface.stated(),
                                                count  = len(surface.list_semantics))]],
        [_block(_paragraphs(text) or [htpy.p(class_ = 'gap')['Not stated.']],
                [htpy.p[htpy.span(class_ = 'label')[field.replace('_', ' ')]],
                 htpy.p(class_ = 'gloss')[gloss]],
                class_ = 'part' if text else 'part unstated')
         for (field, gloss, text) in surface.list_semantics]]


# -----------------------------------------------------------------------------
def _type(node: dict) -> str:
    """
    Return the spelling of the type a member carries, or empty.

    """

    value = node.get('type')
    return str(value.get('spelling', '')) if isinstance(value, dict) else ''


# -----------------------------------------------------------------------------
def _text(value: typing.Any) -> str:
    """
    Return value as text, or empty if it is not text.

    """

    return value if isinstance(value, str) else ''


# -----------------------------------------------------------------------------
def edit(graph:      Graph,
         request:    Request,
         list_added: list[str] | None = None) -> str:
    """
    Return the form that makes request: what to write, the fields its
    kind needs, each with what it is for in the margin and filled in
    with what request holds, and the press that sends it. list_added
    names the failures the request would have added when it was last
    sent, and nothing was written. The page script shows the section
    of the form over the decision page it was opened from.

    """

    id_decision = cc_public.web.request.decision_of(graph, request)
    heading     = MAP_HEADING[(request.kind, request.role)]
    if request.kind != KIND_OPTION:
        heading = '{heading} \u2018{target}\u2019'.format(heading = heading,
                                                        target  = graph.title(request.target))

    list_field = [htpy.input(type = 'hidden', name = key, value = value)
                  for (key, value) in ((KEY_KIND,   request.kind),
                                       (KEY_TARGET, request.target),
                                       (KEY_ROLE,   request.role),
                                       (KEY_AT,     request.at))
                  if value]

    def field(label: str, key: str, value: str, is_long: bool = False) -> typing.Any:
        return _field(label, key, value, is_long, cc_public.web.request.hint(request.kind, key))

    if request.kind == KIND_DETERMINE:
        existing = cc_public.web.request.determination(graph, id_decision)
        reason   = (existing.brief or '').strip() if existing is not None else ''
        list_field.append(field('Reason', KEY_REASON, request.map_text.get(KEY_REASON, reason),
                                is_long = True))
        press = 'Uphold' if request.role == ROLE_UPHOLD else 'Reject'
    else:
        list_field += [field('Title', KEY_TITLE, request.text(KEY_TITLE)),
                       field('Brief', KEY_BRIEF, request.text(KEY_BRIEF), is_long = True),
                       field('Description', KEY_DESCRIPTION, request.text(KEY_DESCRIPTION),
                             is_long = True)]
        if request.kind == KIND_ARGUMENT:
            list_field.append(_concern_choice(graph, request, id_decision))
        list_field.append(field('Id', KEY_ID, request.text(KEY_ID)))
        press = 'Add'

    role_press = (ROLE_AGAINST if request.role in (ROLE_AGAINST, ROLE_REJECT)
                  else ROLE_FOR if request.role else '')

    return _page(heading,
                 [htpy.section(class_ = 'edit-form')[
                      _refusal(list_added),
                      _block([htpy.ul(class_ = 'prompt')[
                                  [htpy.li[line]
                                   for line in cc_public.web.request.MAP_LEAD[request.kind]]]],
                             [htpy.p['What to write']],
                             class_ = 'prompt'),
                      htpy.form(class_ = 'edit', method = 'post', action = PATH_EDIT)[
                          list_field,
                          htpy.p(class_ = 'press')[
                              htpy.button(type   = 'submit',
                                          class_ = ' '.join(['pill', role_press]).strip())[
                                  press],
                              ' ',
                              htpy.a(class_ = 'cancel', href = PATH_DECISION + id_decision)[
                                  'Cancel']]]]],
                 [htpy.h1[heading],
                  htpy.p(class_ = 'subtitle')[
                      htpy.a(href = PATH_DECISION + id_decision)[graph.title(id_decision)]]])


# -----------------------------------------------------------------------------
def _field(label:   str,
           name:    str,
           value:   str,
           is_long: bool = False,
           note:    str = '') -> typing.Any:
    """
    Return a field of an edit form, named name and holding value, under
    label: a box of several lines if is_long, else one line, with note
    in the margin.

    """

    if is_long:
        control = htpy.textarea(name = name, id = 'field-' + name, rows = '4')[value]
    else:
        control = htpy.input(type = 'text', name = name, id = 'field-' + name, value = value)
    return _block([htpy.label(for_ = 'field-' + name)[label], control],
                  [htpy.p[note] if note else None],
                  class_ = 'field')


# -----------------------------------------------------------------------------
def _concern_choice(graph:    Graph,
                    request:     Request,
                    id_decision: str) -> typing.Any:
    """
    Return the boxes that choose the concerns an annotation argues for:
    the drivers of the subject of the decision id_decision first, then every
    other, with those of request ticked.

    """

    (list_drive, list_other) = cc_public.web.request.concerns(graph, id_decision)

    def box(id_concern: str) -> typing.Any:
        return htpy.label(class_ = 'concern')[
            htpy.input(type    = 'checkbox',
                       name    = KEY_CONCERN,
                       value   = id_concern,
                       checked = id_concern in request.list_concern),
            ' ', graph.title(id_concern)]

    return _block([htpy.span(class_ = 'label')['Concerns'],
                   htpy.div(class_ = 'choice')[[box(id_concern) for id_concern in list_drive]],
                   htpy.div(class_ = 'choice other')[
                       [box(id_concern) for id_concern in list_other]]],
                  [htpy.p[cc_public.web.request.hint(request.kind, KEY_CONCERN)]],
                  class_ = 'field')


# -----------------------------------------------------------------------------
def _refusal(list_added: list[str] | None) -> typing.Any:
    """
    Return what list_added says the last press would have broken, or
    None if it was not refused.

    """

    if not list_added:
        return None
    return _block([htpy.p(class_ = 'refused')[
                       'Nothing was written. The edit would have added ',
                       'this failure:' if len(list_added) == 1 else 'these failures:'],
                   htpy.ul(class_ = 'refused')[[htpy.li[htpy.code[line]]
                                                for line in list_added]]],
                  [])


# -----------------------------------------------------------------------------
def missing(id_item: str) -> str:
    """
    Return the page for a decision or item that the tree does not hold.

    """

    return _page('Not found',
                 [htpy.h1['Not found'],
                  htpy.p['The tree holds no decision ', htpy.code[id_item], '.']])


# -----------------------------------------------------------------------------
def refused(message: str) -> str:
    """
    Return the page for a request that no page of the review could have
    sent, saying why in message.

    """

    return _page('Refused',
                 [htpy.section(class_ = 'edit-form')[htpy.p(class_ = 'refused')[message]]],
                 [htpy.h1['Refused']])


# -----------------------------------------------------------------------------
def _page(title:       str,
          body:        typing.Any,
          head:        typing.Any = None,
          head_margin: typing.Any = None,
          text_search: str        = '') -> str:
    """
    Return the HTML of a page with title and body. head follows the
    name of the site, the links to the indexes and the search box,
    holding text_search, in the text column, with head_margin beside
    them in the margin, so the margin starts at the top of the page.

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
                                     for (name, href) in LIST_INDEX],
                                    _search_form(text_search, css = 'search masthead')],
                        head],
                       [head_margin],
                       class_ = 'masthead ruled' if head_margin else 'masthead'),
                body]]])


# -----------------------------------------------------------------------------
def _decision_table(graph: Graph, list_decision: list[Decision]) -> typing.Any:
    """
    Return a table of the decisions in list_decision: what each asks, how much
    argument it holds, and whether it is settled.

    """

    return htpy.table[
        htpy.thead[htpy.tr[htpy.th['Decision'],
                           htpy.th(class_ = 'number')['Options'],
                           htpy.th(class_ = 'number')['Annotations'],
                           htpy.th(class_ = 'number')['Concerns'],
                           htpy.th['Determined']]],
        htpy.tbody[[
            htpy.tr[
                htpy.td[htpy.a(href = PATH_DECISION + decision.item.id)[decision.item.title]],
                htpy.td(class_ = 'number')[str(len(decision.list_option))],
                htpy.td(class_ = 'number')[str(len(decision.list_annotation))],
                htpy.td(class_ = 'number')[
                    '{spoken} of {count}'.format(
                        spoken = len(decision.list_driver) - len(decision.unspoken()),
                        count  = len(decision.list_driver))],
                htpy.td[_settlement(graph, decision)]]
            for decision in list_decision]]]


# -----------------------------------------------------------------------------
def _settlement(graph: Graph, decision: Decision) -> typing.Any:
    """
    Return the option the decision was settled on, or a mark that it is
    open.

    """

    list_upheld = [id_option for (id_option, stance) in decision.map_stance.items()
                   if stance == cc_public.web.argument.STANCE_UPHELD]
    if not list_upheld:
        return _stance(cc_public.web.argument.STANCE_OPEN)
    return [_stance(cc_public.web.argument.STANCE_UPHELD), ' ',
            ', '.join(graph.title(id_option) for id_option in list_upheld)]


# -----------------------------------------------------------------------------
def _option(graph: Graph, decision: Decision, option: Item) -> typing.Any:
    """
    Return the panel of an option under the head of the matrix: its
    brief, folded over its description if it has one, with its standing
    in the margin. The panel shows only while it is the target of the
    address, which a click on the title of the option makes it.

    """

    block = _block([htpy.p[_prose(option.brief)]],
                   [_stance(decision.map_stance.get(option.id,
                                                 cc_public.web.argument.STANCE_OPEN)),
                    _id(option.id),
                    htpy.p(class_ = 'add')[
                        _pill('+ For', ROLE_FOR, 'Add an annotation for this option',
                              _edit_href(KIND_ARGUMENT, option.id,
                                         ROLE_FOR)),
                        ' ',
                        _pill('+ Against', ROLE_AGAINST,
                              'Add an annotation against this option',
                              _edit_href(KIND_ARGUMENT, option.id,
                                         ROLE_AGAINST))]])
    if option.description:
        block = htpy.details(class_ = 'brief')[htpy.summary[block],
                                               _description(graph, option, option.id)]
    return htpy.div(class_ = 'drill option', id = option.id)[block]


# -----------------------------------------------------------------------------
def _option_style(list_option: list[str]) -> typing.Any:
    """
    Return the rules that show the panel of an option while one of its
    counts is chosen, as it shows while the option is, and underline
    the chosen count.

    """

    list_rule = []
    for id_option in list_option:
        map_id = {'id':      id_option,
                  'for':     cc_public.web.light.chain(id_option, ROLE_FOR),
                  'against': cc_public.web.light.chain(id_option, ROLE_AGAINST)}
        list_rule += [
            ('section.matrix:has(#{for}:target, #{against}:target) #{id} '
             '{{ display: block; }}').format(**map_id),
            ('section.matrix:has(#{for}:target) .row.head a[href=\\#{for}], '
             'section.matrix:has(#{against}:target) .row.head a[href=\\#{against}] '
             '{{ text-decoration: underline; }}').format(**map_id)]
    return htpy.style['\n'.join(list_rule)]


# -----------------------------------------------------------------------------
def _determinations(graph: Graph, decision: Decision) -> typing.Any:
    """
    Return the determinations on the decision, or None if it has none.

    """

    if not decision.list_determination:
        return None

    return htpy.section[
        htpy.h2['Determination'],
        [_block([htpy.p[htpy.span(class_ = 'run-in')[determination.title], ' ',
                        _prose(determination.brief)]],
                [_note_line('Upholds', _titles(graph, determination.targets(
                                                   cc_public.web.argument.R_UPHOLDS))),
                 _note_line('Rejects', _titles(graph, determination.targets(
                                                   cc_public.web.argument.R_REJECTS))),
                 _id(determination.id)])
         for determination in decision.list_determination]]


# -----------------------------------------------------------------------------
def _groups(graph: Graph) -> list[tuple[str, list[Decision]]]:
    """
    Return the decisions grouped by subject, as the index lists them: each
    subject, by title, with its decisions by title. A decision about no
    subject is grouped under ''.

    """

    map_group = collections.defaultdict(list)
    for decision in graph.list_decision():
        for id_subject in decision.item.targets(cc_public.web.argument.R_IS_ABOUT) or ['']:
            map_group[id_subject].append(decision)

    return [(id_subject, map_group[id_subject])
            for id_subject in sorted(map_group, key = graph.title)]


# -----------------------------------------------------------------------------
def _sequence(graph: Graph, decision: Decision) -> typing.Any:
    """
    Return the links to the decisions before and after decision in the order
    of the index, with its place among them.

    """

    list_id = list(dict.fromkeys(each.item.id for (_, list_group) in _groups(graph)
                                 for each in list_group))
    return _steps(graph, list_id, decision.item.id, 'decision')


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
    add   = _add_answer(annotation.id, key)
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
def _facts(graph: Graph, decision: Decision, list_subject: list[str]) -> typing.Any:
    """
    Return the table of facts about a decision that stands beside its
    brief: its standing, its subject, the drivers of its subject and how
    much argument it holds.

    """

    def row(label: str, value: typing.Any) -> typing.Any:
        return htpy.tr[htpy.th(scope = 'row')[label], htpy.td[value]]

    set_unspoken = set(decision.unspoken())
    list_driver  = [htpy.span(class_ = 'line')[
                        htpy.s(title = 'Not argued')[graph.title(id_concern)]
                        if id_concern in set_unspoken else graph.title(id_concern)]
                    for id_concern in decision.list_driver]

    return htpy.table(class_ = 'facts')[htpy.tbody[
        row('Standing', _settlement(graph, decision)),
        row('Subject',  ', '.join(list_subject)) if list_subject else None,
        row('Concerns', list_driver) if list_driver else None,
        row('Argument', '{options} options, {annotations} annotations'.format(
                            options     = len(decision.list_option),
                            annotations = len(decision.list_annotation)))]]


# -----------------------------------------------------------------------------
def _decision_references(graph: Graph, decision: Decision) -> typing.Any:
    """
    Return the cross-references at the foot of the page of decision: its
    subject and the other decisions about it, the concerns argued, and the
    items that point at or are named by what the page shows, beyond
    the page itself.

    """

    is_about     = cc_public.web.argument.R_IS_ABOUT
    list_shown   = ([decision.item] + decision.list_option + decision.list_annotation
                   + decision.list_determination)
    set_shown    = {shown.id for shown in list_shown}
    list_subject = decision.item.targets(is_about)

    list_same    = sorted({id_other
                           for id_subject in list_subject
                           for id_other in graph.sources(is_about, id_subject)
                           if id_other.startswith(cc_public.web.argument.PREFIX_DECISION)
                           and id_other != decision.item.id})
    list_concern = sorted(decision.set_spoken, key = graph.title)
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
    Return the address of the page of id_item: the decision page for an
    decision, the requirement page for a requirement, the interface page
    for an interface control document, the subject page for a logical
    component, the list of its items for a type, and the item page
    otherwise.

    """

    if id_item.startswith(cc_public.web.argument.PREFIX_DECISION):
        return PATH_DECISION + id_item
    if id_item.startswith(cc_public.requirement.compose.PREFIX_REQUIREMENT):
        return PATH_REQUIREMENT + id_item
    if id_item.startswith(cc_public.web.contract.PREFIX_INTERFACE):
        return PATH_INTERFACE + id_item
    if id_item.startswith(cc_public.web.catalogue.PREFIX_SUBJECT):
        return PATH_SUBJECT + id_item
    if id_item.startswith(cc_public.web.catalogue.PREFIX_TYPE):
        return PATH_TYPE + id_item
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
    Return the mark of the stance of an option.

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
