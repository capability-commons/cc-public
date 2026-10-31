"""
---

id_self:                pym_cctool.queue._test.test_bundle
guid_self:              pym_f2373b7a110440f6b29492dfde9f6edf
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Bundle tests
brief:                  |
                        Tests of making bundles of patches, submitting
                        them, and sweeping the inbox.
description:            |
                        Each test makes its work in a clone, as a
                        remote session does, and submits it to the
                        queue of the repository the clone was made
                        from, as atlas does.
edge:                   []

...
"""


import datetime
import subprocess

import pytest

import cctool.queue.bundle
import cctool.queue.patch
import cctool.queue.report
import cctool.queue.run


# A moment to submit at, so that keys are known.
#
NOW = datetime.datetime(2026, 10, 31, 9, 30, 0, tzinfo = datetime.UTC)


# -----------------------------------------------------------------------------
@pytest.fixture
def remote(dev_repo, tmp_path):
    """
    Return the root of the repository on atlas, on dev, and of a clone of
    it on dev, as a remote session holds one.

    """

    clone = tmp_path / 'remote'
    _git(dev_repo.parent, 'clone', '--quiet', '--branch', 'dev', str(dev_repo), str(clone))
    return (dev_repo, clone)


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _work(root, branch, name, start = 'dev'):
    """
    Return the tip of branch, made from start if it does not exist, once
    it holds one more commit, which adds the file name.

    """

    if _git(root, 'branch', '--list', branch).strip():
        _git(root, 'checkout', '--quiet', branch)
    else:
        _git(root, 'checkout', '--quiet', '-b', branch, start)
    (root / name).write_text(name + '\n')
    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'Add ' + name)
    return _git(root, 'rev-parse', 'HEAD').strip()


def test_a_bundle_made_in_a_remote_session_is_submitted_as_its_patch(remote):
    (atlas, clone) = remote
    tip            = _work(clone, 'claude/topic', 'one.txt')
    (path, [made]) = cctool.queue.bundle.make(clone, 'add_one')
    assert path == clone.parent / 'claude-topic-add_one.bundle'
    assert made.endswith(' Add one.txt')
    assert not list(clone.parent.glob('*.part'))

    record = cctool.queue.bundle.submit(atlas, path, now = NOW)
    assert (record['key'], record['thread'], record['source'], record['bundle']) == (
        '20261031_093000_add_one', 'claude-topic', tip, 'claude-topic-add_one.bundle')
    assert _git(atlas, 'rev-parse', 'queue/00_candidate/claude-topic/20261031_093000_add_one',
                'refs/queue/20261031_093000_add_one/source').split() == [tip, tip]
    assert _git(atlas, 'for-each-ref', cctool.queue.bundle.PREFIX_REF) == ''


def test_a_file_that_is_not_a_bundle_of_the_queue_is_refused(remote, tmp_path):
    (atlas, clone) = remote
    path = tmp_path / 'notes.bundle'
    path.write_text('Not a bundle.\n')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'it is not a bundle'):
        cctool.queue.bundle.submit(atlas, path)

    _work(clone, 'topic', 'one.txt')
    _git(clone, 'bundle', 'create', '--quiet', str(path), 'dev..topic')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'was not made by cctool queue'):
        cctool.queue.bundle.submit(atlas, path)
    assert cctool.queue.patch.records(atlas) == []


def test_a_bundle_made_on_a_commit_atlas_lacks_is_refused(remote):
    (atlas, clone) = remote
    _work(clone, 'dev', 'elsewhere.txt')
    _work(clone, 'topic', 'one.txt')
    (path, _) = cctool.queue.bundle.make(clone, 'add_one', base = 'dev')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'made on a commit that this'):
        cctool.queue.bundle.submit(atlas, path)


def test_a_bundle_that_overlaps_a_queued_patch_is_refused(remote):
    (atlas, clone) = remote
    _work(clone, 'topic', 'one.txt')
    _work(clone, 'topic', 'more.txt')
    (path, _) = cctool.queue.bundle.make(clone, 'whole')
    cctool.queue.bundle.submit(atlas, path, now = NOW)
    _git(clone, 'checkout', '--quiet', '-b', 'part', 'topic~1')
    (path, _) = cctool.queue.bundle.make(clone, 'part')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'no clear boundary'):
        cctool.queue.bundle.submit(atlas, path, now = NOW)
    assert len(cctool.queue.patch.records(atlas)) == 1


def test_the_sweep_submits_each_bundle_and_moves_what_it_refuses(remote, tmp_path):
    (atlas, clone) = remote
    inbox = tmp_path / 'inbox'
    inbox.mkdir()
    _git(clone, 'config', cctool.queue.run.CONFIG_INBOX, str(inbox))
    _work(clone, 'topic', 'one.txt')
    (path, _) = cctool.queue.bundle.make(clone, 'add_one')
    assert path == inbox / 'topic-add_one.bundle'
    (inbox / 'junk.bundle').write_text('Not a bundle.\n')

    list_line = cctool.queue.bundle.sweep(atlas, inbox, NOW)
    assert sorted(line.split()[0] for line in list_line) == ['junk.bundle',
                                                             'topic-add_one.bundle']
    [record] = cctool.queue.patch.records(atlas)
    assert (record['thread'], record['agent']) == ('topic', 'inbox')
    assert (inbox / 'processed' / (record['key'] + '.bundle')).is_file()
    assert sorted(path.name for path in (inbox / 'rejected').iterdir()) == [
        '20261031_093000_junk.bundle', '20261031_093000_junk.bundle.txt']
    assert list(inbox.glob('*.bundle')) == []
    assert cctool.queue.bundle.rejected(inbox, NOW.date())[0][0] == '20261031_093000_junk.bundle'

    _git(atlas, 'config', cctool.queue.run.CONFIG_INBOX, str(inbox))
    text = '\n'.join(cctool.queue.report.summary(atlas, NOW))
    assert '1 refused from the inbox.\n  20261031_093000_junk.bundle: junk.bundle cannot be' in text


def test_the_policy_names_the_inbox_and_a_missing_one_pauses_the_queue(remote, tmp_path):
    (atlas, _) = remote
    _git(atlas, 'config', cctool.queue.run.CONFIG_INBOX, str(tmp_path / 'gone'))
    policy = cctool.queue.run.policy(atlas)
    assert policy.inbox == tmp_path / 'gone'
    assert cctool.queue.run.run(atlas, policy) == [
        'The queue is paused: The inbox {path}, which git config queue.inbox names, is not a '
        'folder.'.format(path = tmp_path / 'gone')]
