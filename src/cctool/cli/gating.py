"""
---

id_self:                pym_cctool.cli.gating
guid_self:              pym_22885ee830284cb0a7860549fd984b4e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gating commands
brief:                  |
                        The commands that gate a commit and sum up the
                        times of the gate.
description:            |
                        This module holds the gate command, which runs
                        the gate over the staged content of a
                        repository and prints the verdict of each
                        stage, and the output of each that fails, and
                        the timing command, which sums up the log of
                        timings that each run of the gate appends to.
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.gate.coverage
import cctool.gate.gate
import cctool.gate.timing
import cctool.graph.logic


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
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
    All the tests run when code is staged: something under src/ or
    .githooks/, or a change to pyproject.toml or pixi.lock. When only
    data is staged, only the tests marked reads_data run, and none run
    when only decisions are staged. They leave out the tests marked
    slow, which pixi run test runs, and those marked prepush, which the
    gate of a push runs.
    The check keeps the layout and schema verdicts of
    each file in a store in the git directory, which every worktree
    shares. The exit status is 1 when any stage fails, and 2 when the
    gate cannot run.

    """

    try:
        root        = root.resolve()
        tuple_stage = cctool.gate.gate.stages(root)
        list_result = cctool.gate.gate.gate(root, tuple_stage)
    except cctool.gate.gate.ErrorGate as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for (name, is_passed, output) in list_result:
        if not is_passed:
            click.echo(output.rstrip('\n'))
        click.echo('{name}: {verdict}'.format(name    = name,
                                              verdict = 'passed' if is_passed else 'failed'))

    if len(tuple_stage) < len(cctool.gate.gate.TUPLE_STAGE):
        click.echo('{name}: skipped, as only decisions are staged'.format(
                       name = cctool.gate.gate.NAME_TEST))

    sys.exit(cctool.cli.group.EXIT_OK if all(row[1] for row in list_result)
             else cctool.cli.group.EXIT_NONCONFORMITY)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.option('--data', 'path_data',
              metavar = 'FILEPATH',
              default = None,
              type    = click.Path(dir_okay = False, path_type = pathlib.Path),
              help    = 'The data that coverage run wrote. Defaults to .coverage in the '
                        'repository.')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository whose tests ran. Defaults to the working '
                        'directory.')
def coverage(path_data: pathlib.Path | None, root: pathlib.Path) -> None:
    """
    Check the coverage of each source file against its maturity.

    The tests must first have run under coverage run --branch, as pixi
    run coverage runs them overnight. A source file whose lines or
    branches are covered less than the floor that its maturity level,
    or a lower one, sets is reported, and one the run did not measure
    is covered by none. Nothing measured is kept. The exit status is 1
    when a file is below its floor, and 2 when the coverage cannot be
    read.

    """

    root = root.resolve()
    try:
        list_line = cctool.gate.coverage.check(
                        root, path_data or root / cctool.gate.coverage.FILE_DATA)
    except (cctool.gate.coverage.ErrorCoverage, cctool.graph.logic.ErrorLogic) as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for line in list_line:
        click.echo(line)
    sys.exit(cctool.cli.group.EXIT_NONCONFORMITY if list_line else cctool.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.option('--runs', 'count_run',
              default      = cctool.gate.timing.COUNT_RUN,
              show_default = True,
              type         = click.IntRange(min = 1),
              help         = 'How many of the newest runs of the gate to sum up.')
@click.option('--tests', 'count_test',
              default      = cctool.gate.timing.COUNT_TEST,
              show_default = True,
              type         = click.IntRange(min = 0),
              help         = 'How many of the slowest tests to name.')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The repository whose gate was timed. Defaults to the working '
                        'directory.')
def timing(count_run: int, count_test: int, root: pathlib.Path) -> None:
    """
    Sum up the timings of the newest runs of the gate.

    Each run of the gate, of a commit or of a push, appends a line for
    each stage to a log in the git directory, which every worktree
    shares and no commit records: when it started, its wall seconds,
    its outcome, the tree it gated, the host and the python, and for
    the tests the seconds of each test. This prints, as tab-separated
    columns, the mean and the most wall seconds of each stage over the
    newest runs, and the slowest tests among them.

    """

    try:
        path_log = cctool.gate.gate.timing_log(root.resolve())
    except cctool.gate.gate.ErrorGate as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    for text in cctool.gate.timing.summary(cctool.gate.timing.read(path_log),
                                           count_run, count_test):
        click.echo(text)
