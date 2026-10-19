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
relation:               []

...
"""


import http
import urllib.parse

import cc_public.edit.edit
import cc_public.web.argument
import cc_public.web.request
import cc_public.web.server


ID_ISSUE         = 'iss_cross_item_checks_engine'
ID_UPHELD        = 'dec_cross_item_checks_in_clingo'
ID_REJECTED      = 'dec_cross_item_checks_in_souffle'
ID_DETERMINATION = 'det_cross_item_checks_engine'
ID_OPEN          = 'iss_tooling_language'
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
    assert cc_public.web.request.slug('dec_', 'Tooling in Go, for now!') == 'dec_tooling_in_go_for_now'
    assert len(cc_public.web.request.slug('ann_', 'word ' * 30)) <= 4 + 48


def test_a_decision_answers_its_issue(tree):
    assert _operations(tree, kind = 'decision', target = ID_OPEN,
                       title = 'Tooling in Go', brief = 'Write it in Go.') == [
        {'new':   'dec_tooling_in_go',
         'field': {'title': 'Tooling in Go', 'brief': 'Write it in Go.'},
         'link':  [['r_answers', ID_OPEN]]}]


def test_an_argument_bears_on_its_decision_and_argues_for_its_concerns(tree):
    [operation] = _operations(tree, kind = 'argument', target = ID_UPHELD, role = 'against',
                              title = 'A', brief = 'B', id = 'ann_x',
                              concern = ['concern_cost', 'concern_simplicity'])
    assert operation['new'] == 'ann_x'
    assert operation['link'] == [['r_is_about', ID_ISSUE],
                                 ['r_challenges', ID_UPHELD],
                                 ['r_argues_for_concern', 'concern_cost'],
                                 ['r_argues_for_concern', 'concern_simplicity']]


def test_an_answer_bears_on_its_annotation_and_argues_for_no_concern(tree):
    [operation] = _operations(tree, kind = 'answer', target = ID_ANNOTATION, role = 'for',
                              title = 'A', brief = 'B', concern = 'concern_cost')
    assert operation['link'] == [['r_is_about', ID_ISSUE], ['r_supports', ID_ANNOTATION]]


def test_to_uphold_changes_the_one_determination_of_the_issue(tree):
    assert _operations(tree, kind = 'determine', target = ID_REJECTED, role = 'uphold',
                       reason = 'Because.') == [
        {'set':    [ID_DETERMINATION, 'brief', 'Because.']},
        {'unlink': [ID_DETERMINATION, 'r_rejects', ID_REJECTED]},
        {'link':   [ID_DETERMINATION, 'r_upholds', ID_REJECTED]}]


def test_to_reject_an_open_issue_makes_its_determination(tree):
    graph = cc_public.web.argument.Graph(tree)
    [id_decision, *_] = [decision.id for decision in graph.issue(ID_OPEN).list_decision]
    assert _operations(tree, kind = 'determine', target = id_decision, role = 'reject',
                       reason = 'Because.') == [
        {'new':   'det_tooling_language',
         'field': {'title': graph.title(ID_OPEN), 'brief': 'Because.'},
         'link':  [['r_rejects', id_decision]]}]


def test_a_form_holds_the_fields_of_its_kind(tree):
    query = cc_public.web.request.query('argument', ID_UPHELD, 'for')
    (status, _, body) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert status == http.HTTPStatus.OK
    for name in ('title', 'brief', 'description', 'id', 'concern'):
        assert 'name="{name}"'.format(name = name).encode() in body
    assert body.index(b'value="concern_maintainability"') < body.index(b'value="concern_privacy"')

    query = cc_public.web.request.query('determine', ID_UPHELD, 'reject')
    (_, _, body) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert b'name="reason"' in body and b'name="title"' not in body


def test_a_form_for_what_it_cannot_act_on_is_refused(tree):
    query = cc_public.web.request.query('argument', ID_OPEN, 'for')
    (status, _, _) = cc_public.web.server.respond(tree, '/edit?' + query)
    assert status == http.HTTPStatus.BAD_REQUEST


def test_a_form_from_another_site_is_refused(tree):
    for (host, origin) in ((HOST, 'http://example.com'), ('example.com', None)):
        (status, _, _, _) = cc_public.web.server.submit(tree, host, origin, b'kind=decision')
        assert status == http.HTTPStatus.FORBIDDEN


def test_a_decision_sent_is_written_in_its_issue(tree):
    (status, _, _, location) = _submit(tree, 'http://' + HOST, kind = 'decision',
                                       target = ID_OPEN, title = 'Tooling in Go',
                                       brief = 'Write the tooling in Go.')
    assert status == http.HTTPStatus.SEE_OTHER
    assert location == '/issue/{id}?to=dec_tooling_in_go#dec_tooling_in_go'.format(id = ID_OPEN)
    issue = cc_public.web.argument.Graph(tree).issue(ID_OPEN)
    assert 'dec_tooling_in_go' in [decision.id for decision in issue.list_decision]


def test_an_argument_without_a_concern_is_refused_and_writes_nothing(tree):
    before = cc_public.edit.edit.Tree(tree).map_original.keys()
    (status, _, body, location) = _submit(tree, kind = 'argument', target = ID_UPHELD,
                                          role = 'for', title = 'A', brief = 'B.')
    assert status == http.HTTPStatus.UNPROCESSABLE_ENTITY and location is None
    assert b'argument_without_concern' in body and b'value="A"' in body
    assert cc_public.edit.edit.Tree(tree).map_original.keys() == before


def test_an_uphold_sent_changes_the_determination_in_place(tree):
    (status, _, _, _) = _submit(tree, kind = 'determine', target = ID_REJECTED,
                                role = 'uphold', reason = 'Both, for now.')
    assert status == http.HTTPStatus.SEE_OTHER
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    assert [item.id for item in issue.list_determination] == [ID_DETERMINATION]
    assert issue.map_stance[ID_REJECTED] == cc_public.web.argument.STANCE_UPHELD
    assert issue.map_stance[ID_UPHELD] == cc_public.web.argument.STANCE_UPHELD
    assert issue.list_determination[0].brief.strip() == 'Both, for now.'


def test_a_form_says_what_to_write_and_what_each_field_is_for(tree):
    for (kind, target, role) in (('decision', ID_OPEN, ''), ('argument', ID_UPHELD, 'for'),
                                 ('answer', ID_ANNOTATION, 'against'),
                                 ('determine', ID_UPHELD, 'uphold')):
        query = cc_public.web.request.query(kind, target, role)
        text  = cc_public.web.server.respond(tree, '/edit?' + query)[2].decode()
        for line in cc_public.web.request.MAP_LEAD[kind]:
            assert line in text
        assert '<section class="edit-form">' in text
    assert cc_public.web.request.hint('argument', 'title') != cc_public.web.request.hint(
                                                                'decision', 'title')
    assert cc_public.web.request.hint('answer', 'brief') == 'One or two sentences.'
