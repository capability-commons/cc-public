"""
---

id_self:                pym_cc_public.web.request
guid_self:              pym_3a05e3dbeb864c4988a5d99599e6234d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Edit requests from the review pages
brief:                  |
                        Turn a form of the review pages into the
                        operations of a batch, as cctool batch takes
                        them.
description:            |
                        A request is what a form sends: its kind, the
                        item it acts on, the role it takes, and the
                        fields typed into it. There are four kinds. An
                        option is offered for a decision. An argument
                        is an annotation for or against an option,
                        which speaks for one or more concerns. An
                        answer is an annotation that supports or
                        challenges another, and speaks for none. A
                        ruling upholds or rejects an option, with a
                        reason.

                        operations returns the batch for a request. An
                        decision has at most one ruling, so to uphold
                        or reject an option changes the one the
                        decision has, or makes it if there is none:
                        the reason becomes its brief, and the option
                        is upheld or rejected in place of what it was
                        before. Other options keep their standing. A
                        new item takes its id from its title unless
                        one is given.

                        Each form tells the reviewer what it wants, as
                        a brief tells an agent: MAP_LEAD holds what to
                        write for each kind, and MAP_HINT what each
                        field is for. address returns the decision
                        page to show once a request is made, naming
                        the item to show in its query as well as its
                        fragment, since a page that sends a form by
                        script is not told the fragment.
edge:                   []

...
"""


import dataclasses
import re
import urllib.parse

import cc_public.web.argument


KIND_OPTION       = 'option'
KIND_ARGUMENT     = 'argument'
KIND_ANSWER       = 'answer'
KIND_RULE         = 'rule'
TUPLE_KIND        = (KIND_OPTION, KIND_ARGUMENT, KIND_ANSWER, KIND_RULE)

ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
ROLE_UPHOLD       = 'uphold'
ROLE_REJECT       = 'reject'
MAP_ROLE          = {KIND_OPTION:  ('',),
                     KIND_ARGUMENT:  (ROLE_FOR, ROLE_AGAINST),
                     KIND_ANSWER:    (ROLE_FOR, ROLE_AGAINST),
                     KIND_RULE:      (ROLE_UPHOLD, ROLE_REJECT)}

KEY_KIND          = 'kind'
KEY_TARGET        = 'target'
KEY_ROLE          = 'role'
KEY_AT            = 'at'
KEY_ID            = 'id'
KEY_TITLE         = 'title'
KEY_BRIEF         = 'brief'
KEY_DESCRIPTION   = 'description'
KEY_REASON        = 'reason'
KEY_CONCERN       = 'concern'
TUPLE_KEY_TEXT    = (KEY_ID, KEY_TITLE, KEY_BRIEF, KEY_DESCRIPTION, KEY_REASON)

PREFIX_DECISION   = cc_public.web.argument.PREFIX_DECISION
PREFIX_OPTION     = cc_public.web.argument.PREFIX_OPTION
PREFIX_ANNOTATION = cc_public.web.argument.PREFIX_ANNOTATION
PREFIX_RULING     = 'ruling_'
PREFIX_CONCERN    = 'concern_'

RELATION_IS_OPTION_FOR      = cc_public.web.argument.RELATION_IS_OPTION_FOR
RELATION_IS_ABOUT           = cc_public.web.argument.RELATION_IS_ABOUT
RELATION_SUPPORTS           = cc_public.web.argument.RELATION_SUPPORTS
RELATION_CHALLENGES         = cc_public.web.argument.RELATION_CHALLENGES
RELATION_UPHOLDS            = cc_public.web.argument.RELATION_UPHOLDS
RELATION_REJECTS            = cc_public.web.argument.RELATION_REJECTS
RELATION_SPEAKS_FOR_CONCERN = cc_public.web.argument.RELATION_SPEAKS_FOR_CONCERN
MAP_RELATION                = {ROLE_FOR:     RELATION_SUPPORTS,
                               ROLE_AGAINST: RELATION_CHALLENGES,
                               ROLE_UPHOLD:  RELATION_UPHOLDS,
                               ROLE_REJECT:  RELATION_REJECTS}

# An id made from a title keeps whole words, up to this many
# characters after its prefix.
#
LENGTH_SLUG       = 48

DELIM_KEY         = '/'
KEY_SHOW          = 'show'
KEY_TO            = 'to'

# What to write in the form of each kind, as a short list above its
# fields, so that the reviewer writes what the argument needs.
#
MAP_LEAD          = {
    KIND_OPTION:  ('State the choice, so that it can be upheld or rejected without reading '
                     'anything else.',
                     'Say how it differs from the options already here.'),
    KIND_ARGUMENT:  ('Make one assertion that one person could check.',
                     'Tick the concern it speaks for: the one it would weigh for in a ruling.',
                     'Say where it comes from in the description: a file and line, a commit, '
                     'an engineering document, or your own judgment.'),
    KIND_ANSWER:    ('Say what in the annotation is wrong, missing or out of date, and how '
                     'you know.',
                     'An answer settles a fact, so it speaks for no concern.',
                     'If what you write is a rule or a commitment, it may belong in an option '
                     'instead.'),
    KIND_RULE:      ('Say why this option is better than its rivals, not only why it is '
                     'good.',
                     'Name the challenge you found strongest, and say why it does not change '
                     'the ruling.',
                     'Name the concerns that weighed most for this subject.',
                     'Write two or three sentences.')}

# What each field of a form is for, by kind and field, or by field
# alone where every kind uses it alike.
#
MAP_HINT          = {
    (KIND_OPTION, KEY_TITLE):  'A short name for the choice.',
    (KIND_OPTION, KEY_BRIEF):  'The choice itself, in one or two sentences.',
    (KIND_ARGUMENT, KEY_TITLE):  'A short phrase that states the claim.',
    (KIND_ANSWER,   KEY_TITLE):  'A short phrase that states what you found.',
    KEY_BRIEF:                   'One or two sentences.',
    KEY_DESCRIPTION:             'Optional. Where it comes from, and what a reader needs to '
                                 'check it.',
    KEY_ID:                      'Optional. Made from the title if left empty.',
    KEY_CONCERN:                 'The drivers of the subject come first. Tick at least one.',
    KEY_REASON:                  'This becomes the brief of the ruling of the decision, '
                                 'in place of what it said before.'}

Graph             = cc_public.web.argument.Graph


# -----------------------------------------------------------------------------
class ErrorRequest(Exception):
    """
    A request that names no kind, role or target the form could have
    sent.

    """


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Request:
    """
    What a form of the review pages sends: its kind, the id of the item
    it acts on, the role it takes, the key of that item on the decision
    page, the text of each field, and the concerns ticked.

    """

    kind:         str
    target:       str
    role:         str
    at:           str
    map_text:     dict[str, str]
    list_concern: list[str]

    # -------------------------------------------------------------------------
    def text(self, key: str) -> str:
        """
        Return the text of the field key, with its lines ended by a
        newline alone and no space around it.

        """

        return self.map_text.get(key, '').replace('\r\n', '\n').strip()


# -----------------------------------------------------------------------------
def parse(text: str) -> Request:
    """
    Return the request in text, a query or a form body. Raise
    ErrorRequest if it names no kind or role a form sends.

    """

    map_value = urllib.parse.parse_qs(text, keep_blank_values = True)

    def one(key: str) -> str:
        return map_value.get(key, [''])[0]

    kind = one(KEY_KIND)
    role = one(KEY_ROLE)
    if kind not in TUPLE_KIND:
        raise ErrorRequest('No form adds a {kind!r}.'.format(kind = kind))
    if role not in MAP_ROLE[kind]:
        raise ErrorRequest('A {kind} takes no role {role!r}.'.format(kind = kind, role = role))

    return Request(kind         = kind,
                   target       = one(KEY_TARGET),
                   role         = role,
                   at           = one(KEY_AT),
                   map_text     = {key: one(key) for key in TUPLE_KEY_TEXT if key in map_value},
                   list_concern = map_value.get(KEY_CONCERN, []))


# -----------------------------------------------------------------------------
def query(kind: str, target: str, role: str = '', at: str = '') -> str:
    """
    Return the query of the address of the form of kind, acting on
    target in role, at the key at on the decision page.

    """

    list_pair = [(KEY_KIND, kind), (KEY_TARGET, target)]
    list_pair += [(key, value) for (key, value) in ((KEY_ROLE, role), (KEY_AT, at)) if value]
    return urllib.parse.urlencode(list_pair)


# -----------------------------------------------------------------------------
def decision_of(graph: Graph, request: Request) -> str:
    """
    Return the id of the decision the request adds to. Raise ErrorRequest
    if its target is not what its kind acts on.

    """

    item = graph.map_item.get(request.target)
    if item is None:
        raise ErrorRequest('The tree holds no item {id}.'.format(id = request.target))

    if request.kind == KIND_OPTION:
        list_decision = [request.target] if request.target.startswith(PREFIX_DECISION) else []
    elif request.kind == KIND_ANSWER:
        list_decision = [id_decision for id_decision in item.targets(RELATION_IS_ABOUT)
                      if request.target.startswith(PREFIX_ANNOTATION)
                      and id_decision.startswith(PREFIX_DECISION)]
    else:
        list_decision = [id_decision for id_decision in item.targets(RELATION_IS_OPTION_FOR)
                      if request.target.startswith(PREFIX_OPTION)]

    if not list_decision:
        raise ErrorRequest('A {kind} cannot be added to {id}.'.format(kind = request.kind,
                                                                     id   = request.target))
    return list_decision[0]


# -----------------------------------------------------------------------------
def ruling(graph: Graph, id_decision: str) -> cc_public.web.argument.Item | None:
    """
    Return the one ruling of the decision id_decision, or None if it
    has none.

    """

    decision = graph.decision(id_decision)
    if decision is None or not decision.list_ruling:
        return None
    return decision.list_ruling[0]


# -----------------------------------------------------------------------------
def id_new(graph: Graph, request: Request) -> str:
    """
    Return the id of the item the request makes: the id typed into it,
    or one made from its title, or that of the ruling it makes or
    changes.

    """

    if request.kind == KIND_RULE:
        id_decision = decision_of(graph, request)
        existing    = ruling(graph, id_decision)
        if existing is not None:
            return existing.id
        return PREFIX_RULING + id_decision.removeprefix(PREFIX_DECISION)

    prefix = PREFIX_OPTION if request.kind == KIND_OPTION else PREFIX_ANNOTATION
    return request.text(KEY_ID) or slug(prefix, request.text(KEY_TITLE))


# -----------------------------------------------------------------------------
def slug(prefix: str, title: str) -> str:
    """
    Return an id with prefix made from the words of title, in lower
    case, cut after a whole word to at most LENGTH_SLUG characters.

    """

    list_word = re.findall(r'[a-z0-9]+', title.lower())
    text      = ''
    for word in list_word:
        if text and len(text) + 1 + len(word) > LENGTH_SLUG:
            break
        text = '_'.join((text, word)) if text else word
    return prefix + text


# -----------------------------------------------------------------------------
def operations(graph: Graph, request: Request) -> list:
    """
    Return the operations of the batch that makes the request on the
    tree of graph.

    """

    id_decision = decision_of(graph, request)
    id_item     = id_new(graph, request)

    if request.kind == KIND_RULE:
        return _rule(graph, request, id_decision, id_item)

    map_field = {key: request.text(key) for key in (KEY_TITLE, KEY_BRIEF, KEY_DESCRIPTION)
                 if request.text(key)}

    if request.kind == KIND_OPTION:
        list_link = [[RELATION_IS_OPTION_FOR, id_decision]]
    else:
        list_link = [[RELATION_IS_ABOUT, id_decision],
                     [MAP_RELATION[request.role], request.target]]
    if request.kind == KIND_ARGUMENT:
        list_link += [[RELATION_SPEAKS_FOR_CONCERN, id_concern]
                      for id_concern in request.list_concern]

    return [{'new': id_item, 'field': map_field, 'link': list_link}]


# -----------------------------------------------------------------------------
def _rule(graph:       Graph,
          request:     Request,
          id_decision: str,
          id_item:     str) -> list:
    """
    Return the operations that uphold or reject the option of request
    in the ruling id_item of the decision id_decision, with the reason
    of request as its brief. The ruling is made if the decision has
    none.

    """

    id_relation = MAP_RELATION[request.role]
    id_other    = RELATION_REJECTS if id_relation == RELATION_UPHOLDS else RELATION_UPHOLDS
    reason      = request.text(KEY_REASON)
    existing    = ruling(graph, id_decision)

    if existing is None:
        map_field = {KEY_TITLE: graph.title(id_decision)}
        if reason:
            map_field[KEY_BRIEF] = reason
        return [{'new': id_item, 'field': map_field, 'link': [[id_relation, request.target]]}]

    list_operation = []
    if reason:
        list_operation.append({'set': [id_item, KEY_BRIEF, reason]})
    if request.target in existing.targets(id_other):
        list_operation.append({'unlink': [id_item, id_other, request.target]})
    if request.target not in existing.targets(id_relation):
        list_operation.append({'link': [id_item, id_relation, request.target]})
    return list_operation


# -----------------------------------------------------------------------------
def address(graph: Graph, request: Request, id_item: str) -> str:
    """
    Return the address of the decision page to show once the request is
    made, at the item it made or changed.

    """

    path = '/decision/' + decision_of(graph, request)

    if request.kind == KIND_OPTION:
        list_pair = [(KEY_TO, id_item)]
    elif request.kind == KIND_RULE:
        list_pair = [(KEY_TO, request.target)]
    elif request.kind == KIND_ARGUMENT and request.list_concern:
        key       = DELIM_KEY.join((request.list_concern[0], id_item))
        list_pair = [(KEY_SHOW, key), (KEY_TO, key)]
    elif request.kind == KIND_ANSWER and request.at:
        key       = DELIM_KEY.join((request.at, id_item))
        list_pair = [(KEY_SHOW, key), (KEY_TO, key)]
    else:
        return path

    return '{path}?{query}#{to}'.format(path  = path,
                                        query = urllib.parse.urlencode(list_pair),
                                        to    = list_pair[-1][1])


# -----------------------------------------------------------------------------
def hint(kind: str, key: str) -> str:
    """
    Return what the field key of the form of kind is for, or '' if
    nothing need be said.

    """

    return MAP_HINT.get((kind, key), MAP_HINT.get(key, ''))


# -----------------------------------------------------------------------------
def concerns(graph: Graph, id_decision: str) -> tuple[list[str], list[str]]:
    """
    Return the concerns an argument on the decision id_decision may speak for:
    the drivers of its subject, and every other concern.

    """

    decision   = graph.decision(id_decision)
    list_drive = list(decision.list_driver) if decision is not None else []
    list_other = sorted(id_item for id_item in graph.map_item
                        if id_item.startswith(PREFIX_CONCERN) and id_item not in list_drive)
    return (list_drive, list_other)
