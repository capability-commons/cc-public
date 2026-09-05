"""
---

id_self:                pym_cc_public.eval.runner
guid_self:              pym_83b8eb7c9d3f4aa1980016e9231297e6
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Eval runner
brief:                  |
                        Turn a task into a verdict.
description:            |
                        The runner protocol, and the null runner which
                        judges nothing and reports what it would have
                        judged. The null runner uses no model, no
                        credentials and no network.
relation:               []

...
"""


import typing


VERDICT_MET     = 'met'
VERDICT_UNMET   = 'unmet'
VERDICT_UNKNOWN = 'unknown'      # not judged, rather than judged and unsure

ID_MODEL_NULL   = 'null'

# A judge should be as repeatable as the provider allows. The provider
# default is not zero, and a verdict that moves between runs cannot be
# acted on.
#
TEMPERATURE     = 0.0

# How many judgements an adverse verdict is confirmed over. The screen
# is one call; only what comes back unmet is asked again, so on a clean
# corpus the cost stays close to one pass. See ddr_cost_of_checking.
#
COUNT_CONFIRM   = 5

# What names the judge, where a caller has named nothing.
#
NAME_ENV_MODEL  = 'CCTOOL_JUDGE_MODEL'


# -----------------------------------------------------------------------------
def check_count(count, what):
    """
    Return count, an odd positive integer, or raise ValueError.

    A majority is taken over an odd count, so that there is one. An
    even count can tie, and a tie read either way is a verdict nobody
    reached.

    """

    if not isinstance(count, int) or count < 1 or count % 2 == 0:
        raise ValueError('{what} is {count}, and must be an odd positive '
                         'integer, so that a majority of judgements '
                         'exists.'.format(what = what, count = count))

    return count


# -----------------------------------------------------------------------------
def majority(tally):
    """
    Return the verdict most of the tally holds, met or unmet.

    A verdict that is neither, unknown for one, counts for neither, so
    a tally of unknowns is met: nothing found the subject wanting.

    """

    check_count(len(tally), 'The number of judgements')

    return VERDICT_UNMET if tally.count(VERDICT_UNMET) * 2 > len(tally) \
                         else VERDICT_MET


# -----------------------------------------------------------------------------
class Verdict(typing.NamedTuple):
    """
    What a runner returns for one task.

    verdict is unknown where nothing judged the task. That is not a
    third outcome of judgement -- a judge answers met or unmet -- but
    the absence of one, and it is what a dry run produces.

    id_model names what produced the verdict, since a verdict is only
    meaningful alongside the thing that reached it, and is what makes a
    cached verdict safe to reuse or not.

    """

    id_eval:    str
    id_subject: tuple
    verdict:    str
    feedback:   str
    id_model:   str
    is_cached:  bool = False


# -----------------------------------------------------------------------------
class Runner(typing.Protocol):
    """
    The one thing a runner does.

    """

    def run(self, task) -> Verdict:
        ...

    def confirm(self, task, verdict, count) -> Verdict:
        ...

    def sample(self, task, count) -> list:
        ...


# -----------------------------------------------------------------------------
class NullRunner:
    """
    A runner that judges nothing and reports what it would have judged.

    """

    def __init__(self):
        self.id_model   = ID_MODEL_NULL
        self.count_call = 0
        self.count_char = 0

    # -------------------------------------------------------------------------
    def run(self, task) -> Verdict:
        """
        Return an unknown verdict, recording what a real run would cost.

        """

        self.count_call += 1
        self.count_char += len(task.text_input)

        return Verdict(id_eval    = task.id_eval,
                       id_subject = task.id_subject,
                       verdict    = VERDICT_UNKNOWN,
                       feedback   = 'Not judged. No runner was configured.',
                       id_model   = ID_MODEL_NULL)

    # -------------------------------------------------------------------------
    def confirm(self, task, verdict, count) -> Verdict:
        """
        Return the verdict unchanged. Nothing judged it the first time.

        """

        return verdict

    # -------------------------------------------------------------------------
    def sample(self, task, count) -> list:
        """
        Return count unknowns. Nothing judges anything here.

        """

        self.count_call += count
        self.count_char += len(task.text_input) * count

        return [VERDICT_UNKNOWN] * count


# -----------------------------------------------------------------------------
class ErrorNoJudge(Exception):
    """
    Raised where evals were asked for and no judge was named.

    Not a finding about the data. The analysis could not be performed,
    which is a different thing and is reported differently.

    """



# -----------------------------------------------------------------------------
class DspyRunner:
    """
    A runner that puts the criterion to a language model.

    """

    def __init__(self, id_model):

        import dspy

        self.id_model = id_model
        self._lm      = dspy.LM(id_model, temperature = TEMPERATURE)
        self._judge   = dspy.Predict(_signature())

        # Confirmation asks the same question again and wants a fresh
        # answer each time. Against the cache, five judgements would be
        # one judgement copied five times.
        #
        self._lm_fresh = dspy.LM(id_model, temperature = TEMPERATURE,
                                 cache = False)

    # -------------------------------------------------------------------------
    def run(self, task) -> Verdict:
        """
        Return the verdict a judge reaches on this task.

        """

        import dspy

        document = task.document_eval

        with dspy.context(lm = self._lm):
            answer = self._judge(
                        criterion = document.get('criterion', ''),
                        example   = _text_example(document),
                        subject   = task.text_input)

        return Verdict(id_eval    = task.id_eval,
                       id_subject = task.id_subject,
                       verdict    = answer.verdict,
                       feedback   = answer.feedback,
                       id_model   = self.id_model)

    # -------------------------------------------------------------------------
    def confirm(self, task, verdict, count) -> Verdict:
        """
        ---

        id_self:                pyf_cc_public.eval.runner.dspyrunner.confirm
        guid_self:              pyf_29ceb0158ff1456a8fd2606da0e65101
        copyright:              Copyright 2026 William Payne
        license:                Apache-2.0

        protective_mark:

          - id_mark:            mark_public
            guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

        title:                  Confirm
        brief:                  |
                                Return the majority verdict over count
                                judgements of this task.
        description:            |
                                The screening verdict counts as the first
                                judgement and the rest are fresh samples; the
                                majority over the odd count is the verdict
                                reported, met dropping the finding and unmet
                                standing with the tally.
        relation:               []

        ...
        """

        if check_count(count, 'The confirmation count') == 1:
            return verdict

        tally       = [verdict.verdict] + self.sample(task, count - 1)
        count_unmet = tally.count(VERDICT_UNMET)

        if majority(tally) == VERDICT_MET:
            return verdict._replace(verdict = VERDICT_MET)

        return verdict._replace(
                    feedback = 'Unmet on {n} of {count} judgements. '
                               '{feedback}'.format(n        = count_unmet,
                                                   count    = len(tally),
                                                   feedback = verdict.feedback))

    # -------------------------------------------------------------------------
    def sample(self, task, count) -> list:
        """
        Return count fresh verdicts on the task, none of them cached.

        What measurement and confirmation both need: the same question
        asked again and answered again, not one answer copied.

        """

        import dspy

        document = task.document_eval
        tally    = []

        for _ in range(count):
            with dspy.context(lm = self._lm_fresh):
                answer = self._judge(
                            criterion = document.get('criterion', ''),
                            example   = _text_example(document),
                            subject   = task.text_input)
            tally.append(answer.verdict)

        return tally


# -----------------------------------------------------------------------------
def build(id_model):
    """
    Return the runner that the named model asks for.

    """

    if not id_model:
        raise ErrorNoJudge(
            'Evals were asked for and no judge was named. Give '
            '--judge-model, or set {name}. Name the model null for a dry '
            'run, which reports what would be judged without judging '
            'it.'.format(name = NAME_ENV_MODEL))

    if id_model == ID_MODEL_NULL:
        return NullRunner()

    return DspyRunner(id_model)


# -----------------------------------------------------------------------------
def _signature():
    """
    Return the signature a judge answers.

    Built here rather than declared at module level because declaring
    it needs dspy, and reading this module must not.

    """

    import dspy

    class Judge(dspy.Signature):
        """
        Judge one subject against one criterion.

        Answer met or unmet, and say why. Follow the criterion exactly:
        it states what met means, what unmet means, and what to say.
        The examples show how it has been applied before.

        """

        criterion: str = dspy.InputField(
                            desc = 'The criterion to judge against.')
        example:   str = dspy.InputField(
                            desc = 'Worked cases showing how it applies.')
        subject:   str = dspy.InputField(
                            desc = 'What is being judged.')

        verdict: typing.Literal['met', 'unmet'] = dspy.OutputField(
                            desc = 'Whether the subject meets the criterion.')
        feedback: str = dspy.OutputField(
                            desc = 'Why, in the terms the criterion asks for.')

    return Judge


# -----------------------------------------------------------------------------
def _text_example(document_eval):
    """
    Return the eval's worked cases, as a judge would read them.

    """

    return '\n\n'.join(
        'INPUT\n{input}\nVERDICT {verdict}\nFEEDBACK {feedback}'.format(
                            input    = item.get('input', '').strip(),
                            verdict  = item.get('verdict', ''),
                            feedback = item.get('feedback', '').strip())
            for item in document_eval.get('example') or [])
