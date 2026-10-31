"""
---

id_self:                pym_cctool.queue.run
guid_self:              pym_c4db6ead640945b6bfdb429eeb4a88b4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Daemon of the landing queue
brief:                  |
                        Take the oldest eligible patch, replay and
                        sign it onto dev, run the landing gate, and
                        land it if it passes.
description:            |
                        One run of the daemon recovers whatever an
                        interrupted run left unfinished, then tries
                        each eligible patch in turn, oldest first, and
                        pushes dev if a remote is set. It replays the
                        own commits of a patch onto dev in a private
                        worktree in the git directory, signing each
                        with the queue's own key, runs the history
                        check on each replayed commit with the code
                        they hold and the gate of a push on their tip,
                        and writes a gate result. A conflict sends the
                        patch to queue/01_conflict and a failure of
                        any stage to queue/03_rework, each with a
                        note, and no test is retried. A pass is landed
                        by a fast-forward of dev in the main checkout,
                        but only if dev, the tested commit and its
                        gate result still match the attempt. A failure
                        of the queue itself, such as a missing
                        interpreter, a key that cannot sign, a dirty
                        main checkout or a remote that refuses the
                        key, pauses the queue, with the patch in hand
                        back where it was, until WTP resumes it.
edge:                   []

...
"""


import dataclasses
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys

import cctool.gate.gate
import cctool.gate.result
import cctool.queue.bundle
import cctool.queue.patch


# The lock that one run of the daemon holds for as long as it runs, the
# file that says the queue is paused and why, and the private worktree
# in which the daemon replays a patch, all in the git directory.
#
FILE_RUN      = 'cctool_queue_run.lock'
FILE_PAUSE    = 'paused.json'
DIR_WORKTREE  = 'cctool_queue_worktree'

# The settings of git that the daemon reads: the key it signs with,
# which is its own, and the remote it pushes dev to, by a host alias of
# a deploy key. With no remote, dev is not pushed.
#
CONFIG_KEY    = 'queue.signingKey'
CONFIG_REMOTE = 'queue.remote'

# The setting that names the inbox, a folder that the daemon sweeps for
# bundles at each run and submits as patches. With no inbox, a bundle is
# submitted only by cctool queue submit.
#
CONFIG_INBOX  = 'queue.inbox'

# The outcomes of an attempt.
#
OUTCOME_CONFLICT = 'conflict'
OUTCOME_FAILED   = 'failed'
OUTCOME_PASSED   = 'passed'
OUTCOME_STALE    = 'stale'
OUTCOME_LOST     = 'interrupted'
OUTCOME_PAUSED   = 'paused'

# What git says when a remote refuses who is pushing, as against a
# remote that cannot be reached, which is tried again at the next run.
#
TUPLE_DENIED  = ('Permission denied', 'denied', 'Authentication failed',
                 'could not read Username', 'not found')

# The least free space, in bytes, that a run needs in the git
# directory: a gate copies the tree and pytest writes beside it.
#
BYTES_FREE    = 1 << 30
COUNT_LINE    = 200

# How pytest begins the line of its summary that names a test that
# failed, or raised an error, so that the first line of a note can name
# it.
#
TUPLE_FAILED  = ('FAILED ', 'ERROR ')
STAGE_HISTORY = 'history'
MODULE_COMMAND = 'cctool.cli.command'


# -----------------------------------------------------------------------------
class ErrorPause(Exception):
    """
    A failure of the queue itself, not of a patch: the queue pauses.

    """


# -----------------------------------------------------------------------------
@dataclasses.dataclass(frozen = True)
class Policy:
    """
    How the daemon makes a landing run: the stages of the gate it runs on
    the tip of a patch, whether it runs the history check on each of its
    commits, the key it signs with, the remote it pushes dev to, how
    long a stage may run, and the inbox it sweeps for bundles.

    """

    stages:    tuple
    history:   bool          = True
    key:       str | None    = None
    remote:    str | None    = None
    seconds:   float         = cctool.gate.gate.SECONDS_STAGE
    inbox:     pathlib.Path | None = None


# -----------------------------------------------------------------------------
def policy(root: pathlib.Path) -> Policy:
    """
    Return the policy of the daemon of the repository at root: the stages
    of the gate of a push, with every test not marked slow, the history
    check, and the key, remote and inbox that its git settings give.

    """

    inbox = _config(root, CONFIG_INBOX)
    return Policy(stages = cctool.gate.gate.TUPLE_STAGE,
                  key    = _config(root, CONFIG_KEY),
                  remote = _config(root, CONFIG_REMOTE),
                  inbox  = pathlib.Path(inbox) if inbox else None)


# -----------------------------------------------------------------------------
def run(root: pathlib.Path, policy: Policy) -> list[str]:
    """
    Return a line for each thing that one run of the daemon did in the
    repository at root, its main checkout, under policy.

    A run that finds another holding the queue does nothing, and so does
    one that finds the queue paused. Otherwise it first recovers each
    patch that an interrupted run left under test, then submits each
    bundle in the inbox of policy, if it has one, then tries the oldest
    eligible patch, and the next, until none is left, and then pushes
    dev if a remote is set. A failure of the queue itself pauses it,
    with the patch in hand back where it was. Each run rewrites the
    summary of the day.

    """

    with cctool.queue.patch.locked(root, FILE_RUN, is_waiting = False) as is_held:
        if not is_held:
            return ['Another run holds the queue, so this one does nothing.']
        list_line = []
        try:
            pause = paused(root)
            if pause is not None:
                return ['The queue is paused since {time}: {reason}'.format(**pause)]
            list_line += recover(root)
            if policy.inbox is not None:
                if not policy.inbox.is_dir():
                    raise ErrorPause('The inbox {inbox}, which git config {name} names, is not '
                                     'a folder.'.format(inbox = policy.inbox,
                                                        name  = CONFIG_INBOX))
                list_line += cctool.queue.bundle.sweep(root, policy.inbox)
            list_tried = []
            while True:
                list_ready = [record for record in cctool.queue.patch.eligible(
                                  root, cctool.queue.patch.records(root))
                              if record['key'] not in list_tried]
                if not list_ready:
                    break
                list_tried.append(list_ready[0]['key'])
                list_line += attempt(root, policy, list_ready[0])
            list_line += push(root, policy)
        except ErrorPause as error:
            set_paused(root, str(error))
            list_line.append('The queue is paused: {reason}'.format(reason = error))
        return list_line or ['Nothing was ready to land.']


# -----------------------------------------------------------------------------
def recover(root: pathlib.Path) -> list[str]:
    """
    Return a line for each patch whose state an interrupted run left
    unfinished, once it is put right: each record's branch is made to
    show its stage, and each patch under test is landed if dev already
    holds its tested commit or its run passed, and is otherwise a
    candidate again, since the outcome of its run is not known.

    """

    _discard_worktree(root)
    list_line = []

    for record in cctool.queue.patch.records(root):
        _reconcile(root, record)
        if record['state'] != cctool.queue.patch.STAGE_TEST:
            continue
        last = record['attempts'][-1] if record['attempts'] else None
        if last and last['tip'] and cctool.queue.patch.is_ancestor(
                root, last['tip'], cctool.queue.patch.DEV):
            _landed(root, record, last)
            list_line.append('{key} was found on dev, so it is marked landed.'.format(
                                 key = record['key']))
        elif last and last['outcome'] == OUTCOME_PASSED:
            list_line += land(root, record)
        else:
            if last:
                last['outcome'] = OUTCOME_LOST
            _to(root, record, cctool.queue.patch.STAGE_CANDIDATE,
                'interrupted before its run was complete')
            list_line.append('{key} was interrupted under test, so it is a candidate '
                             'again.'.format(key = record['key']))

    return list_line


# -----------------------------------------------------------------------------
def attempt(root: pathlib.Path, policy: Policy, record: dict) -> list[str]:
    """
    Return what came of one attempt at the patch of record: its own
    commits replayed onto dev and signed in the private worktree, the
    history check run on each, and the gate on the tip, as a landing
    run. A conflict sends the patch to conflict, a failure to rework,
    each with a note, and a pass lands it. A failure of the queue itself
    puts the patch back where it was and pauses the queue.

    """

    preflight(root, policy)
    if not _take(root, record):
        return ['{key} changed while it was taken, so it is left for the next run.'.format(
                    key = record['key'])]
    dev  = cctool.queue.patch.rev(root, cctool.queue.patch.DEV)
    last = {'n':       len(record['attempts']) + 1,
            'dev':     dev,
            'start':   _now(),
            'end':     None,
            'tip':     None,
            'commits': [],
            'outcome': None,
            'stage':   None,
            'note':    None}
    record['attempts'].append(last)
    _to(root, record, cctool.queue.patch.STAGE_TEST, 'taken', dev)

    try:
        tip = replay(root, policy, record, last)
        if tip is None:
            return ['{key} conflicts with dev, so it is in conflict.'.format(key = record['key'])]
        list_done = landing_run(root, policy, record, last)
    except ErrorPause:
        last['outcome'] = OUTCOME_PAUSED
        _to(root, record, cctool.queue.patch.STAGE_CANDIDATE, 'held while the queue pauses')
        raise
    finally:
        _discard_worktree(root)

    list_failed = [(name, output) for (name, is_passed, output) in list_done if not is_passed]
    last['end'] = _now()
    if list_failed:
        (name, output) = list_failed[0]
        last['outcome'] = OUTCOME_FAILED
        last['stage']   = name
        list_test       = [line.split()[1] for line in output.splitlines()
                           if line.startswith(TUPLE_FAILED) and len(line.split()) > 1]
        last['note']    = ('The {name} stage failed on {tip}, replayed onto dev at {dev}, and '
                           'is not retried.{which}\n{output}').format(
                               name   = name,
                               tip    = tip[:7],
                               dev    = dev[:7],
                               which  = (' {count} failed, the first {first}.'.format(
                                             count = len(list_test), first = list_test[0])
                                         if list_test else ''),
                               output = _tail(output))
        record['note']  = last['note']
        _to(root, record, cctool.queue.patch.STAGE_REWORK,
            'the {name} stage failed'.format(name = name), dev)
        return ['{key} failed its {name} stage, so it is in rework.'.format(
                    key = record['key'], name = name)]

    last['outcome'] = OUTCOME_PASSED
    cctool.queue.patch.write(root, record)
    return land(root, record)


# -----------------------------------------------------------------------------
def replay(root: pathlib.Path, policy: Policy, record: dict, last: dict) -> str | None:
    """
    Return the tip of the own commits of the patch of record, from its
    base to its source, replayed onto the dev commit of last in the
    private worktree, each signed with the key of policy; or None, once
    the patch is in conflict, if the replay conflicts. Its submitted
    commits are never changed. A replay that fails for another reason,
    such as a key that cannot sign, is a failure of the queue.

    """

    path = _worktree(root, last['dev'])
    done = _run(path, '-c', 'user.signingkey=' + str(policy.key), '-c', 'commit.gpgsign=true',
                'rebase', '--quiet', '--force-rebase', '-S',
                '--onto', last['dev'], record['base'], record['source'])
    if done.returncode:
        list_path = _run(path, 'diff', '--name-only', '--diff-filter=U').stdout.split()
        _run(path, 'rebase', '--abort')
        if not list_path:
            raise ErrorPause('Replaying {key} failed for a reason other than a conflict: '
                             '{said}'.format(key  = record['key'],
                                             said = (done.stderr or done.stdout).strip()))
        last['outcome'] = OUTCOME_CONFLICT
        last['end']     = _now()
        last['note']    = ('Replaying onto dev at {dev} conflicts in {paths}. Rebase the '
                           'branch onto dev, resolve them, and resubmit it.').format(
                               dev = last['dev'][:7], paths = ', '.join(list_path))
        record['note']  = last['note']
        _to(root, record, cctool.queue.patch.STAGE_CONFLICT, 'replay conflicts', last['dev'])
        return None

    tip             = cctool.queue.patch.rev(path, 'HEAD')
    last['tip']     = tip
    last['commits'] = cctool.queue.patch.commits(root, last['dev'] + '..' + tip)
    cctool.queue.patch.git(root, 'update-ref',
                            cctool.queue.patch.ref(record,
                                                   cctool.queue.patch.REF_ATTEMPT.format(
                                                       n = last['n'])), tip)
    with cctool.queue.patch.locked(root):
        cctool.queue.patch.write(root, record)
    return tip


# -----------------------------------------------------------------------------
def landing_run(root:   pathlib.Path,
                policy: Policy,
                record: dict,
                last:   dict) -> list[tuple[str, bool, str]]:
    """
    Return each stage of the landing run of the attempt last, with
    whether it passed and what it printed: the history check of each
    replayed commit, run with the code they hold, and then, if that
    passes, the gate of policy on their tip, whose gate result is
    written. A gate that cannot run is a failure of the queue.

    """

    tip = last['tip']
    if policy.history:
        path = cctool.gate.gate.git_dir(root) / DIR_WORKTREE
        env  = {**os.environ, 'PYTHONPATH': str(path / 'src')}
        done = subprocess.run([sys.executable, '-m', MODULE_COMMAND, 'history', 'check',
                               '{dev}..{tip}'.format(dev = last['dev'], tip = tip),
                               '--root', str(path)],
                              cwd = path, env = env, capture_output = True, text = True,
                              check = False)
        if done.returncode not in (0, 1):
            raise ErrorPause('The history check of {key} could not run: {said}'.format(
                                 key = record['key'], said = (done.stderr or done.stdout).strip()))
        if done.returncode:
            return [(STAGE_HISTORY, False, done.stdout + done.stderr)]

    try:
        list_done = cctool.gate.gate.gate(root, policy.stages, rev = tip, seconds = policy.seconds)
    except cctool.gate.gate.ErrorGate as error:
        raise ErrorPause('The gate of {key} could not run: {error}'.format(
                             key = record['key'], error = error)) from error

    cctool.gate.result.write(root, tip, last['dev'], policy.stages, list_done)
    return list_done


# -----------------------------------------------------------------------------
def land(root: pathlib.Path, record: dict) -> list[str]:
    """
    Return what came of landing the patch of record, whose last attempt
    passed: dev is fast-forwarded to exactly its tested commit in the
    main checkout, if dev is still the commit it was tested on and the
    gate result of that commit shows the pass. Otherwise the patch is a
    candidate again, and dev is not changed. A main checkout that is not
    on dev, or has changes, pauses the queue, and the patch waits under
    test for the next run. Once landed, the work branch the patch came
    from is deleted, or kept, as tidy decides.

    """

    last   = record['attempts'][-1]
    dev    = cctool.queue.patch.rev(root, cctool.queue.patch.DEV)
    result = cctool.gate.result.read(root, last['tip'])
    held   = cctool.queue.patch.try_git(root, 'rev-parse', '--verify', '--quiet',
                                     cctool.queue.patch.ref(
                                         record, cctool.queue.patch.REF_ATTEMPT.format(
                                             n = last['n']))).stdout.strip()

    if (dev != last['dev'] or held != last['tip'] or result is None
            or result.get('passed') is not True or result.get('commit') != last['tip']
            or result.get('base') != last['dev']):
        last['outcome'] = OUTCOME_STALE
        _to(root, record, cctool.queue.patch.STAGE_CANDIDATE,
            'dev, the tested commit or its gate result no longer match the attempt', dev)
        return ['{key} no longer matches dev, so it is a candidate again.'.format(
                    key = record['key'])]

    _check_main(root)
    done = cctool.queue.patch.try_git(root, 'merge', '--quiet', '--ff-only', last['tip'])
    if done.returncode:
        raise ErrorPause('dev cannot be fast-forwarded in the main checkout: {said}'.format(
                             said = (done.stderr or done.stdout).strip()))

    _landed(root, record, last)
    tidied = cctool.queue.patch.tidy(root, record)
    return ['{key} landed as {tip}.'.format(key = record['key'], tip = last['tip'][:7]),
            *([tidied[0].upper() + tidied[1:] + '.'] if tidied else [])]


# -----------------------------------------------------------------------------
def push(root: pathlib.Path, policy: Policy) -> list[str]:
    """
    Return what came of pushing dev to the remote of policy, if it is
    set and a landed patch is not yet pushed. The pre-push hook runs, as
    for any push. A remote that already holds dev needs nothing; one
    that cannot be reached is tried again at the next run; one that
    refuses the key, or whose dev has diverged, pauses the queue.

    """

    list_record = [record for record in cctool.queue.patch.records(root)
                   if record['state'] == cctool.queue.patch.STATE_LANDED
                   and not record['landed'].get('pushed')]
    if policy.remote is None or not list_record:
        return []

    dev   = cctool.queue.patch.rev(root, cctool.queue.patch.DEV)
    fetch = cctool.queue.patch.try_git(root, 'fetch', '--quiet', policy.remote,
                                    cctool.queue.patch.DEV)
    if fetch.returncode:
        return _unpushed(fetch, 'reached')
    there = cctool.queue.patch.rev(root, 'FETCH_HEAD')
    if not cctool.queue.patch.is_ancestor(root, there, dev):
        raise ErrorPause('dev on {remote} has diverged from dev here, at {there}.'.format(
                             remote = policy.remote, there = there[:7]))
    if there != dev:
        done = cctool.queue.patch.try_git(root, 'push', '--quiet', policy.remote,
                                       '{dev}:refs/heads/{name}'.format(
                                           dev = dev, name = cctool.queue.patch.DEV))
        if done.returncode:
            return _unpushed(done, 'pushed to')

    for record in list_record:
        if cctool.queue.patch.is_ancestor(root, record['landed']['tip'], dev):
            record['landed']['pushed'] = True
            with cctool.queue.patch.locked(root):
                cctool.queue.patch.write(root, record)
    return ['dev is on {remote} at {dev}.'.format(remote = policy.remote, dev = dev[:7])]


# -----------------------------------------------------------------------------
def _unpushed(done: subprocess.CompletedProcess, what: str) -> list[str]:
    """
    Return why dev was not pushed, from done, a run of git that failed,
    or raise ErrorPause if the remote refused the key.

    """

    said = (done.stderr or done.stdout).strip()
    if any(text in said for text in TUPLE_DENIED):
        raise ErrorPause('The remote refused to be {what}: {said}'.format(what = what,
                                                                           said = said))
    return ['The remote could not be {what}, so dev is pushed at the next run: {said}'.format(
                what = what, said = said)]


# -----------------------------------------------------------------------------
def preflight(root: pathlib.Path, policy: Policy) -> None:
    """
    Raise ErrorPause if the queue cannot make a landing run: the main
    checkout is not on dev or has changes, the git directory is short of
    space, the key of policy is not set or cannot sign, or the
    interpreter or a tool that a stage runs cannot be found.

    """

    _check_main(root)
    if shutil.disk_usage(cctool.gate.gate.git_dir(root)).free < BYTES_FREE:
        raise ErrorPause('The git directory has less than {gib} GiB free.'.format(
                             gib = BYTES_FREE >> 30))
    if not policy.key:
        raise ErrorPause('No signing key is set for the queue. Set it with git config '
                         '{name} KEYID.'.format(name = CONFIG_KEY))
    program = _config(root, 'gpg.program') or 'gpg'
    if subprocess.run([program, '--batch', '--list-secret-keys', policy.key],
                      capture_output = True, check = False).returncode:
        raise ErrorPause('The signing key {key} of the queue cannot be found by {program}.'.format(
                             key = policy.key, program = program))
    for (name, tuple_arg) in policy.stages:
        tool = sys.executable if tuple_arg[0] == '{python}' else tuple_arg[0]
        if shutil.which(tool) is None:
            raise ErrorPause('{tool}, which the {name} stage runs, cannot be found.'.format(
                                 tool = tool, name = name))


# -----------------------------------------------------------------------------
def paused(root: pathlib.Path) -> dict | None:
    """
    Return when the queue of root was paused and why, or None if it is
    not paused.

    """

    try:
        return json.loads(_path_pause(root).read_text(encoding = 'utf-8'))
    except (OSError, ValueError):
        return None


# -----------------------------------------------------------------------------
def set_paused(root: pathlib.Path, reason: str) -> None:
    """
    Pause the queue of root, for reason.

    """

    path = _path_pause(root)
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(json.dumps({'time': _now(), 'reason': reason}), encoding = 'utf-8')


# -----------------------------------------------------------------------------
def resume(root: pathlib.Path) -> dict | None:
    """
    Return the pause that the queue of root was in, once it is lifted,
    or None if it was not paused.

    """

    pause = paused(root)
    _path_pause(root).unlink(missing_ok = True)
    return pause


# -----------------------------------------------------------------------------
def _check_main(root: pathlib.Path) -> None:
    """
    Raise ErrorPause unless root is the main checkout, on dev, with no
    change to a tracked file.

    """

    if (cctool.gate.gate.git_dir(root)
            != (root / cctool.queue.patch.git(root, 'rev-parse', '--git-dir').strip()).resolve()):
        raise ErrorPause('{root} is not the main checkout; run the queue there.'.format(
                             root = root))
    if cctool.queue.patch.git(root, 'branch', '--show-current').strip() != (
            cctool.queue.patch.DEV):
        raise ErrorPause('The main checkout is not on dev.')
    if cctool.queue.patch.git(root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ErrorPause('The main checkout has changes to tracked files, and the queue does '
                         'not reset them. Commit them on a topic branch, or discard them.')


# -----------------------------------------------------------------------------
def _take(root: pathlib.Path, record: dict) -> bool:
    """
    Return whether the patch of record is still the candidate it was
    read as, with the same source, as its record now holds it, so that a
    resubmission or withdrawal made since is not overwritten.

    """

    with cctool.queue.patch.locked(root):
        held = cctool.queue.patch.by_ref(root, record['key'])
    return (held['state'], held['source'], held['stale']) == (
        cctool.queue.patch.STAGE_CANDIDATE, record['source'], False)


# -----------------------------------------------------------------------------
def _landed(root: pathlib.Path, record: dict, last: dict) -> None:
    """
    Record the patch of record as landed by its attempt last, and delete
    its branch.

    """

    stage            = record['state']
    record['state']  = cctool.queue.patch.STATE_LANDED
    record['note']   = None
    record['landed'] = {'time':    _now(),
                        'dev':     last['dev'],
                        'tip':     last['tip'],
                        'commits': last['commits'],
                        'pushed':  False}
    with cctool.queue.patch.locked(root):
        cctool.queue.patch.write(root, record)
        _move(root, record, stage, None, 'landed', last['tip'])


# -----------------------------------------------------------------------------
def _to(root: pathlib.Path, record: dict, stage: str, reason: str,
        dev: str | None = None) -> None:
    """
    Move the patch of record to stage, writing its record first.

    """

    old             = record['state']
    record['state'] = stage
    with cctool.queue.patch.locked(root):
        cctool.queue.patch.write(root, record)
        _move(root, record, old, stage, reason, dev)


# -----------------------------------------------------------------------------
def _move(root: pathlib.Path, record: dict, old: str, new: str | None, reason: str,
          dev: str | None) -> None:
    """
    Move the branch of record from old to new, or journal the move alone
    if the branch at old is not there, as when a run was interrupted
    between writing a record and moving its branch.

    """

    name = cctool.queue.patch.PREFIX_HEAD + cctool.queue.patch.branch(record, old)
    if old in cctool.queue.patch.TUPLE_STAGE and cctool.queue.patch.try_git(
            root, 'rev-parse', '--verify', '--quiet', name).returncode:
        old = None
    cctool.queue.patch.move(root, record, old, new, reason, dev)


# -----------------------------------------------------------------------------
def _reconcile(root: pathlib.Path, record: dict) -> None:
    """
    Make the branches of the queue show the state of record: its branch
    at its stage, made if it is missing, and none at any other stage.

    """

    list_name = [cctool.queue.patch.branch(record, stage)
                 for stage in cctool.queue.patch.TUPLE_STAGE]
    list_held = [name for name in list_name if not cctool.queue.patch.try_git(
                     root, 'rev-parse', '--verify', '--quiet',
                     cctool.queue.patch.PREFIX_HEAD + name).returncode]
    want      = (cctool.queue.patch.branch(record)
                 if record['state'] in cctool.queue.patch.TUPLE_STAGE else None)
    if list_held == ([want] if want else []):
        return
    with cctool.queue.patch.locked(root):
        for name in list_held:
            if name != want:
                cctool.queue.patch.git(root, 'update-ref', '-d',
                                        cctool.queue.patch.PREFIX_HEAD + name)
        if want and want not in list_held:
            cctool.queue.patch.move(root, record, None, record['state'], 'reconciled')


# -----------------------------------------------------------------------------
def _worktree(root: pathlib.Path, dev: str) -> pathlib.Path:
    """
    Return the private worktree of the daemon, made afresh at dev.

    """

    _discard_worktree(root)
    path = cctool.gate.gate.git_dir(root) / DIR_WORKTREE
    cctool.queue.patch.git(root, 'worktree', 'add', '--quiet', '--detach', str(path), dev)
    return path


# -----------------------------------------------------------------------------
def _discard_worktree(root: pathlib.Path) -> None:
    """
    Remove the private worktree of the daemon, if there is one.

    """

    path = cctool.gate.gate.git_dir(root) / DIR_WORKTREE
    if path.exists():
        cctool.queue.patch.try_git(root, 'worktree', 'remove', '--force', str(path))
        shutil.rmtree(path, ignore_errors = True)
    cctool.queue.patch.try_git(root, 'worktree', 'prune')


# -----------------------------------------------------------------------------
def _path_pause(root: pathlib.Path) -> pathlib.Path:
    """
    Return the file that says the queue of root is paused.

    """

    return cctool.queue.patch.directory(root) / FILE_PAUSE


# -----------------------------------------------------------------------------
def _config(root: pathlib.Path, name: str) -> str | None:
    """
    Return the git setting name of root, or None if it is not set.

    """

    return cctool.queue.patch.try_git(root, 'config', '--get', name).stdout.strip() or None


# -----------------------------------------------------------------------------
def _tail(text: str) -> str:
    """
    Return the last lines of text, as many as a note holds.

    """

    return '\n'.join(text.rstrip('\n').splitlines()[-COUNT_LINE:])


# -----------------------------------------------------------------------------
def _now() -> str:
    """
    Return the UTC time now, to the second.

    """

    return datetime.datetime.now(datetime.UTC).isoformat(timespec = 'seconds')


# -----------------------------------------------------------------------------
def _run(path: pathlib.Path, *list_arg: str) -> subprocess.CompletedProcess:
    """
    Run git with list_arg in path, and return how it went.

    """

    return subprocess.run(['git', *list_arg], cwd = path, capture_output = True, text = True,
                          check = False)
