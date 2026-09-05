"""
---

id_self:                pym_test.conftest
guid_self:              pym_9455e1335ac84fc5be416a2f0b60e143
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pytest adapter
brief:                  |
                        Pytest hooks that hand a session's outcomes to
                        the evidence module.
description:            |
                        Holds the fixture every test module shares, a
                        copy of the tree with its defaults and a
                        helper that lists critical findings, and the
                        pytest hooks that note the outcome of every
                        test instance, map pytest's words onto the
                        evidence outcomes, an expected failure being
                        nothing observed and an unexpected pass a
                        failure, and at the end of the session hand
                        them to the evidence module from the
                        controller alone. A failure to write is
                        reported and never hidden.
relation:               []

...
"""


import pathlib
import shutil

import pytest

import cc_public.check
import cc_public.edit.tree
import cc_public.evidence


ROOT        = pathlib.Path(__file__).resolve().parent.parent
MAP_OUTCOME = {}

# What a test tree is made of, and what a new item in it is given.
#
DEFAULTS = {'copyright': 'Copyright 2026 William Payne',
            'license':   'Apache-2.0',
            'id_mark':   'mark_public'}
KEEP     = ('ddr', 'specimen', 'schema', 'register', 'eval', 'workflow', 'execution', 'requirement', 'need', 'src')


@pytest.fixture
def tree(tmp_path):
    for name in KEEP:
        shutil.copytree(ROOT / name, tmp_path / name)
    return cc_public.edit.tree.Tree([tmp_path])


def clean(root):
    report = cc_public.check.check(list_path = [root])['report']
    return [(c['id_check'], n['message'])
            for c in report['check'] for n in c['nonconformity']
            if n['severity'] == 'critical']

# pytest's words for what happened, as evidence records them. An
# expected failure that failed observed nothing about the requirement;
# one that passed unexpectedly is a failure of the expectation.
#
OUTCOME     = {'passed': cc_public.evidence.OUTCOME_PASSED,
               'failed': cc_public.evidence.OUTCOME_FAILED,
               'skipped': cc_public.evidence.OUTCOME_SKIPPED}


# -----------------------------------------------------------------------------
def pytest_runtest_logreport(report):
    """
    Note the outcome of each instance as it is reported.

    """

    if report.when == 'setup' and report.outcome != 'passed':
        MAP_OUTCOME[report.nodeid] = (cc_public.evidence.OUTCOME_SKIPPED
                                      if report.outcome == 'skipped'
                                      else cc_public.evidence.OUTCOME_ERROR)
    elif report.when == 'call':
        outcome = OUTCOME.get(report.outcome, cc_public.evidence.OUTCOME_ERROR)
        if hasattr(report, 'wasxfail'):
            outcome = (cc_public.evidence.OUTCOME_FAILED if report.outcome == 'passed'
                       else cc_public.evidence.OUTCOME_SKIPPED)
        MAP_OUTCOME[report.nodeid] = outcome


# -----------------------------------------------------------------------------
def pytest_sessionfinish(session, exitstatus):
    """
    Write what the session observed as evidence, once every test has run.

    """

    # Under xdist a worker is a session too, and every report it makes
    # reaches the controller; the controller alone writes, once.
    #
    if hasattr(session.config, 'workerinput'):
        return

    reporter = session.config.pluginmanager.get_plugin('terminalreporter')

    try:
        written = cc_public.evidence.from_pytest(ROOT, MAP_OUTCOME, pytest.__version__)
    except Exception as err:                        # noqa: BLE001 -- reported, never hidden
        written = None
        if reporter is not None:
            reporter.write_line('evidence NOT written: {err}'.format(err = err))
        return

    if reporter is not None and written is not None:
        reporter.write_line('evidence written to {path}'.format(
                                path = written.relative_to(ROOT)))
