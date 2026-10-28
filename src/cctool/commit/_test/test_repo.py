"""
---

id_self:                pym_cctool.commit._test.test_repo
guid_self:              pym_747e9eedf54c4caebe6ac4bbf2e1ae0e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Repository step tests
brief:                  |
                        Tests of landing, signing, pushing and
                        bundling commits.
description:            |
                        Each test works in a signed copy of the
                        repository, makes a branch of unsigned commits
                        as an agent would, and takes the steps of the
                        maintainer on it.
edge:                   []

...
"""


import subprocess

import pytest

import cctool.commit.message
import cctool.commit.repo


pytestmark = pytest.mark.prepush


# -----------------------------------------------------------------------------
@pytest.fixture
def topic(signed_repo):
    """
    Return the root of a signed copy of the repository in which the
    branch topic holds one unsigned commit beyond the first, and main
    has moved on by a signed commit of its own, as when an agent's work
    comes back after the maintainer's.

    """

    _git(signed_repo, 'checkout', '--quiet', '-b', 'topic')
    path = signed_repo / 'AGENTS.md'
    path.write_text(path.read_text() + '\nNotes.\n')
    _commit(signed_repo, 'Change AGENTS.md so that it ends with notes', 'It ends with notes.',
            is_signed = False)
    _git(signed_repo, 'checkout', '--quiet', 'main')
    (signed_repo / 'README.md').write_text('Changed.\n')
    _commit(signed_repo, 'Change README.md so that it is short', 'It is short.')
    return signed_repo


def test_land_replays_signs_and_checks_the_commits_of_a_bundle(topic):
    base = _git(topic, 'rev-parse', 'main~1').strip()
    path = topic.parent / 'topic.bundle'
    assert len(cctool.commit.repo.bundle(topic, 'topic', base, path)) == 1
    _git(topic, 'branch', '--quiet', '-D', 'topic')

    [landed] = cctool.commit.repo.land(topic, path)
    assert landed.endswith(' Change AGENTS.md so that it ends with notes')
    assert _git(topic, 'log', '--format=%s', 'main').splitlines() == [
        'Change AGENTS.md so that it ends with notes', 'Change README.md so that it is short', 'Add the first version of cc-public']
    assert _git(topic, 'log', '-1', '--format=%G?', 'main').strip() == 'G'


def test_land_of_commits_that_fail_their_checks_leaves_the_branch(topic):
    _git(topic, 'checkout', '--quiet', 'topic')
    (topic / 'AGENTS.md').write_text((topic / 'AGENTS.md').read_text() + 'Tidied.\n')
    _git(topic, 'add', '--all')
    _git(topic, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify',
         '--message', 'Tidy up')
    _git(topic, 'checkout', '--quiet', 'main')
    head = _git(topic, 'rev-parse', 'main')
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'fail their checks'):
        cctool.commit.repo.land(topic, path)
    assert _git(topic, 'rev-parse', 'main') == head
    assert _git(topic, 'branch', '--show-current').strip() == 'main'


def test_land_with_reset_author_makes_the_maintainer_the_author(topic):
    _git(topic, 'checkout', '--quiet', 'topic')
    (topic / 'AGENTS.md').write_text((topic / 'AGENTS.md').read_text() + 'By an agent.\n')
    _git(topic, 'add', '--all')
    _git(topic, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify',
         '--author', 'Claude <noreply@anthropic.com>', '--message',
         cctool.commit.message.compose('Change AGENTS.md so that an agent wrote to it',
                                       'An agent wrote to it.'))
    _git(topic, 'checkout', '--quiet', 'main')
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'fail their checks'):
        cctool.commit.repo.land(topic, path)
    assert len(cctool.commit.repo.land(topic, path, reset_author = True)) == 2
    assert _git(topic, 'log', '-2', '--format=%an <%ae> %G?', 'main').splitlines() == [
        'William Payne <wtpayne@gmail.com> G', 'William Payne <wtpayne@gmail.com> G']


def test_land_of_commits_that_conflict_leaves_the_branch(topic):
    _git(topic, 'checkout', '--quiet', 'topic')
    (topic / 'README.md').write_text('Otherwise.\n')
    _commit(topic, 'Change README.md so that it says otherwise', 'It says otherwise.',
            is_signed = False)
    _git(topic, 'checkout', '--quiet', 'main')
    head = _git(topic, 'rev-parse', 'main')
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'cannot be replayed'):
        cctool.commit.repo.land(topic, path)
    assert _git(topic, 'rev-parse', 'main') == head
    assert _git(topic, 'status', '--porcelain', '--untracked-files=no') == ''


def test_land_refuses_changes_that_no_commit_holds(topic):
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)
    (topic / 'README.md').write_text('Unsaved.\n')
    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'commit or stash them first'):
        cctool.commit.repo.land(topic, path)


def test_push_refuses_a_commit_that_is_not_signed_until_it_is_signed(topic, tmp_path_factory):
    remote = tmp_path_factory.mktemp('remote')
    _git(remote, 'init', '--quiet', '--bare')
    _git(topic, 'remote', 'add', 'origin', str(remote))
    _git(topic, 'push', '--quiet', 'origin', 'main')
    (topic / 'README.md').write_text('Shorter.\n')
    _commit(topic, 'Change README.md so that it is shorter', 'It is shorter.', is_signed = False)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'not signed'):
        cctool.commit.repo.push(topic, 'origin')
    _git(topic, 'branch', 'copy')
    ([signed], list_branch) = cctool.commit.repo.sign(topic)
    assert signed.endswith(' Change README.md so that it is shorter')
    assert list_branch == ['copy']
    assert 'copy' not in _git(topic, 'branch', '--format=%(refname:short)').split()
    assert cctool.commit.repo.unsigned(topic, 'origin') == []
    assert cctool.commit.repo.push(topic, 'origin') == 0


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _commit(root, title, brief, is_signed = True):
    """
    Commit everything in root, without hooks, under a message that
    conforms, signed unless is_signed is false, as an agent commits
    without the maintainer's key.

    """

    _git(root, 'add', '--all')
    _git(root, '-c', 'commit.gpgsign={sign}'.format(sign = str(is_signed).lower()), 'commit',
         '--quiet', '--no-verify', '--message', cctool.commit.message.compose(title, brief))
