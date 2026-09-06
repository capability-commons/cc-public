"""
---

id_self:                pym_cc_public.cli.committing
guid_self:              pym_5f5dd94acb004e519720507af71b5c25
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Committing commands
brief:                  |
                        commit and log: history written with a record
                        in the message, and read back.
description:            |
                        commit hands its options to the committer,
                        which runs the checks and the linters and
                        refuses on what the refusal policy says; log
                        walks the history and validates each record
                        again.
relation:               []

...
"""


import pathlib

import click

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
@click.argument('title')
@click.option('--brief', 'brief', default = None,
              help = 'One sentence on what the commit is for. Defaults to '
                     'the title.')
@click.option('--description', 'description', default = None,
              help = 'Why, at whatever length it needs.')
@click.option('--checkpoint', 'is_checkpoint', is_flag = True,
              help = 'Commit although the checks fail, and say so in the '
                     'record.')
@click.option('--execution', 'id_execution', default = None,
              help = 'The execution this commit results from, where a '
                     'workflow made it.')
@click.option('--trailer', 'list_trailer', multiple = True,
              help = 'A trailer line appended after the record.')
@click.option('--link', 'list_link', multiple = True, nargs = 2,
              metavar = 'RELATION TARGET',
              help = 'An edge from the record to an item, by any relation '
                     'in the register: what this commit relates to on '
                     'purpose. May be given more than once.')
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path),
              help = 'The repository. Defaults to the working directory.')
@click.option('--path', 'list_path', multiple = True,
              type = click.Path(path_type = pathlib.Path),
              help = 'A further tree the checks read beside the repository: '
                     'the core a consumer segment names. Checked, not '
                     'committed. May be given more than once.')
def commit(title, brief, description, is_checkpoint, id_execution,
           list_trailer, list_link, root, list_path):
    """
    Commit what has changed, with a commit record in the message.

    TITLE is the first line of the message and the record's title. The
    checks run first; a critical finding refuses the commit unless
    --checkpoint is given.

    """

    try:
        (hash, id_self) = cc_public.commit.commit(
                    root, title, brief, description, is_checkpoint,
                    id_execution, list_trailer, list_link, list_path)
    except (cc_public.commit.ErrorCommit, cc_public.edit.tree.ErrorItem) as err:
        cc_public.cli.group.fail(err)

    click.echo('{hash}  {id_self}'.format(hash = hash[:10], id_self = id_self))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('-n', 'count', default = 10, type = click.IntRange(min = 1),
              show_default = True, help = 'How many commits to read.')
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path))
def log(count, root):
    """
    Read the commit records in the history, newest first, and say
    which are valid.

    """

    tree       = cc_public.cli.group.tree([root])
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    for c in cc_public.load.git.iter_commit(root, count):

        if c.document is None:
            click.echo('{hash}  -  {title}'.format(hash = c.hash[:10],
                                                   title = c.title))
            continue

        list_error = cc_public.check.schema.validate(
                        c.document, 'sch_commit', map_schema, registry)
        state = 'ok' if not list_error else 'INVALID'

        if c.document.get('title') != c.title:
            state += ', title differs from first line'

        click.echo('{hash}  {id}  {status}  {crit}c/{adv}a  {state}  {title}'.format(
                        hash   = c.hash[:10],
                        id     = c.document.get('id_self', '?'),
                        status = c.document.get('status', '?'),
                        crit   = (c.document.get('check') or {}).get('critical', '?'),
                        adv    = (c.document.get('check') or {}).get('advisory', '?'),
                        state  = state,
                        title  = c.title))
