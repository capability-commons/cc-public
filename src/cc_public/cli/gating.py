"""
---

id_self:                pym_cc_public.cli.gating
guid_self:              pym_c781c30db1c347419bf2e2faa337d17f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gating command
brief:                  |
                        gate: the gate, run on a snapshot of the
                        working copy in a worktree of its own.
description:            |
                        Makes a commit holding what the working copy
                        holds, committed or not and tracked or not,
                        through an index of its own so that neither
                        the index nor the working copy is touched.
                        Points a worktree at that commit and runs the
                        gate task there, so that the working copy is
                        free for the length of the run. Copies back
                        the evidence the run observed, whatever it
                        observed.

                        The worktree is kept between runs and pointed
                        at each new snapshot, because what is worth
                        keeping is the environment it holds rather
                        than the files. It has an environment of its
                        own rather than sharing the working copy's:
                        pixi rewrites where the editable install
                        points on each run, so a shared environment
                        would be re-pointed by whichever run went
                        last, and two runs at once would disagree
                        about whose source they were testing.

                        The order the gate runs in is not named here.
                        This module runs the task, and the task is
                        where the order lives
                        (ddr_test_in_a_worktree).
relation:               []

...
"""


import os
import pathlib
import shutil
import subprocess
import tempfile

import click

import cc_public.cli.group


NAME_WORKTREE = '.gate'
NAME_EVIDENCE = 'evidence'
TASK          = 'gate'

MESSAGE_SNAPSHOT = 'snapshot for the gate'


# -----------------------------------------------------------------------------
class ErrorGate(Exception):
    """
    Raised where the worktree the gate runs in could not be made ready.

    Git said why, and what it said is carried rather than replaced,
    since the thing that went wrong is a repository state nobody here
    can describe better than git can.

    """


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--here', 'is_here', is_flag = True,
              help = 'Run in the working copy rather than on a snapshot of it. '
                     'What a fresh checkout wants, since it has nothing to protect.')
@cc_public.cli.group.OPTION_ROOT
def gate(is_here, list_root):
    """
    Run the gate on a snapshot of the working copy, in a worktree of its
    own, so that the working copy is free while it runs.

    The snapshot holds everything the working copy holds, committed and
    not, tracked and not. It is made through an index of its own, so
    nothing about the working copy changes. The evidence the run writes
    is brought back.

    """

    root = pathlib.Path((list_root or (pathlib.Path('.'),))[0]).resolve()

    if is_here:
        raise SystemExit(_run(['pixi', 'run', TASK], root))

    try:
        snapshot = _snapshot(root)
        worktree = _worktree(root, snapshot)
    except (OSError, ErrorGate) as err:
        cc_public.cli.group.fail(err)

    click.echo('{snapshot} in {worktree}'.format(snapshot = snapshot[:10],
                                                 worktree = worktree))

    status = _run(['pixi', 'run', '--frozen', TASK], worktree)
    _bring_back(worktree, root)

    raise SystemExit(status)


# -----------------------------------------------------------------------------
def _snapshot(root):
    """
    Return the identity of a commit holding what the working copy holds.

    Made through an index of its own, so the index and the working copy
    are untouched. Everything git is not told to ignore goes in,
    including what has never been added, because an item here is
    untracked until it is and the ones worth testing are the newest.

    """

    with tempfile.TemporaryDirectory() as dirpath:

        env = {'GIT_INDEX_FILE': str(pathlib.Path(dirpath) / 'index')}

        _git(root, ['add', '--all'], env)
        tree = _git(root, ['write-tree'], env)

        return _git(root, ['commit-tree', tree, '-p', 'HEAD',
                           '-m', MESSAGE_SNAPSHOT], env)


# -----------------------------------------------------------------------------
def _worktree(root, snapshot):
    """
    Return the worktree the gate runs in, at the snapshot given.

    One worktree, kept between runs and pointed at each new snapshot,
    because what it holds that is worth keeping is its environment. A
    worktree of its own rather than the environment of the working copy
    shared with it: pixi rewrites where the editable install points on
    every run, so a shared environment would be re-pointed by whichever
    run went last.

    """

    path = root / NAME_WORKTREE

    if (path / '.git').exists():
        # Forced, and then cleaned, because the run before this one wrote
        # its evidence and its coverage here and left them behind. What
        # git is told to ignore is left alone, which is what keeps the
        # environment.
        #
        _git(path, ['checkout', '--detach', '--force', snapshot])
        _git(path, ['clean', '--force', '-d'])
        return path

    _git(root, ['worktree', 'add', '--detach', str(path), snapshot])

    click.echo('Installing the environment of the gate worktree, once.')
    _run(['pixi', 'install'], path)

    return path


# -----------------------------------------------------------------------------
def _bring_back(worktree, root):
    """
    Copy the evidence the run observed into the working copy.

    Whatever it observed, passing or failing, because evidence records
    what was seen and not what was hoped. It is evidence of the
    snapshot, so a working copy that has moved on since will read it as
    stale, which is true.

    """

    for filepath in sorted((worktree / NAME_EVIDENCE).glob('*.yaml')):
        shutil.copy(filepath, root / NAME_EVIDENCE / filepath.name)


# -----------------------------------------------------------------------------
def _git(root, argument, env = None):
    """
    Run one git command at root and return what it printed, stripped.

    """

    done = subprocess.run(['git', '-C', str(root), *argument],
                          capture_output = True, text = True, check = False,
                          env = dict(os.environ, **(env or {})))

    if done.returncode != 0:
        raise ErrorGate('git {argument} in {root} said: {said}'.format(
                            argument = ' '.join(argument[:2]),
                            root     = root,
                            said     = (done.stderr or done.stdout).strip()))

    return done.stdout.strip()


# -----------------------------------------------------------------------------
def _run(command, cwd):
    """
    Run one command in cwd, its output going to the terminal, and return
    what it exited with.

    """

    return subprocess.run(command, cwd = str(cwd), check = False).returncode
