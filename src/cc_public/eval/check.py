"""
---

id_self:                pym_cc_public.eval.check
guid_self:              pym_f7d96b0d7bf84b16b05cb018b140590f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Eval check
brief:                  |
                        Check that items meet the evals anchored on
                        them.
description:            |
                        The seam between the eval machinery and the
                        mechanical checks. Turns a verdict into the
                        same nonconformity every other check produces.
                        Handed to the check driver by the command line
                        as a judgement, this module with the selector,
                        a builder for the judge and the confirmation
                        count, so that the checks import nothing above
                        themselves. Does not run unless asked for.
relation:               []

...
"""


import functools
import sys

import cc_public.check.confidence
import cc_public.check.result
import cc_public.control
import cc_public.eval.runner
import cc_public.eval.measure
import cc_public.eval.select


ID_CHECK     = 'eval'
TITLE        = 'Items meet their evals'
NOUN         = 'judgement'

KEY_SEVERITY = 'severity'


# -----------------------------------------------------------------------------
def judgement(selector, id_model, count_confirm = cc_public.eval.runner.COUNT_CONFIRM):
    """
    Return what the check driver is handed to run the evals as a check:
    this module, the selector, a builder for the judge named, and the
    confirmation count, which must be odd.

    """

    cc_public.eval.runner.check_count(count_confirm, 'The confirmation count')

    return cc_public.check.result.Judgement(
                module        = sys.modules[__name__],
                selector      = selector,
                build         = functools.partial(cc_public.eval.runner.build, id_model),
                count_confirm = count_confirm)


# -----------------------------------------------------------------------------
def check(context):
    """
    ---

    id_self:                pyf_cc_public.eval.check.check
    guid_self:              pyf_4eb27e7eab764186ae2ade5946cda02f
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Eval check
    brief:                  |
                            Return a Result holding a verdict for every
                            task the selector picks.
    description:            |
                            The judge screens every subject once and
                            confirms an adverse verdict over the
                            confirmation count; what comes back unmet is a
                            nonconformity at the severity the eval
                            declares, met says nothing, and unknown is a
                            note.
    relation:               []

    ...
    """

    if context.selector_eval is None or context.runner_eval is None:
        return cc_public.check.result.Result(0, [], [])

    runner = context.runner_eval

    list_note          = []
    list_nonconformity = []
    count_verdict      = 0
    map_known          = {}
    set_unmeasured     = set()

    for task in cc_public.eval.select.select(context, context.selector_eval):

        # Findings from an eval with no current confidence for this
        # judge carry none, which is said once per eval, not per finding.
        #
        if task.id_eval not in set_unmeasured and not any(
                isinstance(row, dict) and row.get('model') == runner.id_model
                and cc_public.check.confidence.is_current(row, task.document_eval,
                                                      context.map_document)
                for row in task.document_eval.get('confidence') or []):
            set_unmeasured.add(task.id_eval)
            list_note.append(cc_public.check.result.Note(
                    filepath = task.filepath,
                    message  = '{id_eval} carries no current confidence for '
                               '{model}, so its findings carry none. Measure '
                               'it.'.format(id_eval = task.id_eval,
                                            model   = runner.id_model)))

        verdict        = runner.run(task)
        count_verdict += 1

        if verdict.verdict == cc_public.eval.runner.VERDICT_UNMET:
            verdict = runner.confirm(task, verdict, context.count_confirm)

        if verdict.verdict == cc_public.eval.runner.VERDICT_MET:
            continue

        subject = ' + '.join(task.id_subject)

        # A person may already have judged this very text. A case
        # holding it as met answers the finding; one holding it as
        # unmet confirms it.
        #
        if verdict.verdict == cc_public.eval.runner.VERDICT_UNMET:

            guid_eval = task.document_eval.get(cc_public.control.KEY_GUID_SELF)

            if guid_eval not in map_known:
                map_known[guid_eval] = cc_public.control.map_case(
                                            context.map_document, guid_eval)

            case = map_known[guid_eval].get(
                        cc_public.control.normalise(task.text_input))

            if case is not None:
                id_case = case.get(cc_public.control.KEY_ID_SELF)
                if case.get(cc_public.control.KEY_VERDICT) == \
                                        cc_public.eval.runner.VERDICT_MET:
                    list_note.append(cc_public.check.result.Note(
                            filepath = task.filepath,
                            message  = 'Judged unmet, and judged met by hand '
                                       'in {case}. {note}'.format(
                                            case = id_case,
                                            note = case.get(
                                                cc_public.control.KEY_NOTE,
                                                '')).strip()))
                    continue
                verdict = verdict._replace(
                            feedback = verdict.feedback
                                       + ' Confirmed by hand in {case}.'.format(
                                                                case = id_case))

        if verdict.verdict == cc_public.eval.runner.VERDICT_UNKNOWN:
            list_note.append(cc_public.check.result.Note(
                    filepath = task.filepath,
                    message  = 'would judge {subject}'.format(
                                                        subject = subject)))
            continue

        list_nonconformity.append(cc_public.check.result.Nonconformity(
                filepath = task.filepath,
                path     = subject,
                severity = task.document_eval.get(
                                KEY_SEVERITY,
                                cc_public.check.result.SEVERITY_ADVISORY),
                message  = verdict.feedback))

    return cc_public.check.result.Result(
                        count_item         = count_verdict,
                        list_nonconformity = list_nonconformity,
                        list_note          = list_note,
                        detail             = _detail(runner, context, count_verdict))


# -----------------------------------------------------------------------------
def _detail(runner, context, count_verdict):
    """
    Return what the report says about the judge, and, for a dry run,
    what a real one would cost at most: the screening calls, the calls
    if every screen came back unmet and was confirmed, and the
    characters of subject sent.

    """

    detail = {'id_model':      runner.id_model,
              'count_confirm': context.count_confirm}

    if hasattr(runner, 'count_call'):
        detail['count_call']     = runner.count_call
        detail['count_call_max'] = count_verdict * context.count_confirm
        detail['count_char']     = runner.count_char

    return detail
