"""
---

id_self:                pym_cctool.cli.serving
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
import sys

import click

import cctool.cli.group
import cctool.web.server


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to show. Defaults to the working directory.')
@click.option('--host',
              metavar = 'HOST',
              default = cctool.web.server.HOST_DEFAULT,
              help    = 'The address to listen on. Defaults to this computer only.')
@click.option('--port',
              metavar      = 'PORT',
              default      = cctool.web.server.PORT_DEFAULT,
              show_default = True,
              type         = click.IntRange(0, 65535),
              help         = 'The port to listen on.')
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

    Pages are served to a browser that names the server by a name of
    this computer or by an IP address, and not under any other name, so
    that a site cannot read them by pointing a name of its own at this
    computer. With --host 0.0.0.0, every computer that can reach the
    port can read the pages, by its address.

    """

    click.echo('Serving {root} at http://{host}:{port}/'.format(root = root.resolve(),
                                                              host = host,
                                                              port = port))
    try:
        cctool.web.server.serve(root.resolve(), host, port)
    except KeyboardInterrupt:
        click.echo('Stopped.')
    except OSError as error:
        click.echo('Cannot serve at {host}:{port}: {error}. Give another --port, or stop '
                   'what listens there.'.format(host  = host,
                                                port  = port,
                                                error = error.strerror or error),
                   err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)
