"""
---

id_self:                pym_cc_public.cli.editing
guid_self:              pym_8a84f2c29d87412f8d1ef923c8abc71f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Editing commands
brief:                  |
                        new, insert, set, unset, link, unlink, rename
                        and accept: every write to the tree.
description:            |
                        Each adapts what was typed into one call on
                        the edit tier and prints the file it touched.
                        new takes fields and edges so that an item
                        need never exist half made; accept is the only
                        path to an accepted requirement.
relation:               []

...
"""


import pathlib
import sys

import click
import ruamel.yaml

import cc_public.check
import cc_public.check.schema
import cc_public.cli.group
import cc_public.cli.report
import cc_public.commit
import cc_public.control
import cc_public.edit.accept
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.rename
import cc_public.edit.tree
import cc_public.eval.case
import cc_public.eval.check
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.evidence
import cc_public.layout
import cc_public.load.git
import cc_public.question
import cc_public.trace
import cc_public.workflow.generate
import cc_public.workflow.graph
import cc_public.workflow.run


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('id_type')
@click.argument('id_self')
@click.option('--out', 'dirpath_out', default = None,
              type = click.Path(path_type = pathlib.Path),
              help = 'Where to write the item. Defaults to where items of '
                     'this type already live.')
@click.option('--set', 'list_set', multiple = True, metavar = 'PATH=VALUE',
              help = 'A field to write once the item exists, VALUE read as '
                     'YAML as set reads it. May be given more than once.')
@click.option('--prose', 'list_prose', multiple = True, metavar = 'PATH=TEXT',
              help = 'A prose field to write, TEXT held as a block scalar. '
                     'May be given more than once.')
@click.option('--link', 'list_link', multiple = True, nargs = 2,
              metavar = 'RELATION TARGET',
              help = 'An edge to add from the new item. May be given more '
                     'than once.')
@cc_public.cli.group.OPTION_ROOT
def new(id_type, id_self, dirpath_out, list_set, list_prose, list_link, list_root):
    """
    Make a data item of ID_TYPE called ID_SELF.

    Its identity is minted and every field its schema requires is
    present and empty, so it fails the checks until written; --set,
    --prose and --link write it in the same command, so that it never
    need exist half made. Rights come from [tool.cctool.new] in
    pyproject.toml.

    """

    try:
        tree     = cc_public.cli.group.tree(list_root)
        filepath = cc_public.edit.new.new(tree, id_type, id_self,
                                          tree.defaults(), dirpath_out)
        for (path, text) in (_split(one) for one in list_set):
            cc_public.edit.field.set_field(tree, id_self, path,
                                           value = ruamel.yaml.YAML(typ = 'safe').load(text))
        for (path, text) in (_split(one) for one in list_prose):
            cc_public.edit.field.set_field(tree, id_self, path,
                                           prose = text.rstrip('\n') + '\n')
        for (id_relation, name_target) in list_link:
            cc_public.edit.link.link(tree, id_self, id_relation, name_target)
    except (cc_public.edit.tree.ErrorItem, KeyError, ValueError) as err:
        cc_public.cli.group.fail(err)

    click.echo(str(filepath))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'set')
@click.argument('name')
@click.argument('path')
@click.argument('value', required = False)
@click.option('--prose', 'is_prose', is_flag = True,
              help = 'Read the value from standard input and store it as '
                     'prose, a block scalar the printer fills.')
@cc_public.cli.group.OPTION_ROOT
def set_(name, path, value, is_prose, list_root):
    """
    Set PATH within the item called NAME to VALUE.

    NAME is a readable id or a guid, of a top level or an embedded item.
    VALUE is read as YAML, so 3 is a number and [] is a list; quote a
    string that would otherwise read as something else.

    """

    if is_prose == (value is not None):
        cc_public.cli.group.fail('Give VALUE, or --prose with the text on standard input.')

    try:
        item = cc_public.edit.field.set_field(
                    cc_public.cli.group.tree(list_root), name, path,
                    value = (ruamel.yaml.YAML(typ = 'safe').load(value)
                             if value is not None else None),
                    prose = sys.stdin.read() if is_prose else None)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        cc_public.cli.group.fail(err)

    click.echo('{file}  {item}.{path}'.format(file = item.filepath,
                                              item = item.id_self,
                                              path = path))


# -----------------------------------------------------------------------------
def _split(assignment):
    """
    Return (path, value) from PATH=VALUE, or raise where there is no =.

    """

    if '=' not in assignment:
        raise ValueError('{one} is not PATH=VALUE.'.format(one = assignment))

    return tuple(assignment.split('=', 1))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name_source')
@click.argument('id_relation')
@click.argument('name_target')
@cc_public.cli.group.OPTION_ROOT
def unlink(name_source, id_relation, name_target, list_root):
    """
    Remove the edge from NAME_SOURCE labelled ID_RELATION to NAME_TARGET.

    The edge is found by its relation and the target's guid, so a
    stale readable id on it does not hide it. An edge that is not
    there is reported.

    """

    try:
        (source, target) = cc_public.edit.link.unlink(cc_public.cli.group.tree(list_root),
                                                      name_source,
                                                      id_relation, name_target)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    click.echo('{src} no longer {rel} {dst}'.format(src = source.id_self,
                                                    rel = id_relation,
                                                    dst = target.id_self))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name_requirement')
@cc_public.cli.group.OPTION_ROOT
def accept(name_requirement, list_root):
    """
    Accept a requirement whose assurance is complete: judged as
    accepted in a closed world, the trace shows no gap and the evidence
    check finds nothing. Refuses otherwise, saying what it lacks.

    The only path to accepted, so that the status never names a
    requirement the checks would refuse.

    """

    try:
        item = cc_public.edit.accept.accept(cc_public.cli.group.tree(list_root), name_requirement)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    click.echo('{req}  accepted'.format(req = item.id_self))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name_source')
@click.argument('id_relation')
@click.argument('name_target')
@cc_public.cli.group.OPTION_ROOT
def link(name_source, id_relation, name_target, list_root):
    """
    Add an edge NAME_SOURCE --ID_RELATION--> NAME_TARGET.

    Both names are readable ids or guids, of top level or embedded
    items. The relation must be in the relation register. The edge is
    appended to the source's relation list, created where absent.

    """

    try:
        (source, target) = cc_public.edit.link.link(
                    cc_public.cli.group.tree(list_root), name_source, id_relation, name_target)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    click.echo('{file}  {src} {rel} {dst}'.format(file = source.filepath,
                                                 src  = source.id_self,
                                                 rel  = id_relation,
                                                 dst  = target.id_self))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('id_type')
@click.argument('name')
@click.option('--into', 'name_container', required = True,
              help = 'The item to put it in, by readable id or guid.')
@click.option('--at', 'path_collection', default = None,
              help = 'The collection within that item, as a dot path. '
                     'Defaults to table where the item is a register.')
@click.option('--id', 'id_self', default = None,
              help = 'The readable id to give it, where the derived one '
                     'is not wanted.')
@cc_public.cli.group.OPTION_ROOT
def insert(id_type, name, name_container, path_collection, id_self, list_root):
    """
    Put a new item of ID_TYPE called NAME into a collection of another.

    Its shape comes from the container's schema, every required field
    empty. In a register the key is the id; elsewhere NAME is the key
    and the id is qualified by the container. A list is appended to.

    """

    try:
        (key, made) = cc_public.edit.insert.insert(
                        cc_public.cli.group.tree(list_root), id_type, name, name_container,
                        path_collection, id_self)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        cc_public.cli.group.fail(err)

    click.echo('{container}.{key}  {made}'.format(container = name_container,
                                                  key       = key,
                                                  made      = made or ''))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name')
@click.argument('path')
@cc_public.cli.group.OPTION_ROOT
def unset(name, path, list_root):
    """
    Remove PATH from the item called NAME.

    """

    try:
        item = cc_public.edit.field.unset_field(cc_public.cli.group.tree(list_root), name, path)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        cc_public.cli.group.fail(err)

    click.echo('{file}  {item}.{path} removed'.format(file = item.filepath,
                                                     item = item.id_self,
                                                     path = path))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name')
@click.argument('id_new')
@cc_public.cli.group.OPTION_ROOT
def rename(name, id_new, list_root):
    """
    Rename the item called NAME to ID_NEW.

    The guid stays. The readable id changes where it is declared, in
    the file name, in every embedded item it qualifies, and in every
    reference. Prose mentioning the old id is listed and left alone.

    """

    try:
        report = cc_public.edit.rename.rename(cc_public.cli.group.tree(list_root), name, id_new)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    for (old, new) in report.map_rename.items():
        click.echo('{old}  ->  {new}'.format(old = old, new = new))
    for filepath in report.list_filepath:
        click.echo(str(filepath))
    for (filepath, path) in report.list_mention:
        click.echo('mention  {file}  {path}'.format(file = filepath, path = path))
