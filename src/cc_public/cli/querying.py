"""
---

id_self:                pym_cc_public.cli.querying
guid_self:              pym_35b0b721622849b6bea11026ab8fb086
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Querying commands
brief:                  |
                        The commands that query the graph of data
                        items, in SQL, in Datalog or in jq.
description:            |
                        This module holds the query group and its
                        commands: sql, datalog, jq, and schema, which
                        lists the relations SQL and Datalog see.
                        Output is tab separated text with a header
                        row, or JSON with --json, and is cut at
                        --limit rows, with a note on stderr of how
                        many were left out. A jq query prints one
                        result to a line.
relation:               []

...
"""


import json
import pathlib
import sqlite3
import sys
import textwrap

import click

import cc_public.cli.group
import cc_public.graph.datalog
import cc_public.graph.extract
import cc_public.graph.jq
import cc_public.graph.sql


LIMIT_DEFAULT     = 100
DELIM_FIELD       = '\t'
WIDTH_TEXT        = 70
INDENT_TEXT       = '      '

HINT              = 'Run cctool query schema to list the relations and their columns.'
HINT_JQ           = 'Run cctool query jq --help to see the shape of its input.'

EXAMPLE_SQL       = ('cctool query sql "SELECT type, count(*) AS n '
                     'FROM type_of GROUP BY type"')
EXAMPLE_DATALOG   = ("cctool query datalog '#show out/1. "
                     "out(Id) :- type_of(Id, \"t_concern\").'")
EXAMPLE_JQ        = ("cctool query jq '.[] | select(.file | startswith(\"_data/issue/\")) "
                     "| .document.id_self'")


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def query():
    """
    Query the graph of data items, in SQL, in Datalog or in jq.

    SQL and Datalog see the same relations: the base relations
    extracted from the tree, and the relations derived from them.
    Run cctool query schema to list them. jq sees the documents
    themselves, as they are written.

    """


# -----------------------------------------------------------------------------
def _option(function):
    """
    Add the options that every query command shares to function.

    """

    list_option = [
        click.argument('text', metavar = 'QUERY', required = False),
        click.option('--file', '-f', 'path_file',
                     type = click.Path(exists    = True,
                                       dir_okay  = False,
                                       path_type = pathlib.Path),
                     help = 'Read the query from this file instead of QUERY.'),
        click.option('--root',
                     default = '.',
                     type    = click.Path(exists    = True,
                                          file_okay = False,
                                          path_type = pathlib.Path),
                     help    = 'The tree to query. Defaults to the working directory.'),
        click.option('--limit',
                     default = LIMIT_DEFAULT,
                     show_default = True,
                     type    = click.IntRange(min = 0),
                     help    = 'The most rows to print for each result. 0 prints all.'),
        click.option('--json', 'is_json',
                     is_flag = True,
                     help    = 'Print JSON: columns, rows and the count of all rows.')]

    for option in reversed(list_option):
        function = option(function)

    return function


# -----------------------------------------------------------------------------
@query.command()
@_option
def sql(text, path_file, root, limit, is_json):
    """
    Evaluate one SQL query over the graph.

    Each relation is a SQLite table. A line is an integer, and every
    other value is text. Give the query as QUERY, as - to read it from
    stdin, or with --file.

    \b
    Examples:
      cctool query sql "SELECT * FROM item WHERE id LIKE 'dec_%'"
      cctool query sql "SELECT type, count(*) AS n FROM type_of GROUP BY type"
      cctool query sql "SELECT source FROM primary_edge WHERE relation = 'r_is_about'"

    """

    text  = _read(text, path_file, EXAMPLE_SQL)
    facts = cc_public.graph.extract.extract(root.resolve())

    try:
        (tuple_column, list_row) = cc_public.graph.sql.query(facts, text)
    except (sqlite3.Error, cc_public.graph.datalog.ErrorDatalog) as error:
        _fail('SQL error: {error}'.format(error = error), EXAMPLE_SQL)

    if is_json:
        click.echo(json.dumps(_result(tuple_column, list_row, limit)))
    else:
        _print(tuple_column, list_row, limit)


# -----------------------------------------------------------------------------
@query.command()
@_option
def datalog(text, path_file, root, limit, is_json):
    """
    Evaluate Datalog rules over the graph, with clingo.

    The rules are clingo rules. They are added to a program that
    already holds every relation, so they may use any of them. Each
    relation the rules name in a #show directive is printed. Its
    columns are named by a comment such as "% decl out(id: symbol)",
    or left unnamed. Variables begin with a capital letter, and a value
    in quotes is a string. Give the rules as QUERY, as - to read them
    from stdin, or with --file.

    \b
    Examples:
      cctool query datalog '#show out/1.
        out(Id) :- type_of(Id, "t_concern").'
      cctool query datalog --file query.lp

    """

    text = _read(text, path_file, EXAMPLE_DATALOG)

    if not cc_public.graph.datalog.output(text):
        _fail('The rules name no relation in a #show directive, so there is '
              'nothing to print.', EXAMPLE_DATALOG)

    facts = cc_public.graph.extract.extract(root.resolve())

    try:
        rows = cc_public.graph.datalog.run(facts, text)
    except cc_public.graph.datalog.ErrorDatalog as error:
        _fail('Datalog error: {error}'.format(error = error), EXAMPLE_DATALOG)

    map_column = {name: tuple(column for (column, _) in tuple_column)
                  for (name, tuple_column) in cc_public.graph.datalog.declared(text).items()}

    if is_json:
        click.echo(json.dumps({name: _result(map_column.get(name, ()), list_row, limit)
                               for (name, list_row) in rows.items()}))
        return

    for (index, (name, list_row)) in enumerate(rows.items()):
        if index:
            click.echo()
        click.echo('# {name}'.format(name = name))
        _print(map_column.get(name, ()), list_row, limit)


# -----------------------------------------------------------------------------
@query.command()
@_option
def jq(text, path_file, root, limit, is_json):
    """
    Evaluate one jq filter over the documents of the tree.

    The input is one array, with an object for each file that holds a
    document: {"file": ..., "line": ..., "document": ...}, where line
    is the line of the file the document starts on, and document is
    the document as it is written, nested. Each result is printed on a
    line: a string as it is, and any other value as compact JSON. Give
    the filter as QUERY, as - to read it from stdin, or with --file.

    \b
    Examples:
      cctool query jq 'length'
      cctool query jq '.[] | select(.file | startswith("_data/issue/"))
        | .document.id_self'
      cctool query jq '[.[].document | objects | .title // empty]'

    """

    text         = _read(text, path_file, EXAMPLE_JQ)
    map_document = cc_public.graph.extract.documents(root.resolve())

    try:
        list_result = cc_public.graph.jq.query(map_document, text)
    except cc_public.graph.jq.ErrorJq as error:
        _fail(str(error), EXAMPLE_JQ, HINT_JQ)

    if is_json:
        click.echo(json.dumps({'results': _cut(list_result, limit),
                               'count':   len(list_result)}))
        return

    for result in _cut(list_result, limit):
        click.echo(result if isinstance(result, str) else json.dumps(result))


# -----------------------------------------------------------------------------
@query.command()
def schema():
    """
    List the relations that an SQL or Datalog query may use, with
    their columns.

    """

    click.echo('Base relations, extracted from the tree:\n')

    for (name, (tuple_column, meaning)) in cc_public.graph.extract.RELATION.items():
        click.echo('  {name}({column})'.format(name = name, column = ', '.join(tuple_column)))
        click.echo(textwrap.fill(meaning,
                                 width             = WIDTH_TEXT,
                                 initial_indent    = INDENT_TEXT,
                                 subsequent_indent = INDENT_TEXT))

    click.echo('\nDerived relations, as defined in cc_public/graph/derive.lp:\n')
    click.echo(cc_public.graph.datalog.PATH_DERIVE.read_text(encoding = 'utf-8'))
    click.echo('A column is a symbol, or text in SQL, unless it is marked :number,')
    click.echo('an integer in SQL. In SQL each relation is a table.\n')
    click.echo('Examples:')
    click.echo('  ' + EXAMPLE_SQL)
    click.echo('  ' + EXAMPLE_DATALOG)
    click.echo('\nA jq query sees the documents, not these relations. See cctool query jq --help.')


# -----------------------------------------------------------------------------
def _read(text, path_file, example):
    """
    Return the query: from path_file, from stdin if text is -, or text.

    """

    if path_file is not None:
        return path_file.read_text(encoding = 'utf-8')
    if text == '-':
        return sys.stdin.read()
    if text:
        return text

    return _fail('No query given. Give it as QUERY, as - for stdin, or with --file.',
                 example,
                 HINT_JQ if example == EXAMPLE_JQ else HINT)


# -----------------------------------------------------------------------------
def _fail(message, example, hint = HINT):
    """
    Print message, an example and hint to stderr, and exit with the
    status of an error.

    """

    click.echo(message, err = True)
    click.echo('For example: {example}'.format(example = example), err = True)
    click.echo(hint, err = True)
    sys.exit(cc_public.cli.group.EXIT_ERROR)


# -----------------------------------------------------------------------------
def _cut(list_row, limit):
    """
    Return the rows to print, and note on stderr how many are left out.

    """

    if limit and len(list_row) > limit:
        click.echo('{count} of {total} rows shown. Pass --limit 0 to show all.'.format(
                      count = limit,
                      total = len(list_row)),
                   err = True)
        return list_row[:limit]

    return list_row


# -----------------------------------------------------------------------------
def _result(tuple_column, list_row, limit):
    """
    Return the result as a JSON-ready dict.

    """

    return {'columns': list(tuple_column),
            'rows':    [list(row) for row in _cut(list_row, limit)],
            'count':   len(list_row)}


# -----------------------------------------------------------------------------
def _print(tuple_column, list_row, limit):
    """
    Print the result as tab separated text, with a header row.

    """

    if tuple_column:
        click.echo(DELIM_FIELD.join(tuple_column))

    for row in _cut(list_row, limit):
        click.echo(DELIM_FIELD.join('' if value is None else str(value) for value in row))
