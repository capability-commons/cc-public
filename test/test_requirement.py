"""
---

id_self:                pym_test.test_requirement
guid_self:              pym_0267d23fb9454c388ea4e45b1f8ba4b1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement statement tests
brief:                  |
                        Tests of the requirement statement composer:
                        the SOPHIST forms, the slots that do not
                        compose, and where the statement is shown.
description:            |
                        Composes statements from slots in each
                        activity and condition form, refuses the slot
                        combinations that cannot compose, and checks
                        that a requirement shows its composed
                        statement to a judge and that the evidence
                        digest follows the slots.
relation:               []

...
"""


import pytest

import cc_public.check.evidence
import cc_public.edit.field
import cc_public.eval.select
import cc_public.load
import cc_public.requirement


BASE = {'id_self': 'req_x', 'entity': 'Library_System', 'obligation': 'shall',
        'activity': 'autonomous', 'process': 'display', 'object': 'the Item_Statistics'}


def test_the_three_activities_compose_as_the_sophist_template_gives_them():
    say = cc_public.requirement.statement
    assert say(BASE) == 'The Library_System shall display the Item_Statistics.'
    assert say(dict(BASE, activity = 'interaction', actor = 'Librarian')) == \
        'The Library_System shall provide the Librarian with the ability to display the Item_Statistics.'
    assert say(dict(BASE, activity = 'interface', obligation = 'will')) == \
        'The Library_System will be able to display the Item_Statistics.'


def test_a_condition_opens_with_the_keyword_its_kind_names_and_the_qualifier_closes():
    say = cc_public.requirement.statement
    doc = dict(BASE, condition = 'the Librarian has started the calculation.',
               qualifier = 'within 3 seconds')
    assert say(dict(doc, condition_kind = 'logic')) == \
        'If the Librarian has started the calculation, the Library_System shall display the Item_Statistics within 3 seconds.'
    assert say(dict(doc, condition_kind = 'event')).startswith('As soon as the Librarian')
    assert say(dict(doc, condition_kind = 'time')).startswith('As long as the Librarian')
    assert say(dict(BASE, object = '  the   Item_Statistics. ')) == \
        'The Library_System shall display the Item_Statistics.'


def test_slots_that_do_not_compose_are_refused():
    say = cc_public.requirement.statement
    with pytest.raises(cc_public.requirement.ErrorSlot):
        say(dict(BASE, activity = 'interaction'))
    with pytest.raises(cc_public.requirement.ErrorSlot):
        say(dict(BASE, actor = 'Librarian'))
    with pytest.raises(cc_public.requirement.ErrorSlot):
        say(dict(BASE, condition = 'the item is reserved'))
    with pytest.raises(cc_public.requirement.ErrorSlot):
        say(dict(BASE, condition_kind = 'logic'))


def test_compose_puts_the_statement_before_the_slots_and_leaves_other_documents_alone():
    fill = cc_public.requirement.compose
    doc = {'id_self': 'req_x', 'title': 'Statistics shown',
           **{k: v for (k, v) in BASE.items() if k != 'id_self'}, 'rationale': 'Why.'}
    out = fill(doc)
    assert list(out)[:3] == ['id_self', 'title', 'statement']
    assert out['statement'] == 'The Library_System shall display the Item_Statistics.\n'
    assert 'statement' not in doc
    assert fill(dict(doc, id_self = 'crq_x.y'))['statement'].startswith('The Library_System')
    assert fill({'id_self': 'need_x', 'entity': 'A'}) == {'id_self': 'need_x', 'entity': 'A'}
    assert fill(dict(doc, statement = 'kept')) ['statement'] == 'kept'
    broken = dict(doc, activity = 'interaction')
    assert fill(broken) is broken
    assert not cc_public.requirement.is_requirement(dict(BASE, process = ''))


def test_a_requirement_shows_its_composed_statement_to_a_judge(tree, tmp_path):
    doc = cc_public.load.from_file(tmp_path / 'requirement' / 'req_executor_honours_budget.yaml')
    assert 'statement' not in doc and doc['claim'] == 'design'
    rendered = cc_public.eval.select.render((('req_executor_honours_budget', doc),),
                                            {'scope': {'include': ['statement']}})
    assert 'statement:' in rendered
    assert 'As long as the Execution runs, the Executor shall run each Node' in rendered


def test_the_evidence_digest_follows_the_slots(tree):
    guid   = tree.resolve('req_executor_honours_budget').guid_self
    before = cc_public.check.evidence.digest(tree.context.map_document, guid)
    cc_public.edit.field.set_field(tree, 'req_executor_honours_budget', 'object', value = 'each Edge')
    after  = cc_public.check.evidence.digest(tree.context.map_document, guid)
    assert before != after
