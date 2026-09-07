"""
---

id_self:                pym_test.test_schema
guid_self:              pym_b4eb1d78ee574e9d9eb090f1a39caa94
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Schema check tests
brief:                  |
                        Tests that a pattern-constrained field refuses
                        a value written as a block scalar.
description:            |
                        A pattern constrains a datum, and a datum
                        holds no line break. The draft reads a regular
                        expression by ECMA-262, where a dollar anchors
                        the end of the string, while Python matches it
                        before a final newline as well, so an anchored
                        pattern accepts a block scalar and says
                        nothing. The check refuses the line break
                        itself.
relation:               []

...
"""


import pathlib

import cc_public.check
import cc_public.edit.field


ID   = 'need_agent_asks_graph'
PATH = 'entity'


def _findings(tmp_path):
    report   = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    return [n['message'] for n in found['nonconformity'] if ID in n['filepath']]


def test_a_datum_written_as_a_block_scalar_is_refused(tree, tmp_path):
    assert _findings(tmp_path) == []
    cc_public.edit.field.set_field(tree, ID, PATH, prose = 'Tool')
    (message,) = _findings(tmp_path)
    assert 'holds a datum' in message and 'no line break' in message


def test_the_same_value_as_a_datum_conforms(tree, tmp_path):
    cc_public.edit.field.set_field(tree, ID, PATH, prose = 'Tool')
    assert _findings(tmp_path) != []
    cc_public.edit.field.unset_field(tree, ID, PATH)
    cc_public.edit.field.set_field(tree, ID, PATH, value = 'Tool')
    assert _findings(tmp_path) == []


def test_a_value_that_breaks_the_pattern_is_still_refused(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'term_performer', 'term', value = 'NOT a term!')
    report   = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    assert any('does not match' in n['message'] for n in found['nonconformity'])
