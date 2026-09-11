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
                        before a final newline as well. The check
                        refuses the line break itself.
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


def test_the_rule_reaches_an_item_held_within_another(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'term_performer', 'term', prose = 'performer')
    report   = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    entry    = [n for n in found['nonconformity'] if 'holds a datum' in n['message']]
    (one,)   = entry                                     # once, not once per pass
    assert one['path'] == 'table.term_performer.term'


def test_an_undeclared_field_is_reported_beside_any_other_fault(tree, tmp_path):
    # Every error lies beneath the root, so the rule that hid a
    # parent's unevaluated fields behind a child's own fault hid a
    # field nobody declared behind any other fault the item had. A
    # skeleton made by new fails until every field is written, which is
    # exactly when a misspelled field is accepted.
    cc_public.edit.field.set_field(tree, ID, 'frobnicate', value = 'nonsense')
    assert any('nevaluated' in m for m in _findings(tmp_path)), _findings(tmp_path)

    cc_public.edit.field.set_field(tree, ID, 'title', value = '')
    found = _findings(tmp_path)
    assert any('nevaluated' in m for m in found), found
    assert len(found) > 1


def test_one_fault_on_a_register_entry_is_reported_once(tree, tmp_path):
    # An entry is validated against the envelope by the register
    # schema, by the register's own schema and by the entry schema
    # composing sch_entry, and identical findings were not collapsed.
    cc_public.edit.field.set_field(tree, 'term_anchor', 'brief', value = '')

    report = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    said = [(n['path'], n['message']) for n in found['nonconformity']
            if 'reg_term' in n['filepath']]

    assert said, said
    assert len(said) == len(set(said)), said


def test_a_required_field_whose_description_calls_it_optional_is_reported(tree, tmp_path):
    # A schema is what travels to a partner, so it says one thing about
    # a field or the reader believes the wrong one. sch_entry_type
    # called id_term optional while requiring it.
    cc_public.edit.field.set_field(
            tree, 'sch_entry_type', 'properties.id_term.description',
            prose = 'Optional. Readable id of the term entry.')

    report = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    said = [n['message'] for n in found['nonconformity'] if 'sch_entry_type' in n['filepath']]

    assert any('description calls it optional' in m for m in said), said


def test_a_definition_that_is_a_bare_reference_to_a_schema_is_reported(tree, tmp_path):
    # One shape with two names: the next register schema copied from a
    # neighbour carries whichever it copied.
    cc_public.edit.field.set_field(
            tree, 'sch_register', '$defs.register_entry',
            value = {'$ref': 'https://capability-commons.org/schema/sch_entry.yaml'})

    report = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']
    said = [n['message'] for n in found['nonconformity'] if 'sch_register' in n['filepath']]

    assert any('gives one shape two names' in m for m in said), said


def test_a_bare_reference_to_a_primitive_is_not_reported(tree, tmp_path):
    # It names a role for a type, which six definitions do.
    report = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'schema']

    assert not [n for n in found['nonconformity'] if 'two names' in n['message']]
