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
                        anchored to sch_descriptive, because
                        sch_descriptive composes into every entry
                        schema through sch_entry. A type register
                        entry takes the schema of an entry. It does
                        not take the schema of the items its type
                        describes, although the entry names that
                        second schema by an edge.
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


# -----------------------------------------------------------------------------
# What a judge is shown of an item that is not itself code but stands
# for some. A test case names the function that automates it, and an
# eval asking whether the test catches anything must see the code.
#
# Read against the repository itself: a test tree holds no test/, so
# the functions these cases name are not in one.

ID_EVAL = 'evl_test_exercises_criteria'


def _shown():
    import conftest

    import cc_public.eval.select

    context = cc_public.check.context([conftest.ROOT])[0]

    return {t.id_subject: t.text_input
            for t in cc_public.eval.select.select(context)
            if t.id_eval == ID_EVAL}


def test_an_item_with_source_of_its_own_shows_it():
    shown = _shown()
    (subject,) = [s for s in shown
                  if s[0] == 'pyf_test.test_layout.test_printer_preserves_and_is_fixpoint']
    assert 'def test_printer_preserves_and_is_fixpoint' in shown[subject]


def test_a_case_shows_the_source_of_what_implements_it():
    shown = _shown()
    (subject,) = [s for s in shown if s[0] == 'tc_path_reported']

    # The function the case names by r_is_implemented_by, not the case's
    # own prose about it.
    assert 'def test_a_shortest_path_is_reported_or_its_absence' in shown[subject]


def test_an_item_naming_nothing_that_implements_it_shows_no_source():
    import cc_public.eval.select

    document = {'id_self': 'tc_alone', 'title': 'Alone', 'relation': []}
    assert cc_public.eval.select._with_source(document, None, {}) is document


def test_an_item_naming_something_the_map_lacks_shows_no_source():
    import cc_public.eval.select

    document = {'id_self':  'tc_dangling',
                'relation': [{'id_relation': 'r_is_implemented_by',
                              'guid_target': 'pyf_' + '0' * 32}]}
    assert cc_public.eval.select._with_source(document, None, {}) is document


# -----------------------------------------------------------------------------
# The surroundings of a definition. A name in a test refers to imports
# and module level values that are not in the test, and a judge shown
# the definition alone guesses at them.

MODULE = '''"""
The module document, which the reader already has.

"""


import pathlib

ROOT  = pathlib.Path('.')
FILES = sorted(ROOT.glob('*.yaml'))


def helper():
    """
    Not the surroundings of anything.

    """

    return 1


def test_reads_files():
    """
    A test naming a module level value.

    """

    assert FILES
'''


def test_the_module_context_is_what_the_definition_refers_to():
    import cc_public.load.python

    context = cc_public.load.python.context_of(MODULE)
    assert 'import pathlib' in context
    assert "ROOT  = pathlib.Path('.')" in context
    assert 'FILES = sorted' in context


def test_the_module_context_leaves_out_definitions_and_the_document():
    import cc_public.load.python

    context = cc_public.load.python.context_of(MODULE)
    assert 'def helper' not in context
    assert 'def test_reads_files' not in context
    assert 'The module document' not in context


def test_a_module_of_definitions_alone_has_no_context():
    import cc_public.load.python

    assert cc_public.load.python.context_of('def only():\n    return 1\n') is None


def test_a_module_that_does_not_parse_has_no_context():
    import cc_public.load.python

    assert cc_public.load.python.context_of('def (\n') is None


def test_the_projection_carries_the_module_beside_the_source():
    shown = _shown()
    (subject,) = [s for s in shown
                  if s[0] == 'pyf_test.test_layout.test_printer_preserves_and_is_fixpoint']

    # The decorator names FILES and the definition does not define it.
    assert 'FILES' in shown[subject]
    assert 'FILES = sorted' in shown[subject]


def test_a_module_item_carries_no_context_of_its_own():
    import cc_public.eval.select

    # The whole file is already the source, so the surroundings are in it.
    import conftest
    import cc_public.edit.tree

    tree = cc_public.edit.tree.Tree([conftest.ROOT])
    held = tree.resolve('pym_cc_public.layout')
    out  = cc_public.eval.select._with_source({'id_self': held.id_self}, held.location)
    assert 'module' not in out


def test_a_requirement_is_not_shown_the_code_that_implements_it():
    # A requirement names what implements it by the same relation a
    # case names the function that automates it. Following it for both
    # handed a judge asked whether a test would fail the code under
    # test beside the test, which it can answer from instead.
    shown = _shown()
    (subject,) = [s for s in shown
                  if s[0] == 'pyf_test.test_run.'
                             'test_back_edge_is_exhausted_when_the_budget_is_spent']

    assert 'def test_back_edge_is_exhausted_when_the_budget_is_spent' in shown[subject]
    assert 'def run(' not in shown[subject]
    assert shown[subject].count('source:') == 1


def test_only_a_case_follows_what_implements_it():
    import cc_public.eval.select

    held = {'id_self': 'req_probe', 'title': 'Probe',
            'relation': [{'id_relation': 'r_is_implemented_by',
                          'guid_target': 'pym_' + '0' * 32}]}

    assert cc_public.eval.select._with_source(held, None, {}) is held
    assert not cc_public.eval.select._is_case(held)
    assert cc_public.eval.select._is_case({'id_self': 'tc_probe'})
