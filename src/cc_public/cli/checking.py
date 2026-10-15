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
                        failure, one line for each. A checker that
                        cannot run is an error, with its own exit
                        status, never a pass.
relation:               []

...
"""


import pathlib
import sys

import click

import cc_public.check.check
import cc_public.cli.group
import cc_public.graph.datalog


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--root',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to check. Defaults to the working directory.')
def check(root: pathlib.Path) -> None:
    """
    Check the tree under --root, or the working directory.

    Each failure is printed as the name of the check and the row that
    fails it. The exit status is 1 when any check fails, and 2 when
    the checks cannot be run.

    """

    try:
        failures = cc_public.check.check.check(root.resolve())
    except cc_public.graph.datalog.ErrorDatalog as error:
        click.echo('The checks could not be run: {error}'.format(error = error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    count = 0

    for (name, list_row) in failures.items():
        for row in list_row:
            click.echo('{name}: {row}'.format(name = name, row = '  '.join(row)))
            count += 1

    click.echo('{count} failures'.format(count = count))
    sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY if count
             else cc_public.cli.group.EXIT_OK)
