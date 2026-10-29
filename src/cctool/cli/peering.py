"""
---

id_self:                pym_cctool.cli.peering
guid_self:              pym_a64a75e2aee74836bade953559de0d98
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Peering commands
brief:                  |
                        The commands that set up a peer and report
                        which release it pins.
description:            |
                        This module holds the peer group: init writes
                        the segment item of a new peer, and status
                        reports the release that each segment item of
                        a tree pins, and the newest release of the
                        segment that holds it. The commands that
                        switch a peer between a release and a checkout
                        and upgrade it are still to come.
usage:                  |
                        cctool peer init NAME --title TEXT --brief
                        TEXT --copyright TEXT --license TEXT cctool
                        peer status
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.edit.peer


OPTION_ROOT = click.option('--root',
                           metavar = 'DIRPATH',
                           default = '.',
                           type    = click.Path(exists    = True,
                                                file_okay = False,
                                                path_type = pathlib.Path),
                           help    = 'The tree of the peer. Defaults to the working directory.')


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
def peer() -> None:
    """
    Set up a peer, and report which release it pins.

    """


# -----------------------------------------------------------------------------
@peer.command()
@click.argument('name')
@click.option('--title',
              required = True,
              metavar  = 'TEXT',
              help     = 'The title of the segment item, such as "The cc-patrol segment".')
@click.option('--brief',
              required = True,
              metavar  = 'TEXT',
              help     = 'What the segment is, as the brief of its segment item.')
@click.option('--copyright',
              'text_copyright',
              required = True,
              metavar  = 'TEXT',
              help     = 'The copyright of the segment, such as "Copyright 2026 A Person", '
                         'which new items of the peer take.')
@click.option('--license',
              'text_license',
              required = True,
              metavar  = 'TEXT',
              help     = 'The license of the segment, as an SPDX expression, which new items '
                         'of the peer take.')
@OPTION_ROOT
def init(name:           str,
         title:          str,
         brief:          str,
         text_copyright: str,
         text_license:   str,
         root:           pathlib.Path) -> None:
    """
    Write the segment item of a new peer, segment_NAME, which consumes
    the newest release of the tree that this cctool reads.

    NAME is in lower case words joined by underscores, such as
    cc_patrol. The tree is that of the installed package when cctool was
    installed from a release, and the checkout it runs from when not.
    The command covers what follows the install of cctool: it writes no
    dependency on a release, and commits nothing. The exit status is 2
    when nothing can be written.

    """

    try:
        relative = cctool.edit.peer.init(root.resolve(), name, title, brief,
                                         (text_copyright, text_license))
    except cctool.edit.peer.ErrorPeer as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    click.echo('Wrote {file}'.format(file = relative))


# -----------------------------------------------------------------------------
@peer.command()
@OPTION_ROOT
def status(root: pathlib.Path) -> None:
    """
    Report the release that each segment item of the tree pins.

    Each line names the segment, the release it consumes, the segment
    that holds that release, its newest release, and whether it is read
    from an installed release or a checkout. The exit status is 1 when
    a segment pins a release that no tree read holds, or one older than
    the newest, and 2 when the tree holds no segment that consumes.

    """

    list_row = cctool.edit.peer.status(root.resolve())

    if not list_row:
        click.echo('The tree holds no segment item that consumes a release.', err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    is_behind = False
    for (id_self, release, segment, newest, place) in list_row:
        if not segment:
            is_behind = True
            click.echo('{id} pins {release}, which no tree read holds.'.format(
                           id = id_self, release = release))
            continue
        is_behind = is_behind or release != newest
        click.echo('{id} pins {release} of {segment}, read from a {place}; the newest is '
                   '{newest}.'.format(id      = id_self,
                                      release = release,
                                      segment = segment,
                                      place   = place,
                                      newest  = newest))

    sys.exit(cctool.cli.group.EXIT_NONCONFORMITY if is_behind else cctool.cli.group.EXIT_OK)
