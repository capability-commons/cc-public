"""
---

id_self:                pym_cctool.cli.messaging
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
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.commit.change
import cctool.commit.message
import cctool.gate.gate
import cctool.graph.extract
import cctool.graph.logic


OPTION_ROOT = click.option('--root',
                           metavar = 'DIRPATH',
                           default = '.',
                           type    = click.Path(exists    = True,
                                                file_okay = False,
                                                path_type = pathlib.Path),
                           help    = 'The tree whose sch_commit is used. Defaults to the '
                                     'working directory.')

# A title that fits no template is reported with this sentence, and
# then the templates are listed, from the description of the title in
# sch_commit, whose second paragraph names them.
#
PREFIX_TEMPLATE = 'The title is not built from a template'
KEY_TEMPLATE    = ('allOf', 'properties', 'title', 'description')


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
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
    trailers after it. A message that fails sch_commit is not printed:
    each way it fails is, with the templates if the title fits none,
    and the exit status is 2.

    """

    text       = cctool.commit.message.compose(title, brief, description)
    list_found = cctool.commit.message.violations(root.resolve(), text)

    for found in list_found:
        click.echo(found, err = True)
    if any(found.startswith(PREFIX_TEMPLATE) for found in list_found):
        templates = _templates(root.resolve())
        if templates:
            click.echo('Build the title from one of these templates, with no period: '
                       '{templates}'.format(templates = templates), err = True)
    if list_found:
        sys.exit(cctool.cli.group.EXIT_ERROR)

    click.echo(text, nl = False)


# -----------------------------------------------------------------------------
def _templates(root: pathlib.Path) -> str | None:
    """
    Return the templates that a title is built from, as the description
    of the title in sch_commit in the tree at root names them, or None
    if they cannot be found.

    """

    (key_all, key_property, key_title, key_description) = KEY_TEMPLATE

    for (document, _) in cctool.graph.extract.documents(root).values():
        if not (isinstance(document, dict)
                and document.get('id_self') == cctool.commit.message.ID_SCHEMA):
            continue
        for part in document.get(key_all) or []:
            if not isinstance(part, dict):
                continue
            title          = (part.get(key_property) or {}).get(key_title) or {}
            list_paragraph = str(title.get(key_description, '')).split('\n\n')
            if len(list_paragraph) > 1:
                return ' '.join(list_paragraph[1].split())

    return None


# -----------------------------------------------------------------------------
@message.command()
@click.argument('file', metavar = 'FILEPATH', type = click.File('r', encoding = 'utf-8'))
@click.option('--author',
              metavar = 'IDENT',
              default = None,
              help    = 'The author of the commit, as git var GIT_AUTHOR_IDENT gives it. '
                        'If given, it must be the git_author of a team member.')
@OPTION_ROOT
def check(file, author: str | None, root: pathlib.Path) -> None:
    """
    Check the commit message in FILEPATH, or - for stdin, and the commit of
    the staged content that it records.

    The message is checked against sch_commit, and the author, if
    given, against the git_author of each member of reg_team_member.
    If they pass, the commit is checked against the graph before and
    after it: nothing disappears or changes type unannounced, and the
    verb of the title is true of the change. The exit status is 1 when
    any fails.

    """

    text = file.read()
    _report(cctool.commit.message.violations(root.resolve(), text)
            + ([] if author is None
               else cctool.commit.message.author_violations(root.resolve(), author)))

    (_, item) = cctool.commit.message.parse(text)
    try:
        failures = cctool.commit.change.check(root.resolve(), item)
    except (cctool.gate.gate.ErrorGate, cctool.graph.logic.ErrorLogic) as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    _report(cctool.commit.change.described(failures))


# -----------------------------------------------------------------------------
@message.command()
@click.argument('path', metavar = 'FILEPATH', type = click.Path(exists    = True,
                                                            dir_okay  = False,
                                                            path_type = pathlib.Path))
@OPTION_ROOT
def draft(path: pathlib.Path, root: pathlib.Path) -> None:
    """
    Make the message that git drafted in FILEPATH for a merge or a revert
    into one that conforms, in place, for a commit of what is staged.
    Any other message is left as it is.

    Run by the prepare-commit-msg hook. A draft that cannot be made,
    for any reason, is reported and the message left as it is, so that
    the commit-msg hook says what is wrong. A merge or a revert runs
    the hook even with the flag --no-verify, so the hook must never
    stop one, and it succeeds whatever this command does. A FILEPATH
    that does not exist is an error, with exit status 2.

    """

    try:
        text    = path.read_text(encoding = 'utf-8')
        drafted = cctool.commit.message.draft(root.resolve(), text)
        if drafted != text:
            path.write_text(drafted, encoding = 'utf-8')
    except Exception as error:
        click.echo('No draft: {error}'.format(error = error), err = True)


# -----------------------------------------------------------------------------
def _report(list_found: list[str]) -> None:
    """
    Print each way the message fails, and exit with 1 if there is any.

    """

    for found in list_found:
        click.echo(found, err = True)
    if list_found:
        sys.exit(cctool.cli.group.EXIT_NONCONFORMITY)
