"""
---

id_self:                pym_cctool.cli.releasing
guid_self:              pym_f48aaee9e5d54ed08822e01d2acd618e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Releasing commands
brief:                  |
                        The commands that propose a release and check
                        a commit before it is tagged.
description:            |
                        This module holds the release group: prepare
                        writes the release item and the version module
                        and prints the bump, the renames, the removals
                        and the commits since the last release, and
                        check says whether a commit may be tagged as a
                        release. Neither commits, tags or pushes.
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.edit.edit
import cctool.gate.gate
import cctool.graph.logic
import cctool.release.release


# What each level of bump says of the change since the last release.
#
MAP_LEVEL_TEXT  = {cctool.release.release.LEVEL_MAJOR: 'a supported item is removed or renamed',
                   cctool.release.release.LEVEL_MINOR: 'a supported item is added',
                   cctool.release.release.LEVEL_PATCH: 'no supported item is added, removed or '
                                                       'renamed'}
TUPLE_ERROR     = (cctool.release.release.ErrorRelease,
                   cctool.edit.edit.ErrorEdit,
                   cctool.gate.gate.ErrorGate,
                   cctool.graph.logic.ErrorLogic)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
def release() -> None:
    """
    Propose a release, and check a commit before it is tagged.

    """


# -----------------------------------------------------------------------------
@release.command()
@click.option('--brief',
              required = True,
              metavar  = 'TEXT',
              help     = 'Why the release is made, as the brief of the release item.')
@click.option('--maturity',
              required = True,
              metavar  = 'ID',
              help     = 'The maturity level the release is for, such as maturity_100. '
                         'cctool release check refuses a release that ships a source file '
                         'below it.')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository. Defaults to the working directory.')
def prepare(brief: str, maturity: str, root: pathlib.Path) -> None:
    """
    Write the release item and the version module for a release of HEAD.

    The version is that of the last release tag, vX.Y.Z, bumped by
    what the commits since it change: major if one removes or renames a
    supported item, minor if one adds one, and patch otherwise. Before
    1.0.0 each level bumps the part below it. A supported item is a schema,
    a register or a register entry, such as a type or a relation. With
    no release tag, the release is the first, at the version the module
    holds. The release item records the runtime packages of pixi.lock.
    It records too the old id, new id and guid of each item renamed
    since the tag, and the maturity level the release is for. The
    renames, the removals and the commits since the tag are printed.
    Nothing is committed or tagged: commit what is written, run the
    release gate, then cctool release check, and tag the commit if the
    release is to be made. The exit status is 2 when nothing can be
    written.

    """

    try:
        result = cctool.release.release.prepare(root.resolve(), brief, maturity)
    except TUPLE_ERROR as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for line in _prepared(result):
        click.echo(line)


# -----------------------------------------------------------------------------
def _prepared(result: dict) -> list[str]:
    """
    Return the lines that say what prepare did and found.

    """

    version = result['version']
    base    = result['base']

    if base is None:
        list_line = ['Release {version}, the first: there is no release tag before '
                     'HEAD.'.format(version = version)]
    else:
        list_line = ['Release {version}, after {base}: a {level} bump, as {text}.'.format(
                         version = version,
                         base    = base,
                         level   = result['level'],
                         text    = MAP_LEVEL_TEXT[result['level']])]

    for (id_item, delta, was, _, _) in result['reason']:
        list_line.append('  {delta} {id}{was}{commit}'.format(
            delta  = delta,
            id     = id_item,
            was    = ' (was {was})'.format(was = was) if was else '',
            commit = ''.join(' {short}'.format(short = short)
                             for short in result['commit'].get(was or id_item, []))))

    list_line += ['Wrote {file}'.format(file = file) for file in result['written']]

    if base is not None:
        list_line.append('')
        list_line.append('Renamed since {base}: {count}'.format(
                             base = base, count = len(result['renamed'])))
        list_line += ['  {was} -> {id}'.format(was = was, id = id_item)
                      for (was, id_item) in result['renamed']]
        list_line.append('Removed since {base}: {count}'.format(
                             base = base, count = len(result['removed'])))
        list_line += ['  {id}'.format(id = id_item) for id_item in result['removed']]
        list_line.append('Commits since {base}: {count}'.format(
                             base = base, count = len(result['notes'])))
        list_line += ['  {short} {title}'.format(short = short, title = title)
                      for (short, title) in result['notes']]

    list_line.append('')
    list_line.append('Next: commit these files, run the release gate, then cctool release '
                     'check v{version}, and tag the commit v{version} if it is to be '
                     'released.'.format(version = version))

    return list_line


# -----------------------------------------------------------------------------
@release.command()
@click.argument('tag')
@click.argument('rev', metavar = '[REV]', default = 'HEAD')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository. Defaults to the working directory.')
def check(tag: str, rev: str, root: pathlib.Path) -> None:
    """
    Check that the commit REV may be tagged TAG, such as v1.2.3.

    The tree at REV must hold exactly one release item whose version
    is that of TAG, the version module must hold that version too, and
    the item must record the runtime packages of pixi.lock at REV and
    the renames since the last release tag before REV. The item may
    have been added by an earlier commit. REV is HEAD if left out.
    Nothing is tagged. The exit status is 1 when REV may not be tagged
    TAG, and 2 when it cannot be checked.

    """

    try:
        list_found = cctool.release.release.verify(root.resolve(), tag, rev)
    except TUPLE_ERROR as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for found in list_found:
        click.echo(found)
    click.echo('{rev} {verdict} be tagged {tag}.'.format(
                   rev     = rev,
                   verdict = 'may not' if list_found else 'may',
                   tag     = tag))

    sys.exit(cctool.cli.group.EXIT_NONCONFORMITY if list_found else cctool.cli.group.EXIT_OK)
