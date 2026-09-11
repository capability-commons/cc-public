"""
---

id_self:                pym_test.test_selection
guid_self:              pym_4682c8b0a45a4d87b9f4e8cc55a67dd9
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test selection tests
brief:                  |
                        Tests that selection errs towards running
                        everything, and says why whenever it does.
description:            |
                        Each test here names a change whose reach the
                        map cannot say, and asserts that the whole
                        suite is asked for and a reason given.
relation:               []

...
"""


import json

import pytest

import selection


BY_SOURCE = {'src/cc_public/layout.py': ['test/test_layout.py::test_one',
                                         'test/test_layout.py::test_two'],
             'src/cc_public/query.py':  ['test/test_query.py::test_three']}
NODE = ('test/test_layout.py::test_one', 'test/test_layout.py::test_two',
        'test/test_query.py::test_three')
MAP  = selection.Map(BY_SOURCE, NODE, ())


def test_a_source_change_runs_what_the_map_says_reaches_it():
    decided = selection.plan({'src/cc_public/query.py'}, MAP)
    assert not decided.is_whole
    assert decided.node == ('test/test_query.py::test_three',)
    assert '1 of 3' in decided.reason


def test_two_changes_run_the_union():
    decided = selection.plan({'src/cc_public/query.py', 'src/cc_public/layout.py'},
                             selection.Map(BY_SOURCE, NODE + tuple('n{n}'.format(n = i) for i in range(7)), ()))
    assert not decided.is_whole and len(decided.node) == 3


def test_no_map_runs_everything():
    decided = selection.plan({'src/cc_public/query.py'}, selection.NO_MAP)
    assert decided.is_whole and 'no map' in decided.reason


def test_a_change_to_the_shared_fixtures_runs_everything():
    decided = selection.plan({'test/conftest.py'}, MAP)
    assert decided.is_whole and 'conftest' in decided.reason


def test_a_data_item_runs_everything_since_no_line_names_it():
    # The reason this is not merely conservative: a test reads a data
    # item without executing any line that mentions it, so a map of
    # executed lines cannot see the dependence at all.
    decided = selection.plan({'register/reg_relation.yaml'}, MAP)
    assert decided.is_whole and 'reg_relation.yaml' in decided.reason


def test_the_project_file_runs_everything():
    decided = selection.plan({'pyproject.toml'}, MAP)
    assert decided.is_whole


def test_a_module_the_map_never_saw_runs_everything():
    decided = selection.plan({'src/cc_public/brand_new.py'}, MAP)
    assert decided.is_whole and 'does not hold it' in decided.reason


def test_a_changed_test_module_runs_that_whole_module():
    # By path and not by node id, since the map cannot hold a test that
    # did not exist when it was measured.
    decided = selection.plan({'test/test_query.py'}, MAP)
    assert not decided.is_whole and decided.node == ('test/test_query.py',)


def test_selecting_most_of_the_suite_runs_all_of_it():
    decided = selection.plan({'src/cc_public/layout.py'}, MAP)
    assert decided.is_whole and 'enough of the suite' in decided.reason


def test_nothing_changed_runs_nothing_and_says_so():
    decided = selection.plan(set(), MAP)
    assert not decided.is_whole and decided.node == ()
    assert 'Nothing has changed' in decided.reason


def test_a_map_measured_by_a_core_that_cannot_attribute_is_refused(tmp_path):
    # The failure this guards against is silent: the default core on
    # this python stops reporting a line once it has been seen, so only
    # the first test to reach it is recorded and every later one looks
    # untouched. Such a map would select a handful of tests and pass.
    path = tmp_path / 'map.json'
    path.write_text(json.dumps({'core': 'sysmon', 'test': ['a'],
                                'by_source': BY_SOURCE}), encoding = 'utf-8')
    assert selection.load(path, root = tmp_path) == selection.NO_MAP

    path.write_text(json.dumps({'core': 'ctrace', 'test': ['a'],
                                'by_source': BY_SOURCE}), encoding = 'utf-8')
    held = selection.load(path, root = tmp_path)
    assert held.by_source == BY_SOURCE and held.count == 1


def test_an_absent_map_is_no_map_rather_than_an_error(tmp_path):
    assert selection.load(tmp_path / 'nothing.json', root = tmp_path) \
           == selection.NO_MAP


def test_what_counts_as_a_module_and_a_test():
    assert selection.is_source('src/cc_public/layout.py')
    assert not selection.is_source('src/cc_public/layout.yaml')
    assert not selection.is_source('test/test_layout.py')
    assert selection.is_test('test/test_layout.py')
    assert not selection.is_test('src/cc_public/layout.py')


def test_a_module_the_measurement_could_not_account_for_always_runs():
    # Its data did not read, or its tests did not pass under
    # measurement. Nothing is known about what its tests reach, so
    # leaving it out would be the silent under-run this exists to
    # avoid.
    held    = selection.Map(BY_SOURCE, NODE + tuple('n{n}'.format(n = i) for i in range(17)),
                            ('test/test_edit.py',))
    decided = selection.plan({'src/cc_public/query.py'}, held)
    assert not decided.is_whole
    assert set(decided.node) == {'test/test_query.py::test_three', 'test/test_edit.py'}
    assert 'does not account for' in decided.reason


MODULE  = 'test_glossary.py'
REACHED = 'src/cc_public/glossary.py'


def _measured(tmp_path, core):
    """
    Measure one small test module and return the map it yields.

    """

    import coverage

    dirpath = tmp_path / 'data'
    dirpath.mkdir(parents = True)
    assert selection._measure_one(selection.ROOT, dirpath, MODULE, core) == 0

    held = coverage.CoverageData(str(dirpath / 'combined'))
    selection._combine_into(held, sorted(dirpath.glob('data.*')))

    return selection._map_of(held, selection.ROOT, core, set())


@pytest.mark.slow
def test_a_measured_map_selects_the_tests_that_reached_what_changed(tmp_path):
    # The whole chain, once, over one small module: the core records a
    # context per test, the map attributes them, and the plan selects.
    # Everything else here tests the plan against a map written by
    # hand, which cannot show that the measurement produces one.
    written = _measured(tmp_path, selection.CORE_ATTRIBUTING[0])
    assert REACHED in written[selection.KEY_SOURCE]

    # What is reached, and not the plan over it: measuring one module
    # gives a map of eight tests, all of which reach the module that
    # changed, so the plan rightly says the whole suite. The threshold
    # that decides that is tested above against a map written by hand.
    held    = selection.Map(written[selection.KEY_SOURCE],
                            len(written[selection.KEY_TEST]), ())
    reached = selection._reached({REACHED}, held)
    assert all(node.startswith('test/' + MODULE) for node in reached), reached
    assert len(reached) > 1


@pytest.mark.slow
def test_the_default_core_attributes_almost_nothing_and_is_why_one_is_named(tmp_path):
    # The blind spot this guards. The default core on this python asks
    # the interpreter to stop reporting a line once it has been seen,
    # so only the first test to reach a line is recorded against it.
    # The map is not coarser, it is wrong, and a run selected from it
    # would pass having run a handful of tests.
    attributing = _measured(tmp_path / 'a', selection.CORE_ATTRIBUTING[0])
    default     = _measured(tmp_path / 'b', 'sysmon')

    assert len(default[selection.KEY_TEST]) < len(attributing[selection.KEY_TEST])
    assert REACHED in attributing[selection.KEY_SOURCE]


def test_a_test_module_the_map_never_saw_always_runs(tmp_path):
    # Every rule reads the map, so a module committed after the map was
    # measured was invisible to all of them: a change to something it
    # exercises selected the modules the map held, ran green, and never
    # ran it.
    (tmp_path / 'test').mkdir()
    for name in ('test_seen.py', 'test_new.py', 'helper.py'):
        (tmp_path / 'test' / name).write_text('', encoding = 'utf-8')

    node = tuple('test/test_seen.py::test_{n}'.format(n = i) for i in range(20))
    held = selection.Map(BY_SOURCE, node, ())
    held = held._replace(unseen = selection.unseen(tmp_path, held))
    assert held.unseen == ('test/test_new.py',)

    decided = selection.plan({'src/cc_public/query.py'}, held)
    assert 'test/test_new.py' in decided.node


def test_a_helper_under_test_runs_everything():
    # is_test accepted any python file under test/, so a change to a
    # helper named that file as the node and never ran the module that
    # tests it.
    decided = selection.plan({'test/selection.py'}, MAP)
    assert decided.is_whole and 'helper under test/' in decided.reason

    assert selection.is_helper('test/selection.py')
    assert not selection.is_helper('test/test_selection.py')
    assert not selection.is_test('test/selection.py')
    assert selection.is_test('test/test_selection.py')


def test_the_comparison_runs_from_the_commit_the_map_was_measured_at(tmp_path):
    # Comparing to the last commit alone said nothing had changed the
    # moment a change was committed, and a commit runs the checks and
    # no tests.
    import subprocess

    def git(*argument):
        subprocess.run(['git', '-C', str(tmp_path), *argument], check = True,
                       capture_output = True)

    git('init', '-q')
    git('config', 'user.email', 'probe@example.com')
    git('config', 'user.name', 'Probe')
    (tmp_path / 'src').mkdir(parents = True)
    (tmp_path / 'src' / 'cc_public').mkdir()
    (tmp_path / 'src' / 'cc_public' / 'query.py').write_text('x = 1\n', encoding = 'utf-8')
    git('add', '-A')
    git('-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'first')
    first = subprocess.run(['git', '-C', str(tmp_path), 'rev-parse', 'HEAD'],
                           capture_output = True, text = True, check = True).stdout.strip()

    (tmp_path / 'src' / 'cc_public' / 'query.py').write_text('x = 2\n', encoding = 'utf-8')
    git('add', '-A')
    git('-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'second')

    # Committed, so nothing differs from HEAD; the map still describes
    # the tree as it was at the first commit.
    assert selection.changed(tmp_path, first) == {'src/cc_public/query.py'}
    assert selection.changed(tmp_path, 'HEAD') == set()
