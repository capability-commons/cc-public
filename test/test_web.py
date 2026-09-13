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


import pathlib
import re

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


# What the contrast test reads, and the minimum it holds every text to.
# The figure is WCAG 2.2 for normal text; the workbench shows position by
# contrast, so its faintest level is ordinary content and not decoration.
#
PATH_STYLE  = pathlib.Path(cc_public.web.app.DIR_STATIC) / 'style.css'
DARK        = '@media (prefers-color-scheme: dark)'
TOKEN       = re.compile(r'(--[a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;')
KEY_PAGE    = '--surface-page'
MINIMUM     = 4.5


def _luminance(colour):
    """Relative luminance of a six digit hexadecimal colour."""

    def channel(value):
        value = value / 255
        return value / 12.92 if value <= 0.03928 \
               else ((value + 0.055) / 1.055) ** 2.4

    colour = colour.lstrip('#')
    (r, g, b) = (int(colour[at:at + 2], 16) for at in (0, 2, 4))

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _ratio(one, other):
    """Contrast ratio between two colours, the brighter over the darker."""

    (a, b) = (_luminance(one), _luminance(other))

    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _theme(text, is_dark):
    """The tokens one theme declares, a later declaration winning."""

    (light, _, dark) = text.partition(DARK)

    return dict(TOKEN.findall(light + (dark if is_dark else '')))


def test_every_text_the_workbench_presents_clears_the_contrast_minimum():
    """
    ---

    id_self:                pyf_test.test_web.test_every_text_the_workbench_presents_clears_the_contrast_minimum
    guid_self:              pyf_f7ec5c551e284c3f9f77bec6d9dd4c49
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Every text clears the contrast minimum
    brief:                  |
                            Every colour the workbench puts text in stands
                            far enough from the page behind it to be read,
                            in both themes.
    description:            |
                            Reads the tokens the stylesheet declares,
                            computes the contrast of each colour that
                            carries text against the page behind it, in
                            the light theme and in the dark, and holds
                            every one to four and a half to one. Holds the
                            three levels to descending order as well,
                            since a cursor fainter than what surrounds it
                            would pass the minimum and carry nothing.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_workbench_text_read
        guid_target:        req_8e8b8a90c77e4114b005cca23963c191

    ...
    """

    text = PATH_STYLE.read_text(encoding = 'utf-8')

    for is_dark in (False, True):
        token = _theme(text, is_dark)
        page  = token[KEY_PAGE]
        for (name, colour) in sorted(token.items()):
            if not (name.startswith('--text-') or name == '--action'):
                continue
            assert _ratio(colour, page) >= MINIMUM, (name, is_dark, colour, page)

    # The levels are three, and each is fainter than the one before, or
    # the cursor is not the loudest thing on the page.
    for is_dark in (False, True):
        token = _theme(text, is_dark)
        rung  = [_ratio(token['--text-' + name], token[KEY_PAGE])
                 for name in ('cursor', 'near', 'far')]
        assert rung == sorted(rung, reverse = True)


def test_a_row_says_whether_opening_it_would_find_anything(graph):
    """
    ---

    id_self:                pyf_test.test_web.test_a_row_says_whether_opening_it_would_find_anything
    guid_self:              pyf_c77c60fa396748aa925065ddd8453a98
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A row tells the truth about what is beneath it
    brief:                  |
                            What a row claims about having more beneath it
                            agrees with what opening it finds, for every
                            view and every row at its root.
    description:            |
                            Opens every row at the root of every view the
                            tree holds and compares what the row claimed
                            with what opening it found. A row that says it
                            has more and has none makes a reader act for
                            nothing; a row that says it has none and has
                            some hides what the view was asked for.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_workbench_more_distinguished
        guid_target:        req_6e06060b9c3146e290e7811879adc915

    ...
    """

    seen = 0

    for view in cc_public.web.projection.views(graph):
        for row in cc_public.web.projection.roots(graph, view):
            found = cc_public.web.projection.opened(graph, view, row.path)
            assert row.has_child == bool(found.groups), row.id_self
            seen += 1

    assert seen > 0
