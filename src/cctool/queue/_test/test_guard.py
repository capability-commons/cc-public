"""
---

id_self:                pym_cctool.queue._test.test_guard
guid_self:              pym_e504fe94c4d944889272cbdc54e10511
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Main checkout guard tests
brief:                  |
                        Tests that the queue runs only while the main
                        checkout is on dev, and that leaving dev is
                        warned of.
description:            |
                        Each test works in a small repository on dev,
                        as the main checkout, and runs the run script
                        of the service or checks out another branch
                        with the hooks of the repository.
edge:                   []

...
"""


import json
import os
import subprocess

import cctool.conftest
import cctool.queue.patch
import cctool.queue.run


# The script that cctool-queue.service runs, and the hook that warns when
# the main checkout leaves dev.
#
PATH_RUN  = cctool.conftest.DIR_REPO / 'systemd' / 'cctool-queue-run'
PATH_HOOK = cctool.conftest.DIR_REPO / '.githooks' / 'post-checkout'


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return how it went.

    """

    return subprocess.run(['git', *list_arg], cwd = root, check = True, capture_output = True,
                          text = True)


# -----------------------------------------------------------------------------
def _run(root, tmp_path):
    """
    Return how the run script went in root, with a stand-in for pixi that
    prints what it was asked to run.

    """

    dir_bin = tmp_path / 'bin'
    dir_bin.mkdir(exist_ok = True)
    pixi = dir_bin / 'pixi'
    pixi.write_text('#!/bin/sh\necho "pixi $*"\n')
    pixi.chmod(0o755)
    env = {**os.environ, 'PATH': '{bin}{sep}{path}'.format(bin = dir_bin, sep = os.pathsep,
                                                          path = os.environ['PATH'])}
    return subprocess.run([str(PATH_RUN)], cwd = root, env = env, capture_output = True,
                          text = True, check = False)


def test_the_run_script_runs_the_queue_while_the_main_checkout_is_on_dev(dev_repo, tmp_path):
    done = _run(dev_repo, tmp_path)
    assert (done.returncode, done.stdout) == (0, 'pixi run --locked cctool queue run --once\n')
    assert cctool.queue.run.paused(dev_repo) is None


def test_the_run_script_pauses_the_queue_while_the_main_checkout_is_elsewhere(dev_repo,
                                                                              tmp_path):
    _git(dev_repo, 'checkout', '--quiet', '-b', 'trial')
    done = _run(dev_repo, tmp_path)
    assert (done.returncode, done.stdout) == (0, '')
    assert done.stderr == 'The queue is paused: the main checkout is on trial, not dev.\n'
    pause = cctool.queue.run.paused(dev_repo)
    assert pause['reason'].startswith('The main checkout is on trial, not dev. Run git '
                                      'checkout dev there')

    path = cctool.queue.patch.directory(dev_repo) / cctool.queue.run.FILE_PAUSE
    path.write_text(json.dumps({'time': 'earlier', 'reason': 'kept'}))
    _run(dev_repo, tmp_path)
    assert cctool.queue.run.paused(dev_repo) == {'time': 'earlier', 'reason': 'kept'}


def test_the_hook_warns_when_the_main_checkout_leaves_dev_and_not_in_a_worktree(dev_repo,
                                                                               tmp_path):
    _git(dev_repo, 'config', 'core.hooksPath', str(PATH_HOOK.parent))
    _git(dev_repo, 'branch', 'trial')
    done = _git(dev_repo, 'checkout', '--quiet', 'trial')
    assert 'The main checkout has left dev for trial.' in done.stderr

    done = _git(dev_repo, 'checkout', '--quiet', 'dev')
    assert 'left dev' not in done.stderr
    done = _git(dev_repo, 'worktree', 'add', '--quiet', str(tmp_path / 'topic'), 'trial')
    assert 'left dev' not in done.stderr
