"""
---

id_self:                pym_cc_public.render.pdf
guid_self:              pym_41b0e5c73b8a459287aa180fb572c510
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  PDF
brief:                  |
                        A page written as a PDF.
description:            |
                        Writes an HTML document as a PDF with
                        WeasyPrint, which lays the page out from the
                        stylesheet without a browser.
relation:               []

...
"""


import pathlib

import weasyprint


# -----------------------------------------------------------------------------
def write(html, path):
    """
    Write the HTML document as a PDF at path and return the path.

    """

    path = pathlib.Path(path)
    path.parent.mkdir(parents = True, exist_ok = True)
    weasyprint.HTML(string = html).write_pdf(path)

    return path
