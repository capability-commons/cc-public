"""
---

id_self:                pym_cctool.cli.checking
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
                        status, never a pass. It also holds the
                        friction command, which reports what may be
                        worth deciding about, and never fails.
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.check.check
import cctool.check.friction
import cctool.cli.group
import cctool.graph.logic


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.option('--root',
              metavar = 'DIRPATH',
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
    failure. A row about the trees that the segment of the tree
    consumes is printed next, as "notice:" and then the same, and is
    not a failure either. The exit status is 1 when any check fails,
    and 2 when the checks cannot be run.

    """

    try:
        (failures, advice, notices) = cctool.check.check.review(root.resolve())
    except cctool.graph.logic.ErrorLogic as error:
        click.echo('The checks could not be run: {error}'.format(error = error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    map_column  = cctool.check.check.columns()
    map_wording = cctool.check.check.wording()

    for line in cctool.graph.logic.described(advice, map_column, map_wording, 'advice: '):
        click.echo(line)
    for line in cctool.graph.logic.described(notices, map_column, map_wording, 'notice: '):
        click.echo(line)

    for line in cctool.graph.logic.described(failures, map_column, map_wording):
        click.echo(line)

    count  = sum(len(list_row) for list_row in failures.values())
    notice = sum(len(list_row) for list_row in notices.values())
    if notice:
        click.echo('{count} notices about the trees it consumes'.format(count = notice))
    click.echo('{count} failures'.format(count = count))
    sys.exit(cctool.cli.group.EXIT_NONCONFORMITY if count
             else cctool.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to read. Defaults to the working directory.')
def friction(root: pathlib.Path) -> None:
    """
    Report the signals of friction in the tree under --root.

    Each signal is a place where something may be bent to fit an
    earlier choice, or may be waiting for a decision: a term two
    concepts share, a rule that needs an exception, a decision with no
    ruling, and the count of each kind of advice. Each row is printed as
    cctool check prints a failure, then a count of each signal. The
    report is read by the scheduled reviews. It never fails: the exit
    status is 0, or 2 when the rules cannot be run.

    """

    try:
        report = cctool.check.friction.friction(root.resolve())
    except cctool.graph.logic.ErrorLogic as error:
        click.echo('The friction report could not be made: {error}'.format(error = error),
                   err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for line in cctool.graph.logic.described(report,
                                             cctool.check.friction.columns(),
                                             cctool.check.friction.wording()):
        click.echo(line)

    for (name, list_row) in report.items():
        click.echo('{name}: {count}'.format(name = name, count = len(list_row)))

    sys.exit(cctool.cli.group.EXIT_OK)
