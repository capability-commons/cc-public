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


import pathlib
import shutil
import subprocess

import pytest

import cctool.commit.message
import cctool.commit.repo
import cctool.edit.edit


pytestmark = pytest.mark.prepush

# The source of the repository, all of which land needs in the copy,
# since it checks the commits it lands with the code they hold; and
# what a copy of it leaves out.
#
DIR_SOURCE = pathlib.Path(__file__).resolve().parents[3]
TUPLE_SKIP = ('_test', '__pycache__', 'conftest.py')


# -----------------------------------------------------------------------------
@pytest.fixture
def topic(signed_repo):
    """
    Return the root of a signed copy of the repository, with all of its
    source, in which the
    branch topic holds one unsigned commit beyond the first, and main
    has moved on by a signed commit of its own, as when an agent's work
    comes back after the maintainer's.

    """

    shutil.copytree(DIR_SOURCE, signed_repo / DIR_SOURCE.name,
                    ignore        = shutil.ignore_patterns(*TUPLE_SKIP),
                    dirs_exist_ok = True)
    _git(signed_repo, 'add', '--all')
    _git(signed_repo, 'commit', '--quiet', '--no-verify', '--amend', '--no-edit')
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

    [landed] = cctool.commit.repo.land(topic, path, is_gated = False)
    assert landed.endswith(' Change AGENTS.md so that it ends with notes')
    assert _git(topic, 'log', '--format=%s', 'main').splitlines() == [
        'Change AGENTS.md so that it ends with notes', 'Change README.md so that it is short', 'Add the first version of cc-public']
    assert _git(topic, 'log', '-1', '--format=%G?', 'main').strip() == 'G'


def test_the_default_bundle_of_a_branch_with_a_slash_sits_beside_the_repository():
    root = pathlib.Path('/work/cc-public')
    assert cctool.commit.repo.bundle_path(root, 'claude/fix-x') == pathlib.Path(
                                                                    '/work/claude-fix-x.bundle')
    assert cctool.commit.repo.bundle_path(root, 'topic') == pathlib.Path('/work/topic.bundle')


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
        cctool.commit.repo.land(topic, path, is_gated = False)
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
        cctool.commit.repo.land(topic, path, is_gated = False)
    assert len(cctool.commit.repo.land(topic, path, reset_author = True, is_gated = False)) == 2
    assert _git(topic, 'log', '-2', '--format=%an <%ae> %G?', 'main').splitlines() == [
        'William Payne <wtpayne@gmail.com> G', 'William Payne <wtpayne@gmail.com> G']


def test_land_checks_the_commits_with_the_code_they_hold(topic):
    _git(topic, 'checkout', '--quiet', 'topic')
    path = topic / 'src' / 'cctool' / 'commit' / 'history.py'
    path.write_text(path.read_text().replace(
        '    list_found = []\n',
        '    list_found = [\'The checks of the landed code ran.\']\n', 1))
    _commit(topic, 'Change the history check so that it always fails', 'It always fails.',
            is_signed = False)
    _git(topic, 'checkout', '--quiet', 'main')
    head = _git(topic, 'rev-parse', 'main')
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'checks of the landed code ran'):
        cctool.commit.repo.land(topic, path, is_gated = False)
    assert _git(topic, 'rev-parse', 'main') == head
    assert _git(topic, 'branch', '--show-current').strip() == 'main'


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
        cctool.commit.repo.land(topic, path, is_gated = False)
    assert _git(topic, 'rev-parse', 'main') == head
    assert _git(topic, 'status', '--porcelain', '--untracked-files=no') == ''


def test_land_of_a_bundle_made_on_a_commit_the_branch_does_not_hold_leaves_the_branch(topic):
    _git(topic, 'checkout', '--quiet', '-b', 'old', 'main~1')
    (topic / 'README.md').write_text('Old.\n')
    _commit(topic, 'Change README.md so that it is old', 'It is old.')
    old  = _git(topic, 'rev-parse', 'HEAD').strip()
    _git(topic, 'checkout', '--quiet', '-b', 'later')
    path = topic / 'AGENTS.md'
    path.write_text(path.read_text() + '\nLater.\n')
    _commit(topic, 'Change AGENTS.md so that it ends later', 'It ends later.', is_signed = False)
    _git(topic, 'checkout', '--quiet', 'main')
    head = _git(topic, 'rev-parse', 'main')
    path = topic.parent / 'later.bundle'
    cctool.commit.repo.bundle(topic, 'later', 'old', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo,
                       match = 'The bundle starts after {old} Change README.md so that it is '
                               'old, which main does not hold'.format(old = old[:7])):
        cctool.commit.repo.land(topic, path, is_gated = False)
    assert _git(topic, 'rev-parse', 'main') == head


def test_land_of_a_bundle_made_on_one_already_landed_lands_only_its_own_commits(topic):
    _git(topic, 'checkout', '--quiet', '-b', 'later', 'topic')
    path = topic / 'AGENTS.md'
    path.write_text(path.read_text() + 'Later.\n')
    _commit(topic, 'Change AGENTS.md so that it ends later', 'It ends later.', is_signed = False)
    _git(topic, 'checkout', '--quiet', 'main')
    path_first = topic.parent / 'topic.bundle'
    path_later = topic.parent / 'later.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path_first)
    cctool.commit.repo.bundle(topic, 'later', 'topic', path_later)
    cctool.commit.repo.land(topic, path_first, is_gated = False)

    [landed] = cctool.commit.repo.land(topic, path_later, is_gated = False)
    assert landed.endswith(' Change AGENTS.md so that it ends later')
    assert _git(topic, 'log', '--format=%s', 'main').splitlines() == [
        'Change AGENTS.md so that it ends later', 'Change AGENTS.md so that it ends with notes',
        'Change README.md so that it is short', 'Add the first version of cc-public']


def test_land_of_commits_whose_tree_together_fails_the_gate_leaves_the_branch(topic):
    _git(topic, 'checkout', '--quiet', 'topic')
    _annotate(topic, 'dec_cross_item_checks_engine')
    _commit(topic, 'Add ann_land_twice', 'It is added on topic.', is_signed = False)
    _git(topic, 'checkout', '--quiet', 'main')
    _annotate(topic, 'dec_tooling_language')
    _commit(topic, 'Add ann_land_twice', 'It is added on main.')
    head = _git(topic, 'rev-parse', 'main')
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~2', path)

    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'duplicate_id'):
        cctool.commit.repo.land(topic, path)
    assert _git(topic, 'rev-parse', 'main') == head
    assert _git(topic, 'branch', '--show-current').strip() == 'main'


def test_land_refuses_changes_that_no_commit_holds(topic):
    path = topic.parent / 'topic.bundle'
    cctool.commit.repo.bundle(topic, 'topic', 'main~1', path)
    (topic / 'README.md').write_text('Unsaved.\n')
    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'commit or stash them first'):
        cctool.commit.repo.land(topic, path, is_gated = False)


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
    assert cctool.commit.repo.push(topic, 'origin', is_gated = False) == 0


def test_push_of_a_branch_new_to_the_remote_signs_only_what_it_lacks(topic, tmp_path_factory):
    remote = tmp_path_factory.mktemp('remote')
    _git(remote, 'init', '--quiet', '--bare')
    _git(topic, 'remote', 'add', 'origin', str(remote))
    _git(topic, 'push', '--quiet', 'origin', 'main')
    _git(topic, 'checkout', '--quiet', '-b', 'trial')
    (topic / 'README.md').write_text('Shorter.\n')
    _commit(topic, 'Change README.md so that it is shorter', 'It is shorter.', is_signed = False)

    [unsigned] = cctool.commit.repo.unsigned(topic, 'origin')
    assert unsigned.endswith(' Change README.md so that it is shorter')
    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'not signed'):
        cctool.commit.repo.push(topic, 'origin')
    ([signed], _) = cctool.commit.repo.sign(topic)
    assert signed.endswith(' Change README.md so that it is shorter')
    assert _git(topic, 'rev-parse', 'HEAD~1') == _git(topic, 'rev-parse', 'main')
    assert cctool.commit.repo.unsigned(topic, 'origin') == []
    assert cctool.commit.repo.push(topic, 'origin', is_gated = False) == 0
    assert _git(remote, 'branch', '--format=%(refname:short)').split() == ['main', 'trial']


def test_push_checks_the_tip_before_git_connects_and_tells_the_hook(topic, tmp_path_factory):
    remote = tmp_path_factory.mktemp('remote')
    _git(remote, 'init', '--quiet', '--bare')
    _git(topic, 'remote', 'add', 'origin', str(remote))
    _git(topic, 'push', '--quiet', 'origin', 'main')
    (topic / 'README.md').write_text('Shorter.\n')
    _commit(topic, 'Change README.md so that it is shorter', 'It is shorter.')
    tip       = _git(topic, 'rev-parse', 'HEAD').strip()
    path_seen = topic.parent / 'seen'
    path_hook = topic / '.git' / 'hooks' / 'pre-push'
    path_hook.write_text('#!/bin/sh\nprintf "%s\\n" "$CCTOOL_PUSH_CHECKED" > {seen}\n'
                         'cat >> {seen}\n'.format(seen = path_seen))
    path_hook.chmod(0o755)

    assert cctool.commit.repo.push(topic, 'origin', is_gated = False) == 0
    [checked, line] = path_seen.read_text().splitlines()
    assert checked == tip
    assert line.split()[1:3] == [tip, 'refs/heads/main']
    assert _git(remote, 'rev-parse', 'main').strip() == tip


def test_push_of_a_tip_that_fails_its_checks_sends_nothing(topic, tmp_path_factory):
    remote = tmp_path_factory.mktemp('remote')
    _git(remote, 'init', '--quiet', '--bare')
    _git(topic, 'remote', 'add', 'origin', str(remote))
    _git(topic, 'push', '--quiet', 'origin', 'main')
    (topic / 'AGENTS.md').write_text((topic / 'AGENTS.md').read_text() + 'Tidied.\n')
    _git(topic, 'add', '--all')
    _git(topic, 'commit', '--quiet', '--no-verify', '--message', 'Tidy up')

    assert cctool.commit.repo.push(topic, 'origin', is_gated = False) == 1
    assert _git(remote, 'rev-parse', 'main') == _git(topic, 'rev-parse', 'main~1')


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _annotate(root, id_decision):
    """
    Add the annotation ann_land_twice about the decision id_decision to
    the tree at root.

    """

    tree = cctool.edit.edit.Tree(root)
    cctool.edit.edit.batch(tree, [{'new':   'ann_land_twice',
                                   'field': {'title': 'Landed twice',
                                             'brief': 'It is added on each side.'},
                                   'link':  [['relation_is_about', id_decision]]}])
    assert cctool.edit.edit.apply(tree) == {}


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
