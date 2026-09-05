"""
---

id_self:                pym_test.test_source
guid_self:              pym_755645e90d0845b6968cbfef54bec1f8
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Source item tests
brief:                  |
                        A class or function becomes an item in its
                        docstring, is named by where it sits, and
                        shows its source to an eval.
description:            |
                        Copies the tree and makes function and class
                        items through new, asserting the docstring
                        becomes a document the printer lays out, the
                        edit commands address it, the source check
                        refuses a document whose id is not where it
                        sits, the prefix tells a class from a function
                        of one name, and the renderer projects a
                        definition's source where an eval names source
                        in its scope.
relation:               []

...
"""


import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.rename
import cc_public.edit.tree
import cc_public.eval.select
import cc_public.layout
import cc_public.load
import cc_public.load.python
from conftest import DEFAULTS, clean


def test_a_function_becomes_an_item_in_its_own_docstring(tree, tmp_path):

    # The definition's prose docstring becomes the brief; the file still
    # parses, lays out as the printer would, and the checks are clean.
    path = cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.path.select', DEFAULTS)
    text = path.read_text()
    assert cc_public.layout.format_metadata(text) == text
    docs = dict(cc_public.load.iter_document(path))
    loc  = cc_public.load.Location(path, ('select',), 'function')
    assert loc in docs and docs[loc]['id_self'] == 'pyf_cc_public.path.select'
    assert docs[loc]['brief'].strip() and docs[loc]['title'] == ''
    assert str(loc).endswith('path.py::select')
    item = tree.resolve('pyf_cc_public.path.select')
    assert item.location == loc and item.path == ''
    faults = clean(tmp_path)
    assert faults and all(c == 'schema' for (c, _) in faults)        # title is empty, as new leaves it

    # The edit commands address it like any item.
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.path.select', 'title', value = 'Select')
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.path.select', 'description',
                                   prose = 'Walks a dot path.')
    cc_public.edit.link.link(tree, 'ddr_path_notation', 'r_decides', 'pyf_cc_public.path.select')
    assert clean(tmp_path) == []
    text = path.read_text()
    assert cc_public.layout.format_metadata(text) == text
    assert 'def select(' in text and "id_self:                pyf_cc_public.path.select" in text
    assert cc_public.load.from_file(path)['id_self'] == 'pym_cc_public.path'   # the module is untouched

    # A class too, and a method beneath it, named in lower case.
    cc_public.edit.new.new(tree, 't_python_class', 'pyc_cc_public.edit.tree.tree', DEFAULTS)
    cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.edit.tree.tree.resolve', DEFAULTS)
    assert tree.resolve('pyf_cc_public.edit.tree.tree.resolve').location.anchor == ('Tree', 'resolve')

    # Refusals: a name that is not there, a kind that is wrong, a rename.
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.path.nothing', DEFAULTS)
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.new.new(tree, 't_python_class', 'pyc_cc_public.path.select', DEFAULTS)
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.rename.rename(tree, 'pyf_cc_public.path.select', 'pyf_cc_public.path.pick')


def test_a_source_item_is_named_by_where_it_sits(tree, tmp_path):
    cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.path.select', DEFAULTS)
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.path.select', 'title', value = 'Select')
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.path.select', 'description', prose = 'Walks.')
    assert clean(tmp_path) == []
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.path.select', 'id_self',
                                   value = 'pyf_cc_public.path.write')
    faults = [(c, m) for (c, m) in clean(tmp_path) if c == 'source']
    assert len(faults) == 1 and 'sits in function select of pym_cc_public.path' in faults[0][1]


def test_a_class_and_a_function_of_one_name_are_told_apart_by_kind(tree, tmp_path):
    # check/__init__.py holds class Refusal and def refusal.
    cc_public.edit.new.new(tree, 't_python_class', 'pyc_cc_public.check.refusal', DEFAULTS)
    assert tree.resolve('pyc_cc_public.check.refusal').location.anchor == ('Refusal',)
    with pytest.raises(cc_public.edit.tree.ErrorItem):          # the function item exists already
        cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.check.refusal', DEFAULTS)
    for name in ('pyc_cc_public.check.refusal', 'pyf_cc_public.check.refusal'):
        for (field, value) in (('title', 'Refusal'), ('description', 'Why a report refuses.')):
            cc_public.edit.field.set_field(tree, name, field, value = value)
    assert clean(tmp_path) == []
    text = (tmp_path / 'src' / 'cc_public' / 'check' / '__init__.py').read_text()
    assert text.count('id_self:                pyc_cc_public.check.refusal') == 1
    assert text.count('id_self:                pyf_cc_public.check.refusal') == 1


def test_a_source_item_shows_its_source_where_an_eval_asks(tree, tmp_path):
    ctx = cc_public.check.context([tmp_path])[0]
    sel = cc_public.eval.select.Selector(id_eval = ('evl_record_and_code_agree',))
    tasks = list(cc_public.eval.select.select(ctx, sel))
    assert [t.id_subject for t in tasks] == [('ddr_fail_closed', 'pyf_cc_public.check.refusal')]
    text = tasks[0].text_input
    assert 'decision:' in text and 'source:' in text
    assert 'def refusal(report, is_checkpoint = False):' in text
    assert 'class Refusal' not in text                    # its own definition, not its module

    # Without source in scope, a source item shows only its fields; and a
    # class's source holds the methods beneath it.
    item = tree.resolve('pyf_cc_public.check.refusal')
    doc  = tree.context.map_document[item.location]
    plain = cc_public.eval.select.render(((item.id_self, doc, item.location),), {})
    assert 'def refusal' not in plain and 'title:' in plain
    text = (tmp_path / 'src' / 'cc_public' / 'check' / '__init__.py').read_text()
    src  = cc_public.load.python.source_of(text, ('Refusal',))
    assert src.startswith('class Refusal') and 'def message(self)' in src
    assert cc_public.load.python.source_of(text, ('nothing',)) is None
    assert cc_public.load.python.source_of(text, ()) == text
