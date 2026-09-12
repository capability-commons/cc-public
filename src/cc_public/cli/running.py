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
                        The run command builds the generator and the
                        judge that the deployment names, and hands
                        them to the executor with the bindings given.
                        It then renders what each node made, revised,
                        fired and declined, or why the run stopped.
relation:               []

...
"""


import pathlib

import click

import cc_public.adapter
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
import cc_public.nonconformity
import cc_public.eval.case
import cc_public.eval.check
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.evidence
import cc_public.layout
import cc_public.load.git
import cc_public.question
import cc_public.testing
import cc_public.trace
import cc_public.workflow.generate
import cc_public.workflow.graph
import cc_public.workflow.run


ID_TYPE_REPORT  = 't_nonconformity_report'

# What an execution says happened, and what it says about the item
# under test. They are two things: an execution that did not complete
# carries no result at all (ddr_test_execution).
#
KEY_OUTCOME     = 'execution_outcome'
KEY_RESULT      = 'result'
KEY_CONFORMANCE = 'conformance_result'
OUTCOME_COMPLETED    = 'completed'
RESULT_PASSED        = 'passed'
RESULT_NOT_APPLICABLE = 'not_applicable'
KEY_EXPECTATION = 'expectation'


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
@click.option('--root', 'list_root', multiple = True,
              type = click.Path(path_type = pathlib.Path),
              help = 'The repository run in, then the trees it consumes. May be '
                     'given more than once; the first is where items are made.')
def run_(id_workflow, id_deployment, list_bind, is_dry, id_model_judge,
         list_trailer, id_format, list_root):
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

    root = list(list_root) or [pathlib.Path('.')]
    tree = cc_public.cli.group.tree(root)

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
@click.option('--root', 'list_root', multiple = True,
              type = click.Path(path_type = pathlib.Path),
              help = 'The repository resumed in, then the trees it consumes. May be '
                     'given more than once; the first is where items are made.')
def resume_(id_execution, id_model_judge, list_trailer, id_format, list_root):
    """
    Continue a run that is waiting at an agent node, once the work its
    brief asks for is in the tree.

    """

    import json

    root = list(list_root) or [pathlib.Path('.')]
    tree = cc_public.cli.group.tree(root)

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


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'test')
@click.argument('name_case')
@click.option('--under-test', 'name_under_test', required = True,
              help = 'The item the run observes, by readable id or guid.')
@click.option('--record', 'is_record', is_flag = True,
              help = 'Write the execution to the tree.')
@click.option('--evidence', 'is_evidence', is_flag = True,
              help = 'Update the current verification evidence from the result.')
@click.option('--report', 'is_report', is_flag = True,
              help = 'Write a nonconformity report for each failed result, and '
                     'the execution it came from.')
@click.option('--format', 'id_format', type = click.Choice(['text', 'json']),
              default = 'text', show_default = True,
              help = 'text for a person; json for a program.')
@cc_public.cli.group.OPTION_ROOT
def test_(name_case, name_under_test, is_record, is_evidence, is_report,
          id_format, list_root):
    """
    Run the test case NAME_CASE against the item under test.

    The case names the method, the method names the adapter, and the
    adapter is one installed with the tool. Nothing the case carries
    reaches a shell.

    A failed result is shown as the report it makes, whatever the
    options. Nothing is written unless it is asked for: --record keeps
    the execution, --evidence brings the current evidence up to what
    was observed, and --report keeps the reports, and with them the
    execution they name. Without any of them the run leaves the
    repository as it found it.

    """

    tree = cc_public.cli.group.tree(list_root)

    # Both are resolved here, so that a guid names what a readable id
    # names, as it does everywhere else. What runs the case indexes by
    # readable id alone.
    #
    id_case  = tree.resolve(name_case).id_self
    id_under = tree.resolve(name_under_test).id_self

    (document, list_problem) = cc_public.adapter.execute(tree, id_case, id_under)

    if document is None:
        cc_public.cli.group.fail('\n'.join(list_problem))

    defaults = dict(tree.defaults())
    defaults['guid_mark'] = tree.resolve(defaults['id_mark']).guid_self
    case     = tree.context.map_document[tree.resolve(id_case).location]

    def reported(is_kept):
        return cc_public.nonconformity.from_execution(
                        tree.context.map_document, document, defaults,
                        cc_public.testing.expectation(tree.context.map_document,
                                                      case.get('id_self')),
                        is_kept)

    list_report = reported(False)

    written = []

    if not list_problem:

        # A report names the execution that produced it, so keeping one
        # keeps that too. A report about a run the tree does not hold
        # could not be followed back to what was observed.
        #
        is_kept = is_record or (is_report and list_report)

        if is_kept:
            written.append(cc_public.adapter.record(tree, document))
            list_report = reported(True)

        if is_evidence and cc_public.evidence.from_execution(
                                    tree, document, is_kept) is not None:
            written.append(cc_public.evidence.ID_PYTEST)

        if is_report:
            written.extend(cc_public.edit.new.from_document(
                                    tree, ID_TYPE_REPORT, report)
                           for report in list_report)

    cc_public.cli.report.write_execution_test(document, list_report, list_problem,
                                              written, id_format)

    # A caller reads the exit status, as it does of run and resume. A
    # result that is not passed, and an execution that did not
    # complete, are both failures of the run (ddr_test_execution).
    #
    if not _is_passed(document):
        raise SystemExit(cc_public.cli.group.EXIT_NONCONFORMITY)


# -----------------------------------------------------------------------------
def _is_passed(document):
    """
    Return whether an execution completed and every result it holds
    says the item under test met what was expected.

    """

    if document.get(KEY_OUTCOME) != OUTCOME_COMPLETED:
        return False

    return all(one.get(KEY_CONFORMANCE) in (RESULT_PASSED, RESULT_NOT_APPLICABLE)
               for one in (document.get(KEY_RESULT) or {}).values())
