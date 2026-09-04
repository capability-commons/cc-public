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

import cc_public.eval.control
import cc_public.eval.runner
import cc_public.eval.select


VERDICT_MET   = cc_public.eval.runner.VERDICT_MET
VERDICT_UNMET = cc_public.eval.runner.VERDICT_UNMET

ORIGIN_POOLED = 'all'


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

    A case's verdict is the majority of its samples. Unanimous is the
    fraction of cases every sample answered alike.

    """

    def majority(tally):
        return VERDICT_UNMET if tally.count(VERDICT_UNMET) * 2 > len(tally) \
                             else VERDICT_MET

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
    date     = datetime.date.today().isoformat()
    kept     = [r for r in (document.get('confidence') or [])
                  if r.get('model') != id_model]
    fresh    = [dict(model = id_model, date = date, **r) for r in rows]

    cc_public.edit.field.set_field(tree, id_eval, 'confidence',
                                   value = _yaml(kept + fresh))


# -----------------------------------------------------------------------------
def _yaml(value):
    """
    Return value as YAML text, for the field setter to read back.

    """

    import io
    import ruamel.yaml
    import ruamel.yaml.comments

    # The round trip dumper keeps keys in the order they were given, so
    # that a row reads model, date, origin and then its numbers.
    #
    def keep(node):
        if isinstance(node, dict):
            out = ruamel.yaml.comments.CommentedMap()
            for (k, v) in node.items():
                out[k] = keep(v)
            return out
        if isinstance(node, list):
            return [keep(v) for v in node]
        return node

    stream = io.StringIO()
    ruamel.yaml.YAML(typ = 'rt').dump(keep(value), stream)

    return stream.getvalue()
