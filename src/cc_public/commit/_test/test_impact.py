"""
---

id_self:                pym_cc_public.commit._test.test_impact
guid_self:              pym_6db7c7e8ab8b412e993b365e823a8a74
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit impact tests
brief:                  |
                        Tests of what cctool impact finds a change
                        touches, and what it finds around it.
description:            |
                        Each test changes a copy of the repository and
                        compares the result with the copy as it was
                        before.
relation:               []

...
"""


import os
import shutil
import subprocess

import click.testing
import pytest

import cc_public.cli.command
import cc_public.commit.impact


ISSUE      = '_data/issue/iss_tooling_language/'
ANN        = 'ann_a_port_costs_a_rewrite'
FILE_ANN   = ISSUE + ANN + '.yaml'
FILE_CHECK = 'src/cc_public/check/check.py'
PYF_CHECK  = 'pyf_cc_public.check.check.check'
PYM_CHECK  = 'pym_cc_public.check.check'


# -----------------------------------------------------------------------------
@pytest.fixture
def before(tree, tmp_path_factory):
    """
    Return the root of a copy of tree, made before a test changes tree.

    """

    dir_before = tmp_path_factory.mktemp('before')
    shutil.copytree(tree, dir_before, dirs_exist_ok = True)
    return dir_before


# -----------------------------------------------------------------------------
def _edit(tree, file, old, new):
    """
    Replace old, which must occur in file under tree, with new.

    """

    path = tree / file
    text = path.read_text(encoding = 'utf-8')
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding = 'utf-8')


def _touched(result):
    """
    Return the id, delta and former id of each touched item of result.

    """

    return [row[:3] for row in result['touched']]


def _links(result):
    """
    Return the id, depth, via, relation and direction of each
    neighbour of result.

    """

    return {row[:5] for row in result['neighbour']}


# -----------------------------------------------------------------------------
def test_no_change_touches_nothing(tree, before):
    result = cc_public.commit.impact.impact_trees(before, tree)
    assert result == {'touched': [], 'neighbour': []}


# -----------------------------------------------------------------------------
def test_a_changed_annotation_shows_what_it_argues_about(tree, before):
    _edit(tree, FILE_ANN, 'Moving to Rust now', 'A move to Rust now')

    result = cc_public.commit.impact.impact_trees(before, tree)

    assert _touched(result) == [(ANN, 'changed', '')]
    assert _links(result) == {
        ('opt_tooling_in_rust',  '1', ANN, 'r_challenges',         'out'),
        ('iss_tooling_language', '1', ANN, 'r_is_about',           'out'),
        ('concern_cost',         '1', ANN, 'r_argues_for_concern', 'out'),
        ('mark_public',          '1', ANN, 'mark',                 'out'),
        ('t_annotation',         '1', ANN, 'has_type',             'out'),
        ('r_challenges',         '1', ANN, 'uses',                 'out'),
        ('r_is_about',           '1', ANN, 'uses',                 'out'),
        ('r_argues_for_concern', '1', ANN, 'uses',                 'out')}
    assert result['touched'][0][3:] == (FILE_ANN, '1')


# -----------------------------------------------------------------------------
def test_a_walk_keeps_its_direction(tree, before):
    _edit(tree, FILE_ANN, 'Moving to Rust now', 'A move to Rust now')

    result = cc_public.commit.impact.impact_trees(before, tree, depth = 2, direction = 'in')

    assert _touched(result) == [(ANN, 'changed', '')]
    assert result['neighbour'] == []


# -----------------------------------------------------------------------------
def test_a_removed_item_shows_what_it_linked_to(tree, before):
    (tree / FILE_ANN).unlink()

    result = cc_public.commit.impact.impact_trees(before, tree, direction = 'out')

    assert _touched(result) == [(ANN, 'removed', '')]
    assert ('opt_tooling_in_rust', '1', ANN, 'r_challenges', 'out') in _links(result)
    assert result['touched'][0][3:] == (FILE_ANN, '1')


# -----------------------------------------------------------------------------
def test_a_renamed_item_names_the_id_it_had(tree, before):
    _edit(tree, FILE_ANN, 'id_self:                ' + ANN, 'id_self:                ann_x')

    result = cc_public.commit.impact.impact_trees(before, tree)

    assert _touched(result) == [('ann_x', 'renamed', ANN)]


# -----------------------------------------------------------------------------
def test_a_change_of_code_touches_its_function_and_module(tree, before):
    _edit(tree, FILE_CHECK, '    return review(root)[0]\n', '    return review(root = root)[0]\n')

    result = cc_public.commit.impact.impact_trees(before, tree, direction = 'out')

    assert _touched(result) == [(PYF_CHECK, 'changed', ''), (PYM_CHECK, 'changed', '')]
    assert ('icm_cc_public_check.check', '1', PYF_CHECK, 'r_realizes', 'out') in _links(result)


# -----------------------------------------------------------------------------
def test_an_item_reaches_the_items_that_use_its_relation(tree, before):
    _edit(tree, '_data/register/reg_relation.yaml',
          'brief:              SUBJ gives a reason not to accept OBJ',
          'brief:              SUBJ gives a reason to doubt OBJ')

    result = cc_public.commit.impact.impact_trees(before, tree, direction = 'in')

    assert _touched(result) == [('r_challenges', 'changed', '')]
    assert ('ann_a_port_costs_a_rewrite', '1', 'r_challenges', 'uses', 'in') in _links(result)


# -----------------------------------------------------------------------------
def test_an_unknown_direction_is_refused(tree, before):
    with pytest.raises(ValueError, match = 'sideways'):
        cc_public.commit.impact.impact_trees(before, tree, direction = 'sideways')


# -----------------------------------------------------------------------------
def test_cctool_impact_prints_each_neighbour_once(tree, monkeypatch):
    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet')
    _git(tree, 'add', '--all')
    _git(tree, 'commit', '--quiet', '--no-verify', '--message', 'x')
    _edit(tree, FILE_ANN, 'Moving to Rust now', 'A move to Rust now')
    _git(tree, 'add', '--all')

    result = click.testing.CliRunner().invoke(
                 cc_public.cli.command.main,
                 ['impact', '--staged', '--direction', 'out', '--root', str(tree)])

    assert result.exit_code == 0, result.output
    list_line = result.output.splitlines()
    assert list_line[:2] == ['changed  {ann}  {file}:1'.format(ann = ANN, file = FILE_ANN),
                             '1 touched.']
    assert '     {ann} r_challenges opt_tooling_in_rust'.format(ann = ANN) in list_line
    assert list_line[-1] == '8 neighbours untouched.'


def _git(root, *list_arg):
    """
    Run git with list_arg in root.

    """

    subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', *list_arg],
                   cwd = root, check = True, capture_output = True)
