"""
---

id_self:                pym_cc_public.web._test.test_web
guid_self:              pym_8849e56e907444ad898ae14b428b9118
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review page tests
brief:                  |
                        Tests of the reading of issues and of the
                        review pages.
description:            |
                        Each test reads a copy of the repository,
                        whose one settled issue is
                        iss_cross_item_checks_engine, and checks the
                        argument gathered or the page served.
relation:               []

...
"""


import http
import urllib.parse

import cc_public.web.argument
import cc_public.web.sankey
import cc_public.web.server


ID_ISSUE         = 'iss_cross_item_checks_engine'
ID_UPHELD        = 'dec_cross_item_checks_in_clingo'
ID_REJECTED      = 'dec_cross_item_checks_in_souffle'
ID_DETERMINATION = 'det_cross_item_checks_engine'


def test_issue_gathers_its_decisions_and_determination(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    assert ID_UPHELD in [decision.id for decision in issue.list_decision]
    assert [determination.id for determination in issue.list_determination] == [ID_DETERMINATION]
    assert issue.map_stance[ID_UPHELD] == cc_public.web.argument.STANCE_UPHELD
    assert issue.map_stance[ID_REJECTED] == cc_public.web.argument.STANCE_REJECTED
    assert not issue.is_open()


def test_issue_gathers_only_annotations_about_it(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    assert issue.list_annotation
    for annotation in issue.list_annotation:
        assert ID_ISSUE in annotation.targets(cc_public.web.argument.R_IS_ABOUT)


def test_issue_lists_the_drivers_of_its_subject(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    assert 'concern_maintainability' in issue.list_driver
    assert issue.unspoken() == []


def test_a_new_determination_supersedes_the_old(tree):
    graph = cc_public.web.argument.Graph(tree)
    old   = graph.map_item[ID_DETERMINATION]
    graph.map_item['det_again'] = cc_public.web.argument.Item(
                                      id          = 'det_again',
                                      title       = 'Again',
                                      brief       = '',
                                      description = '',
                                      map_edge    = {'r_upholds':    [ID_REJECTED],
                                                     'r_rejects':    [ID_UPHELD],
                                                     'r_supersedes': [old.id]})
    graph.map_source[('r_upholds', ID_REJECTED)].append('det_again')
    issue = graph.issue(ID_ISSUE)
    assert [determination.id for determination in issue.current()] == ['det_again']
    assert issue.map_stance[ID_REJECTED] == cc_public.web.argument.STANCE_UPHELD


def test_issue_is_none_for_an_id_that_is_not_an_issue(tree):
    graph = cc_public.web.argument.Graph(tree)
    assert graph.issue(ID_UPHELD) is None
    assert graph.issue('iss_no_such_issue') is None


def test_index_links_every_issue(tree):
    (status, type_content, body) = cc_public.web.server.respond(tree, '/')
    assert status == http.HTTPStatus.OK
    assert type_content.startswith('text/html')
    assert '/issue/{id}'.format(id = ID_ISSUE).encode() in body


def test_issue_page_shows_each_annotation(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    (status, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    assert status == http.HTTPStatus.OK
    for annotation in issue.list_annotation:
        assert '<code>{id}</code>'.format(id = annotation.id).encode() in body


def test_issue_page_escapes_prose(tree):
    path = tree / '_data' / 'issue' / ID_ISSUE / (ID_ISSUE + '.yaml')
    path.write_text(path.read_text().replace('one item?', '<b>one</b> item?'))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    assert b'&lt;b&gt;one&lt;/b&gt; item?' in body


def test_unknown_issue_is_not_found(tree):
    (status, _, body) = cc_public.web.server.respond(tree, '/issue/iss_no_such_issue')
    assert status == http.HTTPStatus.NOT_FOUND
    assert b'iss_no_such_issue' in body


def test_static_serves_the_style_sheet(tree):
    (status, type_content, body) = cc_public.web.server.respond(tree, '/static/review.css')
    assert status == http.HTTPStatus.OK
    assert type_content == 'text/css'
    assert b'@font-face' in body


def test_static_refuses_a_path_out_of_its_directory(tree):
    (status, _, _) = cc_public.web.server.respond(tree, '/static/../server.py')
    assert status == http.HTTPStatus.NOT_FOUND


def test_units_count_each_annotation_concern_and_decision(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    count = sum(len(annotation.targets('r_argues_for_concern'))
                * len([id_target
                       for id_relation in ('r_supports', 'r_challenges')
                       for id_target in annotation.targets(id_relation)
                       if id_target.startswith('dec_')])
                for annotation in issue.list_annotation)
    assert len(cc_public.web.sankey.units(issue)) == count > 0


def test_decisions_are_ordered_from_most_supported(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    list_unit = cc_public.web.sankey.units(issue)
    list_lean = [cc_public.web.sankey.lean([unit for unit in list_unit
                                             if unit.decision == decision.id])
                 for decision in cc_public.web.sankey.ordered_decisions(issue)]
    assert list_lean == sorted(list_lean)


def test_map_opens_concerns_and_closes_annotations_by_default(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    unit  = cc_public.web.sankey.units(issue)[0]
    title = cc_public.web.argument.Graph(tree).title(unit.annotation)
    path  = '/issue/' + ID_ISSUE
    (_, _, opened) = cc_public.web.server.respond(tree, path)
    query = '&'.join('toggle=' + other.concern for other in cc_public.web.sankey.units(issue)
                     if other.annotation == unit.annotation)
    (_, _, closed) = cc_public.web.server.respond(tree, path + '?' + query)
    assert title.encode() in opened.split(b'</svg>')[0]
    assert title.encode() not in closed.split(b'</svg>')[0]
    assert '?toggle={key}'.format(key = unit.concern).encode() in opened


def test_closing_a_concern_closes_what_is_open_within_it(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    unit  = cc_public.web.sankey.units(issue)[0]
    inner = unit.concern + '/' + unit.annotation
    path  = '/issue/{id}?toggle={i}'.format(id = ID_ISSUE, i = inner)
    (status, _, body) = cc_public.web.server.respond(tree, path)
    assert status == http.HTTPStatus.OK
    assert '?toggle={key}"'.format(key = unit.concern).encode() in body
    assert cc_public.web.sankey.parse_toggle('toggle=a&toggle=a%2Fb') == {'a', 'a/b'}


def test_numbers_follow_the_diagram_from_the_top(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    list_first = []
    for id_concern in outline.list_concern:
        for id_annotation in outline.map_annotation[id_concern]:
            if id_annotation not in list_first:
                list_first.append(id_annotation)
    list_number = [outline.map_number[id_annotation] for id_annotation in list_first]
    assert list_number == sorted(list_number)
    assert list_number[0] == 1
    assert sorted(outline.map_number.values()) == list(range(1, len(outline.map_number) + 1))


def test_an_annotation_sits_under_each_of_its_concerns(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    for id_concern in outline.list_concern:
        for id_annotation in outline.map_annotation[id_concern]:
            assert 'id="{c}/{a}"'.format(c = id_concern, a = id_annotation).encode() in body


def test_an_annotation_title_in_the_map_opens_it_in_the_list(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    id_concern    = outline.list_concern[0]
    id_annotation = outline.map_annotation[id_concern][0]
    key           = id_concern + '/' + id_annotation
    path          = '/issue/' + ID_ISSUE
    (_, _, body)  = cc_public.web.server.respond(tree, path)
    assert '?show={q}#{k}"'.format(q = urllib.parse.quote(key, safe = ''),
                                   k = key).encode() in body
    assert b' open' not in body.split(b'</svg>')[1]
    (_, _, shown) = cc_public.web.server.respond(
        tree, path + '?show=' + urllib.parse.quote(key, safe = ''))
    assert 'id="{k}" open'.format(k = key).encode() in shown
