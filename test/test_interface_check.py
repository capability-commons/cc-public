"""
---

id_self:                pym_test.test_interface_check
guid_self:              pym_d6368026ca36494c9e911f686dae5392
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Interface check tests
brief:                  |
                        Tests that a member disagreeing with its key,
                        its siblings, its declaration reference, its
                        source or its language is reported.
description:            |
                        Each fault is written into the specimen and
                        the check is run over a copy of the tree. The
                        messages asserted are the ones the check
                        reports.
relation:               []

...
"""


import pathlib

import cc_public.check
import cc_public.edit.field
import cc_public.edit.link


ID       = 'icd_cc_public_query'
PARAM    = 'surface.python.native.class.database.method.path.parameter.0'
NAME_ARG = PARAM + '.name'


def _findings(tmp_path):
    report   = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'interface']
    return [n['message'] for n in found['nonconformity']]


def test_the_specimen_as_it_stands_earns_nothing(tree, tmp_path):
    assert _findings(tmp_path) == []


def test_an_identity_that_does_not_end_with_its_key_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, ID, 'surface.python.native.function.named.id_self',
            value = 'icm_cc_public_query.other')
    (message,) = _findings(tmp_path)
    assert 'ends other' in message and 'holds it is named' in message


def test_an_identity_not_qualified_by_its_document_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, ID, 'surface.python.native.function.named.id_self',
            value = 'icm_something_else.named')
    (message,) = _findings(tmp_path)
    assert 'identified by icm_cc_public_query' in message


def test_two_members_of_one_table_sharing_a_name_are_reported(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, ID, 'surface.python.native.function.drawing.name', value = 'named')
    messages = _findings(tmp_path)
    assert any('are named named' in message for message in messages)


def test_a_type_naming_a_declaration_the_document_lacks_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(tree, ID, PARAM + '.type',
                                   value = {'declaration': 'identifier'})
    (message,) = _findings(tmp_path)
    assert 'Names the declaration identifier' in message


def test_a_parameter_mode_python_does_not_have_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(tree, ID, PARAM + '.mode', value = 'output')
    (message,) = _findings(tmp_path)
    assert 'A parameter of a python surface is input' in message


def test_a_member_whose_source_does_not_carry_its_name_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(
            tree, ID, 'surface.python.native.function.named.name', value = 'nomen')
    messages = _findings(tmp_path)
    assert any('does not end with that name' in message for message in messages)
