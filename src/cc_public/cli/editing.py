"""
---

id_self:                pym_cc_public.cli.editing
guid_self:              pym_e25b436077ee4217a567d4e052acb03b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Editing commands
brief:                  |
                        The commands that edit the data items in the
                        tree.
description:            |
                        This module holds the new, link, set, batch
                        and format commands. Each makes its edit,
                        checks the tree with the edit in place, and
                        writes it only if it adds no failure. With
                        --dry-run, each prints the edit as a diff and
                        writes nothing.
usage:                  |
                        cctool new ID [--field NAME VALUE]... [--link
                        RELATION TARGET]...

                        cctool link SOURCE RELATION TARGET

                        cctool set ID NAME VALUE

                        cctool batch FILE

                        cctool format [--check]
relation:               []

...
"""


import difflib
import pathlib
import sys

import click
import ruamel.yaml

import cc_public.cli.group
import cc_public.edit.edit
import cc_public.edit.layout
import cc_public.graph.extract


# -----------------------------------------------------------------------------
def _option(function):
    """
    Add the options that every editing command shares to function.

    """

    list_option = [
        click.option('--root',
                     default = '.',
                     type    = click.Path(exists    = True,
                                          file_okay = False,
                                          path_type = pathlib.Path),
                     help    = 'The tree to edit. Defaults to the working directory.'),
        click.option('--dry-run', 'is_dry_run',
                     is_flag = True,
                     help    = 'Print the edit as a diff, and write nothing.')]

    for option in reversed(list_option):
        function = option(function)

    return function


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('id_self', metavar = 'ID')
@click.option('--field',
              'list_field',
              nargs    = 2,
              multiple = True,
              metavar  = 'NAME VALUE',
              help     = 'A field of the new item. Repeat for each field. A NAME given '
                         'more than once makes a list.')
@click.option('--link',
              'list_link',
              nargs    = 2,
              multiple = True,
              metavar  = 'RELATION TARGET',
              help     = 'An edge from the new item. Repeat for each edge.')
@_option
def new(id_self, list_field, list_link, root, is_dry_run):
    """
    Make a new item with the id ID.

    The type is the one whose prefix ID has. An item of a type held in
    a register is added at the end of its table; any other gets a file
    of its own under _data. The guid is made for it, and a standalone
    item takes its rights from the item of the project.

    """

    map_field = {}
    for (key, value) in list_field:
        map_field.setdefault(key, []).append(value)

    _run(root, is_dry_run, [{'new':   id_self,
                             'field': {key: list_value if len(list_value) > 1 else list_value[0]
                                       for (key, list_value) in map_field.items()},
                             'link':  [list(pair) for pair in list_link]}])


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('id_source', metavar = 'SOURCE')
@click.argument('id_relation', metavar = 'RELATION')
@click.argument('id_target', metavar = 'TARGET')
@_option
def link(id_source, id_relation, id_target, root, is_dry_run):
    """
    Add an edge of RELATION from SOURCE to TARGET.

    """

    _run(root, is_dry_run, [{'link': [id_source, id_relation, id_target]}])


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command('set')
@click.argument('id_self', metavar = 'ID')
@click.argument('key', metavar = 'NAME')
@click.argument('value', metavar = 'VALUE')
@_option
def set_field(id_self, key, value, root, is_dry_run):
    """
    Set the text field NAME of the item ID to VALUE.

    A prose field is wrapped to the width of prose, and a blank line in
    VALUE starts a new paragraph. Pass - as VALUE to read it from stdin.

    """

    if value == '-':
        value = sys.stdin.read()

    _run(root, is_dry_run, [{'set': [id_self, key, value]}])


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('path_file', metavar = 'FILE', type = click.File(encoding = 'utf-8'))
@_option
def batch(path_file, root, is_dry_run):
    """
    Make the operations listed in the YAML file FILE, or - for stdin,
    as one edit. Items that need each other, such as a concept and the
    item that names it, are made this way. For example:

    \b
    - new:   con_x
      field: {title: X, brief: ..., description: ..., term_preferred: x}
    - new:   ann_x
      field: {title: ..., brief: ...}
      link:  [[r_is_about, con_x]]
    - link:  [con_x, r_is_about, con_concept]
    - set:   [con_x, usage, ...]

    """

    try:
        list_operation = cc_public.edit.edit.YAML.load(path_file.read())
    except ruamel.yaml.YAMLError as error:
        click.echo('FILE is not YAML: {error}'.format(error = error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    _run(root, is_dry_run, list_operation)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command('format')
@click.option('--root',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to lay out. Defaults to the working directory.')
@click.option('--check', 'is_check',
              is_flag = True,
              help    = 'Name the files that would change, and write nothing. The exit '
                        'status is 1 when any would.')
def format_(root, is_check):
    """
    Lay out every document in the tree under --root, or the working
    directory: the YAML files under _data, the module docstrings of
    python modules, and the comment headers of other files.

    """

    root         = root.resolve()
    map_document = cc_public.graph.extract.documents(root)
    list_changed = []

    for (relative, (document, _)) in sorted(map_document.items()):
        if document is None:
            continue
        path = root / relative
        text = path.read_text(encoding = 'utf-8')
        try:
            laid_out = cc_public.edit.layout.format_file(text, pathlib.Path(relative))
        except cc_public.edit.layout.Unsupported as error:
            click.echo('{file}: {error}'.format(file = relative, error = error), err = True)
            continue
        if laid_out != text:
            list_changed.append(relative)
            if not is_check:
                path.write_text(laid_out, encoding = 'utf-8')

    for relative in list_changed:
        click.echo('{verb} {file}'.format(verb = 'Would change' if is_check else 'Changed',
                                          file = relative))

    sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY if (is_check and list_changed)
             else cc_public.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
def _run(root, is_dry_run, list_operation):
    """
    Make the operations of list_operation over the tree under root as
    one edit, check it, and write it, or print it with --dry-run. Exit
    with 1 if it adds a failure, and with 2 if it cannot be made.

    """

    try:
        tree  = cc_public.edit.edit.Tree(root.resolve())
        cc_public.edit.edit.batch(tree, list_operation)
        added = cc_public.edit.edit.apply(tree, is_written = not is_dry_run)
    except cc_public.edit.edit.ErrorEdit as error:
        click.echo(str(error), err = True)
        sys.exit(cc_public.cli.group.EXIT_ERROR)

    if is_dry_run:
        for (relative, text) in tree.edit.items():
            path = tree.root / relative
            old  = path.read_text(encoding = 'utf-8') if path.exists() else ''
            click.echo(''.join(difflib.unified_diff(old.splitlines(True),
                                                    text.splitlines(True),
                                                    'a/' + relative,
                                                    'b/' + relative)),
                       nl = False)

    if added:
        for (name, list_row) in added.items():
            for row in list_row:
                click.echo('{name}: {row}'.format(name = name, row = '  '.join(row)), err = True)
        count = sum(len(list_row) for list_row in added.values())
        click.echo('Refused: the edit adds {count} {noun}. Nothing was written.'.format(
                       count = count,
                       noun  = 'failure' if count == 1 else 'failures'),
                   err = True)
        sys.exit(cc_public.cli.group.EXIT_NONCONFORMITY)

    if not is_dry_run:
        for relative in tree.edit:
            click.echo('Wrote {file}'.format(file = relative))
