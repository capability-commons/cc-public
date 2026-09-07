"""
---

id_self:                pym_test.test_select
guid_self:              pym_62403ea9ad984541a86bddf4520bdf20
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Eval selector tests
brief:                  |
                        Tests that the selector reaches an item held
                        within another, and that such an item takes
                        the schema its type names.
description:            |
                        A register entry is a subject of the evals
                        anchored to sch_descriptive, which composes
                        into every entry schema through sch_entry. A
                        type register entry takes the schema of an
                        entry and not the schema of the items it
                        describes, although it names the second by an
                        edge.
relation:               []

...
"""


import pathlib

import cc_public.check
import cc_public.check.register
import cc_public.check.schema
import cc_public.eval.select


ID_EVAL = 'evl_plain_text'


def _subjects(tmp_path, id_eval = ID_EVAL):
    (context, _) = cc_public.check.context([pathlib.Path(tmp_path)], False, None)
    return {name for task in cc_public.eval.select.select(context)
            if task.id_eval == id_eval for name in task.id_subject}


def _prefix(tmp_path):
    (context, _) = cc_public.check.context([pathlib.Path(tmp_path)], False, None)
    return cc_public.check.register.map_prefix(
                    cc_public.check.register.find_type(context.map_document)[1])


def _entry(tmp_path, id_register, key):
    (context, _) = cc_public.check.context([pathlib.Path(tmp_path)], False, None)
    for document in context.map_document.values():
        if isinstance(document, dict) and document.get('id_self') == id_register:
            return document['table'][key]
    raise KeyError(id_register)


def test_a_register_entry_is_a_subject(tree, tmp_path):
    subject = _subjects(tmp_path)
    assert 'term_segment' in subject
    assert 'unit_metre' in subject or any(s.startswith('unit_') for s in subject)


def test_the_register_holding_it_is_a_subject_too(tree, tmp_path):
    assert 'reg_term' in _subjects(tmp_path)


def test_every_type_entry_is_a_subject(tree, tmp_path):
    subject = _subjects(tmp_path)
    assert {'t_term', 't_commit', 't_decision', 't_sweep'} <= subject


def test_an_embedded_item_takes_the_schema_its_type_names(tree, tmp_path):
    entry = _entry(tmp_path, 'reg_type', 't_commit')
    prefix = _prefix(tmp_path)
    assert cc_public.check.schema.select_schema(
                    entry, prefix, is_embedded = True)[0] == 'sch_entry_type'
    assert cc_public.check.schema.select_schema(
                    entry, prefix)[0] == 'sch_commit'
