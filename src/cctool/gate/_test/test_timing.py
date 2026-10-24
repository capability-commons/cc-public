"""
---

id_self:                pym_cctool.gate._test.test_timing
guid_self:              pym_5512ee1ae4844a07afa1df90e45a896b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate timing tests
brief:                  |
                        Tests of the log of timings of the gate, and
                        of its summary.
description:            |
                        Each test writes lines of the log, or a JUnit
                        XML report, of its own, and reads them back,
                        or sums them up.
edge:                   []

...
"""


import json

import cctool.gate.timing


# -----------------------------------------------------------------------------
def _line(run, stage, seconds, tests = None):
    """
    Return a line of the log of timings for stage of run.

    """

    line = {'run': run, 'stage': stage, 'start': 'start_' + run, 'seconds': seconds}
    if tests is not None:
        line['tests'] = tests
    return line


def test_lines_appended_are_read_back_in_order(tmp_path):
    path_log = tmp_path / 'log.jsonl'
    cctool.gate.timing.append(path_log, [_line('a', 'check', 1.0)])
    cctool.gate.timing.append(path_log, [_line('b', 'check', 2.0)])
    assert cctool.gate.timing.read(path_log) == [_line('a', 'check', 1.0),
                                                 _line('b', 'check', 2.0)]


def test_a_missing_log_reads_as_empty(tmp_path):
    assert cctool.gate.timing.read(tmp_path / 'log.jsonl') == []


def test_a_line_that_is_not_whole_is_left_out(tmp_path):
    path_log = tmp_path / 'log.jsonl'
    path_log.write_text(json.dumps(_line('a', 'check', 1.0)) + '\n{"run": "b", "sta')
    assert cctool.gate.timing.read(path_log) == [_line('a', 'check', 1.0)]


def test_the_durations_are_read_from_a_junit_report(tmp_path):
    path_junit = tmp_path / 'junit.xml'
    path_junit.write_text('<testsuites><testsuite>'
                          '<testcase classname="src.a.test_a" name="test_one" time="0.25"/>'
                          '<testcase classname="src.a.test_a" name="test_two[x]" time="1.5"/>'
                          '</testsuite></testsuites>')
    assert cctool.gate.timing.durations(path_junit) == {'src.a.test_a::test_one':    0.25,
                                                        'src.a.test_a::test_two[x]': 1.5}


def test_a_report_that_is_missing_or_not_whole_gives_no_durations(tmp_path):
    path_junit = tmp_path / 'junit.xml'
    assert cctool.gate.timing.durations(path_junit) == {}
    path_junit.write_text('<testsuites><testsuite><testcase')
    assert cctool.gate.timing.durations(path_junit) == {}


def test_the_summary_gives_the_mean_and_most_of_each_stage_over_the_newest_runs():
    list_line = [_line('a', 'check', 9.0),
                 _line('b', 'check', 1.0), _line('b', 'test', 4.0, {'t1': 3.0, 't2': 0.5}),
                 _line('c', 'check', 3.0), _line('c', 'test', 6.0, {'t1': 1.0, 't2': 5.0})]
    assert cctool.gate.timing.summary(list_line, count_run = 2) == [
        '2 runs, started from start_b to start_c.',
        'stage\truns\tmean_s\tmax_s',
        'check\t2\t2.0\t3.0',
        'test\t2\t5.0\t6.0',
        'test\tmax_s',
        't2\t5.00',
        't1\t3.00']


def test_the_summary_names_only_as_many_tests_as_asked():
    list_line = [_line('a', 'test', 4.0, {'t1': 3.0, 't2': 0.5})]
    assert cctool.gate.timing.summary(list_line, count_test = 1)[-2:] == ['test\tmax_s', 't1\t3.00']
    assert cctool.gate.timing.summary(list_line, count_test = 0)[-1] == 'test\t1\t4.0\t4.0'


def test_the_summary_of_an_empty_log_says_so():
    assert cctool.gate.timing.summary([]) == ['No timings are recorded.']
