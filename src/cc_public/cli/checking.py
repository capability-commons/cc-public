"""
---

id_self:                pym_cc_public.cli.checking
guid_self:              pym_18b02bd04054455a950c7ddce926c2c1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Checking commands
brief:                  |
                        The commands that check the tree.
description:            |
                        This module holds the check command, which
                        runs the checker over a tree and prints every
                        failure, one line for each.
relation:               []

...
"""


import pathlib
import sys

import click

import cc_public.check.check
import cc_public.cli.group


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('root',
                default = '.',
                type    = click.Path(exists    = True,
                                     file_okay = False,
                                     path_type = pathlib.Path))
def check(root: pathlib.Path) -> None:
    """
    Check the tree under ROOT, or the working directory.

    Each failure is printed as the name of the check and the row that
    fails it. The exit status is 1 when any check fails.

    """

    failures = cc_public.check.check.check(root.resolve())
    count    = 0

    for (name, list_row) in failures.items():
        for row in list_row:
            click.echo('{name}: {row}'.format(name = name, row = '  '.join(row)))
            count += 1

    click.echo('{count} failures'.format(count = count))
    sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY if count
             else cc_public.cli.group.EXIT_OK)
