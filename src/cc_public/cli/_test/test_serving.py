"""
---

id_self:                pym_cc_public.cli._test.test_serving
guid_self:              pym_d588d4e9684e45d4892e291f54a306dd
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Serving command tests
brief:                  |
                        Tests of the serve command, as the command
                        line presents it.
description:            |
                        Each test runs serve where it cannot listen,
                        and checks that it says why and exits with the
                        status of an error, with no traceback.
edge:                   []

...
"""


import socket

import click.testing

import cc_public.cli.command


# -----------------------------------------------------------------------------
def _run(*list_arg):
    """
    Return the result of cctool serve with list_arg.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main, ['serve', *list_arg])


def test_a_port_in_use_is_an_error(tmp_path):
    with socket.socket() as taken:
        taken.bind(('127.0.0.1', 0))
        taken.listen()
        port   = taken.getsockname()[1]
        result = _run('--root', str(tmp_path), '--host', '127.0.0.1', '--port', str(port))
    assert result.exit_code == 2
    assert 'Cannot serve at 127.0.0.1:{port}'.format(port = port) in result.stderr
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_a_port_out_of_range_is_an_error(tmp_path):
    result = _run('--root', str(tmp_path), '--port', '99999')
    assert result.exit_code == 2
    assert '0<=x<=65535' in result.stderr
