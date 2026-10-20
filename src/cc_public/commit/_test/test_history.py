"""
---

id_self:                pym_cc_public.commit._test.test_history
guid_self:              pym_9f8b1e62c6a04c078f2f008d2ab77295
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit history tests
brief:                  |
                        Tests of checking commits already made.
description:            |
                        Each test commits a copy of the repository
                        without hooks, as a rebase, a cherry-pick or a
                        clone without hooks would, and checks the
                        commits it made.
relation:               []

...
"""


import os
import subprocess

import pytest

import cc_public.commit.history
import cc_public.commit.message


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tree, monkeypatch):
    """
    Return the root of a copy of the repository, committed on main
    under a message that conforms.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet', '--initial-branch', 'main')
    _commit(tree, cc_public.commit.message.compose('Add the first version of cc-public',
                                                   'The first version.'))
    return tree


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _commit(root, message):
    """
    Commit everything in root under message, without hooks, as a
    rebase or a clone without hooks would.

    """

    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--allow-empty', '--message', message)


def test_a_history_that_conforms_passes(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cc_public.commit.message.compose('Change README.md so that it is short',
                                                   'It is short.'))
    list_commit = cc_public.commit.history.commits(repo, ['HEAD'])
    assert len(list_commit) == 2
    assert [cc_public.commit.history.check(repo, commit) for commit in list_commit] == [[], []]
    assert cc_public.commit.history.duplicates(repo, list_commit) == []


def test_a_commit_made_without_the_hooks_is_reported(repo):
    (repo / '_data/register/reg_concern.yaml').unlink()
    _commit(repo, 'Tidy up')
    [found] = cc_public.commit.history.check(repo, 'HEAD')
    assert found.startswith('A commit message is a subject line, a blank line,')
    assert found.endswith(cc_public.commit.history.HINT_CUT)


def test_a_commit_copied_with_git_am_is_reported_with_the_cause(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cc_public.commit.message.compose('Change README.md so that it is short',
                                                   'It is short.'))
    patch = _git(repo, 'format-patch', '-1', '--stdout', 'HEAD')
    _git(repo, 'reset', '--quiet', '--hard', 'HEAD~1')
    subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', 'am', '--quiet'],
                   cwd = repo, check = True, input = patch, text = True)
    assert _git(repo, 'log', '-1', '--format=%B').strip() == 'Change README.md so that it is short'
    [found] = cc_public.commit.history.check(repo, 'HEAD')
    assert found.endswith(cc_public.commit.history.HINT_CUT)


def test_a_commit_item_shared_by_two_commits_is_reported(repo):
    message = cc_public.commit.message.compose('Change README.md so that it is short',
                                               'It is short.')
    _commit(repo, message)
    _commit(repo, message)
    list_commit = cc_public.commit.history.commits(repo, ['HEAD'])
    (_, item)   = cc_public.commit.message.parse(message)
    assert cc_public.commit.history.duplicates(repo, list_commit[-1:]) == [
        (item['id_self'], list_commit[1:])]


def test_a_push_sends_only_what_the_remote_does_not_have(repo):
    head = _git(repo, 'rev-parse', 'HEAD').strip()
    _git(repo, 'update-ref', 'refs/remotes/origin/main', head)
    _commit(repo, cc_public.commit.message.compose('Add nothing', 'Nothing.'))
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = ('refs/heads/main {tip} refs/heads/main {head}\n'
            'refs/heads/old {zero} refs/heads/old {head}\n').format(
                tip = tip, head = head, zero = cc_public.commit.history.ZERO)
    assert cc_public.commit.history.pushed(repo, 'origin', text) == ([tip], [tip])
