"""
---

id_self:                pym_cctool.cli.repository
guid_self:              pym_f54b17babc8342de884707e026d535ff
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Repository commands
brief:                  |
                        The commands for the daily steps of the
                        maintainer: land, sign, push and bundle.
description:            |
                        This module holds the repo group, whose
                        commands run the steps of
                        pym_cctool.commit.repo, so that the maintainer
                        need not remember the git commands each takes.
                        A step that cannot be taken says why, with
                        exit status 2, and leaves the branch where it
                        was.
usage:                  |
                        cctool repo land BUNDLE [--branch NAME]
                        [--reset-author] cctool repo sign [--since
                        REF] [--reset-author] cctool repo push
                        [--remote NAME] cctool repo bundle BRANCH
                        [--base REF] [--output FILEPATH]
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.commit.repo
import cctool.gate.gate
import cctool.graph.logic


OPTION_ROOT = click.option('--root',
                           metavar = 'DIRPATH',
                           default = '.',
                           type    = click.Path(exists    = True,
                                                file_okay = False,
                                                path_type = pathlib.Path),
                           help    = 'The repository. Defaults to the working directory.')

OPTION_RESET_AUTHOR = click.option('--reset-author',
                                   is_flag = True,
                                   help    = 'Make whoever runs this the author of each commit '
                                             'too, as when an agent committed under its own '
                                             'name.')


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
def repo() -> None:
    """
    Land, sign, push and bundle commits.

    """


# -----------------------------------------------------------------------------
@repo.command()
@click.argument('path', metavar = 'BUNDLE', type = click.Path(exists    = True,
                                                              dir_okay  = False,
                                                              path_type = pathlib.Path))
@click.option('--branch',
              metavar = 'NAME',
              default = None,
              help    = 'The branch of the bundle to land, if it holds more than one.')
@OPTION_RESET_AUTHOR
@OPTION_ROOT
def land(path: pathlib.Path, branch: str | None, reset_author: bool, root: pathlib.Path) -> None:
    """
    Land the commits of the branch that BUNDLE holds on the current
    branch.

    The commits are replayed onto the current branch, each signed as it
    is replayed, and checked as cctool history check checks them. Only
    if all of that succeeds is the current branch moved forward to
    them. With --reset-author, whoever lands them also becomes their
    author. Push them with cctool repo push.

    """

    _report('Landed', lambda: cctool.commit.repo.land(root.resolve(), path.resolve(), branch,
                                                             reset_author))


# -----------------------------------------------------------------------------
@repo.command()
@click.option('--since',
              metavar = 'REF',
              default = None,
              help    = 'Sign the commits after REF. Defaults to the branch of the same name '
                        'on origin, so that the commits not yet pushed are signed.')
@OPTION_RESET_AUTHOR
@OPTION_ROOT
def sign(since: str | None, reset_author: bool, root: pathlib.Path) -> None:
    """
    Sign each commit of the current branch that is not yet pushed.

    Each is replayed in place with a signature, so each gets a new
    hash. Another branch that ended at one of them would be left naming
    the unsigned copy, so it is removed. With --reset-author, whoever
    signs them also becomes their author.

    """

    list_branch = []

    def step() -> list[str]:
        (list_commit, list_removed) = cctool.commit.repo.sign(root.resolve(), since,
                                                               reset_author)
        list_branch.extend(list_removed)
        return list_commit

    _report('Signed', step)
    for name in list_branch:
        click.echo('Removed the branch {name}, which ended at a commit now signed.'.format(
                                                                                name = name))


# -----------------------------------------------------------------------------
@repo.command()
@click.option('--remote',
              metavar = 'NAME',
              default = 'origin',
              help    = 'The remote to push to.')
@OPTION_ROOT
def push(remote: str, root: pathlib.Path) -> None:
    """
    Push the current branch to the branch of the same name on the
    remote, once each commit not yet pushed is signed.

    The pre-push hook then checks what is pushed, as it does for any
    push. The exit status is that of git push.

    """

    try:
        status = cctool.commit.repo.push(root.resolve(), remote)
    except cctool.commit.repo.ErrorRepo as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)
    sys.exit(status)


# -----------------------------------------------------------------------------
@repo.command()
@click.argument('branch', metavar = 'BRANCH')
@click.option('--base',
              metavar = 'REF',
              default = 'dev',
              help    = 'The commit the bundle starts after, which whoever lands it must '
                        'have.')
@click.option('--output', 'path',
              metavar = 'FILEPATH',
              default = None,
              type    = click.Path(dir_okay = False, path_type = pathlib.Path),
              help    = 'The bundle to write. Defaults to BRANCH.bundle beside the '
                        'repository.')
@OPTION_ROOT
def bundle(branch: str, base: str, path: pathlib.Path | None, root: pathlib.Path) -> None:
    """
    Write a bundle of the commits that BRANCH holds beyond the base, for
    cctool repo land to land elsewhere.

    """

    root = root.resolve()
    path = path or root.parent / (branch + '.bundle')
    _report('Bundled into {path}'.format(path = path),
            lambda: cctool.commit.repo.bundle(root, branch, base, path))


# -----------------------------------------------------------------------------
def _report(verb: str, step) -> None:
    """
    Take step, and print the commits it returns after verb, or why it
    could not be taken, with exit status 2.

    """

    try:
        list_commit = step()
    except (cctool.commit.repo.ErrorRepo,
            cctool.gate.gate.ErrorGate,
            cctool.graph.logic.ErrorLogic) as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    click.echo('{verb} {count} {noun}{colon}'.format(
                   verb  = verb,
                   count = len(list_commit),
                   noun  = 'commit' if len(list_commit) == 1 else 'commits',
                   colon = ':' if list_commit else '.'))
    for commit in list_commit:
        click.echo('  ' + commit)
