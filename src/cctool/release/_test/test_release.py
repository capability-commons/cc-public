"""
---

id_self:                pym_cctool.release._test.test_release
guid_self:              pym_121c6563d00b4dbfaabdc2c5a5b51f15
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Release tests
brief:                  |
                        Tests of the release step: the bump, the
                        runtime packages of the lock, the release item
                        and the check of a tag candidate.
description:            |
                        The tests that commit run in a copy of the
                        repository, committed without hooks, and are
                        marked prepush, since they test the history
                        machinery.
edge:                   []

...
"""


import os
import shutil
import subprocess

import click.testing
import pytest

import cctool.cli.command
import cctool.commit.message
import cctool.conftest
import cctool.edit.edit
import cctool.release.record
import cctool.release.release


# A lock of one platform, as pixi writes it: the project needs click,
# which needs colorama only on Windows, and clingo, which a conda
# package provides and which needs python. pytest is there only to
# develop with.
#
TEXT_LOCK = """
version: 6
environments:
  default:
    packages:
      linux-64:
      - conda: https://conda.anaconda.org/conda-forge/linux-64/python-3.15.0-h6e52b48_101_cp315.conda
      - conda: https://conda.anaconda.org/conda-forge/linux-64/clingo-5.8.2-py315h62b6238_1.conda
      - conda: https://conda.anaconda.org/conda-forge/noarch/pytest-9.1.1-pyhc364b38_2.conda
      - pypi: https://files.pythonhosted.org/packages/58/50/click-8.5.0-py3-none-any.whl
      - pypi: ./
packages:
- conda: https://conda.anaconda.org/conda-forge/linux-64/python-3.15.0-h6e52b48_101_cp315.conda
  sha256: {a}
  depends:
  - __glibc >=2.17,<3.0.a0
- conda: https://conda.anaconda.org/conda-forge/linux-64/clingo-5.8.2-py315h62b6238_1.conda
  sha256: {b}
  depends:
  - python >=3.15,<3.16.0a0
  purls:
  - pkg:pypi/clingo?source=hash-mapping
- conda: https://conda.anaconda.org/conda-forge/noarch/pytest-9.1.1-pyhc364b38_2.conda
  sha256: {c}
- pypi: https://files.pythonhosted.org/packages/58/50/click-8.5.0-py3-none-any.whl
  name: click
  version: 8.5.0
  sha256: {d}
  requires_dist:
  - colorama ; sys_platform == 'win32'
  - pytest ; extra == 'test'
- pypi: ./
  name: cc-public
  version: 0.1.0
  sha256: {e}
  requires_dist:
  - click>=8.2,<9
  - clingo>=5.8,<6
""".format(a = 'a' * 64, b = 'b' * 64, c = 'c' * 64, d = 'd' * 64, e = 'e' * 64)


# -----------------------------------------------------------------------------
def test_a_bump_follows_semver_from_one_on():
    assert cctool.release.release.bumped('1.2.3', 'major') == '2.0.0'
    assert cctool.release.release.bumped('1.2.3', 'minor') == '1.3.0'
    assert cctool.release.release.bumped('1.2.3', 'patch') == '1.2.4'


# -----------------------------------------------------------------------------
def test_a_bump_before_one_bumps_the_part_below():
    assert cctool.release.release.bumped('0.2.3', 'major') == '0.3.0'
    assert cctool.release.release.bumped('0.2.3', 'minor') == '0.2.4'
    assert cctool.release.release.bumped('0.2.3', 'patch') == '0.2.4'


# -----------------------------------------------------------------------------
def test_a_bump_of_what_is_not_a_release_version_is_refused():
    with pytest.raises(cctool.release.release.ErrorRelease):
        cctool.release.release.bumped('1.2.3-rc.1', 'patch')


# -----------------------------------------------------------------------------
def test_only_a_public_item_removed_or_renamed_breaks():
    row_code   = ('pym_cctool.x', 'removed', '', 'src/cctool/x.py', '1')
    row_rename = ('style_b', 'renamed', 'style_a', '_data/register/reg_writing_style_rule.yaml', '9')
    row_add    = ('sch_new', 'added', '', '_data/schema/sch_new.yaml', '1')
    assert cctool.release.release.level([row_code]) == ('patch', [])
    assert cctool.release.release.level([row_code, row_add]) == ('minor', [row_add])
    assert cctool.release.release.level([row_add, row_rename]) == ('major', [row_rename])


# -----------------------------------------------------------------------------
def test_the_dependencies_are_what_the_project_needs_to_run():
    list_package = cctool.release.release.dependencies(TEXT_LOCK)
    assert [(package['name'], package['version']) for package in list_package] == [
        ('click', '8.5.0'), ('clingo', '5.8.2'), ('python', '3.15.0')]
    assert list_package[0] == {'platform': 'linux-64', 'name': 'click',
                               'version': '8.5.0', 'sha256': 'd' * 64}


# -----------------------------------------------------------------------------
def test_the_dependencies_are_the_tool_environment_where_there_is_one():
    text = TEXT_LOCK.replace('environments:\n  default:', 'environments:\n  tool:')
    assert [package['name'] for package in cctool.release.release.dependencies(text)] == [
        'click', 'clingo', 'pytest', 'python']


# -----------------------------------------------------------------------------
def test_a_tree_without_a_lock_has_no_dependencies_to_record():
    with pytest.raises(cctool.release.release.ErrorRelease):
        cctool.release.release.dependencies('')


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tree, monkeypatch):
    """
    Return the root of a copy of the repository with a version module,
    committed on main under a message that conforms.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _module(tree)
    _git(tree, 'init', '--quiet', '--initial-branch', 'main')
    _commit(tree, cctool.commit.message.compose('Add the first version of cc-public',
                                                'The first version.'))
    return tree


# -----------------------------------------------------------------------------
@pytest.mark.prepush
def test_the_first_release_takes_the_version_of_the_module(repo):
    result = cctool.release.release.prepare(repo, 'The first release.')
    assert (result['base'], result['version'], result['level']) == (None, '0.1.0', None)
    assert result['written'] == ['_data/release/release_0_1_0.yaml', 'src/cctool/version.py']
    _commit(repo, cctool.commit.message.compose('Add release_0_1_0', 'The first release.'))
    assert cctool.release.release.verify(repo, 'v0.1.0', 'HEAD') == []
    assert cctool.release.release.verify(repo, 'v0.2.0', 'HEAD') == [
        '_data/release/release_0_1_0.yaml records the version 0.1.0, not 0.2.0.',
        'The version module at {short} holds 0.1.0, not 0.2.0.'.format(short = _short(repo))]


# -----------------------------------------------------------------------------
@pytest.mark.prepush
def test_a_rename_of_a_public_item_bumps_the_minor_part_before_one(repo):
    _git(repo, 'tag', 'v0.1.0')
    tree = cctool.edit.edit.Tree(repo)
    tree.update(cctool.edit.edit.rename(tree, 'concern_simplicity', 'concern_plainness'))
    assert cctool.edit.edit.apply(tree) == {}
    _commit(repo, cctool.commit.message.compose('Rename concern_simplicity to concern_plainness',
                                                'A plainer name.'))
    result = cctool.release.release.prepare(repo, 'A plainer name for a concern.')
    assert (result['base'], result['version'], result['level']) == ('v0.1.0', '0.2.0', 'major')
    assert result['renamed'] == [('concern_simplicity', 'concern_plainness')]
    assert result['commit']['concern_simplicity'] == [_short(repo)]
    assert result['notes'] == [(_short(repo), 'Rename concern_simplicity to concern_plainness')]
    assert cctool.release.record.module_version(
               (repo / cctool.release.record.PATH_MODULE).read_text()) == '0.2.0'


# -----------------------------------------------------------------------------
@pytest.mark.prepush
def test_the_release_item_records_the_renames_and_the_check_holds_it_to_them(repo):
    _git(repo, 'tag', 'v0.1.0')
    tree = cctool.edit.edit.Tree(repo)
    guid = tree.guid('concern_simplicity')
    tree.update(cctool.edit.edit.rename(tree, 'concern_simplicity', 'concern_plainness'))
    assert cctool.edit.edit.apply(tree) == {}
    _commit(repo, cctool.commit.message.compose('Rename concern_simplicity to concern_plainness',
                                                'A plainer name.'))
    cctool.release.release.prepare(repo, 'A plainer name for a concern.')
    path = repo / '_data/release/release_0_2_0.yaml'
    item = cctool.edit.edit.Tree(repo).map_document['_data/release/release_0_2_0.yaml'][0]
    assert [dict(rename) for rename in item['rename']] == [
        {'old': 'concern_simplicity', 'new': 'concern_plainness', 'guid': guid}]
    _commit(repo, cctool.commit.message.compose('Add release_0_2_0', 'A plainer name.'))
    assert cctool.release.release.verify(repo, 'v0.2.0', 'HEAD') == []
    path.write_text(path.read_text().replace('new:                concern_plainness',
                                             'new:                concern_plain'))
    _commit(repo, cctool.commit.message.compose('Change release_0_2_0 so that it is wrong',
                                                'A wrong rename.'))
    _git(repo, 'reset', '--quiet', '--soft', 'HEAD~2')
    _commit(repo, cctool.commit.message.compose('Add release_0_2_0', 'A wrong rename.'))
    assert cctool.release.release.verify(repo, 'v0.2.0', 'HEAD') == [
        '_data/release/release_0_2_0.yaml does not record the renames since v0.1.0. Remove the '
        'release item, and run cctool release prepare again.']


# -----------------------------------------------------------------------------
@pytest.mark.prepush
def test_a_commit_that_adds_no_release_item_may_not_be_tagged(repo):
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['release', 'check', 'v0.1.0', '--root', str(repo)])
    assert result.exit_code == 1
    assert result.stdout.startswith('The commit {short} adds 0 release items, not one.'.format(
                                        short = _short(repo)))


# -----------------------------------------------------------------------------
@pytest.mark.prepush
def test_nothing_is_released_twice(repo):
    _git(repo, 'tag', 'v0.1.0')
    with pytest.raises(cctool.release.release.ErrorRelease, match = 'nothing to release'):
        cctool.release.release.prepare(repo, 'Again.')


# -----------------------------------------------------------------------------
def _module(root):
    """
    Copy the version module of the repository into the tree at root.

    """

    path = root / cctool.release.record.PATH_MODULE
    path.parent.mkdir(parents = True, exist_ok = True)
    shutil.copy(cctool.conftest.DIR_REPO / cctool.release.record.PATH_MODULE, path)


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _commit(root, message):
    """
    Commit everything in root under message, without hooks.

    """

    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--allow-empty', '--message', message)


# -----------------------------------------------------------------------------
def _short(root):
    """
    Return the short hash of HEAD in root.

    """

    return _git(root, 'rev-parse', '--short=7', 'HEAD').strip()
