"""
---

id_self:                pym_cc_public.adapter.pytest_function
guid_self:              pym_c62e5f399bae4c6fb04593696c3d2c04
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pytest function adapter
brief:                  |
                        The adapter that carries out a test method by
                        running one pytest test function.
description:            |
                        A case names the source item of the test
                        function it runs. The node id is the file that
                        item sits in and the definitions down to it,
                        as the loader read them from the source, so
                        the names carry the case the source spells
                        them with and the readable id does not.

                        The run is made in a process of its own, with
                        the source of the tree being read first on the
                        path, so what runs is the code that tree
                        holds. Reading one tree and running another
                        tree's code would let an execution name an
                        item under test it never observed. The reports
                        come back as one line of json, so the outcome
                        is read from what pytest reported and not from
                        what it printed.

                        Neither the method nor the case carries a
                        command or a path, so a case names something
                        this tree resolves and asks for nothing but a
                        test to be run.
relation:               []

...
"""


import contextlib
import json
import os
import pathlib
import subprocess
import sys
import time
import typing

import cc_public.evidence
import cc_public.testing


KEY_ID_TEST   = 'id_test'
KEY_ID_SELF   = 'id_self'

PREFIX_TEST   = 'pyf'
SEPARATOR     = '_'
DELIM         = '.'
DELIM_NODE    = '::'

# What pytest is run with: quiet, no header, and no cache written beside
# the tree it reads.
#
ARGUMENT      = ('-q', '--no-header', '-p', 'no:cacheprovider')

# Set while pytest runs, so that a conftest of the tree being read knows
# it is an adapter running one node and not a session establishing
# evidence. What an execution does to the current evidence is decided by
# ddr_evidence_dependency_closure, not by a side effect here.
#
VARIABLE      = 'CCTOOL_ADAPTER'
DIRECTORY_SOURCE = 'src'
MARKER        = '--- cctool adapter '

# The program the run is made by. It runs in a process of its own, with
# the source of the tree being read first on the path, so that what runs
# is the code that tree holds and not the code this process imported.
# The reports are handed back as one line of json, so the outcome is
# still read from what pytest reported and not from what it printed.
#
RUNNER        = """
import json, sys, pytest

class Collector:
    def __init__(self):
        self.report  = []
        self.collect = []
    def pytest_runtest_logreport(self, report):
        self.report.append([report.when, report.outcome, str(report.longrepr or '')])
    def pytest_collectreport(self, report):
        if report.failed:
            self.collect.append(str(report.longrepr or ''))

collector = Collector()
pytest.main(['-q', '--no-header', '-p', 'no:cacheprovider', sys.argv[1]],
            plugins = [collector])
print('--- cctool adapter ' + json.dumps({'report':  collector.report,
                                          'collect': collector.collect}))
"""


# -----------------------------------------------------------------------------
def specify(map_document, configuration, dirpath = None):
    """
    Return (node_id, [problem]) for the configuration of one case.

    The node id is the file the item sits in and the definitions down to
    it, as the loader read them from the source. The names carry the
    case the source spells them with, which the readable id does not.

    A case that named a path or a command could ask for anything to be
    run; one that names an identity can ask only for a test this tree
    holds.

    """

    id_test = configuration.get(KEY_ID_TEST)

    if not isinstance(id_test, str):
        return (None, ['The configuration names no test function under {key}.'.format(
                                                                key = KEY_ID_TEST)])

    if id_test.split(SEPARATOR, 1)[0] != PREFIX_TEST:
        return (None, ['{name} is not a python function, so it is not a test to '
                       'run.'.format(name = id_test)])

    location = cc_public.testing.locate(map_document, id_test)

    if location is None:
        return (None, ['The configuration names {name}, which this tree does not '
                       'hold.'.format(name = id_test)])

    if not location.anchor:
        return (None, ['{name} names a whole file and not a definition in it, so there '
                       'is no test to run.'.format(name = id_test)])

    filepath = location.filepath

    if dirpath is not None:
        with contextlib.suppress(ValueError):
            filepath = filepath.relative_to(dirpath)

    return (DELIM_NODE.join([str(filepath), *location.anchor]), [])



OUTCOME_COMPLETED = 'completed'
OUTCOME_ERROR     = 'error'
OUTCOME_NOT_RUN   = 'not_run'

RESULT_PASSED     = 'passed'
RESULT_FAILED     = 'failed'
RESULT_SKIPPED    = 'not_applicable'

WHEN_CALL         = 'call'

# What pytest-timeout writes into the report when it stops a test. A
# timeout arrives as an ordinary call failure, so without this the run
# that never finished would be read as the item under test failing.
#
MARK_TIMEOUT      = 'from pytest-timeout'


# -----------------------------------------------------------------------------
def _version():
    """
    Return the version of pytest, or absent where it is not installed.

    Imported here and not at the top of the module. The adapter runs
    pytest in a subprocess of its own and needs it in this process only
    to say what observed a result, but cli.running imports this module
    to reach the adapter allowlist, so a module level import would make
    cctool refuse to start without a test runner. It did: the installed
    wheel would not run --help.

    """

    try:
        import pytest
    except ImportError:
        return 'absent'

    return pytest.__version__


# -----------------------------------------------------------------------------
class Observation(typing.NamedTuple):
    """
    What one run of this adapter observed.

    conformance_result is None where the execution did not complete. A
    test that could not be collected, or whose setup failed, has
    observed nothing about the item under test, and saying otherwise
    would make a fault in the harness look like a fault in the product.

    """

    execution_outcome:  str
    conformance_result: str | None
    observation:        str
    node:               str | None
    version:            str
    second:             float


# -----------------------------------------------------------------------------
def run(map_document, configuration, dirpath = None):
    """
    Run the one test function a case names, and return what was
    observed.

    pytest is run with a plugin that keeps its reports, so the outcome
    is read from what pytest reported rather than from what it printed.

    """

    (node, list_problem) = specify(map_document, configuration, dirpath)

    if node is None:
        return Observation(execution_outcome  = OUTCOME_NOT_RUN,
                           conformance_result = None,
                           observation        = ' '.join(list_problem),
                           node               = None,
                           version            = _version(),
                           second             = 0.0)

    root    = pathlib.Path(dirpath or '.').resolve()
    started = time.monotonic()
    done    = subprocess.run([sys.executable, '-c', RUNNER, node],
                             cwd            = str(root),
                             env            = _environment(root),
                             capture_output = True,
                             text           = True,
                             check          = False)

    return _observation(_collected(done), node, time.monotonic() - started)


# -----------------------------------------------------------------------------
def _environment(root):
    """
    Return the environment the run is made in.

    The source of the tree being read comes first on the path, so what
    runs is the code that tree holds. Reading one tree and running
    another's code would let an execution name an item under test it
    never observed.

    """

    out            = dict(os.environ)
    out[VARIABLE]  = '1'
    out['PYTHONPATH'] = os.pathsep.join(
                            [str(root / DIRECTORY_SOURCE),
                             *([out['PYTHONPATH']] if out.get('PYTHONPATH') else [])])

    return out


# -----------------------------------------------------------------------------
def _collected(done):
    """
    Return the collector the run reported, or one holding why it could
    not be read.

    """

    collector = _Collector()

    for line in done.stdout.splitlines():
        if line.startswith(MARKER):
            reported = json.loads(line[len(MARKER):])
            collector.list_report  = [tuple(one) for one in reported['report']]
            collector.list_collect = reported['collect']
            return collector

    collector.list_collect = ['pytest reported nothing this adapter could read. '
                              + (done.stderr.strip() or done.stdout.strip())[:2000]]

    return collector


# -----------------------------------------------------------------------------
def _observation(collector, node, second):
    """
    Return what the collected reports say, as one Observation.

    An error in setup or teardown is an execution error and no
    conformance result. Only what the call phase reported is a result
    about the item under test.

    A timeout is not one of those results. pytest-timeout stops the
    test and reports an ordinary call failure, but a run that was
    stopped never reached an end, and what it says about the item under
    test is nothing. Reading it as a failure would name the item in a
    nonconformity report for something the run never observed.

    """

    def made(outcome, result, text):
        return Observation(execution_outcome  = outcome,
                           conformance_result = result,
                           observation        = text.strip() or 'Nothing was reported.',
                           node               = node,
                           version            = _version(),
                           second             = round(second, 3))

    if collector.list_collect:
        return made(OUTCOME_ERROR, None,
                    'pytest could not collect the node. ' + collector.list_collect[0])

    # Read through cc_public.evidence, so that the session hook writing
    # evidence and this adapter reading one node cannot disagree about
    # what an event means. They did: the hook had no branch for
    # teardown and read a timeout as a failure of the item.
    #
    # Every instance and not the first. A parametrised function is one
    # item however many times it runs, so the worst of what its
    # instances said is what it said.
    #
    said = [(cc_public.evidence.outcome_of_event(when, outcome, text), text)
            for (when, outcome, text) in collector.list_report]
    held = [(outcome, text) for (outcome, text) in said if outcome is not None]

    if not held:
        return made(OUTCOME_NOT_RUN, None, 'pytest ran no test for the node.')

    worst = min((outcome for (outcome, _) in held),
                key = cc_public.evidence.RANK.index)
    text  = next(text for (outcome, text) in held if outcome == worst)

    if worst == cc_public.evidence.OUTCOME_ERROR:
        return made(OUTCOME_ERROR, None, _why_error(collector, text))

    if worst == cc_public.evidence.OUTCOME_FAILED:
        return made(OUTCOME_COMPLETED, RESULT_FAILED, text)

    if worst == cc_public.evidence.OUTCOME_SKIPPED:
        return made(OUTCOME_COMPLETED, RESULT_SKIPPED,
                    'pytest reported the node skipped. ' + text)

    return made(OUTCOME_COMPLETED, RESULT_PASSED,
                'pytest reported {n} instance(s) of the node, and every one '
                'passed.'.format(n = sum(1 for (when, _, _) in collector.list_report
                                           if when == WHEN_CALL)))


# -----------------------------------------------------------------------------
def _why_error(collector, text):
    """
    Return what to say of a run that did not complete.

    """

    if MARK_TIMEOUT in text:
        return ('pytest stopped the node at its timeout, so the run did not finish. '
                + text)

    when = next((when for (when, outcome, one) in collector.list_report
                       if outcome == 'failed' and one == text), WHEN_CALL)

    return 'pytest reported an error in {when}. {text}'.format(when = when, text = text)


# -----------------------------------------------------------------------------
class _Collector:
    """
    A pytest plugin that keeps what pytest reports.

    """

    def __init__(self):
        self.list_report  = []
        self.list_collect = []

    def pytest_runtest_logreport(self, report):
        self.list_report.append((report.when, report.outcome, str(report.longrepr or '')))

    def pytest_collectreport(self, report):
        if report.failed:
            self.list_collect.append(str(report.longrepr or ''))
