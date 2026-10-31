"""
---

id_self:                pym_cctool.gate._test.test_result
guid_self:              pym_2dba3ede87224f01bb0a7afd4ba6a81e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate result tests
brief:                  |
                        Tests that a gate result proves a pass only
                        for its commit, policy and environment.
description:            |
                        Each test works in a repository of one commit,
                        writes a result for it, and asks whether the
                        result proves a pass for a policy.
edge:                   []

...
"""


import json
import os
import subprocess

import pytest

import cctool.gate.gate
import cctool.gate.result


# The stages of a gate, and of one that selects fewer tests.
#
TUPLE_WIDE   = (('test', ('{python}', '-m', 'pytest', '-m', 'not slow')),)
TUPLE_NARROW = (('test', ('{python}', '-m', 'pytest', '-m', 'not slow and not prepush')),)
LIST_PASSED  = [('test', True, '1 passed')]
LIST_FAILED  = [('test', False, '1 failed')]


# -----------------------------------------------------------------------------
@pytest.fixture
def commit(tmp_path, monkeypatch):
    """
    Return the root of a repository of one commit, and the commit.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)

    (tmp_path / 'marker.txt').write_text('marker\n')
    for list_arg in (['init', '--quiet'],
                     ['add', '--all'],
                     ['-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                      '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--message', 'Start']):
        subprocess.run(['git', *list_arg], cwd = tmp_path, check = True, capture_output = True)
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd = tmp_path, check = True,
                          capture_output = True, text = True).stdout.strip()
    return (tmp_path, head)


def test_a_passing_result_proves_its_commit_under_the_same_policy(commit):
    (root, head) = commit
    result = cctool.gate.result.write(root, head, head, TUPLE_WIDE, LIST_PASSED)
    assert result['passed'] is True
    assert result['policy']['stages'] == [['test', '{python}', '-m', 'pytest', '-m', 'not slow']]
    assert cctool.gate.result.read(root, head) == result
    assert cctool.gate.result.proves(root, head, TUPLE_WIDE)


def test_a_result_from_a_narrower_selection_proves_nothing(commit):
    (root, head) = commit
    cctool.gate.result.write(root, head, head, TUPLE_NARROW, LIST_PASSED)
    assert not cctool.gate.result.proves(root, head, TUPLE_WIDE)


def test_a_result_from_another_environment_proves_nothing(commit):
    (root, head) = commit
    cctool.gate.result.write(root, head, head, TUPLE_WIDE, LIST_PASSED)
    path   = cctool.gate.result.directory(root) / (head + '.json')
    result = json.loads(path.read_text())
    result['environment']['python'] = '3.0.0'
    path.write_text(json.dumps(result))
    assert not cctool.gate.result.proves(root, head, TUPLE_WIDE)


def test_a_failed_result_proves_nothing(commit):
    (root, head) = commit
    cctool.gate.result.write(root, head, head, TUPLE_WIDE, LIST_FAILED)
    assert not cctool.gate.result.proves(root, head, TUPLE_WIDE)


def test_a_result_that_is_not_whole_proves_nothing(commit):
    (root, head) = commit
    path = cctool.gate.result.directory(root) / (head + '.json')
    path.parent.mkdir(parents = True)
    path.write_text('{"commit": ')
    assert cctool.gate.result.read(root, head) is None
    assert not cctool.gate.result.proves(root, head, TUPLE_WIDE)


def test_the_results_are_kept_in_the_git_directory(commit):
    (root, _) = commit
    assert cctool.gate.result.directory(root) == (cctool.gate.gate.git_dir(root)
                                                   / cctool.gate.result.DIR_RESULT)
