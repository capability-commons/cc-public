"""
---

id_self:                pym_cc_public.cli.assurance
guid_self:              pym_091ea6c8043a4ae4a7c817a4fdaa9ac4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Assurance commands
brief:                  |
                        questions, trace, show and attest: what is
                        open, what a requirement rests on, what an
                        item is, and what a person observed.
description:            |
                        Each reads a projection from the foundations
                        and renders it through the report module,
                        except attest, which writes an attestation
                        through the evidence module. trace shows a
                        requirement, a source item's impact, or what
                        the files changed since a commit may affect.
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
@click.option('--open', 'is_open_only', is_flag = True,
              help = 'Only the questions nothing has answered.')
@cc_public.cli.group.OPTION_ROOT
def questions(is_open_only, list_root):
    """
    List what the design decisions leave open, and what answered it.

    """

    list_row = cc_public.question.report(cc_public.cli.group.tree(list_root).context.map_document)
    count    = 0

    for (_id_record, id_question, text, list_answerer) in list_row:
        if is_open_only and list_answerer:
            continue
        count += 1
        state = 'open' if not list_answerer else 'answered by ' + ', '.join(list_answerer)
        click.echo('{q}\n    {state}\n    {text}'.format(
                        q = id_question, state = state,
                        text = text if len(text) <= 100 else text[:97] + '...'))

    click.echo('{n} question(s){only}.'.format(n = count,
                                            only = ' open' if is_open_only else ''))


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--requirement', 'list_requirement', multiple = True,
              help = 'A requirement to show, by readable id or guid. May be '
                     'given more than once. Absent, every requirement.')
@click.option('--source', 'list_source', multiple = True,
              help = 'A source item, by readable id or guid: show the '
                     'requirements it implements and the ones it verifies.')
@click.option('--changed-since', 'ref', default = None, metavar = 'REF',
              help = 'Show what the files changed since REF, a commit or a '
                     'branch, may affect: every item in them that implements '
                     'or verifies a requirement. Potentially affected; a '
                     'static edge claims no more.')
@click.option('--gaps', 'is_gaps_only', is_flag = True,
              help = 'Show only requirements that lack something.')
@click.option('--closed-world', 'is_closed_world', is_flag = True,
              help = 'Assert the tree holds everything an edge could point '
                     'at, so that a leaf with nothing implementing it lacks '
                     'it entirely rather than perhaps elsewhere.')
@click.option('--format', 'id_format', type = click.Choice(['text', 'json']),
              default = 'text', show_default = True,
              help = 'text for a person; json for a program, in a stable order.')
@cc_public.cli.group.OPTION_ROOT
def trace(list_requirement, list_source, ref, is_gaps_only, is_closed_world,
          id_format, list_root):
    """
    Show what each requirement derives from, what implements it, what
    verifies it, and what it lacks; or, for a source item, what it may
    affect.

    Reads what the trace check reads, and writes nothing.

    """

    tree         = cc_public.cli.group.tree(list_root)
    map_document = tree.context.map_document

    if ref is not None:
        try:
            set_filepath = cc_public.load.git.changed_since(tree.root, ref)
        except cc_public.load.git.ErrorGit as err:
            cc_public.cli.group.fail(err)
        cc_public.cli.report.write_impact(
            cc_public.trace.impact_of_files(map_document, set_filepath, is_closed_world),
            id_format)
        return

    if list_source:
        list_impact = [cc_public.trace.impact(map_document, name, is_closed_world)
                       for name in list_source]
        if None in list_impact:
            cc_public.cli.group.fail(
                'Nothing in this tree is named {name}.'.format(
                        name = list_source[list_impact.index(None)]))
        cc_public.cli.report.write_impact(list_impact, id_format)
        return

    list_record = cc_public.trace.projection(map_document, is_closed_world)

    if list_requirement:
        wanted = set(list_requirement)
        list_record = [r for r in list_record
                         if r.id_self in wanted or r.guid_self in wanted]
        if len(list_record) != len(wanted):
            cc_public.cli.group.fail('Not every requirement named is in this tree.')

    if is_gaps_only:
        list_record = [r for r in list_record if r.gap]

    cc_public.cli.report.write_trace(list_record, id_format)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.argument('name')
@click.option('--format', 'id_format', type = click.Choice(['text', 'json']),
              default = 'text', show_default = True,
              help = 'text for a person; json for a program.')
@cc_public.cli.group.OPTION_ROOT
def show(name, id_format, list_root):
    """
    Show one item, by readable id or guid: where it is, what it says of
    itself, every edge it holds, and every edge that points at it.

    """

    map_document = cc_public.cli.group.tree(list_root).context.map_document
    found        = cc_public.trace.neighbourhood(map_document, name)

    if found is None:
        cc_public.cli.group.fail('Nothing in this tree is named {name}.'.format(name = name))

    cc_public.cli.report.write_neighbourhood(found, id_format)


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--requirement', 'name_requirement', required = True,
              help = 'The requirement attested, by readable id or guid. Its '
                     'verification method must be inspection, demonstration '
                     'or analysis; a test observes itself.')
@click.option('--outcome', 'outcome', required = True,
              type = click.Choice(['passed', 'failed']),
              help = 'What the observer found.')
@click.option('--by', 'observer', required = True,
              help = 'Who or what observed: a person, or a tool and its version.')
@click.option('--note', 'note', default = None,
              help = 'What was inspected, demonstrated or analysed, and how.')
@cc_public.cli.group.OPTION_ROOT
def attest(name_requirement, outcome, observer, note, list_root):
    """
    Record that a person or a tool found a requirement met, or not, by
    the method it declares.

    The row is stamped with the digest of the requirement and the code
    implementing it as they are now, so that the evidence check can say
    when the attestation no longer applies.

    """

    tree = cc_public.cli.group.tree(list_root)

    try:
        path = cc_public.evidence.attest(tree, name_requirement, outcome, observer, note)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    click.echo(str(path))
