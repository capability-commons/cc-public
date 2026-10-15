"""
---

id_self:                pym_cc_public.gate._test.test_gate
guid_self:              pym_e84b2529264f40e5afdf4bdf01c0f170
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate tests
brief:                  |
                        Tests of the gate, over a small repository of
                        their own.
description:            |
                        Each test makes a repository, stages some of
                        its content, and runs the gate with stages
                        that report what they see, rather than the
                        real stages, which would run these tests
                        again.
note:                   |
                        A stage's output is matched by how it begins,
                        since an interpreter may add warnings of its
                        own after it.
relation:               []

...
"""


import os
import subprocess

import click.testing
import pytest

import cc_public.cli.command
import cc_public.gate.gate


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tmp_path, monkeypatch):
    """
    Return the root of a repository whose staged content is a module,
    src/marker.py, and whose working copy has an unstaged edit to it
    and an untracked file.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)

    path = tmp_path / 'src/marker.py'
    path.parent.mkdir()
    path.write_text('TEXT = "staged"\n')
    _git(tmp_path, 'init', '--quiet')
    _git(tmp_path, 'add', '--all')
    path.write_text('TEXT = "unstaged"\n')
    (tmp_path / 'untracked.txt').write_text('')
    return tmp_path


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root.

    """

    subprocess.run(['git', *list_arg], cwd = root, check = True, capture_output = True)


def _stage(name, code):
    """
    Return a stage that runs the python code.

    """

    return (name, ('{python}', '-c', code))


def test_the_copy_holds_what_is_staged_and_not_the_working_copy(repo, tmp_path_factory):
    dir_copy = tmp_path_factory.mktemp('copy')
    cc_public.gate.gate.copy_staged(repo, dir_copy)
    assert (dir_copy / 'src/marker.py').read_text() == 'TEXT = "staged"\n'
    assert not (dir_copy / 'untracked.txt').exists()


def test_a_stage_runs_the_code_of_the_copy(repo):
    stage = _stage('read', 'import marker; print(marker.TEXT)')
    [(_, is_passed, output)] = cc_public.gate.gate.gate(repo, (stage,))
    assert is_passed
    assert output.startswith('staged\n')


def test_each_stage_reports_whether_it_passed_and_what_it_printed(repo):
    tuple_stage = (_stage('pass', 'pass'),
                   _stage('fail', 'import sys; print("Wrong."); sys.exit(1)'))
    [(name, is_passed, _), (other, is_failed, output)] = cc_public.gate.gate.gate(repo, tuple_stage)
    assert (name, is_passed, other, is_failed) == ('pass', True, 'fail', False)
    assert output.startswith('Wrong.\n')


def test_a_stage_that_runs_too_long_is_stopped_and_fails(repo):
    stage = _stage('slow', 'import time; print("Started.", flush = True); time.sleep(30)')
    [(_, is_passed, output)] = cc_public.gate.gate.gate(repo, (stage,), seconds = 2)
    assert not is_passed
    assert output.startswith('Started.\n')
    assert output.endswith('Stopped after 2 s, the time limit of a stage.\n')


def test_a_stage_runs_without_the_git_environment_of_the_hook(repo, monkeypatch):
    monkeypatch.setenv('GIT_INDEX_FILE', str(repo / '.git/index'))
    stage = _stage('env', 'import os; print(os.environ.get("GIT_INDEX_FILE"))')
    [(_, _, output)] = cc_public.gate.gate.gate(repo, (stage,))
    assert output.startswith('None\n')


def test_a_tree_that_is_not_a_repository_cannot_be_gated(tmp_path):
    with pytest.raises(cc_public.gate.gate.ErrorGate) as info:
        cc_public.gate.gate.gate(tmp_path, (_stage('pass', 'pass'),))
    assert str(info.value).startswith('The staged content cannot be copied: ')


def test_the_command_prints_a_failure_before_its_verdict(repo, monkeypatch):
    monkeypatch.setattr(cc_public.gate.gate, 'TUPLE_STAGE',
                        (_stage('pass', 'pass'),
                         _stage('fail', 'import sys; print("Wrong."); sys.exit(1)')))
    result = click.testing.CliRunner().invoke(cc_public.cli.command.main,
                                              ['gate', '--root', str(repo)])
    assert result.exit_code == 1
    assert result.stdout.startswith('pass: passed\nWrong.\n')
    assert result.stdout.endswith('\nfail: failed\n')


def test_the_test_files_are_split_into_shards_of_about_equal_size(tmp_path):
    for (name, size) in (('a', 30), ('b', 20), ('c', 15), ('d', 5)):
        path = tmp_path / 'src' / name / '_test' / 'test_{name}.py'.format(name = name)
        path.parent.mkdir(parents = True)
        path.write_text('#' * size)
    assert cc_public.gate.gate.shards(tmp_path, 2) == [['src/a/_test/test_a.py',
                                                        'src/d/_test/test_d.py'],
                                                       ['src/b/_test/test_b.py',
                                                        'src/c/_test/test_c.py']]
    assert len(cc_public.gate.gate.shards(tmp_path, 8)) == 4


def test_a_sharded_stage_runs_once_for_each_shard_and_reports_once(repo, monkeypatch):
    for name in ('a', 'b'):
        path = repo / 'src' / name / 'test_{name}.py'.format(name = name)
        path.parent.mkdir(parents = True)
        path.write_text('#')
    subprocess.run(['git', 'add', '.'], cwd = repo, check = True, capture_output = True)
    monkeypatch.setattr(cc_public.gate.gate.os, 'cpu_count', lambda: 2)
    stage = ('shard', ('{python}', '-c', 'import sys; print(sys.argv[1:])',
                       cc_public.gate.gate.ARG_SHARD))
    [(name, is_passed, output)] = cc_public.gate.gate.gate(repo, (stage,))
    assert (name, is_passed) == ('shard', True)
    assert "['src/a/test_a.py']\n" in output
    assert "['src/b/test_b.py']\n" in output
