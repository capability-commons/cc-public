"""
---

id_self:                pym_cc_public.web._test.test_request
guid_self:              pym_f0145815c01549f4acf4af5a608d4b97
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Edit request tests
brief:                  |
                        Tests of the forms of the review pages and the
                        batches they make.
description:            |
                        Each test reads a copy of the repository. Most
                        check the operations a form makes; a few send
                        a form to the server, which checks the whole
                        tree, and see what it writes.
edge:                   []

...
"""


import http
import urllib.parse

import cc_public.edit.edit
import cc_public.web.argument
import cc_public.web.request
import cc_public.web.server


ID_DECISION      = 'dec_cross_item_checks_engine'
ID_UPHELD        = 'opt_cross_item_checks_in_clingo'
ID_REJECTED      = 'opt_cross_item_checks_in_souffle'
ID_RULING        = 'ruling_cross_item_checks_engine'
ID_OPEN          = 'dec_tooling_language'
ID_ANNOTATION    = 'ann_clingo_is_slower_at_this_size'
HOST             = '127.0.0.1:8100'


# -----------------------------------------------------------------------------
def _request(**map_value: str | list[str]) -> cc_public.web.request.Request:
    return cc_public.web.request.parse(urllib.parse.urlencode(map_value, doseq = True))


# -----------------------------------------------------------------------------
def _operations(tree, **map_value: str | list[str]) -> list:
    return cc_public.web.request.operations(cc_public.web.argument.Graph(tree),
                                            _request(**map_value))


# -----------------------------------------------------------------------------
def _submit(tree, origin: str | None = None, **map_value: str | list[str]):
    body = urllib.parse.urlencode(map_value, doseq = True).encode()
    return cc_public.web.server.submit(tree, HOST, origin, body)


# -----------------------------------------------------------------------------
def test_an_id_is_made_from_the_title_in_whole_words():
    assert cc_public.web.request.slug('opt_', 'Tooling in Go, for now!') == 'opt_tooling_in_go_for_now'
    assert len(cc_public.web.request.slug('ann_', 'word ' * 30)) <= 4 + 48


def test_an_option_is_for_its_decision(tree):
    assert _operations(tree, kind = 'option', target = ID_OPEN,
                       title = 'Tooling in Go', brief = 'Write it in Go.') == [
        {'new':   'opt_tooling_in_go',
         'field': {'title': 'Tooling in Go', 'brief': 'Write it in Go.'},
         'link':  [['relation_is_option_for', ID_OPEN]]}]


def test_an_argument_bears_on_its_option_and_speaks_for_its_concerns(tree):
    [operation] = _operations(tree, kind = 'argument', target = ID_UPHELD, role = 'against',
                              title = 'A', brief = 'B', id = 'ann_x',
                              concern = ['concern_cost', 'concern_simplicity'])
    assert operation['new'] == 'ann_x'
    assert operation['link'] == [['relation_is_about', ID_DECISION],
                                 ['relation_challenges', ID_UPHELD],
                                 ['relation_speaks_for_concern', 'concern_cost'],
                                 ['relation_speaks_for_concern', 'concern_simplicity']]


def test_a_reply_bears_on_its_annotation_and_speaks_for_no_concern(tree):
    [operation] = _operations(tree, kind = 'reply', target = ID_ANNOTATION, role = 'for',
                              title = 'A', brief = 'B', concern = 'concern_cost')
    assert operation['link'] == [['relation_is_about', ID_DECISION], ['relation_supports', ID_ANNOTATION]]


def test_to_uphold_changes_the_one_ruling_of_the_decision(tree):
    assert _operations(tree, kind = 'rule', target = ID_REJECTED, role = 'uphold',
                       reason = 'Because.') == [
        {'set':    [ID_RULING, 'brief', 'Because.']},
        {'unlink': [ID_RULING, 'relation_rejects', ID_REJECTED]},
        {'link':   [ID_RULING, 'relation_upholds', ID_REJECTED]}]


def test_to_reject_an_open_decision_makes_its_ruling(tree):
    graph = cc_public.web.argument.Graph(tree)
    [id_option, *_] = [option.id for option in graph.decision(ID_OPEN).list_option]
    assert _operations(tree, kind = 'rule', target = id_option, role = 'reject',
                       reason = 'Because.') == [
        {'new':   'ruling_tooling_language',
         'field': {'title': graph.title(ID_OPEN), 'brief': 'Because.'},
         'link':  [['relation_rejects', id_option]]}]


def test_a_form_holds_the_fields_of_its_kind(tree):
    query = cc_public.web.request.query('argument', ID_UPHELD, 'for')
    (status, _, body) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert status == http.HTTPStatus.OK
    for name in ('title', 'brief', 'description', 'id', 'concern'):
        assert 'name="{name}"'.format(name = name).encode() in body
    assert body.index(b'value="concern_maintainability"') < body.index(b'value="concern_privacy"')

    query = cc_public.web.request.query('rule', ID_UPHELD, 'reject')
    (_, _, body) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert b'name="reason"' in body and b'name="title"' not in body


def test_a_form_for_what_it_cannot_act_on_is_refused(tree):
    query = cc_public.web.request.query('argument', ID_OPEN, 'for')
    (status, _, _) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert status == http.HTTPStatus.BAD_REQUEST


def test_a_form_from_another_site_is_refused(tree):
    for (host, origin) in ((HOST, 'http://example.com'), ('example.com', None)):
        (status, _, _, _) = cc_public.web.server.submit(tree, host, origin, b'kind=option')
        assert status == http.HTTPStatus.FORBIDDEN


def test_an_option_sent_is_written_in_its_decision(tree):
    (status, _, _, location) = _submit(tree, 'http://' + HOST, kind = 'option',
                                       target = ID_OPEN, title = 'Tooling in Go',
                                       brief = 'Write the tooling in Go.')
    assert status == http.HTTPStatus.SEE_OTHER
    assert location == '/decision/{id}?to=opt_tooling_in_go#opt_tooling_in_go'.format(id = ID_OPEN)
    decision = cc_public.web.argument.Graph(tree).decision(ID_OPEN)
    assert 'opt_tooling_in_go' in [option.id for option in decision.list_option]


def test_an_argument_without_a_concern_is_refused_and_writes_nothing(tree):
    before = cc_public.edit.edit.Tree(tree).map_original.keys()
    (status, _, body, location) = _submit(tree, kind = 'argument', target = ID_UPHELD,
                                          role = 'for', title = 'A', brief = 'B.')
    assert status == http.HTTPStatus.UNPROCESSABLE_ENTITY and location is None
    assert b'argument_without_concern' in body and b'value="A"' in body
    assert cc_public.edit.edit.Tree(tree).map_original.keys() == before


def test_an_uphold_sent_changes_the_ruling_in_place(tree):
    (status, _, _, _) = _submit(tree, kind = 'rule', target = ID_REJECTED,
                                role = 'uphold', reason = 'Both, for now.')
    assert status == http.HTTPStatus.SEE_OTHER
    decision = cc_public.web.argument.Graph(tree).decision(ID_DECISION)
    assert [item.id for item in decision.list_ruling] == [ID_RULING]
    assert decision.map_standing[ID_REJECTED] == cc_public.web.argument.STANDING_UPHELD
    assert decision.map_standing[ID_UPHELD] == cc_public.web.argument.STANDING_UPHELD
    assert decision.list_ruling[0].brief.strip() == 'Both, for now.'


def test_a_form_says_what_to_write_and_what_each_field_is_for(tree):
    for (kind, target, role) in (('option', ID_OPEN, ''), ('argument', ID_UPHELD, 'for'),
                                 ('reply', ID_ANNOTATION, 'against'),
                                 ('rule', ID_UPHELD, 'uphold')):
        query = cc_public.web.request.query(kind, target, role)
        text  = cc_public.web.server.respond(tree, '/edit?' + query)[2].decode()
        for line in cc_public.web.request.MAP_LEAD[kind]:
            assert line in text
        assert '<section class="edit-form">' in text
    assert cc_public.web.request.hint('argument', 'title') != cc_public.web.request.hint(
                                                                'option', 'title')
    assert cc_public.web.request.hint('reply', 'brief') == 'One or two sentences.'
