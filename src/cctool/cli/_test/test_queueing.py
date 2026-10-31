"""
---

id_self:                pym_cctool.cli._test.test_queueing
guid_self:              pym_7c0e82ad22234dbbb5fe332a690d1dc9
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Queue command tests
brief:                  |
                        Tests of the queue commands as an agent and
                        the timer run them.
description:            |
                        Each test works in a small repository on dev,
                        and runs cctool queue as the command line
                        does.
edge:                   []

...
"""


import datetime
import subprocess

import click.testing

import cctool.cli.command
import cctool.gate.gate
import cctool.queue.report


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _queue(root, *list_arg):
    """
    Return the run of cctool queue with list_arg in the repository at
    root.

    """

    return click.testing.CliRunner().invoke(cctool.cli.command.main,
                                            ['queue', *list_arg, '--root', str(root)])


# -----------------------------------------------------------------------------
def _topic(root):
    """
    Check out the branch agent/topic in root, made from dev, with one
    commit.

    """

    _git(root, 'checkout', '--quiet', '-b', 'agent/topic')
    (root / 'one.txt').write_text('one\n')
    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'Add one.txt')


def test_a_submission_is_shown_by_status_and_withdrawn_by_its_branch(dev_repo):
    _topic(dev_repo)
    result = _queue(dev_repo, 'submit', 'add_one', '--agent', 'claude')
    assert result.exit_code == 0
    assert result.stdout.startswith('Submitted queue/00_candidate/agent-topic/')
    branch = result.stdout.split()[1].rstrip('.')

    result = _queue(dev_repo, 'status')
    assert result.stdout.splitlines() == ['The queue is running.',
                                          '00_candidate {key} from agent-topic'.format(
                                              key = branch.rsplit('/', 1)[1])]

    assert _queue(dev_repo, 'withdraw', branch).exit_code == 0
    assert _queue(dev_repo, 'status').stdout == 'The queue is running.\n'


def test_a_refused_submission_says_why_with_status_2(dev_repo):
    result = _queue(dev_repo, 'submit', 'nothing')
    assert result.exit_code == 2
    assert result.stderr.endswith('so there is nothing to submit.\n')


def test_a_run_without_a_key_pauses_until_resumed_and_writes_the_summary(dev_repo):
    _topic(dev_repo)
    _queue(dev_repo, 'submit', 'add_one')
    _git(dev_repo, 'checkout', '--quiet', 'dev')

    result = _queue(dev_repo, 'run', '--once')
    assert result.exit_code == 0
    assert result.stdout.startswith('The queue is paused: No signing key is set for the queue.')
    path = (cctool.gate.gate.git_dir(dev_repo) / cctool.queue.report.DIR_SUMMARY
            / datetime.datetime.now(datetime.UTC).strftime('%Y%m%d.txt'))
    assert 'The queue is paused since ' in path.read_text()

    result = _queue(dev_repo, 'run', '--once', '--resume')
    assert result.stdout.startswith('Lifted the pause of ')


def test_status_with_measures_says_there_are_none_yet(dev_repo):
    result = _queue(dev_repo, 'status', '--measures')
    assert result.stdout.splitlines()[1:] == ['submission to landing: none yet',
                                              'landing run: none yet',
                                              'attempts gone to conflict: none tried',
                                              'attempts gone to rework: none tried',
                                              'oldest ready patch: none ready']


def test_a_bundle_made_by_the_command_is_submitted_by_its_path(dev_repo, tmp_path):
    clone = tmp_path / 'remote'
    _git(tmp_path, 'clone', '--quiet', '--branch', 'dev', str(dev_repo), str(clone))
    _topic(clone)
    path   = tmp_path / 'topic.bundle'
    result = _queue(clone, 'bundle', 'add_one', '--output', str(path))
    assert result.exit_code == 0
    assert result.stdout.startswith('Bundled 1 commit into {path}:\n'.format(path = path))

    result = _queue(dev_repo, 'submit', str(path))
    assert result.exit_code == 0
    assert result.stdout.startswith('Submitted queue/00_candidate/agent-topic/')
