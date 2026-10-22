"""
---

id_self:                pym_cc_public.cli._test.test_messaging
guid_self:              pym_c2f4503cc3cb4ec49d6247f82e64632c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Message command tests
brief:                  |
                        Tests of the message commands, as the command
                        line presents them.
description:            |
                        Each test runs a message command, and checks
                        what it prints, what it leaves in the message
                        and its exit status.
edge:                   []

...
"""


import click.testing

import cc_public.cli.command


# -----------------------------------------------------------------------------
def _run(*list_arg):
    """
    Return the result of cctool message with list_arg.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main, ['message', *list_arg])


def test_draft_of_a_missing_file_is_an_error(tmp_path):
    result = _run('draft', str(tmp_path / 'missing'), '--root', str(tmp_path))
    assert result.exit_code == 2
    assert 'does not exist' in result.stderr


def test_draft_of_a_message_that_is_not_utf_8_is_reported_and_left(tmp_path):
    path = tmp_path / 'MERGE_MSG'
    path.write_bytes(b'Merge \xff\n')
    result = _run('draft', str(path), '--root', str(tmp_path))
    assert result.exit_code == 0
    assert result.stderr.startswith('No draft:')
    assert path.read_bytes() == b'Merge \xff\n'
