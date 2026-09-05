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
                        Uses a scripted runner in place of a model, so
                        that the arithmetic of the rates, the per
                        origin split, and the suppression path can be
                        asserted exactly.

...
"""

import pathlib
import shutil

import click.testing
import pytest

import cc_public.check
import cc_public.check.eval
import cc_public.check.result
import cc_public.cli.command
import cc_public.edit.case
import cc_public.edit.tree
import cc_public.eval.control
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.load


ROOT = pathlib.Path(__file__).resolve().parent.parent
KEEP = ('ddr', 'schema', 'register', 'eval', 'workflow', 'src', 'pyproject.toml')


class Scripted:
    """A runner answering from a table of normalised subject -> verdicts."""

    id_model = 'scripted'

    def __init__(self, table):
        self.table = table

    def _answer(self, task):
        return self.table.get(cc_public.eval.control.normalise(task.text_input),
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


@pytest.fixture
def tree(tmp_path):
    for name in KEEP:
        src = ROOT / name
        (shutil.copytree if src.is_dir() else shutil.copy)(src, tmp_path / name)
    return cc_public.edit.tree.Tree([tmp_path])


def test_case_makes_set_and_suppresses(tree, tmp_path):
    (id_set, id_case) = cc_public.edit.case.case(
                tree, 'evl_prose_matches_structure', 'pym_cc_public.load.yaml', 'met',
                'Describes the loader. The judge misreads an effect as an argument.')
    assert id_set == 'ctl_prose_matches_structure'
    assert id_case.startswith('case_prose_matches_structure.')

    doc = cc_public.load.from_file(tmp_path / 'eval' / 'ctl_prose_matches_structure.yaml')
    case = doc['case'][id_case.rsplit('.', 1)[1]]
    assert case['verdict'] == 'met' and case['origin'] == 'suppressed'
    assert case['subject'].startswith('--- pym_cc_public.load.yaml')
    assert any(e['id_relation'] == 'r_is_snapshot_of' for e in case['relation'])

    # A sweep whose judge says unmet on that very text now reports a note.
    tree2    = cc_public.edit.tree.Tree([tmp_path])
    ctx      = tree2.context._replace(
                    selector_eval = cc_public.eval.select.Selector(
                                        id_eval = ('evl_prose_matches_structure',),
                                        id_item = ('pym_cc_public.load.yaml',)),
                    runner_eval   = Scripted({cc_public.eval.control.normalise(
                                                case['subject']): ['unmet']}),
                    count_confirm = 1)
    result = cc_public.check.eval.check(ctx)
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
        cc_public.edit.case.case(tree, 'evl_prose_matches_structure', item, verdict, note)

    tree2 = cc_public.edit.tree.Tree([tmp_path])
    ev    = tree2.context.map_document[tree2.resolve('evl_prose_matches_structure').filepath]
    cases = list(cc_public.eval.control.iter_case(tree2.context.map_document,
                                                  ev['guid_self']))
    assert len(cases) == 3

    # Judge: right on the first met case, always wrong on the second, and
    # split on the unmet one (majority met, so a false negative).
    subj = {k: cc_public.eval.control.normalise(c['subject']) for (_, k, c) in cases}
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
        cc_public.check.check(list_path = [tmp_path], count_confirm = 2)
    ev = tree.context.map_document[tree.resolve('evl_prose_matches_structure').filepath]
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
    doc    = tree.context.map_document[tree.resolve(ev).filepath]
    before = cc_public.eval.measure.digest(doc, tree.context.map_document)
    assert len(before) == 8

    # Refilling prose does not change the digest; changing a case, the
    # criterion, an example or the scope does.
    cc_public.edit.field.set_field(tree, ev, 'criterion',
                                   prose = ' '.join(doc['criterion'].split()) + '\n')
    doc = tree.context.map_document[tree.resolve(ev).filepath]
    assert cc_public.eval.measure.digest(doc, tree.context.map_document) == before
    seen = {before}
    cc_public.edit.case.case(tree, ev, 'sch_primitive', 'unmet', 'a case')
    doc = tree.context.map_document[tree.resolve(ev).filepath]
    seen.add(cc_public.eval.measure.digest(doc, tree.context.map_document))
    cc_public.edit.field.set_field(tree, ev, 'criterion', prose = 'Another criterion.\n')
    doc = tree.context.map_document[tree.resolve(ev).filepath]
    seen.add(cc_public.eval.measure.digest(doc, tree.context.map_document))
    cc_public.edit.field.set_field(tree, ev, 'scope', value = {'include': ['title']})
    doc = tree.context.map_document[tree.resolve(ev).filepath]
    seen.add(cc_public.eval.measure.digest(doc, tree.context.map_document))
    assert len(seen) == 4

    # Recording stamps the rows, the check is quiet, and a later change
    # makes the rows stale, which the check reports as advisory.
    rows = [{'origin': 'all', 'cases': 1, 'samples': 3, 'false_positive': 0.0,
             'false_negative': 0.0, 'unanimous': 1.0}]
    cc_public.eval.measure.record(tree, ev, rows, 'scripted')
    ev2 = cc_public.load.from_file(tree.resolve(ev).filepath)
    assert ev2['confidence'][0]['digest'] == cc_public.eval.measure.digest(
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
    rep = cc_public.check.check(list_path = [tmp_path], selector_eval = selector,
                                id_model_eval = 'null', count_confirm = 1)['report']
    c   = next(c for c in rep['check'] if c['id_check'] == 'eval')
    assert sum('no current confidence for null' in n['message'] for n in c['note']) == 1
    assert c['detail']['count_call_max'] == c['detail']['count_call'] * 1
    assert c['detail']['count_char'] > 0
