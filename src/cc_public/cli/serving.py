"""
---

id_self:                pym_cc_public.cli.serving
guid_self:              pym_b19064f7f1d04166aae79ef78e16399e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Serving commands
brief:                  |
                        The command that serves the review pages.
description:            |
                        This module holds the serve command, which
                        serves the review pages of a tree until
                        interrupted.
relation:               []

...
"""


import pathlib

import click

import cc_public.cli.group
import cc_public.web.server


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--root',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to show. Defaults to the working directory.')
@click.option('--host',
              default = cc_public.web.server.HOST_DEFAULT,
              help    = 'The address to listen on. Defaults to this computer only.')
@click.option('--port',
              default = cc_public.web.server.PORT_DEFAULT,
              type    = int,
              help    = 'The port to listen on.')
def serve(root: pathlib.Path, host: str, port: int) -> None:
    """
    Serve pages to review the issues of the tree under --root, and the
    argument on each, until interrupted.

    The pages change nothing. Each page shows the tree as it is when
    the page is loaded.

    """

    click.echo('Serving {root} at http://{host}:{port}/'.format(root = root.resolve(),
                                                              host = host,
                                                              port = port))
    try:
        cc_public.web.server.serve(root.resolve(), host, port)
    except KeyboardInterrupt:
        click.echo('Stopped.')
