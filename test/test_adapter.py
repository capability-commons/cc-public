"""
---

id_self:                pym_test.test_adapter
guid_self:              pym_3f7c1a92d4be4e8090c5b7a61f2e8d47
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pytest adapter tests
brief:                  |
                        Tests that the adapter tells a pass, a
                        failure, a skip, an error and an absent node
                        apart, and that a run that did not complete
                        carries no conformance result.
description:            |
                        The normalisation is tested against reports
                        made here, so that every outcome is covered
                        without running five test sessions. One test
                        runs a real case end to end and writes
                        nothing.
relation:               []

...
"""


import shutil

import conftest

import cc_public.adapter
import cc_public.adapter.pytest_function as adapter
import cc_public.edit.tree


ID_CASE  = 'tc_path_reported'
ID_UNDER = 'pyf_cc_public.query.database.path'
NODE     = 'test/test_query.py::test_a_shortest_path_is_reported_or_its_absence'


class _Collector:
    """
    A collector holding reports written here rather than by pytest.

    """

    def __init__(self, list_report = (), list_collect = ()):
        self.list_report  = list(list_report)
        self.list_collect = list(list_collect)


def _seen(list_report = (), list_collect = ()):
    return adapter._observation(_Collector(list_report, list_collect), NODE, 0.5)


def test_a_call_that_passed_is_a_completed_pass():
    seen = _seen([('setup', 'passed', ''), ('call', 'passed', '')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'passed'


def test_a_call_that_failed_is_a_completed_failure():
    seen = _seen([('setup', 'passed', ''), ('call', 'failed', 'assert 1 == 2')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'failed'
    assert 'assert 1 == 2' in seen.observation


def test_a_skip_is_completed_and_not_applicable():
    seen = _seen([('setup', 'skipped', 'not today')])
    assert seen.execution_outcome  == 'completed'
    assert seen.conformance_result == 'not_applicable'


def test_an_error_in_setup_is_an_execution_error_and_no_result():
    seen = _seen([('setup', 'failed', 'the fixture could not be made')])
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None
    assert 'setup' in seen.observation


def test_a_node_that_could_not_be_collected_is_an_execution_error_and_no_result():
    seen = _seen(list_collect = ['SyntaxError'])
    assert seen.execution_outcome  == 'error'
    assert seen.conformance_result is None


def test_a_node_nothing_ran_for_is_not_run_and_no_result():
    seen = _seen()
    assert seen.execution_outcome  == 'not_run'
    assert seen.conformance_result is None


def test_a_run_produces_a_conforming_execution_and_writes_nothing(tmp_path):
    # Read against the repository itself: the fixture tree holds no test/,
    # so the test function a case names is not in it.
    tree              = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, ID_CASE, ID_UNDER)
    assert problem == []
    assert document['execution_outcome'] == 'completed'
    assert document['result']['main']['conformance_result'] == 'passed'
    assert document['id_method']     == 'tm_pytest_function'
    assert document['digest_method'] and document['digest_case']
    assert document['adapter_version'].startswith('pytest ')
    assert not list(tmp_path.iterdir())


def test_a_case_that_does_not_resolve_yields_no_execution():
    tree = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, 'tc_absent', ID_UNDER)
    assert document is None
    assert 'tc_absent' in problem[0]


def test_an_item_the_tree_lacks_yields_no_execution():
    tree = cc_public.edit.tree.Tree(['.'])
    (document, problem) = cc_public.adapter.execute(tree, ID_CASE, 'pyf_absent.absent')
    assert document is None
    assert 'nothing to observe' in problem[0]


def test_recording_an_execution_writes_it_and_the_tree_still_checks(tree, tmp_path):
    import cc_public.check
    import test_test_execution

    document = dict(test_test_execution.EXECUTION)
    document['id_method']       = 'tm_pytest_function'
    document['guid_method']     = tree.resolve('tm_pytest_function').guid_self
    document['id_case']         = ID_CASE
    document['guid_case']       = tree.resolve(ID_CASE).guid_self
    document['id_under_test']   = ID_UNDER
    document['guid_under_test'] = tree.resolve(ID_UNDER).guid_self
    document['relation']        = [
        {'id_relation':   'r_uses_test_method',
         'guid_relation': tree.resolve('r_uses_test_method').guid_self,
         'id_target':     'tm_pytest_function',
         'guid_target':   tree.resolve('tm_pytest_function').guid_self},
        {'id_relation':   'r_tests',
         'guid_relation': tree.resolve('r_tests').guid_self,
         'id_target':     ID_UNDER,
         'guid_target':   tree.resolve(ID_UNDER).guid_self}]

    id_self = cc_public.adapter.record(tree, document)

    assert (tmp_path / 'execution' / (id_self + '.yaml')).is_file()

    critical = [(c['id_check'], n['message'])
                for c in cc_public.check.check(list_path = [tmp_path])['report']['check']
                for n in c['nonconformity'] if n['severity'] == 'critical']
    assert critical == []


def test_the_run_reads_the_code_of_the_tree_it_was_given(tmp_path):
    # A whole copy, the tests included, since the case names one of them.
    conftest.copy_tree(tmp_path)
    shutil.copytree(conftest.ROOT / 'test', tmp_path / 'test')

    # Break the candidate in the copy. A run that read the installed package
    # instead would pass, and the execution would name an item under test it
    # never observed.
    filepath = tmp_path / 'src' / 'cc_public' / 'query.py'
    text     = filepath.read_text()
    head     = text.index('    def path(self, name_from, name_to):')
    close    = text.index('"""', text.index('"""', head) + 3) + 3
    body     = text.index('\n', close) + 1
    filepath.write_text(text[:body] + '        return None\n' + text[body:])

    tree = cc_public.edit.tree.Tree([tmp_path])
    (document, problem) = cc_public.adapter.execute(tree, ID_CASE, ID_UNDER)

    assert problem == []
    assert document['execution_outcome'] == 'completed'
    assert document['result']['main']['conformance_result'] == 'failed'


def _run(tmp_path, *option):
    import click.testing
    import cc_public.cli.group
    import cc_public.cli.running                              # noqa: F401 -- registers
    return click.testing.CliRunner().invoke(
                cc_public.cli.group.main,
                ['test', ID_CASE, '--under-test', ID_UNDER, '--root', str(tmp_path),
                 *option])


def _whole(tmp_path):
    import shutil
    import conftest
    conftest.copy_tree(tmp_path)
    shutil.copytree(conftest.ROOT / 'test', tmp_path / 'test')


def test_a_run_writes_nothing_unless_it_is_asked_to(tmp_path):
    _whole(tmp_path)
    done = _run(tmp_path)
    assert done.exit_code == 0
    assert 'Nothing was written.' in done.output
    assert not (tmp_path / 'nonconformity').exists()


def test_evidence_brings_the_current_evidence_up_to_what_was_observed(tmp_path):
    import ruamel.yaml
    _whole(tmp_path)
    done = _run(tmp_path, '--evidence')
    assert done.exit_code == 0
    assert 'evd_pytest' in done.output

    loaded = ruamel.yaml.YAML(typ = 'safe').load(
                    (tmp_path / 'evidence' / 'evd_pytest.yaml').read_text())
    (row,) = [one for one in loaded['case'].values() if one.get('id_case') == ID_CASE]
    assert row['outcome']       == 'passed'
    assert row['id_method']     == 'tm_pytest_function'
    assert row['id_under_test'] == ID_UNDER
    # --evidence keeps no execution, so the row names none: it could not be
    # followed to one the tree does not hold.
    assert 'id_execution' not in row
    assert list((tmp_path / 'execution').glob('tex_*.yaml')) == []


def test_keeping_a_report_keeps_the_execution_it_names(tmp_path):
    _whole(tmp_path)

    # Break the candidate, so the run has a failure to report.
    filepath = tmp_path / 'src' / 'cc_public' / 'query.py'
    text     = filepath.read_text()
    head     = text.index('    def path(self, name_from, name_to):')
    close    = text.index('"""', text.index('"""', head) + 3) + 3
    body     = text.index('\n', close) + 1
    filepath.write_text(text[:body] + '        return None\n' + text[body:])

    done = _run(tmp_path, '--report')
    assert done.exit_code == 0

    (report,)    = list((tmp_path / 'nonconformity').iterdir())
    list_kept    = list((tmp_path / 'execution').glob('tex_*.yaml'))
    assert report.name.startswith('ncr_')
    assert len(list_kept) == 1

    # A report names the execution that produced it, and that execution is
    # in the tree, so nothing dangles.
    critical = [n['message']
                for c in cc_public.check.check(list_path = [tmp_path])['report']['check']
                for n in c['nonconformity'] if n['severity'] == 'critical']
    assert critical == []
