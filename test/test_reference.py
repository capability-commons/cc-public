"""
---

id_self:                pym_test.test_reference
guid_self:              pym_8dd447fdaaa14104abed954944df6c29
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Reference check tests
brief:                  |
                        Tests that an identifier written in prose is
                        read like one written in a field.
description:            |
                        The reference check read the identity fields
                        of an item and said nothing about the prose
                        beside them, and most of what a record asserts
                        is in the prose. A review found records naming
                        a command no longer run, a check said to read
                        a flag it has no key for, and six type entries
                        saying no schema names them where one does
                        (ddr_prose_reference).
relation:               []

...
"""


import pathlib

import cc_public.check
import cc_public.edit.field


def _prose_findings(tmp_path):
    report = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']

    return [n['message'] for c in report['check'] if c['id_check'] == 'reference'
            for n in c['nonconformity'] if 'holds no item for' in n['message']]


def test_an_identifier_in_prose_that_resolves_to_nothing_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, 'ddr_gate_tool', 'brief',
            prose = 'What the gate believes, and what r_is_never_made does not say.\n')

    found = _prose_findings(tmp_path)
    assert any('r_is_never_made' in message for message in found), found


def test_a_file_name_and_a_path_into_an_item_are_not_identifiers(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, 'ddr_gate_tool', 'brief',
            prose = 'Written in sch_entry_gate_tool.yaml, whose t_gate_tool.prefix is gt.\n')

    found = _prose_findings(tmp_path)
    assert not [m for m in found
                if 'sch_entry_gate_tool' in m or 't_gate_tool.prefix' in m], found


def test_what_a_record_rejects_is_not_reported(tree, tmp_path):
    # A record naming what it considered and rejected is the predicted
    # false alarm, and the alternative field is where that lives.
    cc_public.edit.field.set_field(
            tree, 'ddr_gate_tool', 'alternative',
            prose = 'Name it r_is_never_made instead. Rejected: it says less.\n')

    assert not [m for m in _prose_findings(tmp_path) if 'r_is_never_made' in m]
