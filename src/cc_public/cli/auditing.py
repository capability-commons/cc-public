"""
---

id_self:                pym_cc_public.cli.auditing
guid_self:              pym_51616bc93b834e85bb4e948a54ef33d2
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Auditing commands
brief:                  |
                        The command that checks commits already made.
description:            |
                        This module holds the history group and its
                        check command, which checks each commit of a
                        range, or of what a push would send, as the
                        commit hooks would, and with --gate checks,
                        lints and tests the newest content too. The
                        pre-push hook runs it, and it is the check of
                        record: the commit hooks give early feedback,
                        and can be skipped.
usage:                  |
                        cctool history check [RANGE] [--gate]
                        [--pre-push REMOTE]
relation:               []

...
"""


import pathlib
import sys

import click

import cc_public.cli.group
import cc_public.commit.history
import cc_public.gate.gate
import cc_public.graph.datalog


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def history() -> None:
    """
    Check commits already made.

    """


# -----------------------------------------------------------------------------
@history.command()
@click.argument('list_arg', metavar = 'RANGE', nargs = -1)
@click.option('--pre-push', 'remote',
              default = None,
              metavar = 'REMOTE',
              help    = 'Check what a push to REMOTE would send, from the lines git gives a '
                        'pre-push hook on stdin, in place of RANGE.')
@click.option('--gate', 'is_gate',
              is_flag = True,
              help    = 'Also check, lint and test the content of the newest commit, or of '
                        'each ref a push updates.')
@click.option('--root',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository. Defaults to the working directory.')
def check(list_arg: tuple[str, ...], remote: str | None, is_gate: bool, root: pathlib.Path) -> None:
    """
    Check each commit in RANGE, oldest first, however it was made.

    RANGE is what git rev-list takes, such as origin/main..HEAD, and is
    HEAD, the whole history, if left out. Each commit is checked as the
    commit-msg hook checks one: its message against sch_commit as its
    own tree holds it, and its change against its first parent. A
    commit item whose id another commit's item has, as a cherry-pick
    makes, is reported too. The exit status is 1 when any check fails.

    """

    root = root.resolve()
    try:
        if remote is not None:
            (list_commit, list_tip) = cc_public.commit.history.pushed(root, remote,
                                                                       sys.stdin.read())
        else:
            list_commit = cc_public.commit.history.commits(root, list(list_arg) or ['HEAD'])
            list_tip    = list_commit[-1:]
        list_found = _found(root, list_commit)
        if is_gate:
            list_found += _gated(root, list_tip)
    except (cc_public.gate.gate.ErrorGate, cc_public.graph.datalog.ErrorDatalog) as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    for found in list_found:
        click.echo(found)
    click.echo('{count} {noun} checked, {verdict}.'.format(
                   count   = len(list_commit),
                   noun    = 'commit' if len(list_commit) == 1 else 'commits',
                   verdict = 'with failures' if list_found else 'all passed'))

    sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY if list_found
             else cc_public.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
def _found(root: pathlib.Path, list_commit: list[str]) -> list[str]:
    """
    Return a line for each failure of each commit of list_commit, and
    for each commit id held by more than one commit.

    """

    list_found = []

    for commit in list_commit:
        head = cc_public.commit.history.short(root, commit)
        list_found += ['{head}: {found}'.format(head = head, found = found)
                       for found in cc_public.commit.history.check(root, commit)]

    for (id_item, list_holder) in cc_public.commit.history.duplicates(root, list_commit):
        list_found.append('{id} is the id of the items of more than one commit: {list}'.format(
            id = id_item, list = ', '.join(holder[:cc_public.commit.history.LENGTH_SHORT]
                                           for holder in list_holder)))

    return list_found


# -----------------------------------------------------------------------------
def _gated(root: pathlib.Path, list_tip: list[str]) -> list[str]:
    """
    Return the output and verdict of each stage of the gate that fails
    for the content of a commit of list_tip.

    """

    list_found = []

    for tip in list_tip:
        head = cc_public.commit.history.short(root, tip)
        for (name, is_passed, output) in cc_public.gate.gate.gate(root, rev = tip):
            if not is_passed:
                list_found.append('{head}: {output}\n{name}: failed'.format(
                                      head = head, output = output.rstrip('\n'), name = name))

    return list_found
