"""
---

id_self:                pym_cctool.queue.night
guid_self:              pym_c338e3c23ee349eda46d81698c11dc26
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  The night of the landing queue
brief:                  |
                        Run the overnight tasks on the tip of dev,
                        move the verified branch to it if they pass,
                        and review the tree.
description:            |
                        A night takes the lock of the landing queue,
                        waiting for a landing run to end, and runs the
                        overnight tasks on the tip of dev in a
                        worktree of its own in the git directory,
                        which keeps its environments from one night to
                        the next: the slow run on every supported
                        python, the property tests with many examples,
                        coverage against the floors and the full
                        check. It records the night in the git
                        directory, writes its outcome as a gate result
                        of the commit tested, and, if every task
                        passed, moves the branch verified forward to
                        that commit by fast-forward and pushes it.
                        Then it runs the review: Claude Code,
                        headless, in a worktree of its own beside the
                        main checkout, limited to reading, cctool and
                        committing, which records its findings as
                        annotations and submits them to the queue. On
                        Thursday it runs the weekly in-depth review in
                        place of the daily one.
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
import time
import zoneinfo

import cctool.gate.gate
import cctool.gate.result
import cctool.queue.patch
import cctool.queue.run


# The overnight tasks, each the pixi task that runs it, in the order the
# night runs them: the suite on every supported python, the property
# tests with many examples, coverage against the floors, and the check
# of every document with jsonschema alone.
#
TUPLE_TASK    = (('slow',       ('pixi', 'run', '--locked', 'slow')),
                 ('fuzz',       ('pixi', 'run', '--locked', 'fuzz')),
                 ('coverage',   ('pixi', 'run', '--locked', 'coverage')),
                 ('check-full', ('pixi', 'run', '--locked', 'check-full')))

# The branch that a night that passes moves forward to the commit it
# tested, until main takes its place.
#
BRANCH_VERIFIED = 'verified'

# What a night keeps in the git directory: the worktree it tests in,
# whose environments it keeps between nights, a record of each night,
# and what each review printed. The worktree of a review is made beside
# the main checkout, as any agent's is.
#
DIR_TREE      = 'cctool_night_worktree'
DIR_RECORD    = 'cctool_night'
DIR_REVIEW    = 'cctool_review'
PREFIX_REVIEW = 'cc-public-review-'
BRANCH_REVIEW = 'work/review/'
SUFFIX_RECORD = '.json'
FORMAT_DAY    = '%Y%m%d'

# The longest a task may run, in seconds, and a review.
#
SECONDS_TASK   = 3 * 3600
FILE_MANIFEST  = 'pyproject.toml'
PREFIX_PIXI    = 'PIXI_'
SECONDS_REVIEW = 2 * 3600
SECONDS_WEEKLY = 6 * 3600

# The in-depth review takes the place of the daily one on Thursday, in
# WTP's time zone, just before his weekly budget of tokens resets.
#
ZONE_REVIEW    = 'Europe/London'
DAY_WEEKLY     = 3
KIND_DAILY     = 'daily'
KIND_WEEKLY    = 'weekly'
COUNT_LINE     = 200

# The review: Claude Code, run headless in a worktree of its own, with
# only the tools it needs to read the tree, record its findings as
# annotations with cctool, commit them and submit them to the queue. Any
# other tool is refused rather than asked for, since nobody is there to
# answer.
#
ARG_PROMPT    = '{prompt}'
ARG_GIT_DIR   = '{git_dir}'
TUPLE_REVIEW  = ('claude', '-p', ARG_PROMPT, '--permission-mode', 'dontAsk',
                 '--add-dir', ARG_GIT_DIR, '--allowedTools',
                 'Read', 'Glob', 'Grep', 'Write', 'Task', 'Bash(cctool:*)', 'Bash(git status:*)',
                 'Bash(git diff:*)', 'Bash(git log:*)', 'Bash(git show:*)', 'Bash(git add:*)',
                 'Bash(git commit:*)', 'Bash(git cherry:*)', 'Bash(date:*)')

TEXT_REVIEW   = '''Run the daily review of cc-public, as the skill reviewing-the-repository
describes, in this worktree, which is on the branch {branch} made from dev at {dev}.

The night's run of the overnight tasks is recorded in {record}. Read it first: a
red night comes first in the report, since a failing test stops the line
(ruling_what_work_comes_first). The landing queue's summary of the day is in
{summary}, and the log of gate timings is {timing}.

Record each finding the skill says to record as an annotation, with cctool new,
and remove with cctool remove each annotation that no longer applies, saying why
in the commit. Fix nothing else: the review records, it does not repair. Commit
the annotations on this branch through the commit gate, with a title from
cctool message new and the trailer Co-Authored-By: Claude <noreply@anthropic.com>,
and then submit them with cctool queue submit {patch}. If there is nothing to
record, commit nothing.

Write the report to {report}, as the skill describes, and end by printing one
line: the path of the report and the key of the patch submitted, if any.'''

TEXT_WEEKLY   = '''Run the weekly in-depth review of cc-public, as the skill
reviewing-the-repository describes, in this worktree, which is on the branch
{branch} made from dev at {dev}. It takes the place of today's daily review, and
runs just before WTP's weekly budget of tokens resets, so thoroughness is worth
more than economy.

The night's run of the overnight tasks is recorded in {record}. Read it first: a
red night comes first in the report, since a failing test stops the line
(ruling_what_work_comes_first). The landing queue's summary of the day is in
{summary}, the log of gate timings is {timing}, and the earlier reports, daily
and weekly, are in {reports}.

Scope:
- Everything in the daily review, over the commits on dev since the last weekly
  report, or over the last 7 days if there is none.
- Read the whole repository area by area. Split the areas between subagents and
  merge their findings; give each this rule: read anywhere, and write nothing
  but your findings, which you return.
- Judge every design rule and every writing style rule: where the repository
  breaks the parts of it that no check holds, and whether what holds it, its
  relation_is_held_by edges or its enforcement field, still holds what the rule
  claims.
- Count the trends, advice by kind, exception entries and the time of the gate,
  and compare them with last week's report.
- List the patches that cctool queue status shows in conflict or rework, and
  any daily report missing since the last weekly one.

Record each finding the skill says to record as an annotation, with cctool new,
and remove with cctool remove each annotation that no longer applies, saying why
in the commit. Do not record rulings or adopt design rules: only WTP does that.
Commit on this branch through the commit gate, with a title from cctool message
new and the trailer Co-Authored-By: Claude <noreply@anthropic.com>, and submit
with cctool queue submit {patch}. If there is nothing to record, commit nothing.

Write the report to {report}, as the skill describes, ending with what needs
WTP: decisions to rule on and rules to adopt. End by printing one line: the path
of the report and the key of the patch submitted, if any.'''

MAP_REVIEW    = {KIND_DAILY:  (TEXT_REVIEW, SECONDS_REVIEW),
                 KIND_WEEKLY: (TEXT_WEEKLY, SECONDS_WEEKLY)}


# -----------------------------------------------------------------------------
@dataclasses.dataclass(frozen = True)
class Night:
    """
    How a night is run: its tasks, each with the command that runs it in
    the tree tested, how long a task may run, the remote that the
    verified branch is pushed to, and the command that reviews the tree
    after the tasks, or None for no review.

    """

    tasks:   tuple                = TUPLE_TASK
    seconds: float                = SECONDS_TASK
    remote:  str | None           = None
    review:  tuple | None         = TUPLE_REVIEW


# -----------------------------------------------------------------------------
def night(root: pathlib.Path) -> Night:
    """
    Return how a night of the repository at root is run: every overnight
    task, the remote of the landing queue, and the review.

    """

    remote = cctool.queue.patch.try_git(root, 'config', '--get',
                                        cctool.queue.run.CONFIG_REMOTE).stdout.strip()
    return Night(remote = remote or None)


# -----------------------------------------------------------------------------
def run(root: pathlib.Path, night: Night, now: datetime.datetime | None = None) -> list[str]:
    """
    Return a line for each thing that a night did in the repository at
    root, its main checkout: the overnight tasks run on the tip of dev,
    and, if every one passed, the verified branch moved forward to that
    commit and pushed; then the review.

    The tasks run under the lock of the landing queue, waiting for a
    landing run to end, so that they have the processors to themselves
    and dev stands still while they run. They run in a worktree of the
    night's own, at the commit tested, which keeps its environments from
    one night to the next. The night is recorded, and its outcome is
    written as a gate result of that commit, whatever it is. A night that
    cannot run, such as one that finds the main checkout off dev, is
    recorded as failed, with the reason.

    """

    now       = now or datetime.datetime.now(datetime.UTC)
    record    = {'day': now.strftime(FORMAT_DAY), 'start': _now(), 'end': None,
                 'commit': None, 'tasks': [], 'passed': False, 'reason': None,
                 'verified': None}
    list_line = []

    with cctool.queue.patch.locked(root, cctool.queue.run.FILE_RUN):
        try:
            cctool.queue.run.check_main(root)
            tip = cctool.queue.patch.rev(root, cctool.queue.patch.DEV)
            record['commit'] = tip
            path = _tree(root, tip)
            list_done = []
            for (name, tuple_arg) in night.tasks:
                (is_passed, seconds, output) = _task(path, tuple_arg, night.seconds)
                list_done.append((name, is_passed, output))
                record['tasks'].append({'name': name, 'passed': is_passed,
                                        'seconds': round(seconds, 1),
                                        'output': _tail(output)})
                list_line.append('{name} {verdict} in {minutes:.1f} min.'.format(
                                     name    = name,
                                     verdict = 'passed' if is_passed else 'failed',
                                     minutes = seconds / 60))
            record['passed'] = all(is_passed for (_, is_passed, _) in list_done)
            cctool.gate.result.write(root, tip, tip, night.tasks, list_done)
            if record['passed']:
                record['verified'] = advance(root, tip, night.remote)
                list_line.append('verified is at {tip}.'.format(tip = tip[:7]))
            else:
                list_line.append('The night failed on {tip}, so verified stays where it '
                                 'was.'.format(tip = tip[:7]))
        except (cctool.queue.run.ErrorPause, cctool.queue.patch.ErrorQueue) as error:
            record['reason'] = str(error)
            list_line.append('The night could not run: {error}'.format(error = error))
        finally:
            record['end'] = _now()
            write(root, record)

    if night.review is not None:
        list_line += review(root, night.review, record, now)

    return list_line


# -----------------------------------------------------------------------------
def advance(root: pathlib.Path, tip: str, remote: str | None) -> str:
    """
    Return the commit that the verified branch of the repository at root
    is at, once it is moved forward to tip, by fast-forward only, and
    pushed to remote if it is given. Raise ErrorQueue if the branch is at
    a commit that tip does not hold.

    """

    ref  = cctool.queue.patch.PREFIX_HEAD + BRANCH_VERIFIED
    done = cctool.queue.patch.try_git(root, 'rev-parse', '--verify', '--quiet', ref)
    old  = done.stdout.strip() or cctool.queue.patch.ZERO
    if done.stdout.strip() and not cctool.queue.patch.is_ancestor(root, old, tip):
        raise cctool.queue.patch.ErrorQueue(
            '{branch} is at {old}, which {tip} does not hold, so it is not moved.'.format(
                branch = BRANCH_VERIFIED, old = old[:7], tip = tip[:7]))
    cctool.queue.patch.git(root, 'update-ref', ref, tip, old)
    if remote:
        done = cctool.queue.patch.try_git(root, 'push', '--quiet', remote,
                                          '{tip}:{ref}'.format(tip = tip, ref = ref))
        if done.returncode:
            raise cctool.queue.patch.ErrorQueue(
                '{branch} was moved to {tip} here, and could not be pushed: {said}'.format(
                    branch = BRANCH_VERIFIED, tip = tip[:7],
                    said = (done.stderr or done.stdout).strip()))
    return tip


# -----------------------------------------------------------------------------
def review(root:    pathlib.Path,
           command: tuple,
           record:  dict,
           now:     datetime.datetime) -> list[str]:
    """
    Return what came of the review of the night of record: command, with
    the prompt and the git directory put in, run in a worktree of its own
    beside the main checkout, on a branch made from dev, with the cctool
    of that worktree first on the path. On Thursday it is the weekly
    in-depth review, and on any other day the daily one. What it prints
    is kept in the git directory. A review worktree from an earlier night
    whose patch has landed, or that holds no commit, is removed first.

    """

    _sweep_reviews(root)
    day    = record['day']
    kind   = kind_of(now)
    name   = day if kind == KIND_DAILY else '{day}-{kind}'.format(day = day, kind = kind)
    (text, seconds) = MAP_REVIEW[kind]
    branch = BRANCH_REVIEW + name
    path   = root.parent / (PREFIX_REVIEW + name)
    git    = cctool.gate.gate.git_dir(root)
    if path.exists():
        return ['The review worktree {path} is already there, so no review runs.'.format(
                    path = path)]
    cctool.queue.patch.git(root, 'worktree', 'add', '--quiet', '-b', branch, str(path),
                           cctool.queue.patch.DEV)
    dir_review = git / DIR_REVIEW
    dir_review.mkdir(parents = True, exist_ok = True)
    prompt = text.format(
                 branch  = branch,
                 dev     = cctool.queue.patch.rev(root, cctool.queue.patch.DEV)[:7],
                 record  = git / DIR_RECORD / (day + SUFFIX_RECORD),
                 summary = git / 'cctool_queue_summary' / (day + '.txt'),
                 timing  = git / 'cctool_timing.jsonl',
                 reports = dir_review,
                 patch   = 'review_' + name.replace('-', '_'),
                 report  = dir_review / '{date}-{kind}.md'.format(date = now.date().isoformat(),
                                                                  kind = kind))

    env = {**os.environ, 'PATH': os.pathsep.join([str(path / '.pixi' / 'envs' / 'default' /
                                                       'bin'), os.environ.get('PATH', '')])}
    if (path / FILE_MANIFEST).is_file():
        subprocess.run(['pixi', 'install', '--locked'], cwd = path, capture_output = True,
                       check = False, env = {key: value for (key, value) in env.items()
                                             if not key.startswith(PREFIX_PIXI)})
    clock = time.perf_counter()
    try:
        list_arg = [prompt if arg == ARG_PROMPT else str(git) if arg == ARG_GIT_DIR else arg
                    for arg in command]
        done = subprocess.run(list_arg, cwd = path, env = env, capture_output = True,
                              text = True, check = False, timeout = seconds)
        printed = done.stdout + done.stderr
        outcome = 'finished' if done.returncode == 0 else 'failed'
    except subprocess.TimeoutExpired:
        printed = ''
        outcome = 'stopped'
    except FileNotFoundError:
        printed = '{name} cannot be found.\n'.format(name = command[0])
        outcome = 'failed'
    (dir_review / (name + '.log')).write_text(printed, encoding = 'utf-8')

    return ['The {kind} review {outcome} in {minutes:.1f} min: {last}'.format(
                kind    = kind,
                outcome = outcome,
                minutes = (time.perf_counter() - clock) / 60,
                last    = (printed.strip().splitlines() or ['it printed nothing'])[-1])]


# -----------------------------------------------------------------------------
def kind_of(now: datetime.datetime) -> str:
    """
    Return the kind of review that a night at now runs: the weekly one on
    Thursday in WTP's time zone, and the daily one on any other day.

    """

    weekday = now.astimezone(zoneinfo.ZoneInfo(ZONE_REVIEW)).weekday()
    return KIND_WEEKLY if weekday == DAY_WEEKLY else KIND_DAILY


# -----------------------------------------------------------------------------
def records(root: pathlib.Path) -> list[dict]:
    """
    Return the record of each night of the repository at root, oldest
    first.

    """

    dir_record = cctool.gate.gate.git_dir(root) / DIR_RECORD
    if not dir_record.is_dir():
        return []
    return [json.loads(path.read_text(encoding = 'utf-8'))
            for path in sorted(dir_record.glob('*' + SUFFIX_RECORD))]


# -----------------------------------------------------------------------------
def write(root: pathlib.Path, record: dict) -> None:
    """
    Write the record of a night, in place of any record of the same day.

    """

    dir_record = cctool.gate.gate.git_dir(root) / DIR_RECORD
    dir_record.mkdir(parents = True, exist_ok = True)
    (dir_record / (record['day'] + SUFFIX_RECORD)).write_text(
        json.dumps(record, indent = 2, sort_keys = True), encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _tree(root: pathlib.Path, tip: str) -> pathlib.Path:
    """
    Return the worktree of the night, at tip, with every file that git
    does not track removed but its environments, which it keeps.

    """

    path = cctool.gate.gate.git_dir(root) / DIR_TREE
    if not path.exists():
        cctool.queue.patch.try_git(root, 'worktree', 'prune')
        cctool.queue.patch.git(root, 'worktree', 'add', '--quiet', '--detach', str(path), tip)
    else:
        cctool.queue.patch.git(path, 'checkout', '--quiet', '--detach', '--force', tip)
        cctool.queue.patch.git(path, 'clean', '-q', '-ffdx', '--exclude', '.pixi')
    return path


# -----------------------------------------------------------------------------
def _task(path: pathlib.Path, tuple_arg: tuple, seconds: float) -> tuple[bool, float, str]:
    """
    Return whether the task tuple_arg passed in path, within seconds, how
    many seconds it took, and what it printed. A task that runs too long
    is stopped, and fails; one whose program cannot be found fails too.

    """

    clock = time.perf_counter()
    try:
        done = subprocess.run(list(tuple_arg), cwd = path, capture_output = True, text = True,
                              check = False, timeout = seconds)
    except subprocess.TimeoutExpired:
        return (False, time.perf_counter() - clock,
                'Stopped after {seconds:g} s, the time limit of a task.\n'.format(
                    seconds = seconds))
    except FileNotFoundError:
        return (False, time.perf_counter() - clock,
                '{name} cannot be found.\n'.format(name = tuple_arg[0]))
    return (done.returncode == 0, time.perf_counter() - clock, done.stdout + done.stderr)


# -----------------------------------------------------------------------------
def _sweep_reviews(root: pathlib.Path) -> None:
    """
    Remove each review worktree beside the main checkout, and its branch,
    whose commits dev holds the changes of, as its patch landed or it
    committed nothing.

    """

    for path in sorted(root.parent.glob(PREFIX_REVIEW + '*')):
        branch = BRANCH_REVIEW + path.name.removeprefix(PREFIX_REVIEW)
        cherry = cctool.queue.patch.try_git(root, 'cherry', cctool.queue.patch.DEV, branch)
        if cherry.returncode or any(line.startswith('+') for line in cherry.stdout.splitlines()):
            continue
        cctool.queue.patch.try_git(root, 'worktree', 'remove', '--force', str(path))
        shutil.rmtree(path, ignore_errors = True)
        cctool.queue.patch.try_git(root, 'branch', '-D', branch)


# -----------------------------------------------------------------------------
def _tail(text: str) -> str:
    """
    Return the last lines of text, as many as a record keeps.

    """

    return '\n'.join(text.rstrip('\n').splitlines()[-COUNT_LINE:])


# -----------------------------------------------------------------------------
def _now() -> str:
    """
    Return the UTC time now, to the second.

    """

    return datetime.datetime.now(datetime.UTC).isoformat(timespec = 'seconds')
