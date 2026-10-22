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
edge:                   []

...
"""


import json
import pathlib
import sys

import click

import cc_public.cli.group
import cc_public.commit.history
import cc_public.commit.impact
import cc_public.gate.gate
import cc_public.graph.logic


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def history() -> None:
    """
    Check commits already made.

    """


# -----------------------------------------------------------------------------
@history.command()
@click.argument('list_arg', metavar = '[RANGE]...', nargs = -1)
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
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository. Defaults to the working directory.')
def check(list_arg: tuple[str, ...], remote: str | None, is_gate: bool, root: pathlib.Path) -> None:
    """
    Check each commit in RANGE, oldest first, however it was made.

    RANGE is what git rev-list takes, such as dev..HEAD, and is
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
    except (cc_public.gate.gate.ErrorGate, cc_public.graph.logic.ErrorLogic) as error:
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


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('rev', metavar = '[REV]', default = 'HEAD')
@click.option('--staged', 'is_staged',
              is_flag = True,
              help    = 'Show what the staged content would touch as the next commit, in '
                        'place of REV.')
@click.option('--depth',
              default      = cc_public.commit.impact.DEPTH_DEFAULT,
              show_default = True,
              type         = click.IntRange(min = 1),
              help         = 'How many links from a touched item to look.')
@click.option('--direction',
              default      = 'both',
              show_default = True,
              type         = click.Choice(cc_public.commit.impact.TUPLE_DIRECTION),
              help         = 'in: the items that link to a touched one. out: those it links '
                             'to. both: either.')
@click.option('--json', 'is_json',
              is_flag = True,
              help    = 'Print JSON: the touched items and the neighbors, as lists of '
                        'objects.')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository. Defaults to the working directory.')
def impact(rev:       str,
           is_staged: bool,
           depth:     int,
           direction: str,
           is_json:   bool,
           root:      pathlib.Path) -> None:
    """
    Show what the commit REV touches, and the untouched items around it.

    Each item the commit adds, removes, renames or changes is listed,
    against the commit's first parent. An item is changed when its own
    fields change, or the source text of the code or file that holds
    it. Then each untouched item within --depth links of a touched one
    is listed, with the links that reach it. A link is an edge, a
    reference by id and guid, or one item holding another. A walk keeps
    the direction it starts in. REV is HEAD if left out.

    \b
    Examples:
      cctool impact
      cctool impact HEAD~2 --depth 2 --direction in
      cctool impact --staged --json

    """

    root = root.resolve()
    try:
        result = cc_public.commit.impact.impact(root, None if is_staged else rev, depth, direction)
    except (cc_public.gate.gate.ErrorGate, cc_public.graph.logic.ErrorLogic) as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    if is_json:
        click.echo(json.dumps(
            {'touched':   [dict(zip(TUPLE_TOUCHED, row, strict = True))
                           for row in result['touched']],
             'neighbor':  [dict(zip(TUPLE_NEIGHBOR, row, strict = True))
                           for row in result['neighbor']]}))
    else:
        for line in _impact_lines(result):
            click.echo(line)


TUPLE_TOUCHED   = ('id', 'delta', 'was', 'file', 'line')
TUPLE_NEIGHBOR  = ('id', 'depth', 'via', 'relation', 'direction', 'file', 'line')


# -----------------------------------------------------------------------------
def _impact_lines(result: cc_public.commit.impact.Impact) -> list[str]:
    """
    Return the lines that show result: each touched item, then each
    neighbor once, with each link that reaches it written as source,
    relation and target.

    """

    list_line = ['{delta:<8} {id}{was}  {file}:{line}'.format(
                     delta = delta,
                     id    = id_item,
                     was   = ' (was {was})'.format(was = was) if was else '',
                     file  = file,
                     line  = line)
                 for (id_item, delta, was, file, line) in result['touched']]
    list_line.append('{count} touched.'.format(count = len(result['touched'])))

    map_link = {}
    for (id_item, depth, via, relation, direction, file, line) in result['neighbor']:
        link = (via, relation, id_item) if direction == 'out' else (id_item, relation, via)
        map_link.setdefault((id_item, depth, file, line), []).append(' '.join(link))

    if map_link:
        list_line.append('')
    for ((id_item, depth, file, line), list_link) in map_link.items():
        list_line.append('{depth}  {id}  {file}:{line}'.format(
                             depth = depth, id = id_item, file = file, line = line))
        list_line += ['     {link}'.format(link = link) for link in list_link]
    list_line.append('{count} {noun} untouched.'.format(
                         count = len(map_link),
                         noun  = 'neighbor' if len(map_link) == 1 else 'neighbors'))

    return list_line
