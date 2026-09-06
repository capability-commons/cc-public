"""
---

id_self:                pym_cc_public.render.html
guid_self:              pym_6552a11395a544848649ee0301ad8a6c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pages
brief:                  |
                        The briefing and the technical appendix as
                        HTML, from templates.
description:            |
                        Renders the projection through Jinja templates
                        held beside this module, with the stylesheet
                        inlined so that a page stands alone. Prose is
                        escaped and split into paragraphs; the drawing
                        is inlined as SVG.
relation:               []

...
"""


import pathlib

import jinja2
import markupsafe


DIR_TEMPLATE = pathlib.Path(__file__).parent / 'template'
NAME_STYLE   = 'style.css'
SUFFIX       = '.html'


# -----------------------------------------------------------------------------
def briefing(projection):
    """
    Return the briefing as an HTML document: the short account for a
    reader with little time.

    """

    return _render('briefing', projection)


# -----------------------------------------------------------------------------
def appendix(projection, svg = None):
    """
    Return the technical appendix as an HTML document: every item in
    full, every finding, the runs, the drawing and the identities.

    """

    return _render('appendix', projection, svg = svg)


# -----------------------------------------------------------------------------
def _render(name, projection, svg = None):
    env = jinja2.Environment(loader = jinja2.FileSystemLoader(DIR_TEMPLATE),
                             autoescape = True, trim_blocks = True, lstrip_blocks = True)
    env.filters['prose'] = _prose
    env.filters['words'] = _words
    template = env.get_template(name + SUFFIX)
    return template.render(d = projection, svg = markupsafe.Markup(svg or ''),  # noqa: S704 -- an SVG graphviz drew from text the tool wrote
                           style = (DIR_TEMPLATE / NAME_STYLE).read_text(encoding = 'utf-8'))


def _prose(text):
    """Paragraphs of a block scalar as paragraphs of HTML, escaped."""
    paragraphs = [' '.join(p.split()) for p in str(text or '').split('\n\n')]
    return markupsafe.Markup(''.join('<p>{p}</p>'.format(p = markupsafe.escape(p))  # noqa: S704 -- every paragraph is escaped
                                     for p in paragraphs if p))


def _words(text):
    """A block scalar as one line."""
    return ' '.join(str(text or '').split())
