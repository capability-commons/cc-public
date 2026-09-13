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
                        plain values: the graph indexed for
                        navigation, the views it holds, and the rows,
                        groups and records a view asks for. The page
                        module turns those values into HTML with htpy.
                        The application module binds them to routes
                        with Starlette and serves the vendored HTMX,
                        the stylesheet and the script that places the
                        cursor. Nothing here writes to the tree. The
                        domain never imports this package; the command
                        line does, inside the serve command, so that a
                        tree that is never served need not install the
                        web extra. What the surface does and why is
                        decided in ddr_navigation_surface,
                        ddr_progressive_disclosure and ddr_view.
relation:               []

...
"""
