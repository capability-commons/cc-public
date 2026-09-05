"""
---

id_self:                pym_cc_public.eval.measure
guid_self:              pym_77bb285571e34b1ea01f58e8d019661f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Measure an eval
brief:                  |
                        Judge an eval's control cases and report how
                        often, and how steadily, the judge agrees with
                        them.
description:            |
                        Every case is judged several times without the
                        cache, through the same path a sweep uses. The
                        two error rates are reported apart, and per
                        origin, because cases from different origins
                        answer different questions and pooling them
                        without saying so would say nothing true.

...
"""


import datetime
import hashlib
import json

import cc_public.eval.control
import cc_public.eval.runner
import cc_public.eval.select


VERDICT_MET   = cc_public.eval.runner.VERDICT_MET
VERDICT_UNMET = cc_public.eval.runner.VERDICT_UNMET

ORIGIN_POOLED = 'all'

KEY_DIGEST    = 'digest'
KEY_MODEL     = 'model'

# The eval's fields that shape a judgement. A change to any of them is
# a change to what the confidence was measured about.
#
FIELD_JUDGED  = ('criterion', 'example', 'scope')

LENGTH_DIGEST = cc_public.eval.control.LENGTH_KEY


# -----------------------------------------------------------------------------
def digest(document_eval, map_document):
    """
    Return a short digest of everything a measurement of this eval
    depends on: the fields that shape a judgement, and every control
    case measuring it as (subject, verdict, origin).

    A confidence row carries the digest at the time it was measured, and
    a row whose digest is not the eval's now was measured about
    something else.

    """

    cases = sorted(
        (cc_public.eval.control.normalise(case.get(cc_public.eval.control.KEY_SUBJECT, '')),
         case.get(cc_public.eval.control.KEY_VERDICT),
         case.get(cc_public.eval.control.KEY_ORIGIN))
        for (_, _, case) in cc_public.eval.control.iter_case(
                    map_document, document_eval[cc_public.eval.control.KEY_GUID_SELF]))

    content = {field: _plain(document_eval.get(field)) for field in FIELD_JUDGED}
    content['case'] = cases
    text = json.dumps(content, sort_keys = True, ensure_ascii = True,
                      separators = (',', ':'))

    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:LENGTH_DIGEST]


# -----------------------------------------------------------------------------
def is_current(row, document_eval, map_document):
    """
    Return whether a confidence row describes the eval as it is now.

    """

    return row.get(KEY_DIGEST) == digest(document_eval, map_document)


# -----------------------------------------------------------------------------
def _plain(node):
    """
    Return node as plain python with its prose whitespace collapsed, so
    that a refilled paragraph is the same content.

    """

    if isinstance(node, dict):
        return {str(k): _plain(v) for (k, v) in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    if isinstance(node, str):
        return cc_public.eval.control.normalise(node)
    return node


# -----------------------------------------------------------------------------
def measure(context, document_eval, runner, count_sample):
    """
    Return (rows, detail) for the eval.

    rows holds one mapping per origin present, and one pooled, each
    with the case count, the sample count, the false positive rate
    over the met cases, the false negative rate over the unmet cases,
    and the fraction of cases the judge answered the same way every
    time. detail holds one (id_case, origin, want, tally) per case.

    """

    cc_public.eval.runner.check_count(count_sample, 'The sample count')

    detail = []

    for (id_set, key, case) in cc_public.eval.control.iter_case(
                                    context.map_document,
                                    document_eval[cc_public.eval.control.KEY_GUID_SELF]):

        task  = cc_public.eval.select.Task(
                    id_eval       = document_eval['id_self'],
                    document_eval = document_eval,
                    id_subject    = (case.get('id_self') or key,),
                    filepath      = id_set,
                    text_input    = case[cc_public.eval.control.KEY_SUBJECT])
        tally = runner.sample(task, count_sample)

        detail.append((case.get('id_self') or key,
                       case.get(cc_public.eval.control.KEY_ORIGIN),
                       case.get(cc_public.eval.control.KEY_VERDICT),
                       tally))

    rows = [_row(origin, [d for d in detail if d[1] == origin], count_sample)
            for origin in cc_public.eval.control.ORIGIN_ALL
            if any(d[1] == origin for d in detail)]

    rows.append(_row(ORIGIN_POOLED, detail, count_sample))

    return (rows, detail)


# -----------------------------------------------------------------------------
def _row(origin, list_detail, count_sample):
    """
    Return the rates over one stratum of cases.

    A case's verdict is the majority of its samples, taken as a sweep
    takes it. Unanimous is the fraction of cases every sample answered
    alike.

    """

    majority = cc_public.eval.runner.majority

    met   = [d for d in list_detail if d[2] == VERDICT_MET]
    unmet = [d for d in list_detail if d[2] == VERDICT_UNMET]

    return {'origin':         origin,
            'cases':          len(list_detail),
            'samples':        count_sample,
            'false_positive': (round(sum(majority(d[3]) == VERDICT_UNMET
                                         for d in met) / len(met), 3)
                               if met else None),
            'false_negative': (round(sum(majority(d[3]) == VERDICT_MET
                                         for d in unmet) / len(unmet), 3)
                               if unmet else None),
            'unanimous':      (round(sum(len(set(d[3])) == 1
                                         for d in list_detail)
                                     / len(list_detail), 3)
                               if list_detail else 0.0)}


# -----------------------------------------------------------------------------
def record(tree, id_eval, rows, id_model):
    """
    Write the rows onto the eval as its confidence for this model,
    replacing any earlier rows for the same model.

    """

    import cc_public.edit.field
    import cc_public.load

    item     = tree.resolve(id_eval)
    document = cc_public.load.from_file(item.filepath)
    date     = datetime.datetime.now(datetime.UTC).date().isoformat()
    stamp    = digest(document, tree.context.map_document)
    kept     = [r for r in (document.get('confidence') or [])
                  if r.get(KEY_MODEL) != id_model]
    fresh    = [dict(model = id_model, date = date, **r, digest = stamp)
                for r in rows]

    cc_public.edit.field.set_field(tree, id_eval, 'confidence',
                                   value = kept + fresh)
