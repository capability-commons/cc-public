"""
---

id_self:                pym_cc_public.cli.querying
guid_self:              pym_574c0f5b1b2046529d3a922086e781c2
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Querying commands
brief:                  |
                        walk, path, orphans and query: questions put
                        to the graph of relations.
description:            |
                        Each opens the tree, loads its facts into the
                        query database, and renders what comes back
                        through the report module: a neighbourhood as
                        text, json or a drawing; a shortest path or
                        its absence; the items and relations nothing
                        names; the rows of a named query or of SQL
                        typed at the command line.
relation:               []

...
"""


import json

import click

import cc_public.cli.group
import cc_public.cli.report
import cc_public.query


FORMAT_ALL = ('text', 'json', 'dot', 'mermaid')


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name')
@click.option('--depth', 'depth', default = 1, type = click.IntRange(min = 1),
              show_default = True, help = 'How many edges out to walk.')
@click.option('--relation', 'list_relation', multiple = True,
              help = 'Follow only edges of this relation. May be given more '
                     'than once. Absent, every relation.')
@click.option('--direction', 'direction', type = click.Choice(['both', 'out', 'in']),
              default = 'both', show_default = True,
              help = 'out follows edges the item holds; in follows edges that '
                     'name it.')
@click.option('--format', 'id_format', type = click.Choice(FORMAT_ALL),
              default = 'text', show_default = True,
              help = 'text or json to read; dot or mermaid to draw.')
@cc_public.cli.group.OPTION_ROOT
def walk(name, depth, list_relation, direction, id_format, list_root):
    """
    Walk the neighbourhood of one item: every item within DEPTH edges,
    in either direction, with the edge that reached it.

    """

    with cc_public.query.Database(
            cc_public.cli.group.tree(list_root).context.map_document) as db:
        step = db.walk(name, depth, list_relation,
                       cc_public.query.DIRECTION_ALL if direction == 'both' else (direction,))

    if step is None:
        cc_public.cli.group.fail('Nothing in this tree is named {name}.'.format(name = name))

    cc_public.cli.report.write_walk(step, id_format)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name_from')
@click.argument('name_to')
@click.option('--format', 'id_format', type = click.Choice(FORMAT_ALL),
              default = 'text', show_default = True)
@cc_public.cli.group.OPTION_ROOT
def path(name_from, name_to, id_format, list_root):
    """
    Show a shortest path of edges from one item to another, in either
    direction, or say that none joins them.

    """

    with cc_public.query.Database(
            cc_public.cli.group.tree(list_root).context.map_document) as db:
        step = db.path(name_from, name_to)

    if step is None:
        cc_public.cli.group.fail('One of {a} and {b} is not in this tree.'.format(
                                    a = name_from, b = name_to))

    if not step:
        click.echo('No path joins {a} and {b}.'.format(a = name_from, b = name_to))
        return

    cc_public.cli.report.write_walk(step, id_format)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--format', 'id_format', type = click.Choice(['text', 'json']),
              default = 'text', show_default = True)
@cc_public.cli.group.OPTION_ROOT
def orphans(id_format, list_root):
    """
    List every item no edge points at and no item holds, and every
    relation no edge uses.

    """

    with cc_public.query.Database(
            cc_public.cli.group.tree(list_root).context.map_document) as db:
        (list_item, list_relation) = db.orphans()

    if id_format == 'json':
        click.echo(json.dumps({'item': list_item, 'relation': list_relation}, indent = 2))
        return

    for one in list_item:
        click.echo('item      {one}'.format(one = one))
    for one in list_relation:
        click.echo('relation  {one}'.format(one = one))
    click.echo('{n} item(s) nothing points at, {m} relation(s) nothing uses.'.format(
                    n = len(list_item), m = len(list_relation)))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name', required = False)
@click.option('--sql', 'sql', default = None,
              help = 'SQL to run over the tables item, edge and containment, '
                     'instead of a named query.')
@click.option('--format', 'id_format', type = click.Choice(['text', 'json']),
              default = 'text', show_default = True)
@cc_public.cli.group.OPTION_ROOT
def query(name, sql, id_format, list_root):
    """
    Run a named query, an item of type t_query, or SQL given here, over
    the facts of the tree, and report the rows.

    """

    if (name is None) == (sql is None):
        cc_public.cli.group.fail('Name one query, or give --sql.')

    map_document = cc_public.cli.group.tree(list_root).context.map_document

    if name is not None:
        sql = cc_public.query.named(map_document, name)
        if sql is None:
            cc_public.cli.group.fail('No query is called {name}.'.format(name = name))

    try:
        with cc_public.query.Database(map_document) as db:
            (names, rows) = db.run(sql)
    except cc_public.query.sqlite3.Error as err:
        cc_public.cli.group.fail('The query did not run: {err}'.format(err = err))

    cc_public.cli.report.write_rows(names, rows, id_format)
