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
                        function it runs, and the adapter derives the
                        pytest node id from that item: the file the
                        item sits in, then the definitions beneath it.
                        Neither the method nor the case carries a
                        command or a path, so a case names something
                        this tree resolves and asks for nothing but a
                        test to be run.
relation:               []

...
"""


import contextlib
import os
import pathlib
import time
import typing

import pytest

import cc_public.testing


KEY_ID_TEST   = 'id_test'
KEY_ID_SELF   = 'id_self'

PREFIX_MODULE = 'pym'
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


# -----------------------------------------------------------------------------
def specify(map_document, configuration):
    """
    Return (node_id, [problem]) for the configuration of one case.

    The node id is derived from the identity the case names and from
    nothing else: the file the test function's module sits in, then the
    definitions beneath it. A case that named a path or a command could
    ask for anything to be run; one that names an identity can ask only
    for a test this tree holds.

    """

    id_test = configuration.get(KEY_ID_TEST)

    if not isinstance(id_test, str):
        return (None, ['The configuration names no test function under {key}.'.format(
                                                                key = KEY_ID_TEST)])

    if id_test.split(SEPARATOR, 1)[0] != PREFIX_TEST:
        return (None, ['{name} is not a python function, so it is not a test to '
                       'run.'.format(name = id_test)])

    map_item = cc_public.testing.index(map_document)

    if id_test not in map_item:
        return (None, ['The configuration names {name}, which this tree does not '
                       'hold.'.format(name = id_test)])

    (id_module, list_definition) = _split(id_test, map_item)

    if id_module is None:
        return (None, ['No python module item holds {name}, so the file to run it in is '
                       'not known.'.format(name = id_test)])

    filepath = id_module.split(SEPARATOR, 1)[1].replace(DELIM, '/') + '.py'

    return (DELIM_NODE.join([filepath, *list_definition]), [])


# -----------------------------------------------------------------------------
def _split(id_test, map_item):
    """
    Return (id of the module holding the test, the definition names
    beneath it), by taking the longest module id the test id begins
    with.

    A function id is its module's id and then the definitions, so the
    module is found by looking rather than by guessing how many parts
    it has.

    """

    stem   = id_test.split(SEPARATOR, 1)[1]
    prefix = PREFIX_MODULE + SEPARATOR
    best   = None

    for name in map_item:
        if not name.startswith(prefix):
            continue
        candidate = name.split(SEPARATOR, 1)[1]
        if (stem + DELIM).startswith(candidate + DELIM) \
                and (best is None or len(candidate) > len(best)):
            best = candidate

    if best is None:
        return (None, [])

    return (prefix + best, stem[len(best) + 1:].split(DELIM))


OUTCOME_COMPLETED = 'completed'
OUTCOME_ERROR     = 'error'
OUTCOME_NOT_RUN   = 'not_run'

RESULT_PASSED     = 'passed'
RESULT_FAILED     = 'failed'
RESULT_SKIPPED    = 'not_applicable'

WHEN_CALL         = 'call'


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

    The node id is derived from the identity the case names, so nothing
    a case carries reaches a shell. pytest is run with a plugin that
    keeps its reports, so the outcome is read from what pytest reported
    rather than from what it printed.

    """

    (node, list_problem) = specify(map_document, configuration)

    if node is None:
        return Observation(execution_outcome  = OUTCOME_NOT_RUN,
                           conformance_result = None,
                           observation        = ' '.join(list_problem),
                           node               = None,
                           version            = pytest.__version__,
                           second             = 0.0)

    collector = _Collector()
    started   = time.monotonic()

    with _announced():
        pytest.main([*ARGUMENT, str(pathlib.Path(dirpath or '.') / node)],
                    plugins = [collector])

    return _observation(collector, node, time.monotonic() - started)


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def _announced():
    """
    Set the variable that says an adapter is running, and put it back.

    """

    before = os.environ.get(VARIABLE)
    os.environ[VARIABLE] = '1'

    try:
        yield
    finally:
        if before is None:
            del os.environ[VARIABLE]
        else:
            os.environ[VARIABLE] = before


# -----------------------------------------------------------------------------
def _observation(collector, node, second):
    """
    Return what the collected reports say, as one Observation.

    An error in setup or teardown is an execution error and no
    conformance result. Only what the call phase reported is a result
    about the item under test.

    """

    def made(outcome, result, text):
        return Observation(execution_outcome  = outcome,
                           conformance_result = result,
                           observation        = text.strip() or 'Nothing was reported.',
                           node               = node,
                           version            = pytest.__version__,
                           second             = round(second, 3))

    if collector.list_collect:
        return made(OUTCOME_ERROR, None,
                    'pytest could not collect the node. ' + collector.list_collect[0])

    for (when, outcome, text) in collector.list_report:
        if when != WHEN_CALL and outcome == 'failed':
            return made(OUTCOME_ERROR, None,
                        'pytest reported an error in {when}. {text}'.format(when = when,
                                                                            text = text))

    for (when, outcome, text) in collector.list_report:

        if when != WHEN_CALL:
            continue

        if outcome == 'passed':
            return made(OUTCOME_COMPLETED, RESULT_PASSED,
                        'pytest reported the node passed.')

        if outcome == 'failed':
            return made(OUTCOME_COMPLETED, RESULT_FAILED, text)

    for (_, outcome, text) in collector.list_report:
        if outcome == 'skipped':
            return made(OUTCOME_COMPLETED, RESULT_SKIPPED,
                        'pytest reported the node skipped. ' + text)

    return made(OUTCOME_NOT_RUN, None, 'pytest ran no test for the node.')


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
