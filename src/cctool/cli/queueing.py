"""
---

id_self:                pym_cctool.cli.queueing
guid_self:              pym_aea7560b8032468cbef5557fad9292ba
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Queue commands
brief:                  |
                        The commands that submit work to the landing
                        queue, show how it stands, and run its daemon.
description:            |
                        This module holds the queue group: submit,
                        resubmit and withdraw, which agents and WTP
                        use to hand work to the queue; status, which
                        shows whether the queue runs and where each
                        patch stands, with its measures on request;
                        and run --once, which a systemd user timer on
                        atlas runs each minute in the main checkout.
usage:                  |
                        cctool queue submit ID_PATCH [--source REF]
                        [--thread NAME] [--agent NAME]; cctool queue
                        resubmit REF; cctool queue withdraw REF;
                        cctool queue status [--measures]; cctool queue
                        run --once [--resume]
edge:                   []

...
"""


import pathlib
import sys

import click

import cctool.cli.group
import cctool.queue.bundle
import cctool.queue.night
import cctool.queue.patch
import cctool.queue.report
import cctool.queue.run


OPTION_ROOT = click.option('--root',
                           metavar = 'DIRPATH',
                           default = '.',
                           type    = click.Path(exists    = True,
                                                file_okay = False,
                                                path_type = pathlib.Path),
                           help    = 'The repository. Defaults to the working directory.')


# -----------------------------------------------------------------------------
@cctool.cli.group.main.group()
def queue() -> None:
    """
    Submit work to the landing queue, and run it.

    """


# -----------------------------------------------------------------------------
@queue.command()
@click.argument('id_patch', metavar = 'ID_PATCH|BUNDLE')
@click.option('--source',
              metavar = 'REF',
              default = 'HEAD',
              help    = 'The tip of the work to submit. Defaults to HEAD.')
@click.option('--thread',
              metavar = 'NAME',
              default = None,
              help    = 'The thread that made the work. Defaults to the current branch, with '
                        'each slash written as a hyphen.')
@click.option('--agent',
              metavar = 'NAME',
              default = None,
              help    = 'The agent that submits the work, for the record.')
@OPTION_ROOT
def submit(id_patch: str, source: str, thread: str | None, agent: str | None,
           root: pathlib.Path) -> None:
    """
    Submit the commits that the source holds beyond dev as the patch
    ID_PATCH, and return at once.

    The patch becomes the branch queue/00_candidate/THREAD/KEY, where KEY
    is the UTC time of submission and ID_PATCH, and no test runs. Work
    built on the tip of a patch still in the queue depends on it, and
    is tried only once that patch has landed. Work that overlaps a patch
    in any other way is refused. Given a file that ends in .bundle, as
    cctool queue bundle makes, in place of ID_PATCH, the patch and its
    thread are those the bundle names, and --source and --thread are
    not used.

    """

    root = root.resolve()
    _warn_name(root, thread, source)
    if id_patch.endswith(cctool.queue.bundle.SUFFIX_BUNDLE):
        record = _step(lambda: cctool.queue.bundle.submit(root, pathlib.Path(id_patch).resolve(),
                                                          agent))
    else:
        record = _step(lambda: cctool.queue.patch.submit(root, id_patch, source, thread, agent))
    click.echo('Submitted {branch}.'.format(branch = cctool.queue.patch.branch(record)))
    if record['depends']:
        click.echo('It depends on {key}, and waits for it to land.'.format(
                       key = record['depends']['key']))


# -----------------------------------------------------------------------------
@queue.command()
@click.argument('id_patch', metavar = 'ID_PATCH')
@click.option('--source',
              metavar = 'REF',
              default = 'HEAD',
              help    = 'The tip of the work to bundle. Defaults to HEAD.')
@click.option('--thread',
              metavar = 'NAME',
              default = None,
              help    = 'The thread that made the work. Defaults to the current branch, with '
                        'each slash written as a hyphen.')
@click.option('--base',
              metavar = 'REF',
              default = 'dev',
              help    = 'The commit the bundle starts after, which the machine that runs the '
                        'queue must have.')
@click.option('--output', 'path',
              metavar = 'FILEPATH',
              default = None,
              type    = click.Path(dir_okay = False, path_type = pathlib.Path),
              help    = 'The bundle to write. Defaults to THREAD-ID_PATCH.bundle in the inbox '
                        'that git config queue.inbox names, or else beside the repository.')
@OPTION_ROOT
def bundle(id_patch: str, source: str, thread: str | None, base: str,
           path: pathlib.Path | None, root: pathlib.Path) -> None:
    """
    Write a bundle of the commits that the source holds beyond the base,
    as the patch ID_PATCH, for the landing queue on another machine.

    Use it where the queue cannot be reached, as in a remote session,
    and write the bundle to the inbox of the queue, which the daemon
    sweeps at each run and submits as cctool queue submit would. The
    bundle names the thread and the patch, and is written whole or not
    at all.

    """

    list_commit = []
    _warn_name(root.resolve(), thread, source)

    def step() -> dict:
        (written, list_made) = cctool.queue.bundle.make(root.resolve(), id_patch, source, thread,
                                                        base, path)
        list_commit.extend(list_made)
        return {'path': written}

    made = _step(step)
    click.echo('Bundled {count} {noun} into {path}:'.format(
                   count = len(list_commit),
                   noun  = 'commit' if len(list_commit) == 1 else 'commits',
                   path  = made['path']))
    for commit in list_commit:
        click.echo('  ' + commit)


# -----------------------------------------------------------------------------
@queue.command()
@click.argument('ref', metavar = 'REF')
@click.option('--source',
              metavar = 'REF',
              default = None,
              help    = 'Take the commits from this ref, such as the work branch the fix was '
                        'made on. Defaults to the branch of the patch.')
@OPTION_ROOT
def resubmit(ref: str, source: str | None, root: pathlib.Path) -> None:
    """
    Make the patch whose branch is REF a candidate again, holding the
    commits its branch now holds.

    Fix the work on the branch of a patch in conflict or rework, as its
    note says, and then resubmit it. It keeps its key, and so its age
    and its attempts.

    """

    record = _step(lambda: cctool.queue.patch.resubmit(root.resolve(), ref, source))
    click.echo('Resubmitted {branch}.'.format(branch = cctool.queue.patch.branch(record)))


# -----------------------------------------------------------------------------
@queue.command()
@click.argument('ref', metavar = 'REF')
@OPTION_ROOT
def withdraw(ref: str, root: pathlib.Path) -> None:
    """
    Take the patch whose branch is REF out of the queue.

    Its branch is deleted, and its record and the refs that keep its
    commits stay. A patch that depends on it waits, and cctool queue
    status says why.

    """

    record = _step(lambda: cctool.queue.patch.withdraw(root.resolve(), ref))
    click.echo('Withdrew {key}.'.format(key = record['key']))


# -----------------------------------------------------------------------------
@queue.command()
@click.option('--measures', 'is_measures',
              is_flag = True,
              help    = 'Also show the time from submission to landing and of a landing run, '
                        'the rates of conflict and rework, and the age of the oldest ready '
                        'patch.')
@OPTION_ROOT
def status(is_measures: bool, root: pathlib.Path) -> None:
    """
    Show whether the queue is running or paused and why, and each patch
    in it with its stage, its latest attempt, what it waits on, what
    waits on it, and the worktree that has claimed its repair.

    """

    root = root.resolve()
    for line in cctool.queue.report.status(root):
        click.echo(line)
    if is_measures:
        for line in cctool.queue.report.measures(root):
            click.echo(line)


# -----------------------------------------------------------------------------
@queue.command()
@click.option('--once', '_is_once',
              is_flag  = True,
              required = True,
              help     = 'Make one run, as the timer does each minute.')
@click.option('--resume', 'is_resume',
              is_flag = True,
              help    = 'Lift a pause first, once its cause is fixed.')
@OPTION_ROOT
def run(_is_once: bool, is_resume: bool, root: pathlib.Path) -> None:
    """
    Make one run of the daemon of the queue, in the main checkout.

    A run recovers whatever an interrupted run left, then lands each
    eligible patch in turn, oldest first, and pushes dev to the remote
    that git config queue.remote names, if any. It signs with the key
    that git config queue.signingKey names. A run that finds another
    running does nothing. A failure of the queue itself pauses it until
    a run with --resume. Each run rewrites the summary of the day in the
    git directory, for the daily review.

    """

    root = root.resolve()
    if is_resume:
        pause = cctool.queue.run.resume(root)
        if pause:
            click.echo('Lifted the pause of {time}: {reason}'.format(**pause))
    try:
        for line in cctool.queue.run.run(root, cctool.queue.run.policy(root)):
            click.echo(line)
    except cctool.queue.patch.ErrorQueue as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)
    finally:
        cctool.queue.report.write_summary(root)


# -----------------------------------------------------------------------------
@queue.command()
@click.option('--review/--no-review', 'is_review',
              default = True,
              help    = 'Review the tree with Claude Code after the tasks. Defaults to review.')
@OPTION_ROOT
def night(is_review: bool, root: pathlib.Path) -> None:
    """
    Run the overnight tasks on the tip of dev, in the main checkout, and
    move the verified branch to it if they all pass; then review the tree.

    The tasks are the slow run on every supported python, the property
    tests with many examples, coverage against the floors and the full
    check, run under the lock of the queue in a worktree of the night's
    own. Each night is recorded in the git directory, and its outcome is
    a gate result of the commit tested. The review runs Claude Code
    headless in a worktree of its own, which records its findings as
    annotations and submits them to the queue. The summary of the day
    shows the night.

    """

    root   = root.resolve()
    policy = cctool.queue.night.night(root)
    if not is_review:
        policy = cctool.queue.night.Night(remote = policy.remote, review = None)
    try:
        for line in cctool.queue.night.run(root, policy):
            click.echo(line)
    finally:
        cctool.queue.report.write_summary(root)


# -----------------------------------------------------------------------------
def _warn_name(root: pathlib.Path, thread: str | None, source: str) -> None:
    """
    Warn, if the thread is to be read from the current branch, that the
    branch is not named work/THREAD/TOPIC, and say what thread is read.

    """

    branch = cctool.queue.patch.try_git(root, 'branch', '--show-current').stdout.strip()
    if thread or source != 'HEAD' or not branch or cctool.queue.patch.is_work(branch):
        return
    click.echo('{branch} is not named work/THREAD/TOPIC, so the thread is taken to be {thread}. '
               'Name a branch of work in progress work/THREAD/TOPIC.'.format(
                   branch = branch, thread = cctool.queue.patch.thread_of(branch)), err = True)


# -----------------------------------------------------------------------------
def _step(step) -> dict:
    """
    Return what step returns, or print why the queue refused it and exit
    with status 2.

    """

    try:
        return step()
    except cctool.queue.patch.ErrorQueue as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)
