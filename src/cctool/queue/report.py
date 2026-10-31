"""
---

id_self:                pym_cctool.queue.report
guid_self:              pym_f603be06d9a640e79ca44b830f900eb4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Reports of the landing queue
brief:                  |
                        Say how the queue stands, measure it, and
                        write the summary of each day for the daily
                        review.
description:            |
                        The status names whether the queue runs or is
                        paused and why, and each patch not landed or
                        withdrawn, with its stage, its latest attempt,
                        what it waits on, what waits on it, the
                        worktree that has claimed its repair, and its
                        note. The measures come from the records: the
                        time from submission to landing and of a
                        landing run, the share of attempts gone to
                        conflict and to rework, and the age of the
                        oldest ready patch. The summary of a UTC day
                        is a file in the git directory, beside the
                        journal, which each run rewrites and the daily
                        review reads: whether the queue runs, each
                        patch gone to conflict or rework that day with
                        its reason and age, and what landed.
edge:                   []

...
"""


import datetime
import pathlib
import statistics

import cctool.gate.gate
import cctool.queue.bundle
import cctool.queue.patch
import cctool.queue.run


# The summaries, one file for each UTC day, in the git directory beside
# the journal. Each run of the daemon rewrites the file of its day.
#
DIR_SUMMARY   = 'cctool_queue_summary'
SUFFIX_DAY    = '.txt'
FORMAT_DAY    = '%Y%m%d'
PREFIX_TREE   = 'worktree '
PREFIX_BRANCH = 'branch '


# -----------------------------------------------------------------------------
def status(root: pathlib.Path) -> list[str]:
    """
    Return the lines that say how the queue of the repository at root
    stands: whether it runs or is paused and why, and for each patch not
    landed or withdrawn, oldest first, its stage and key, its latest
    attempt, what it waits on, the patches that wait on it, the worktree
    that has its branch checked out, as an agent does to repair it, and
    its note.

    """

    list_record = cctool.queue.patch.records(root)
    map_record  = {record['key']: record for record in list_record}
    map_claim   = _claims(root)
    list_line   = [_state(root)]

    for record in sorted(list_record, key = lambda record: record['key'][:15]):
        if record['state'] not in cctool.queue.patch.TUPLE_STAGE:
            continue
        list_part = ['{stage} {key} from {thread}'.format(stage  = record['state'],
                                                          key    = record['key'],
                                                          thread = record['thread'])]
        if record['attempts']:
            last = record['attempts'][-1]
            list_part.append('attempt {n} {outcome} on dev {dev}'.format(
                                 n       = last['n'],
                                 outcome = last['outcome'] or 'running',
                                 dev     = last['dev'][:7]))
        if record['state'] == cctool.queue.patch.STAGE_CANDIDATE:
            why = cctool.queue.patch.blocker(record, map_record)
            if why:
                list_part.append('waits: ' + why)
        list_above = [other['key'] for other in list_record
                      if (other['depends'] or {}).get('key') == record['key']
                      and other['state'] in cctool.queue.patch.TUPLE_STAGE]
        if list_above:
            list_part.append('blocks ' + ', '.join(list_above))
        claim = map_claim.get(cctool.queue.patch.branch(record))
        if claim:
            list_part.append('claimed by ' + claim)
        list_line.append('; '.join(list_part))
        if record['note']:
            list_line.append('  ' + record['note'].splitlines()[0])

    return list_line


# -----------------------------------------------------------------------------
def measures(root: pathlib.Path, now: datetime.datetime | None = None) -> list[str]:
    """
    Return the measures of the queue of the repository at root, from its
    records: the hours from submission to landing and the minutes of a
    landing run, each as a median and a maximum, the share of attempts
    that went to conflict and to rework, and the age of the oldest patch
    ready to be tried, as of now.

    """

    now         = now or datetime.datetime.now(datetime.UTC)
    list_record = cctool.queue.patch.records(root)
    list_wait   = [(_time(record['landed']['time']) - _submitted(record)).total_seconds() / 3600
                   for record in list_record
                   if record['state'] == cctool.queue.patch.STATE_LANDED]
    list_try    = [last for record in list_record for last in record['attempts']
                   if last['outcome'] in (cctool.queue.run.OUTCOME_PASSED,
                                          cctool.queue.run.OUTCOME_FAILED,
                                          cctool.queue.run.OUTCOME_CONFLICT)]
    list_run    = [(_time(last['end']) - _time(last['start'])).total_seconds() / 60
                   for last in list_try
                   if last['end'] and last['outcome'] != cctool.queue.run.OUTCOME_CONFLICT]
    list_ready  = cctool.queue.patch.eligible(root, list_record)

    def _share(outcome: str) -> str:
        if not list_try:
            return 'none tried'
        count = sum(1 for last in list_try if last['outcome'] == outcome)
        return '{count} of {total}'.format(count = count, total = len(list_try))

    return ['submission to landing: {text}'.format(text = _spread(list_wait, 'h')),
            'landing run: {text}'.format(text = _spread(list_run, 'min')),
            'attempts gone to conflict: {text}'.format(
                text = _share(cctool.queue.run.OUTCOME_CONFLICT)),
            'attempts gone to rework: {text}'.format(
                text = _share(cctool.queue.run.OUTCOME_FAILED)),
            'oldest ready patch: {text}'.format(
                text = '{hours:.1f} h'.format(hours = (now - _submitted(list_ready[0]))
                                              .total_seconds() / 3600)
                       if list_ready else 'none ready')]


# -----------------------------------------------------------------------------
def summary(root: pathlib.Path, now: datetime.datetime | None = None) -> list[str]:
    """
    Return the lines of the summary of the UTC day of now, for the daily
    review: whether the queue runs or is paused and why, each patch that
    went to conflict or rework that day with its reason and its age,
    what landed that day, and each bundle that the inbox refused that
    day, if there is an inbox.

    """

    now       = now or datetime.datetime.now(datetime.UTC)
    day       = now.date().isoformat()
    list_move = [line for line in cctool.queue.patch.read_journal(root)
                 if line['time'].startswith(day)]
    list_down = [line for line in list_move
                 if line['to'] in (cctool.queue.patch.STAGE_CONFLICT,
                                   cctool.queue.patch.STAGE_REWORK)]
    list_land = [line for line in list_move if line['to'] is None
                 and line['reason'] == 'landed']
    map_note  = {record['key']: record['note'] for record in cctool.queue.patch.records(root)}

    list_line = ['Landing queue, {day}, as of {time} UTC.'.format(
                     day = day, time = now.strftime('%H:%M')),
                 _state(root),
                 '{count} gone to conflict or rework.'.format(count = len(list_down))]
    for line in list_down:
        age  = _time(line['time']) - _submitted(line)
        note = map_note.get(line['key']) or line['reason']
        list_line.append('  {key} to {to}, {hours:.1f} h old: {note}'.format(
                             key   = line['key'],
                             to    = line['to'],
                             hours = age.total_seconds() / 3600,
                             note  = note.splitlines()[0]))
    list_line.append('{count} landed.'.format(count = len(list_land)))
    list_line.extend('  {key} as {tip}'.format(key = line['key'], tip = (line['dev'] or '')[:7])
                     for line in list_land)

    inbox = cctool.queue.patch.try_git(root, 'config', '--get',
                                       cctool.queue.run.CONFIG_INBOX).stdout.strip()
    if inbox:
        list_refused = cctool.queue.bundle.rejected(pathlib.Path(inbox), now.date())
        list_line.append('{count} refused from the inbox.'.format(count = len(list_refused)))
        list_line.extend('  {name}: {why}'.format(name = name, why = why)
                         for (name, why) in list_refused)

    return list_line


# -----------------------------------------------------------------------------
def write_summary(root: pathlib.Path, now: datetime.datetime | None = None) -> pathlib.Path:
    """
    Return the file of the summary of the UTC day of now, once it is
    rewritten.

    """

    now  = now or datetime.datetime.now(datetime.UTC)
    path = (cctool.gate.gate.git_dir(root) / DIR_SUMMARY
            / (now.strftime(FORMAT_DAY) + SUFFIX_DAY))
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text('\n'.join(summary(root, now)) + '\n', encoding = 'utf-8')
    return path


# -----------------------------------------------------------------------------
def _state(root: pathlib.Path) -> str:
    """
    Return whether the queue of root runs, or is paused and why.

    """

    pause = cctool.queue.run.paused(root)
    if pause is None:
        return 'The queue is running.'
    return 'The queue is paused since {time}: {reason}'.format(**pause)


# -----------------------------------------------------------------------------
def _claims(root: pathlib.Path) -> dict[str, str]:
    """
    Return the worktree of root that has each branch checked out, by the
    name of the branch.

    """

    map_claim = {}
    path      = None
    for line in cctool.queue.patch.git(root, 'worktree', 'list', '--porcelain').splitlines():
        if line.startswith(PREFIX_TREE):
            path = line.removeprefix(PREFIX_TREE)
        elif line.startswith(PREFIX_BRANCH) and path:
            map_claim[line.removeprefix(PREFIX_BRANCH).removeprefix(
                cctool.queue.patch.PREFIX_HEAD)] = path
    return map_claim


# -----------------------------------------------------------------------------
def _spread(list_value: list[float], unit: str) -> str:
    """
    Return the median and maximum of list_value, in unit.

    """

    if not list_value:
        return 'none yet'
    return 'median {median:.1f} {unit}, at most {most:.1f} {unit}, of {count}'.format(
               median = statistics.median(list_value),
               most   = max(list_value),
               unit   = unit,
               count  = len(list_value))


# -----------------------------------------------------------------------------
def _submitted(holder: dict) -> datetime.datetime:
    """
    Return the UTC time of the first submission of the patch whose key
    holder holds.

    """

    return datetime.datetime.strptime(holder['key'][:15], cctool.queue.patch.FORMAT_TIME).replace(
        tzinfo = datetime.UTC)


# -----------------------------------------------------------------------------
def _time(text: str) -> datetime.datetime:
    """
    Return the time that text, as a record writes one, gives.

    """

    return datetime.datetime.fromisoformat(text)
