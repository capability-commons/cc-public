"""
---

id_self:                pym_cctool.web._test.test_web
guid_self:              pym_8849e56e907444ad898ae14b428b9118
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review page tests
brief:                  |
                        Tests of the reading of decisions and of the
                        review pages.
description:            |
                        Each test reads a copy of the repository,
                        whose one settled decision is
                        dec_cross_item_checks_engine, and checks the
                        argument gathered or the page served.
edge:                   []

...
"""


import concurrent.futures
import http
import re
import urllib.parse

import htpy
import pytest

import cctool.web.argument
import cctool.web.catalog
import cctool.web.description
import cctool.web.network
import cctool.web.page
import cctool.web.sankey
import cctool.web.server


ID_DECISION      = 'dec_cross_item_checks_engine'
ID_UPHELD        = 'opt_cross_item_checks_in_clingo'
ID_REJECTED      = 'opt_cross_item_checks_in_souffle'
ID_RULING        = 'ruling_cross_item_checks_engine'


def test_decision_gathers_its_options_and_ruling(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    assert ID_UPHELD in [option.id for option in decision.list_option]
    assert [ruling.id for ruling in decision.list_ruling] == [ID_RULING]
    assert decision.map_standing[ID_UPHELD] == cctool.web.argument.STANDING_UPHELD
    assert decision.map_standing[ID_REJECTED] == cctool.web.argument.STANDING_REJECTED
    assert not decision.is_open()


def test_decision_gathers_only_annotations_about_it(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    assert decision.list_annotation
    for annotation in decision.list_annotation:
        assert ID_DECISION in annotation.targets(cctool.web.argument.RELATION_IS_ABOUT)


def test_decision_lists_the_drivers_of_its_subject(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    assert 'concern_maintainability' in decision.list_driver
    assert decision.unspoken() == []


def test_a_ruling_changed_in_place_changes_the_standing(tree):
    path = tree / '_data' / 'decision' / ID_DECISION / (ID_RULING + '.yaml')
    path.write_text(path.read_text().replace('relation_upholds', 'relation_placeholder')
                                    .replace('relation_rejects', 'relation_upholds', 1)
                                    .replace('relation_placeholder', 'relation_rejects'))
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    assert decision.map_standing[ID_UPHELD] == cctool.web.argument.STANDING_REJECTED
    assert decision.map_standing[ID_REJECTED] == cctool.web.argument.STANDING_UPHELD


def test_decision_is_none_for_an_id_that_is_not_a_decision(tree):
    graph = cctool.web.argument.Graph(tree)
    assert graph.decision(ID_UPHELD) is None
    assert graph.decision('dec_no_such_decision') is None


def test_index_links_every_decision(tree):
    (status, type_content, body) = cctool.web.server.respond(tree, '/decisions')
    assert status == http.HTTPStatus.OK
    assert type_content.startswith('text/html')
    assert '/decision/{id}'.format(id = ID_DECISION).encode() in body


def test_decision_list_folds_each_decision_to_its_title_and_standing(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decisions')
    text = body.decode()
    assert '<details class="decision-entry" id="{id}">'.format(id = ID_DECISION) in text
    assert re.search(r'id="{id}"><summary>.*?<span class="standing standing-upheld">settled<'.format(
        id = ID_DECISION), text, re.DOTALL)
    assert '<span class="drivers">Driven by ' in text


def test_a_decision_opens_to_its_brief_and_its_options(tree):
    graph    = cctool.web.argument.Graph(tree)
    decision = graph.decision(ID_DECISION)
    (_, _, body) = cctool.web.server.respond(tree, '/decisions')
    text = body.decode()
    assert '<p class="brief">{brief}</p>'.format(
        brief = cctool.web.page._prose(decision.item.brief)) in text
    for option in decision.list_option:
        assert 'href="/decision/{decision}#{id}"'.format(decision = ID_DECISION, id = option.id) in text
    assert re.search(r'option-upheld"><div class="main"><p><span class="glyph glyph-upheld" '
                     r'title="upheld">✓</span><a class="run-in" href="/decision/{decision}#{id}"'.format(
                         decision = ID_DECISION, id = ID_UPHELD), text)
    assert '<span class="glyph glyph-rejected" title="rejected">✗</span>' in text
    assert '<a href="/decision/{id}">Decision matrix</a>'.format(id = ID_DECISION) in text


def test_an_option_counts_its_units_for_and_against(tree):
    graph   = cctool.web.argument.Graph(tree)
    summary = cctool.web.page.Summary(graph, graph.decision(ID_DECISION))
    list_unit = [unit for unit in cctool.web.sankey.units(summary.decision)
                 if unit.option == ID_UPHELD]
    assert summary.map_for[ID_UPHELD] == sum(1 for unit in list_unit if unit.is_for())
    assert summary.map_against[ID_UPHELD] == sum(1 for unit in list_unit if not unit.is_for())
    assert summary.standing == cctool.web.page.DECISION_SETTLED


def test_a_decision_with_only_rejections_is_narrowed(tree):
    path = tree / '_data' / 'decision' / ID_DECISION / (ID_RULING + '.yaml')
    path.write_text(path.read_text().replace('relation_upholds', 'relation_rejects'))
    graph   = cctool.web.argument.Graph(tree)
    summary = cctool.web.page.Summary(graph, graph.decision(ID_DECISION))
    assert summary.standing == cctool.web.page.DECISION_NARROWED


def test_decision_list_opens_every_decision_on_request(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?show=open')
    assert '<details class="decision-entry" id="{id}" open>'.format(id = ID_DECISION).encode() in body
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?show=counts')
    assert b'<th class="number">Annotations</th>' in body


def test_decision_list_filter_keeps_and_opens_what_it_finds(tree):
    title = cctool.web.argument.Graph(tree).title(ID_UPHELD)
    query = urllib.parse.urlencode({'q': title})
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?' + query)
    assert body.count(b'<details class="decision-entry"') == 1
    assert '<details class="decision-entry" id="{id}" open>'.format(id = ID_DECISION).encode() in body
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?q=zzqqxx')
    assert b'<details class="decision-entry"' not in body


def test_decision_list_in_another_order_is_not_grouped(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?sort=title')
    text = body.decode()
    assert '<span class="drivers">' not in text
    assert '<span class="subject">Tooling</span>' in text
    list_title = re.findall(r'<span class="title">([^<]+)</span>', text)
    assert list_title == sorted(list_title)
    (_, _, body) = cctool.web.server.respond(tree, '/decisions?sort=standing')
    list_standing = re.findall(r'<span class="standing standing-\w+">(\w+)</span>', body.decode())
    assert list_standing == sorted(list_standing,
                                   key = cctool.web.page.LIST_DECISION_STANDING.index)


def test_decision_page_shows_each_annotation(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    (status, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    assert status == http.HTTPStatus.OK
    for annotation in decision.list_annotation:
        assert '<code>{id}</code>'.format(id = annotation.id).encode() in body


def test_decision_page_escapes_prose(tree):
    path = tree / '_data' / 'decision' / ID_DECISION / (ID_DECISION + '.yaml')
    path.write_text(path.read_text().replace('one item?', '<b>one</b> item?'))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    assert b'&lt;b&gt;one&lt;/b&gt; item?' in body


def test_matrix_has_a_column_for_each_option_and_a_row_for_each_concern(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    head    = matrix[matrix.index('<div class="row head">'):matrix.index('<style>')]
    assert head.count('<div class="cell">') == len(outline.list_option) + 1
    assert '>+ Option</a></span></div></div>' in head
    for id_option in outline.list_option:
        assert 'href="#{id}"'.format(id = id_option) in head
    assert len(re.findall(r'class="(?:row )?concern"', matrix)) == len(outline.list_concern)
    assert '--options: {count}'.format(count = len(outline.list_option)) in matrix
    assert 'matrix-style' not in matrix
    assert '<h2>Decision matrix</h2>' not in text
    assert '<h2>Options</h2>' not in text


def test_an_option_title_opens_its_brief_under_the_head(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text  = body.decode()
    for option in decision.list_option:
        panel = text[text.index('<div class="drill option" id="{id}">'.format(id = option.id)):]
        assert panel.index('<div class="row') > panel.index('<code>{id}</code>'.format(
                                                                id = option.id))
        assert re.search(r'<a href="#{id}" class="mutes [^"]*\blit-show show-{id}"'.format(
                             id = option.id), text)
    assert 'src="/static/review.js"' in text


def test_an_option_is_one_chain_across_the_page(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    sankey  = text[text.index('<figure class="map sankey">'):]
    sankey  = sankey[:sankey.index('</figure>')]
    network = text[text.index('<figure class="map network">'):]
    network = network[:network.index('</figure>')]
    for option in decision.list_option:
        for name in (option.id, option.id + '--for', option.id + '--against'):
            assert ':has(.show-{n}:hover)'.format(n = name) in text
            assert ':has(#{n}:target)'.format(n = name) in text
            assert text.count('id="{n}"'.format(n = name)) == 1
            for part in (matrix, sankey, network):
                assert re.search(r'class="[^"]*\blit-{n}\b'.format(n = re.escape(name)), part)
                assert 'href="#{n}"'.format(n = name) in part


def test_matrix_text_is_in_the_chains_of_the_sankey_diagram(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    assert matrix.startswith('<section class="matrix lit-region"')
    assert 'name other' not in matrix
    for id_concern in outline.list_concern:
        if not outline.units(concern = id_concern):
            continue
        id_option = outline.units(concern = id_concern)[0].option
        assert re.search(r'<span class="name mutes [^"]*\blit-{id}\b[^"]*">'.format(
                             id = id_option), matrix)
        for id_annotation in outline.map_annotation[id_concern]:
            start = matrix.index('id="{c}/{a}"'.format(c = id_concern, a = id_annotation))
            assert re.match(r'[^>]*>\s*<summary><div class="block"><div class="main mutes [^"]*'
                            r'lit-{a}\b'.format(a = id_annotation), matrix[start:])
            summary = matrix[start:matrix.index('</summary>', start)]
            assert re.search(r'<aside class="margin fades [^"]*lit-{a}\b'.format(
                                 a = id_annotation), summary)


def test_for_and_against_are_marked_with_a_tick_and_a_cross(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text  = body.decode()
    assert re.search(r'<tspan class="for">✓\d+</tspan> <tspan class="against">✗\d+</tspan>', text)
    assert re.search(r'<li class="for">✓ ', text)
    assert re.search(r'<li class="against">✗ ', text)
    assert '<li class="for">+' not in text


def test_the_sankey_diagram_is_shown_and_the_graph_folded(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text  = body.decode()
    assert re.search(r'<details class="diagram sankey" open><summary><span class="label">'
                     r'Flow</span></summary><figure class="map sankey">', text)
    assert re.search(r'<details class="diagram network"><summary><span class="label">'
                     r'Tree</span></summary><figure class="map network">', text)


def test_the_graph_keeps_the_order_of_the_sankey_diagram(tree):
    graph = cctool.web.argument.Graph(tree)
    for decision in graph.list_decision():
        outline = cctool.web.sankey.Outline(graph, decision)
        if not outline.map_number:
            continue
        text    = str(cctool.web.network.figure(graph, outline))
        list_y  = [float(re.search(r'id="node-{id}"><title>[^<]*</title><circle cx="[^"]*" '
                                   r'cy="([^"]*)"'.format(id = id_option), text).group(1))
                   for id_option in outline.list_option]
        assert list_y == sorted(list_y)


def test_a_concern_row_opens_to_the_annotations_that_argue_for_it(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text    = body.decode()
    for id_concern in outline.list_concern:
        if not outline.map_annotation[id_concern]:
            continue
        start = text.index('<details class="concern" id="{id}">'.format(id = id_concern))
        row   = text[start:text.index('<div class="drill">', start)]
        assert '<summary><div class="row">' in row
        for id_annotation in outline.map_annotation[id_concern]:
            assert 'id="{c}/{a}"'.format(c = id_concern, a = id_annotation) in text[start:]


def test_replies_sit_under_the_description_of_what_they_reply_to(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text    = body.decode()
    count   = 0
    for id_concern in outline.list_concern:
        for id_annotation in outline.map_annotation[id_concern]:
            list_reply = outline.replies(id_annotation)
            if not list_reply or not graph.map_item[id_annotation].description:
                continue
            key   = id_concern + '/' + id_annotation
            start = text.index('id="{key}"'.format(key = key))
            inner = text[start:text.index('id="{key}/{a}"'.format(key = key,
                                                                  a   = list_reply[0][0]))]
            assert inner.index('<details class="brief">') \
                < inner.index('<details class="description">') \
                < inner.rindex('<div class="replies">')
            count += 1
            key_found = key
    assert count > 0
    key = key_found
    (_, _, shown) = cctool.web.server.respond(
        tree, '/decision/{id}?show={k}/x'.format(id = ID_DECISION, k = urllib.parse.quote(key, safe = '')))
    assert 'id="{k}" open'.format(k = key).encode() in shown
    assert b'<details class="brief" open>' in shown
    assert b'<details class="description" open>' in shown


def test_matrix_cells_show_a_marked_disc_for_each_unit_and_head_totals_in_words(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/{id}?matrix=pugh'.format(
                                                          id = ID_DECISION))
    text    = body.decode()
    matrix  = text[text.index('<section class="matrix'):text.index('</section>')]
    list_unit = outline.list_unit
    count_for = sum(1 for unit in list_unit if unit.is_for())
    assert len(re.findall(r'<span class="unit for fades lit-[^"]*">✓</span>', matrix)) == count_for
    assert (len(re.findall(r'<span class="unit against fades lit-[^"]*">✗</span>', matrix))
            == len(list_unit) - count_for)
    for id_option in outline.list_option:
        list_own = outline.units(option = id_option)
        count    = sum(1 for unit in list_own if unit.is_for())
        head     = matrix[:matrix.index('<style>')]
        assert re.search((r'<a class="for fades [^"]*\blit-show show-{id}--for" href="#{id}--for">'
                          r'{f} for</a>, <a class="against fades [^"]*\blit-show show-{id}--against" '
                          r'href="#{id}--against">{a} against</a>')
                         .format(id = id_option, f = count, a = len(list_own) - count), head)
        assert 'id="{id}--for"'.format(id = id_option) in matrix
    assert 'matrix=' not in matrix
    assert '>All<' not in matrix


def test_description_moves_sources_to_the_margin_and_keeps_other_brackets(tree):
    graph = cctool.web.argument.Graph(tree)
    text  = ('It is so (check.py lines 3-4) and slow (a guess). ASSUMPTION: it stays so. '
             'See opt_cross_item_checks_in_clingo (https://example.org/a).')
    (list_prose, list_note) = cctool.web.description.description(graph, text, 'k')
    prose = str(htpy.p[list_prose])
    assert [str(note) for note in list_note] == [
        '<li id="k-note-1" value="1">check.py lines 3-4</li>',
        '<li id="k-note-2" value="2"><a href="https://example.org/a">example.org/a</a></li>']
    assert 'slow (a guess).' in prose
    assert '<span class="label">assumption</span> it stays so</span>' in prose
    assert '>{title}</a>'.format(title = graph.title(ID_UPHELD)) in prose


def test_description_links_a_term_to_its_concept_and_shows_the_term(tree):
    graph = cctool.web.argument.Graph(tree)
    text  = 'Each [[concept_item|thing]] is an [[item]].'
    (list_prose, _) = cctool.web.description.description(graph, text, 'k')
    prose = str(htpy.p[list_prose])
    assert '<a class="term" href="/item/concept_item"' in prose
    assert '>thing</a> is an item.' in prose


def test_decision_page_steps_to_the_decisions_before_and_after(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text = body.decode()
    assert 'rel="prev"' in text and 'rel="next"' in text
    assert ' 1 of 2 ' in text


def test_matrix_cell_opens_every_annotation_it_counts(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    for href in re.findall(r'<a class="cell" href="([^"]+)"', body.decode().replace('&amp;', '&')):
        list_key   = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)['show']
        id_concern = list_key[0].split(cctool.web.sankey.DELIM_KEY)[0]
        list_unit  = [unit for unit in outline.units(concern = id_concern)
                      if unit.annotation in {key.split(cctool.web.sankey.DELIM_KEY)[1]
                                             for key in list_key}]
        assert len({unit.option for unit in list_unit}) >= 1
        assert href.endswith('#' + list_key[0])
        (_, _, opened) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION + href.split('#')[0])
        for key in list_key:
            assert 'id="{key}" open'.format(key = key).encode() in opened


def test_an_annotation_brief_folds_over_its_description(tree):
    graph    = cctool.web.argument.Graph(tree)
    decision = graph.decision(ID_DECISION)
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text  = body.decode()
    list_with = [annotation for annotation in decision.list_annotation if annotation.description]
    assert list_with
    assert text.count('<details class="brief">') >= len(list_with)
    assert len(re.findall(r'<details class="brief">\s*<summary>\s*<div class="block">', text)) \
        == text.count('<details class="brief">')
    assert 'Evidence' not in text


def test_graph_option_lights_its_chains_through_concerns(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision('dec_tooling_language'))
    body    = str(cctool.web.network.figure(graph, outline))
    name    = 'opt_tooling_in_python'
    assert 'href="#{n}" class="pick lit-show show-{n}"'.format(n = name) in body

    def css(id_item):
        pattern = 'class="([^"]*)" id="node-{id}"'.format(id = id_item)
        return re.search(pattern, body).group(1).split()

    assert 'lit-for-' + name in css('ann_python_is_fast_enough')
    assert 'lit-against-' + name in css('ann_graphs_will_grow')
    assert 'lit-for-' + name in css('ann_cross_item_checks_run_in_clingo')
    assert 'lit-' + name not in css('ann_types_catch_errors_early')
    assert 'lit-' + name in css('concern_performance_efficiency')
    assert not any(css_concern.endswith('-' + name) and css_concern != 'lit-' + name
                   for css_concern in css('concern_performance_efficiency'))
    assert 'href="#concern_' not in body and 'concern_reliability--' not in body
    assert 'href="#{n}--against" class="tally tally-against'.format(n = name) in body
    assert ' id="{n}' .format(n = name) not in body
    assert body.count('href="#ann_graphs_will_grow" class="pick') == 2


def test_a_concern_lights_its_chains_in_the_matrix_and_both_diagrams(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision('dec_tooling_language'))
    (_, _, page) = cctool.web.server.respond(tree, '/decision/dec_tooling_language')
    text    = page.decode()
    network = str(cctool.web.network.figure(graph, outline))
    sankey  = str(cctool.web.sankey.figure(graph, outline, set(), set()))
    concern = 'concern_dependency_risk'

    def classes(body, pattern):
        return re.search(pattern, body).group(1).split()

    node = classes(network, 'class="([^"]*)" id="node-{c}"'.format(c = concern))
    assert 'show-' + concern in node and 'lit-' + concern in node
    assert 'lit-' + concern in classes(
        network, 'class="([^"]*)" id="node-ann_dependencies_are_few_and_permissive"')
    assert 'lit-' + concern not in classes(network,
                                           'class="([^"]*)" id="node-ann_types_catch_errors_early"')
    assert 'lit-' + concern in classes(network, 'class="([^"]*)" id="node-opt_tooling_in_rust"')
    assert re.search(r'<text [^>]*class="concern [^"]*\bshow-{c}\b'.format(c = concern), sankey)
    assert ':has(.show-{c}:hover)'.format(c = concern) in text
    assert re.search(r'<span class="name mutes [^"]*\blit-{c} [^"]*lit-show show-{c}"'.format(
                         c = concern), text)


def test_the_head_of_the_matrix_is_in_the_chains_of_its_options(tree):
    (_, _, page) = cctool.web.server.respond(tree, '/decision/dec_tooling_language')
    text  = page.decode()
    head  = text[text.index('<div class="row head">'):]
    head  = head[:head.index('<style>')]
    title = re.search(r'<a href="#opt_tooling_in_rust" class="([^"]*)"', head).group(1).split()
    assert {'mutes', 'lit-opt_tooling_in_rust', 'lit-opt_tooling_in_rust--for',
            'lit-concern_cost'} <= set(title)
    assert 'lit-opt_tooling_in_python' not in title
    count = re.search(r'<a class="([^"]*)" href="#opt_tooling_in_rust--for"', head).group(1)
    assert {'fades', 'lit-opt_tooling_in_rust'} <= set(count.split())


def test_graph_node_lights_both_its_chains(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision('dec_tooling_language'))
    body    = str(cctool.web.network.figure(graph, outline))
    name    = 'ann_python_is_fast_enough'
    assert 'href="#{n}" class="pick lit-show show-{n}"'.format(n = name) in body
    (_, _, page) = cctool.web.server.respond(tree, '/decision/dec_tooling_language')
    assert '<i id="{n}" class="lit-pin">'.format(n = name) in page.decode()

    def css(id_item):
        pattern = 'class="([^"]*)" id="node-{id}"'.format(id = id_item)
        return re.search(pattern, body).group(1).split()

    assert 'lit-for-' + name in css('ann_gate_takes_a_minute')
    assert 'lit-against-' + name in css('ann_graphs_will_grow')
    assert 'lit-for-' + name in css('ann_cross_item_checks_run_in_clingo')
    assert 'lit-' + name in css('opt_tooling_in_python')
    assert 'lit-' + name not in css('opt_tooling_in_rust')
    reply = 'ann_cross_item_checks_run_in_clingo'
    assert 'lit-' + reply in css('ann_graphs_will_grow')
    assert 'lit-' + reply in css('opt_tooling_in_rust')
    assert 'lit-' + reply not in css('ann_types_catch_errors_early')


def test_sankey_inks_a_reply_by_its_net_effect_on_an_option(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision('dec_tooling_language'))
    key     = 'concern_performance_efficiency/ann_python_is_fast_enough'
    body    = str(cctool.web.sankey.figure(
                  graph, outline, {key, key + '/ann_graphs_will_grow'}, set()))
    assert 'href="#opt_tooling_in_python--for"' in body
    assert 'lit-show show-opt_tooling_in_python--for' in body

    def css(title):
        pattern = r'<text [^>]*class="([^"]*)"[^>]*>(?:(?!</text>).)*?</tspan> {title}<'
        return re.search(pattern.format(title = title), body).group(1).split()

    name = 'opt_tooling_in_python'
    assert 'lit-for-' + name in css('Python fast enough')
    assert 'lit-against-' + name in css('Graphs expected to grow large')
    assert 'lit-for-' + name in css('Cross-item checks run in clingo')
    assert 'lit-against-ann_python_is_fast_enough' in css('Graphs expected to grow large')


def test_item_page_names_the_decision_of_an_option(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/item/' + ID_UPHELD)
    assert '/decision/{id}'.format(id = ID_DECISION).encode() in body


def test_unknown_decision_is_not_found(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/decision/dec_no_such_decision')
    assert status == http.HTTPStatus.NOT_FOUND
    assert b'dec_no_such_decision' in body


def test_static_serves_the_style_sheet(tree):
    (status, type_content, body) = cctool.web.server.respond(tree, '/static/review.css')
    assert status == http.HTTPStatus.OK
    assert type_content == 'text/css'
    assert b'@font-face' in body


def test_static_refuses_a_path_out_of_its_directory(tree):
    (status, _, _) = cctool.web.server.respond(tree, '/static/../server.py')
    assert status == http.HTTPStatus.NOT_FOUND


def test_units_count_each_annotation_concern_and_option(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    count    = sum(len(annotation.targets('relation_speaks_for_concern'))
                * len([id_target
                       for id_relation in ('relation_supports', 'relation_challenges')
                       for id_target in annotation.targets(id_relation)
                       if id_target.startswith('opt_')])
                for annotation in decision.list_annotation)
    assert len(cctool.web.sankey.units(decision)) == count > 0


def test_options_are_ordered_from_most_supported(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    list_unit = cctool.web.sankey.units(decision)
    list_lean = [cctool.web.sankey.lean([unit for unit in list_unit
                                             if unit.option == option.id])
                 for option in cctool.web.sankey.ordered_options(decision)]
    assert list_lean == sorted(list_lean)


def test_map_opens_concerns_and_closes_annotations_by_default(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    unit     = cctool.web.sankey.units(decision)[0]
    title    = cctool.web.argument.Graph(tree).title(unit.annotation)
    path     = '/decision/' + ID_DECISION
    (_, _, opened) = cctool.web.server.respond(tree, path)
    query = '&'.join('toggle=' + other.concern for other in cctool.web.sankey.units(decision)
                     if other.annotation == unit.annotation)
    (_, _, closed) = cctool.web.server.respond(tree, path + '?' + query)
    assert title.encode() in _figure(opened)
    assert title.encode() not in _figure(closed)
    assert '?toggle={key}'.format(key = unit.concern).encode() in opened


def test_closing_a_concern_closes_what_is_open_within_it(tree):
    decision = cctool.web.argument.Graph(tree).decision(ID_DECISION)
    unit     = cctool.web.sankey.units(decision)[0]
    inner    = unit.concern + '/' + unit.annotation
    path     = '/decision/{id}?toggle={i}'.format(id = ID_DECISION, i = inner)
    (status, _, body) = cctool.web.server.respond(tree, path)
    assert status == http.HTTPStatus.OK
    assert '?toggle={key}"'.format(key = unit.concern).encode() in body
    assert cctool.web.sankey.parse_toggle('toggle=a&toggle=a%2Fb') == {'a', 'a/b'}


def test_numbers_follow_the_diagram_from_the_top(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
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
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    for id_concern in outline.list_concern:
        for id_annotation in outline.map_annotation[id_concern]:
            assert 'id="{c}/{a}"'.format(c = id_concern, a = id_annotation).encode() in body


def test_an_annotation_title_in_the_map_opens_it_in_the_list(tree):
    graph   = cctool.web.argument.Graph(tree)
    outline = cctool.web.sankey.Outline(graph, graph.decision(ID_DECISION))
    id_concern    = outline.list_concern[0]
    id_annotation = outline.map_annotation[id_concern][0]
    key           = id_concern + '/' + id_annotation
    path          = '/decision/' + ID_DECISION
    (_, _, body)  = cctool.web.server.respond(tree, path)
    assert '?show={q}#{k}"'.format(q = urllib.parse.quote(key, safe = ''),
                                   k = key).encode() in body
    assert b' open' not in body.split(b'</svg>')[1]
    (_, _, shown) = cctool.web.server.respond(
        tree, path + '?show=' + urllib.parse.quote(key, safe = ''))
    assert 'id="{k}" open'.format(k = key).encode() in shown


def test_decision_page_ends_with_cross_references(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    footer = body.split(b'<footer class="bookend">')[1]
    assert b'Cross-references' in footer
    assert b'/component/lco_tooling' in footer


def test_item_page_shows_edges_in_and_out(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/item/' + ID_UPHELD)
    assert status == http.HTTPStatus.OK
    assert ('/decision/' + ID_DECISION).encode() in body
    assert ('/item/' + ID_RULING).encode() in body


def test_unknown_item_is_not_found(tree):
    (status, _, _) = cctool.web.server.respond(tree, '/item/opt_no_such_option')
    assert status == http.HTTPStatus.NOT_FOUND


def test_requests_at_once_are_all_answered(tree):
    list_path = (['/', '/decision/' + ID_DECISION, '/item/' + ID_UPHELD, '/favicon.ico'] * 3)
    with concurrent.futures.ThreadPoolExecutor(max_workers = len(list_path)) as pool:
        list_status = list(pool.map(
            lambda path: cctool.web.server.respond(tree, path)[0], list_path))
    assert list_status.count(http.HTTPStatus.NOT_FOUND) == 3
    assert list_status.count(http.HTTPStatus.OK) == len(list_path) - 3


def test_requirement_page_shows_its_statement(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/item/rqt_rename_keeps_guid')
    assert status == http.HTTPStatus.OK
    assert (b'As soon as the Tooling renames an item, the Tooling shall keep the guid of '
            b'the item.') in body
    assert b'Renaming an item leaves its guid as it was.' in body


def test_decision_page_offers_to_add_to_the_argument(tree):
    (_, _, body) = cctool.web.server.respond(tree, '/decision/' + ID_DECISION)
    text = body.decode()
    assert text.count('>+ Option</a>') == 1
    assert text.count('>+ For</a>') == len(re.findall(r'class="drill option"', text))
    for id_annotation in re.findall(r'class="block add" data-for="(\w+)"', text):
        assert id_annotation.startswith('ann_')
    assert re.findall(r'<a class="pill (for|against)"[^>]*>(\w+)<', text)[-2:] \
        == [('for', 'Uphold'), ('against', 'Reject')]


def test_every_page_links_to_the_indexes(tree):
    for path in ('/', '/decision/' + ID_DECISION, '/item/' + ID_UPHELD):
        (_, _, body) = cctool.web.server.respond(tree, path)
        assert b'<a href="/">Index</a>' in body
        assert b'<a href="/components">Components</a>' in body
        assert b'<form class="search masthead" method="get" action="/search">' in body


def test_home_lists_every_type_with_its_count(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/')
    assert status == http.HTTPStatus.OK
    text      = body.decode()
    graph     = cctool.web.argument.Graph(tree)
    catalog   = cctool.web.catalog.Catalog(graph)
    list_type = [id_item for id_item in graph.map_item if id_item.startswith('type_')]
    for id_type in list_type:
        assert 'href="{href}"'.format(href = cctool.web.page._type_href(id_type)) in text
    assert '<a href="/decisions">Decision</a>' in text
    assert '<a href="/type/type_option">Option</a>' in text
    count = len(catalog.items('type_option'))
    assert re.search(r'href="/type/type_option">.*?<td class="number">{count}<'.format(
        count = count), text, re.DOTALL)
    assert '<tr class="empty">' in text


def test_type_page_lists_its_items_and_filters_them(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/type/type_option')
    assert status == http.HTTPStatus.OK
    assert '/item/{id}'.format(id = ID_UPHELD).encode() in body
    (_, _, body) = cctool.web.server.respond(tree, '/type/type_option?q=no+such+words+at+all')
    assert '/item/{id}'.format(id = ID_UPHELD).encode() not in body
    (status, _, _) = cctool.web.server.respond(tree, '/type/type_no_such_type')
    assert status == http.HTTPStatus.NOT_FOUND
    (status, _, _) = cctool.web.server.respond(tree, '/type/' + ID_UPHELD)
    assert status == http.HTTPStatus.NOT_FOUND


def test_subject_page_gathers_what_is_about_it(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/components')
    assert status == http.HTTPStatus.OK
    assert b'href="/component/lco_tooling"' in body
    (status, _, body) = cctool.web.server.respond(tree, '/component/lco_tooling')
    assert status == http.HTTPStatus.OK
    assert '/decision/{id}'.format(id = ID_DECISION).encode() in body
    (status, _, _) = cctool.web.server.respond(tree, '/component/' + ID_UPHELD)
    assert status == http.HTTPStatus.NOT_FOUND


def test_search_finds_items_by_their_words(tree):
    title = cctool.web.argument.Graph(tree).title(ID_UPHELD)
    query = urllib.parse.urlencode({'q': title})
    (status, _, body) = cctool.web.server.respond(tree, '/search?' + query)
    assert status == http.HTTPStatus.OK
    assert '/item/{id}'.format(id = ID_UPHELD).encode() in body
    (_, _, body) = cctool.web.server.respond(tree, '/search?q=zzqqxx')
    assert b'No item holds those words.' in body


def test_interface_index_lists_interface_control_documents(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/interfaces')
    assert status == http.HTTPStatus.OK
    text = body.decode()
    assert text.count('href="/interface/icd_') == 5
    assert '<a href="/interface/icd_cctool_check">Checker interface</a>' in text
    assert re.search(r'<td>Python</td>\s*<td class="number">(<span class="gap">)?\d+ of 8<', text)


def test_requirement_index_groups_requirements_by_subject(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/requirements')
    assert status == http.HTTPStatus.OK
    assert b'<h2>Tooling</h2>' in body
    assert b'<h2>Chat</h2>' in body
    assert body.count(b'href="/requirement/rqt_') == len(
                            list((tree / '_data' / 'requirement').glob('rqt_*.yaml')))
    assert (b'If an edit would add a failure to the tree, the Tooling shall refuse the '
            b'edit.') in body


def test_requirement_page_reads_down_its_trace(tree):
    (status, _, body) = cctool.web.server.respond(
                            tree, '/requirement/rqt_edit_refuses_new_failure')
    assert status == http.HTTPStatus.OK
    text = body.decode()
    list_slot = re.findall(r'<span class="slot">(\w+)</span>', text)
    assert list_slot == ['condition', 'subject', 'modal_verb', 'process_word', 'object']
    list_station = re.findall(r'<div class="block (station[^"]*)">.*?<span class="label">(\w+)',
                              text)
    assert list_station == [('station gap', 'Source'), ('station gap', 'Parent'),
                            ('station', 'Rationale'), ('station statement', 'Statement'),
                            ('station', 'Subject'), ('station', 'Verification')]
    assert 'Does ‘failure’ name a process' in text
    assert text.count('<td class="said">') == 9
    assert 'class="pill' not in text
    assert '/requirement/rqt_format_keeps_formatted_file' in text


@pytest.mark.parametrize('path', ['/requirement/rqt_missing',
                                  '/requirement/lco_tooling'])
def test_requirement_page_of_anything_else_is_not_found(tree, path):
    (status, _, _) = cctool.web.server.respond(tree, path)
    assert status == http.HTTPStatus.NOT_FOUND


def test_interface_page_opens_with_its_contract(tree):
    (status, _, body) = cctool.web.server.respond(tree, '/interface/icd_cctool_check')
    assert status == http.HTTPStatus.OK
    text = body.decode()
    list_name = re.findall(r'<code class="name">([\w.]+)</code>', text)
    assert list_name == ['Failures', 'cctool.check.check', 'check', 'review',
                         'check_documents', 'review_documents', 'columns', 'wording']
    assert re.findall(r'<div class="label">(\w+)</div>', text) == ['Declarations', 'Modules',
                                                                   'Functions', 'All']
    assert text.count('class="verdict unrealized"') == 1
    assert 'class="verdict differs"' not in text
    assert '<code>check(root: pathlib.Path) -&gt; Failures</code>' in text
    assert 'href="/item/pyf_cctool.check.check.review"' in text


def test_interface_page_marks_where_the_code_differs(tree):
    path = tree / '_data/interface_control_document/icd_cctool_check.yaml'
    path.write_text(path.read_text().replace('spelling:  tuple[Failures, Failures]',
                                             'spelling:  tuple[Failures, str]', 1))
    (_, _, body) = cctool.web.server.respond(tree, '/interface/icd_cctool_check')
    text = body.decode()
    assert text.count('class="verdict differs"') == 1
    assert ('<span class="stated differs">tuple[Failures, str]</span>'
            '<span class="code-says" title="What the code says">tuple[Failures, Failures]'
            '</span>') in text
    assert 'The code differs for 1 of 8 members' in text


def test_dataflow_interface_page_draws_the_step_and_its_semantics(tree):
    path = tree / '_data/interface_control_document/icd_frame_detector.yaml'
    path.write_text(TEXT_DATAFLOW)
    (status, _, body) = cctool.web.server.respond(tree, '/interface/icd_frame_detector')
    assert status == http.HTTPStatus.OK
    text = body.decode()
    assert '<th scope="row">Surface</th><td>Dataflow step, Artifact</td>' in text
    figure = text[text.index('<figure class="step">'):text.index('</figure>')]
    assert re.findall(r'<g class="(port[^"]*)">', figure) == ['port', 'port optional', 'port',
                                                             'port']
    assert figure.count('marker-start=') == 1
    assert re.findall(r'<tr id="port-icm_frame_detector.(\w+)">', text) == [
        'frame', 'threshold', 'detections', 'background']
    assert re.findall(r'Semantics <span class="note">(\d+ of \d+) stated', text) == [
        '6 of 12', '3 of 10']
    assert text.count('class="block part unstated"') == 13
    assert re.findall(r'<span class="column">(\w+)</span>', text) == ['Realized']
    assert '<span class="run-in artifact-name">detection file</span>' in text


@pytest.mark.parametrize('path', ['/interface/icd_missing',
                                  '/interface/lco_tooling'])
def test_interface_page_of_anything_else_is_not_found(tree, path):
    (status, _, _) = cctool.web.server.respond(tree, path)
    assert status == http.HTTPStatus.NOT_FOUND


def _figure(body: bytes) -> bytes:
    return body[body.index(b'<figure'):body.index(b'</svg>')]


# An interface control document with a dataflow step surface and an
# artifact surface, which the tree does not hold.
#
TEXT_DATAFLOW = """\
id_self:                icd_frame_detector
guid_self:              icd_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a60
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Frame detector
brief:                  |
                        A step that finds objects in camera frames,
                        and the detection files it leaves for the
                        logger.
description:            |
                        The step runs once for each frame the camera
                        delivers, against a background model it keeps
                        between frames. Each run writes the detections
                        it finds, and every minute the step closes a
                        file of them for the logger to collect.
version_interface:      '0.1'
support:                unsupported

declaration:

  detection:
    id_self:            icm_frame_detector.detection
    guid_self:          icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a61
    name:               Detection
    brief:              |
                        One object found in a frame.
    shape:              |
                        A box in pixel coordinates of the frame, a
                        class name and a confidence between 0 and 1.

surface:

  step:

    dataflow_step:

      input:

        frame:
          id_self:      icm_frame_detector.frame
          guid_self:    icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a62
          name:         frame
          brief:        |
                        The image to search, with its capture time.

          type:
            spelling:   Frame

        threshold:
          id_self:      icm_frame_detector.threshold
          guid_self:    icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a63
          name:         threshold
          brief:        |
                        The least confidence a detection is kept at.

          type:
            spelling:   float

          optional:     true

      output:

        detections:
          id_self:      icm_frame_detector.detections
          guid_self:    icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a64
          name:         detections
          brief:        |
                        The objects found in the frame, most confident
                        first.

          type:
            declaration:  detection
            spelling:   list[Detection]

      state:

        background:
          id_self:      icm_frame_detector.background
          guid_self:    icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a65
          name:         background
          brief:        |
                        A running model of the empty scene.

          type:
            spelling:   BackgroundModel

      invocation:       |
                        Once for each frame, as it arrives. The
                        threshold last given is used; with none given,
                        0.5.
      initialization:   |
                        The background model starts empty and is
                        learned over the first 50 frames, during which
                        no detections are written.
      persistence:      |
                        The background model is kept between
                        invocations and lost on a restart.
      ordering:         |
                        Detections are written in the order of the
                        frames they come from.
      back_pressure:    |
                        A frame that arrives while the last is still
                        being searched is dropped, and the drop is
                        counted.
      failure:          |
                        A frame that cannot be decoded writes no
                        detections; the next frame is searched as
                        usual.

  log:

    artifact:

      artifact:

        detection_file:
          id_self:      icm_frame_detector.detection_file
          guid_self:    icm_5d0a8a3c6e2b4f0e9c7a1b2d3e4f5a66
          name:         detection file
          brief:        |
                        The detections of one minute.
          content:      |
                        Every detection written in one minute, with
                        the capture time of its frame.

          payload:
            declaration:  detection
            version:    '1'

          encoding:     |
                        JSON Lines in UTF-8, one detection to a line,
                        compressed with gzip.
          convention:   |
                        Boxes in pixels, origin at the top left of the
                        frame, x to the right and y down. Times in
                        UTC.

      production:       |
                        At the end of each minute, whether or not
                        anything was detected.
      atomicity:        |
                        The file is written under a temporary name and
                        renamed when complete.
      retention:        |
                        Kept for seven days, then removed by the
                        logger.

edge:                   []
"""
