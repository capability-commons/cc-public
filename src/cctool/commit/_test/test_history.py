"""
---

id_self:                pym_cctool.commit._test.test_history
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
edge:                   []

...
"""


import os
import shutil
import subprocess
import tempfile

import pytest

import cctool.commit.history
import cctool.commit.message


pytestmark = pytest.mark.prepush


# The identity of the maintainer, as git takes it, which the team member
# register gives as his git_author.
#
IDENT_MAINTAINER = ('-c', 'user.name=William Payne', '-c', 'user.email=wtpayne@gmail.com')


REGISTER = '_data/register/reg_team_member.yaml'

# The signing key that the team member register gives for the
# maintainer, which each copy gives the key of a keyring made for the
# tests in its place.
#
LINE_KEY = 'git_signing_key:    9C4FB30F113CAB6A\n'


# -----------------------------------------------------------------------------
@pytest.fixture(scope = 'module')
def keyring():
    """
    Return a keyring made for the tests, with one signing key and no
    passphrase, as the folder that holds it and the long id of the key.
    gpg runs an agent for a keyring, and the path of the agent's socket
    must be short, so the folder is made directly in the temporary
    folder of the system.

    """

    if shutil.which('gpg') is None:
        pytest.skip('gpg is not installed, so no commit can be signed.')
    home = tempfile.mkdtemp(prefix = 'gpg')
    env  = {**os.environ, 'GNUPGHOME': home}
    subprocess.run(['gpg', '--batch', '--pinentry-mode', 'loopback', '--passphrase', '',
                    '--quick-generate-key', 'Test key <test@example.invalid>', 'ed25519',
                    'sign', 'never'],
                   env = env, check = True, capture_output = True)
    listing = subprocess.run(['gpg', '--list-keys', '--with-colons'],
                             env = env, check = True, capture_output = True, text = True).stdout
    key = next(line.split(':')[4] for line in listing.splitlines() if line.startswith('pub:'))
    yield (home, key.upper())
    subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env = env, check = False,
                   capture_output = True)
    shutil.rmtree(home, ignore_errors = True)


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tree, keyring, monkeypatch):
    """
    Return the root of a copy of the repository, committed on main
    under a message that conforms. Each commit is signed with the key
    of keyring, which the copy's register gives as the maintainer's.

    """

    (home, key) = keyring
    for key_env in [key_env for key_env in os.environ if key_env.startswith('GIT_')]:
        monkeypatch.delenv(key_env)
    monkeypatch.setenv('GNUPGHOME', home)
    for (index, (name, value)) in enumerate([('commit.gpgsign', 'true'),
                                              ('user.signingkey', key),
                                              ('gpg.format', 'openpgp')]):
        monkeypatch.setenv('GIT_CONFIG_KEY_{index}'.format(index = index), name)
        monkeypatch.setenv('GIT_CONFIG_VALUE_{index}'.format(index = index), value)
    monkeypatch.setenv('GIT_CONFIG_COUNT', '3')
    _replace(tree, REGISTER, LINE_KEY, LINE_KEY.replace('9C4FB30F113CAB6A', key))
    _git(tree, 'init', '--quiet', '--initial-branch', 'main')
    _commit(tree, cctool.commit.message.compose('Add the first version of cc-public',
                                                'The first version.'))
    return tree


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *IDENT_MAINTAINER, *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _replace(root, relative, old, new):
    """
    Replace the one old in the file at relative under root with new.

    """

    path = root / relative
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))


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
    _commit(repo, cctool.commit.message.compose('Change README.md so that it is short',
                                                'It is short.'))
    list_commit = cctool.commit.history.commits(repo, ['HEAD'])
    assert len(list_commit) == 2
    assert [cctool.commit.history.check(repo, commit) for commit in list_commit] == [[], []]
    assert cctool.commit.history.duplicates(repo, list_commit) == []


def test_a_commit_made_without_the_hooks_is_reported(repo):
    (repo / '_data/register/reg_concern.yaml').unlink()
    _commit(repo, 'Tidy up')
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('A commit message is a subject line, a blank line,')
    assert found.endswith(cctool.commit.history.HINT_CUT)


def test_a_commit_authored_by_no_team_member_is_reported(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, 'commit', '--quiet', '--no-verify',
         '--author', 'Claude <noreply@anthropic.com>',
         '--message', cctool.commit.message.compose('Change README.md so that it is short',
                                                    'It is short.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('The commit is authored by Claude <noreply@anthropic.com>, who '
                            'is not the git_author of a team member')


def test_a_commit_that_is_not_signed_is_reported(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '--message',
         cctool.commit.message.compose('Change README.md so that it is short', 'It is short.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('The commit is not signed, and a team member')


def test_a_commit_signed_with_the_key_of_no_team_member_is_reported(repo, keyring):
    _replace(repo, REGISTER, keyring[1], 'ABCDEF0123456789')
    _commit(repo, cctool.commit.message.compose('Change the team member register so that it is '
                                                'wrong', 'It is wrong.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found == ('The commit is signed with the key {key}, which is the git_signing_key of '
                     'no team member that reg_team_member holds.'.format(key = keyring[1]))


def test_a_tree_that_gives_no_signing_key_checks_no_signature(repo, keyring):
    _replace(repo, REGISTER, '    ' + LINE_KEY.replace('9C4FB30F113CAB6A', keyring[1]), '')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '--message',
         cctool.commit.message.compose('Change the team member register so that it gives no '
                                       'key', 'It gives no key.'))
    assert cctool.commit.history.check(repo, 'HEAD') == []


def test_a_commit_copied_with_git_am_is_reported_with_the_cause(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cctool.commit.message.compose('Change README.md so that it is short',
                                                'It is short.'))
    patch = _git(repo, 'format-patch', '-1', '--stdout', 'HEAD')
    _git(repo, 'reset', '--quiet', '--hard', 'HEAD~1')
    subprocess.run(['git', *IDENT_MAINTAINER, 'am', '--quiet'],
                   cwd = repo, check = True, input = patch, text = True)
    assert _git(repo, 'log', '-1', '--format=%B').strip() == 'Change README.md so that it is short'
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.endswith(cctool.commit.history.HINT_CUT)


def test_a_commit_item_shared_by_two_commits_is_reported(repo):
    message = cctool.commit.message.compose('Change README.md so that it is short',
                                            'It is short.')
    _commit(repo, message)
    _commit(repo, message)
    list_commit = cctool.commit.history.commits(repo, ['HEAD'])
    (_, item)   = cctool.commit.message.parse(message)
    assert cctool.commit.history.duplicates(repo, list_commit[-1:]) == [
        (item['id_self'], list_commit[1:])]


def test_a_push_sends_only_what_the_remote_does_not_have(repo):
    head = _git(repo, 'rev-parse', 'HEAD').strip()
    _git(repo, 'update-ref', 'refs/remotes/origin/main', head)
    _commit(repo, cctool.commit.message.compose('Add nothing', 'Nothing.'))
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = ('refs/heads/main {tip} refs/heads/main {head}\n'
            'refs/heads/old {zero} refs/heads/old {head}\n'
            'refs/tags/old {tip} refs/tags/old {zero}\n').format(
                tip = tip, head = head, zero = cctool.commit.history.ZERO)
    assert cctool.commit.history.pushed(repo, 'origin', text) == ([tip], [tip])


def test_a_pushed_tag_is_not_checked(repo):
    _commit(repo, 'An old message with no item')
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = 'refs/tags/old {tip} refs/tags/old {zero}\n'.format(
               tip = tip, zero = cctool.commit.history.ZERO)
    assert cctool.commit.history.pushed(repo, 'origin', text) == ([], [])
