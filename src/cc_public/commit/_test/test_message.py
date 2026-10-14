"""
---

id_self:                pym_cc_public.commit._test.test_message
guid_self:              pym_d3cb204963404131a47f49653dbb3dfe
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit message tests
brief:                  |
                        Tests of composing and checking commit
                        messages.
description:            |
                        Each test composes or edits a message and
                        checks it against sch_commit as the repository
                        holds it.
relation:               []

...
"""


import datetime

import click.testing
import pytest

import cc_public.cli.command
import cc_public.commit.message
from cc_public.conftest import DIR_REPO


NOW   = datetime.datetime(2026, 10, 14, 11, 20, 48, tzinfo = datetime.UTC)
BRIEF = 'Each commit message holds a commit item.'


# -----------------------------------------------------------------------------
def _message(title = 'Add the commit-msg hook', **kwargs):
    """
    Return a composed message with title.

    """

    return cc_public.commit.message.compose(title, BRIEF, now = NOW, **kwargs)


def _found(text):
    """
    Return the ways text fails, as the repository holds sch_commit.

    """

    return cc_public.commit.message.violations(DIR_REPO, text)


def test_a_composed_message_passes_and_its_id_sorts_by_time():
    text = _message()
    assert _found(text) == []
    (subject, item) = cc_public.commit.message.parse(text)
    assert subject == 'Add the commit-msg hook'
    assert item['id_self'].startswith('cmt_20261014112048_')
    assert item['guid_self'][4:10] == item['id_self'][-6:]


@pytest.mark.parametrize('title', [
    'Add the commit type t_commit',
    'Remove status from registers',
    'Reformat every document',
    'Rename t_datalog_module to t_datalog_source_file',
    'Move the checker to cc_public.check',
    'Split r_is_specified_by_schema into two relations',
    'Fold testability into maintainability',
    'Merge branch commit-items into main',
    'Revert "Add the commit type t_commit"',
    'Change cctool batch so that a field keeps its YAML value',
    'Fix the checker so that a malformed subschema is reported',
    'Lock jsonschema at 4.26.0',
])
def test_a_title_from_a_template_passes(title):
    assert _found(_message(title)) == []


@pytest.mark.parametrize('title', [
    'Commit type',
    'Added the commit type',
    'Add the commit type.',
    'Rename the commit type',
    'Change the checker',
    'add the commit type',
    'Merge testability into maintainability',
    "Merge branch 'commit-items'",
    'Revert the commit type',
    'Revert "Add the commit type t_commit',
])
def test_a_title_from_no_template_is_reported(title):
    assert _found(_message(title)) == [
        'The title is not built from a template in sch_commit: ' + title]


def test_a_subject_line_that_is_not_the_title_is_reported():
    text = _message().replace('Add the commit-msg hook\n', 'Add a hook\n', 1)
    assert _found(text) == ['The subject line is not the title of the commit item.']


def test_an_id_that_does_not_end_with_the_guid_is_reported():
    text = _message()
    (_, item) = cc_public.commit.message.parse(text)
    text = text.replace(item['id_self'], item['id_self'][:-6] + 'ffffff')
    assert _found(text) == ['The id does not end with the first 6 hex digits of the guid.']


def test_a_verdict_field_is_reported():
    text = _message().replace('relation:', 'status:                 clean\nrelation:')
    assert _found(text) == [
        "item: Unevaluated properties are not allowed ('status' was unexpected)"]


def test_lines_that_git_treats_as_comments_are_left_out():
    assert _found(_message() + '# Please enter the commit message.\n') == []


def test_a_message_without_an_item_is_reported():
    assert _found('Add the commit-msg hook\n\nSome prose.\n') == [
        'A commit message is a subject line, a blank line, and then the commit item, '
        'opened by ---.']


def test_check_exits_with_1_and_says_why():
    result = click.testing.CliRunner().invoke(
                    cc_public.cli.command.main,
                    ['message', 'check', '-', '--root', str(DIR_REPO)],
                    input = 'Commit-msg hook\n')
    assert result.exit_code == 1
    assert result.stderr.startswith('A commit message is a subject line')
