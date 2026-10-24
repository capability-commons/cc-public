"""
---

id_self:                pym_cctool.check._test.test_friction
guid_self:              pym_3895afa31c574fdb8d48535cb1721746
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Friction tests
brief:                  |
                        Tests of the friction report, each over a copy
                        of the repository.
description:            |
                        Each test reads the signals of a copy, some
                        after changing it, and one runs cctool
                        friction to see that the report never fails.
edge:                   []

...
"""


import click.testing

import cctool.check.friction
import cctool.cli.command


# -----------------------------------------------------------------------------
def test_a_term_two_concepts_share_is_a_signal(tree):
    report = cctool.check.friction.friction(tree)
    assert ('item', 'concept_identifiable_data_item', 'concept_item') in report['shared_term']


def test_a_deprecated_term_is_not_shared(tree):
    # "issue" is a deprecated term of concept_decision. Giving another
    # concept the same term as preferred does not make it shared.
    path = tree / '_data/register/reg_concept.yaml'
    path.write_text(path.read_text().replace('term_preferred:     finding\n',
                                             'term_preferred:     issue\n'))
    report = cctool.check.friction.friction(tree)
    assert [row for row in report['shared_term'] if row[0] == 'issue'] == []


def test_a_prefix_exception_is_a_signal(tree):
    report = cctool.check.friction.friction(tree)
    assert [row[0] for row in report['rule_exception']] == ['type_python_class']


def test_a_decision_with_no_ruling_is_open(tree):
    list_open = [row[0] for row in cctool.check.friction.friction(tree)['open_decision']]
    assert 'dec_tooling_language' in list_open
    assert 'dec_cross_item_checks_engine' not in list_open


def test_the_report_counts_each_signal_and_never_fails(tree):
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['friction', '--root', str(tree)])
    assert result.exit_code == 0, result.output
    assert 'shared_term: concept_identifiable_data_item and concept_item share the term item.' \
        in result.output
    assert '\nopen_decision: ' in result.output
