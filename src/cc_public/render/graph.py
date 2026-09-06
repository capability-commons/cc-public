"""
---

id_self:                pym_cc_public.render.graph
guid_self:              pym_c14ad50354024816ad89ebd2dbbc07c7
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Drawing
brief:                  |
                        A dot graph drawn as SVG by Graphviz.
description:            |
                        Runs dot on the text of a graph and returns
                        the SVG element for inlining, or nothing where
                        dot is not installed, so that a page renders
                        without its drawing rather than not at all.
relation:               []

...
"""


import subprocess


COMMAND = 'dot'
MARK    = '<svg'


# -----------------------------------------------------------------------------
def svg(dot):
    """
    Return the drawing of a dot graph as an SVG element, for inlining
    in a page, or an empty string where dot is not available. A fresh
    Graphviz install knows no formats until its plugin registry is
    written, which dot does for itself when asked once.

    """

    text = _dot(dot)

    if text is None and _register():
        text = _dot(dot)

    return text[text.find(MARK):] if text and MARK in text else ''


# -----------------------------------------------------------------------------
def _dot(dot):
    try:
        done = subprocess.run([COMMAND, '-Tsvg'], input = dot, capture_output = True,  # noqa: S603 -- graphviz on text the tool wrote
                              text = True, check = False)
    except OSError:
        return None

    return done.stdout if done.returncode == 0 else None


def _register():
    try:
        return subprocess.run([COMMAND, '-c'], capture_output = True, text = True,  # noqa: S603 -- writes graphviz's own plugin registry
                              check = False).returncode == 0
    except OSError:
        return False
