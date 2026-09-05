"""
---

id_self:                pym_cc_public.cli.judging
guid_self:              pym_680f985033a442b79af41f2386f9f966
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Judging commands
brief:                  |
                        measure and case: what a judge is measured
                        against, and how a finding becomes a case.
description:            |
                        measure judges an eval's control cases fresh
                        and writes the rates, for one eval or for
                        every eval whose confidence for the judge is
                        absent or stale. case turns a finding into a
                        control case, suppressed or confirmed as a
                        person judged it.
relation:               []

...
"""



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
@click.option('--id-eval', 'id_eval', default = None,
              help = 'The eval to measure, by readable id.')
@click.option('--stale', 'is_stale', is_flag = True,
              help = 'Measure every eval with cases whose confidence for this '
                     'judge is absent or stale, instead of naming one.')
@click.option('--samples', 'count_sample', default = 5,
              type = cc_public.cli.group.ODD, show_default = True,
              help = 'Fresh judgements per case. Odd, so that a majority exists.')
@click.option('--record', 'is_record', is_flag = True,
              help = 'Write the rates onto the eval as its confidence for '
                     'this judge model, replacing earlier rows for it.')
@click.option('--judge-model', 'id_model_eval', default = None,
              envvar = cc_public.eval.runner.NAME_ENV_MODEL, show_envvar = True,
              help = 'The model that judges. Required.')
@cc_public.cli.group.OPTION_ROOT
def measure(id_eval, is_stale, count_sample, is_record, id_model_eval, list_root):
    """
    Judge the control cases for an eval and report the error rates.

    Every case is judged SAMPLES times without the cache. False
    positive is the share of met cases the judge called unmet; false
    negative the share of unmet cases it called met; unanimous the
    share of cases it answered the same way every time. Reported per
    origin and pooled. --stale measures every eval whose confidence
    for the judge is absent or stale, one after another.

    """

    tree = cc_public.cli.group.tree(list_root)

    if bool(id_eval) == is_stale:
        cc_public.cli.group.fail('Name one eval with --id-eval, or every stale one with --stale.')

    try:
        runner = cc_public.eval.runner.build(id_model_eval)
    except Exception as err:
        cc_public.cli.group.fail(err)

    list_id = cc_public.eval.measure.list_stale(tree.context, runner.id_model) \
              if is_stale else [id_eval]

    if not list_id:
        click.echo('  nothing is stale for {model}'.format(model = runner.id_model))

    for one in list_id:
        click.echo(one)
        _measure_one(tree, one, runner, count_sample, is_record)


# -----------------------------------------------------------------------------
def _measure_one(tree, id_eval, runner, count_sample, is_record):
    """
    Measure one eval and write the rates, recording them where asked.

    """

    try:
        item = tree.resolve(id_eval)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    document_eval  = tree.context.map_document[item.location]
    (rows, detail) = cc_public.eval.measure.measure(tree.context, document_eval,
                                                    runner, count_sample)

    for (id_case, origin, want, tally) in detail:
        click.echo('  {want:5} {origin:10} {tally}  {id_case}'.format(
                            want = want, origin = origin, id_case = id_case,
                            tally = '/'.join('U' if v == 'unmet' else 'M'
                                             if v == 'met' else '?'
                                             for v in tally)))
    click.echo()
    click.echo('  {:10} {:>5} {:>7} {:>14} {:>14} {:>9}'.format(
                    'origin', 'cases', 'samples', 'false_positive',
                    'false_negative', 'unanimous'))
    for row in rows:
        click.echo('  {origin:10} {cases:5} {samples:7} {fp:>14} {fn:>14} '
                   '{un:9}'.format(origin = row['origin'], cases = row['cases'],
                                   samples = row['samples'],
                                   fp = cc_public.cli.report.rate(row['false_positive']),
                                   fn = cc_public.cli.report.rate(row['false_negative']),
                                   un = row['unanimous']))

    if is_record:
        cc_public.eval.measure.record(tree, id_eval, rows, runner.id_model)
        click.echo('  recorded on {id_eval} for {model}'.format(
                                    id_eval = id_eval, model = runner.id_model))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'case')
@click.option('--id-eval', 'id_eval', required = True,
              help = 'The eval the finding came from.')
@click.option('--item', 'name_item', required = True,
              help = 'The item the finding was on, by readable id or guid.')
@click.option('--verdict', 'verdict', required = True,
              type = click.Choice(['met', 'unmet']),
              help = 'What a person holds the subject to. met answers the '
                     'finding; unmet confirms it.')
@click.option('--origin', 'origin', default = None,
              type = click.Choice(cc_public.control.ORIGIN_ALL),
              help = 'Where the case came from. Defaults to suppressed for '
                     'met and confirmed for unmet; written marks a subject '
                     'a person wrote and holds to the verdict.')
@click.option('--note', 'note', default = '',
              help = 'Why. Kept with the case and shown when it answers.')
@cc_public.cli.group.OPTION_ROOT
def case_(id_eval, name_item, verdict, origin, note, list_root):
    """
    Turn a finding into a control case.

    The item is rendered for the eval exactly as a sweep renders it,
    and that text becomes the case's subject. A later sweep matching
    the same words finds the case: met answers the finding as a note,
    unmet confirms it.

    """

    try:
        (id_set, id_case) = cc_public.eval.case.case(
                    cc_public.cli.group.tree(list_root), id_eval, name_item, verdict, note,
                    origin)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    click.echo('{set}  {case}'.format(set = id_set, case = id_case))
