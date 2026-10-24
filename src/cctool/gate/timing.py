"""
---

id_self:                pym_cctool.gate.timing
guid_self:              pym_709d220fd3ae4561829157cc38bd9840
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate timings
brief:                  |
                        Record how long each stage of the gate takes,
                        and sum up the record.
description:            |
                        Each run of the gate appends a line for each
                        stage to a log in the git directory, which
                        every worktree shares and no commit records. A
                        line is a JSON object: the run it belongs to,
                        the stage, when the run started, the wall
                        seconds of the stage, its outcome, the
                        processor seconds of the whole run, the digest
                        of the tree gated, the commit if one was
                        gated, the host and the version of python. The
                        line of the tests holds the seconds of each
                        test, setup and teardown included, which
                        pytest reports in JUnit XML. The summary takes
                        the newest runs, and gives the mean and the
                        most wall seconds of each stage, and the
                        slowest tests.
edge:                   []

...
"""


import collections
import json
import pathlib
import xml.etree.ElementTree


# The log of timings, a file in the git directory that each worktree
# shares, as the store of the checker is. It is never committed.
#
FILE_LOG   = 'cctool_timing.jsonl'

# How many of the newest runs a summary covers, and how many of the
# slowest tests it names.
#
COUNT_RUN  = 10
COUNT_TEST = 10


# -----------------------------------------------------------------------------
def append(path_log: pathlib.Path, list_line: list[dict]) -> None:
    """
    Append each line of list_line to the log at path_log, as one JSON
    object to a line.

    """

    with path_log.open('a', encoding = 'utf-8') as file:
        for line in list_line:
            file.write(json.dumps(line) + '\n')


# -----------------------------------------------------------------------------
def read(path_log: pathlib.Path) -> list[dict]:
    """
    Return the lines of the log at path_log, oldest first, or none if
    there is no log. A line that is not whole, as a run stopped while
    it wrote would leave, is left out.

    """

    if not path_log.is_file():
        return []

    list_line = []
    for text in path_log.read_text(encoding = 'utf-8').splitlines():
        try:
            list_line.append(json.loads(text))
        except json.JSONDecodeError:
            continue

    return list_line


# -----------------------------------------------------------------------------
def durations(path_junit: pathlib.Path) -> dict[str, float]:
    """
    Return the seconds that each test took, setup and teardown
    included, from the JUnit XML report that pytest wrote at
    path_junit, by the class name and name that the report gives the
    test. There are none if the report is missing or not whole, as when
    the tests are stopped.

    """

    # The report is trusted: pytest wrote it, in a directory of the gate's
    # own.
    #
    try:
        element = xml.etree.ElementTree.parse(path_junit).getroot()  # noqa: S314
    except (OSError, xml.etree.ElementTree.ParseError):
        return {}

    return {'{classname}::{name}'.format(classname = case.get('classname', ''),
                                         name      = case.get('name', '')):
            float(case.get('time', 0))
            for case in element.iter('testcase')}


# -----------------------------------------------------------------------------
def summary(list_line:  list[dict],
            count_run:  int = COUNT_RUN,
            count_test: int = COUNT_TEST) -> list[str]:
    """
    Return the lines of a summary of the newest count_run runs of
    list_line: how many there are and when they started, the mean and
    the maximum wall seconds of each stage, and the count_test slowest
    tests by the most seconds each took.

    """

    list_run  = list(dict.fromkeys(line['run'] for line in list_line))[-count_run:]
    set_run   = set(list_run)
    list_kept = [line for line in list_line if line['run'] in set_run]
    if not list_kept:
        return ['No timings are recorded.']

    map_stage = collections.defaultdict(list)
    map_test  = collections.defaultdict(list)
    for line in list_kept:
        map_stage[line['stage']].append(line['seconds'])
        for (name, seconds) in line.get('tests', {}).items():
            map_test[name].append(seconds)

    list_text = ['{count} {noun}, started from {first} to {last}.'.format(
                     count = len(list_run),
                     noun  = 'run' if len(list_run) == 1 else 'runs',
                     first = list_kept[0]['start'],
                     last  = list_kept[-1]['start']),
                 'stage\truns\tmean_s\tmax_s']
    for (stage, list_seconds) in map_stage.items():
        list_text.append('{stage}\t{count}\t{mean:.1f}\t{max:.1f}'.format(
                             stage = stage,
                             count = len(list_seconds),
                             mean  = sum(list_seconds) / len(list_seconds),
                             max   = max(list_seconds)))

    list_slow = sorted(map_test.items(), key = lambda item: -max(item[1]))[:count_test]
    if list_slow:
        list_text.append('test\tmax_s')
        list_text.extend('{name}\t{max:.2f}'.format(name = name, max = max(list_seconds))
                         for (name, list_seconds) in list_slow)

    return list_text
