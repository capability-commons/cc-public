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
import cc_public.graph.logic


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

    Each failure is printed as its file and line, where it has them,
    the name of the check, and a sentence that says what is wrong. The
    rows of a check are followed once by what to do about them. Advice
    is printed first, as "advice:" and then the same, and is not a
    failure. The exit status is 1 when any check fails, and 2 when the
    checks cannot be run.

    """

    try:
        (failures, advice) = cc_public.check.check.review(root.resolve())
    except cc_public.graph.logic.ErrorLogic as error:
        click.echo('The checks could not be run: {error}'.format(error = error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    map_column  = cc_public.check.check.columns()
    map_wording = cc_public.check.check.wording()

    for line in cc_public.graph.logic.described(advice, map_column, map_wording, 'advice: '):
        click.echo(line)
    for line in cc_public.graph.logic.described(failures, map_column, map_wording):
        click.echo(line)

    count = sum(len(list_row) for list_row in failures.values())
    click.echo('{count} failures'.format(count = count))
    sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY if count
             else cc_public.cli.group.EXIT_OK)
