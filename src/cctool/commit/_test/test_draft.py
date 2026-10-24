"""
---

id_self:                pym_cctool.commit._test.test_draft
guid_self:              pym_0470a0ec1f1946e78dea680c3211b540
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit draft tests
brief:                  |
                        Tests of making the message git drafts for a
                        merge or a revert into one that conforms.
description:            |
                        Each test commits a copy of the repository,
                        stages what a merge or revert would, and
                        checks the drafted message and the commit it
                        records.
edge:                   []

...
"""


import os
import subprocess

import click.testing
import pytest

import cctool.cli.command
import cctool.commit.change
import cctool.commit.message


pytestmark = pytest.mark.prepush


TEXT_ANN = ('id_self:                ann_x\n'
            'guid_self:              ann_{hex}\n'
            'copyright:              Copyright 2026 William Payne\n'
            'license:                Apache-2.0\n'
            '\n'
            'protective_mark:\n'
            '\n'
            '  - id_mark:            mark_public\n'
            '    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f\n'
            '\n'
            'title:                  X\n'
            'brief:                  |\n'
            '                        X.\n'
            '\n'
            'edge:\n'
            '\n'
            '  - id_relation:        relation_is_about\n'
            '    guid_relation:      relation_1bb0463a053f42c498e3e9285df99c8f\n'
            '    id_target:          concept_concept\n'
            '    guid_target:        concept_4c11efe184cd47289cfa3941377d4807\n').format(hex = '1' * 32)


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(tree, monkeypatch):
    """
    Return the root of a copy of the repository, committed on main.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)
    _git(tree, 'init', '--quiet', '--initial-branch', 'main')
    _git(tree, 'add', '--all')
    _git(tree, 'commit', '--quiet', '--no-verify', '--message', 'x')
    return tree


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root.

    """

    subprocess.run(['git', '-c', 'user.name=x', '-c', 'user.email=x', *list_arg],
                   cwd = root, check = True, capture_output = True)


# -----------------------------------------------------------------------------
def _passes(root, text):
    """
    Return True if the message text conforms, and the commit of what is
    staged under it passes its check.

    """

    (_, item) = cctool.commit.message.parse(text)
    return (cctool.commit.message.violations(root, text) == []
            and cctool.commit.change.check(root, item) == {})


def test_a_merge_into_the_main_branch_is_given_the_branch_and_an_item(repo):
    text = cctool.commit.message.draft(repo, "Merge branch 'topic'")
    assert text.startswith("Merge branch 'topic' into main\n\n---\n")
    assert "brief:                  |\n                        Merge branch 'topic' into main.\n" in text
    assert _passes(repo, text)


def test_a_revert_keeps_its_body_and_names_what_it_removes(repo):
    (repo / '_data/annotation').mkdir(exist_ok = True)
    (repo / '_data/annotation/ann_x.yaml').write_text(TEXT_ANN)
    _git(repo, 'add', '--all')
    _git(repo, 'commit', '--quiet', '--no-verify', '--message', 'Add an annotation')
    _git(repo, 'revert', '--no-commit', 'HEAD')
    text = cctool.commit.message.draft(repo, 'Revert "Add an annotation"\n\n'
                                                'This reverts commit 1234567.\n')
    assert text.startswith('Revert "Add an annotation"\n\n---\n')
    assert 'This reverts commit 1234567.\n' in text
    assert 'description:            |\n                        It removes ann_x.\n' in text
    assert _passes(repo, text)


def test_a_revert_of_a_long_title_quotes_as_much_as_fits(repo):
    title = 'Change ' + 'x' * 72
    text  = cctool.commit.message.draft(repo, 'Revert "{title}"\n'.format(title = title))
    (subject, _, _) = text.partition('\n')
    assert subject == 'Revert "{quoted}..."'.format(quoted = title[:68])
    assert len(subject) == 80
    assert _passes(repo, text)


def test_a_draft_that_cannot_be_made_leaves_the_message_and_exits_0(repo, monkeypatch):
    def _fail(root, text):
        raise ValueError('Bad YAML')

    monkeypatch.setattr(cctool.commit.message, 'draft', _fail)
    path = repo / 'MSG'
    path.write_text('Merge branch \'x\'\n')
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['message', 'draft', str(path), '--root', str(repo)])
    assert result.exit_code == 0
    assert result.stderr == 'No draft: Bad YAML\n'
    assert path.read_text() == 'Merge branch \'x\'\n'


def test_the_comments_of_the_draft_are_kept_after_it(repo):
    text = cctool.commit.message.draft(repo, "Merge branch 'topic'\n# Conflicts:\n#\tREADME.md\n")
    assert text.endswith('...\n\n# Conflicts:\n#\tREADME.md')


@pytest.mark.parametrize('text', [
    'Add an annotation\n',
    "Merge branch 'topic' into main\n\n---\n\nid_self: x\n\n...\n",
])
def test_any_other_message_is_left_as_it_is(repo, text):
    assert cctool.commit.message.draft(repo, text) == text
