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
    result = _run(tree, 'datalog', '% decl o(t: symbol)\n#show o/1. o(T) :- type_of("concern_cost", T).')
    assert result.exit_code == 0
    assert result.stdout == '# o\nt\nt_concern\n'


def test_datalog_gives_a_number_column_as_numbers(tree):
    result = _run(tree, 'datalog', '% decl o(n: number)\n#show o/1. o(9). o(10).', '--json')
    assert json.loads(result.stdout) == {'o': {'columns': ['n'], 'rows': [[9], [10]], 'count': 2}}


def test_datalog_without_an_output_is_refused(tree):
    result = _run(tree, 'datalog', 'o(T) :- type_of(_, T).')
    assert result.exit_code == 2
    assert 'no relation in a #show directive' in result.stderr


def test_jq_prints_each_result_on_a_line(tree):
    result = _run(tree, 'jq', '[.[].document | .. | objects | .id_self? | strings '
                              '| select(startswith("concern_"))] | sort | .[]',
                  '--limit', '2')
    assert result.exit_code == 0
    assert result.stdout == 'concern_compatibility\nconcern_cost\n'
    assert result.stderr == '2 of 16 rows shown. Pass --limit 0 to show all.\n'


def test_jq_sees_the_file_and_line_of_each_document(tree):
    result = _run(tree, 'jq', '.[] | select(.document.id_self? == "lc_tooling") '
                              '| {file, line}', '--json')
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        'results': [{'file': '_data/logical_component/lc_tooling.yaml', 'line': 1}],
        'count':   1}


def test_jq_error_is_refused_with_an_example(tree):
    result = _run(tree, 'jq', '.[] |')
    assert result.exit_code == 2
    assert result.stderr.startswith('jq: error')
    assert 'For example: cctool query jq' in result.stderr
    assert 'cctool query jq --help' in result.stderr


def test_a_missing_query_is_refused_with_an_example(tree):
    result = _run(tree, 'sql')
    assert result.exit_code == 2
    assert 'For example: cctool query sql' in result.stderr


def test_sparql_prints_the_rows_of_a_select(tree):
    result = _run(tree, 'sparql', 'SELECT ?id WHERE { ?id a cc:t_concern } ORDER BY ?id',
                  '--limit', '2')
    assert result.exit_code == 0
    assert result.stdout == 'id\nconcern_compatibility\nconcern_cost\n'
    assert result.stderr == '2 of 16 rows shown. Pass --limit 0 to show all.\n'


def test_sparql_sees_fields_and_edges(tree):
    result = _run(tree, 'sparql', 'SELECT ?title WHERE { cc:iss_tooling_language '
                                  'cc:r_is_about ?lc . ?lc f:title ?title }', '--json')
    assert json.loads(result.stdout) == {'columns': ['title'], 'rows': [['Tooling']], 'count': 1}


def test_sparql_ask_prints_true_or_false(tree):
    result = _run(tree, 'sparql', 'ASK { cc:lc_tooling a cc:t_logical_component }')
    assert result.stdout == 'true\n'


def test_sparql_error_is_refused_with_an_example(tree):
    result = _run(tree, 'sparql', 'SELECT ?x WHERE {')
    assert result.exit_code == 2
    assert result.stderr.startswith('SPARQL error:')
    assert 'For example: cctool query sparql' in result.stderr


def test_text_prints_a_header_and_the_best_hits(tree):
    result = _run(tree, 'text', 'souffle clingo', '--issue', '--limit', '1')
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0] == 'score\tissue\thits\ttitle\tdetermination\tupheld'
    assert result.stdout.splitlines()[1].split('\t')[1] == 'iss_cross_item_checks_engine'


def test_text_says_which_terms_of_a_concept_it_adds(tree):
    result = _run(tree, 'text', 'every regentry')
    assert result.exit_code == 0
    assert 'Also matching: "register entry" (con_register_entry)' in result.stderr
    result = _run(tree, 'text', '--exact', 'every regentry')
    assert 'Also matching' not in result.stderr


def test_datalog_with_text_reads_the_hits_as_facts(tree):
    rules  = '% decl best(id)\n#show best/1.\nbest(Id) :- text_hit(Id, _, 1).'
    result = _run(tree, 'datalog', '--text', 'souffle', rules)
    assert result.exit_code == 0
    assert result.stdout.splitlines()[0:2] == ['# best', 'id']
    assert len(result.stdout.splitlines()) == 3


def test_text_with_no_words_is_refused_with_an_example(tree):
    result = _run(tree, 'text', '?!')
    assert result.exit_code == 2
    assert 'no words to search for' in result.stderr
    assert 'For example: cctool query text' in result.stderr
