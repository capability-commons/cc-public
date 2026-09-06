"""
---

id_self:                pyp_cc_public.check
guid_self:              pyp_0dcce7d7c1084e04b20e99e52400d2b7
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Check driver
brief:                  |
                        Run the checks and return a report.
description:            |
                        Decides what to check and in what order.
                        Discovers files from the union of the paths
                        given, loads them once into a shared context,
                        runs each check against it, and assembles the
                        report. Knows nothing about how a report is
                        presented.
relation:               []

...
"""


import os
import pathlib
import traceback
import typing

import cc_public.load

from cc_public.check import confidence as check_confidence
from cc_public.check import evidence   as check_evidence
from cc_public.check import identifier as check_identifier
from cc_public.check import identity   as check_identity
from cc_public.check import layout     as check_layout
from cc_public.check import parse     as check_parse
from cc_public.check import reference as check_reference
from cc_public.check import relation  as check_relation
from cc_public.check import requirement as check_requirement
from cc_public.check import result    as check_result
from cc_public.check import schema    as check_schema
from cc_public.check import segment    as check_segment
from cc_public.check import source    as check_source
from cc_public.check import trace     as check_trace
from cc_public.check import workflow  as check_workflow


# The checks, in the order they run. Ordering matters only for fail
# fast, where the first check to find anything is the last one run.
#
CHECK      = (check_parse,
              check_identity,
              check_identifier,
              check_source,
              check_reference,
              check_segment,
              check_relation,
              check_schema,
              check_requirement,
              check_layout,
              check_workflow,
              check_trace,
              check_evidence,
              check_confidence)

STATUS_OK  = 'ok'
STATUS_ADV = 'advisory'
STATUS_BAD = 'nonconformity'
STATUS_ERR = 'error'

TOOL       = 'cctool'
COMMAND    = 'check'


# -----------------------------------------------------------------------------
def check(list_path = (), is_fail_fast = False,
          is_closed_world = False, judgement = None):
    """
    Return a report over the union of the paths given.

    An empty list_path means the current working directory. A report is
    always returned; failures of the analysis are recorded in it rather
    than raised.

    judgement is what the judgement tier hands in to run the evals as a
    check: the check module, the selector, and a builder for the judge,
    which is called here rather than by the caller, so that having no
    judge is reported like any other failure of the analysis. None runs
    the mechanical checks alone, which cost nothing.

    is_closed_world asserts that the paths given hold everything a
    reference could resolve to. It is an assertion by the caller, who
    alone is in a position to make it, and it changes what an
    unresolved reference means.

    """

    list_dirpath   = [pathlib.Path(path) for path in list_path]
    list_dirpath   = list_dirpath or [pathlib.Path.cwd()]

    (ctx, list_error) = context(list_dirpath, is_closed_world, judgement)

    tuple_check = CHECK + ((judgement.module,) if judgement is not None else ())

    list_check = []

    for module in tuple_check:

        (entry, error) = _run(module, ctx, is_fail_fast)

        if error is not None:
            list_error.append(error)

        list_check.append(entry)

        # Advisories do not stop the run. They are things to know
        # about, not things that block, and in a federated slice there
        # may always be some.
        #
        if is_fail_fast and _count(entry, check_result.SEVERITY_CRITICAL):
            break

    return _report(list_dirpath, list_check, list_error, is_fail_fast,
                   is_closed_world)


# -----------------------------------------------------------------------------
class Refusal(typing.NamedTuple):
    """
    Why a report cannot be acted on: what kind of thing stops it, how
    many of them there are, and the first of them.

    """

    kind:  str
    count: int
    first: str

    @property
    def message(self):
        if self.kind == STATUS_ERR:
            return ('The analysis did not complete, so nothing can be said '
                    'about conformity: {n} error(s), the first: '
                    '{first}'.format(n = self.count, first = self.first))
        return '{n} critical finding(s), the first: {first}'.format(
                                            n = self.count, first = self.first)


# -----------------------------------------------------------------------------
def refusal(report, is_checkpoint = False):
    """
    ---

    id_self:                pyf_cc_public.check.refusal
    guid_self:              pyf_1837aeb3fd5340beb2dbceb63ff0c537
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Refusal
    brief:                  |
                            Return the Refusal a caller acting on this
                            report must stop for, or None where the report
                            may be acted on.
    description:            |
                            The one place the policy lives, so that the
                            committer, the executor and the gate cannot
                            disagree about it. An analysis that failed to
                            run refuses always: no claim about the data
                            can be made from a report that did not look at
                            all of it, and a checkpoint, which records a
                            known nonconformity, does not cover an unknown
                            one. A critical finding refuses unless a
                            checkpoint is asked for. Advisories never
                            refuse.
    relation:               []

    ...
    """

    inner = report['report']

    if inner['error']:
        return Refusal(STATUS_ERR, len(inner['error']),
                       '{id_check}: {message}'.format(
                                    id_check = inner['error'][0]['id_check'],
                                    message  = inner['error'][0]['message']))

    if inner['summary']['count_critical'] and not is_checkpoint:
        first = next(n['message'] for c in inner['check']
                                  for n in c['nonconformity']
                                  if n['severity'] == check_result.SEVERITY_CRITICAL)
        return Refusal(STATUS_BAD, inner['summary']['count_critical'], first)

    return None


# -----------------------------------------------------------------------------
def _run(module, context, is_fail_fast):
    """
    Return (check entry, error) for one check. One or the other is None.

    A check that raises is a defect in the tool rather than a finding
    about the data, so the exception is caught, recorded as an error,
    and the remaining checks are still run.

    """

    try:
        result = module.check(context)
    except Exception as err:                        # noqa: BLE001 -- see above
        return ({'id_check':      module.ID_CHECK,
                 'title':         module.TITLE,
                 'status':        STATUS_ERR,
                 'noun':          module.NOUN,
                 'count_item':    0,
                 'detail':        {},
                 'nonconformity': [],
                 'note':          []},
                {'id_check':  module.ID_CHECK,
                 'message':   '{name}: {err}'.format(name = type(err).__name__,
                                                     err  = err),
                 'traceback': traceback.format_exc()})

    list_nonconformity = list(result.list_nonconformity)

    if is_fail_fast:
        list_nonconformity = _truncate(list_nonconformity)

    list_dict = [item._asdict() for item in list_nonconformity]

    entry = {'id_check':      module.ID_CHECK,
             'title':         module.TITLE,
             'status':        STATUS_OK,
             'noun':          module.NOUN,
             'count_item':    result.count_item,
             'detail':        dict(result.detail or {}),
             'nonconformity': list_dict,
             'note':          [item._asdict() for item in result.list_note]}

    if _count(entry, check_result.SEVERITY_CRITICAL):
        entry['status'] = STATUS_BAD
    elif _count(entry, check_result.SEVERITY_ADVISORY):
        entry['status'] = STATUS_ADV

    return (entry, None)


# -----------------------------------------------------------------------------
def _truncate(list_nonconformity):
    """
    Return the first critical nonconformity, or all of the advisories.

    Under fail fast the run stops at the first critical finding and
    reports only it. Advisories neither stop the run nor get trimmed,
    since they are reported for information and there is no reason to
    hide the rest of them.

    """

    for item in list_nonconformity:
        if item.severity == check_result.SEVERITY_CRITICAL:
            return [item]

    return list_nonconformity


# -----------------------------------------------------------------------------
def _count(entry, severity):
    """
    Return how many of entry's nonconformities carry severity.

    """

    return sum(1 for item in entry['nonconformity']
                 if  item['severity'] == severity)


# -----------------------------------------------------------------------------
def context(list_dirpath, is_closed_world = False, judgement = None):
    """
    Return (Context, list_error) for the union of the paths given: every
    document under the paths, loaded once, with the failures of loading
    recorded rather than raised.

    What the checks run over, and what the tree indexes.

    """

    list_error    = []
    list_filepath = []

    for dirpath in list_dirpath:

        if not dirpath.exists():
            list_error.append({'id_check':  '',
                               'message':   'Path does not exist: '
                                            '{path}'.format(path = dirpath),
                               'traceback': ''})
            continue

        list_filepath.extend(_iter_filepath(dirpath))

    # The union -- a file named twice, directly and by its directory,
    # is still checked once.
    #
    list_filepath = sorted(set(list_filepath))

    map_document      = {}
    list_failure_load = []

    for filepath in list_filepath:
        try:
            for (location, document) in cc_public.load.iter_document(filepath):
                map_document[location] = document
        except cc_public.load.ERROR_LOAD as err:
            list_failure_load.append((filepath, str(err).strip()))

    runner_eval = None

    if judgement is not None:
        try:
            runner_eval = judgement.build()
        except Exception as err:
            list_error.append({'id_check':  judgement.module.ID_CHECK,
                               'message':   '{name}: {err}'.format(
                                            name = type(err).__name__,
                                            err  = err),
                               'traceback': ''})

    return (check_result.Context(list_filepath     = list_filepath,
                                 map_document      = map_document,
                                 list_failure_load = list_failure_load,
                                 is_closed_world   = is_closed_world,
                                 selector_eval     = judgement.selector
                                                     if judgement is not None else None,
                                 runner_eval       = runner_eval,
                                 count_confirm     = judgement.count_confirm
                                                     if judgement is not None else 1),
            list_error)


# -----------------------------------------------------------------------------
def _iter_filepath(path):
    """
    Yield each structured data filepath at or below path.

    A path naming a single file yields that file, whatever its suffix --
    naming a file explicitly is taken as intent to check it. A path
    naming a directory is walked, and only recognised suffixes are
    yielded from it. Hidden directories are pruned rather than
    filtered, so environment and version control directories are never
    descended into.

    """

    if path.is_file():
        yield path.resolve()
        return

    for (dirpath, list_dirname, list_filename) in os.walk(path):

        list_dirname[:] = sorted(dirname for dirname in list_dirname
                                             if not dirname.startswith('.'))

        for filename in sorted(list_filename):

            if filename.startswith('.'):
                continue

            filepath = pathlib.Path(dirpath) / filename

            if filepath.suffix.lower() in cc_public.load.SUFFIX_ALL:
                yield filepath.resolve()


# -----------------------------------------------------------------------------
def iter_filepath_all(list_path):
    """
    Yield each structured data filepath at or below any of list_path.

    """

    for path in list_path:
        yield from _iter_filepath(path)


# -----------------------------------------------------------------------------
def _report(list_dirpath, list_check, list_error, is_fail_fast,
            is_closed_world):
    """
    Return the report as plain data, ready for any serialisation.

    Nothing in here is anything but a dict, list, string or integer, so
    that it survives being written as JSON, YAML or XML alike.

    """

    count_critical = sum(_count(entry, check_result.SEVERITY_CRITICAL)
                                                    for entry in list_check)
    count_advisory = sum(_count(entry, check_result.SEVERITY_ADVISORY)
                                                    for entry in list_check)

    return {'report': {'tool':    TOOL,
                       'command': COMMAND,
                       'path':    [str(path) for path in list_dirpath],
                       'summary': {'count_check':         len(list_check),
                                   'count_nonconformity': count_critical
                                                        + count_advisory,
                                   'count_critical':      count_critical,
                                   'count_advisory':      count_advisory,
                                   'count_error':         len(list_error),
                                   'is_fail_fast':        is_fail_fast,
                                   'is_closed_world':     is_closed_world},
                       'check':   list_check,
                       'error':   list_error}}
