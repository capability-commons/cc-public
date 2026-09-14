"""
---

id_self:                pym_cc_public.cli.gating
guid_self:              pym_c781c30db1c347419bf2e2faa337d17f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gating command
brief:                  |
                        gate: the gate, run on a snapshot of the
                        working copy in a worktree of its own.
description:            |
                        Makes a commit holding what the working copy
                        holds, committed or not and tracked or not,
                        through an index of its own so that neither
                        the index nor the working copy is touched.
                        Points a worktree at that commit and runs the
                        gate task there, so that the working copy is
                        free for the length of the run. Copies back
                        the evidence the run observed, whatever it
                        observed.

                        The worktree is kept between runs and pointed
                        at each new snapshot, because what is worth
                        keeping is the environment it holds rather
                        than the files. It has an environment of its
                        own rather than sharing the working copy's:
                        pixi rewrites where the editable install
                        points on each run, so a shared environment
                        would be re-pointed by whichever run went
                        last, and two runs at once would disagree
                        about whose source they were testing.

                        Nothing is sent to anybody when a run ends.
                        What the run says goes to a log as it is said,
                        and what the run is doing goes to a status
                        document beside it, so that whoever comes back
                        reads both. The status flag is that reading.
                        It reports a run whose process has gone as
                        stopped rather than as running, and where a
                        run did not pass it shows the end of the log,
                        which is where the gate stops and so where
                        what it found is
                        (qst_test_in_a_worktree.report).

                        The order the gate runs in is not named here.
                        This module runs the task, and the task is
                        where the order lives
                        (ddr_test_in_a_worktree).
relation:               []

...
"""


import datetime
import io
import os
import pathlib
import shutil
import subprocess
import tempfile

import click
import ruamel.yaml

import cc_public.cli.group
import cc_public.edit.tree
import cc_public.layout


NAME_WORKTREE = '.gate'
NAME_LOG      = '.gate.log'
NAME_STATUS   = '.gate.yaml'
NAME_EVIDENCE = 'evidence'
TASK          = 'gate'

MESSAGE_SNAPSHOT = 'snapshot for the gate'
FORM_MOMENT      = '%Y-%m-%dT%H:%M:%SZ'

STATE_RUNNING = 'running'
STATE_PASSED  = 'passed'
STATE_FAILED  = 'failed'
STATE_STOPPED = 'stopped'

COUNT_TAIL = 20


# -----------------------------------------------------------------------------
class ErrorGate(Exception):
    """
    Raised where the worktree the gate runs in could not be made ready.

    Git said why, and what it said is carried rather than replaced,
    since the thing that went wrong is a repository state nobody here
    can describe better than git can.

    """


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command()
@click.option('--here', 'is_here', is_flag = True,
              help = 'Run in the working copy rather than on a snapshot of it. '
                     'What a fresh checkout wants, since it has nothing to protect.')
@click.option('--status', 'is_status', is_flag = True,
              help = 'Say what the run in flight is doing, or what the last one '
                     'found, and run nothing.')
@cc_public.cli.group.OPTION_ROOT
def gate(is_here, is_status, list_root):
    """
    Run the gate on a snapshot of the working copy, in a worktree of its
    own, so that the working copy is free while it runs.

    The snapshot holds everything the working copy holds, committed and
    not, tracked and not. It is made through an index of its own, so
    nothing about the working copy changes. The evidence the run writes
    is brought back.

    What the run said is kept, as it is said, so that a person who was
    doing something else can read it during the run or after it. --status
    says where that is and what the run is doing.

    """

    root = pathlib.Path((list_root or (pathlib.Path('.'),))[0]).resolve()

    if is_status:
        raise SystemExit(_say_status(root))

    if is_here:
        raise SystemExit(_run(['pixi', 'run', TASK], root))

    running = _running(root)

    if running is not None:
        cc_public.cli.group.fail(
            'A gate started at {when} is still running as process {pid}, on '
            '{snapshot}. There is one worktree and starting a second run would '
            'point it away from under the first (ddr_gate_worktrees_are_few). '
            'Wait for it, or read {log}.'.format(
                        when     = running.get('started'),
                        pid      = running.get('pid'),
                        snapshot = str(running.get('snapshot'))[:10],
                        log      = root / NAME_LOG))

    try:
        snapshot = _snapshot(root)
        worktree = _worktree(root, snapshot)
    except (OSError, ErrorGate) as err:
        cc_public.cli.group.fail(err)

    log = root / NAME_LOG
    click.echo('{snapshot} in {worktree}, saying so in {log}'.format(
                    snapshot = snapshot[:10], worktree = worktree, log = log))

    _write_status(root, {'snapshot': snapshot,
                         'started':  _now(),
                         'pid':      os.getpid(),
                         'state':    STATE_RUNNING,
                         'log':      str(log)})

    status = _run(['pixi', 'run', '--frozen', TASK], worktree, log)
    _bring_back(worktree, root)

    _write_status(root, {'snapshot': snapshot,
                         'started':  _read_status(root).get('started'),
                         'finished': _now(),
                         'state':    STATE_PASSED if status == 0 else STATE_FAILED,
                         'log':      str(log)})

    raise SystemExit(status)


# -----------------------------------------------------------------------------
def _snapshot(root):
    """
    Return the identity of a commit holding what the working copy holds.

    Made through an index of its own, so the index and the working copy
    are untouched. Everything git is not told to ignore goes in,
    including what has never been added, because an item here is
    untracked until it is and the ones worth testing are the newest.

    """

    with tempfile.TemporaryDirectory() as dirpath:

        env = {'GIT_INDEX_FILE': str(pathlib.Path(dirpath) / 'index')}

        _git(root, ['add', '--all'], env)
        tree = _git(root, ['write-tree'], env)

        return _git(root, ['commit-tree', tree, '-p', 'HEAD',
                           '-m', MESSAGE_SNAPSHOT], env)


# -----------------------------------------------------------------------------
def _worktree(root, snapshot):
    """
    Return the worktree the gate runs in, at the snapshot given.

    One worktree, kept between runs and pointed at each new snapshot,
    because what it holds that is worth keeping is its environment. A
    worktree of its own rather than the environment of the working copy
    shared with it: pixi rewrites where the editable install points on
    every run, so a shared environment would be re-pointed by whichever
    run went last.

    """

    path = root / NAME_WORKTREE

    if (path / '.git').exists():
        # Forced, and then cleaned, because the run before this one wrote
        # its evidence and its coverage here and left them behind. What
        # git is told to ignore is left alone, which is what keeps the
        # environment.
        #
        _git(path, ['checkout', '--detach', '--force', snapshot])
        _git(path, ['clean', '--force', '-d'])
        return path

    _git(root, ['worktree', 'add', '--detach', str(path), snapshot])

    click.echo('Installing the environment of the gate worktree, once.')
    _run(['pixi', 'install'], path)

    return path


# -----------------------------------------------------------------------------
def _bring_back(worktree, root):
    """
    Copy the evidence the run observed into the working copy.

    Whatever it observed, passing or failing, because evidence records
    what was seen and not what was hoped. It is evidence of the
    snapshot, so a working copy that has moved on since will read it as
    stale, which is true.

    """

    for filepath in sorted((worktree / NAME_EVIDENCE).glob('*.yaml')):
        shutil.copy(filepath, root / NAME_EVIDENCE / filepath.name)


# -----------------------------------------------------------------------------
def _git(root, argument, env = None):
    """
    Run one git command at root and return what it printed, stripped.

    """

    done = subprocess.run(['git', '-C', str(root), *argument],
                          capture_output = True, text = True, check = False,
                          env = dict(os.environ, **(env or {})))

    if done.returncode != 0:
        raise ErrorGate('git {argument} in {root} said: {said}'.format(
                            argument = ' '.join(argument[:2]),
                            root     = root,
                            said     = (done.stderr or done.stdout).strip()))

    return done.stdout.strip()


# -----------------------------------------------------------------------------
def _run(command, cwd, log = None):
    """
    Run one command in cwd and return what it exited with, its output
    going to the terminal and, where a log is given, to that as it is
    said.

    Written line by line rather than at the end, because the reason the
    run is somewhere else is that nobody is watching it, and a person
    who comes back to a finished run wants what it said at the moment it
    said it rather than a summary of it.

    """

    if log is None:
        return subprocess.run(command, cwd = str(cwd), check = False).returncode

    with open(log, 'w', encoding = 'utf-8') as stream:

        done = subprocess.Popen(command, cwd = str(cwd), text = True,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.STDOUT,
                                bufsize = 1)

        for line in done.stdout:
            click.echo(line, nl = False)
            stream.write(line)
            stream.flush()

        return done.wait()


# -----------------------------------------------------------------------------
def _now():
    """
    Return the moment, to the second, in the one form this tree writes.

    """

    return datetime.datetime.now(datetime.UTC).strftime(FORM_MOMENT)


# -----------------------------------------------------------------------------
def _read_status(root):
    """
    Return what the last run said of itself, or nothing where no run has.

    """

    path = root / NAME_STATUS

    if not path.exists():
        return {}

    return ruamel.yaml.YAML(typ = 'safe').load(
                        path.read_text(encoding = 'utf-8')) or {}


# -----------------------------------------------------------------------------
def _write_status(root, status):
    """
    Write what a run is doing, through the printer, so that it reads the
    way everything else here reads.

    """

    stream = io.StringIO()
    ruamel.yaml.YAML(typ = 'rt').dump(dict(status), stream)

    cc_public.edit.tree.write_text(root / NAME_STATUS,
                                   cc_public.layout.format(stream.getvalue()))


# -----------------------------------------------------------------------------
def _running(root):
    """
    Return what a run still in flight said of itself, or None.

    A run that recorded itself as running and whose process has gone is
    a run that died, and is not in flight. Signal zero asks whether the
    process is there without doing anything to it.

    """

    status = _read_status(root)

    if status.get('state') != STATE_RUNNING:
        return None

    try:
        os.kill(int(status.get('pid') or 0), 0)
    except (OSError, ValueError):
        return None

    return status


# -----------------------------------------------------------------------------
def _say_status(root):
    """
    Say what the run in flight is doing, or what the last one found.

    Nothing pushes this. A run that has found something waits to be
    asked, because whoever asks is nearly always the agent that will
    work out what went wrong and propose the fix, and an agent reads
    when it comes back rather than being interrupted
    (qst_test_in_a_worktree.report).

    """

    status = _read_status(root)

    if not status:
        click.echo('No gate has run here. cctool gate starts one.')
        return 0

    state   = _state(root, status)
    elapsed = _elapsed(status)
    said    = dict(status, state = state)

    if elapsed is not None:
        said['elapsed'] = elapsed

    for (key, value) in said.items():
        click.echo('    {key:10} {value}'.format(key = key, value = value))

    if state != STATE_PASSED:
        _say_end(root, status)

    return 0 if state == STATE_PASSED else 1


# -----------------------------------------------------------------------------
def _state(root, status):
    """
    Return the state of the run, which is not always the one it wrote.

    A run that wrote running and whose process has gone did not finish
    and did not fail: it stopped, and nothing wrote down why. Saying so
    is the difference between waiting for a run that will never end and
    starting another one.

    """

    if status.get('state') != STATE_RUNNING:
        return status.get('state')

    return STATE_RUNNING if _running(root) is not None else STATE_STOPPED


# -----------------------------------------------------------------------------
def _elapsed(status):
    """
    Return how long the run took, or how long it has been going.

    The moment a run started is what it wrote down, and the question
    asked of a run still going is how long it has been going, which is
    a duration and not a time of day.

    """

    started = _moment(status.get('started'))

    if started is None:
        return None

    ended  = _moment(status.get('finished')) or datetime.datetime.now(
                                                            datetime.UTC)
    second = max(int((ended - started).total_seconds()), 0)

    return '{minute}m{second:02d}s'.format(minute = second // 60,
                                           second = second %  60)


# -----------------------------------------------------------------------------
def _moment(text):
    """
    Return the moment a status field holds, or nothing where it holds none.

    """

    if not text:
        return None

    return datetime.datetime.strptime(
                        str(text), FORM_MOMENT).replace(tzinfo = datetime.UTC)


# -----------------------------------------------------------------------------
def _say_end(root, status):
    """
    Say how the log ends, which is where a run says what it found.

    The gate stops at the first step that fails, so what a failing run
    found is at the end of what it said and not somewhere in the middle
    of it. That is a property of the gate rather than of any tool the
    gate runs, which is why nothing here reads what ruff, mypy, pytest
    or the checks print. The end of the log of a run still going is
    where it has got to, which is the other thing worth knowing.

    """

    path = pathlib.Path(status.get('log') or (root / NAME_LOG))

    if not path.exists():
        return

    list_line = path.read_text(encoding = 'utf-8',
                               errors   = 'replace').splitlines()

    if not list_line:
        return

    click.echo('')
    click.echo('The log ends:')

    for line in list_line[-COUNT_TAIL:]:
        click.echo('    {line}'.format(line = line))
