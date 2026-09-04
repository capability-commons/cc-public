"""
---

id_self:                pym_cc_public.check.eval
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
                        rest of the checks. Turns a verdict into the
                        same nonconformity every other check produces.
                        Does not run unless asked for.

...
"""


import cc_public.check.result
import cc_public.eval.control
import cc_public.eval.runner
import cc_public.eval.select


ID_CHECK     = 'eval'
TITLE        = 'Items meet their evals'
NOUN         = 'judgement'

KEY_SEVERITY = 'severity'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result holding a verdict for every task the selector picks.

    An UNMET verdict becomes a nonconformity at the severity the eval
    declares. A MET verdict says nothing. A verdict of unknown -- which
    is what a dry run produces -- becomes a note, since a task that was
    not judged must not be mistaken for one that passed.

    """

    if context.selector_eval is None or context.runner_eval is None:
        return cc_public.check.result.Result(0, [], [])

    runner = context.runner_eval

    list_note          = []
    list_nonconformity = []
    count_verdict      = 0
    map_known          = {}

    for task in cc_public.eval.select.select(context, context.selector_eval):

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

            guid_eval = task.document_eval.get(cc_public.eval.control.KEY_GUID_SELF)

            if guid_eval not in map_known:
                map_known[guid_eval] = cc_public.eval.control.map_case(
                                            context.map_document, guid_eval)

            case = map_known[guid_eval].get(
                        cc_public.eval.control.normalise(task.text_input))

            if case is not None:
                id_case = case.get(cc_public.eval.control.KEY_ID_SELF)
                if case.get(cc_public.eval.control.KEY_VERDICT) == \
                                        cc_public.eval.runner.VERDICT_MET:
                    list_note.append(cc_public.check.result.Note(
                            filepath = task.filepath,
                            message  = 'Judged unmet, and judged met by hand '
                                       'in {case}. {note}'.format(
                                            case = id_case,
                                            note = case.get(
                                                cc_public.eval.control.KEY_NOTE,
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
                        detail             = {'id_model':      runner.id_model,
                                              'count_confirm': context.count_confirm})
