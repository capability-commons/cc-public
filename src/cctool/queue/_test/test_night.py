"""
---

id_self:                pym_cctool.queue._test.test_night
guid_self:              pym_3cecca8da2414f7484e86c61aea5d80e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Night tests
brief:                  |
                        Tests of a night of the overnight tasks, the
                        verified branch and the review.
description:            |
                        Each test runs a night in a small repository
                        on dev, with stand-in tasks that pass or fail
                        at once and a stand-in review that writes the
                        prompt it was given.
edge:                   []

...
"""


import datetime
import subprocess
import sys

import pytest

import cctool.gate.gate
import cctool.gate.result
import cctool.queue.night
import cctool.queue.report


pytestmark = pytest.mark.prepush

# A night to run at, so that its day is known.
#
NOW       = datetime.datetime(2026, 11, 1, 1, 0, 0, tzinfo = datetime.UTC)
TASK_PASS = ('pass', (sys.executable, '-c', 'pass'))
TASK_FAIL = ('fail', (sys.executable, '-c', 'import sys; print("Wrong."); sys.exit(1)'))

# A stand-in for the review, which writes the prompt it was given to a
# file in its worktree and prints one line.
#
TUPLE_REVIEW = (sys.executable, '-c',
                'import sys; open("prompt.txt", "w").write(sys.argv[1]); print("Reviewed.")',
                cctool.queue.night.ARG_PROMPT)


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _night(*tuple_task, review = None):
    """
    Return a night of tuple_task, with no remote, and review if given.

    """

    return cctool.queue.night.Night(tasks = tuple_task, review = review)


def test_a_night_that_passes_moves_verified_to_the_commit_it_tested(dev_repo):
    tip = _git(dev_repo, 'rev-parse', 'dev').strip()
    assert cctool.queue.night.run(dev_repo, _night(TASK_PASS), NOW)[-1] == (
        'verified is at {tip}.'.format(tip = tip[:7]))
    assert _git(dev_repo, 'rev-parse', 'verified').strip() == tip
    [record] = cctool.queue.night.records(dev_repo)
    assert (record['day'], record['commit'], record['passed']) == ('20261101', tip, True)
    assert cctool.gate.result.proves(dev_repo, tip, (TASK_PASS,))

    (dev_repo / 'two.txt').write_text('two\n')
    _git(dev_repo, 'add', '--all')
    _git(dev_repo, 'commit', '--quiet', '--no-verify', '--message', 'Add two.txt')
    cctool.queue.night.run(dev_repo, _night(TASK_PASS), NOW)
    assert _git(dev_repo, 'rev-parse', 'verified') == _git(dev_repo, 'rev-parse', 'dev')


def test_a_night_that_fails_leaves_verified_where_it_was(dev_repo):
    cctool.queue.night.run(dev_repo, _night(TASK_PASS), NOW)
    before = _git(dev_repo, 'rev-parse', 'verified')
    (dev_repo / 'two.txt').write_text('two\n')
    _git(dev_repo, 'add', '--all')
    _git(dev_repo, 'commit', '--quiet', '--no-verify', '--message', 'Add two.txt')

    list_line = cctool.queue.night.run(dev_repo, _night(TASK_PASS, TASK_FAIL), NOW)
    assert list_line[1].startswith('fail failed in ')
    assert list_line[-1].startswith('The night failed on ')
    assert _git(dev_repo, 'rev-parse', 'verified') == before
    [record] = cctool.queue.night.records(dev_repo)
    assert record['passed'] is False
    assert record['tasks'][1]['output'] == 'Wrong.'
    assert ('The night failed on {tip}: fail.'.format(tip = record['commit'][:7])
            in cctool.queue.report.summary(dev_repo, NOW))


def test_a_night_off_dev_records_why_it_could_not_run(dev_repo):
    _git(dev_repo, 'checkout', '--quiet', '-b', 'trial')
    [line] = cctool.queue.night.run(dev_repo, _night(TASK_PASS), NOW)
    assert line == 'The night could not run: The main checkout is not on dev.'
    [record] = cctool.queue.night.records(dev_repo)
    assert (record['tasks'], record['reason']) == ([], 'The main checkout is not on dev.')


def test_the_review_runs_in_a_worktree_of_its_own_with_the_prompt(dev_repo):
    list_line = cctool.queue.night.run(dev_repo, _night(TASK_PASS, review = TUPLE_REVIEW), NOW)
    assert list_line[-1].startswith('The daily review finished in ')
    assert list_line[-1].endswith(' min: Reviewed.')
    path   = dev_repo.parent / 'cc-public-review-20261101'
    prompt = (path / 'prompt.txt').read_text()
    assert 'on the branch work/review/20261101 made from dev' in prompt
    assert 'cctool queue submit review_20261101' in prompt
    assert _git(path, 'branch', '--show-current').strip() == 'work/review/20261101'
    log = cctool.gate.gate.git_dir(dev_repo) / cctool.queue.night.DIR_REVIEW / '20261101.log'
    assert log.read_text() == 'Reviewed.\n'

    later = NOW + datetime.timedelta(days = 1)
    cctool.queue.night.run(dev_repo, _night(TASK_PASS, review = TUPLE_REVIEW), later)
    assert not path.exists()
    assert (dev_repo.parent / 'cc-public-review-20261102').is_dir()


def test_a_night_runs_every_overnight_task_by_default(dev_repo):
    assert [name for (name, _) in cctool.queue.night.night(dev_repo).tasks] == [
        'slow', 'fuzz', 'coverage', 'check-full']


def test_a_night_on_thursday_runs_the_weekly_review_in_its_place(dev_repo):
    thursday  = datetime.datetime(2026, 11, 5, 1, 0, 0, tzinfo = datetime.UTC)
    list_line = cctool.queue.night.run(dev_repo, _night(TASK_PASS, review = TUPLE_REVIEW),
                                       thursday)
    assert list_line[-1].startswith('The weekly review finished in ')
    path   = dev_repo.parent / 'cc-public-review-20261105-weekly'
    prompt = (path / 'prompt.txt').read_text()
    assert prompt.startswith('Run the weekly in-depth review of cc-public')
    assert 'cctool queue submit review_20261105_weekly' in prompt
    assert '2026-11-05-weekly.md' in prompt
    assert _git(path, 'branch', '--show-current').strip() == 'work/review/20261105-weekly'


def test_the_kind_of_review_follows_the_calendar_of_wtp():
    assert cctool.queue.night.kind_of(datetime.datetime(2026, 11, 5, 1, 0,
                                                        tzinfo = datetime.UTC)) == 'weekly'
    assert cctool.queue.night.kind_of(datetime.datetime(2026, 11, 4, 23, 30,
                                                        tzinfo = datetime.UTC)) == 'daily'
    assert cctool.queue.night.kind_of(datetime.datetime(2026, 7, 1, 23, 30,
                                                        tzinfo = datetime.UTC)) == 'weekly'
