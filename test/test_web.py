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
                        fragments with one root, and the application
                        through its routes, over a copy of the tree.
description:            |
                        One test checks that the listing holds every
                        item, counts each kind, and narrows by query
                        and by kind. One test checks that the detail
                        of a record labels its fields from its schema,
                        holds its edges both ways, and is None for a
                        name nothing bears. One test checks that each
                        page renders to one root and escapes what it
                        shows. One test drives the application: the
                        index, the search fragment, an item as a page
                        and as JSON, the static files, and not found.
relation:               []

...
"""


import pytest
import starlette.testclient

import cc_public.item
import cc_public.web.app
import cc_public.web.page
import cc_public.web.projection


ID_RECORD = 'ddr_layered_architecture'


def test_a_listing_holds_every_item_and_narrows_by_query_and_kind(tree):
    listing = cc_public.web.projection.listing(tree, limit = 100000)
    index   = cc_public.item.index(tree.context.map_document)
    assert listing.total == len(index.by_id) == len(listing.entries)
    assert sum(kind.count for kind in listing.kinds) == listing.total
    assert all(kind.title != kind.prefix for kind in listing.kinds)

    narrowed = cc_public.web.projection.listing(tree, query = 'layered architecture')
    assert ID_RECORD in [e.id_self for e in narrowed.entries]
    assert 0 < narrowed.total < listing.total

    by_kind = cc_public.web.projection.listing(tree, prefix = 'ddr', limit = 5)
    assert by_kind.total > 5 and len(by_kind.entries) == 5
    assert all(e.prefix == 'ddr' for e in by_kind.entries)


def test_a_detail_labels_its_fields_from_the_schema_and_holds_its_edges(tree):
    found = cc_public.web.projection.detail(tree, ID_RECORD)
    assert found.prefix == 'ddr' and found.kind == 'Design decision type'
    assert found.path == '' and found.location.endswith('ddr_layered_architecture.yaml')

    by_key = {field.key: field for field in found.fields}
    assert 'id_self' not in by_key and 'relation' not in by_key
    assert by_key['decision'].kind == cc_public.web.projection.KIND_PROSE
    assert by_key['decision'].help and 'decided' in by_key['decision'].help.lower()
    assert by_key['title'].kind == cc_public.web.projection.KIND_DATUM
    assert by_key['question'].kind == cc_public.web.projection.KIND_HELD
    assert all(id_self.startswith('qst_') for (id_self, _) in by_key['question'].value)

    assert found.outgoing and all(len(edge) == 2 for edge in found.outgoing)
    assert found.incoming and all(len(edge) == 2 for edge in found.incoming)

    same = cc_public.web.projection.detail(tree, found.guid_self)
    assert same == found
    assert cc_public.web.projection.detail(tree, 'ddr_nowhere') is None


def test_a_page_renders_to_one_root_and_escapes_what_it_shows(tree):
    found = cc_public.web.projection.detail(tree, ID_RECORD)
    html  = str(cc_public.web.page.detail(found))
    assert html.startswith('<article') and html.endswith('</article>')
    assert html.count('<article') == 1 and 'cc_public.cli' in html

    listing = cc_public.web.projection.listing(tree, query = 'a < b & "c"')
    html    = str(cc_public.web.page.index(listing))
    assert html.startswith('<section') and html.endswith('</section>')
    assert 'a &lt; b &amp; &#34;c&#34;' in html and '<b &' not in html

    page = str(cc_public.web.page.document('T', cc_public.web.page.fragment_listing(listing),
                                           'here'))
    assert page.startswith('<!doctype html><html') and '<title>T</title>' in page
    assert 'htmx.min.js' in page and 'style.css' in page


@pytest.fixture
def client(tree):
    return starlette.testclient.TestClient(
                cc_public.web.app.application([str(tree.root)]))


def test_the_application_serves_the_index_the_search_the_items_and_the_static(client):
    got = client.get('/')
    assert got.status_code == 200 and 'Design decision type' in got.text

    got = client.get('/search', params = {'q': 'layered architecture'})
    assert got.status_code == 200 and got.text.startswith('<div id="listing"')
    assert '/item/' + ID_RECORD in got.text and '<html' not in got.text

    got = client.get('/', params = {'q': 'layered architecture', 'kind': 'sch'})
    assert got.status_code == 200 and 'Nothing matches' in got.text

    got = client.get('/item/' + ID_RECORD)
    assert got.status_code == 200 and '<article' in got.text and '<html' in got.text

    got = client.get('/item/' + ID_RECORD + '.json')
    assert got.status_code == 200
    assert got.json()['id_self'] == ID_RECORD
    assert {f['key'] for f in got.json()['fields']} >= {'decision', 'rationale'}

    assert client.get('/item/ddr_nowhere').status_code == 404
    assert client.get('/item/ddr_nowhere.json').status_code == 404
    assert client.get('/static/htmx.min.js').status_code == 200
    assert client.get('/static/style.css').status_code == 200
