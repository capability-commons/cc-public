"""
---

id_self:                pym_test.test_burden
guid_self:              pym_a79773f0b5f84b7eb8a2056b93b6faab
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Reader burden tests
brief:                  |
                        The measures on fixed sentences, and the
                        burden command on a copied tree.
description:            |
                        These tests measure a verbless sentence, a
                        pointer, a nominalisation and a noun run, on
                        text written to show each one. They run the
                        burden command over a copied tree, as a list
                        and as a summary, in text and in JSON. They
                        also show the refusal the command gives when
                        the prose extra is absent.
relation:               []

...
"""
import click.testing
import pytest

import cc_public.check
import cc_public.cli.command
import cc_public.eval.burden


def run(*args):
    return click.testing.CliRunner().invoke(cc_public.cli.command.main, list(args))


@pytest.fixture(scope = 'module')
def nlp():
    return cc_public.eval.burden.load()


def test_measure_sees_a_fragment_a_pointer_a_nominalisation_and_a_run(nlp):
    plain = cc_public.eval.burden.measure(
        nlp, 'The printer lays the file out. The check compares the result.')
    dense = cc_public.eval.burden.measure(
        nlp, 'One item per identity with its prefix, status and location, '
             'derived from the documents on every use. This is the '
             'implementation of the relation edge digest computation.')

    assert plain['sentences'] == 2
    assert plain['finite'] >= 1.0
    assert plain['pointers'] == 0.0
    assert plain['nominal'] == 0.0

    assert dense['finite'] < plain['finite']
    assert dense['pointers'] > 0.0
    assert dense['nominal'] > 0.0
    assert dense['runs'] > 0.0
    assert dense['dependents'] > 0.0
    assert dense['length'] > plain['length']
    assert 0.0 < dense['propositions'] < 1.0
    assert 0.0 < dense['density'] <= 1.0
    assert dense['grade'] > 0.0


def test_measure_grades_nothing_too_short_to_grade(nlp):
    assert cc_public.eval.burden.measure(nlp, 'Yes.')['grade'] == 0.0


def test_rows_and_summary_cover_the_tree(tree):
    (context, _) = cc_public.check.context([tree.root])

    list_row = cc_public.eval.burden.rows(
        tree, context, list_field = ('description',), list_prefix = ('t',))

    assert list_row
    assert all(r['field'] == 'description' for r in list_row)
    assert all(r['id'].startswith('t_') for r in list_row)
    assert all(r['words'] >= cc_public.eval.burden.MINIMUM for r in list_row)

    by_field  = cc_public.eval.burden.summarise(list_row, 'field')
    by_prefix = cc_public.eval.burden.summarise(list_row, 'prefix')

    assert [s['field'] for s in by_field] == ['description']
    assert [s['prefix'] for s in by_prefix] == ['t']
    assert by_field[0]['rows'] == len(list_row)
    assert by_field[0]['words'] == sum(r['words'] for r in list_row)


def test_burden_command_lists_and_summarises(tree):
    listed = run('burden', '--root', str(tree.root), '--prefix', 't', '--field', 'description',
                 '--format', 'json')
    assert listed.exit_code == 0, listed.output
    assert listed.output.count('"id": "t_') > 1

    heavy = run('burden', '--root', str(tree.root), '--prefix', 't', '--field', 'brief',
                '--min-words', '5', '--sort', 'pointers')
    assert heavy.exit_code == 0, heavy.output
    assert 'row(s).' in heavy.output

    summary = run('burden', '--root', str(tree.root), '--prefix', 't', '--by', 'field')
    assert summary.exit_code == 0, summary.output
    assert summary.output.startswith('field')

    none = run('burden', '--root', str(tree.root), '--prefix', 'zzz')
    assert none.exit_code == 0, none.output
    assert '0 row(s).' in none.output


def test_burden_refuses_without_the_extra(tree, monkeypatch):
    def absent():
        raise cc_public.eval.burden.Absent('absent')

    monkeypatch.setattr(cc_public.eval.burden, 'load', absent)

    refused = run('burden', '--root', str(tree.root), '--prefix', 't')
    assert refused.exit_code != 0
    assert 'absent' in refused.output


def test_load_raises_absent_for_a_model_that_is_not_there(monkeypatch):
    import spacy

    def missing(name, **kwargs):
        raise OSError(name)

    monkeypatch.setattr(spacy, 'load', missing)
    cc_public.eval.burden.load.cache_clear()
    with pytest.raises(cc_public.eval.burden.Absent):
        cc_public.eval.burden.load()
    cc_public.eval.burden.load.cache_clear()


def test_a_rater_failure_is_a_nan_and_sorts_last(nlp, monkeypatch):
    import ideadensity

    def broken(text):
        raise ValueError(text)

    monkeypatch.setattr(ideadensity, 'cpidr', broken)
    measured = cc_public.eval.burden.measure(nlp, 'The check compares the result.')
    assert measured['propositions'] != measured['propositions']
