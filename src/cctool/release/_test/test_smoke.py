"""
---

id_self:                pym_cctool.release._test.test_smoke
guid_self:              pym_5b2bedaf0f0d494eba4dcb343ec48809
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Smoke test tests
brief:                  |
                        Tests of the smoke test of a release, and of
                        cctool release smoke.
description:            |
                        git and each program the smoke test runs are
                        stood in for, so that a test says which steps
                        run, in which order, and what is reported when
                        one fails, without building or installing
                        anything. The smoke test itself was run on a
                        commit of the repository by hand when it was
                        written.
edge:                   []

...
"""


import pathlib

import click.testing
import pytest

import cctool.cli.command
import cctool.gate.gate
import cctool.release.smoke


# -----------------------------------------------------------------------------
def _write(dir_data, map_text):
    """
    Write each text of map_text to the file under dir_data that its key
    names.

    """

    for (name, text) in map_text.items():
        path = dir_data / name
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_text(text, encoding = 'utf-8')


# -----------------------------------------------------------------------------
@pytest.fixture
def stub(monkeypatch, tmp_path):
    """
    Stand in for git and for each program that the smoke test runs, and
    return the list of the programs run, each as its arguments. Each
    program exits with 0 unless the dict the fixture gives with it maps
    one of its arguments to another status.

    """

    dir_package = tmp_path / 'package' / '_data'
    _write(dir_package, {'register/reg_a.yaml': 'a\n'})

    def copy_commit(root, rev, dir_copy):
        _write(dir_copy / '_data', {'register/reg_a.yaml': 'a\n'})

    list_run  = []
    map_fails = {}

    def run(list_arg, cwd):
        list_run.append([pathlib.Path(list_arg[0]).name, *list_arg[1:]])
        code = next((map_fails[arg] for arg in list_arg if arg in map_fails), 0)
        if '-c' in list_arg and list_arg[list_arg.index('-c') + 1] == cctool.release.smoke.SCRIPT_BUILD:
            return (code, 'cc_public-0.1.0-py3-none-any.whl\n')
        if '-c' in list_arg:
            return (code, '{dir}\n'.format(dir = dir_package))
        return (code, 'said by {name}\n'.format(name = list_arg[-1]))

    monkeypatch.setattr(cctool.gate.gate, 'copy_commit', copy_commit)
    monkeypatch.setattr(cctool.release.smoke, '_run', run)
    return (list_run, map_fails, dir_package)


def test_the_same_data_with_shadows_besides_passes(tmp_path):
    _write(tmp_path / 'tree', {'register/reg_a.yaml': 'a\n', 'schema/sch_a.yaml': 's\n'})
    _write(tmp_path / 'package', {'register/reg_a.yaml': 'a\n', 'schema/sch_a.yaml': 's\n',
                                  'shadow/segment_cc_public.yaml': 'x\n'})
    assert cctool.release.smoke.data_differences(tmp_path / 'tree', tmp_path / 'package') == []


@pytest.mark.parametrize('map_text', [{'register/reg_a.yaml': 'b\n'},
                                      {},
                                      {'register/reg_a.yaml': 'a\n', 'register/reg_b.yaml': 'b\n'}])
def test_data_that_differs_from_the_commit_is_reported(tmp_path, map_text):
    _write(tmp_path / 'tree', {'register/reg_a.yaml': 'a\n'})
    _write(tmp_path / 'package', map_text)
    [found] = cctool.release.smoke.data_differences(tmp_path / 'tree', tmp_path / 'package')
    assert found.startswith('The installed package does not hold the data of the commit: ')
    assert found.endswith('such as register/reg_{x}.yaml.'.format(x = 'b' if len(map_text) == 2
                                                                         else 'a'))


def test_a_commit_whose_steps_all_pass_passes(stub, tmp_path):
    (list_run, _, _) = stub
    list_said = []
    assert cctool.release.smoke.smoke(tmp_path, 'HEAD', tmp_path / 'work', list_said.append) == []
    assert [each[1:3] for each in list_run] == [['-c', cctool.release.smoke.SCRIPT_BUILD],
                                                ['-m', 'venv'],
                                                ['-m', 'pip'],
                                                ['-c', cctool.release.smoke.SCRIPT_DATA],
                                                ['check', '--root'],
                                                ['peer', 'init'],
                                                ['check', '--root'],
                                                ['peer', 'status']]
    assert list_run[4][0] == 'cctool'
    assert list_said[0] == 'Copying HEAD as git stores it.'


def test_a_wheel_that_cannot_be_built_stops_the_smoke_test(stub, tmp_path):
    (list_run, map_fails, _) = stub
    map_fails[cctool.release.smoke.SCRIPT_BUILD] = 1
    found = cctool.release.smoke.smoke(tmp_path, 'v1.0.0', tmp_path / 'work', print)
    assert found == ['The wheel cannot be built from v1.0.0:\n  cc_public-0.1.0-py3-none-any.whl']
    assert len(list_run) == 1


def test_a_failed_check_and_a_failed_peer_are_each_reported(stub, tmp_path):
    (list_run, map_fails, _) = stub
    map_fails['check'] = 1
    found = cctool.release.smoke.smoke(tmp_path, 'HEAD', tmp_path / 'work', print)
    assert [each.split('\n')[0] for each in found] == [
        'The installed cctool check of HEAD exits with 1:',
        'The installed cctool check of the fixture peer exits with 1:']
    assert list_run[-1][1] == 'check'


def test_a_package_without_the_data_of_the_commit_fails(stub, tmp_path):
    (_, _, dir_package) = stub
    (dir_package / 'register' / 'reg_a.yaml').write_text('changed\n', encoding = 'utf-8')
    [found] = cctool.release.smoke.smoke(tmp_path, 'HEAD', tmp_path / 'work', print)
    assert found.startswith('The installed package does not hold the data of the commit')


@pytest.mark.parametrize(('list_found', 'code', 'verdict'), [([], 0, 'HEAD passes'),
                                                             (['A step failed.'], 1, 'HEAD fails')])
def test_smoke_says_whether_the_commit_passes(monkeypatch, tmp_path, list_found, code, verdict):
    monkeypatch.setattr(cctool.release.smoke, 'smoke',
                        lambda *_: list_found)
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['release', 'smoke', '--root', str(tmp_path)])
    assert result.exit_code == code
    assert result.stdout.endswith('{verdict} the smoke test of the release gate.\n'.format(
                                      verdict = verdict))


def test_smoke_of_a_commit_that_cannot_be_copied_exits_with_2(monkeypatch, tmp_path):
    def smoke(root, rev, dir_work, say):
        raise cctool.gate.gate.ErrorGate('The commit nope cannot be read.')

    monkeypatch.setattr(cctool.release.smoke, 'smoke', smoke)
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['release', 'smoke', 'nope', '--root', str(tmp_path)])
    assert result.exit_code == 2
    assert result.stderr == 'The commit nope cannot be read.\n'
