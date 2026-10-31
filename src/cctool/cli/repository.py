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
                        The command that bundles commits for the
                        machine that runs the landing queue.
description:            |
                        This module holds the repo group, whose bundle
                        command runs the step of
                        pym_cctool.commit.repo. A step that cannot be
                        taken says why, with exit status 2. Only the
                        landing queue moves dev, so the group has no
                        command that lands, signs or pushes.
usage:                  |
                        cctool repo bundle BRANCH [--base REF]
                        [--output FILEPATH]
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


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
def repo() -> None:
    """
    Bundle commits for the machine that runs the landing queue.

    """


# -----------------------------------------------------------------------------
@repo.command()
@click.argument('branch', metavar = 'BRANCH')
@click.option('--base',
              metavar = 'REF',
              default = 'dev',
              help    = 'The commit the bundle starts after, which the machine it goes to '
                        'must have.')
@click.option('--output', 'path',
              metavar = 'FILEPATH',
              default = None,
              type    = click.Path(dir_okay = False, path_type = pathlib.Path),
              help    = 'The bundle to write. Defaults to BRANCH.bundle beside the '
                        'repository, with each slash of BRANCH written as a hyphen.')
@OPTION_ROOT
def bundle(branch: str, base: str, path: pathlib.Path | None, root: pathlib.Path) -> None:
    """
    Write a bundle of the commits that BRANCH holds beyond the base, to
    submit to the landing queue on the machine that runs it.

    """

    root = root.resolve()
    path = path or cctool.commit.repo.bundle_path(root, branch)
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
