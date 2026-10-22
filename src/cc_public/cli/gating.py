"""
---

id_self:                pym_cc_public.cli.gating
guid_self:              pym_22885ee830284cb0a7860549fd984b4e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gating commands
brief:                  |
                        The command that gates a commit.
description:            |
                        This module holds the gate command, which runs
                        the gate over the staged content of a
                        repository and prints the verdict of each
                        stage, and the output of each that fails.
edge:                   []

...
"""


import pathlib
import sys

import click

import cc_public.cli.group
import cc_public.gate.gate


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository whose staged content is gated. Defaults to the '
                        'working directory.')
def gate(root: pathlib.Path) -> None:
    """
    Check, lint and test what a commit of the repository would record.

    The staged content is copied out, and each stage runs in the copy.
    The output of a stage that fails is printed before its verdict.
    The tests run only when code is staged: something under src/ or
    .githooks/, or a change to pyproject.toml or pixi.lock. They leave
    out the tests marked slow, which pixi run test runs, and those
    marked prepush, which the gate of a push runs.
    The check keeps the layout and schema verdicts of
    each file in a store in the git directory, which every worktree
    shares. The exit status is 1 when any stage fails, and 2 when the
    gate cannot run.

    """

    try:
        root        = root.resolve()
        tuple_stage = cc_public.gate.gate.stages(root)
        list_result = cc_public.gate.gate.gate(root, tuple_stage)
    except cc_public.gate.gate.ErrorGate as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    for (name, is_passed, output) in list_result:
        if not is_passed:
            click.echo(output.rstrip('\n'))
        click.echo('{name}: {verdict}'.format(name    = name,
                                              verdict = 'passed' if is_passed else 'failed'))

    if len(tuple_stage) < len(cc_public.gate.gate.TUPLE_STAGE):
        click.echo('{name}: skipped, as no code is staged'.format(
                       name = cc_public.gate.gate.NAME_TEST))

    sys.exit(cc_public.cli.group.EXIT_OK if all(row[1] for row in list_result)
             else cc_public.cli.group.EXIT_NONCONFORMITY)
