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
                        items, in SQL, in a logic program, in SPARQL,
                        in jq or by text.
description:            |
                        This module holds the query group and its
                        commands: sql, logic, sparql, jq, text, which
                        finds items by the words of their prose, and
                        predicates, which lists the predicates SQL and
                        logic programs see. Output is tab separated
                        text with a header row, or JSON with --json,
                        and is cut at --limit rows, with a note on
                        stderr of how many were left out. A jq query
                        prints one result to a line.
edge:                   []

...
"""


import json
import pathlib
import sqlite3
import sys
import textwrap

import click

import cc_public.cli.group
import cc_public.graph.logic
import cc_public.graph.extract
import cc_public.graph.item
import cc_public.graph.jq
import cc_public.graph.sparql
import cc_public.graph.sql
import cc_public.graph.text


LIMIT_DEFAULT     = 100
DELIM_FIELD       = '\t'
WIDTH_TEXT        = 70
INDENT_TEXT       = '      '

HINT              = 'Run cctool query predicates to list the predicates and their columns.'
HINT_JQ           = 'Run cctool query jq --help to see the shape of its input.'
HINT_SPARQL       = 'Run cctool query sparql --help to see how the graph is named.'
HINT_TEXT         = 'Run cctool query text --help to see how a query is read.'

EXAMPLE_SQL       = ('cctool query sql "SELECT type, count(*) AS n '
                     'FROM has_type GROUP BY type"')
EXAMPLE_LOGIC     = ("cctool query logic '#show out/1. "
                     "out(Id) :- has_type(Id, \"type_concern\").'")
EXAMPLE_SPARQL    = ("cctool query sparql 'SELECT ?id ?title WHERE "
                     "{ ?id a cc:type_concern ; f:title ?title }'")
EXAMPLE_TEXT      = 'cctool query text --decision "status field on an option"'
EXAMPLE_JQ        = ("cctool query jq '.[] | select(.file | startswith(\"_data/decision/\")) "
                     "| .document.id_self'")

MAP_HINT          = {EXAMPLE_JQ:     HINT_JQ,
                     EXAMPLE_SPARQL: HINT_SPARQL,
                     EXAMPLE_TEXT:   HINT_TEXT}


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.group()
def query():
    """
    Query the graph of data items, in SQL, in a logic program, in SPARQL or in
    jq, or find items by the words of their prose.

    SQL and logic programs see the same predicates: the base predicates
    extracted from the tree, and the predicates derived from them.
    Run cctool query predicates to list them. SPARQL sees the items as
    RDF triples: their types, fields and primary edges. jq sees the
    YAML documents themselves, as they are written.

    """


# -----------------------------------------------------------------------------
def _option(function):
    """
    Add the options that every query command shares to function.

    """

    list_option = [
        click.argument('text', metavar = 'QUERY', required = False),
        click.option('--file', '-f', 'path_file',
                     metavar = 'FILEPATH',
                     type    = click.Path(exists    = True,
                                          dir_okay  = False,
                                          path_type = pathlib.Path),
                     help    = 'Read the query from this file instead of QUERY.'),
        click.option('--root',
                     metavar = 'DIRPATH',
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

    Each predicate is a SQLite table. A line is an integer, and every
    other value is text. The prose of each item is in item_text(id,
    field, text), an FTS5 table that MATCH searches; cctool query text
    does that for you. Give the query as QUERY, as - to read it from
    stdin, or with --file.

    \b
    Examples:
      cctool query sql "SELECT * FROM item WHERE id LIKE 'opt_%'"
      cctool query sql "SELECT type, count(*) AS n FROM has_type GROUP BY type"
      cctool query sql "SELECT source FROM primary_edge WHERE relation = 'relation_is_about'"

    """

    text         = _read(text, path_file, EXAMPLE_SQL)
    map_document = cc_public.graph.extract.documents(root.resolve())
    facts        = cc_public.graph.extract.facts_of(map_document)

    try:
        (tuple_column, list_row) = cc_public.graph.sql.query(
                                       facts, text, cc_public.graph.text.rows(map_document))
    except (sqlite3.Error, cc_public.graph.logic.ErrorLogic) as error:
        _fail('SQL error: {error}'.format(error = error), EXAMPLE_SQL)

    if is_json:
        click.echo(json.dumps(_result(tuple_column, list_row, limit)))
    else:
        _print(tuple_column, list_row, limit)


# -----------------------------------------------------------------------------
@query.command()
@_option
@click.option('--text', 'text_search',
              metavar = 'WORDS',
              help    = 'Add text_hit(id, field, rank) for each item whose prose matches WORDS.')
@click.option('--exact', 'is_exact',
              is_flag = True,
              help    = 'Match --text on its own words, not the terms of the concepts it names.')
def logic(text, path_file, root, limit, is_json, text_search, is_exact):
    """
    Evaluate logic program rules over the graph, with clingo.

    The rules are clingo rules. They are added to a program that
    already holds every predicate, so they may use any of them. Each
    predicate the rules name in a #show directive is printed. Its
    columns are named by a comment such as "% decl out(id: symbol)",
    or left unnamed. Variables begin with a capital letter, and a value
    in quotes is a string. Give the rules as QUERY, as - to read them
    from stdin, or with --file.

    With --text, the rules may also use text_hit(id, field, rank): one
    row for each item whose prose matches WORDS, as cctool query text
    reads them, with the field it matches best in and its rank, from 1
    for the best.

    \b
    Examples:
      cctool query logic '#show out/1.
        out(Id) :- has_type(Id, "type_concern").'
      cctool query logic --file query.lp
      cctool query logic --text "status field" '#show out/2.
        out(Id, Decision) :- text_hit(Id, _, Rank), Rank <= 10, decision_of(Id, Decision).'

    """

    text = _read(text, path_file, EXAMPLE_LOGIC)

    if not cc_public.graph.logic.output(text):
        _fail('The rules name no predicate in a #show directive, so there is '
              'nothing to print.', EXAMPLE_LOGIC)

    map_document = cc_public.graph.extract.documents(root.resolve())
    facts        = cc_public.graph.extract.facts_of(map_document)

    if text_search is not None:
        list_term = _widened(text_search, map_document, is_exact)
        try:
            facts = facts | {'text_hit': cc_public.graph.text.hits(map_document, text_search,
                                                                   list_term = list_term)}
        except cc_public.graph.text.ErrorText as error:
            _fail(str(error), EXAMPLE_LOGIC)

    try:
        rows = cc_public.graph.logic.run(facts, text, cc_public.graph.text.MAP_COLUMN_HIT)
    except cc_public.graph.logic.ErrorLogic as error:
        _fail('Logic program error: {error}'.format(error = error), EXAMPLE_LOGIC)

    map_declared = cc_public.graph.logic.declared(text)
    map_column   = {name: tuple(column for (column, _) in tuple_column)
                    for (name, tuple_column) in map_declared.items()}
    rows         = {name: _typed(list_row, map_declared.get(name, ()))
                    for (name, list_row) in rows.items()}

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
    Evaluate one jq filter over the YAML documents of the tree.

    The input is one array, with an object for each file that holds a
    document: {"file": ..., "line": ..., "document": ...}, where line
    is the line of the file the document starts on, and document is
    the document as it is written, nested. Each result is printed on a
    line: a string as it is, and any other value as compact JSON. Give
    the filter as QUERY, as - to read it from stdin, or with --file.

    \b
    Examples:
      cctool query jq 'length'
      cctool query jq '.[] | select(.file | startswith("_data/decision/"))
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
@_option
def sparql(text, path_file, root, limit, is_json):
    """
    Evaluate one SPARQL query over the graph, with Oxigraph.

    Each item is the node cc:ID, such as cc:ann_x. Its type is its
    rdf:type, such as cc:type_annotation, and each primary edge is a
    triple of its relation, such as cc:relation_is_about; an inverse relation
    may be used too. Its fields are f:NAME: f:guid, f:file, f:line and
    f:holder, every field of text, number or truth, such as f:title,
    and every item it names in an id_NAME field, as f:NAME. The
    prefixes cc, f, rdf, rdfs and xsd are declared. An item is printed
    by its id. Give the query as QUERY, as - to read it from stdin, or
    with --file.

    \b
    Examples:
      cctool query sparql 'SELECT ?id ?title WHERE { ?id a cc:type_concern ; f:title ?title }'
      cctool query sparql 'SELECT ?ann WHERE { ?ann cc:relation_is_about cc:dec_licence }'
      cctool query sparql 'SELECT ?item WHERE { ?item f:holder+ cc:reg_relation }'
      cctool query sparql 'ASK { cc:opt_apache_2_0 a cc:type_option }'

    """

    text         = _read(text, path_file, EXAMPLE_SPARQL)
    map_document = cc_public.graph.extract.documents(root.resolve())
    facts        = cc_public.graph.extract.facts_of(map_document)
    map_item     = cc_public.graph.item.items(map_document, facts)

    try:
        result = cc_public.graph.sparql.query(map_item, facts, text)
    except cc_public.graph.sparql.ErrorSparql as error:
        _fail('SPARQL error: {error}'.format(error = error), EXAMPLE_SPARQL, HINT_SPARQL)

    if isinstance(result, bool):
        click.echo(json.dumps({'boolean': result}) if is_json else str(result).lower())
        return

    (tuple_column, list_row) = result

    if is_json:
        click.echo(json.dumps(_result(tuple_column, list_row, limit)))
    else:
        _print(tuple_column, list_row, limit)


# -----------------------------------------------------------------------------
@query.command()
def predicates():
    """
    List the predicates that an SQL or logic program query may use, with
    their columns.

    """

    click.echo('Base predicates, extracted from the tree:\n')

    for (name, (tuple_column, meaning)) in cc_public.graph.extract.PREDICATE.items():
        click.echo('  {name}({column})'.format(name = name, column = ', '.join(tuple_column)))
        click.echo(textwrap.fill(meaning,
                                 width             = WIDTH_TEXT,
                                 initial_indent    = INDENT_TEXT,
                                 subsequent_indent = INDENT_TEXT))

    click.echo('\nDerived predicates, as defined in cc_public/graph/derive.lp:\n')
    click.echo(cc_public.graph.logic.PATH_DERIVE.read_text(encoding = 'utf-8'))
    click.echo('A column is a symbol, or text in SQL, unless it is marked :number,')
    click.echo('an integer in SQL. In SQL each predicate is a table.\n')
    click.echo('Examples:')
    click.echo('  ' + EXAMPLE_SQL)
    click.echo('  ' + EXAMPLE_LOGIC)
    click.echo('\nA SPARQL query sees the items as triples, and a jq query the YAML documents,')
    click.echo('not these predicates. See cctool query sparql --help and cctool query jq --help.')


# -----------------------------------------------------------------------------
@query.command()
@_option
@click.option('--match', 'is_match',
              is_flag = True,
              help    = 'Read QUERY as an FTS5 match expression, such as "status NEAR field".')
@click.option('--decision', 'is_decision',
              is_flag = True,
              help    = 'Print one row for each decision, ranked by its best match.')
@click.option('--exact', 'is_exact',
              is_flag = True,
              help    = 'Match the words of QUERY, not the terms of the concepts it names.')
def text(text, path_file, root, limit, is_json, is_match, is_decision, is_exact):
    """
    Find the items whose prose matches the words of QUERY, best first.

    Each word is searched for in the title, brief, description and
    other prose of every item, stemmed, and an item that matches more
    of the words, or rarer ones, ranks higher (BM25). Each hit names
    the decision it belongs to, the ruling that settles that decision
    and the options it upholds, the standing of an option (upheld,
    rejected or open), and the concerns an annotation speaks for. With
    --decision, each row is a decision, so that a hit on any part of a
    deliberation leads to how it was settled. Give the query as QUERY, as
    - to read it from stdin, or with --file.

    A query that names a concept by one of its terms, preferred or
    admitted, also matches the other terms of that concept, such as
    "regentry" for "register entry". The terms added are printed to
    stderr. --exact turns this off, and so does --match.

    \b
    Examples:
      cctool query text "status field on an option"
      cctool query text --decision "checks engine"
      cctool query text --match '"commit" NEAR "title"'

    """

    text         = _read(text, path_file, EXAMPLE_TEXT)
    map_document = cc_public.graph.extract.documents(root.resolve())
    facts        = cc_public.graph.extract.facts_of(map_document)
    list_term    = _widened(text, map_document, is_match or is_exact)

    try:
        (tuple_column, list_row) = cc_public.graph.text.search(facts, map_document, text,
                                                               is_match    = is_match,
                                                               is_decision = is_decision,
                                                               list_term   = list_term)
    except (cc_public.graph.text.ErrorText, cc_public.graph.logic.ErrorLogic) as error:
        _fail(str(error), EXAMPLE_TEXT, HINT_TEXT)

    if is_json:
        click.echo(json.dumps(_result(tuple_column, list_row, limit)))
    else:
        _print(tuple_column, list_row, limit)


# -----------------------------------------------------------------------------
def _widened(text, map_document, is_exact):
    """
    Return the terms that widen the plain query text, unless is_exact,
    and say on stderr which they are.

    """

    if is_exact:
        return []

    list_added = cc_public.graph.text.widen(text, cc_public.graph.text.terms(map_document))

    if list_added:
        list_text = ['"{term}" ({concept})'.format(term = term, concept = concept)
                     for (concept, term) in list_added]
        click.echo('Also matching: {terms}'.format(terms = ', '.join(list_text)), err = True)

    return [term for (_, term) in list_added]


# -----------------------------------------------------------------------------
def _typed(list_row, tuple_column):
    """
    Return the rows, with each value of a column declared a number as
    an integer, sorted, so that numbers sort and print as numbers.

    """

    set_index = {index for (index, (_, type_column)) in enumerate(tuple_column)
                 if type_column == cc_public.graph.logic.TYPE_NUMBER}

    return sorted(tuple(int(value) if index in set_index else value
                        for (index, value) in enumerate(row))
                  for row in list_row)


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
                 MAP_HINT.get(example, HINT))


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
