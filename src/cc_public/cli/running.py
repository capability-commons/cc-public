"""
---

id_self:                pym_cc_public.cli.running
guid_self:              pym_2e94fa6dd42a4d75947f283c4f4a02fa
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Running command
brief:                  |
                        run: one run of a dataflow workflow under a
                        deployment; resume: continue one that waits.
description:            |
                        Builds the generator and the judge the
                        deployment names, hands them to the executor
                        with the bindings given, and renders what each
                        node made, revised, fired and declined, or why
                        the run stopped.
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
@cc_public.cli.group.main.command(name = 'run')
@click.argument('id_workflow')
@click.option('--deployment', 'id_deployment', required = True,
              help = 'The deployment to run under: model, budget, what to '
                     'judge, when to commit.')
@click.option('--bind', 'list_bind', multiple = True, metavar = 'PORT=ITEM',
              help = 'Bind one of the workflow\'s own inputs, node.input.port, '
                     'to an item by readable id. May be given more than once.')
@click.option('--dry-run', 'is_dry', is_flag = True,
              help = 'Show the order and what each node would do. Writes '
                     'nothing and calls no model.')
@click.option('--judge-model', 'id_model_judge', default = None,
              envvar = cc_public.eval.runner.NAME_ENV_MODEL, show_envvar = True,
              help = 'The model that judges what the run produces. Needed '
                     'unless the deployment judges nothing.')
@click.option('--trailer', 'list_trailer', multiple = True,
              help = 'A trailer line for any commit the run makes.')
@click.option('--format', 'id_format', default = 'text',
              type = click.Choice(['text', 'json']), show_default = True)
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path))
def run_(id_workflow, id_deployment, list_bind, is_dry, id_model_judge,
         list_trailer, id_format, root):
    """
    Run a dataflow workflow once under a deployment.

    """

    import json

    map_bind = {}
    for pair in list_bind:
        if '=' not in pair:
            cc_public.cli.group.fail('--bind takes node.input.port=ITEM')
        (k, v) = pair.split('=', 1)
        map_bind[k.strip()] = v.strip()

    tree = cc_public.cli.group.tree([root])

    try:
        dep       = tree.context.map_document[tree.resolve(id_deployment).location]
        generator = (cc_public.workflow.generate.NullGenerator() if is_dry
                     else cc_public.workflow.generate.build(dep.get('model')))
        generator_challenge = (None if is_dry or not dep.get('model_challenge')
                               else cc_public.workflow.generate.build(dep.get('model_challenge')))
        runner    = None
        if not is_dry and dep.get('judge', 'always') != 'never' and id_model_judge:
            runner = cc_public.eval.runner.build(id_model_judge)
        report = cc_public.workflow.run.run(root, id_workflow, id_deployment,
                                            map_bind, generator, runner,
                                            is_dry, list_trailer,
                                            generator_challenge = generator_challenge)
    except (cc_public.workflow.run.Stop, cc_public.workflow.graph.ErrorGraph,
            cc_public.edit.tree.ErrorItem, cc_public.commit.ErrorCommit) as err:
        cc_public.cli.group.fail(err)

    if id_format == 'json':
        click.echo(json.dumps(report, indent = 2, default = str))
    else:
        cc_public.cli.report.write_run(report)

    raise SystemExit(cc_public.cli.group.EXIT_NONCONFORMITY if report['stopped']
                     else cc_public.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'resume')
@click.argument('id_execution')
@click.option('--judge-model', 'id_model_judge', default = None,
              envvar = cc_public.eval.runner.NAME_ENV_MODEL, show_envvar = True,
              help = 'The model that judges what the run produces. Needed '
                     'unless the deployment judges nothing.')
@click.option('--trailer', 'list_trailer', multiple = True,
              help = 'A trailer line for any commit the run makes.')
@click.option('--format', 'id_format', default = 'text',
              type = click.Choice(['text', 'json']), show_default = True)
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path))
def resume_(id_execution, id_model_judge, list_trailer, id_format, root):
    """
    Continue a run that is waiting at an agent node, once the work its
    brief asks for is in the tree.

    """

    import json

    tree = cc_public.cli.group.tree([root])

    try:
        record = tree.context.map_document[tree.resolve(id_execution).location]
        dep    = _deployment_of(tree, record)
        generator = cc_public.workflow.generate.build(dep.get('model'))
        generator_challenge = (cc_public.workflow.generate.build(dep['model_challenge'])
                               if dep.get('model_challenge') else None)
        runner = None
        if dep.get('judge', 'always') != 'never' and id_model_judge:
            runner = cc_public.eval.runner.build(id_model_judge)
        report = cc_public.workflow.run.resume(root, id_execution, generator, runner,
                                               list_trailer,
                                               generator_challenge = generator_challenge)
    except (cc_public.workflow.run.Stop, cc_public.workflow.graph.ErrorGraph,
            cc_public.edit.tree.ErrorItem, cc_public.commit.ErrorCommit) as err:
        cc_public.cli.group.fail(err)

    if id_format == 'json':
        click.echo(json.dumps(report, indent = 2, default = str))
    else:
        cc_public.cli.report.write_run(report)

    raise SystemExit(cc_public.cli.group.EXIT_NONCONFORMITY if report['stopped']
                     else cc_public.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
def _deployment_of(tree, record):
    """
    Return the deployment document an execution ran under.

    """

    for edge in record.get('relation') or []:
        if edge.get('id_relation') == cc_public.workflow.run.REL_RAN_UNDER:
            return tree.context.map_document[tree.resolve(edge['id_target']).location]

    raise cc_public.edit.tree.ErrorItem(
            '{exe} names no deployment.'.format(exe = record.get('id_self')))
