"""
---

id_self:                pym_cctool.commit._test.test_change
guid_self:              pym_c92d128efbd74fbfb7f21f9ea72566c9
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit change tests
brief:                  |
                        Tests of checking a commit against the graph
                        before and after it.
description:            |
                        Each test commits a copy of the repository,
                        stages a change to it, and checks the change
                        under a commit item.
edge:                   []

...
"""


import os
import subprocess
import uuid

import pytest

import cctool.commit.change
import cctool.edit.edit


pytestmark = pytest.mark.prepush


HOOK      = '.githooks/commit-msg'
ID_HOOK   = 'shell_githooks_commit_msg'
GUID_HOOK = 'shell_62b23a71a636401eb534266abaf6933d'
REGISTER  = '_data/register/reg_writing_style_rule.yaml'
ID_STYLE  = 'style_commit_title_template'
ICD       = '_data/interface_control_document/icd_cctool_check.yaml'
ID_MEMBER = 'icm_cctool_check.failures'


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tree, monkeypatch):
    """
    Return the root of a copy of the repository, committed.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet')
    _commit(tree)
    return tree


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root.

    """

    subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', *list_arg],
                   cwd = root, check = True, capture_output = True)


def _commit(root):
    """
    Commit everything in root.

    """

    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--message', 'x')


def _check(root, title, brief = 'A change.'):
    """
    Stage everything in root, and return the failures of committing it
    under an item with title and brief.

    """

    _git(root, 'add', '--all')
    return cctool.commit.change.check(root, {'title': title, 'brief': brief})


def _rename(root, id_old, id_new):
    """
    Rename id_old to id_new in root with cctool rename, as one edit.

    """

    tree = cctool.edit.edit.Tree(root)
    cctool.edit.edit.batch(tree, [{'rename': [id_old, id_new]}])
    assert cctool.edit.edit.apply(tree) == {}


def _replace(root, relative, old, new):
    """
    Replace old with new in the file at relative.

    """

    path = root / relative
    path.write_text(path.read_text().replace(old, new))


def test_a_commit_that_changes_no_item_passes(repo):
    _replace(repo, 'README.md', 'Capability Commons', 'Capability commons')
    assert _check(repo, 'Change README.md so that its title is in sentence case') == {}


def test_an_unannounced_removal_is_reported(repo):
    (repo / HOOK).unlink()
    assert _check(repo, 'Remove the commit-msg hook') == {
        'unannounced_removal': [(ID_HOOK, GUID_HOOK)]}


def test_a_removal_the_commit_names_passes(repo):
    (repo / HOOK).unlink()
    assert _check(repo, 'Remove the commit-msg hook', 'Removes ' + ID_HOOK + '.') == {}


def test_a_verb_the_change_contradicts_is_reported(repo):
    (repo / HOOK).unlink()
    assert _check(repo, 'Add nothing', 'Removes ' + ID_HOOK + '.') == {
        'verb_contradicted': [('Add', 'remove', ID_HOOK)]}


def test_a_renamed_entry_without_its_old_id_as_alias_is_reported(repo):
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Rename {id} to style_commit_titles'.format(id = ID_STYLE)) == {
        'rename_without_alias': [(ID_STYLE, 'style_commit_titles')]}


def test_a_revert_of_a_rename_needs_no_alias(repo):
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd = repo, check = True,
                          capture_output = True, text = True).stdout.strip()
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Revert "Rename {id} to style_commit_titles"'.format(id = ID_STYLE),
                  'This reverts commit {head}.'.format(head = head)) == {}


@pytest.mark.parametrize('brief', ['A change.', 'This reverts commit {zero}.'.format(zero = '0' * 40)])
def test_a_revert_that_names_no_earlier_commit_needs_an_alias(repo, brief):
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Revert "Rename {id} to style_commit_titles"'.format(id = ID_STYLE),
                  brief) == {'rename_without_alias': [(ID_STYLE, 'style_commit_titles')]}


def test_an_item_that_keeps_its_id_and_takes_a_new_guid_is_reported(repo):
    guid = 'shell_' + uuid.uuid4().hex
    _replace(repo, HOOK, GUID_HOOK, guid)
    assert _check(repo, 'Change the hook so that its guid is new', 'Changes ' + ID_HOOK + '.') == {
        'reguided_item': [(ID_HOOK, GUID_HOOK, guid)]}


def test_a_file_that_holds_no_item_is_removed_only_by_its_path(repo):
    (repo / 'NOTICE').unlink()
    title = 'Change the notices so that there are none'
    assert _check(repo, title) == {'unannounced_file_removal': [('NOTICE',)]}
    assert _check(repo, title, 'Removes NOTICE.') == {}
    assert _check(repo, 'Add nothing', 'Removes NOTICE.') == {
        'verb_contradicted': [('Add', 'remove', 'NOTICE')]}


def test_a_file_that_holds_no_item_moved_elsewhere_is_not_removed(repo):
    path = repo / 'src/cctool/_test/_fixture/x.json'
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text('{}\n')
    _commit(repo)
    path.rename(path.with_name('y.json'))
    assert _check(repo, 'Move the fixture x.json to y.json') == {}


def test_an_unannounced_rename_is_reported(repo):
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Change the register so that it is tidy') == {
        'rename_without_alias': [(ID_STYLE, 'style_commit_titles')],
        'unannounced_rename':   [(ID_STYLE, 'style_commit_titles')]}


def test_a_renamed_member_needs_no_alias(repo):
    _replace(repo, ICD, ID_MEMBER, 'icm_cctool_check.failure_map')
    assert _check(repo, 'Rename {id} to icm_cctool_check.failure_map'.format(
                                                                    id = ID_MEMBER)) == {}


def test_an_unannounced_rename_of_a_member_asks_for_no_alias(repo):
    _replace(repo, ICD, ID_MEMBER, 'icm_cctool_check.failure_map')
    assert _check(repo, 'Change the interface so that it is tidy') == {
        'unannounced_rename': [(ID_MEMBER, 'icm_cctool_check.failure_map')]}


@pytest.mark.parametrize(('id_old', 'id_new'), [
    (ID_MEMBER,                            'icm_cctool_check.failure_map'),
    ('dfn_stableflow_smoketest.ctrl_proc', 'dfn_stableflow_smoketest.proc_ctrl'),
    ('icd_cctool_check',                   'icd_cctool_checks'),
    ('dfg_stableflow_smoketest',           'dfg_stableflow_smoke'),
])
def test_a_rename_made_with_cctool_passes(repo, id_old, id_new):
    _rename(repo, id_old, id_new)
    assert _check(repo, 'Rename {old} to {new}'.format(old = id_old, new = id_new)) == {}


def test_the_members_of_a_renamed_document_are_named_with_it(repo):
    _rename(repo, 'icd_cctool_check', 'icd_cctool_checks')
    assert _check(repo, 'Change the interface so that it is tidy',
                  'Renames icd_cctool_check.') == {}
    _git(repo, 'reset', '--quiet')
    assert _check(repo, 'Change the interface so that it is tidy')[
        'unannounced_rename'][0] == ('icd_cctool_check', 'icd_cctool_checks')


def test_a_guid_given_another_prefix_is_reported(repo):
    _replace(repo, HOOK, GUID_HOOK, 'sch_' + GUID_HOOK[5:])
    assert _check(repo, 'Change the hook so that its guid is wrong',
                  'Changes ' + ID_HOOK + '.')['retyped_guid'] == [
        (GUID_HOOK, 'sch_' + GUID_HOOK[5:])]


def test_a_reformat_that_changes_only_layout_passes(repo):
    _replace(repo, REGISTER, 'title:              Commit titles from templates',
                             'title: Commit titles from templates')
    _commit(repo)
    _replace(repo, REGISTER, 'title: Commit titles from templates',
                             'title:              Commit titles from templates')
    assert _check(repo, 'Reformat ' + REGISTER) == {}


def test_a_reformat_that_changes_content_is_reported(repo):
    _replace(repo, 'README.md', 'Capability Commons', 'Capability commons')
    assert _check(repo, 'Reformat README.md') == {
        'reformat_changes_content': [('README.md',)]}


def test_the_first_commit_adds_everything(tree, monkeypatch):
    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet')
    assert _check(tree, 'Add the first version of cc-public') == {}


def _edit(root, *list_operation):
    """
    Make the operations over root as one edit, which must add no
    failures.

    """

    tree = cctool.edit.edit.Tree(root)
    cctool.edit.edit.batch(tree, list(list_operation))
    assert cctool.edit.edit.apply(tree) == {}


def test_a_ruling_made_while_a_driver_is_unargued_is_reported(repo):
    _edit(repo,
          {'link': ['dec_tooling_language', 'relation_is_driven_by', 'concern_privacy']},
          {'new':   'ruling_tooling_language',
           'field': {'title': 'Tooling in Python', 'brief': 'Write the tooling in Python.'},
           'link':  [['relation_upholds', 'opt_tooling_in_python']]})
    assert _check(repo, 'Add a ruling on the tooling language') == {'unargued_driver': [
        ('ruling_tooling_language', 'opt_tooling_in_python', 'concern_privacy')]}


def test_a_driver_added_after_a_ruling_leaves_it_standing(repo):
    _edit(repo, {'link': ['dec_cross_item_checks_engine', 'relation_is_driven_by',
                          'concern_privacy']})
    assert _check(repo, 'Change dec_cross_item_checks_engine so that privacy drives it') == {}


def test_a_ruling_revisited_to_uphold_another_option_is_judged_again(repo):
    _edit(repo, {'link': ['dec_cross_item_checks_engine', 'relation_is_driven_by',
                          'concern_privacy']})
    _commit(repo)
    _edit(repo,
          {'unlink': ['ruling_cross_item_checks_engine', 'relation_upholds',
                      'opt_cross_item_checks_in_clingo']},
          {'unlink': ['ruling_cross_item_checks_engine', 'relation_rejects',
                      'opt_cross_item_checks_in_python']},
          {'link':   ['ruling_cross_item_checks_engine', 'relation_upholds',
                      'opt_cross_item_checks_in_python']},
          {'link':   ['ruling_cross_item_checks_engine', 'relation_rejects',
                      'opt_cross_item_checks_in_clingo']})
    assert _check(repo, 'Change ruling_cross_item_checks_engine so that Python is upheld') == {
        'unargued_driver': [('ruling_cross_item_checks_engine', 'opt_cross_item_checks_in_python',
                             'concern_privacy')]}
