"""
---

id_self:                pym_test.test_gating
guid_self:              pym_d31f3b19e75a4653940496c3b751e6ff
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gating status tests
brief:                  |
                        What the status of a detached gate run says.
                        Which state it is in, how long it has taken,
                        and how its log ends.
description:            |
                        A detached run is read rather than watched, so
                        what the status says is the whole of what a
                        reader gets. These tests write a status
                        document and a log, then assert what the view
                        over them says. A run whose process has gone
                        is reported as stopped rather than as running.
                        A failing run is followed by the end of its
                        log and not the whole of it. A passing run
                        needs no log at all. A second run is refused
                        while one is live, and the refusal names the
                        run that holds the worktree.
relation:               []

...
"""


import os
import subprocess
import sys

import click.testing

import cc_public.cli.command
import cc_public.cli.gating




def run(*args):
    return click.testing.CliRunner().invoke(cc_public.cli.command.main, list(args))




def status(root, **field):
    """
    Write a status document the way a run writes one, and return the root.

    """

    cc_public.cli.gating._write_status(root, field)
    return root




def pid_gone():
    """
    Return the identity of a process that has certainly finished.

    Started and waited for, rather than a number chosen for being
    large, because what os.kill is asked is whether a process is there
    and only a process that has been there can answer that with no.

    """

    done = subprocess.Popen([sys.executable, '-c', ''])
    done.wait()
    return done.pid




def test_a_run_still_going_says_so_with_how_long_and_where_it_has_got_to(tmp_path):
    (tmp_path / '.gate.log').write_text('one\ntwo\nthree\n', encoding = 'utf-8')
    status(tmp_path,
           snapshot = 'a' * 40,
           started  = '2026-09-14T13:00:00Z',
           pid      = os.getpid(),
           state    = 'running',
           log      = str(tmp_path / '.gate.log'))

    out = run('gate', '--status', '--root', str(tmp_path))

    assert out.exit_code == 1
    assert 'state      running' in out.output
    assert 'elapsed' in out.output
    assert 'The log ends:' in out.output
    assert 'three' in out.output


def test_a_run_whose_process_has_gone_is_stopped_and_not_still_running(tmp_path):
    status(tmp_path,
           snapshot = 'a' * 40,
           started  = '2026-09-14T13:00:00Z',
           pid      = pid_gone(),
           state    = 'running',
           log      = str(tmp_path / '.gate.log'))

    out = run('gate', '--status', '--root', str(tmp_path))

    assert out.exit_code == 1
    assert 'state      stopped' in out.output
    assert 'running' not in out.output


def test_a_failing_run_is_followed_by_the_end_of_its_log_and_not_the_whole(tmp_path):
    line = ['line {n}'.format(n = n) for n in range(100)]
    (tmp_path / '.gate.log').write_text('\n'.join(line), encoding = 'utf-8')
    status(tmp_path,
           snapshot = 'a' * 40,
           started  = '2026-09-14T13:00:00Z',
           finished = '2026-09-14T13:13:20Z',
           state    = 'failed',
           log      = str(tmp_path / '.gate.log'))

    out = run('gate', '--status', '--root', str(tmp_path))

    assert out.exit_code == 1
    assert 'elapsed    13m20s' in out.output
    assert 'line 99' in out.output
    assert 'line 80' in out.output
    assert 'line 79' not in out.output


def test_a_passing_run_says_it_passed_and_says_nothing_of_the_log(tmp_path):
    (tmp_path / '.gate.log').write_text('nobody needs this\n', encoding = 'utf-8')
    status(tmp_path,
           snapshot = 'a' * 40,
           started  = '2026-09-14T13:00:00Z',
           finished = '2026-09-14T13:05:00Z',
           state    = 'passed',
           log      = str(tmp_path / '.gate.log'))

    out = run('gate', '--status', '--root', str(tmp_path))

    assert out.exit_code == 0
    assert 'state      passed' in out.output
    assert 'elapsed    5m00s'  in out.output
    assert 'The log ends:' not in out.output


def test_where_no_gate_has_run_the_status_says_so_and_is_not_a_failure(tmp_path):
    out = run('gate', '--status', '--root', str(tmp_path))

    assert out.exit_code == 0
    assert 'No gate has run here' in out.output


def test_a_second_run_is_refused_while_one_is_live_and_named_in_the_refusal(tmp_path):
    status(tmp_path,
           snapshot = 'b' * 40,
           started  = '2026-09-14T13:00:00Z',
           pid      = os.getpid(),
           state    = 'running',
           log      = str(tmp_path / '.gate.log'))

    out = run('gate', '--root', str(tmp_path))

    assert out.exit_code == 2
    assert 'bbbbbbbbbb' in out.output
    assert str(os.getpid()) in out.output
    assert 'ddr_gate_worktrees_are_few' in out.output
