"""
---

id_self:                pym_cc_public.cli.serving
guid_self:              pym_6bfadd9e59d7408d9c21dfe49c528296
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Serving command
brief:                  |
                        serve: the web interface over a tree, on a
                        local port.
description:            |
                        Opens the application over the roots given, or
                        the working directory, and runs it under
                        uvicorn on the host and port given until
                        interrupted. Several roots are read as one
                        closed world, so a consumer segment is served
                        beside the core it names. The web tier is
                        imported inside the command, so that the tool
                        runs without the web extra installed.
relation:               []

...
"""


import click

import cc_public.cli.group


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--host', 'host', default = '127.0.0.1', show_default = True,
              help = 'The interface to listen on.')
@click.option('--port', 'port', default = 8000, show_default = True, type = int,
              help = 'The port to listen on.')
@cc_public.cli.group.OPTION_ROOT
def serve(host, port, list_root):
    """
    Serve the web interface over the tree, until interrupted. Reads the
    tree once; writes nothing into it.

    """

    # The web tier is imported here, not at the top: it needs the web
    # extra, and a tree that is never served should not have to install
    # it to check or edit.
    #
    import uvicorn

    import cc_public.web.app

    list_root = [str(root) for root in list_root] or ['.']
    uvicorn.run(cc_public.web.app.application(list_root), host = host, port = port)
