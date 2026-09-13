"""
---

id_self:                pyp_cc_public.web
guid_self:              pyp_6de4efa609f542ac9933cbca0b7fb0e8
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Web interface
brief:                  |
                        The human interface: projections of the tree,
                        pages built from them, and the application
                        that serves both.
description:            |
                        The package holds three modules. The
                        projection module reads the tree and returns
                        plain values: an index of items by type, and
                        one item in full with its fields described by
                        its schema and the edges at it. The page
                        module turns those values into HTML with htpy,
                        as fragments with one root each and as whole
                        documents. The application module binds the
                        pages and their JSON to routes with Starlette
                        and serves the vendored HTMX and the
                        stylesheet from static. Nothing here writes to
                        the tree. The domain never imports this
                        package; the command line does, inside the
                        serve command, so that a tree that is never
                        served need not install the web extra
                        (ddr_display_stack).
relation:               []

...
"""
