"""
---

id_self:                pym_cc_public.nonconformity
guid_self:              pym_688cc1d43ab841ac9455a21837334a04
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Nonconformity reports
brief:                  |
                        Turn what a check, an eval or a test observed
                        into the one shape a report carries.
description:            |
                        A check states what it expects as its title,
                        and a finding states what was observed
                        instead. A test case states what it expects,
                        and a result states what was observed. Both
                        become the same report, each keeping the
                        origin it came from.

                        An absence of observation is not a report. A
                        harness error, a test that did not run, a
                        skip, an inconclusive observation and a
                        criterion that does not apply each say that
                        nothing was found, and none of them yields
                        one.

                        Nothing here writes. A caller that wants a
                        report kept passes it to record.
relation:               []

...
"""


import datetime
import uuid

import cc_public.item


KEY_ID_SELF     = 'id_self'
KEY_GUID_SELF   = 'guid_self'
KEY_CHECK       = 'check'
KEY_TITLE       = 'title'
KEY_ID_CHECK    = 'id_check'
KEY_FINDING     = 'nonconformity'
KEY_FILEPATH    = 'filepath'
KEY_PATH        = 'path'
KEY_MESSAGE     = 'message'
KEY_SEVERITY    = 'severity'
KEY_RESULT      = 'result'
KEY_CONFORMANCE = 'conformance_result'
KEY_OBSERVATION = 'observation'
KEY_OUTCOME     = 'execution_outcome'
KEY_EXPECTATION = 'expectation'

ORIGIN_CHECK    = 'check'
ORIGIN_EVAL     = 'eval'
REL_RESULTS_FROM = 'r_results_from'
ORIGIN_TEST     = 'test'

ID_CHECK_EVAL   = 'eval'
OUTCOME_DONE    = 'completed'
RESULT_FAILED   = 'failed'
SEVERITY_HIGH   = 'critical'

PREFIX          = 'ncr'


# -----------------------------------------------------------------------------
def from_report(map_document, report, defaults):
    """
    Return a report for every finding in a check report.

    The check states what it expects as its title, so the expectation
    is read from the check rather than written again beside it, and the
    two cannot drift. A finding of the eval check keeps eval as its
    origin, since what a judge found and what a check found are told
    apart by where they came from and not by their shape.

    """

    map_id = _map_id(map_document)
    out    = []

    for entry in report.get(KEY_CHECK) or []:

        id_check = entry.get(KEY_ID_CHECK)
        origin   = ORIGIN_EVAL if id_check == ID_CHECK_EVAL else ORIGIN_CHECK

        for finding in entry.get(KEY_FINDING) or []:

            id_subject = map_id.get(finding.get(KEY_FILEPATH))

            out.append(_document(defaults, map_document, {
                'expected':   entry.get(KEY_TITLE) or id_check,
                'observed':   finding.get(KEY_MESSAGE) or '',
                'origin':     origin,
                'severity':   finding.get(KEY_SEVERITY) or SEVERITY_HIGH,
                'title':      'What {id_check} found in {where}'.format(
                                    id_check = id_check,
                                    where    = id_subject or finding.get(KEY_FILEPATH)),
                'brief':      '{where} does not meet what the {id_check} check '
                              'expects.'.format(
                                    id_check = id_check,
                                    where    = id_subject or finding.get(KEY_FILEPATH)),
                'id_subject': id_subject,
                'path':       finding.get(KEY_PATH) or None,
                'diagnostic': 'Reported by the {id_check} check at {filepath}.'.format(
                                    id_check = id_check,
                                    filepath = finding.get(KEY_FILEPATH))}))

    return tuple(out)


# -----------------------------------------------------------------------------
def from_execution(map_document, document, defaults, expectation = None,
                   is_kept = False):
    """
    Return a report for every failed result of one test execution.

    Only a completed execution yields one, and only a result that
    failed. An execution that errored, did not run or was cancelled has
    observed nothing about the item under test; a skip and an
    inconclusive observation say the same. None of them is a failure to
    meet an expectation, and reporting one would say something false
    about the item.

    """

    if document.get(KEY_OUTCOME) != OUTCOME_DONE:
        return ()

    out = []

    for result in (document.get(KEY_RESULT) or {}).values():

        if result.get(KEY_CONFORMANCE) != RESULT_FAILED:
            continue

        out.append(_document(defaults, map_document, {
            'expected':       expectation or 'What {case} expects.'.format(
                                                case = document.get('id_case')),
            'observed':       result.get(KEY_OBSERVATION) or '',
            'origin':         ORIGIN_TEST,
            'severity':       SEVERITY_HIGH,
            'title':          'What {case} found in {subject}'.format(
                                case    = document.get('id_case'),
                                subject = document.get('id_under_test')),
            'brief':          '{subject} does not meet what {case} expects of '
                              'it.'.format(subject = document.get('id_under_test'),
                                           case    = document.get('id_case')),
            'id_subject':     document.get('id_under_test'),
            'digest_subject': document.get('digest_under_test'),
            'diagnostic':     'Observed by {method} through {case}.'.format(
                                method = document.get('id_method'),
                                case   = document.get('id_case')),
            'extra':          {'id_execution':   document.get(KEY_ID_SELF),
                               'guid_execution': document.get(KEY_GUID_SELF),
                               'id_method':      document.get('id_method'),
                               'guid_method':    document.get('guid_method'),
                               'id_case':        document.get('id_case'),
                               'guid_case':      document.get('guid_case')},
            'edge':           _edges(map_document, document) if is_kept else []}))

    return tuple(out)


# -----------------------------------------------------------------------------
def _edges(map_document, document):
    """
    Return the edges a report holds: the run it came from.

    The execution's own guid is used rather than the index, because a
    report is made from an execution before it is written. The edge is
    added only where the execution is kept: one naming a run the tree
    does not hold would dangle, and a report about a development run
    has nothing to point at.

    A field does not carry what an edge should, and a kept report
    could not be walked to the run that produced it. What carries the
    obligation the failure is against is
    qst_nonconformity_report.obligation.

    """

    index = cc_public.item.index(map_document)
    held  = index.by_id.get(REL_RESULTS_FROM)

    if held is None or not document.get(KEY_GUID_SELF):
        return []

    return [{'id_relation':   REL_RESULTS_FROM,
             'guid_relation': held.guid_self,
             'id_target':     document.get(KEY_ID_SELF),
             'guid_target':   document.get(KEY_GUID_SELF)}]


# -----------------------------------------------------------------------------
def _document(defaults, map_document, field):
    """
    Return one report, in the shape sch_nonconformity_report gives it.

    field carries what the origin observed: expected, observed, origin,
    severity, title, and optionally id_subject, path, digest_subject,
    diagnostic and whatever else the origin can say.

    """

    expected   = field['expected']
    observed   = field['observed']
    id_subject = field.get('id_subject')
    now        = datetime.datetime.now(datetime.UTC)
    stamp    = now.strftime('%Y%m%d%H%M%S')
    document = {
        KEY_ID_SELF:      '{p}_{stamp}_{short}'.format(p     = PREFIX, stamp = stamp,
                                                       short = uuid.uuid4().hex[:6]),
        KEY_GUID_SELF:    PREFIX + '_' + uuid.uuid4().hex,
        'copyright':      defaults.get('copyright'),
        'license':        defaults.get('license'),
        'protective_mark': [{'id_mark':   defaults.get('id_mark'),
                             'guid_mark': defaults.get('guid_mark')}],
        'title':          field['title'],
        'brief':          _prose(field['brief']),
        'expected':       _prose(expected),
        'observed':       _prose(observed),
        'origin':         field['origin'],
        'severity':       field['severity'],
        'time_detected':  now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'relation':       list(field.get('edge') or [])}

    if id_subject:
        document['id_subject']   = id_subject
        document['guid_subject'] = _guid_of(cc_public.item.index(map_document),
                                            id_subject)

    for key in ('path', 'digest_subject'):
        if field.get(key):
            document[key] = field[key]

    if field.get('diagnostic'):
        document['diagnostic'] = _prose(field['diagnostic'])

    for (key, value) in (field.get('extra') or {}).items():
        if value:
            document[key] = value

    return {key: value for (key, value) in document.items() if value is not None}


# -----------------------------------------------------------------------------
def _map_id(map_document):
    """
    Return {the location a check reports, the readable id of the item
    there}, so that a report names an item rather than a path.

    """

    return {str(held.location): held.id_self
            for held in cc_public.item.index(map_document).by_id.values()
            if not held.path}


# -----------------------------------------------------------------------------
def _guid_of(index, id_self):
    """
    Return the guid of the item called id_self, or None.

    """

    held = index.by_id.get(id_self)

    return held.guid_self if held is not None else None


def _prose(text):
    """
    Return text as a field holding prose ends.

    """

    return str(text).rstrip('\n') + '\n'
