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
edge:                   []

...
"""


import pathlib

import click

import cc_public.cli.group
import cc_public.web.server


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--root',
              metavar = 'DIRPATH',
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
    Serve pages to review the decisions of the tree under --root, and the
    deliberation of each, until interrupted.

    Each page shows the tree as it is when the page is loaded, and
    reading a page changes nothing. The forms on the decision pages add
    options, arguments and rulings. Each form is made as one batch edit,
    as cctool batch makes one: it is written only if it adds no failure,
    and otherwise the form is shown again with the failures it would
    add. Forms are taken only from the pages of this server, on this
    computer.

    """

    click.echo('Serving {root} at http://{host}:{port}/'.format(root = root.resolve(),
                                                              host = host,
                                                              port = port))
    try:
        cc_public.web.server.serve(root.resolve(), host, port)
    except KeyboardInterrupt:
        click.echo('Stopped.')
