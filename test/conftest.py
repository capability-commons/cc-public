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


import os
import pathlib
import shutil
import subprocess

import pytest

import cc_public.check
import cc_public.edit.link
import cc_public.edit.tree
import cc_public.evidence


ROOT        = pathlib.Path(__file__).resolve().parent.parent
MAP_OUTCOME = {}

# Set where the session is running some of the suite and not all of it:
# a selective run, a measurement, or the verify component observing the
# tests of one requirement. record keeps the rows a partial run did not
# observe, so nothing is lost; what a partial run rewrites is the
# item's time, its revision and whether the tree was dirty, so the
# record would claim as of now for rows most of which are older. Named
# once, in cc_public.evidence, since the runs that set it are there.
#
VARIABLE_PARTIAL = cc_public.evidence.VARIABLE_PARTIAL

# What a test tree is made of, and what a new item in it is given.
#
DEFAULTS = {'copyright': 'Copyright 2026 William Payne',
            'license':   'Apache-2.0',
            'id_mark':   'mark_public'}
# Every directory the tree keeps items in, read from the tree rather
# than listed, so that a new kind of directory is copied from the day
# it exists; the tests themselves and the working directories stay out.
#
KEEP     = tuple(sorted(p.name for p in ROOT.iterdir()
                        if p.is_dir() and not p.name.startswith('.') and p.name != 'test')
                 ) + ('pyproject.toml',)


def copy_tree(dirpath):
    """
    Copy what a test tree is made of into dirpath.

    """

    for name in KEEP:
        src = ROOT / name
        (shutil.copytree if src.is_dir() else shutil.copy)(src, dirpath / name)


def git(root, *args):
    """
    Run git at root with a test identity, and return its output.

    """

    return subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test',
                           '-c', 'user.email=t@t', *args],
                          capture_output = True, text = True, check = True).stdout


@pytest.fixture
def tree(tmp_path):
    """
    A copy of the tree, opened.

    """

    copy_tree(tmp_path)
    return cc_public.edit.tree.Tree([tmp_path])


@pytest.fixture
def repo(tmp_path):
    """
    A copy of the tree in a git repository with one commit and an
    identity of its own, since a runner may have none.

    """

    copy_tree(tmp_path)
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'config', 'user.name', 'Test')
    git(tmp_path, 'config', 'user.email', 't@t')
    git(tmp_path, 'add', '-A')
    git(tmp_path, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'start')
    return tmp_path


def unverify(tree, id_requirement):
    """
    Remove every verification edge naming a requirement.

    A test that observes what a requirement lacks must decide for
    itself what verifies it. The copy holds no test/, so no test
    function in it verifies anything; a test case is data, is copied,
    and does.

    """

    for document in list(tree.context.map_document.values()):
        for edge in list(document.get('relation') or []):
            if (    edge.get('id_relation') == 'r_verifies'
                and edge.get('id_target')   == id_requirement):
                cc_public.edit.link.unlink(tree, document['id_self'],
                                           'r_verifies', id_requirement)


def clean(root):
    report = cc_public.check.check(list_path = [root])['report']
    return [(c['id_check'], n['message'])
            for c in report['check'] for n in c['nonconformity']
            if n['severity'] == 'critical']

# -----------------------------------------------------------------------------
def pytest_runtest_logreport(report):
    """
    Note the outcome of each instance as it is reported.

    """

    said = cc_public.evidence.outcome_of_event(report.when, report.outcome,
                                              str(report.longrepr or ''),
                                              hasattr(report, 'wasxfail'))

    if said is None:
        return

    # The worst of what the phases said, and not the last of them. A
    # function whose call passed and whose teardown then errored had
    # its pass left standing, because the hook had no branch for
    # teardown and the later event never overwrote the earlier one.
    #
    held = MAP_OUTCOME.get(report.nodeid)
    MAP_OUTCOME[report.nodeid] = said if held is None else \
                                 min(held, said, key = cc_public.evidence.RANK.index)


# -----------------------------------------------------------------------------
def reporter_of(session):
    """
    Return the plugin that writes lines to the terminal, or None.

    """

    return session.config.pluginmanager.get_plugin('terminalreporter')


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

    # An adapter running one node is a test execution, not a session that
    # establishes evidence. What an execution does to the current evidence
    # is ddr_evidence_dependency_closure's, and is not a side effect here.
    #
    if os.environ.get('CCTOOL_ADAPTER'):
        return

    # A session that ran part of the suite observed part of the
    # evidence, and writing it would drop every case it did not run.
    #
    if os.environ.get(VARIABLE_PARTIAL):
        if reporter_of(session) is not None:
            reporter_of(session).write_line(
                    'evidence not written: this session ran part of the suite.')
        return

    reporter = reporter_of(session)

    try:
        written = cc_public.evidence.from_pytest(ROOT, MAP_OUTCOME, pytest.__version__)
    except Exception as err:  # reported, never hidden
        written = None
        if reporter is not None:
            reporter.write_line('evidence NOT written: {err}'.format(err = err))
        return

    if reporter is not None and written is not None:
        reporter.write_line('evidence written to {path}'.format(
                                path = written.relative_to(ROOT)))
