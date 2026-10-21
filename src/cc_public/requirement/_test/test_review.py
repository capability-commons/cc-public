"""
---

id_self:                pym_cc_public.requirement._test.test_review
guid_self:              pym_8504c4e0f245449b820f7ccf0bd8176e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement review tests
brief:                  |
                        Tests of the questions raised of a requirement
                        and of the characteristics it is signed off
                        against.
description:            |
                        Each test reviews a requirement written in the
                        test.
relation:               []

...
"""


import cc_public.requirement.review


REQUIREMENT = {'condition_kind':      'event',
               'condition':           'the Tooling formats every file faster than before',
               'modal_verb':          'shall',
               'activity':            'autonomous',
               'object':              'the configuration as appropriate',
               'rationale':           'A reason.',
               'verification_method': 'test'}


# -----------------------------------------------------------------------------
def test_questions_ask_after_each_transformation():
    list_question = cc_public.requirement.review.questions(REQUIREMENT, 'keep')
    assert [(question.category, question.text.split('’')[0].split('‘')[-1])
            for question in list_question] == [
        ('deletion',       'keep'),
        ('deletion',       'It has no qualifier. Is a measure of how well, how soon or how '
                           'often needed?'),
        ('deletion',       'faster'),
        ('generalization', 'every'),
        ('distortion',     'configuration'),
        ('distortion',     'as appropriate')]


# -----------------------------------------------------------------------------
def test_questions_ask_after_a_missing_condition():
    requirement   = {key: value for (key, value) in REQUIREMENT.items()
                     if key not in ('condition', 'condition_kind')}
    list_question = cc_public.requirement.review.questions(requirement, 'keep')
    assert any(question.text.startswith('It has no condition.') for question in list_question)


# -----------------------------------------------------------------------------
def test_characteristics_say_what_the_tree_shows():
    list_question = cc_public.requirement.review.questions(REQUIREMENT, 'keep')
    map_said      = {code: said for (code, _, _, said)
                     in cc_public.requirement.review.characteristics(
                            REQUIREMENT, list_question, [])}
    assert list(map_said) == ['C{n}'.format(n = n) for n in range(1, 10)]
    assert map_said['C1'] == 'A rationale is given.'
    assert map_said['C3'] == '3 words asked after below.'
    assert map_said['C7'] == 'By test, with no approach.'
    assert map_said['C8'] == 'No parent to compare it with.'
