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


import concurrent.futures
import http
import re
import urllib.parse

import htpy

import cc_public.web.argument
import cc_public.web.description
import cc_public.web.network
import cc_public.web.page
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


def test_matrix_has_a_column_for_each_decision_and_a_row_for_each_concern(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    head    = matrix[matrix.index('<div class="row head">'):matrix.index('<style>')]
    assert head.count('<div class="cell">') == len(outline.list_decision)
    for id_decision in outline.list_decision:
        assert 'href="#{id}"'.format(id = id_decision) in head
    assert len(re.findall(r'class="(?:row )?concern"', matrix)) == len(outline.list_concern)
    assert '--decisions: {count}'.format(count = len(outline.list_decision)) in matrix
    assert 'matrix-style' not in matrix
    assert '<h2>Decision matrix</h2>' not in text
    assert '<h2>Decisions</h2>' not in text


def test_a_decision_title_opens_its_brief_under_the_head(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text  = body.decode()
    for decision in issue.list_decision:
        panel = text[text.index('<div class="drill decision" id="{id}">'.format(id = decision.id)):]
        assert panel.index('<div class="row') > panel.index('<code>{id}</code>'.format(
                                                                id = decision.id))
        assert 'a[href=\\#{id}]'.format(id = decision.id) in text
    assert 'src="/static/review.js"' in text


def test_a_decision_shown_in_the_matrix_is_lit_in_both_diagrams(tree):
    issue = cc_public.web.argument.Graph(tree).issue(ID_ISSUE)
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text  = body.decode()
    for decision in issue.list_decision:
        shown = ':root:has(#{id}:target)'.format(id = decision.id)
        assert '{shown} .sankey svg .dims'.format(shown = shown) in text
        assert '{shown} .network svg .dims'.format(shown = shown) in text
        assert text.count('href="#{id}"'.format(id = decision.id)) >= 3
        for role in ('for', 'against'):
            alias = '{id}--{role}'.format(id = decision.id, role = role)
            assert ':root:has(#{alias}:target) .sankey svg .dims'.format(alias = alias) in text
            assert ':root:has(#{alias}:target) .network svg .dims'.format(alias = alias) in text
            assert text.count('href="#{alias}"'.format(alias = alias)) == 3


def test_matrix_text_is_in_the_chains_of_the_sankey_diagram(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    assert 'name other' not in matrix
    for id_decision in outline.list_decision:
        key = 'lit-dec-' + id_decision
        assert ':root:has(#{id}:target)) section.matrix .mutes.{key}'.format(
                   id = id_decision, key = key) in matrix
    for id_concern in outline.list_concern:
        if not outline.units(concern = id_concern):
            continue
        id_decision = outline.units(concern = id_concern)[0].decision
        assert re.search(r'<span class="name mutes [^"]*\blit-dec-{id}\b[^"]*">'.format(
                             id = id_decision), matrix)
        for id_annotation in outline.map_annotation[id_concern]:
            start = matrix.index('id="{c}/{a}"'.format(c = id_concern, a = id_annotation))
            assert re.match(r'[^>]*>\s*<summary><div class="block"><div class="main mutes [^"]*'
                            r'lit-ann-{a}\b'.format(a = id_annotation), matrix[start:])


def test_a_concern_row_opens_to_the_annotations_that_argue_for_it(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text    = body.decode()
    for id_concern in outline.list_concern:
        if not outline.map_annotation[id_concern]:
            continue
        start = text.index('<details class="concern" id="{id}">'.format(id = id_concern))
        row   = text[start:text.index('<div class="drill">', start)]
        assert '<summary><div class="row">' in row
        for id_annotation in outline.map_annotation[id_concern]:
            assert 'id="{c}/{a}"'.format(c = id_concern, a = id_annotation) in text[start:]


def test_answers_sit_under_the_description_of_what_they_answer(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text    = body.decode()
    count   = 0
    for id_concern in outline.list_concern:
        for id_annotation in outline.map_annotation[id_concern]:
            list_answer = outline.answers(id_annotation)
            if not list_answer or not graph.map_item[id_annotation].description:
                continue
            key   = id_concern + '/' + id_annotation
            start = text.index('id="{key}"'.format(key = key))
            inner = text[start:text.index('id="{key}/{a}"'.format(key = key,
                                                                  a   = list_answer[0][0]))]
            assert inner.index('<details class="brief">') \
                < inner.index('<details class="description">') \
                < inner.rindex('<div class="answers">')
            count += 1
            key_found = key
    assert count > 0
    key = key_found
    (_, _, shown) = cc_public.web.server.respond(
        tree, '/issue/{id}?show={k}/x'.format(id = ID_ISSUE, k = urllib.parse.quote(key, safe = '')))
    assert 'id="{k}" open'.format(k = key).encode() in shown
    assert b'<details class="brief" open>' in shown
    assert b'<details class="description" open>' in shown


def test_matrix_cells_show_a_marked_disc_for_each_unit_and_head_totals_in_words(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/{id}?matrix=pugh'.format(
                                                          id = ID_ISSUE))
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    list_unit = outline.list_unit
    count_for = sum(1 for unit in list_unit if unit.is_for())
    assert matrix.count('<span class="unit for">+</span>') == count_for
    assert matrix.count('<span class="unit against">−</span>') == len(list_unit) - count_for
    for id_decision in outline.list_decision:
        list_own = outline.units(decision = id_decision)
        count    = sum(1 for unit in list_own if unit.is_for())
        head     = matrix[:matrix.index('<style>')]
        assert ('<a class="for" href="#{id}--for">{f} for</a>, '
                '<a class="against" href="#{id}--against">{a} against</a>'
                .format(id = id_decision, f = count, a = len(list_own) - count)) in head
        assert 'id="{id}--for"'.format(id = id_decision) in matrix
    assert 'matrix=' not in matrix
    assert '>All<' not in matrix


def test_description_moves_sources_to_the_margin_and_keeps_other_brackets(tree):
    graph = cc_public.web.argument.Graph(tree)
    text  = ('It is so (check.py lines 3-4) and slow (a guess). ASSUMPTION: it stays so. '
             'See dec_cross_item_checks_in_clingo (https://example.org/a).')
    (list_prose, list_note) = cc_public.web.description.description(graph, text, 'k')
    prose = str(htpy.p[list_prose])
    assert [str(note) for note in list_note] == [
        '<li id="k-note-1" value="1">check.py lines 3-4</li>',
        '<li id="k-note-2" value="2"><a href="https://example.org/a">example.org/a</a></li>']
    assert 'slow (a guess).' in prose
    assert '<span class="label">assumption</span> it stays so</span>' in prose
    assert '>{title}</a>'.format(title = graph.title(ID_UPHELD)) in prose


def test_issue_page_steps_to_the_issues_before_and_after(tree):
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text = body.decode()
    assert 'rel="prev"' in text and 'rel="next"' in text
    assert ' 1 of 2 ' in text


def test_matrix_cell_opens_every_annotation_it_counts(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue(ID_ISSUE))
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    for href in re.findall(r'<a class="cell" href="([^"]+)"', body.decode().replace('&amp;', '&')):
        list_key   = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)['show']
        id_concern = list_key[0].split(cc_public.web.sankey.DELIM_KEY)[0]
        list_unit  = [unit for unit in outline.units(concern = id_concern)
                      if unit.annotation in {key.split(cc_public.web.sankey.DELIM_KEY)[1]
                                             for key in list_key}]
        assert len({unit.decision for unit in list_unit}) >= 1
        assert href.endswith('#' + list_key[0])
        (_, _, opened) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE + href.split('#')[0])
        for key in list_key:
            assert 'id="{key}" open'.format(key = key).encode() in opened


def test_an_annotation_brief_folds_over_its_description(tree):
    graph = cc_public.web.argument.Graph(tree)
    issue = graph.issue(ID_ISSUE)
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    text  = body.decode()
    list_with = [annotation for annotation in issue.list_annotation if annotation.description]
    assert list_with
    assert text.count('<details class="brief">') >= len(list_with)
    assert len(re.findall(r'<details class="brief">\s*<summary>\s*<div class="block">', text)) \
        == text.count('<details class="brief">')
    assert 'Evidence' not in text


def test_graph_decision_lights_its_chains_through_concerns(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue('iss_tooling_language'))
    body    = str(cc_public.web.network.figure(graph, outline))
    key     = 'pick-dec_tooling_in_python'
    assert 'id="{key}"'.format(key = key) in body

    def css(id_item):
        pattern = 'class="([^"]*)" id="node-{id}"'.format(id = id_item)
        return re.search(pattern, body).group(1).split()

    assert key + "--for" in css('ann_python_is_fast_enough')
    assert key + "--against" in css('ann_graphs_will_grow')
    assert key + "--for" in css('ann_cross_item_checks_run_in_clingo')
    assert key not in css('ann_types_catch_errors_early')
    assert key in css('concern_performance_efficiency')
    assert not any(css_concern.startswith(key + '-')
                   for css_concern in css('concern_performance_efficiency'))
    assert 'pick-concern_' not in body and 'port-concern_' not in body
    assert 'id="port-dec_tooling_in_python-against"' in body


def test_graph_node_lights_both_its_chains(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue('iss_tooling_language'))
    body    = str(cc_public.web.network.figure(graph, outline))
    key     = 'pick-ann_python_is_fast_enough'
    assert 'href="#{key}" id="{key}"'.format(key = key) in body

    def css(id_item):
        pattern = 'class="([^"]*)" id="node-{id}"'.format(id = id_item)
        return re.search(pattern, body).group(1).split()

    assert key + "--for" in css('ann_gate_takes_a_minute')
    assert key + "--against" in css('ann_graphs_will_grow')
    assert key + "--for" in css('ann_cross_item_checks_run_in_clingo')


def test_sankey_inks_an_answer_by_its_net_effect_on_a_decision(tree):
    graph   = cc_public.web.argument.Graph(tree)
    outline = cc_public.web.sankey.Outline(graph, graph.issue('iss_tooling_language'))
    key     = 'concern_performance_efficiency/ann_python_is_fast_enough'
    body    = str(cc_public.web.sankey.figure(
                  graph, outline, {key, key + '/ann_graphs_will_grow'}, set()))
    assert 'id="lit-dec-dec_tooling_in_python"' in body
    assert 'lit-trigger hover-lit-port-dec_tooling_in_python-for' in body

    def css(title):
        pattern = r'<text [^>]*class="([^"]*)"[^>]*>(?:(?!</text>).)*?</tspan> {title}<'
        return re.search(pattern.format(title = title), body).group(1).split()

    lit = 'lit-dec-dec_tooling_in_python'
    assert lit + '--for' in css('Python is fast enough')
    assert lit + '--against' in css('Graphs will grow large')
    assert lit + '--for' in css('Cross-item checks run in clingo')
    assert 'lit-ann-ann_python_is_fast_enough--against' in css('Graphs will grow large')


def test_item_page_names_the_issue_of_a_decision(tree):
    (_, _, body) = cc_public.web.server.respond(tree, '/item/' + ID_UPHELD)
    assert '/issue/{id}'.format(id = ID_ISSUE).encode() in body


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
    assert title.encode() in _figure(opened)
    assert title.encode() not in _figure(closed)
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


def test_issue_page_ends_with_cross_references(tree):
    (_, _, body) = cc_public.web.server.respond(tree, '/issue/' + ID_ISSUE)
    footer = body.split(b'<footer class="bookend">')[1]
    assert b'Cross-references' in footer
    assert b'/item/lc_tooling' in footer


def test_item_page_shows_edges_in_and_out(tree):
    (status, _, body) = cc_public.web.server.respond(tree, '/item/' + ID_UPHELD)
    assert status == http.HTTPStatus.OK
    assert ('/issue/' + ID_ISSUE).encode() in body
    assert ('/item/' + ID_DETERMINATION).encode() in body


def test_unknown_item_is_not_found(tree):
    (status, _, _) = cc_public.web.server.respond(tree, '/item/dec_no_such_decision')
    assert status == http.HTTPStatus.NOT_FOUND


def test_requests_at_once_are_all_answered(tree):
    list_path = (['/', '/issue/' + ID_ISSUE, '/item/' + ID_UPHELD, '/favicon.ico'] * 3)
    with concurrent.futures.ThreadPoolExecutor(max_workers = len(list_path)) as pool:
        list_status = list(pool.map(
            lambda path: cc_public.web.server.respond(tree, path)[0], list_path))
    assert list_status.count(http.HTTPStatus.NOT_FOUND) == 3
    assert list_status.count(http.HTTPStatus.OK) == len(list_path) - 3


def test_requirement_page_shows_its_statement(tree):
    (status, _, body) = cc_public.web.server.respond(tree, '/item/req_rename_keeps_guid')
    assert status == http.HTTPStatus.OK
    assert (b'As soon as the Tooling renames an item, the Tooling shall keep the guid of '
            b'the item.') in body
    assert b'Renaming an item leaves its guid as it was.' in body


def _figure(body: bytes) -> bytes:
    return body[body.index(b'<figure'):body.index(b'</svg>')]
