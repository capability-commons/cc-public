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
from conftest import DEFAULTS, clean, unverify


def test_requirements_trace_to_code_and_the_projection_says_what_each_lacks(tree, tmp_path):

    # The tree's requirements are accepted; these start again from proposed.
    for req in ('req_printer_idempotent', 'req_renamer_keeps_guid', 'req_executor_honours_budget'):
        cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
        unverify(tree, req)

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
    # since the copy holds no tests and unverify took the case away.
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
        unverify(tree, req)
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


# -----------------------------------------------------------------------------
# A verdict that stands for two requirements. The fixture tree holds no
# test/, so the verifiers here are cases, which are data and are copied.

SHARED  = 'Every verifier observes another requirement too'
ID_WALK = 'req_walk_reports_neighbourhood'
ID_ONLY = 'req_walk_follows_named_relations'


def _shared(tmp_path, id_requirement):
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    return [g for g in by[id_requirement].gap if SHARED in g.message]


def test_a_verdict_shared_between_requirements_is_reported(tree, tmp_path):
    # tc_walk_follows_named_relations verifies one requirement. Give it a
    # second, and it can no longer say which of the two a verdict was about.
    cc_public.edit.link.link(tree, 'tc_walk_follows_named_relations',
                             'r_verifies', ID_WALK)

    (gap,) = _shared(tmp_path, ID_ONLY)
    assert gap.severity == 'advisory' and ID_WALK in gap.message

    # The walk requirement keeps a case of its own, so nothing is lost
    # for it and it is not reported.
    assert _shared(tmp_path, ID_WALK) == []


def test_a_criticality_that_requires_a_verdict_makes_it_critical(tree, tmp_path):
    cc_public.edit.link.link(tree, 'tc_walk_follows_named_relations',
                             'r_verifies', ID_WALK)
    cc_public.edit.field.set_field(
        tree, ID_ONLY, 'criticality',
        value = {'safety': {
            'id_criticality':   'crit_safety_60',
            'guid_criticality': tree.resolve('crit_safety_60').guid_self}})

    (gap,) = _shared(tmp_path, ID_ONLY)
    assert gap.severity == 'critical'

    # And the level decides it, not this test: a level that does not
    # require the objective leaves the finding advisory.
    cc_public.edit.field.set_field(
        tree, ID_ONLY, 'criticality',
        value = {'safety': {
            'id_criticality':   'crit_safety_40',
            'guid_criticality': tree.resolve('crit_safety_40').guid_self}})
    assert _shared(tmp_path, ID_ONLY)[0].severity == 'advisory'


def test_an_evidential_claim_makes_a_shared_verdict_critical(tree, tmp_path):
    cc_public.edit.link.link(tree, 'tc_walk_follows_named_relations',
                             'r_verifies', ID_WALK)
    cc_public.edit.field.set_field(tree, ID_ONLY, 'claim', value = 'evidential')
    assert _shared(tmp_path, ID_ONLY)[0].severity == 'critical'


def test_dividing_a_shared_verdict_clears_it_and_remerging_returns_it(tree, tmp_path):
    cc_public.edit.link.link(tree, 'tc_walk_follows_named_relations',
                             'r_verifies', ID_WALK)
    assert _shared(tmp_path, ID_ONLY) != []

    cc_public.edit.link.unlink(tree, 'tc_walk_follows_named_relations',
                               'r_verifies', ID_WALK)
    assert _shared(tmp_path, ID_ONLY) == []


def test_a_method_carried_out_by_a_person_is_asked_for_a_case_like_any_other(tree,
                                                                            tmp_path):
    # The tree holds one requirement verified by inspection, and its
    # case. Take the case away and the requirement is asked for one, in
    # the same words a requirement verified by test is asked.
    req = 'req_committer_writes_record'
    assert clean(tmp_path) == []

    unverify(tree, req)
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    (gap,) = [g for g in by[req].gap if g.path == 'verification']
    assert 'Verified by inspection, and nothing names it' in gap.message

    # And critically where the paths given hold everything, since an
    # accepted requirement has claimed to be complete.
    ctx = cc_public.check.context([tmp_path], True)[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document, True)}
    assert [g.severity for g in by[req].gap if g.path == 'verification'] == ['critical']


def test_a_requirement_that_names_no_method_is_asked_for_the_method_and_not_a_case(tree,
                                                                                  tmp_path):
    # Nothing names it is a gap about a stated method. A requirement
    # stating none is asked for the method first, and asking it for a
    # case as well would name two faults for one omission.
    req = 'req_committer_writes_record'
    unverify(tree, req)
    cc_public.edit.field.unset_field(tree, req, 'verification')
    ctx = cc_public.check.context([tmp_path])[0]
    by  = {r.id_self: r for r in cc_public.trace.projection(ctx.map_document)}
    message = [g.message for g in by[req].gap if g.path == 'verification']
    assert any('no verification method' in m for m in message), message
    assert not any('nothing names it' in m for m in message), message


def test_changed_lists_what_changed_and_what_rests_on_it(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_trace.test_changed_lists_what_changed_and_what_rests_on_it
    guid_self:              pyf_02fe06fb036e4c2dbbcfd7c669d6e70f
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  The changed projection lists what changed and what rests on it
    brief:                  |
                            What changed and what rests on it, read from
                            the projection over a tree of known shape.
    description:            |
                            Two annotations are made in a copy of the
                            tree, one about the layout module and one
                            challenging it; the projection over the layout
                            file names the module with its decision, and
                            reaches the requirement the module implements
                            and both annotations, the second through the
                            first, and nothing through r_verifies.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_changed_reports_dependents
        guid_target:        req_0786a6ec0c774c57ad73b6a3c68d7f43

    ...
    """

    # Two annotations: one about the layout module, one challenging it.
    for (id_self, title, target, relation) in (
            ('ann_layout_slow', 'The printer is slow', 'pym_cc_public.layout', 'r_is_about'),
            ('ann_layout_cached', 'The layout is cached', 'ann_layout_slow', 'r_is_about')):
        cc_public.edit.new.new(tree, 't_annotation', id_self, DEFAULTS)
        cc_public.edit.field.set_field(tree, id_self, 'title', value = title)
        cc_public.edit.field.set_field(tree, id_self, 'brief', value = title + '.')
        cc_public.edit.link.link(tree, id_self, relation, target)
    cc_public.edit.link.link(tree, 'ann_layout_cached', 'r_challenges', 'ann_layout_slow')
    assert clean(tmp_path) == []

    ctx  = cc_public.check.context([tmp_path])[0]
    file = {loc.filepath for loc in ctx.map_document
            if loc.filepath.parts[-2:] == ('cc_public', 'layout.py')}
    (changed, dependent) = cc_public.trace.changed(ctx.map_document, file)

    # The module is the one standalone item in the file, and its decision is named.
    assert [c.id_self for c in changed] == ['pym_cc_public.layout']
    assert changed[0].prefix == 'pym' and changed[0].decided_by == ('ddr_layout_convention',)

    # What rests on it: the requirement it implements, the annotation about it,
    # and the annotation challenging that one, each with the edge it holds and
    # the changed item the chain ends at. r_verifies declares no dependency,
    # so nothing is reached through it.
    by = {d.id_self: d for d in dependent}
    assert by['req_printer_idempotent'].id_relation == 'r_is_implemented_by'
    assert (by['ann_layout_slow'].id_relation, by['ann_layout_slow'].id_target) \
                == ('r_is_about', 'pym_cc_public.layout')
    assert by['ann_layout_cached'].id_relation in ('r_is_about', 'r_challenges')
    assert (by['ann_layout_cached'].id_target, by['ann_layout_cached'].changed) \
                == ('ann_layout_slow', 'pym_cc_public.layout')
    assert not any(d.id_self.startswith('pyf_test') for d in dependent)
    assert dependent == sorted(dependent)
