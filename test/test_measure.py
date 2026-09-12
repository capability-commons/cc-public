"""
---

id_self:                pym_test.test_measure
guid_self:              pym_b2f92f99ae944b67ad50e9b7566ca01a
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Measurement tests
brief:                  |
                        Control cases measure an eval and answer its
                        findings.
description:            |
                        These tests use a scripted runner in place of
                        a model. They assert the arithmetic of the
                        rates, the split per origin, and the
                        suppression path.
relation:               []

...
"""


import click.testing
import pytest

import cc_public.check
import cc_public.check.confidence
import cc_public.check.result
import cc_public.cli.command
import cc_public.edit.tree
import cc_public.eval.case
import cc_public.eval.check
import cc_public.control
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.load




class Scripted:
    """A runner answering from a table of normalised subject -> verdicts."""

    id_model = 'scripted'

    def __init__(self, table):
        self.table = table

    def _answer(self, task):
        return self.table.get(cc_public.control.normalise(task.text_input),
                              ['met'])

    def run(self, task):
        return cc_public.eval.runner.Verdict(task.id_eval, task.id_subject,
                                             self._answer(task)[0], 'scripted',
                                             self.id_model)

    def confirm(self, task, verdict, count):
        return verdict

    def sample(self, task, count):
        answers = self._answer(task)
        return [answers[i % len(answers)] for i in range(count)]




ID_SET = 'ctl_test_exercises_criteria'


def test_case_makes_set_and_suppresses(tree, tmp_path):
    (id_set, id_case) = cc_public.eval.case.case(
                tree, 'evl_prose_matches_structure', 'pym_cc_public.load.yaml', 'met',
                'Describes the loader. The judge misreads an effect as an argument.')
    assert id_set == 'ctl_prose_matches_structure'
    assert id_case.startswith('case_prose_matches_structure.')

    doc = cc_public.load.from_file(tmp_path / 'eval' / 'ctl_prose_matches_structure.yaml')
    case = doc['case'][id_case.rsplit('.', 1)[1]]
    assert case['verdict'] == 'met' and case['origin'] == 'suppressed'
    # Stored as written, so the printer does not refill the code in it.
    assert cc_public.control.is_verbatim(case['subject'])
    assert cc_public.control.as_written(case['subject']).startswith(
                                                    '--- pym_cc_public.load.yaml')
    assert any(e['id_relation'] == 'r_is_snapshot_of' for e in case['relation'])

    # A sweep whose judge says unmet on that very text now reports a note.
    tree2    = cc_public.edit.tree.Tree([tmp_path])
    ctx      = tree2.context._replace(
                    selector_eval = cc_public.eval.select.Selector(
                                        id_eval = ('evl_prose_matches_structure',),
                                        id_item = ('pym_cc_public.load.yaml',)),
                    runner_eval   = Scripted({cc_public.control.normalise(
                                        cc_public.control.as_written(
                                                case['subject'])): ['unmet']}),
                    count_confirm = 1)
    result = cc_public.eval.check.check(ctx)
    assert result.list_nonconformity == []
    assert any('judged met by hand' in n.message for n in result.list_note)

    faults = [(c['id_check'], n['message'])
              for c in cc_public.check.check(list_path = [tmp_path])['report']['check']
              for n in c['nonconformity'] if n['severity'] == 'critical']
    assert faults == []


def test_measure_rates_per_origin(tree, tmp_path):
    for (item, verdict, note) in (('pym_cc_public.load.yaml', 'met',   'a'),
                                  ('pym_cc_public.load.xml',  'met',   'b'),
                                  ('sch_primitive',           'unmet', 'c')):
        cc_public.eval.case.case(tree, 'evl_prose_matches_structure', item, verdict, note)

    tree2 = cc_public.edit.tree.Tree([tmp_path])
    ev    = tree2.context.map_document[tree2.resolve('evl_prose_matches_structure').location]
    cases = list(cc_public.control.iter_case(tree2.context.map_document,
                                                  ev['guid_self']))
    assert len(cases) == 3

    # Judge: right on the first met case, always wrong on the second, and
    # split on the unmet one (majority met, so a false negative).
    # Keyed by what measure sends, which is the subject as rendered.
    # Keying by the stored text is why a printer-refilled subject went
    # unnoticed: no test saw what the judge was given.
    subj = {k: cc_public.control.normalise(cc_public.control.as_written(c['subject']))
            for (_, k, c) in cases}
    by   = {c['verdict']: [] for (_, _, c) in cases}
    for (_, k, c) in cases:
        by[c['verdict']].append(subj[k])
    table = {by['met'][0]: ['met'], by['met'][1]: ['unmet'],
             by['unmet'][0]: ['met', 'met', 'unmet']}
    (rows, detail) = cc_public.eval.measure.measure(tree2.context, ev,
                                                    Scripted(table), 3)
    pooled = next(r for r in rows if r['origin'] == 'all')
    assert pooled['cases'] == 3
    assert pooled['false_positive'] == 0.5
    assert pooled['false_negative'] == 1.0
    assert pooled['unanimous'] == round(2 / 3, 3)
    assert {r['origin'] for r in rows} == {'suppressed', 'confirmed', 'all'}

    cc_public.eval.measure.record(tree2, 'evl_prose_matches_structure', rows, 'scripted')
    ev2 = cc_public.load.from_file(tree2.resolve('evl_prose_matches_structure').filepath)
    assert {r['origin'] for r in ev2['confidence']} == {'suppressed', 'confirmed', 'all'}
    assert all(r['model'] == 'scripted' for r in ev2['confidence'])


def test_a_majority_needs_an_odd_count_everywhere(tree, tmp_path):
    majority = cc_public.eval.runner.majority
    assert majority(['unmet', 'met', 'unmet']) == 'unmet'
    assert majority(['met', 'met', 'unmet']) == 'met'
    assert majority(['unmet']) == 'unmet'
    assert majority(['unknown', 'unknown', 'unknown']) == 'met'
    for bad in ([], ['met', 'unmet'], ['unmet'] * 4):
        with pytest.raises(ValueError):
            majority(bad)
    for bad in (0, -1, 2, 4, '3'):
        with pytest.raises(ValueError):
            cc_public.eval.runner.check_count(bad, 'The count')
    with pytest.raises(ValueError):
        cc_public.eval.check.judgement(cc_public.eval.select.Selector(), 'null', 2)
    ev = tree.context.map_document[tree.resolve('evl_prose_matches_structure').location]
    with pytest.raises(ValueError):
        cc_public.eval.measure.measure(tree.context, ev, Scripted({}), 2)

    result = click.testing.CliRunner().invoke(cc_public.cli.command.main,
                                              ['measure', '--id-eval', 'x', '--samples', '2'])
    assert result.exit_code == 2 and 'odd' in result.output
    result = click.testing.CliRunner().invoke(cc_public.cli.command.main,
                                              ['check', '--confirm', '4', '--path', str(tmp_path)])
    assert result.exit_code == 2 and 'odd' in result.output


def test_confidence_carries_the_digest_of_what_it_measured(tree, tmp_path):
    ev     = 'evl_prose_matches_structure'
    doc    = tree.context.map_document[tree.resolve(ev).location]
    before = cc_public.check.confidence.digest(doc, tree.context.map_document)
    assert len(before) == 8

    # Refilling prose does not change the digest; changing a case, the
    # criterion, an example or the scope does.
    cc_public.edit.field.set_field(tree, ev, 'criterion',
                                   prose = ' '.join(doc['criterion'].split()) + '\n')
    doc = tree.context.map_document[tree.resolve(ev).location]
    assert cc_public.check.confidence.digest(doc, tree.context.map_document) == before
    seen = {before}
    cc_public.eval.case.case(tree, ev, 'sch_primitive', 'unmet', 'a case')
    doc = tree.context.map_document[tree.resolve(ev).location]
    seen.add(cc_public.check.confidence.digest(doc, tree.context.map_document))
    cc_public.edit.field.set_field(tree, ev, 'criterion', prose = 'Another criterion.\n')
    doc = tree.context.map_document[tree.resolve(ev).location]
    seen.add(cc_public.check.confidence.digest(doc, tree.context.map_document))
    cc_public.edit.field.set_field(tree, ev, 'scope', value = {'include': ['title']})
    doc = tree.context.map_document[tree.resolve(ev).location]
    seen.add(cc_public.check.confidence.digest(doc, tree.context.map_document))
    assert len(seen) == 4

    # Recording stamps the rows, the check is quiet, and a later change
    # makes the rows stale, which the check reports as advisory.
    rows = [{'origin': 'all', 'cases': 1, 'samples': 3, 'false_positive': 0.0,
             'false_negative': 0.0, 'unanimous': 1.0}]
    cc_public.eval.measure.record(tree, ev, rows, 'scripted')
    ev2 = cc_public.load.from_file(tree.resolve(ev).filepath)
    assert ev2['confidence'][0]['digest'] == cc_public.check.confidence.digest(
                                                ev2, tree.context.map_document)

    def confidence():
        rep = cc_public.check.check(list_path = [tmp_path])['report']
        c   = next(c for c in rep['check'] if c['id_check'] == 'confidence')
        return ([n['message'] for n in c['nonconformity'] if ev in n['filepath']],
                [n['message'] for n in c['note'] if ev in n['filepath']])

    assert confidence() == ([], [])
    cc_public.edit.field.set_field(tree, ev, 'criterion', prose = 'Changed again.\n')
    (bad, note) = confidence()
    assert bad and 'scripted' in bad[0] and 'since changed' in bad[0] and note == []
    cc_public.edit.field.set_field(tree, ev, 'confidence',
                                   value = [dict(model = 'scripted', date = '2026-01-01', **rows[0])])
    (bad, note) = confidence()
    assert bad == [] and note and 'before rows carried a digest' in note[0]

    # A sweep says once, per eval, that its findings carry no confidence.
    selector = cc_public.eval.select.Selector(id_eval = (ev,))
    rep = cc_public.check.check(list_path = [tmp_path],
                                judgement = cc_public.eval.check.judgement(selector, 'null', 1))['report']
    c   = next(c for c in rep['check'] if c['id_check'] == 'eval')
    assert sum('no current confidence for null' in n['message'] for n in c['note']) == 1
    assert c['detail']['count_call_max'] == c['detail']['count_call'] * 1
    assert c['detail']['count_char'] > 0


class Sampled(cc_public.eval.runner.DspyRunner):
    """The judge's confirmation over scripted fresh samples, no model needed."""

    def __init__(self, samples):
        self.id_model = 'sampled'
        self.samples  = list(samples)
        self.asked    = []

    def sample(self, task, count):
        self.asked.append(count)
        return [self.samples.pop(0) for _ in range(count)]


def test_an_unmet_screen_is_confirmed_count_times_and_the_majority_reported(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_measure.test_an_unmet_screen_is_confirmed_count_times_and_the_majority_reported
    guid_self:              pyf_9bc5b3f1136c42be92f969c533edd42a
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  An unmet screen is confirmed count times and the majority reported
    brief:                  |
                            An unmet screen is confirmed count times and
                            the majority reported.
    description:            |
                            The test confirms an unmet screening verdict
                            over scripted fresh samples. It asserts that
                            the judge asks for one fewer sample than the
                            count, that it reports met where the majority
                            is met, that it reports unmet with the tally
                            where the majority is unmet, and that it asks
                            for nothing when the count is one.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_judge_confirms_unmet
        guid_target:        req_ad4f5b42320a4f3f9aa2b1b9457b32f3

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_judge_reports_confirmed_verdict
        guid_target:        req_7e8813d18aa3443ba6cb92805469a451

    ...
    """

    task    = cc_public.eval.select.Task('evl_x', {}, ('sch_x',), 'x', 'subject')
    screen  = cc_public.eval.runner.Verdict('evl_x', ('sch_x',), 'unmet', 'because', 'sampled')

    judge   = Sampled(['met', 'met', 'unmet', 'met'])
    verdict = judge.confirm(task, screen, 5)
    assert judge.asked == [4]                      # the screen counts as the first
    assert verdict.verdict == 'met'                # two unmet of five: variance

    judge   = Sampled(['unmet', 'met', 'unmet', 'unmet'])
    verdict = judge.confirm(task, screen, 5)
    assert verdict.verdict == 'unmet'
    assert verdict.feedback.startswith('Unmet on 4 of 5 judgements.')

    judge   = Sampled([])
    assert judge.confirm(task, screen, 1) is screen
    assert judge.asked == []


def test_an_eval_with_no_cases_cannot_be_measured(tree, tmp_path):
    ev = tree.context.map_document[tree.resolve('evl_prose_matches_structure').location]
    with pytest.raises(ValueError):
        cc_public.eval.measure.measure(tree.context, ev, Scripted({}), 3)


def test_every_control_case_holds_what_the_projection_renders_now():
    # A case is a snapshot, and a snapshot of text no sweep produces
    # suppresses nothing and confirms nothing. All nine coverage cases
    # and twelve across nine other sets had drifted from the
    # projection while the confidence check read every row current,
    # because the digest covers the stored subjects and not what the
    # projection makes of the items they name.
    import conftest

    import cc_public.check
    import cc_public.control
    import cc_public.eval.select

    context = cc_public.check.context([conftest.ROOT])[0]
    live    = {task.id_subject: task.text_input
               for task in cc_public.eval.select.select(context)}

    # The coverage control set, which this holds exactly. Every other
    # set is reported alongside, because the case command and the
    # sweep projection still render an embedded item differently and
    # twelve snapshots elsewhere differ for that reason, which is
    # qst_eval_measurement.rendered and not this.
    drifted = []
    elsewhere = []

    for document in context.map_document.values():
        if not isinstance(document, dict):
            continue
        for (key, case) in (document.get('case') or {}).items():
            if not isinstance(case, dict):
                continue
            # A written or a mutated case is meant to differ: one a
            # person wrote, one altered on purpose. A suppressed or a
            # confirmed case is a snapshot of a finding, and a
            # snapshot of text no sweep renders suppresses nothing and
            # confirms nothing.
            if case.get('origin') not in ('suppressed', 'confirmed'):
                continue
            snap = tuple(edge['id_target'] for edge in case.get('relation') or []
                         if edge.get('id_relation') == 'r_is_snapshot_of')
            if snap in live and \
                    live[snap] != cc_public.control.as_written(case.get('subject', '')):
                (drifted if document.get('id_self') == ID_SET
                         else elsewhere).append((document.get('id_self'), key))

    assert drifted == [], drifted
    assert len(elsewhere) == 12, elsewhere


def test_a_stored_subject_survives_the_printer_as_it_was_rendered():
    # The printer refills the paragraphs of a block scalar, so a
    # definition line was broken across lines and a module joined into
    # one paragraph. A heading and an indent under it survive both the
    # printer and the loader.
    import cc_public.control
    import cc_public.layout

    text  = '--- pyf_probe\ntitle: T\n\nsource:\ndef probe():\n    return 1\n'
    held  = cc_public.control.verbatim(text)
    assert cc_public.control.as_written(held) == text

    laid  = cc_public.layout.format(
                'id_self:                ctl_probe\nsubject:                |\n'
                + '\n'.join('                        ' + line if line.strip() else ''
                            for line in held.split('\n')) + '\n')
    assert 'def probe():' in laid
    assert 'as rendered:' in laid
