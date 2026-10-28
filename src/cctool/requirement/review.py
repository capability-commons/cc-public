"""
---

id_self:                pym_cctool.requirement.review
guid_self:              pym_a71469ef66cf44a48381e39c64317e24
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review questions for requirements
brief:                  |
                        Raise the questions a reviewer asks of a
                        requirement, in the manner of SOPHIST, and the
                        characteristics of the INCOSE guide it is is
                        reviewed against.
description:            |
                        SOPHIST reads a requirement for three
                        transformations of what was meant: deletion,
                        where it leaves something out; generalization,
                        where it says more than is meant; and
                        distortion, where words stand in for what is
                        meant. The questions here are raised from the
                        words of the slots: every process word is
                        asked after, a missing condition or qualifier
                        is asked about, and universal words,
                        comparatives, vague words and nominalisations
                        are each asked after once. They are prompts
                        for a reviewer, not failures.

                        The characteristics C1 to C9 are those the
                        INCOSE Guide to Writing Requirements sets for
                        a single requirement, each with the question
                        it asks and what the tree says toward it.
edge:                   []

...
"""


import re
import typing

import cctool.requirement.compose


KEY_CONDITION        = cctool.requirement.compose.KEY_CONDITION
KEY_OBJECT           = cctool.requirement.compose.KEY_OBJECT
KEY_QUALIFIER        = cctool.requirement.compose.KEY_QUALIFIER
KEY_MEASURE          = cctool.requirement.compose.KEY_MEASURE
KEY_RATIONALE        = 'rationale'
KEY_METHOD           = 'verification_method'
KEY_APPROACH         = 'verification_approach'

RELATION_TRACES_TO_PARENT = 'relation_traces_to_parent'
RELATION_TRACES_TO_SOURCE = 'relation_traces_to_source'

CATEGORY_DELETION    = 'deletion'
CATEGORY_GENERAL     = 'generalization'
CATEGORY_DISTORTION  = 'distortion'

# The transformations SOPHIST reads for, in the order a review asks
# after them, each with its name and what it looks for.
#
LIST_CATEGORY        = ((CATEGORY_DELETION,   'Deletion',
                         'What the statement leaves out.'),
                        (CATEGORY_GENERAL,    'Generalization',
                         'Where it says more than is meant.'),
                        (CATEGORY_DISTORTION, 'Distortion',
                         'Where words stand in for what is meant.'))

SET_UNIVERSAL        = {'all', 'every', 'each', 'any', 'no', 'none', 'never',
                        'always', 'nothing', 'everything', 'only', 'whole'}
SET_COMPARATIVE      = {'more', 'less', 'fewer', 'better', 'worse', 'faster',
                        'slower', 'greater', 'smaller', 'higher', 'lower'}
LIST_VAGUE           = ('appropriate', 'adequate', 'sufficient', 'suitable',
                        'reasonable', 'easy', 'easily', 'simple', 'user-friendly',
                        'fast', 'quick', 'quickly', 'flexible', 'robust', 'efficient',
                        'effective', 'normally', 'usually', 'typically', 'generally',
                        'some', 'several', 'many', 'few', 'various', 'etc',
                        'and/or', 'if possible', 'where possible', 'as appropriate',
                        'as far as possible', 'minimal', 'optimal', 'significant',
                        'relevant')
TUPLE_NOMINAL        = ('tion', 'sion', 'ment', 'ance', 'ence', 'ure')
LEN_NOMINAL          = 6

# The characteristics of a single requirement in the INCOSE Guide to
# Writing Requirements, each with the question a reviewer asks of it.
#
LIST_CHARACTERISTIC  = (
    ('C1', 'Necessary',   'Would its removal leave a need that nothing else meets?'),
    ('C2', 'Appropriate', 'Is its detail right for the level of its subject?'),
    ('C3', 'Unambiguous', 'Can it be read in only one way?'),
    ('C4', 'Complete',    'Can it be understood without asking anything more?'),
    ('C5', 'Singular',    'Does it state one capability, characteristic or constraint?'),
    ('C6', 'Feasible',    'Can it be met within the constraints, at an acceptable risk?'),
    ('C7', 'Verifiable',  'Can it be shown to be met in a way all would accept?'),
    ('C8', 'Correct',     'Does it state truly the need it comes from?'),
    ('C9', 'Conforming',  'Does it follow the agreed form and vocabulary?'))

Requirement          = typing.Mapping[str, typing.Any]


# -----------------------------------------------------------------------------
class Question(typing.NamedTuple):
    """
    A question raised of a requirement: the transformation it asks
    after, and its words.

    """

    category: str
    text:     str


# -----------------------------------------------------------------------------
def questions(requirement: Requirement, process_word: str) -> list[Question]:
    """
    Return the questions raised of requirement, whose process word is
    process_word, in the order of LIST_CATEGORY and then of the words.

    """

    text      = ' '.join(str(requirement.get(key) or '')
                         for key in (KEY_CONDITION, KEY_OBJECT, KEY_QUALIFIER))
    list_word = list(dict.fromkeys(re.findall(r"[a-z][a-z'-]*", text.lower())))

    list_question = [Question(CATEGORY_DELETION,
                              'Is ‘{process}’ fully specified: done to what, '
                              'when, and with what result?'.format(process = process_word))]
    if KEY_CONDITION not in requirement:
        list_question.append(Question(CATEGORY_DELETION,
                                      'It has no condition. Does it hold in every '
                                      'state and mode?'))
    if KEY_QUALIFIER not in requirement and KEY_MEASURE not in requirement:
        list_question.append(Question(CATEGORY_DELETION,
                                      'It has no qualifier. Is a measure of how well, '
                                      'how soon or how often needed?'))
    list_question += [Question(CATEGORY_DELETION,
                               'Compared with what is ‘{word}’?'.format(word = word))
                      for word in list_word if word in SET_COMPARATIVE]

    list_question += [Question(CATEGORY_GENERAL,
                               'Does ‘{word}’ hold without exception?'.format(
                                   word = word))
                      for word in list_word if word in SET_UNIVERSAL]

    list_question += [Question(CATEGORY_DISTORTION,
                               'Does ‘{word}’ name a process as if it were a thing? '
                               'If so, which, and done by whom?'.format(word = word))
                      for word in list_word
                      if len(word) >= LEN_NOMINAL and word.endswith(TUPLE_NOMINAL)]
    list_vague = [vague for vague in LIST_VAGUE
                  if re.search(r'(?<![\w-]){vague}(?![\w-])'.format(vague = re.escape(vague)),
                               text.lower())]
    list_question += [Question(CATEGORY_DISTORTION,
                               '‘{word}’ is vague. What would show that it '
                               'holds?'.format(word = vague))
                      for vague in list_vague
                      if not any(vague != other and vague in other for other in list_vague)]

    return list_question


# -----------------------------------------------------------------------------
def characteristics(requirement:   Requirement,
                    list_question: list[Question],
                    list_parent:   list[str]) -> list[tuple[str, str, str, str]]:
    """
    Return each characteristic of LIST_CHARACTERISTIC with its code,
    name and question, and what the tree says toward it: requirement,
    with the questions raised of it and the parents it traces to.

    """

    count_open = sum(1 for question in list_question if question.category != CATEGORY_DELETION)
    method     = str(requirement.get(KEY_METHOD) or '')

    map_said = {
        'C1': 'A rationale is given.' if requirement.get(KEY_RATIONALE)
              else 'No rationale is given.',
        'C3': ('{count} word{s} asked after below.'.format(count = count_open,
                                                           s = '' if count_open == 1 else 's')
               if count_open else 'No words asked after below.'),
        'C5': 'Composed from one process word and one object.',
        'C7': ('By {method}, {approach}.'.format(
                   method   = method,
                   approach = 'with an approach' if requirement.get(KEY_APPROACH)
                              else 'with no approach')
               if method else 'No method of verification.'),
        'C8': ('Traces to {count} parent{s}.'.format(count = len(list_parent),
                                                     s = '' if len(list_parent) == 1 else 's')
               if list_parent else 'No parent to compare it with.'),
        'C9': 'Composes in the SOPHIST MASTER form.'}

    return [(code, name, question, map_said.get(code, ''))
            for (code, name, question) in LIST_CHARACTERISTIC]
