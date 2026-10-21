"""
---

id_self:                pym_cc_public.cli.exporting
guid_self:              pym_4adabf1c358c496f81b3a5f9d5b9f065
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Exporting commands
brief:                  |
                        The commands that export the graph of data
                        items, as an Obsidian vault or as an Open
                        Knowledge Format bundle.
description:            |
                        This module holds the export group and its
                        commands: obsidian and okf. Each reads the
                        tree, makes the pages of its format, and
                        writes them to the folder it is given, which
                        must be empty unless --replace is passed.
relation:               []

...
"""


import pathlib
import sys

import click

import cc_public.cli.group
import cc_public.export.obsidian
import cc_public.export.okf
import cc_public.export.page
import cc_public.graph.item


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def export():
    """
    Export the graph of data items as pages of markdown, for other tools
    to read.

    Each item becomes one page, named by its id, in a folder for its
    type. The fields that are not prose go in the frontmatter, and the
    prose and the relations of the item are the body, with every item
    they name given as a link to its page.

    """


# -----------------------------------------------------------------------------
def _option(function):
    """
    Add the argument and options that every export command shares to
    function.

    """

    list_option = [
        click.argument('dir_out', metavar = 'DIRPATH',
                       type = click.Path(path_type = pathlib.Path)),
        click.option('--root',
                     metavar = 'DIRPATH',
                     default = '.',
                     type    = click.Path(exists    = True,
                                          file_okay = False,
                                          path_type = pathlib.Path),
                     help    = 'The tree to export. Defaults to the working directory.'),
        click.option('--replace', 'is_replace',
                     is_flag = True,
                     help    = 'Remove the pages already in DIRPATH first, and keep its other '
                               'files, such as the settings of a viewer.')]

    for option in reversed(list_option):
        function = option(function)

    return function


# -----------------------------------------------------------------------------
@export.command()
@_option
def obsidian(dir_out, root, is_replace):
    """
    Write the graph as an Obsidian vault in the folder DIRPATH.

    Each note is named by the id of its item, and shows its title. Its
    type is a tag, so the graph view can color the items by type, and
    its title is an alias, so a link can be found by either.

    \b
    Examples:
      cctool export obsidian ../vault
      cctool export obsidian ../vault --replace

    """

    _write(cc_public.export.obsidian.pages, dir_out, root, is_replace)


# -----------------------------------------------------------------------------
@export.command()
@_option
def okf(dir_out, root, is_replace):
    """
    Write the graph as an Open Knowledge Format bundle in the folder DIRPATH.

    The bundle follows OKF version 0.2: each concept has the name of
    the type of its item as its type, and its brief as its description,
    and links to other concepts from the root of the bundle. An index
    in the root lists the folders, and one in each folder lists its
    concepts.

    \b
    Examples:
      cctool export okf ../bundle
      cctool export okf ../bundle --replace

    """

    _write(cc_public.export.okf.pages, dir_out, root, is_replace)


# -----------------------------------------------------------------------------
def _write(pages, dir_out, root, is_replace):
    """
    Write the pages that pages makes of the items of the tree under
    root to dir_out, and say how many were written.

    """

    map_text = pages(cc_public.graph.item.read(root.resolve()))

    try:
        cc_public.export.page.write(dir_out, map_text, is_replace)
    except cc_public.export.page.ErrorExport as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    click.echo('{count} pages written to {dir}.'.format(count = len(map_text), dir = dir_out))
