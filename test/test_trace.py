"""
---

id_self:                pym_test.test_trace
guid_self:              pym_a88ded64db1f45608ea6879678c78dbd
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Trace tests
brief:                  |
                        Requirements trace to code, the projection
                        says what each lacks by status and world, and
                        the trace command reads it.
description:            |
                        Exercises the implementation relation at every
                        grain and its refusals, the projection's gaps
                        for proposed and accepted requirements in open
                        and closed worlds, leaves and children, the
                        impact of a change to a source item, and the
                        trace command's json and text.
relation:               []

...
"""


import json

import click.testing

import cc_public.check
import cc_public.cli.command
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.load
import cc_public.trace
from conftest import DEFAULTS, clean


def test_requirements_trace_to_code_and_the_projection_says_what_each_lacks(tree, tmp_path):

    # The tree's requirements are accepted; these start again from proposed.
    for req in ('req_printer_idempotent', 'req_renamer_keeps_guid', 'req_executor_honours_budget'):
        cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')

    # A requirement names code at any of the four grains, and several of them:
    # the tree already names the layout module; a function and a package join.
    cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.layout.format', DEFAULTS)
    for (field, value) in (('title', 'Format'), ('description', 'Lays a document out.')):
        cc_public.edit.field.set_field(tree, 'pyf_cc_public.layout.format', field, value = value)
    cc_public.edit.link.link(tree, 'req_printer_idempotent', 'r_is_implemented_by', 'pyf_cc_public.layout.format')
    cc_public.edit.link.link(tree, 'req_renamer_keeps_guid', 'r_is_implemented_by', 'pyp_cc_public.edit')
    assert clean(tmp_path) == []

    # An invalid subject and a non-source target are refused by the relation check.
    cc_public.edit.link.link(tree, 'need_layout_stable', 'r_is_implemented_by', 'pym_cc_public.layout')
    cc_public.edit.link.link(tree, 'req_executor_honours_budget', 'r_is_implemented_by', 'sch_port')
    faults = [(c, m) for (c, m) in clean(tmp_path) if c == 'relation']
    assert len(faults) == 2 and all('r_is_implemented_by' in m for (_, m) in faults)
    cc_public.edit.field.unset_field(tree, 'need_layout_stable', 'relation.0')
    doc = cc_public.load.from_file(tmp_path / 'requirement' / 'req_executor_honours_budget.yaml')
    cc_public.edit.field.unset_field(tree, 'req_executor_honours_budget',
                                     'relation.{n}'.format(n = len(doc['relation']) - 1))
    assert clean(tmp_path) == []

    # The projection: proposed gaps are advisory; every one is a leaf; the
    # printer requirement names its code and is verified by nothing here,
    # since the fixture tree carries no tests.
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    printer = by['req_printer_idempotent']
    assert printer.status == 'proposed' and printer.is_leaf
    assert printer.implemented_by == ('pym_cc_public.layout', 'pyf_cc_public.layout.format')
    assert printer.derives_from == ('need_layout_stable',)
    assert [(g.path, g.severity) for g in printer.gap] == [('verification', 'advisory')]
    assert [g.path for g in by['req_executor_honours_budget'].gap] == ['verification']
    doc = cc_public.load.from_file(tmp_path / 'requirement' / 'req_executor_honours_budget.yaml')
    cc_public.edit.field.unset_field(tree, 'req_executor_honours_budget',
                                     'relation.{n}'.format(n = len(doc['relation']) - 1))
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    assert [g.severity for g in by['req_executor_honours_budget'].gap] == ['advisory', 'advisory']



def test_an_accepted_requirement_lacks_critically_and_the_trace_command_reads_the_projection(tree, tmp_path):
    for req in ('req_printer_idempotent', 'req_renamer_keeps_guid', 'req_executor_honours_budget'):
        cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.layout.format', DEFAULTS)
    for (field, value) in (('title', 'Format'), ('description', 'Lays a document out.')):
        cc_public.edit.field.set_field(tree, 'pyf_cc_public.layout.format', field, value = value)
    cc_public.edit.link.link(tree, 'req_printer_idempotent', 'r_is_implemented_by', 'pyf_cc_public.layout.format')

    # Accepted: gaps become critical, and in an open world a leaf's are advisory.
    cc_public.edit.field.set_field(tree, 'req_executor_honours_budget', 'status', value = 'accepted')
    ctx = cc_public.check.context([tmp_path])[0]
    open_world   = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    closed_world = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document, True)}
    assert [g.severity for g in open_world['req_executor_honours_budget'].gap] == ['advisory']
    assert [g.severity for g in closed_world['req_executor_honours_budget'].gap] == ['critical']
    cc_public.edit.field.unset_field(tree, 'req_executor_honours_budget', 'success_criteria')
    ctx = cc_public.check.context([tmp_path])[0]
    gaps = {r.id_self: r.gap for r in cc_public.trace.projection(ctx.map_document)}
    assert ('success_criteria', 'critical') in [(g.path, g.severity)
                                                for g in gaps['req_executor_honours_budget']]
    faults = [(c, m) for (c, m) in clean(tmp_path) if c == 'trace']
    assert len(faults) == 1 and 'no success criteria' in faults[0][1]

    # A child makes its parent no leaf; a deprecated requirement lacks nothing.
    cc_public.edit.link.link(tree, 'req_printer_idempotent', 'r_is_derived_from',
                             'req_executor_honours_budget')
    cc_public.edit.field.set_field(tree, 'req_renamer_keeps_guid', 'status', value = 'deprecated')
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document, True)}
    assert not by['req_executor_honours_budget'].is_leaf
    assert by['req_executor_honours_budget'].children == ('req_printer_idempotent',)
    assert by['req_renamer_keeps_guid'].gap == ()

    # The reverse: what a source item may affect.
    imp = cc_public.trace.impact(ctx.map_document, 'pym_cc_public.layout')
    assert [r.id_self for r in imp.implements] == ['req_printer_idempotent'] and imp.verifies == ()
    assert cc_public.trace.impact(ctx.map_document, 'nothing_here') is None
    guid = tree.resolve('pyf_cc_public.layout.format').guid_self
    assert [r.id_self for r in cc_public.trace.impact(ctx.map_document, guid).implements] \
           == ['req_printer_idempotent']

    # The command reads the same projection, as json in a stable order.
    runner = click.testing.CliRunner()
    out    = runner.invoke(cc_public.cli.command.main,
                           ['trace', '--root', str(tmp_path), '--format', 'json', '--closed-world'])
    assert out.exit_code == 0, out.output
    rows = json.loads(out.output)
    assert [r['id_self'] for r in rows] == sorted(r['id_self'] for r in rows)
    assert next(r for r in rows if r['id_self'] == 'req_printer_idempotent')['implemented_by'] \
           == ['pym_cc_public.layout', 'pyf_cc_public.layout.format']
    out = runner.invoke(cc_public.cli.command.main,
                        ['trace', '--root', str(tmp_path), '--source', 'pym_cc_public.layout'])
    assert out.exit_code == 0 and 'implements   req_printer_idempotent' in out.output
    out = runner.invoke(cc_public.cli.command.main,
                        ['trace', '--root', str(tmp_path), '--gaps', '--requirement', 'req_renamer_keeps_guid'])
    assert out.exit_code == 0 and '0 requirement(s), 0 with gaps' in out.output
