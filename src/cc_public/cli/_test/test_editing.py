"""
---

id_self:                pym_cc_public.cli._test.test_editing
guid_self:              pym_d203fbe35763494eb549a6ef16939ab3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Editing command tests
brief:                  |
                        Tests of the editing commands, as the command
                        line presents them.
description:            |
                        Each test runs a command over a copy of the
                        repository, and checks what it writes, what it
                        prints and its exit status.
relation:               []

...
"""


import click.testing

import cc_public.cli.command


LIST_ANN = ['new', 'ann_x', '--field', 'title', 'Edits work', '--field', 'brief', 'They do.']


# -----------------------------------------------------------------------------
def _run(tree, *list_arg, stdin = None):
    """
    Return the result of cctool with list_arg, over tree.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main, [*list_arg, '--root', str(tree)],
                         input = stdin)


def test_new_writes_the_item_and_says_where(tree):
    result = _run(tree, *LIST_ANN, '--link', 'r_is_about', 'con_concept')
    assert result.exit_code == 0
    assert result.stdout == 'Wrote _data/annotation/ann_x.yaml\n'
    assert (tree / '_data/annotation/ann_x.yaml').exists()


def test_a_field_named_twice_is_a_list(tree):
    result = _run(tree, 'new', 'concern_x',
                  '--field', 'title', 'X',
                  '--field', 'brief', 'X.',
                  '--field', 'description', 'X.',
                  '--field', 'question', 'Is it X?',
                  '--field', 'question', 'Is it Y?',
                  '--field', 'measure', 'X, in percent.',
                  '--field', 'measure', 'X, per release.')
    assert result.exit_code == 0
    assert ('    measure:\n'
            '      - X, in percent.\n'
            '      - X, per release.\n') in (tree / '_data/register/reg_concern.yaml').read_text()


def test_dry_run_prints_a_diff_and_writes_nothing(tree):
    result = _run(tree, *LIST_ANN, '--link', 'r_is_about', 'con_concept', '--dry-run')
    assert result.exit_code == 0
    assert result.stdout.startswith('--- a/_data/annotation/ann_x.yaml\n'
                                    '+++ b/_data/annotation/ann_x.yaml\n'
                                    '@@ -0,0 +1,20 @@\n'
                                    '+id_self:                ann_x\n')
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_an_edit_that_adds_a_failure_is_refused(tree):
    result = _run(tree, *LIST_ANN)
    assert result.exit_code == 1
    assert result.stdout == ''
    assert result.stderr == ('missing_about: ann_x\n'
                             'Refused: the edit adds 1 failure. Nothing was written.\n')


def test_an_edit_that_cannot_be_made_exits_with_2(tree):
    result = _run(tree, 'link', 'ann_none', 'r_is_about', 'con_concept')
    assert result.exit_code == 2
    assert result.stderr == 'No item has the id ann_none.\n'


def test_batch_makes_items_that_need_each_other_together(tree):
    stdin  = ('- new:   con_x\n'
              '  field: {title: X, brief: X., description: X., term_preferred: x}\n'
              '- new:   ann_x\n'
              '  field: {title: X, brief: X.}\n'
              '  link:  [[r_is_about, con_x]]\n'
              '- set:   [con_x, note, A note.]\n')
    result = _run(tree, 'batch', '-', stdin = stdin)
    assert result.exit_code == 0
    assert result.stdout == ('Wrote _data/register/reg_concept.yaml\n'
                             'Wrote _data/annotation/ann_x.yaml\n')


def test_format_names_the_files_it_would_change_and_then_changes_them(tree):
    path = tree / '_data/register/reg_concern.yaml'
    path.write_text(path.read_text().replace('title:                  Concern register',
                                             'title: Concern register'))
    result = _run(tree, 'format', '--check')
    assert result.exit_code == 1
    assert result.stdout == 'Would change _data/register/reg_concern.yaml\n'
    result = _run(tree, 'format')
    assert result.exit_code == 0
    assert result.stdout == 'Changed _data/register/reg_concern.yaml\n'
    assert _run(tree, 'format', '--check').stdout == ''
