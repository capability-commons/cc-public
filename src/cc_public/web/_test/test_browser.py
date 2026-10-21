"""
---

id_self:                pym_cc_public.web._test.test_browser
guid_self:              pym_a2a39a87361c499bb021c50f15ff887b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review page browser tests
brief:                  |
                        Tests of how the decision page lights its
                        chains, in a browser.
description:            |
                        Each test opens the page of a decision in
                        Chromium, through Playwright, with every
                        request answered by the server's own respond
                        so no port is opened, then hovers over or
                        clicks marks and checks what is lit: in each
                        region a chain reaches, a mark is dimmed,
                        faded or muted exactly when it is outside the
                        chain. They are marked slow, so the gate
                        leaves them out; pixi run test runs them, and
                        skips them if Playwright or its browser is not
                        installed (pixi run browsers). CC_CHROMIUM
                        names a Chromium to use instead of
                        Playwright's own.
edge:                   []

...
"""


import os
import urllib.parse

import pytest

import cc_public.web.server


pytestmark = pytest.mark.slow

URL_BASE    = 'http://review.test'
ID_DECISION = 'dec_tooling_language'

# For a chain called name, the marks in each region it reaches that are
# out of step with it: dimmed, faded or muted although in the chain, or
# in full although outside it. A region the chain does not reach must
# have nothing dimmed.
#
JS_ASTRAY = '''
(name) => {
  const away = (e) => {
    const style = getComputedStyle(e);
    if (e.matches('.mutes')) {
      const rgb = style.color.match(/[\\d.]+/g).map(Number);
      const red = style.color.startsWith('color(') ? rgb[0] * 255 : rgb[0];
      return red > 120;
    }
    return parseFloat(style.opacity) < 0.6;
  };
  const list = [];
  for (const region of document.querySelectorAll('.lit-region')) {
    const reached = name !== null && region.querySelector('.lit-' + CSS.escape(name)) !== null;
    for (const e of region.querySelectorAll('.dims, .fades, .mutes')) {
      const lit = name !== null && e.classList.contains('lit-' + name);
      if (away(e) !== (reached && !lit)) {
        list.push((e.getAttribute('class') || '').split(' ').slice(0, 3).join(' '));
      }
    }
  }
  return list;
}
'''


# -----------------------------------------------------------------------------
@pytest.fixture
def page(tree):
    """
    Return a browser page on the decision, its graph unfolded, answered
    from the copy of the repository at tree.

    """

    sync_api = pytest.importorskip('playwright.sync_api')

    def answer(route):
        url = urllib.parse.urlsplit(route.request.url)
        path = url.path + ('?' + url.query if url.query else '')
        (status, content_type, body) = cc_public.web.server.respond(tree, path)
        route.fulfill(status = status, content_type = content_type, body = body)

    with sync_api.sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(
                          executable_path = os.environ.get('CC_CHROMIUM'))
        except sync_api.Error as error:
            pytest.skip('no browser for Playwright (pixi run browsers): {e}'.format(e = error))
        page = browser.new_page(viewport = {'width': 1400, 'height': 1100})
        page.route(URL_BASE + '/**', answer)
        page.goto('{base}/decision/{id}'.format(base = URL_BASE, id = ID_DECISION))
        page.add_style_tag(content = '* { transition: none !important; }')
        page.locator('details.diagram.network > summary').click()
        page.mouse.move(1, 1)
        yield page
        browser.close()


# -----------------------------------------------------------------------------
def _hover(page, selector: str, text: str | None = None) -> None:
    """
    Move the pointer onto the middle of the first mark that matches
    selector, holding text if given, and let the lighting settle.

    """

    locator = page.locator(selector, has_text = text).first if text else page.locator(selector).first
    locator.scroll_into_view_if_needed()
    box = locator.bounding_box()
    page.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
    page.wait_for_timeout(300)


# -----------------------------------------------------------------------------
def _astray(page, name: str | None) -> list[str]:
    """
    Return the marks out of step with the chain called name, or with no
    chain lit if name is None.

    """

    return page.evaluate(JS_ASTRAY, name)


def test_nothing_is_dimmed_at_rest(page):
    assert _astray(page, None) == []


def test_an_option_title_lights_its_chains_everywhere(page):
    _hover(page, 'section.matrix .row.head .cell > a')
    assert _astray(page, 'opt_tooling_in_python') == []
    assert page.locator('figure.sankey .dims').evaluate_all(
               'list => list.some(e => parseFloat(getComputedStyle(e).opacity) < 0.6)')


@pytest.mark.parametrize('selector', ['section.matrix .row.head .total a.against',
                                      'figure.network a.tally-against'])
def test_a_count_lights_the_chains_of_its_role(page, selector):
    _hover(page, selector)
    assert _astray(page, 'opt_tooling_in_python--against') == []


@pytest.mark.parametrize('selector', ['section.matrix details.concern > summary .name',
                                      'figure.sankey text.concern',
                                      'figure.network g.node.concern'])
def test_a_concern_lights_its_chains_from_wherever_it_is_hovered(page, selector):
    _hover(page, selector, 'Dependency risk')
    assert _astray(page, 'concern_dependency_risk') == []


def test_an_annotation_in_the_sankey_diagram_lights_the_graph_and_matrix(page):
    _hover(page, 'figure.sankey text.annotation', 'Graphs will grow large')
    assert _astray(page, 'ann_graphs_will_grow') == []
    outline = page.locator('figure.network a.pick', has_text = 'Graphs will grow large').first \
              .locator('.shape').evaluate('e => getComputedStyle(e).strokeWidth')
    assert float(outline.removeprefix('calc(').removesuffix('px)').removesuffix('px')) > 1.2


def test_a_pin_holds_until_a_hover_and_a_click_off_clears_it(page):
    page.locator('section.matrix .row.head .cell > a').first.click()
    page.mouse.move(1, 1)
    page.wait_for_timeout(300)
    assert page.evaluate('location.hash') == '#opt_tooling_in_python'
    assert _astray(page, 'opt_tooling_in_python') == []
    _hover(page, 'section.matrix .row.head .cell > a >> nth=1')
    assert _astray(page, 'opt_tooling_in_rust') == []
    page.mouse.move(1, 1)
    page.mouse.click(1, 1)
    page.wait_for_timeout(300)
    assert _astray(page, None) == []


def test_clicking_an_annotation_in_the_graph_pins_it_in_place(page):
    node = page.locator('figure.network a.pick', has_text = 'Graphs will grow large').last
    node.scroll_into_view_if_needed()
    scroll = page.evaluate('window.scrollY')
    node.locator('.shape').click()
    page.mouse.move(1, 1)
    page.wait_for_timeout(300)
    assert page.evaluate('location.hash') == '#ann_graphs_will_grow'
    assert page.evaluate('window.scrollY') == scroll
    assert _astray(page, 'ann_graphs_will_grow') == []
    assert page.evaluate("[...document.querySelectorAll('.chosen')].map(e => e.id)") \
        == ['concern_performance_efficiency/ann_graphs_will_grow']
    assert page.locator('details.annotation.chosen').evaluate('e => e.open')
    assert page.locator('details.annotation.chosen').evaluate(
               "e => e.style.getPropertyValue('--brace-left').startsWith('url(')")


def test_the_folding_of_each_diagram_is_kept_from_decision_to_decision(page):
    page.locator('details.diagram.sankey > summary').click()
    page.goto('{base}/decision/{id}'.format(base = URL_BASE, id = 'dec_cross_item_checks_engine'))
    assert page.locator('details.diagram.network').evaluate('e => e.open')
    assert not page.locator('details.diagram.sankey').evaluate('e => e.open')
