"""
---

id_self:                pym_cctool.queue._test.test_patch
guid_self:              pym_ffb82a70df2d43aba3dd7df581c834a3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Patch tests
brief:                  |
                        Tests of submitting, resubmitting and
                        withdrawing patches of the landing queue.
description:            |
                        Each test works in a small repository on dev,
                        makes topic branches of a commit or two, and
                        submits them as an agent would. The daemon is
                        not run; where a test needs a patch at another
                        stage, it moves the patch there as the daemon
                        would.
edge:                   []

...
"""


import datetime
import json
import subprocess

import pytest

import cctool.gate.gate
import cctool.queue.patch


# A moment to submit at, so that keys are known.
#
NOW = datetime.datetime(2026, 10, 30, 12, 0, 0, tzinfo = datetime.UTC)


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


# -----------------------------------------------------------------------------
def _branches(root):
    """
    Return the branches of the queue of root.

    """

    return _git(root, 'for-each-ref', '--format=%(refname:short)', 'refs/heads/queue/').split()


def test_a_submission_returns_before_any_test_and_makes_its_candidate_branch(dev_repo,
                                                                             monkeypatch):

    """
    ---

    id_self:                pyf_cctool.queue._test.test_patch.test_a_submission_returns_before_any_test_and_makes_its_candidate_branch
    guid_self:              pyf_4a79c2a0402441bc975e975881e39d63
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a submission runs no test
    brief:                  |
                            A submission returns before any test runs, and
                            the candidate branch exists with the name
                            given.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_admits_untested_submissions
        guid_target:        rqt_6a5db6c44c0543bd8ab850585602a574

    ...
    """

    def _refuse(*list_arg, **map_arg):
        raise AssertionError('A submission ran the gate.')

    monkeypatch.setattr(cctool.gate.gate, 'gate', _refuse)
    tip    = _work(dev_repo, 'topic/one', 'one.txt')
    record = cctool.queue.patch.submit(dev_repo, 'add_one', now = NOW)
    assert record['key'] == '20261030_120000_add_one'
    assert record['thread'] == 'topic-one'
    assert _branches(dev_repo) == ['queue/00_candidate/topic-one/20261030_120000_add_one']
    assert _git(dev_repo, 'rev-parse', 'queue/00_candidate/topic-one/20261030_120000_add_one',
                'refs/queue/20261030_120000_add_one/source').split() == [tip, tip]
    assert record['base'] == _git(dev_repo, 'rev-parse', 'dev').strip()
    assert [line['reason'] for line in cctool.queue.patch.read_journal(dev_repo)] == [
        'submitted']


def test_two_submissions_in_one_second_take_different_times_and_a_resubmission_its_first(
        dev_repo):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_patch.test_two_submissions_in_one_second_take_different_times_and_a_resubmission_its_first
    guid_self:              pyf_3e12ea05a64f412ba0415bb68be5ce8c
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a patch is stamped once
    brief:                  |
                            Two submissions in the same second get
                            different times, and a resubmitted patch keeps
                            its first time.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_stamps_patch_once
        guid_target:        rqt_68723d26886a45cbade46703edf0e1e2

    ...
    """

    _work(dev_repo, 'one', 'one.txt')
    first  = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _work(dev_repo, 'two', 'two.txt')
    second = cctool.queue.patch.submit(dev_repo, 'two', now = NOW)
    assert (first['key'], second['key']) == ('20261030_120000_one', '20261030_120001_two')

    _move(dev_repo, first, cctool.queue.patch.STAGE_REWORK)
    _git(dev_repo, 'checkout', '--quiet', cctool.queue.patch.branch(first,
                                                                    cctool.queue.patch.STAGE_REWORK))
    tip    = _work(dev_repo, cctool.queue.patch.branch(first, cctool.queue.patch.STAGE_REWORK),
                   'fixed.txt')
    _git(dev_repo, 'checkout', '--quiet', 'dev')
    again  = cctool.queue.patch.resubmit(dev_repo, 'queue/03_rework/one/20261030_120000_one')
    assert (again['key'], again['source'], again['state']) == ('20261030_120000_one', tip,
                                                               '00_candidate')
    assert 'queue/00_candidate/one/20261030_120000_one' in _branches(dev_repo)
    assert 'queue/03_rework/one/20261030_120000_one' not in _branches(dev_repo)


def test_a_submission_that_shares_commits_with_two_queued_patches_is_refused(dev_repo):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_patch.test_a_submission_that_shares_commits_with_two_queued_patches_is_refused
    guid_self:              pyf_7fbba9c2f98c442f9396b93b7afaccf5
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that an overlapping submission is refused
    brief:                  |
                            A submission that shares commits with two
                            queued patches, which are not one stack, is
                            refused with the reason.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_refuses_overlapping_submission
        guid_target:        rqt_5eed955d37ec4b50b8fc8bc0d45d0f4c

    ...
    """

    _work(dev_repo, 'one', 'one.txt')
    cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _work(dev_repo, 'two', 'two.txt')
    cctool.queue.patch.submit(dev_repo, 'two', now = NOW)
    _git(dev_repo, 'checkout', '--quiet', '-b', 'both', 'one')
    _git(dev_repo, 'merge', '--quiet', '--no-edit', 'two')

    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'not one stack'):
        cctool.queue.patch.submit(dev_repo, 'both', now = NOW)
    assert len(cctool.queue.patch.records(dev_repo)) == 2


def test_a_submission_that_holds_part_of_a_queued_patch_is_refused(dev_repo):
    _work(dev_repo, 'one', 'one.txt')
    _work(dev_repo, 'one', 'more.txt')
    cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _git(dev_repo, 'checkout', '--quiet', '-b', 'part', 'one~1')

    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'no clear boundary'):
        cctool.queue.patch.submit(dev_repo, 'part', now = NOW)


def test_a_source_already_submitted_or_holding_nothing_new_is_refused(dev_repo):
    _work(dev_repo, 'one', 'one.txt')
    cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'already submitted'):
        cctool.queue.patch.submit(dev_repo, 'again', now = NOW)
    _git(dev_repo, 'checkout', '--quiet', 'dev')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'nothing to submit'):
        cctool.queue.patch.submit(dev_repo, 'nothing', now = NOW)


def test_a_name_that_is_not_one_segment_is_refused(dev_repo):
    _work(dev_repo, 'one', 'one.txt')
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'not one segment'):
        cctool.queue.patch.submit(dev_repo, 'a/b', now = NOW)


def test_a_stacked_submission_depends_on_the_revision_of_the_patch_below(dev_repo):
    tip_one = _work(dev_repo, 'one', 'one.txt')
    below   = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _work(dev_repo, 'two', 'two.txt', start = 'one')
    above   = cctool.queue.patch.submit(dev_repo, 'two', now = NOW)
    assert above['base'] == tip_one
    assert above['depends'] == {'key': below['key'], 'source': tip_one}


def test_a_patch_stacked_on_one_in_rework_waits_and_is_stale_once_that_changes(dev_repo):

    """
    ---

    id_self:                pyf_cctool.queue._test.test_patch.test_a_patch_stacked_on_one_in_rework_waits_and_is_stale_once_that_changes
    guid_self:              pyf_703350728e914008bffbde7a3e919b16
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a dependent patch waits for its dependency
    brief:                  |
                            A patch stacked on one in rework is not tried,
                            and is marked stale once the patch below it
                            changes.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_defers_dependent_patch
        guid_target:        rqt_93a598f39a04413a83786aa0883d5979

    ...
    """

    _work(dev_repo, 'one', 'one.txt')
    below = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _work(dev_repo, 'two', 'two.txt', start = 'one')
    above = cctool.queue.patch.submit(dev_repo, 'two', now = NOW)
    _move(dev_repo, below, cctool.queue.patch.STAGE_REWORK)

    list_record = cctool.queue.patch.records(dev_repo)
    assert cctool.queue.patch.eligible(dev_repo, list_record) == []
    map_record  = {record['key']: record for record in list_record}
    assert cctool.queue.patch.blocker(map_record[above['key']], map_record) == (
        'depends on 20261030_120000_one, which is in rework')

    name = cctool.queue.patch.branch(below, cctool.queue.patch.STAGE_REWORK)
    _work(dev_repo, name, 'fixed.txt')
    cctool.queue.patch.resubmit(dev_repo, name)
    list_record = cctool.queue.patch.records(dev_repo)
    assert [record['key'] for record in cctool.queue.patch.eligible(dev_repo, list_record)] == [
        below['key']]
    assert cctool.queue.patch.by_ref(dev_repo, above['key'])['stale'] is True
    assert cctool.queue.patch.read_journal(dev_repo)[-1]['reason'] == 'stale'


def test_a_withdrawn_patch_keeps_its_record_and_the_refs_of_its_commits(dev_repo):
    tip    = _work(dev_repo, 'one', 'one.txt')
    record = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    cctool.queue.patch.withdraw(dev_repo, cctool.queue.patch.branch(record))
    assert _branches(dev_repo) == []
    assert cctool.queue.patch.by_ref(dev_repo, record['key'])['state'] == 'withdrawn'
    assert _git(dev_repo, 'rev-parse', cctool.queue.patch.ref(record, 'source')).strip() == tip


def test_a_patch_under_test_is_neither_resubmitted_nor_withdrawn(dev_repo):
    _work(dev_repo, 'one', 'one.txt')
    record = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    _move(dev_repo, record, cctool.queue.patch.STAGE_TEST)
    for step in (cctool.queue.patch.resubmit, cctool.queue.patch.withdraw):
        with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'under test'):
            step(dev_repo, record['key'])


def test_a_ref_that_names_no_patch_is_refused(dev_repo):
    with pytest.raises(cctool.queue.patch.ErrorQueue, match = 'names no patch'):
        cctool.queue.patch.by_ref(dev_repo, 'queue/03_rework/one/20261030_120000_none')


def test_the_records_hold_only_files_named_by_a_key(dev_repo):
    _work(dev_repo, 'one', 'one.txt')
    record = cctool.queue.patch.submit(dev_repo, 'one', now = NOW)
    (cctool.queue.patch.directory(dev_repo) / 'paused.json').write_text(json.dumps({}))
    assert [found['key'] for found in cctool.queue.patch.records(dev_repo)] == [record['key']]


# -----------------------------------------------------------------------------
def _move(root, record, stage):
    """
    Move the patch of record to stage, as the daemon would.

    """

    old = record['state']
    record['state'] = stage
    cctool.queue.patch.write(root, record)
    cctool.queue.patch.move(root, record, old, stage, 'moved by the test')
