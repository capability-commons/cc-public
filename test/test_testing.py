"""
---

id_self:                pym_test.test_testing
guid_self:              pym_5b1e9a0c47d8401f9d2c6e3a7f10b2c4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test model tests
brief:                  |
                        Tests that a case resolves into a runnable
                        specification, that an unresolvable binding is
                        reported, and that a pytest node id is derived
                        from identity alone.
description:            |
                        The specification carries the method, the
                        adapter, the configuration and the digests a
                        result is bound to. A case naming no method,
                        two methods, a method the tree lacks, or a
                        configuration its method's schema refuses is
                        reported where the case is written.
relation:               []

...
"""


import pathlib

import cc_public.adapter.pytest_function
import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.testing


ID_CASE = 'tc_path_reported'
ID_TEST = 'pyf_test.test_query.test_a_shortest_path_is_reported_or_its_absence'


def _map(tree):
    return tree.context.map_document


def _map_real():
    # The fixture tree holds every directory but test/, so an item of a test
    # function is not in it. The adapter is asked about the repository itself.
    (context, _) = cc_public.check.context([pathlib.Path(__file__).parent.parent],
                                           False, None)
    return context.map_document


def _findings(tmp_path):
    report   = cc_public.check.check(list_path = [pathlib.Path(tmp_path)])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'testing']
    return [n['message'] for n in found['nonconformity']]


def test_a_case_resolves_into_a_specification(tree):
    (specification, problem) = cc_public.testing.resolve(_map(tree), ID_CASE)
    assert problem == []
    assert specification.id_method  == 'tm_pytest_function'
    assert specification.id_adapter == 'pym_cc_public.adapter.pytest_function'
    assert specification.configuration['id_test'] == ID_TEST
    assert 'req_path_reported' in specification.list_verified


def test_the_specification_carries_a_digest_of_the_method_and_the_case(tree):
    (before, _) = cc_public.testing.resolve(_map(tree), ID_CASE)
    cc_public.edit.field.set_field(tree, 'tm_pytest_function', 'verdict_rule',
                                   prose = 'Passed where it passed.')
    (after, _) = cc_public.testing.resolve(_map(tree), ID_CASE)
    assert after.digest_method != before.digest_method
    assert after.digest_case   == before.digest_case


def test_a_case_naming_no_method_does_not_resolve(tree, tmp_path):
    cc_public.edit.link.unlink(tree, ID_CASE, 'r_uses_test_method', 'tm_pytest_function')
    (specification, problem) = cc_public.testing.resolve(_map(tree), ID_CASE)
    assert specification is None
    assert 'names 0 test method' in problem[0]


def test_a_case_that_does_not_resolve_is_reported_where_it_is_written(tree, tmp_path):
    cc_public.edit.link.unlink(tree, ID_CASE, 'r_uses_test_method', 'tm_pytest_function')
    messages = _findings(tmp_path)
    assert any('names 0 test method' in message for message in messages)


def test_a_configuration_the_method_refuses_is_reported(tree, tmp_path):
    cc_public.edit.field.set_field(tree, ID_CASE, 'configuration',
                                   value = {'node': 'test/test_query.py::test_path'})
    messages = _findings(tmp_path)
    assert any('sch_case_pytest_function' in message for message in messages)


def test_a_node_id_is_the_file_and_the_definitions_as_the_source_spells_them():
    root = pathlib.Path(__file__).parent.parent
    (node, problem) = cc_public.adapter.pytest_function.specify(
                                    _map_real(), {'id_test': ID_TEST}, root)
    assert problem == []
    assert node == ('test/test_query.py'
                    '::test_a_shortest_path_is_reported_or_its_absence')


def test_a_node_id_carries_the_case_the_source_spells_a_class_with():
    # The readable id is lower case; the loader kept the real names.
    root = pathlib.Path(__file__).parent.parent
    (node, problem) = cc_public.adapter.pytest_function.specify(
                            _map_real(), {'id_test': 'pyf_cc_public.query.database.path'},
                            root)
    assert problem == []
    assert node.endswith('query.py::Database::path')


def test_a_configuration_naming_no_test_yields_no_node_id():
    (node, problem) = cc_public.adapter.pytest_function.specify(_map_real(), {})
    assert node is None
    assert 'names no test function' in problem[0]


def test_a_configuration_naming_something_the_tree_lacks_yields_no_node_id():
    (node, problem) = cc_public.adapter.pytest_function.specify(
                                    _map_real(), {'id_test': 'pyf_test.absent.absent'})
    assert node is None
    assert 'does not hold' in problem[0]


def test_a_configuration_naming_something_that_is_not_a_function_is_refused(tree):
    (node, problem) = cc_public.adapter.pytest_function.specify(
                                    _map(tree), {'id_test': 'pym_test.test_query'})
    assert node is None
    assert 'is not a python function' in problem[0]
