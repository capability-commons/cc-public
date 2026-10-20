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
import cc_public.graph.logic


OPTION_ROOT = click.option('--root',
                           metavar = 'DIRPATH',
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
@click.argument('file', metavar = 'FILEPATH', type = click.File('r', encoding = 'utf-8'))
@OPTION_ROOT
def check(file, root: pathlib.Path) -> None:
    """
    Check the commit message in FILEPATH, or - for stdin, and the commit of
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
    except (cc_public.gate.gate.ErrorGate, cc_public.graph.logic.ErrorLogic) as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    _report(cc_public.commit.change.described(failures))


# -----------------------------------------------------------------------------
@message.command()
@click.argument('path', metavar = 'FILEPATH', type = click.Path(dir_okay  = False,
                                                            path_type = pathlib.Path))
@OPTION_ROOT
def draft(path: pathlib.Path, root: pathlib.Path) -> None:
    """
    Make the message that git drafted in FILEPATH for a merge or a revert
    into one that conforms, in place, for a commit of what is staged.
    Any other message is left as it is.

    Run by the prepare-commit-msg hook. A draft that cannot be made,
    for any reason, is reported and the message left as it is, so that
    the commit-msg hook says what is wrong. The hook runs for a merge
    or a revert that --no-verify does not skip, so it must never stop
    one.

    """

    text = path.read_text(encoding = 'utf-8')
    try:
        drafted = cc_public.commit.message.draft(root.resolve(), text)
    except Exception as error:
        click.echo('No draft: {error}'.format(error = error), err = True)
        return

    if drafted != text:
        path.write_text(drafted, encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _report(list_found: list[str]) -> None:
    """
    Print each way the message fails, and exit with 1 if there is any.

    """

    for found in list_found:
        click.echo(found, err = True)
    if list_found:
        sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY)
