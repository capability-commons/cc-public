"""
---

id_self:                pym_cctool.queue.patch
guid_self:              pym_8bd82db8fcfb4832b6986c118fe96098
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Patches of the landing queue
brief:                  |
                        Submit, resubmit and withdraw patches, and
                        keep the record of each.
description:            |
                        A patch is the commits a thread submits as one
                        piece of work. Its key is the UTC time of its
                        first submission and its name, and never
                        changes. Its branch, queue/STAGE/THREAD/KEY,
                        shows its stage, and its record, a JSON file
                        in the git directory, says what it is: its
                        thread, its source tip and the base its own
                        commits start after, the patch it depends on
                        and the revision of it that it was built on,
                        each attempt and its outcome, and what it
                        added to dev. Refs under refs/queue/KEY keep
                        the commits a record names from being
                        collected after its branch is deleted. Each
                        move of a branch is one ref transaction, and
                        is journaled. Only a linear stack of patches
                        is accepted.
edge:                   []

...
"""


import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import re
import subprocess
import tempfile
import typing

import cctool.gate.gate


# The stages of a patch that a branch shows, as the folder under queue/
# that the branch sits in, and the states of a patch that no branch
# shows, once it has landed or been withdrawn.
#
STAGE_CANDIDATE = '00_candidate'
STAGE_CONFLICT  = '01_conflict'
STAGE_TEST      = '02_test'
STAGE_REWORK    = '03_rework'
TUPLE_STAGE     = (STAGE_CANDIDATE, STAGE_CONFLICT, STAGE_TEST, STAGE_REWORK)
STATE_LANDED    = 'landed'
STATE_WITHDRAWN = 'withdrawn'
TUPLE_DONE      = (STATE_LANDED, STATE_WITHDRAWN)

# The branches of the queue, and the refs that keep the commits each
# record names from being collected once its branch is gone.
#
PREFIX_HEAD     = 'refs/heads/'
PREFIX_BRANCH   = 'queue/'
PREFIX_REF      = 'refs/queue/'
REF_SOURCE      = 'source'
REF_BASE        = 'base'
REF_ATTEMPT     = 'attempt/{n}'

# The records, one JSON file for each patch, and the lock that each
# change of a record or of the refs of the queue is made under, in the
# git directory that each worktree shares. The run of the daemon holds
# a lock of its own, so that a submission never waits for a test.
#
DIR_RECORD      = 'cctool_queue'
SUFFIX_RECORD   = '.json'
FILE_LOCK       = 'cctool_queue.lock'
FILE_JOURNAL    = 'cctool_queue.jsonl'

# The name of a thread and of a patch: one segment of a branch name, in
# letters, digits, hyphens and underscores. The key of a patch is the
# UTC time of its first submission and its name.
#
PATTERN_NAME    = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')
PATTERN_KEY     = re.compile(r'(\d{8}_\d{6})_([A-Za-z0-9][A-Za-z0-9_-]*)')
FORMAT_TIME     = '%Y%m%d_%H%M%S'
DELIM_BRANCH    = '/'
DELIM_THREAD    = '-'
DEV             = 'dev'
ZERO            = '0' * 40


# -----------------------------------------------------------------------------
class ErrorQueue(Exception):
    """
    A request the queue refuses, and why; nothing is changed.

    """


# -----------------------------------------------------------------------------
def submit(root:     pathlib.Path,
           id_patch: str,
           source:   str = 'HEAD',
           thread:   str | None = None,
           agent:    str | None = None,
           now:      datetime.datetime | None = None,
           bundle:   str | None = None) -> dict:
    """
    Return the record of a new patch of the commits that source holds
    beyond dev, of the repository at root, once its candidate branch
    and its record are made. No test runs.

    The thread is the current branch, with each slash written as a
    hyphen, unless thread is given. The patch is stamped with the UTC
    time of now, or of this moment, under the lock of the queue; if
    another patch holds that second, it takes the next free one, so
    that no two keys share a time. A source built on a patch of the
    queue depends on it, as placed finds it. bundle names the bundle
    file the commits came in, if they came in one.

    """

    thread = thread or current_thread(root)
    for (what, name) in (('thread', thread), ('patch', id_patch)):
        if not PATTERN_NAME.fullmatch(name):
            raise ErrorQueue('The name of the {what}, {name}, is not one segment of letters, '
                             'digits, hyphens and underscores.'.format(what = what,
                                                                         name = name))
    tip = rev(root, source)

    with locked(root):
        list_record = records(root)
        (base, depends) = placed(root, tip, list_record)
        key = '{time}_{patch}'.format(time  = stamp(list_record, now),
                                      patch = id_patch)
        record = {'key':      key,
                  'thread':   thread,
                  'patch':    id_patch,
                  'agent':    agent,
                  'bundle':   bundle,
                  'state':    STAGE_CANDIDATE,
                  'source':   tip,
                  'base':     base,
                  'depends':  depends,
                  'stale':    False,
                  'note':     None,
                  'attempts': [],
                  'landed':   None}
        write(root, record)
        move(root, record, None, STAGE_CANDIDATE, 'submitted')

    return record


# -----------------------------------------------------------------------------
def resubmit(root: pathlib.Path, ref: str) -> dict:
    """
    Return the record of the patch whose branch is ref, of the repository
    at root, once its commits are those its branch now holds and it is
    a candidate again under the same key, so that it keeps its age and
    its attempts. A patch under test, landed or withdrawn is refused.

    """

    with locked(root):
        record = by_ref(root, ref)
        if record['state'] not in (STAGE_CANDIDATE, STAGE_CONFLICT, STAGE_REWORK):
            raise ErrorQueue('{key} is {state}, so it cannot be resubmitted.'.format(
                                 key = record['key'], state = describe(record['state'])))
        tip = rev(root, PREFIX_HEAD + branch(record))
        (base, depends) = placed(root, tip, [other for other in records(root)
                                             if other['key'] != record['key']])
        stage = record['state']
        record.update({'source':  tip,
                       'base':    base,
                       'depends': depends,
                       'stale':   False,
                       'state':   STAGE_CANDIDATE})
        write(root, record)
        move(root, record, stage, STAGE_CANDIDATE, 'resubmitted')

    return record


# -----------------------------------------------------------------------------
def withdraw(root: pathlib.Path, ref: str) -> dict:
    """
    Return the record of the patch whose branch is ref, of the repository
    at root, once it is withdrawn: its branch is deleted, and its record
    and the refs that keep its commits stay. A patch under test is
    refused.

    """

    with locked(root):
        record = by_ref(root, ref)
        if record['state'] not in (STAGE_CANDIDATE, STAGE_CONFLICT, STAGE_REWORK):
            raise ErrorQueue('{key} is {state}, so it cannot be withdrawn.'.format(
                                 key = record['key'], state = describe(record['state'])))
        stage = record['state']
        record['state'] = STATE_WITHDRAWN
        write(root, record)
        move(root, record, stage, None, 'withdrawn')

    return record


# -----------------------------------------------------------------------------
def placed(root: pathlib.Path, tip: str, list_record: list[dict]) -> tuple[str, dict | None]:
    """
    Return where the patch whose source is tip starts, and the patch it
    depends on, as its key and the revision of it that tip is built on,
    or None. Raise ErrorQueue if tip holds no commit that dev does not,
    or overlaps a patch of list_record in any way but a linear stack.

    A patch, landed or not, whose source tip holds is one tip is built
    on, and the nearest of them is the one it depends on: its own
    commits start there, since a landed patch was replayed onto dev and
    its commits are not the ones tip holds. A patch not landed whose
    commits tip holds only in part is an overlap, and so are two that
    tip is built on and that are not one stack.

    """

    set_own = set(commits(root, tip, '--not', DEV))
    if not set_own:
        raise ErrorQueue('{tip} holds no commit that {dev} does not, so there is nothing to '
                         'submit.'.format(tip = tip[:7], dev = DEV))

    list_below = []
    for record in list_record:
        if record['state'] == STATE_WITHDRAWN:
            continue
        if record['source'] == tip:
            raise ErrorQueue('{tip} is already submitted as {key}.'.format(
                                 tip = tip[:7], key = record['key']))
        if record['source'] in set_own:
            list_below.append(record)
        elif record['state'] != STATE_LANDED and set_own.intersection(
                commits(root, record['source'], '--not', record['base'])):
            raise ErrorQueue('{tip} holds some of the commits of {key} but not its tip, so the '
                             'patch has no clear boundary. Only a linear stack of patches is '
                             'accepted: build on the tip of {key}, or on dev.'.format(
                                 tip = tip[:7], key = record['key']))

    list_below.sort(key = lambda record: len(commits(root, record['source'], '--not', DEV)))
    for (lower, upper) in zip(list_below, list_below[1:], strict = False):
        if not is_ancestor(root, lower['source'], upper['source']):
            raise ErrorQueue('{tip} is built on {lower} and {upper}, which are not one stack. '
                             'Only a linear stack of patches is accepted.'.format(
                                 tip = tip[:7], lower = lower['key'], upper = upper['key']))

    if not list_below:
        return (git(root, 'merge-base', tip, DEV).strip(), None)

    below = list_below[-1]
    return (below['source'], {'key': below['key'], 'source': below['source']})


# -----------------------------------------------------------------------------
def stamp(list_record: list[dict], now: datetime.datetime | None = None) -> str:
    """
    Return the UTC time of now, or of this moment, to the second, as the
    key of a patch begins, or the next second that no key of list_record
    begins with.

    """

    now      = (now or datetime.datetime.now(datetime.UTC)).astimezone(datetime.UTC)
    now      = now.replace(microsecond = 0)
    set_used = {record['key'][:15] for record in list_record}
    while now.strftime(FORMAT_TIME) in set_used:
        now += datetime.timedelta(seconds = 1)
    return now.strftime(FORMAT_TIME)


# -----------------------------------------------------------------------------
def move(root:   pathlib.Path,
         record: dict,
         old:    str | None,
         new:    str | None,
         reason: str,
         dev:    str | None = None) -> None:
    """
    Move the branch of record, of the repository at root, from the stage
    old to the stage new, where None is no branch, in one transaction
    with the refs that keep its source and base, and journal the move
    with reason, and with dev if it is given. The new branch points at
    the source of record. The old branch is deleted only if it still
    points where it was read, so that a move made since is not lost.

    """

    list_line = ['start']
    name_old  = PREFIX_HEAD + branch(record, old) if old else None
    if old:
        list_line.append('delete {ref} {tip}'.format(ref = name_old,
                                                     tip = rev(root, name_old)))
    if new:
        list_line.append('update {ref} {tip}'.format(ref = PREFIX_HEAD + branch(record, new),
                                                     tip = record['source']))
    for (name, tip) in ((REF_SOURCE, record['source']), (REF_BASE, record['base'])):
        list_line.append('update {ref} {tip}'.format(ref = ref(record, name), tip = tip))
    list_line.extend(['prepare', 'commit'])

    git(root, 'update-ref', '--stdin', text = '\n'.join(list_line) + '\n')
    journal(root, record, old, new, reason, dev)


# -----------------------------------------------------------------------------
def journal(root:   pathlib.Path,
            record: dict,
            old:    str | None,
            new:    str | None,
            reason: str,
            dev:    str | None = None) -> None:
    """
    Append a line for a move of the patch of record, of the repository at
    root, from the stage or state old to new, to the journal of the
    queue: its time, key, ref, stages, tip, the dev commit if given, and
    reason.

    """

    line = {'time':   datetime.datetime.now(datetime.UTC).isoformat(timespec = 'seconds'),
            'key':    record['key'],
            'ref':    branch(record, new) if new in TUPLE_STAGE else None,
            'from':   old,
            'to':     new,
            'tip':    record['source'],
            'dev':    dev,
            'reason': reason}
    with path_journal(root).open('a', encoding = 'utf-8') as file:
        file.write(json.dumps(line) + '\n')


# -----------------------------------------------------------------------------
def read_journal(root: pathlib.Path) -> list[dict]:
    """
    Return the lines of the journal of the queue of the repository at
    root, oldest first, leaving out a line that is not whole.

    """

    path = path_journal(root)
    if not path.is_file():
        return []

    list_line = []
    for text in path.read_text(encoding = 'utf-8').splitlines():
        with contextlib.suppress(json.JSONDecodeError):
            list_line.append(json.loads(text))
    return list_line


# -----------------------------------------------------------------------------
def eligible(root: pathlib.Path, list_record: list[dict]) -> list[dict]:
    """
    Return the candidates of list_record that may be tried now, oldest
    first by the time their key begins with: those that are not stale
    and depend on no patch, or on one that has landed as the revision
    they were built on. A candidate whose patch below has changed since
    it was built on it is marked stale, and its record written.

    """

    map_record = {record['key']: record for record in list_record}
    list_ready = []

    for record in sorted(list_record, key = lambda record: record['key'][:15]):
        if record['state'] != STAGE_CANDIDATE or record['stale']:
            continue
        depends = record['depends']
        if depends is None:
            list_ready.append(record)
            continue
        below = map_record.get(depends['key'])
        if below is None:
            continue
        if below['source'] != depends['source']:
            record['stale'] = True
            record['note']  = ('{key}, which this patch is built on, has changed since, so '
                               'rebase this patch onto its new tip and resubmit it.'.format(
                                   key = below['key']))
            with locked(root):
                write(root, record)
                journal(root, record, STAGE_CANDIDATE, STAGE_CANDIDATE, 'stale')
            continue
        if below['state'] == STATE_LANDED:
            list_ready.append(record)

    return list_ready


# -----------------------------------------------------------------------------
def blocker(record: dict, map_record: dict) -> str | None:
    """
    Return why the candidate of record waits, if it does: it is stale, or
    the patch it depends on has not landed, or there is no such patch.

    """

    if record['stale']:
        return 'stale'
    depends = record['depends']
    if depends is None:
        return None
    below = map_record.get(depends['key'])
    if below is None:
        return 'depends on {key}, which has no record'.format(key = depends['key'])
    if below['state'] != STATE_LANDED:
        return 'depends on {key}, which is {state}'.format(key   = below['key'],
                                                            state = describe(below['state']))
    return None


# -----------------------------------------------------------------------------
def describe(state: str) -> str:
    """
    Return state as a sentence names it.

    """

    return {STAGE_CANDIDATE: 'a candidate',
            STAGE_CONFLICT:  'in conflict',
            STAGE_TEST:      'under test',
            STAGE_REWORK:    'in rework'}.get(state, state)


# -----------------------------------------------------------------------------
def records(root: pathlib.Path) -> list[dict]:
    """
    Return the record of each patch of the queue of the repository at
    root, in order of key.

    """

    dir_record = directory(root)
    if not dir_record.is_dir():
        return []

    return [json.loads(path.read_text(encoding = 'utf-8'))
            for path in sorted(dir_record.glob('*' + SUFFIX_RECORD))
            if PATTERN_KEY.fullmatch(path.stem)]


# -----------------------------------------------------------------------------
def by_ref(root: pathlib.Path, ref: str) -> dict:
    """
    Return the record of the patch named by ref: its branch, with or
    without refs/heads/, or its key. Raise ErrorQueue if there is none.

    """

    key  = ref.removeprefix(PREFIX_HEAD).rstrip(DELIM_BRANCH).rsplit(DELIM_BRANCH, 1)[-1]
    path = directory(root) / (key + SUFFIX_RECORD)
    if not PATTERN_KEY.fullmatch(key) or not path.is_file():
        raise ErrorQueue('{ref} names no patch of the queue. Name its branch, such as '
                         'queue/03_rework/THREAD/KEY, or its key.'.format(ref = ref))
    return json.loads(path.read_text(encoding = 'utf-8'))


# -----------------------------------------------------------------------------
def write(root: pathlib.Path, record: dict) -> None:
    """
    Write record, whole or not at all, in place of the record of its
    patch.

    """

    dir_record = directory(root)
    dir_record.mkdir(parents = True, exist_ok = True)
    (handle, name) = tempfile.mkstemp(dir = dir_record, suffix = '.tmp')
    with os.fdopen(handle, 'w', encoding = 'utf-8') as file:
        json.dump(record, file, indent = 2, sort_keys = True)
    os.replace(name, dir_record / (record['key'] + SUFFIX_RECORD))


# -----------------------------------------------------------------------------
def branch(record: dict, stage: str | None = None) -> str:
    """
    Return the branch of the patch of record at stage, or at the stage
    its record holds, without refs/heads/.

    """

    return DELIM_BRANCH.join((PREFIX_BRANCH + (stage or record['state']),
                              record['thread'], record['key']))


# -----------------------------------------------------------------------------
def ref(record: dict, name: str) -> str:
    """
    Return the ref named name that keeps a commit of the patch of record.

    """

    return '{prefix}{key}/{name}'.format(prefix = PREFIX_REF, key = record['key'], name = name)


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def locked(root: pathlib.Path, name: str = FILE_LOCK,
           is_waiting: bool = True) -> typing.Iterator[bool]:
    """
    Hold the lock named name in the git directory of the repository at
    root while the block runs, and yield True; or, if is_waiting is
    false and another process holds it, yield False at once.

    """

    path = cctool.gate.gate.git_dir(root) / name
    with path.open('a') as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | (0 if is_waiting else fcntl.LOCK_NB))
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(file, fcntl.LOCK_UN)


# -----------------------------------------------------------------------------
def current_thread(root: pathlib.Path) -> str:
    """
    Return the name of the current branch of root as the name of a
    thread, with each slash written as a hyphen.

    """

    name = git(root, 'branch', '--show-current').strip()
    if not name:
        raise ErrorQueue('No branch is checked out, so the thread cannot be named; give it '
                         'with --thread.')
    return name.replace(DELIM_BRANCH, DELIM_THREAD)


# -----------------------------------------------------------------------------
def directory(root: pathlib.Path) -> pathlib.Path:
    """
    Return the directory of the records of the queue of root.

    """

    return cctool.gate.gate.git_dir(root) / DIR_RECORD


# -----------------------------------------------------------------------------
def path_journal(root: pathlib.Path) -> pathlib.Path:
    """
    Return the journal of the queue of root.

    """

    return cctool.gate.gate.git_dir(root) / FILE_JOURNAL


# -----------------------------------------------------------------------------
def commits(root: pathlib.Path, *list_arg: str) -> list[str]:
    """
    Return the commits that git rev-list selects with list_arg, oldest
    first.

    """

    return git(root, 'rev-list', '--reverse', *list_arg).split()


# -----------------------------------------------------------------------------
def is_ancestor(root: pathlib.Path, commit: str, other: str) -> bool:
    """
    Return whether commit is other or one of its ancestors.

    """

    return try_git(root, 'merge-base', '--is-ancestor', commit, other).returncode == 0


# -----------------------------------------------------------------------------
def rev(root: pathlib.Path, name: str) -> str:
    """
    Return the commit that name names, or raise ErrorQueue if it names
    none.

    """

    done = try_git(root, 'rev-parse', '--verify', '--quiet', name + '^{commit}')
    if done.returncode:
        raise ErrorQueue('{name} names no commit.'.format(name = name))
    return done.stdout.strip()


# -----------------------------------------------------------------------------
def git(root: pathlib.Path, *list_arg: str, text: str | None = None) -> str:
    """
    Return what git prints when run with list_arg in the repository at
    root, given text on its input, or raise ErrorQueue with what it said
    if it fails.

    """

    done = try_git(root, *list_arg, text = text)
    if done.returncode:
        raise ErrorQueue('git {arg} failed: {said}'.format(
                             arg = ' '.join(list_arg), said = (done.stderr or done.stdout).strip()))
    return done.stdout


# -----------------------------------------------------------------------------
def try_git(root: pathlib.Path, *list_arg: str,
            text: str | None = None) -> subprocess.CompletedProcess:
    """
    Run git with list_arg in the repository at root, given text on its
    input, and return how it went.

    """

    return subprocess.run(['git', *list_arg], cwd = root, input = text, capture_output = True,
                          text = True, check = False)
