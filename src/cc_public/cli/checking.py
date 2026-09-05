"""
---

id_self:                pym_cc_public.cli.checking
guid_self:              pym_17f14ede03a74bf29f9f31eccabb2408
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Checking commands
brief:                  |
                        check and format: the mechanical checks as a
                        report, and the printer over a tree.
description:            |
                        check adapts its options into a judgement for
                        the driver where evals are asked for, writes
                        the report in the format asked, and turns it
                        into an exit status: two for a failure of the
                        analysis always, one for a critical finding
                        only when asked. format lays every document
                        out, or says what it would change.
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
@click.option('--path',
              'list_path',
              multiple = True,
              type     = click.Path(path_type = pathlib.Path),
              help     = 'A file or directory tree to check. May be given '
                         'more than once, and the check runs over the union '
                         'of all of them. Defaults to the working directory.')
@click.option('--fail-on-nonconformity',
              'is_fail_on_nonconformity',
              is_flag = True,
              help    = 'Exit non zero on a critical nonconformity. '
                        'Advisories never affect the exit status, since an '
                        'unresolved reference is ordinary in a federated '
                        'slice. Without this flag only a failure of the '
                        'analysis itself is reported in the exit status. Set '
                        'it for a continuous integration gate; leave it unset '
                        'for an agentic process that reads the report.')
@click.option('--fail-fast',
              'is_fail_fast',
              is_flag = True,
              help    = 'Stop at the first critical nonconformity and report '
                        'only that one. Advisories neither stop the run nor '
                        'get trimmed. Set this where the feedback loop '
                        'matters more than completeness.')
@click.option('--closed-world',
              'is_closed_world',
              is_flag = True,
              help    = 'Assert that the paths given hold everything a '
                        'reference could resolve to. A reference that does '
                        'not resolve is then a fault rather than a sharing '
                        'boundary, and is reported as critical rather than '
                        'advisory. Set this for a single repository; leave '
                        'it unset for a federated slice.')
@click.option('--eval',
              'is_eval',
              is_flag = True,
              help    = 'Run the evals. Off by default, because an eval '
                        'costs tokens and seconds where every other check '
                        'costs nothing. Any selector below implies this.')
@click.option('--id-eval',    'id_eval',    multiple = True,
              help = 'Select evals by readable id. An anchored regular '
                     'expression, so a plain id matches only itself.')
@click.option('--guid-eval',  'guid_eval',  multiple = True,
              help = 'Select evals by guid. Exact; a guid has no structure '
                     'worth matching part of.')
@click.option('--id-schema',  'id_schema',  multiple = True,
              help = 'Select evals anchored on a schema, by its readable id. '
                     'Regular expression.')
@click.option('--guid-schema','guid_schema',multiple = True,
              help = 'Select evals anchored on a schema, by its guid. Exact.')
@click.option('--id-type',    'id_type',    multiple = True,
              help = 'Select evals anchored on a type, by its readable id. '
                     'Regular expression.')
@click.option('--guid-type',  'guid_type',  multiple = True,
              help = 'Select evals anchored on a type, by its guid. Exact.')
@click.option('--id-item',    'id_item',    multiple = True,
              help = 'Select the items to be judged, by readable id -- every '
                     'eval that applies to them. Regular expression.')
@click.option('--guid-item',  'guid_item',  multiple = True,
              help = 'Select the items to be judged, by guid. Exact.')
@click.option('--judge-model',
              'id_model_eval',
              default      = None,
              envvar       = cc_public.eval.runner.NAME_ENV_MODEL,
              show_envvar  = True,
              help         = 'The model that judges the evals, named as '
                             'dspy names one -- anthropic/claude-sonnet-4-5, '
                             'openai/gpt-5.1. Name it null for a dry run '
                             'that reports what would be judged without '
                             'judging it. Required when evals are asked '
                             'for. Should not be the same model family as '
                             'wrote the items being judged.')
@click.option('--confirm',
              'count_confirm',
              type    = cc_public.cli.group.ODD,
              default = cc_public.eval.runner.COUNT_CONFIRM,
              show_default = True,
              help    = 'Over how many judgements an adverse verdict is '
                        'confirmed before it is reported. The screen is one '
                        'call and only what comes back unmet is asked again, '
                        'so on a clean corpus this costs little. One believes '
                        'the screen alone. Odd, so that a majority exists.')
@click.option('--out',
              'filepath_out',
              type    = click.Path(path_type = pathlib.Path),
              default = None,
              help    = 'Write the report to this file rather than to the '
                        'console.')
@click.option('--format',
              'id_format',
              type    = click.Choice(cc_public.cli.report.FORMAT_ALL),
              default = cc_public.cli.report.FORMAT_TEXT,
              show_default = True,
              help    = 'Report serialisation. text is for a person; the '
                        'others are for a program.')
def check(list_path,
          is_fail_on_nonconformity,
          is_fail_fast,
          is_closed_world,
          is_eval,
          id_model_eval,
          id_eval,
          guid_eval,
          id_schema,
          guid_schema,
          id_type,
          guid_type,
          id_item,
          guid_item,
          count_confirm,
          filepath_out,
          id_format):
    """
    Check the data for conformity.

    """

    selector = cc_public.eval.select.Selector(id_eval     = id_eval,
                                              guid_eval   = guid_eval,
                                              id_schema   = id_schema,
                                              guid_schema = guid_schema,
                                              id_type     = id_type,
                                              guid_type   = guid_type,
                                              id_item     = id_item,
                                              guid_item   = guid_item)

    # Any selector implies --eval. Naming what to judge and then not
    # judging it would be a surprising thing for the tool to do.
    #
    if not (is_eval or any(selector)):
        selector = None

    judgement = cc_public.eval.check.judgement(selector, id_model_eval, count_confirm) \
                if selector is not None else None
    report    = cc_public.check.check(list_path       = list_path,
                                      is_fail_fast    = is_fail_fast,
                                      is_closed_world = is_closed_world,
                                      judgement       = judgement)

    list_error = report['report']['error']
    list_error.extend(cc_public.cli.report.write(report,
                                                 id_format,
                                                 filepath_out))

    cc_public.cli.report.write_error(list_error)

    raise SystemExit(_status(report, list_error, is_fail_on_nonconformity))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'format')
@click.option('--path',
              'list_path',
              multiple = True,
              type     = click.Path(path_type = pathlib.Path),
              help     = 'A file or directory tree to lay out. May be given '
                         'more than once, and the command runs over the '
                         'union of all of them. Defaults to the working '
                         'directory.')
@click.option('--check',
              'is_check',
              is_flag = True,
              help    = 'Report what would change and write nothing. Exits '
                        'non zero where anything would, which is what a '
                        'hook or a pipeline wants.')
def format_(list_path, is_check):
    """
    Lay documents out to the layout convention.

    """

    list_path    = list_path or (pathlib.Path('.'),)
    list_changed = []
    list_error   = []

    for filepath in sorted(set(cc_public.check.iter_filepath_all(list_path))):

        if filepath.suffix not in (cc_public.layout.SUFFIX_YAML,
                                   cc_public.layout.SUFFIX_PYTHON):
            continue

        try:
            text = filepath.read_text(encoding = 'utf-8')
        except (OSError, UnicodeDecodeError) as error:
            list_error.append('{filepath}: {error}'.format(filepath = filepath,
                                                           error    = error))
            continue

        formatted = cc_public.layout.format_source(text, filepath.suffix)

        if formatted == text:
            continue

        list_changed.append(filepath)

        if not is_check:
            cc_public.edit.tree.write_text(filepath, formatted)

    verb = 'would change' if is_check else 'changed'

    for filepath in list_changed:
        click.echo('{verb}  {filepath}'.format(verb = verb, filepath = filepath))

    click.echo('{count} file(s) {verb}.'.format(count = len(list_changed),
                                                verb  = verb))

    cc_public.cli.report.write_error(list_error)

    if list_error:
        raise SystemExit(cc_public.cli.group.EXIT_ERROR)

    raise SystemExit(cc_public.cli.group.EXIT_NONCONFORMITY if (is_check and list_changed)
                                        else cc_public.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
def _status(report, list_error, is_fail_on_nonconformity):
    """
    Return the exit status.

    A failure of the analysis is always reported in the exit status. A
    critical nonconformity is reported only when asked for, because the
    ordinary case is a caller that wants to read the report rather than
    be stopped by it. An advisory never affects the exit status at all --
    it is something to know about, and in a federated slice there may
    always be some.

    """

    if list_error:
        return cc_public.cli.group.EXIT_ERROR

    if is_fail_on_nonconformity and report['report']['summary'][
                                                    'count_critical']:
        return cc_public.cli.group.EXIT_NONCONFORMITY

    return cc_public.cli.group.EXIT_OK
