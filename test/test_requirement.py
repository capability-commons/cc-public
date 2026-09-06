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

import cc_public.check
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


def _found(tmp_path):
    report = cc_public.check.check(list_path = [tmp_path])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'requirement']
    return found


def test_the_requirement_check_reads_every_requirement_and_candidate_and_passes(tree, tmp_path):
    found = _found(tmp_path)
    assert found['count_item'] >= 17 and found['nonconformity'] == []


def test_an_undefined_process_word_is_advisory_while_proposed_and_critical_once_accepted(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'process', value = 'enumerate')
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'status', value = 'proposed')
    (fault,) = _found(tmp_path)['nonconformity']
    assert fault['severity'] == 'advisory' and 'enumerate' in fault['message']
    assert fault['filepath'].endswith('req_walk_reports_neighbourhood.yaml') and fault['path'] == ''
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'status', value = 'accepted')
    (fault,) = _found(tmp_path)['nonconformity']
    assert fault['severity'] == 'critical'


def test_slots_that_do_not_compose_are_critical(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'activity', value = 'interaction')
    (fault,) = _found(tmp_path)['nonconformity']
    assert fault['severity'] == 'critical' and 'actor' in fault['message']


def test_a_process_word_is_seen_from_its_own_segment_and_its_consumers_only(tree, tmp_path):
    import cc_public.edit.insert
    import cc_public.edit.link
    import cc_public.edit.new
    # An inner segment beneath the core, consuming it, with a register of its own.
    cc_public.edit.new.new(tree, 't_segment', 'seg_inner', tree.defaults(),
                           dirpath_out = tmp_path / 'sub' / 'segment')
    for (field, value) in (('title', 'An inner segment'), ('role', 'segment')):
        cc_public.edit.field.set_field(tree, 'seg_inner', field, value = value)
    for (field, value) in (('brief', 'A segment beneath the core.'), ('description', 'Holds a register.')):
        cc_public.edit.field.set_field(tree, 'seg_inner', field, prose = value)
    cc_public.edit.link.link(tree, 'seg_inner', 'r_consumes', 'seg_cc_public')
    cc_public.edit.new.new(tree, 't_register', 'reg_process_word_inner', tree.defaults(),
                           dirpath_out = tmp_path / 'sub' / 'register')
    for (field, value) in (('title', 'Inner verbs'), ('status', 'draft')):
        cc_public.edit.field.set_field(tree, 'reg_process_word_inner', field, value = value)
    for field in ('brief', 'description'):
        cc_public.edit.field.set_field(tree, 'reg_process_word_inner', field, prose = 'The inner verbs.')
    cc_public.edit.link.link(tree, 'reg_process_word_inner', 'r_is_specified_by_schema', 'sch_reg_process_word')
    cc_public.edit.insert.insert(tree, 't_process_word', 'enumerate', 'reg_process_word_inner')
    for (field, value) in (('title', 'Enumerate'), ('term', 'enumerate'), ('status', 'proposed')):
        cc_public.edit.field.set_field(tree, 'verb_enumerate', field, value = value)
    cc_public.edit.field.set_field(tree, 'verb_enumerate', 'brief', prose = 'Count through a set.')
    cc_public.edit.field.set_field(tree, 'verb_enumerate', 'description', prose = 'The object names the set.')
    # A core requirement cannot see it; one of the inner segment can.
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'process', value = 'enumerate')
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'status', value = 'proposed')
    (fault,) = _found(tmp_path)['nonconformity']
    assert 'enumerate' in fault['message'] and fault['filepath'].endswith('req_walk_reports_neighbourhood.yaml')
    cc_public.edit.field.set_field(tree, 'req_walk_reports_neighbourhood', 'process', value = 'report')
    cc_public.edit.new.new(tree, 't_textual_requirement', 'req_inner_counts', tree.defaults(),
                           dirpath_out = tmp_path / 'sub' / 'requirement')
    for (field, value) in (('title', 'Inner counts'), ('entity', 'Counter'), ('obligation', 'shall'),
                           ('activity', 'autonomous'), ('process', 'enumerate'), ('object', 'each Item'),
                           ('claim', 'design'), ('category', 'function'), ('status', 'proposed')):
        cc_public.edit.field.set_field(tree, 'req_inner_counts', field, value = value)
    cc_public.edit.field.set_field(tree, 'req_inner_counts', 'rationale', prose = 'A verb of its own.')
    cc_public.edit.link.link(tree, 'req_inner_counts', 'r_is_derived_from', 'need_runs_bounded')
    assert _found(tmp_path)['nonconformity'] == []
