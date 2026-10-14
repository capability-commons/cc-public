"""
---

id_self:                pym_cc_public.cli._test.test_querying
guid_self:              pym_4be736c38c224f21a10a4075ec9ebfeb
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Querying command tests
brief:                  |
                        Tests of the query commands, as the command
                        line presents them.
description:            |
                        Each test runs a command over a copy of the
                        repository's data items, and checks its
                        output, its notes on stderr and its exit
                        status.
relation:               []

...
"""


import json

import click.testing

import cc_public.cli.command


SQL_CONCERN = "SELECT id FROM type_of WHERE type = 't_concern' ORDER BY id"


# -----------------------------------------------------------------------------
def _run(tree, *list_arg):
    """
    Return the result of cctool query with list_arg, over tree.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main,
                         ['query', *list_arg, '--root', str(tree)])


def test_sql_prints_a_header_and_the_rows_cut_at_the_limit(tree):
    result = _run(tree, 'sql', SQL_CONCERN, '--limit', '2')
    assert result.exit_code == 0
    assert result.stdout == 'id\nconcern_compatibility\nconcern_cost\n'
    assert result.stderr == '2 of 16 rows shown. Pass --limit 0 to show all.\n'


def test_sql_prints_json_with_the_count_of_all_rows(tree):
    result = _run(tree, 'sql', SQL_CONCERN, '--limit', '1', '--json')
    assert json.loads(result.stdout) == {'columns': ['id'],
                                         'rows':    [['concern_compatibility']],
                                         'count':   16}


def test_datalog_prints_each_output_relation(tree):
    result = _run(tree, 'datalog', '.decl o(t:symbol) .output o o(t) :- type_of("concern_cost", t).')
    assert result.exit_code == 0
    assert result.stdout == '# o\nt\nt_concern\n'


def test_datalog_without_an_output_is_refused(tree):
    result = _run(tree, 'datalog', '.decl o(t:symbol) o(t) :- type_of(_, t).')
    assert result.exit_code == 2
    assert 'no relation in an .output directive' in result.stderr


def test_a_missing_query_is_refused_with_an_example(tree):
    result = _run(tree, 'sql')
    assert result.exit_code == 2
    assert 'For example: cctool query sql' in result.stderr
