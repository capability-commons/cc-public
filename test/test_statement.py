"""
---

id_self:                pym_test.test_statement
guid_self:              pym_8a97aac9c2134070a11419ab9072ef60
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Statement check tests
brief:                  |
                        Tests of the statement check: units, bounds,
                        acronyms, weak verbs, light verbs and
                        nominalisations.
description:            |
                        These tests write requirements with each
                        defect and check that the statement check
                        reports each defect once, by the rule it
                        names. A well formed statement earns no
                        finding.
relation:               []

...
"""


import cc_public.check
import cc_public.check.statement
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new


ID = 'req_probe_statement'


def _make(tree, **slot):
    fields = {'title': 'A probe', 'entity': 'Probe', 'obligation': 'shall', 'activity': 'autonomous',
              'process': 'report', 'object': 'the Result', 'claim': 'design', 'category': 'function',
              'status': 'proposed', **slot}
    if ID not in tree.map_id:
        cc_public.edit.new.new(tree, 't_textual_requirement', ID, tree.defaults())
        cc_public.edit.field.set_field(tree, ID, 'rationale', prose = 'A probe.')
        cc_public.edit.link.link(tree, ID, 'r_is_derived_from', 'need_runs_bounded')
    for (key, value) in fields.items():
        cc_public.edit.field.set_field(tree, ID, key, value = value)
    for key in ('qualifier', 'condition', 'condition_kind', 'actor'):
        if key not in fields and key in tree.context.map_document[tree.resolve(ID).location]:
            cc_public.edit.field.unset_field(tree, ID, key)


def _messages(tmp_path):
    report = cc_public.check.check(list_path = [tmp_path])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'statement']
    return [n['message'] for n in found['nonconformity'] if ID in n['filepath']]


def test_a_well_formed_statement_earns_nothing(tree, tmp_path):
    _make(tree, object = 'the Location of each Nonconformity', qualifier = 'within 2 s of the request')
    assert _messages(tmp_path) == []


def test_a_number_with_no_unit_is_reported_and_a_count_is_not(tree, tmp_path):
    _make(tree, object = 'the Mass of the Crate', qualifier = 'to no more than 40')
    (m,) = _messages(tmp_path)
    assert 'number 40 is followed by no unit' in m and 'rule_r06_common_units' in m
    _make(tree, object = 'each Item to two people')
    assert _messages(tmp_path) == []


def test_a_point_value_with_a_unit_asks_for_its_bound(tree, tmp_path):
    _make(tree, object = 'the Crate at 40 kg')
    (m,) = _messages(tmp_path)
    assert '40 kg is a point value' in m and 'rule_r33_range_of_values' in m
    _make(tree, object = 'the Crate at no more than 40 kg')
    assert _messages(tmp_path) == []
    _make(tree, object = 'the Crate at 10 000 kilograms or less')
    assert _messages(tmp_path) == []


def test_an_unknown_unit_and_an_unknown_acronym_are_questions(tree, tmp_path):
    _make(tree, object = 'the Flow at no more than 3 m/min through the GPS Port')
    messages = _messages(tmp_path)
    assert any('m/min reads as a unit' in m for m in messages)
    assert any('acronym GPS is not defined' in m and 'rule_r37_acronyms' in m for m in messages)
    _make(tree, object = 'the Flow at no more than 3 m/s through the Port')   # a defined unit, no acronym
    assert _messages(tmp_path) == []


def test_a_weak_verb_a_light_verb_and_a_nominalisation_ask_what_the_entity_does(tree, tmp_path):
    cc_public.edit.insert.insert(tree, 't_process_word', 'support', 'reg_process_word')
    for (field, value) in (('title', 'Support'), ('term', 'support'), ('kind', 'management'),
                           ('status', 'proposed')):
        cc_public.edit.field.set_field(tree, 'verb_support', field, value = value)
    cc_public.edit.field.set_field(tree, 'verb_support', 'brief', prose = 'Assist something, vaguely.')
    cc_public.edit.field.set_field(tree, 'verb_support', 'description', prose = 'Which task?')
    _make(tree, process = 'support', object = 'the Operator')
    (m,) = _messages(tmp_path)
    assert 'support names a management' in m and 'rule_s02_main_verb' in m
    _make(tree, process = 'perform', object = 'the Judgement of each Case')
    messages = _messages(tmp_path)
    assert any('perform is a light verb' in m and 'rule_s04_light_verb' in m for m in messages)
    assert any('opens with judgement, a noun standing for the process judge' in m for m in messages)
    _make(tree, process = 'report', object = 'the Judgement of each Case')
    (m,) = _messages(tmp_path)
    assert 'rule_s03_nominalisation' in m
    _make(tree, process = 'report', object = 'the Location of each Nonconformity')   # not a defined verb's noun
    assert _messages(tmp_path) == []


def test_a_number_glued_to_letters_or_over_a_slash_is_not_a_quantity(tree, tmp_path):
    _make(tree, object = 'the 3D Position of each Track to MIL-STD-461G and IEC 62133-2 over a 24-hour period, 24/7')
    assert _messages(tmp_path) == []


def test_an_accepted_requirement_makes_the_finding_critical(tree, tmp_path):
    _make(tree, object = 'the Crate at 40 kg', status = 'accepted')
    report = cc_public.check.check(list_path = [tmp_path])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'statement']
    (n,) = [n for n in found['nonconformity'] if ID in n['filepath']]
    assert n['severity'] == 'critical'
