"""
---

id_self:                pym_test.test_web
guid_self:              pym_6d3e3795f0c84071aa34f45d97c99073
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Web interface tests
brief:                  |
                        The projections as values, the pages as
                        fragments, and the application through its
                        routes, over a copy of the tree.
description:            |
                        One test checks that the views load with the
                        types at their root and the relations they
                        traverse. One test checks that the rows at the
                        root are of the types the view names, sorted
                        and narrowed as it asks. One test checks that
                        opening a row groups its children by the
                        relation that reached them, refuses an item
                        already on the path, and still admits one that
                        appears in another branch. One test checks
                        that a record read in full carries the fields
                        its type adds, described by its schema, and
                        not the envelope shown above it. One test
                        checks that each page renders what it should
                        and escapes what it shows. One test drives the
                        application: the surface, the rows, the
                        groups, a record as HTML and as JSON, the
                        static files, and what is named by nothing.
relation:               []

...
"""


import pytest
import starlette.testclient

import cc_public.web.app
import cc_public.web.page
import cc_public.web.projection


ID_RECORD = 'ddr_layered_architecture'
ID_VIEW   = 'vw_decision'


@pytest.fixture
def graph(tree):
    return cc_public.web.projection.graph(tree)


@pytest.fixture
def view(graph):
    return next(one for one in cc_public.web.projection.views(graph)
                if  one.id_self == ID_VIEW)


def test_a_view_holds_the_types_at_its_root_and_the_relations_it_walks(graph, view):
    every = cc_public.web.projection.views(graph)
    assert [one.id_self for one in every] == ['vw_decision', 'vw_design', 'vw_review']
    assert all(one.prefix and one.traversal for one in every)

    assert view.prefix == ('ddr',)
    assert [(w.id_relation, w.direction) for w in view.traversal] == [
                ('r_decides',  cc_public.web.projection.HOLDS),
                ('r_is_about', cc_public.web.projection.POINTED_AT_BY)]

    # Nothing infers an inverse, so a backward walk is labelled by the
    # forward relation and the direction it is read in (ddr_view).
    assert view.traversal[1].label.startswith('pointed at by ')


def test_the_rows_at_the_root_are_of_the_types_the_view_names(graph, view):
    rows = cc_public.web.projection.roots(graph, view)
    assert rows and all(row.prefix == 'ddr' for row in rows)
    assert [row.id_self for row in rows] == sorted(row.id_self for row in rows)
    assert all(row.path == (row.guid_self,) for row in rows)

    narrowed = cc_public.web.projection.roots(graph, view, 'layered architecture')
    assert ID_RECORD in [row.id_self for row in narrowed]
    assert 0 < len(narrowed) < len(rows)


def test_opening_a_row_groups_its_children_and_refuses_the_path_it_came_by(graph, view):
    row    = next(r for r in cc_public.web.projection.roots(graph, view)
                  if  r.id_self == ID_RECORD)
    opened = cc_public.web.projection.opened(graph, view, row.path)

    label = [group.label for group in opened.groups]
    assert label[0] == 'decides'
    assert label == [w.label for w in view.traversal if w.label in label]
    child = opened.groups[0].rows[0]
    assert child.path == row.path + (child.guid_self,)
    assert child.brief is not None

    # An item already on the path is not entered again, so a branch
    # cannot re-enter itself; the same item is still reached where the
    # path does not hold it (ddr_view).
    def reached(path):
        return {r.guid_self
                for group in cc_public.web.projection.opened(graph, view, path).groups
                for r in group.rows}

    assert child.guid_self in reached(row.path)
    assert child.guid_self not in reached((child.guid_self, row.guid_self))
    assert all(guid not in child.path for guid in reached(child.path))


def test_a_record_read_in_full_carries_what_its_type_adds_described_by_its_schema(graph):
    found  = cc_public.web.projection.record(graph, ID_RECORD)
    by_key = {field.key: field for field in found.fields}

    # The kind is what the glossary calls the thing, not what the type
    # item is called.
    assert found.kind == 'design decision'
    assert found.location.endswith('ddr_layered_architecture.yaml')

    # The heading and the tree show these, so the record does not.
    assert not {'id_self', 'title', 'brief', 'relation'} & set(by_key)

    assert by_key['decision'].kind == cc_public.web.projection.KIND_PROSE
    assert 'decided' in by_key['decision'].help.lower()
    assert by_key['question'].kind == cc_public.web.projection.KIND_HELD
    assert all(id_self.startswith('qst_') for (id_self, _) in by_key['question'].value)

    assert cc_public.web.projection.record(graph, found.guid_self) == found
    assert cc_public.web.projection.record(graph, 'ddr_nowhere') is None


def test_a_page_renders_each_level_and_escapes_what_it_shows(graph, view):
    rows = cc_public.web.projection.roots(graph, view, 'layered architecture')
    html = str(cc_public.web.page.fragment_rows(rows))
    assert html.startswith('<div id="roots"') and html.endswith('</div>')

    # A row carries a place for each level it discloses.
    for expected in ('class="row', 'class="detail"', 'class="record"', 'class="groups"'):
        assert expected in html

    groups = str(cc_public.web.page.fragment_groups(
                    cc_public.web.projection.opened(graph, view, rows[0].path)))
    assert 'class="glabel">decides<' in groups

    # The target is already the record region, so the fragment does not
    # wrap itself in a second one.
    record = str(cc_public.web.page.fragment_record(
                    cc_public.web.projection.record(graph, ID_RECORD)))
    assert 'class="record"' not in record
    assert record.count('<p class="key">') == len(
                cc_public.web.projection.record(graph, ID_RECORD).fields)
    assert '<code>decision</code>' in record and 'class="identity"' in record

    surface = str(cc_public.web.page.surface(
                    cc_public.web.projection.views(graph), view,
                    cc_public.web.projection.roots(graph, view, 'a < b & "c"'), 'a < b & "c"'))
    assert 'a &lt; b &amp; &#34;c&#34;' in surface and '<b &' not in surface
    assert 'Nothing matches' in surface

    page = str(cc_public.web.page.document('T', surface, 'here'))
    assert page.startswith('<!doctype html><html') and '<title>T</title>' in page
    assert 'htmx.min.js' in page and 'surface.js' in page and 'style.css' in page


@pytest.fixture
def client(tree):
    return starlette.testclient.TestClient(
                cc_public.web.app.application([str(tree.root)]))


def test_the_application_serves_each_level_the_static_files_and_what_is_named_by_nothing(client):
    got = client.get('/', params = {'view': ID_VIEW})
    assert got.status_code == 200 and 'id="roots"' in got.text

    got = client.get('/rows', params = {'view': ID_VIEW, 'q': 'layered architecture'})
    assert got.status_code == 200 and got.text.startswith('<div id="roots"')
    assert ID_RECORD in got.text and '<html' not in got.text

    guid = client.get('/rows', params = {'view': ID_VIEW, 'q': 'layered architecture'})
    path = guid.text.split('data-path="', 1)[1].split('"', 1)[0]

    got = client.get('/groups', params = {'view': ID_VIEW, 'path': path})
    assert got.status_code == 200 and 'glabel' in got.text

    got = client.get('/record', params = {'id': ID_RECORD})
    assert got.status_code == 200 and 'class="key"' in got.text

    got = client.get('/record.json', params = {'id': ID_RECORD})
    assert got.status_code == 200 and got.json()['id_self'] == ID_RECORD
    assert {f['key'] for f in got.json()['fields']} >= {'decision', 'rationale'}

    assert client.get('/record', params = {'id': 'ddr_nowhere'}).status_code == 404
    assert client.get('/groups', params = {'view': ID_VIEW, 'path': ''}).status_code == 404
    assert client.get('/static/htmx.min.js').status_code == 200
    assert client.get('/static/surface.js').status_code == 200
    assert client.get('/static/style.css').status_code == 200
