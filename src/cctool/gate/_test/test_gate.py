"""
---

id_self:                pym_cctool.gate._test.test_gate
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
edge:                   []

...
"""


import os
import platform
import subprocess

import click.testing
import pytest

import cctool.cli.command
import cctool.gate.gate
import cctool.gate.timing


pytestmark = pytest.mark.prepush


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


def _commit(root):
    """
    Commit what is staged in root.

    """

    _git(root, '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
         '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--message', 'Start')


def _stage(name, code):
    """
    Return a stage that runs the python code.

    """

    return (name, ('{python}', '-c', code))


def test_the_copy_holds_what_is_staged_and_not_the_working_copy(repo, tmp_path_factory):
    dir_copy = tmp_path_factory.mktemp('copy')
    cctool.gate.gate.copy_staged(repo, dir_copy)
    assert (dir_copy / 'src/marker.py').read_text() == 'TEXT = "staged"\n'
    assert not (dir_copy / 'untracked.txt').exists()


def test_a_stage_runs_the_code_of_the_copy(repo):
    stage = _stage('read', 'import marker; print(marker.TEXT)')
    [(_, is_passed, output)] = cctool.gate.gate.gate(repo, (stage,))
    assert is_passed
    assert output.startswith('staged\n')


def test_each_stage_reports_whether_it_passed_and_what_it_printed(repo):
    tuple_stage = (_stage('pass', 'pass'),
                   _stage('fail', 'import sys; print("Wrong."); sys.exit(1)'))
    [(name, is_passed, _), (other, is_failed, output)] = cctool.gate.gate.gate(repo, tuple_stage)
    assert (name, is_passed, other, is_failed) == ('pass', True, 'fail', False)
    assert output.startswith('Wrong.\n')


def test_a_stage_that_runs_too_long_is_stopped_and_fails(repo):
    stage = _stage('slow', 'import time; print("Started.", flush = True); time.sleep(30)')
    [(_, is_passed, output)] = cctool.gate.gate.gate(repo, (stage,), seconds = 2)
    assert not is_passed
    assert output.startswith('Started.\n')
    assert output.endswith('Stopped after 2 s, the time limit of a stage.\n')


def test_a_stage_runs_without_the_git_environment_of_the_hook(repo, monkeypatch):
    monkeypatch.setenv('GIT_INDEX_FILE', str(repo / '.git/index'))
    stage = _stage('env', 'import os; print(os.environ.get("GIT_INDEX_FILE"))')
    [(_, _, output)] = cctool.gate.gate.gate(repo, (stage,))
    assert output.startswith('None\n')


def test_a_tree_that_is_not_a_repository_cannot_be_gated(tmp_path):
    with pytest.raises(cctool.gate.gate.ErrorGate) as info:
        cctool.gate.gate.gate(tmp_path, (_stage('pass', 'pass'),))
    assert str(info.value).startswith('The staged content cannot be copied: ')


def test_the_command_prints_a_failure_before_its_verdict(repo, monkeypatch):
    monkeypatch.setattr(cctool.gate.gate, 'TUPLE_STAGE',
                        (_stage('pass', 'pass'),
                         _stage('fail', 'import sys; print("Wrong."); sys.exit(1)')))
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['gate', '--root', str(repo)])
    assert result.exit_code == 1
    assert result.stdout.startswith('pass: passed\nWrong.\n')
    assert result.stdout.endswith('\nfail: failed\n')


def test_a_commit_that_stages_only_data_leaves_out_the_tests(repo):
    _commit(repo)
    (repo / '_data').mkdir()
    (repo / '_data/item.yaml').write_text('title: Data\n')
    _git(repo, 'add', '_data/item.yaml')
    assert not cctool.gate.gate.is_code_staged(repo)
    assert [name for (name, _) in cctool.gate.gate.stages(repo)] == ['check', 'lint']


def test_a_commit_that_stages_code_runs_the_tests(repo):
    _commit(repo)
    _git(repo, 'rm', '--quiet', '--cached', 'src/marker.py')
    assert cctool.gate.gate.is_code_staged(repo)
    map_stage = dict(cctool.gate.gate.stages(repo))
    assert list(map_stage) == ['check', 'lint', 'test']
    assert cctool.gate.gate.MARK_COMMIT in map_stage['test']
    assert cctool.gate.gate.MARK_PUSH in dict(cctool.gate.gate.TUPLE_STAGE)['test']


def test_the_first_commit_runs_the_tests(repo):
    assert cctool.gate.gate.is_code_staged(repo)


def test_the_command_says_when_it_leaves_out_the_tests(repo, monkeypatch):
    _commit(repo)
    _git(repo, 'add', 'untracked.txt')
    monkeypatch.setattr(cctool.gate.gate, 'TUPLE_STAGE',
                        (_stage('check', 'pass'),
                         _stage('test', 'import sys; sys.exit(1)')))
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['gate', '--root', str(repo)])
    assert result.exit_code == 0
    assert result.stdout == 'check: passed\ntest: skipped, as no code is staged\n'


def test_the_gate_of_a_commit_keeps_a_store_in_the_git_directory(repo):
    stage = _stage('store', 'import os; print(os.environ.get("CC_PUBLIC_STORE"))')
    [(_, _, output)] = cctool.gate.gate.gate(repo, (stage,))
    assert output.startswith('{dir}\n'.format(
                                 dir = (repo / '.git').resolve() / cctool.gate.gate.DIR_STORE))


def test_the_gate_of_a_commit_already_made_uses_no_store(repo, monkeypatch):
    _commit(repo)
    monkeypatch.setenv('CC_PUBLIC_STORE', str(repo / 'elsewhere'))
    stage = _stage('store', 'import os; print(os.environ.get("CC_PUBLIC_STORE"))')
    [(_, _, output)] = cctool.gate.gate.gate(repo, (stage,), rev = 'HEAD')
    assert output.startswith('None\n')


def _logged(root):
    """
    Return the lines of the log of timings of root.

    """

    return cctool.gate.timing.read(cctool.gate.gate.timing_log(root))


def test_each_run_of_the_gate_logs_each_stage_in_the_git_directory(repo):
    tuple_stage = (_stage('pass', 'pass'),
                   _stage('fail', 'import sys; sys.exit(1)'))
    cctool.gate.gate.gate(repo, tuple_stage)
    [first, second] = _logged(repo)
    assert cctool.gate.gate.timing_log(repo) == (repo / '.git').resolve() / 'cctool_timing.jsonl'
    assert (first['stage'], first['outcome'], second['stage'], second['outcome']) == (
            'pass', 'passed', 'fail', 'failed')
    assert first['run'] == second['run']
    assert first['seconds'] >= 0
    assert first['seconds_cpu_run'] >= 0
    assert first['tree'] == subprocess.run(['git', 'write-tree'], cwd = repo, check = True,
                                           capture_output = True, text = True).stdout.strip()
    assert first['commit'] is None
    assert first['python'] == platform.python_version()
    assert 'tests' not in first


def test_a_later_run_appends_to_the_log(repo):
    cctool.gate.gate.gate(repo, (_stage('pass', 'pass'),))
    cctool.gate.gate.gate(repo, (_stage('pass', 'pass'),))
    [first, second] = _logged(repo)
    assert first['run'] != second['run']


def test_a_stage_stopped_for_its_time_is_logged_as_stopped(repo):
    cctool.gate.gate.gate(repo, (_stage('slow', 'import time; time.sleep(30)'),), seconds = 1)
    [line] = _logged(repo)
    assert line['outcome'] == 'stopped'
    assert line['seconds'] >= 1


def test_the_gate_of_a_commit_already_made_logs_the_commit(repo):
    _commit(repo)
    cctool.gate.gate.gate(repo, (_stage('pass', 'pass'),), rev = 'HEAD')
    [line] = _logged(repo)
    head = subprocess.run(['git', 'rev-parse', 'HEAD', 'HEAD^{tree}'], cwd = repo, check = True,
                          capture_output = True, text = True).stdout.split()
    assert [line['commit'], line['tree']] == head


def test_the_tests_log_the_seconds_of_each_test(repo):
    (repo / 'src/test_marker.py').write_text('def test_one():\n    pass\n')
    _git(repo, 'add', 'src/test_marker.py')
    stage = ('test', ('{python}', '-m', 'pytest', '-p', 'no:cacheprovider', 'src',
                      '--junitxml={report}'))
    [(_, is_passed, _)] = cctool.gate.gate.gate(repo, (stage,))
    assert is_passed
    [line] = _logged(repo)
    assert list(line['tests']) == ['src.test_marker::test_one']


def test_the_real_tests_report_the_seconds_of_each_test():
    assert '--junitxml={report}' in dict(cctool.gate.gate.TUPLE_STAGE)['test']

