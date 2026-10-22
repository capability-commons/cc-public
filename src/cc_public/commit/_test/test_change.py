"""
---

id_self:                pym_cc_public.commit._test.test_change
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

import pytest

import cc_public.commit.change


pytestmark = pytest.mark.prepush


HOOK      = '.githooks/commit-msg'
ID_HOOK   = 'shell_githooks_commit_msg'
GUID_HOOK = 'shell_62b23a71a636401eb534266abaf6933d'
REGISTER  = '_data/register/reg_writing_style_rule.yaml'
ID_STYLE  = 'style_commit_title_template'


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
    return cc_public.commit.change.check(root, {'title': title, 'brief': brief})


def _replace(root, relative, old, new):
    """
    Replace old with new in the file at relative.

    """

    path = root / relative
    path.write_text(path.read_text().replace(old, new))


def test_a_commit_that_changes_no_item_passes(repo):
    _replace(repo, 'README.md', 'Capability commons', 'Capability Commons')
    assert _check(repo, 'Change README.md so that its title is capitalized') == {}


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
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Revert "Rename {id} to style_commit_titles"'.format(id = ID_STYLE)) == {}


def test_an_unannounced_rename_is_reported(repo):
    _replace(repo, REGISTER, ID_STYLE, 'style_commit_titles')
    assert _check(repo, 'Change the register so that it is tidy') == {
        'rename_without_alias': [(ID_STYLE, 'style_commit_titles')],
        'unannounced_rename':   [(ID_STYLE, 'style_commit_titles')]}


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
    _replace(repo, 'README.md', 'Capability commons', 'Capability Commons')
    assert _check(repo, 'Reformat README.md') == {
        'reformat_changes_content': [('README.md',)]}


def test_the_first_commit_adds_everything(tree, monkeypatch):
    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet')
    assert _check(tree, 'Add the first version of cc-public') == {}
