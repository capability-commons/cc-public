"""
---

id_self:                pym_cc_public.cli.messaging
guid_self:              pym_ae162f2110054906ad45fb63db5070c6
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Message commands
brief:                  |
                        The commands that write and check commit
                        messages.
description:            |
                        This module holds message new, which prints a
                        commit message around a new commit item, and
                        message check, which the commit-msg hook runs
                        on each message.
relation:               []

...
"""


import pathlib
import sys

import click

import cc_public.cli.group
import cc_public.commit.change
import cc_public.commit.message
import cc_public.gate.gate
import cc_public.graph.datalog


OPTION_ROOT = click.option('--root',
                           default = '.',
                           type    = click.Path(exists    = True,
                                                file_okay = False,
                                                path_type = pathlib.Path),
                           help    = 'The tree whose sch_commit is used. Defaults to the '
                                     'working directory.')


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def message() -> None:
    """
    Write and check commit messages.

    """


# -----------------------------------------------------------------------------
@message.command()
@click.argument('title')
@click.option('--brief',       required = True, help = 'What changes, and why.')
@click.option('--description', default  = None, help = 'More, where the brief is not enough.')
@OPTION_ROOT
def new(title: str, brief: str, description: str | None, root: pathlib.Path) -> None:
    """
    Print a commit message for TITLE, with a new id and guid.

    TITLE is the subject line, built from one of the templates in
    sch_commit, such as "Add OBJECT" or "Change OBJECT so that
    STATEMENT". The message is checked before it is printed. Add any
    trailers after it.

    """

    text = cc_public.commit.message.compose(title, brief, description)
    _report(cc_public.commit.message.violations(root.resolve(), text))
    click.echo(text, nl = False)


# -----------------------------------------------------------------------------
@message.command()
@click.argument('file', type = click.File('r', encoding = 'utf-8'))
@OPTION_ROOT
def check(file, root: pathlib.Path) -> None:
    """
    Check the commit message in FILE, or - for stdin, and the commit of
    the staged content that it records.

    The message is checked against sch_commit. If it passes, the commit
    is checked against the graph before and after it: nothing
    disappears or changes type unannounced, and the verb of the title
    is true of the change. The exit status is 1 when either fails.

    """

    text = file.read()
    _report(cc_public.commit.message.violations(root.resolve(), text))

    (_, item) = cc_public.commit.message.parse(text)
    try:
        failures = cc_public.commit.change.check(root.resolve(), item)
    except (cc_public.gate.gate.ErrorGate, cc_public.graph.datalog.ErrorDatalog) as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    _report(['{name}: {row}'.format(name = name, row = '  '.join(row))
             for (name, list_row) in failures.items() for row in list_row])


# -----------------------------------------------------------------------------
def _report(list_found: list[str]) -> None:
    """
    Print each way the message fails, and exit with 1 if there is any.

    """

    for found in list_found:
        click.echo(found, err = True)
    if list_found:
        sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY)
