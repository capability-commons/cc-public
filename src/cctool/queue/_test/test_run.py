"""
---

id_self:                pym_cctool.queue._test.test_run
guid_self:              pym_c41de5eb44ea413d9c54a161e98ae19d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Daemon tests
brief:                  |
                        Tests of the runs of the daemon of the landing
                        queue.
description:            |
                        Most tests work in a small repository on dev
                        whose queue signs with a key made for the
                        tests, under a stand-in gate whose one stage
                        logs each time it runs and fails on a tree
                        that holds FAIL.txt. Two work in a signed copy
                        of the repository with all of its source, so
                        that the history check runs with the code the
                        replayed commits hold.
edge:                   []

...
"""


import datetime
import json
import pathlib
import shutil
import subprocess

import pytest

import cctool.commit.message
import cctool.gate.gate
import cctool.gate.result
import cctool.queue.patch
import cctool.queue.report
import cctool.queue.run


pytestmark = pytest.mark.prepush

# A moment to submit at, so that keys are known.
#
NOW       = datetime.datetime(2026, 10, 30, 12, 0, 0, tzinfo = datetime.UTC)

# The test stage of a stand-in gate: it appends a line to a log outside
# the copy each time it runs, and fails if the tree holds FAIL.txt.
#
CODE_TEST = ('import pathlib, sys; open({log!r}, "a").write("ran\\n"); '
             'sys.exit(1 if pathlib.Path("FAIL.txt").exists() else 0)')


# The source of the repository, which a copy needs whole for the history
# check to run with the code its commits hold, and what a copy of it
# leaves out.
#
DIR_SOURCE = pathlib.Path(__file__).resolve().parents[3]
TUPLE_SKIP = ('_test', '__pycache__', 'conftest.py')


# -----------------------------------------------------------------------------
class Interrupt(BaseException):
    """
    A run of the daemon stopped from outside, as by a kill.

    """


# -----------------------------------------------------------------------------
@pytest.fixture
def queue(dev_repo, keyring, monkeypatch, tmp_path):
    """
    Return the root of a small repository on dev, whose queue signs with
    the key of keyring, the policy of a stand-in gate, and the log its
    test stage appends to.

    """

    (home, key) = keyring
    monkeypatch.setenv('GNUPGHOME', home)
    _git(dev_repo, 'config', cctool.queue.run.CONFIG_KEY, key)
    log    = tmp_path / 'ran.txt'
    policy = cctool.queue.run.Policy(
                 stages  = (('test', ('{python}', '-c', CODE_TEST.format(log = str(log)))),),
                 history = False,
                 key     = key)
    return (dev_repo, policy, log)


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _submit(root, branch, name, text = None, start = 'dev', patch = None):
    """
    Return the record of a patch submitted from branch, made from start
    if it does not exist, once it holds one more commit, which writes
    text, or name, to the file name. dev stays checked out.

    """

    if _git(root, 'branch', '--list', branch).strip():
        _git(root, 'checkout', '--quiet', branch)
    else:
        _git(root, 'checkout', '--quiet', '-b', branch, start)
    (root / name).write_text((text or name) + '\n')
    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'Add ' + name)
    record = cctool.queue.patch.submit(root, patch or branch, now = NOW)
    _git(root, 'checkout', '--quiet', 'dev')
    return record


# -----------------------------------------------------------------------------
def _record(root, record):
    """
    Return the record of the patch of record as it is now.

    """

    return cctool.queue.patch.by_ref(root, record['key'])


# -----------------------------------------------------------------------------
def _subjects(root, rev = 'dev'):
    """
    Return the subjects of the commits of rev, newest first.

    """

    return _git(root, 'log', '--format=%s', rev).splitlines()


def test_a_patch_that_passes_lands_as_its_tested_commit_in_the_main_checkout(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_that_passes_lands_as_its_tested_commit_in_the_main_checkout
    guid_self:              pyf_72798f22ca4e4a61b7f992de43a87fd8
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that only the tested commit lands
    brief:                  |
                            After a landing, dev and the main checkout are
                            at the tested commit.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_delivers_only_tested_commit
        guid_target:        rqt_a7ac48fc06a14f7ab0a2bb857367bc46

    ...
    """

    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt')
    assert cctool.queue.run.run(root, policy) == ['20261030_120000_one landed as {tip}.'.format(
        tip = _git(root, 'rev-parse', '--short=7', 'dev').strip())]

    landed = _record(root, record)
    tip    = landed['attempts'][-1]['tip']
    assert landed['state'] == 'landed'
    assert _git(root, 'rev-parse', 'dev', 'HEAD').split() == [tip, tip]
    assert (root / 'one.txt').read_text() == 'one.txt\n'
    assert _git(root, 'status', '--porcelain', '--untracked-files=no') == ''
    assert _git(root, 'log', '-1', '--format=%G?', 'dev').strip() == 'G'


def test_each_landed_patch_has_a_gate_result_naming_the_landed_commit(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_each_landed_patch_has_a_gate_result_naming_the_landed_commit
    guid_self:              pyf_3dad7eb13e8d4c59adc05bc762b68b2d
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a landing leaves a gate result
    brief:                  |
                            Each landed patch has a gate result whose
                            commit is the landed commit.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_captures_gate_result
        guid_target:        rqt_7f02707b66e1438f9adf33330c04b241

    ...
    """

    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt')
    cctool.queue.run.run(root, policy)
    landed = _record(root, record)['landed']
    result = cctool.gate.result.read(root, landed['tip'])
    assert (result['commit'], result['base'], result['passed']) == (landed['tip'],
                                                                   landed['dev'], True)
    assert result['policy'] == cctool.gate.result.policy(policy.stages)
    assert result['environment'] == cctool.gate.result.environment(root, landed['tip'],
                                                                   policy.stages)


def test_a_patch_that_conflicts_goes_to_conflict_with_a_note_and_its_commits_unchanged(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_that_conflicts_goes_to_conflict_with_a_note_and_its_commits_unchanged
    guid_self:              pyf_40fccb82b82d415dbb2c38f6fe7a671d
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a conflicting patch is parked
    brief:                  |
                            A patch that conflicts with dev ends in
                            queue/01_conflict with its note, and its
                            source commits are unchanged.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_defers_conflicting_patch
        guid_target:        rqt_04da5152dedc4e6dbf3001c3723de65f

    ...
    """

    (root, policy, log) = queue
    record = _submit(root, 'one', 'one.txt', 'from the topic')
    (root / 'one.txt').write_text('from dev\n')
    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'Add one.txt on dev')

    assert cctool.queue.run.run(root, policy) == [
        '20261030_120000_one conflicts with dev, so it is in conflict.']
    held = _record(root, record)
    assert held['state'] == '01_conflict'
    assert held['note'].startswith('Replaying onto dev at {dev} conflicts in one.txt.'.format(
                                       dev = _git(root, 'rev-parse', '--short=7', 'dev').strip()))
    assert _git(root, 'rev-parse', 'queue/01_conflict/one/20261030_120000_one').strip() == (
        record['source'])
    assert not log.exists()


def test_a_patch_that_fails_a_test_goes_to_rework_and_the_test_runs_once(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_that_fails_a_test_goes_to_rework_and_the_test_runs_once
    guid_self:              pyf_acc4f19ab66249f9bf707cc2759e7a91
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a failing patch goes to rework
    brief:                  |
                            A patch with a failing test ends in
                            queue/03_rework with its note, and the test
                            ran once.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_defers_failing_patch
        guid_target:        rqt_399ffdb581d24523b97edfe678750f36

    ...
    """

    (root, policy, log) = queue
    record = _submit(root, 'one', 'FAIL.txt')
    before = _git(root, 'rev-parse', 'dev')
    assert cctool.queue.run.run(root, policy) == [
        '20261030_120000_one failed its test stage, so it is in rework.']
    held = _record(root, record)
    assert held['state'] == '03_rework'
    assert held['note'].startswith('The test stage failed on ')
    assert held['attempts'][-1]['stage'] == 'test'
    assert log.read_text() == 'ran\n'
    assert _git(root, 'rev-parse', 'dev') == before
    assert cctool.queue.run.run(root, policy) == ['Nothing was ready to land.']
    assert log.read_text() == 'ran\n'


def test_a_patch_whose_tip_fails_a_test_marked_prepush_is_not_landed(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_whose_tip_fails_a_test_marked_prepush_is_not_landed
    guid_self:              pyf_2e5b47a39f6f4c479076af6ef25761a6
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that the landing gate runs the tests marked prepush
    brief:                  |
                            A patch whose tip fails a test marked prepush
                            is not landed.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_enforces_landing_gate
        guid_target:        rqt_b7c77b61f9e64a9aa7f0aa4ae609635b

    ...
    """

    (root, _, _) = queue
    policy = cctool.queue.run.policy(root)
    assert policy.stages == cctool.gate.gate.TUPLE_STAGE
    policy = cctool.queue.run.Policy(
                 stages  = tuple(stage for stage in policy.stages
                                 if stage[0] == cctool.gate.gate.NAME_TEST),
                 history = False,
                 key     = policy.key)
    record = _submit(root, 'one', 'test_marked.py',
                     'import pytest\n\n\n'
                     '@pytest.mark.prepush\n'
                     'def test_marked():\n'
                     '    assert False')
    before = _git(root, 'rev-parse', 'dev')
    cctool.queue.run.run(root, policy)
    held = _record(root, record)
    assert held['state'] == '03_rework'
    assert held['note'].splitlines()[0].endswith(
        'and is not retried. 1 failed, the first test_marked.py::test_marked.')
    assert _git(root, 'rev-parse', 'dev') == before


def test_moving_dev_during_a_test_returns_the_patch_to_candidate(queue, tmp_path):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_moving_dev_during_a_test_returns_the_patch_to_candidate
    guid_self:              pyf_b835da8c475c457aad0880b869285fcf
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a stale landing is refused
    brief:                  |
                            Moving dev during a test returns the patch to
                            candidate, and dev is not changed by the
                            queue.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_refuses_stale_landing
        guid_target:        rqt_2490df9c7cc949ef88efee6812d2ebba

    ...
    """

    (root, policy, _) = queue
    code   = ('import subprocess; subprocess.run(["git", "-C", {root!r}, "-c", "user.name=W", '
              '"-c", "user.email=w@example.com", "-c", "commit.gpgsign=false", "commit", '
              '"--quiet", "--allow-empty", "--no-verify", "--message", "Moved"], '
              'check = True)').format(root = str(root))
    policy = cctool.queue.run.Policy(stages  = (('test', ('{python}', '-c', code)),),
                                     history = False,
                                     key     = policy.key)
    record = _submit(root, 'one', 'one.txt')
    assert cctool.queue.run.run(root, policy) == [
        '20261030_120000_one no longer matches dev, so it is a candidate again.']
    held = _record(root, record)
    assert (held['state'], held['attempts'][-1]['outcome']) == ('00_candidate', 'stale')
    assert _subjects(root) == ['Moved', 'Start']


def test_a_missing_interpreter_pauses_the_queue_and_the_patch_stays_a_candidate(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_missing_interpreter_pauses_the_queue_and_the_patch_stays_a_candidate
    guid_self:              pyf_4d0fac19aaac4845b2bebef901f6d222
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a failure of the queue pauses it
    brief:                  |
                            A missing interpreter pauses the queue with
                            its reason, and the patch in hand stays a
                            candidate.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_halts_on_queue_failure
        guid_target:        rqt_c00b0195d97644d5b48e2e2c95df99a4

    ...
    """

    (root, policy, log) = queue
    policy = cctool.queue.run.Policy(stages  = (('test', ('no-such-python', '-c', 'pass')),),
                                     history = False,
                                     key     = policy.key)
    record = _submit(root, 'one', 'one.txt')
    assert cctool.queue.run.run(root, policy) == [
        'The queue is paused: no-such-python, which the test stage runs, cannot be found.']
    assert _record(root, record)['state'] == '00_candidate'
    assert cctool.queue.run.paused(root)['reason'] == (
        'no-such-python, which the test stage runs, cannot be found.')
    assert cctool.queue.run.run(root, policy)[0].startswith('The queue is paused since ')
    assert cctool.queue.run.resume(root) is not None
    assert cctool.queue.run.paused(root) is None


def test_a_key_that_cannot_sign_pauses_the_queue_with_no_patch_in_rework(queue):
    (root, policy, _) = queue
    policy = cctool.queue.run.Policy(stages = policy.stages, history = False,
                                     key = 'ABCDEF0123456789')
    record = _submit(root, 'one', 'one.txt')
    [line] = cctool.queue.run.run(root, policy)
    assert line.startswith('The queue is paused: The signing key ABCDEF0123456789')
    assert _record(root, record)['state'] == '00_candidate'


def test_a_main_checkout_with_changes_pauses_the_queue(queue):
    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt')
    (root / 'README.md').write_text('Edited by hand.\n')
    [line] = cctool.queue.run.run(root, policy)
    assert line.startswith('The queue is paused: The main checkout has changes')
    assert _record(root, record)['state'] == '00_candidate'
    assert (root / 'README.md').read_text() == 'Edited by hand.\n'


def test_a_run_that_finds_the_queue_held_does_nothing(queue):
    (root, policy, _) = queue
    _submit(root, 'one', 'one.txt')
    with cctool.queue.patch.locked(root, cctool.queue.run.FILE_RUN):
        assert cctool.queue.run.run(root, policy) == [
            'Another run holds the queue, so this one does nothing.']


@pytest.mark.parametrize('name', ['replay', 'landing_run', 'land', '_landed'])
def test_a_run_interrupted_at_each_step_lands_the_patch_once_on_the_next(queue, monkeypatch,
                                                                         name):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_run_interrupted_at_each_step_lands_the_patch_once_on_the_next
    guid_self:              pyf_8a9d08bc4a264a319804cbd033cbf679
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that an interrupted run is recovered
    brief:                  |
                            Interrupting the daemon at each transition,
                            then running it again, leaves dev holding only
                            tested work, no patch landed twice and every
                            patch accounted for.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_derives_state_after_interruption
        guid_target:        rqt_741864419f5e42d5a76b877939ba62f9

    ...
    """

    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt')
    step   = getattr(cctool.queue.run, name)

    def _interrupt(*list_arg, **map_arg):
        if name == '_landed':
            step(*list_arg, **map_arg)
        raise Interrupt

    with monkeypatch.context() as patched:
        patched.setattr(cctool.queue.run, name, _interrupt)
        with pytest.raises(Interrupt):
            cctool.queue.run.run(root, policy)

    cctool.queue.run.run(root, policy)
    landed = _record(root, record)
    assert landed['state'] == 'landed'
    assert _subjects(root) == ['Add one.txt', 'Start']
    assert landed['landed']['tip'] == _git(root, 'rev-parse', 'dev').strip()
    assert _git(root, 'for-each-ref', 'refs/heads/queue/') == ''
    assert cctool.queue.run.run(root, policy) == ['Nothing was ready to land.']


def test_a_patch_stacked_on_a_landed_patch_replays_only_its_own_commits(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_stacked_on_a_landed_patch_replays_only_its_own_commits
    guid_self:              pyf_eab943e7104947d08aa9647afddbc536
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a patch replays only its own commits
    brief:                  |
                            A patch stacked on a landed patch replays only
                            its own commits.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_replays_only_own_commits
        guid_target:        rqt_060b7e5e20f5482099fab6bd653492d3

    ...
    """

    (root, policy, _) = queue
    below = _submit(root, 'one', 'one.txt')
    above = _submit(root, 'two', 'two.txt', start = 'one')
    cctool.queue.run.run(root, policy)
    assert [_record(root, record)['state'] for record in (below, above)] == ['landed', 'landed']
    assert _subjects(root) == ['Add two.txt', 'Add one.txt', 'Start']
    assert len(_record(root, above)['landed']['commits']) == 1


def test_the_oldest_unblocked_patch_of_several_threads_is_taken_first(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_the_oldest_unblocked_patch_of_several_threads_is_taken_first
    guid_self:              pyf_8e137c00929b48d0932f28ed2adf7167
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that the oldest eligible patch is taken
    brief:                  |
                            With candidates from several threads and some
                            patches blocked, the queue takes the oldest
                            unblocked one.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_takes_oldest_eligible_patch
        guid_target:        rqt_4d7e00fef31a43f78ff58378f64470ac

    ...
    """

    (root, policy, _) = queue
    blocked = _submit(root, 'one', 'FAIL.txt', patch = 'blocked')
    above   = _submit(root, 'two', 'two.txt', start = 'one', patch = 'above')
    older   = _submit(root, 'three', 'three.txt', patch = 'older')
    newer   = _submit(root, 'four', 'four.txt', patch = 'newer')
    cctool.queue.run.run(root, policy)
    list_taken = [line['key'] for line in cctool.queue.patch.read_journal(root)
                  if line['reason'] == 'taken']
    assert list_taken == [blocked['key'], older['key'], newer['key']]
    assert _record(root, above)['state'] == '00_candidate'


def test_a_landed_patch_keeps_its_record_and_commits_once_its_branch_is_gone(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_landed_patch_keeps_its_record_and_commits_once_its_branch_is_gone
    guid_self:              pyf_edfd77189ad142cabb075e3834d02629
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that patch records are kept
    brief:                  |
                            After a patch lands and its branch is deleted,
                            its record and the commits it names are still
                            present.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_keeps_patch_records
        guid_target:        rqt_24293f08698f4c26bb7495964ad899d5

    ...
    """

    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt')
    _git(root, 'branch', '--quiet', '-D', 'one')
    cctool.queue.run.run(root, policy)
    _git(root, 'reflog', 'expire', '--expire=now', '--all')
    _git(root, 'gc', '--quiet', '--prune=now')

    landed = _record(root, record)
    assert landed['source'] == record['source']
    assert landed['landed']['commits'] == [landed['attempts'][-1]['tip']]
    for commit in (record['source'], record['base'], landed['attempts'][-1]['tip']):
        assert _git(root, 'cat-file', '-t', commit).strip() == 'commit'


def test_a_patch_through_conflict_to_landing_leaves_a_line_for_each_move(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_a_patch_through_conflict_to_landing_leaves_a_line_for_each_move
    guid_self:              pyf_19e7a39731df4c83b6a2817a2d284e6a
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that every move is journaled
    brief:                  |
                            A patch that goes through conflict and then
                            lands leaves one line per move.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_traces_every_move
        guid_target:        rqt_bc8579ac0f16432b8bb4b24d46ce9e24

    ...
    """

    (root, policy, _) = queue
    record = _submit(root, 'one', 'one.txt', 'from the topic')
    (root / 'one.txt').write_text('from dev\n')
    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'Add one.txt on dev')
    cctool.queue.run.run(root, policy)

    name = cctool.queue.patch.branch(_record(root, record))
    _git(root, 'checkout', '--quiet', name)
    _git(root, 'rebase', '--quiet', '-X', 'theirs', 'dev')
    _git(root, 'checkout', '--quiet', 'dev')
    cctool.queue.patch.resubmit(root, name)
    cctool.queue.run.run(root, policy)

    list_move = [(line['from'], line['to'], line['reason'])
                 for line in cctool.queue.patch.read_journal(root)]
    assert list_move == [(None, '00_candidate', 'submitted'),
                         ('00_candidate', '02_test', 'taken'),
                         ('02_test', '01_conflict', 'replay conflicts'),
                         ('01_conflict', '00_candidate', 'resubmitted'),
                         ('00_candidate', '02_test', 'taken'),
                         ('02_test', None, 'landed')]
    for line in cctool.queue.patch.read_journal(root):
        assert set(line) == {'time', 'key', 'ref', 'from', 'to', 'tip', 'dev', 'reason'}


def test_dev_is_pushed_and_a_lost_acknowledgement_needs_no_second_push(queue, tmp_path):
    (root, policy, _) = queue
    remote = tmp_path / 'origin.git'
    subprocess.run(['git', 'clone', '--quiet', '--bare', str(root), str(remote)], check = True)
    _git(root, 'remote', 'add', 'origin', str(remote))
    policy = cctool.queue.run.Policy(stages = policy.stages, history = False, key = policy.key,
                                     remote = 'origin')
    record = _submit(root, 'one', 'one.txt')
    cctool.queue.run.run(root, policy)
    assert _git(remote, 'rev-parse', 'dev') == _git(root, 'rev-parse', 'dev')
    assert _record(root, record)['landed']['pushed'] is True

    landed = _record(root, record)
    landed['landed']['pushed'] = False
    cctool.queue.patch.write(root, landed)
    assert cctool.queue.run.run(root, policy) == ['dev is on origin at {dev}.'.format(
        dev = _git(root, 'rev-parse', '--short=7', 'dev').strip())]
    assert _record(root, record)['landed']['pushed'] is True


def test_a_remote_whose_dev_has_diverged_pauses_the_queue(queue, tmp_path):
    (root, policy, _) = queue
    remote = tmp_path / 'origin.git'
    subprocess.run(['git', 'clone', '--quiet', '--bare', str(root), str(remote)], check = True)
    _git(root, 'remote', 'add', 'origin', str(remote))
    other = tmp_path / 'other'
    subprocess.run(['git', 'clone', '--quiet', '--branch', 'dev', str(remote), str(other)],
                   check = True)
    _git(other, 'commit', '--quiet', '--allow-empty', '--message', 'Elsewhere')
    _git(other, 'push', '--quiet', 'origin', 'dev')
    policy = cctool.queue.run.Policy(stages = policy.stages, history = False, key = policy.key,
                                     remote = 'origin')
    _submit(root, 'one', 'one.txt')
    list_line = cctool.queue.run.run(root, policy)
    assert list_line[-1].startswith('The queue is paused: dev on origin has diverged')


def test_a_remote_that_cannot_be_reached_is_tried_at_the_next_run(queue, tmp_path):
    (root, policy, _) = queue
    _git(root, 'remote', 'add', 'origin', str(tmp_path / 'gone.git'))
    policy = cctool.queue.run.Policy(stages = policy.stages, history = False, key = policy.key,
                                     remote = 'origin')
    _submit(root, 'one', 'one.txt')
    list_line = cctool.queue.run.run(root, policy)
    assert list_line[-1].startswith('The remote could not be reached, so dev is pushed at the '
                                    'next run')
    assert cctool.queue.run.paused(root) is None


def test_the_policy_is_the_gate_of_a_push_with_the_key_and_remote_git_gives(queue):
    (root, _, _) = queue
    _git(root, 'config', cctool.queue.run.CONFIG_REMOTE, 'queue')
    policy = cctool.queue.run.policy(root)
    assert (policy.stages, policy.history, policy.remote) == (cctool.gate.gate.TUPLE_STAGE,
                                                              True, 'queue')
    assert json.dumps(cctool.gate.result.policy(policy.stages))


# -----------------------------------------------------------------------------
@pytest.fixture
def checked(signed_repo, keyring, monkeypatch, tmp_path):
    """
    Return the root of a signed copy of the repository with all of its
    source, checked out on dev, whose queue signs with the key that its
    register gives the maintainer, and a policy that runs the history
    check and a stand-in gate.

    """

    shutil.copytree(DIR_SOURCE, signed_repo / DIR_SOURCE.name,
                    ignore        = shutil.ignore_patterns(*TUPLE_SKIP),
                    dirs_exist_ok = True)
    _git(signed_repo, 'add', '--all')
    _git(signed_repo, 'commit', '--quiet', '--no-verify', '--amend', '--no-edit')
    _git(signed_repo, 'branch', '--move', 'main', 'dev')
    _git(signed_repo, 'config', cctool.queue.run.CONFIG_KEY, keyring[1])
    policy = cctool.queue.run.Policy(stages = (('test', ('{python}', '-c', 'pass')),),
                                     key    = keyring[1])
    return (signed_repo, policy)


# -----------------------------------------------------------------------------
def _commit_as_agent(root, branch, message):
    """
    Return the record of a patch of one unsigned commit on branch, made
    from dev, that changes README.md under message, once it is submitted.

    """

    _git(root, 'checkout', '--quiet', '-b', branch, 'dev')
    (root / 'README.md').write_text('Changed on {branch}.\n'.format(branch = branch))
    _git(root, 'add', '--all')
    _git(root, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify',
         '--message', message)
    record = cctool.queue.patch.submit(root, branch, now = NOW)
    _git(root, 'checkout', '--quiet', 'dev')
    return record


def test_a_patch_whose_replayed_commits_pass_the_history_check_lands_signed(checked):
    (root, policy) = checked
    record = _commit_as_agent(root, 'short', cctool.commit.message.compose(
                                  'Change README.md so that it is short', 'It is short.'))
    cctool.queue.run.run(root, policy)
    assert _record(root, record)['state'] == 'landed'
    assert _git(root, 'log', '-1', '--format=%G? %s', 'dev').strip() == (
        'G Change README.md so that it is short')


def test_a_patch_whose_replayed_commit_fails_the_history_check_goes_to_rework(checked):
    (root, policy) = checked
    record = _commit_as_agent(root, 'tidy', 'Tidy up')
    before = _git(root, 'rev-parse', 'dev')
    cctool.queue.run.run(root, policy)
    held = _record(root, record)
    assert (held['state'], held['attempts'][-1]['stage']) == ('03_rework', 'history')
    assert _git(root, 'rev-parse', 'dev') == before


def test_the_summary_after_a_run_with_a_failure_names_the_patch_and_its_reason(queue):
    """
    ---

    id_self:                pyf_cctool.queue._test.test_run.test_the_summary_after_a_run_with_a_failure_names_the_patch_and_its_reason
    guid_self:              pyf_f6eb2a62af964673bdff8e22824a7563
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that the daily summary names each failure
    brief:                  |
                            After a run with a failure, the summary names
                            the patch and its reason.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_queue_publishes_daily_summary
        guid_target:        rqt_353067f2da39444fb7bf615cff507f2f

    ...
    """

    (root, policy, _) = queue
    _submit(root, 'one', 'FAIL.txt')
    _submit(root, 'two', 'two.txt')
    cctool.queue.run.run(root, policy)
    path = cctool.queue.report.write_summary(root)
    text = path.read_text()
    assert path.parent.name == cctool.queue.report.DIR_SUMMARY
    assert 'The queue is running.' in text
    assert '1 gone to conflict or rework.' in text
    assert '  20261030_120000_one to 03_rework, ' in text
    assert 'old: The test stage failed on ' in text
    assert '1 landed.\n  20261030_120001_two as ' in text


def test_the_status_says_what_each_patch_waits_on_and_what_it_blocks(queue):
    (root, policy, _) = queue
    below = _submit(root, 'one', 'FAIL.txt')
    above = _submit(root, 'two', 'two.txt', start = 'one')
    cctool.queue.run.run(root, policy)
    _git(root, 'worktree', 'add', '--quiet', str(root.parent / 'repair'),
         cctool.queue.patch.branch(_record(root, below)))
    list_line = cctool.queue.report.status(root)
    assert list_line[0] == 'The queue is running.'
    assert list_line.pop(1) == ('These branches are named neither work/THREAD/TOPIC nor '
                                'trial/NAME: one, two.')
    assert list_line[1] == ('03_rework {key} from one; attempt 1 failed on dev {dev}; blocks '
                            '{above}; claimed by {path}').format(
                                key   = below['key'],
                                dev   = _git(root, 'rev-parse', '--short=7', 'dev').strip(),
                                above = above['key'],
                                path  = root.parent / 'repair')
    assert list_line[2].startswith('  The test stage failed on ')
    assert list_line[3] == '00_candidate {key} from two; waits: depends on {below}, which is in rework'.format(
        key = above['key'], below = below['key'])


def test_the_measures_come_from_the_records(queue):
    (root, policy, _) = queue
    _submit(root, 'one', 'FAIL.txt')
    _submit(root, 'two', 'two.txt')
    cctool.queue.run.run(root, policy)
    _submit(root, 'three', 'three.txt')
    now       = datetime.datetime(2026, 10, 30, 14, 0, 0, tzinfo = datetime.UTC)
    list_line = cctool.queue.report.measures(root, now)
    assert list_line[0].startswith('submission to landing: median ')
    assert list_line[1].startswith('landing run: median ')
    assert list_line[2:] == ['attempts gone to conflict: 0 of 2',
                             'attempts gone to rework: 1 of 2',
                             'oldest ready patch: 2.0 h']
