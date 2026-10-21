"""
---

id_self:                pym_cc_public.check._test.test_check
guid_self:              pym_fa0c3da481904525a0476ca6420e4c83
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Checker tests
brief:                  |
                        Tests that each check passes a sound tree and
                        reports the one fault put into a copy of it.
description:            |
                        Each test copies the repository's data items,
                        adds or breaks one thing, and asks for every
                        failure. A test of a fault expects that fault
                        and nothing else, so a check that fires where
                        it should not is caught as surely as one that
                        stays silent.
relation:               []

...
"""


import io
import pathlib
import re
import uuid

import click.testing
import pytest
import ruamel.yaml

import cc_public.check.check
import cc_public.cli.command
import cc_public.commit.change
import cc_public.graph.logic
import cc_public.graph.extract
from cc_public.conftest import DIR_REPO


ID_ABOUT     = 'concern_safety'
ID_SUBJECT   = 'lco_x'
FILE_SUBJECT = '_data/logical_component/lco_x.yaml'
DIR_DECISION = '_data/decision/dec_x/'
REGEX_ANN    = '^ann_[a-z][a-z0-9_]*$'

# The widest forms of an id and a guid, from sch_primitive.
#
REGEX_ID     = '^[a-z]{1,8}_[a-z0-9][a-z0-9_]*(\\.[a-z0-9_][a-z0-9_]*)*$'
REGEX_GUID   = '^[a-z]{1,8}_[0-9a-f]{32}$'

# An item written by _item has id_self on its first line, description
# on its tenth, and the id_target of its first edge on its fourteenth.
#
LINE_ITEM        = '1'
LINE_DESCRIPTION = '10'
LINE_TARGET      = '14'


# -----------------------------------------------------------------------------
def _guid(prefix):
    """
    Return a new guid with prefix.

    """

    return '{prefix}_{hex}'.format(prefix = prefix, hex = uuid.uuid4().hex)


# -----------------------------------------------------------------------------
def _guid_of(root, id_self):
    """
    Return the guid of the item in the tree under root with id_self.
    The guid is read from the text, which is quicker than extracting
    every fact of the tree.

    """

    regex = re.compile(r'id_self:\s+{id}\n\s*guid_self:\s+(\S+)'.format(id = re.escape(id_self)))

    for path in sorted((root / '_data').rglob('*.yaml')):
        match = regex.search(path.read_text())
        if match:
            return match.group(1)

    raise KeyError(id_self)


# -----------------------------------------------------------------------------
def _line(root, relative, text):
    """
    Return the number of the line of the file at relative that is text.

    """

    list_line = (root / relative).read_text().splitlines()
    return str(list_line.index(text) + 1)


# -----------------------------------------------------------------------------
def _edge(root, id_relation, id_target):
    """
    Return an edge to id_target, carrying the guids the tree gives.

    """

    return {'id_relation':   id_relation,
            'guid_relation': _guid_of(root, id_relation),
            'id_target':     id_target,
            'guid_target':   _guid_of(root, id_target)}


# -----------------------------------------------------------------------------
def _item(root, relative, id_self, list_edge = (), guid = None):
    """
    Write an item to the file at relative, and return its location.

    """

    path = root / relative
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(_dump(_fields(root, id_self, list_edge, guid)))
    return relative


# -----------------------------------------------------------------------------
def _subject(root):
    """
    Write ID_SUBJECT, a logical component with no drivers, if it is not
    there yet, and return an edge to it for a decision to be about.

    """

    if not (root / FILE_SUBJECT).exists():
        _item(root, FILE_SUBJECT, ID_SUBJECT)
    return _edge(root, 'r_is_about', ID_SUBJECT)


# -----------------------------------------------------------------------------
def _option(root, id_self, list_edge = (), guid = None):
    """
    Write an option that answers dec_x, in the folder of dec_x, and
    return its location. dec_x is written too, about ID_SUBJECT, if it
    is not there yet.

    """

    if not (root / DIR_DECISION / 'dec_x.yaml').exists():
        _item(root, DIR_DECISION + 'dec_x.yaml', 'dec_x', [_subject(root)])
    return _item(root, DIR_DECISION + id_self + '.yaml', id_self,
                 [_edge(root, 'r_is_option_for', 'dec_x'), *list_edge], guid)


# -----------------------------------------------------------------------------
def _fields(root, id_self, list_edge = (), guid = None):
    """
    Return the fields of an item with id_self that its schema accepts.

    """

    return {'id_self':         id_self,
            'guid_self':       guid or _guid(id_self.split('_')[0]),
            'copyright':       'Copyright 2026 William Payne',
            'license':         'Apache-2.0',
            'protective_mark': [{'id_mark':   'mark_public',
                                 'guid_mark': _guid_of(root, 'mark_public')}],
            'title':           'Test item',
            'brief':           'A test item.',
            'description':     'A test item.',
            'relation':        list(list_edge)}


# -----------------------------------------------------------------------------
def _dump(data):
    """
    Return data as YAML text.

    """

    stream = io.StringIO()
    ruamel.yaml.YAML().dump(data, stream)
    return stream.getvalue()


# -----------------------------------------------------------------------------
def _module(root, relative, id_self):
    """
    Write a python module whose docstring holds an item with id_self.

    """

    path = root / relative
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text('"""\n---\n{item}...\n"""\n'.format(item = _dump(_fields(root, id_self))))


# -----------------------------------------------------------------------------
def _program(root, relative, id_self):
    """
    Write a logic program file whose comment header holds an item
    with id_self.

    """

    item = _dump(_fields(root, id_self))
    path = root / relative
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text('% ---\n' + ''.join('% ' + line for line in item.splitlines(True))
                    + '% ...\n')


# -----------------------------------------------------------------------------
def _check(root):
    """
    Return the failures of the tree under root, less those of layout.
    The items these tests write are not laid out, and the tests of
    pym_cc_public.edit.layout cover layout.

    """

    failures = cc_public.check.check.check(root)
    failures.pop(cc_public.check.check.NAME_LAYOUT, None)
    return failures


# -----------------------------------------------------------------------------
def _replace(root, relative, old, new):
    """
    Replace the first old with new in the file at relative.

    """

    path = root / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new, 1))


@pytest.mark.slow
def test_the_repository_passes_every_check():
    assert cc_public.check.check.check(DIR_REPO) == {}


def test_checks_that_cannot_run_exit_with_an_error(tree, tmp_path, monkeypatch):
    path = tmp_path / 'check.lp'
    path.write_text('% decl o(x)\n#show o/1.\no(X) :- itme(X, _, _, _, _).\n')
    monkeypatch.setattr(cc_public.check.check, 'RULES', path)
    result = click.testing.CliRunner().invoke(cc_public.cli.command.main,
                                              ['check', '--root', str(tree)])
    assert result.exit_code == 2
    assert result.stderr.startswith('The checks could not be run:')
    assert 'does not occur in any rule head' in result.stderr


def test_a_schema_ref_to_no_schema_is_reported(tree):
    _replace(tree, '_data/schema/sch_annotation.yaml', 'sch_standalone.yaml', 'sch_missing.yaml')
    assert _check(tree) == {'schema_violation': [(
        'sch_annotation', 'sch_annotation', '_data/schema/sch_annotation.yaml', '1', '$ref',
        'The $ref https://capability-commons.org/schema/sch_missing.yaml names no schema, '
        'so nothing is validated against sch_annotation.')]}


def test_a_pattern_end_matches_only_at_the_end_of_the_text():
    validator = cc_public.check.schema.Validator({'type': 'string', 'pattern': '^[^\\n]+$'})
    assert validator.is_valid('A title')
    assert not validator.is_valid('A title\n')
    assert cc_public.check.schema.ecma('^a[$]\\$b$') == '^a[$]\\$b\\Z'


def test_a_title_that_ends_in_a_newline_is_reported(tree):
    _option(tree, 'opt_x')
    _replace(tree, DIR_DECISION + 'opt_x.yaml', 'title: Test item', 'title: "Test item\\n"')
    failures = _check(tree)
    assert list(failures) == ['schema_violation']
    assert [row[4] for row in failures['schema_violation']] == ['title']


def test_a_document_with_a_repeated_key_is_reported(tree):
    (tree / '_data/annotation').mkdir(exist_ok = True)
    (tree / '_data/annotation/ann_x.yaml').write_text('title: one\ntitle: two\n')
    failures = _check(tree)
    assert list(failures) == ['unreadable_file']
    [(file, line, message)] = failures['unreadable_file']
    assert (file, line) == ('_data/annotation/ann_x.yaml', '2')
    assert 'duplicate key "title"' in message


def test_a_module_that_is_not_python_is_reported(tree):
    (tree / 'src/cc_public/broken.py').write_text('\n\ndef (:\n')
    failures = _check(tree)
    [(file, line, message)] = failures.pop('unreadable_file')
    assert (file, line) == ('src/cc_public/broken.py', '3')
    assert message.startswith('The module is not python')
    assert list(failures) == ['unrecorded_module']


def test_an_annotation_and_an_option_about_an_item_pass(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', 'opt_x'),
                                                         _edge(tree, 'r_speaks_for_concern', ID_ABOUT)])
    assert _check(tree) == {}


def test_an_annotation_about_nothing_is_reported(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x')
    assert _check(tree) == {'missing_about': [('ann_x',)]}


def test_an_option_that_answers_no_decision_is_reported(tree):
    _item(tree, '_data/option/opt_x.yaml', 'opt_x')
    assert _check(tree) == {'option_count': [('opt_x', '0')]}


def test_a_decision_about_nothing_is_reported(tree):
    _item(tree, DIR_DECISION + 'dec_x.yaml', 'dec_x')
    assert _check(tree) == {'missing_about': [('dec_x',)]}


def test_an_option_outside_the_folder_of_its_decision_is_reported(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/option/opt_y.yaml', 'opt_y', [_edge(tree, 'r_is_option_for', 'dec_x')])
    assert _check(tree) == {'misplaced_document': [
        ('opt_y', '_data/option/opt_y.yaml', DIR_DECISION + 'opt_y.yaml')]}


def test_an_annotation_about_a_decision_is_kept_in_its_folder(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'dec_x')])
    assert _check(tree) == {'misplaced_document': [
        ('ann_x', '_data/annotation/ann_x.yaml', DIR_DECISION + 'ann_x.yaml')]}


def test_a_ruling_that_upholds_an_option_passes(tree):
    _option(tree, 'opt_x')
    _option(tree, 'opt_y')
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x'),
                                                    _edge(tree, 'r_rejects', 'opt_y')])
    assert _check(tree) == {}


def test_a_decision_about_other_than_a_component_is_reported(tree):
    _item(tree, DIR_DECISION + 'dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    failures = _check(tree)
    assert failures['decision_about_non_component'] == [('dec_x', ID_ABOUT, 'type_concern')]


def test_an_argument_across_two_decisions_is_reported(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/decision/dec_y/dec_y.yaml', 'dec_y', [_subject(tree)])
    _item(tree, '_data/decision/dec_y/opt_y.yaml', 'opt_y', [_edge(tree, 'r_is_option_for', 'dec_y')])
    _item(tree, '_data/decision/dec_y/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'dec_y'),
                                                          _edge(tree, 'r_challenges', 'opt_x')])
    failures = _check(tree)
    assert failures['argument_across_decisions'] == [('ann_x', 'dec_y', 'opt_x', 'dec_x')]


def test_a_decision_no_option_answers_is_advice(tree):
    _item(tree, DIR_DECISION + 'dec_x.yaml', 'dec_x', [_subject(tree)])
    (failures, advice) = cc_public.check.check.review(tree)
    failures.pop('unformatted_file', None)
    assert failures == {}
    assert advice == {'decision_without_options': [('dec_x',)]}


def test_a_ruling_across_two_decisions_is_reported(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/decision/dec_y/dec_y.yaml', 'dec_y', [_subject(tree)])
    _item(tree, '_data/decision/dec_y/opt_y.yaml', 'opt_y', [_edge(tree, 'r_is_option_for', 'dec_y')])
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x'),
                                                    _edge(tree, 'r_rejects', 'opt_y')])
    failures = _check(tree)
    assert failures['decisions_mixed_in_ruling'] == [('ruling_x', 'dec_x', 'dec_y')]


def test_two_rulings_of_a_decision_are_reported(tree):
    _option(tree, 'opt_x')
    _option(tree, 'opt_y')
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    _item(tree, DIR_DECISION + 'ruling_y.yaml', 'ruling_y', [_edge(tree, 'r_upholds', 'opt_y')])
    assert _check(tree) == {'competing_rulings': [('dec_x', 'ruling_x', 'ruling_y')]}


def test_an_option_that_supersedes_a_ruling_is_reported(tree):
    _option(tree, 'opt_x')
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    _option(tree, 'opt_y', [_edge(tree, 'r_supersedes', 'ruling_x')])
    assert _check(tree)['supersession_across_types'] == [('opt_y', 'ruling_x')]


def test_a_ruling_that_supersedes_is_reported(tree):
    _option(tree, 'opt_x')
    _option(tree, 'opt_y')
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    _item(tree, DIR_DECISION + 'ruling_y.yaml', 'ruling_y',
          [_edge(tree, 'r_upholds', 'opt_y'), _edge(tree, 'r_supersedes', 'ruling_x')])
    assert ('ruling_y', 'r_supersedes', 'ruling_x', 'source', 'rrs_is_supersedable') \
        in _check(tree)['restriction_violation']


def test_a_copy_of_an_item_is_reported(tree):
    path = tree / '_data/logical_component/lco_tooling.yaml'
    (tree / '_data/logical_component/lco_tooling_copy.yaml').write_text(path.read_text())
    assert _check(tree)['repeated_item'] == [
        ('lco_tooling', '_data/logical_component/lco_tooling.yaml', '1'),
        ('lco_tooling', '_data/logical_component/lco_tooling_copy.yaml', '1')]


def test_a_ruling_of_nothing_is_reported(tree):
    _item(tree, '_data/ruling/ruling_x.yaml', 'ruling_x')
    assert _check(tree) == {'no_option_in_ruling': [('ruling_x',)]}


def _driven_options(tree):
    """
    Write lco_x, driven by concern_cost, a decision about it, and two
    options that answer the decision.

    """

    _item(tree, '_data/logical_component/lco_x.yaml', 'lco_x',
          [_edge(tree, 'r_is_driven_by', 'concern_cost')])
    _item(tree, DIR_DECISION + 'dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', 'lco_x')])
    _option(tree, 'opt_x')
    _option(tree, 'opt_y')


def test_a_ruling_with_a_driver_unargued_is_reported(tree):
    _driven_options(tree)
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    assert _check(tree) == {'unargued_driver': [('ruling_x', 'opt_x', 'concern_cost')]}


def test_a_rejection_with_a_driver_unargued_passes(tree):
    _driven_options(tree)
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_rejects', 'opt_x')])
    assert _check(tree) == {}


def test_a_driver_argued_only_in_another_decision_is_unargued(tree):
    _driven_options(tree)
    _item(tree, '_data/decision/dec_y/dec_y.yaml', 'dec_y', [_edge(tree, 'r_is_about', 'lco_x')])
    _item(tree, '_data/decision/dec_y/opt_z.yaml', 'opt_z', [_edge(tree, 'r_is_option_for', 'dec_y')])
    _item(tree, '_data/decision/dec_y/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'dec_y'),
                                                          _edge(tree, 'r_challenges', 'opt_z'),
                                                          _edge(tree, 'r_speaks_for_concern',
                                                                'concern_cost')])
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    assert _check(tree) == {'unargued_driver': [('ruling_x', 'opt_x', 'concern_cost')]}


def test_a_driver_argued_for_an_alternative_passes(tree):
    _driven_options(tree)
    _item(tree, DIR_DECISION + 'ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'dec_x'),
                                                    _edge(tree, 'r_challenges', 'opt_y'),
                                                    _edge(tree, 'r_speaks_for_concern',
                                                          'concern_cost')])
    _item(tree, DIR_DECISION + 'ruling_x.yaml', 'ruling_x', [_edge(tree, 'r_upholds', 'opt_x')])
    assert _check(tree) == {}


def test_an_open_option_with_a_driver_unargued_passes(tree):
    _driven_options(tree)
    assert _check(tree) == {}


def test_an_id_with_no_known_prefix_is_reported(tree):
    location = _item(tree, '_data/x/xyz_x.yaml', 'xyz_x')
    assert _check(tree) == {'unknown_prefix': [('xyz_x', location, LINE_ITEM)]}


def test_an_id_against_the_pattern_of_its_type_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_X.yaml', 'ann_X',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    assert _check(tree) == {
        'bad_id':           [('ann_X', REGEX_ANN, location, LINE_ITEM)],
        'schema_violation': [('ann_X', 'sch_annotation', location, LINE_ITEM, 'id_self',
                              "'ann_X' does not match " + repr(REGEX_ID))]}


def test_a_malformed_guid_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)], guid = 'ann_123')
    assert _check(tree) == {
        'bad_guid':         [('ann_x', 'ann_123', location, LINE_ITEM)],
        'schema_violation': [('ann_x', 'sch_annotation', location, '2', 'guid_self',
                              "'ann_123' does not match " + repr(REGEX_GUID))]}


def test_two_types_sharing_a_prefix_are_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'prefix:             opt\n', 'prefix:             ann\n')
    assert _check(tree)['duplicate_prefix'] == [('ann', 'type_annotation', 'type_option'),
                                                ('ann', 'type_option', 'type_annotation')]


def test_a_prefix_neither_three_letters_nor_a_word_of_its_term_is_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'prefix:             opt\n', 'prefix:             op\n')
    assert _check(tree)['prefix_form'] == [('type_option', 'op')]


def test_a_prefix_that_is_a_word_of_its_preferred_term_passes(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'prefix:             opt\n', 'prefix:             option\n')
    assert 'prefix_form' not in _check(tree)


def test_two_prefixes_one_letter_apart_are_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'prefix:             opt\n', 'prefix:             ant\n')
    assert _check(tree)['prefix_near'] == [('type_annotation', 'ann', 'type_option', 'ant'),
                                           ('type_option', 'ant', 'type_annotation', 'ann')]


def test_two_prefixes_one_letter_apart_in_one_family_pass(tree):
    assert not any(row[1] in ('icd', 'icm') for row in _check(tree).get('prefix_near', []))


def test_an_id_given_to_two_items_is_reported(tree):
    list_edge = [_edge(tree, 'r_is_about', ID_ABOUT)]
    (one, two) = (_guid('ann'), _guid('ann'))
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = one)
    _item(tree, 'src/x/_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = two)
    assert _check(tree) == {'duplicate_id': sorted([('ann_x', one, two),
                                                         ('ann_x', two, one)])}


def test_a_guid_given_to_two_items_is_reported(tree):
    list_edge = [_edge(tree, 'r_is_about', ID_ABOUT)]
    guid      = _guid('ann')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = guid)
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', list_edge, guid = guid)
    assert _check(tree) == {'duplicate_guid': [(guid, 'ann_x', 'ann_y'),
                                                    (guid, 'ann_y', 'ann_x')]}


def test_an_entry_held_under_another_key_is_reported(tree):
    _replace(tree, '_data/register/reg_concern.yaml',
             '  concern_security:\n', '  concern_secure:\n')
    assert _check(tree) == {'key_mismatch': [('reg_concern',
                                                   'concern_secure',
                                                   'concern_security')]}


def test_a_reference_to_nothing_is_reported(tree):
    edge = {'id_relation':   'r_is_about',
            'guid_relation': _guid_of(tree, 'r_is_about'),
            'id_target':     'concern_absent',
            'guid_target':   _guid('concern')}
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert _check(tree) == {'dangling_reference': [('ann_x', 'target', 'concern_absent',
                                                         location, LINE_TARGET)]}


def test_a_reference_by_an_old_id_is_resolved_by_its_guid(tree):
    edge = dict(_edge(tree, 'r_is_about', ID_ABOUT), id_target = 'concern_old')
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert _check(tree) == {'outdated_reference': [('ann_x', 'target', 'concern_old', ID_ABOUT,
                                                         location, LINE_TARGET)]}


def test_a_mark_held_nowhere_here_is_advice_not_a_failure(tree):
    path = tree / '_data/annotation/ann_x.yaml'
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    guid = _guid('mark')
    path.write_text(path.read_text().replace(
        _guid_of(tree, 'mark_public'), guid).replace('mark_public', 'mark_partner'))
    (failures, advice) = cc_public.check.check.review(tree)
    failures.pop('unformatted_file', None)
    assert failures == {}
    assert [row[:3] for row in advice['unresolved_mark']] == [('ann_x', 'mark_partner', guid)]


def test_a_reference_with_a_stale_guid_is_reported(tree):
    edge = dict(_edge(tree, 'r_is_about', ID_ABOUT), guid_target = _guid('concern'))
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert _check(tree) == {'guid_mismatch': [('ann_x', 'target', ID_ABOUT,
                                                 edge['guid_target'], location, LINE_TARGET)]}


def test_an_edge_from_a_source_its_relation_restricts_is_reported(tree):
    # Support runs from an argument. An option gives no reasons.
    _option(tree, 'opt_x')
    _option(tree, 'opt_y', [_edge(tree, 'r_supports', 'opt_x')])
    assert _check(tree) == {'restriction_violation': [
        ('opt_y', 'r_supports', 'opt_x', 'source', 'rrs_is_argument')]}


def test_an_edge_to_a_target_its_relation_restricts_is_reported(tree):
    # Support runs to something arguable, not to a concern.
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', ID_ABOUT)])
    assert _check(tree) == {'restriction_violation': [
        ('ann_x', 'r_supports', ID_ABOUT, 'target', 'rrs_can_be_target_of_an_argument')]}


def test_a_requirement_whose_subject_is_no_design_element_is_reported(tree):
    # The subject of a requirement must play rol_design_element, which a
    # concern does not.
    _replace(tree, '_data/requirement/rqt_rename_keeps_guid.yaml',
             'id_target:          lco_tooling\n'
             '    guid_target:        ' + _guid_of(tree, 'lco_tooling') + '\n',
             'id_target:          concern_cost\n'
             '    guid_target:        ' + _guid_of(tree, 'concern_cost') + '\n')
    assert _check(tree) == {'restriction_violation': [
        ('rqt_rename_keeps_guid', 'r_has_subject', 'concern_cost', 'target',
         'rrs_is_design_element')]}


def test_a_restriction_that_excludes_a_role_passes_only_types_without_it(tree):
    # With its literal turned to an exclude, the restriction on the source
    # of r_has_subject passes an annotation and fails every requirement.
    literal = ('id_relation:    {relation}\n'
               '        guid_relation:  {guid}\n'
               '        id_target:      rol_requirement\n')
    _replace(tree, '_data/register/reg_relation_restriction.yaml',
             literal.format(relation = 'r_admits', guid = _guid_of(tree, 'r_admits')),
             literal.format(relation = 'r_excludes', guid = _guid_of(tree, 'r_excludes')))
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_has_subject', 'lco_tooling')])
    failures = _check(tree)
    assert list(failures) == ['restriction_violation']
    assert {row[0] for row in failures['restriction_violation']} == {
        'rqt_edit_refuses_new_failure', 'rqt_format_keeps_formatted_file', 'rqt_rename_keeps_guid'}
    assert {row[3:] for row in failures['restriction_violation']} == {
        ('source', 'rrs_is_requirement')}


def test_an_edge_recorded_through_an_inverse_is_read_in_reverse(tree):
    # opt_x records that it is the subject of ann_x, which is ann_x
    # being about opt_x, so ann_x is about something.
    path     = tree / '_data/register/reg_relation.yaml'
    register = ruamel.yaml.YAML().load(path.read_text())
    register['table']['r_is_about']['inverse'] = {'id_self':   'r_is_subject_of',
                                                  'guid_self': _guid('r'),
                                                  'brief':     'SOURCE is the subject of TARGET'}
    path.write_text(_dump(register))
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x')
    _option(tree, 'opt_x', [_edge(tree, 'r_is_subject_of', 'ann_x')])
    assert _check(tree) == {}


def test_a_module_named_for_its_place_passes(tree):
    _module(tree, 'src/x/_test/test_y.py', 'pym_x._test.test_y')
    assert _check(tree) == {}


def test_a_module_named_for_another_place_is_reported(tree):
    _module(tree, 'src/x/y.py', 'pym_x.z')
    assert _check(tree) == {'misplaced_module': [('pym_x.z', 'pym_x.y')]}


def _definitions(root, relative, id_class, id_method):
    """
    Write a python module with a class whose docstring holds an item
    with id_class, and a method of it whose docstring holds one with
    id_method.

    """

    def docstring(id_self, indent):
        item = _dump(_fields(root, id_self))
        return ''.join(indent + line if line.strip() else line for line in
                       ('"""\n---\n' + item + '...\n"""\n').splitlines(True))

    _module(root, relative, 'pym_x.y')
    with (root / relative).open('a') as file:
        file.write('\n\nclass Thing:\n' + docstring(id_class, '    ')
                   + '\n    def run(self):\n' + docstring(id_method, '        ')
                   + '        return 1\n')


def _interface(root, id_function, surface = None, stated = None, returns = None):
    """
    Write the interface control document icd_x, with a python surface
    that holds one function member, id_function, with one parameter,
    and return the path of its file. surface, if given, takes the
    place of the python surface. stated, if given, adds its fields to
    the parameter, and returns, if given, is the spelling of the type
    the function returns.

    """

    function = {'id_self':   id_function,
                'guid_self': _guid('icm'),
                'name':      'run',
                'brief':     'Run it.',
                'parameter': [{'id_self':   id_function + '.root',
                               'guid_self': _guid('icm'),
                               'name':      'root',
                               'brief':     'Where to run it.',
                               **(stated or {})}]}
    if returns is not None:
        function['returns'] = {'type': {'spelling': returns}, 'brief': 'What it found.'}
    document = _fields(root, 'icd_x')
    document.update({'version_interface': '1.0',
                     'surface':           surface or {'python': {'native': {
                                                'language': 'python',
                                                'function': {'run': function}}}}})
    return _item_document(root, '_data/interface_control_document/icd_x.yaml', document)


# -----------------------------------------------------------------------------
def _item_document(root, relative, document):
    """
    Write document to the file at relative, and return its location.

    """

    path = root / relative
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(_dump(document))
    return relative


def test_an_interface_control_document_with_its_members_named_for_their_place_passes(tree):
    _interface(tree, 'icm_x.run')
    assert _check(tree) == {}


def test_a_member_named_for_another_place_is_reported(tree):
    _interface(tree, 'icm_y.run')
    assert _check(tree) == {'misnamed_member': [('icm_y.run', 'icd_x')]}


def test_a_member_named_more_than_one_step_below_its_holder_is_reported(tree):
    _interface(tree, 'icm_x.a.run')
    assert _check(tree) == {'misnamed_member': [('icm_x.a.run', 'icd_x')]}


def test_a_surface_of_two_forms_is_reported(tree):
    location = _interface(tree, 'icm_x.run', {'python': {'native':   {'language': 'python'},
                                                         'artifact': {'artifact':   {},
                                                                      'production': 'Daily.'}}})
    failures = _check(tree)
    assert list(failures) == ['schema_violation']
    assert {row[:3] + row[4:5] for row in failures['schema_violation']} == {
        ('icd_x', 'sch_interface_control_document', location, 'surface/python')}


def _realizing(root, list_parameter, returns = None):
    """
    Write a python module with a function whose item realizes the
    member icm_x.run of icd_x, and which takes list_parameter and,
    if returns is given, says it returns that type.

    """

    item = _dump(_fields(root, 'pyf_x.y.run', [_edge(root, 'r_realizes', 'icm_x.run')]))
    _module(root, 'src/x/y.py', 'pym_x.y')
    with (root / 'src/x/y.py').open('a') as file:
        file.write('\n\ndef run({parameter}){returns}:\n'.format(
                       parameter = ', '.join(list_parameter),
                       returns   = '' if returns is None else ' -> ' + returns)
                   + ''.join('    ' + line if line.strip() else line for line in
                             ('"""\n---\n' + item + '...\n"""\n').splitlines(True))
                   + '    return 1\n')


def test_a_function_that_takes_the_parameters_its_member_states_passes(tree):
    _interface(tree, 'icm_x.run')
    _realizing(tree, ['root'])
    assert _check(tree) == {}


def test_a_function_whose_parameters_differ_from_its_member_is_reported(tree):
    _interface(tree, 'icm_x.run')
    _realizing(tree, ['path', 'depth = 1'])
    assert _check(tree) == {'parameter_mismatch': [
        ('icm_x.run', 'pyf_x.y.run', '0', 'root', 'path'),
        ('icm_x.run', 'pyf_x.y.run', '1', '', 'depth')]}


def test_a_parameter_the_function_does_not_take_is_reported(tree):
    _interface(tree, 'icm_x.run')
    _realizing(tree, [])
    assert _check(tree) == {'parameter_mismatch': [('icm_x.run', 'pyf_x.y.run', '0', 'root', '')]}


def test_the_receiver_of_a_method_is_not_a_parameter():
    text = ('class Thing:\n'
            '    def run(self, a, *b, c, **d):\n'
            '        """\n        ---\n        id_self: pyf_x.thing.run\n        ...\n        """\n')
    assert [tuple(name for (name, _) in found[2]) for found in
            cc_public.graph.extract.definitions(text, pathlib.Path('src/x.py'))] == [
           ('a', 'b', 'c', 'd')]


def test_the_parts_of_each_parameter_and_the_return_type_are_read():
    text = ('def run(a: int, b=1, *c: str, d: x.Y | None = None, **e) -> list[int]:\n'
            '    """\n    ---\n    id_self: pyf_x.run\n    ...\n    """\n')
    ((_, _, tuple_parameter, returns, _),) = cc_public.graph.extract.definitions(
                                                text, pathlib.Path('src/x.py'))
    assert returns == 'list[int]'
    assert [(name, map_part['type'], map_part['default'], map_part['optional'],
             map_part['variadic']) for (name, map_part) in tuple_parameter] == [
        ('a', 'int',         '',     'false', 'false'),
        ('b', '',            '1',    'true',  'false'),
        ('c', 'str',         '',     'true',  'true'),
        ('d', 'x.Y | None',  'None', 'true',  'false'),
        ('e', '',            '',     'true',  'true')]


def test_a_signature_the_function_matches_passes(tree):
    _interface(tree, 'icm_x.run',
               stated  = {'type': {'spelling': 'int'}, 'default': '1', 'optional': True},
               returns = 'int')
    _realizing(tree, ['root: int = 1'], returns = 'int')
    assert _check(tree) == {}


def test_a_signature_the_function_does_not_match_is_reported(tree):
    _interface(tree, 'icm_x.run',
               stated  = {'type':     {'spelling': 'int'},
                          'default':  '1',
                          'optional': True,
                          'variadic': True},
               returns = 'int')
    _realizing(tree, ['root: str'], returns = 'list[int]')
    assert _check(tree) == {'signature_mismatch': [
        ('icm_x.run',      'pyf_x.y.run', 'returns',  'int',  'list[int]'),
        ('icm_x.run.root', 'pyf_x.y.run', 'default',  '1',    ''),
        ('icm_x.run.root', 'pyf_x.y.run', 'optional', 'true', 'false'),
        ('icm_x.run.root', 'pyf_x.y.run', 'type',     'int',  'str'),
        ('icm_x.run.root', 'pyf_x.y.run', 'variadic', 'true', 'false')]}


def test_a_part_the_member_does_not_state_is_not_compared(tree):
    _interface(tree, 'icm_x.run')
    _realizing(tree, ['root: int = 1'], returns = 'int')
    assert _check(tree) == {}


def test_a_class_and_a_method_named_for_their_place_pass(tree):
    _definitions(tree, 'src/x/y.py', 'pycls_x.y.thing', 'pyf_x.y.thing.run')
    assert _check(tree) == {}


def test_a_class_or_method_named_for_another_place_is_reported(tree):
    _definitions(tree, 'src/x/y.py', 'pyf_x.y.thing', 'pyf_x.y.run')
    assert _check(tree) == {'misplaced_module': [('pyf_x.y.run', 'pyf_x.y.thing.run'),
                                                 ('pyf_x.y.thing', 'pycls_x.y.thing')]}


def test_a_package_named_for_its_place_passes(tree):
    _module(tree, 'src/x/y/__init__.py', 'pyp_x.y')
    assert _check(tree) == {}


def test_a_package_named_as_a_module_is_reported(tree):
    _module(tree, 'src/x/y/__init__.py', 'pym_x.y.__init__')
    assert _check(tree) == {'misplaced_module': [('pym_x.y.__init__',
                                                                       'pyp_x.y')]}


def test_an_item_in_a_comment_header_is_read(tree):
    item = _dump(_fields(tree, 'file_tool', guid = 'file_123'))
    (tree / 'tool.cfg').write_text('# ---\n' + ''.join('# ' + line for line in item.splitlines(True))
                                   + '# ...\nsetting = 1\n')
    assert _check(tree) == {
        'bad_guid':         [('file_tool', 'file_123', 'tool.cfg', '2')],
        'schema_violation': [('file_tool', 'sch_configuration_file', 'tool.cfg', '3', 'guid_self',
                              "'file_123' does not match " + repr(REGEX_GUID))]}


def test_files_that_hold_no_item_are_passed_over(tree):
    (tree / 'blob.bin').write_bytes(bytes(range(256)))
    (tree / 'plain.py').write_text('"""A module with no item."""\n')
    (tree / 'loose.yaml').write_text('id_self: xyz_x\n')
    (tree / 'notes.txt').write_text('# A heading, not an item.\n')
    assert _check(tree) == {}


def test_a_field_no_schema_allows_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    path     = tree / location
    path.write_text(path.read_text() + 'colour: red\n')
    assert _check(tree) == {'schema_violation': [
        ('ann_x', 'sch_annotation', location, LINE_ITEM, '',
         "Unevaluated properties are not allowed ('colour' was unexpected)")]}


def test_a_violation_inside_a_register_is_reported_at_its_line(tree):
    path     = tree / '_data/register/reg_concern.yaml'
    register = ruamel.yaml.YAML().load(path.read_text())
    register['table']['concern_cost']['title'] = 7
    path.write_text(_dump(register))
    line     = next(index + 1 for (index, text) in enumerate(path.read_text().splitlines())
                    if text.strip() == 'title: 7')
    row      = ('_data/register/reg_concern.yaml', str(line), 'table/concern_cost/title',
                "7 is not of type 'string'")
    assert _check(tree) == {'schema_violation': [
        ('reg_concern', 'sch_reg_concern', *row),
        ('reg_concern', 'sch_register', *row)]}


def test_a_schema_that_is_not_json_schema_is_reported_and_not_used(tree):
    _option(tree, 'opt_x')
    _replace(tree, '_data/schema/sch_option.yaml', '  - type:               object',
                                                     '  - type:               objct')
    line = _line(tree, '_data/schema/sch_option.yaml', '  - type:               objct')
    assert _check(tree) == {'schema_violation': [
        ('sch_option', 'sch_schema', '_data/schema/sch_option.yaml', line, 'allOf/2/type',
         "'objct' is not valid under any of the given schemas")]}


def test_a_schema_with_a_string_for_a_subschema_is_reported(tree):
    _replace(tree, '_data/schema/sch_option.yaml',
             '  - $ref:               https://capability-commons.org/schema/sch_trait_relation.yaml',
             '  - https://capability-commons.org/schema/sch_trait_relation.yaml')
    line = _line(tree, '_data/schema/sch_option.yaml',
                 '  - https://capability-commons.org/schema/sch_trait_relation.yaml')
    assert _check(tree) == {'schema_violation': [
        ('sch_option', 'sch_schema', '_data/schema/sch_option.yaml', line, 'allOf/1',
         "'https://capability-commons.org/schema/sch_trait_relation.yaml' "
         "is not of type 'object', 'boolean'")]}


def test_a_mention_of_nothing_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    _replace(tree, location, 'description: A test item.', 'description: See concern_absent.')
    assert _check(tree) == {'dangling_mention': [
        ('ann_x', 'concern_absent', location, LINE_DESCRIPTION)]}


def test_a_mention_of_a_guid_a_pattern_or_an_unknown_prefix_passes(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    text     = 'See {guid}, sch_regentry_* and xyz_absent.'.format(guid = _guid_of(tree, ID_ABOUT))
    _replace(tree, location, 'description: A test item.', 'description: ' + text)
    assert _check(tree) == {}


def test_a_mention_of_an_old_id_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    _replace(tree, location, 'description: A test item.', 'description: See concern_correctness.')
    assert _check(tree) == {'outdated_mention': [
        ('ann_x', 'concern_correctness', 'concern_functional_suitability', location,
         LINE_DESCRIPTION)]}


def test_a_reference_by_an_old_id_is_reported(tree):
    edge = dict(_edge(tree, 'r_is_about', 'concern_functional_suitability'),
                id_target = 'concern_correctness')
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert _check(tree) == {'outdated_reference': [
        ('ann_x', 'target', 'concern_correctness', 'concern_functional_suitability', location,
         LINE_TARGET)]}


def test_an_alias_that_an_item_has_as_its_id_is_reported(tree):
    _replace(tree, '_data/register/reg_concern.yaml',
             '      - concern_correctness\n', '      - concern_cost\n')
    assert _check(tree) == {'alias_in_use': [
        ('concern_cost', 'concern_functional_suitability')]}


def test_a_logic_program_file_named_for_its_place_passes(tree):
    _program(tree, 'src/x/y.lp', 'lpf_x.y')
    assert _check(tree) == {}


def test_a_logic_program_file_named_for_another_place_is_reported(tree):
    _program(tree, 'src/x/y.lp', 'lpf_x.z')
    assert _check(tree) == {'misplaced_module': [('lpf_x.z', 'lpf_x.y')]}


def test_a_logic_program_file_without_an_item_is_reported(tree):
    (tree / 'src/x').mkdir(parents = True)
    (tree / 'src/x/y.lp').write_text('% Rules with no item.\n')
    assert _check(tree) == {'unrecorded_module': [('src/x/y.lp',)]}


def test_every_check_names_its_columns():
    for path in (cc_public.check.check.RULES,
                 cc_public.check.check.ADVICE,
                 cc_public.commit.change.RULES):
        text = path.read_text()
        assert set(cc_public.graph.logic.output(text)) <= set(
            cc_public.graph.logic.declared(text))


def test_every_check_says_what_a_failure_is_and_how_to_fix_it():
    map_column = cc_public.check.check.columns()
    list_text  = [cc_public.check.check.RULES.read_text(), cc_public.check.check.ADVICE.read_text()]
    list_name  = [name for text in list_text for name in cc_public.graph.logic.output(text)]
    text       = cc_public.commit.change.RULES.read_text()
    map_column.update({name: tuple(column for (column, _) in tuple_column)
                       for (name, tuple_column) in cc_public.graph.logic.declared(text).items()})
    map_wording = cc_public.check.check.wording()
    map_wording.update(cc_public.graph.logic.worded(text))
    list_name  += cc_public.graph.logic.output(text) + [cc_public.check.check.NAME_SCHEMA,
                                                          cc_public.check.check.NAME_LAYOUT]
    for name in list_name:
        assert set(map_wording.get(name, {})) == {'did', 'fix'}, name
        assert set(re.findall(r'{(\w+)}', map_wording[name]['did'])) <= set(map_column[name]), name


def test_a_document_in_the_wrong_folder_is_reported(tree):
    location = _item(tree, '_data/option/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    assert _check(tree) == {'misplaced_document': [
        ('ann_x', location, '_data/annotation/ann_x.yaml')]}


def test_a_python_file_without_an_item_is_reported(tree):
    (tree / 'src/x').mkdir(parents = True)
    (tree / 'src/x/y.py').write_text('"""A module with no item."""\n')
    assert _check(tree) == {'unrecorded_module': [('src/x/y.py',)]}


def test_a_cycle_of_supersession_is_reported(tree):
    (gx, gy) = (_guid('opt'), _guid('opt'))
    edge     = {'id_relation': 'r_supersedes', 'guid_relation': _guid_of(tree, 'r_supersedes')}
    _option(tree, 'opt_x', [dict(edge, id_target = 'opt_y', guid_target = gy)], guid = gx)
    _option(tree, 'opt_y', [dict(edge, id_target = 'opt_x', guid_target = gx)], guid = gy)
    assert _check(tree) == {'cycle': [('r_supersedes', 'opt_x'),
                                                           ('r_supersedes', 'opt_y')]}


def test_an_argument_about_an_option_without_a_concern_is_reported(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'opt_x')])
    assert _check(tree) == {'argument_without_concern': [('ann_x',)]}


def test_an_argument_about_an_option_with_two_concerns_passes(tree):
    _option(tree, 'opt_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'opt_x'),
                                                         _edge(tree, 'r_speaks_for_concern',
                                                               'concern_cost'),
                                                         _edge(tree, 'r_speaks_for_concern',
                                                               'concern_schedule')])
    assert _check(tree) == {}


def test_an_argument_about_an_annotation_with_a_concern_is_reported(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'ann_x'),
                                                         _edge(tree, 'r_speaks_for_concern',
                                                               'concern_cost')])
    assert _check(tree) == {'concern_without_option': [('ann_y', 'concern_cost')]}


def test_an_argument_about_an_annotation_without_a_concern_passes(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', 'ann_x')])
    assert _check(tree) == {}


def test_a_type_that_names_no_schema_for_its_items_is_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'r_has_items_specified_by_schema\n        guid_relation:  '
             'r_c233cc9d78af4ec6bbaec8a4bbc43344\n        id_target:      sch_configuration_file\n',
             'r_is_specified_by_schema\n        guid_relation:  '
             'r_d70024bd40444f93b4fc1903379ded81\n        id_target:      sch_configuration_file\n')
    assert _check(tree) == {
        'restriction_violation': [
            ('type_configuration_file', 'r_is_specified_by_schema', 'sch_configuration_file', 'source', 'rrs_is_register')],
        'schema_count':          [('type_configuration_file', '0')]}


def test_a_schema_nothing_uses_is_reported(tree):
    text = (tree / '_data/schema/sch_configuration_file.yaml').read_text()
    text = text.replace('sch_configuration_file', 'sch_x').replace(_guid_of(tree, 'sch_configuration_file'), _guid('sch'))
    (tree / '_data/schema/sch_x.yaml').write_text(text)
    assert _check(tree) == {'unused_schema': [('sch_x',)]}


def test_a_concept_nothing_names_is_reported(tree):
    _replace(tree, '_data/schema/sch_register_entry.yaml',
             'concept_register_entry.', 'a register entry.')
    assert _check(tree) == {'unused_concept': [('concept_register_entry',)]}


def test_a_register_entry_of_a_type_the_register_does_not_hold_is_reported():
    facts = {name: set() for name in cc_public.graph.extract.RELATION}
    facts['item'].update({('reg_x', 'reg_1', '', 'f', '1'), ('ann_x', 'ann_1', 'reg_x', 'f', '2')})
    facts['type_prefix'].update({('type_register', 'reg', '.*'), ('type_annotation', 'ann', '.*')})
    facts['register_entry_key'].add(('reg_x', 'ann_x', 'ann_x'))
    rows  = cc_public.graph.logic.run(facts, cc_public.check.check.RULES.read_text())
    assert rows['misplaced_register_entry'] == [('reg_x', 'ann_x', 'type_annotation')]


# -----------------------------------------------------------------------------
def _step(root, id_icd = 'icd_x', map_extra = None):
    """
    Write the interface control document id_icd, whose dataflow step
    surface reads the input inp and writes the output out, both ints,
    with the setting rate. map_extra, if given, adds its groups of
    ports to the surface.

    """

    stem = 'icm' + id_icd[len('icd'):]

    def port(name, spelling, **map_field):
        return {'id_self':   '{stem}.{name}'.format(stem = stem, name = name),
                'guid_self': _guid('icm'),
                'name':      name,
                'brief':     'The {name}.'.format(name = name),
                'type':      {'spelling': spelling},
                **map_field}

    step = {'input':      {'inp': port('inp', 'int')},
            'output':     {'out': port('out', 'int')},
            'settings':   {'rate': port('rate', 'float', optional = True)},
            'invocation': 'Once for each input.'}
    for (kind, map_port) in (map_extra or {}).items():
        step.setdefault(kind, {}).update({name: port(name, *spec)
                                          for (name, spec) in map_port.items()})
    document = _fields(root, id_icd)
    document.update({'version_interface': '1.0',
                     'surface':           {'step': {'dataflow_step': step}}})
    return _item_document(root, '_data/interface_control_document/{id}.yaml'.format(id = id_icd),
                          document)


# -----------------------------------------------------------------------------
def _system(root, list_flow, map_node = None, map_extra = None, map_port = None, stem = 'x'):
    """
    Write the dataflow graph dfg_<stem>, with the nodes a, b and
    c, each presenting icd_x, and an edge for each (source, target) of
    list_flow. An end is a node key and a port name, as 'a.out', and a
    third element, if given, is the direction. map_node, if given, adds
    its fields to each node it names, map_extra its fields to the
    document, and map_port its groups of ports to icd_x, which is
    written unless the tree has it. Return the location.

    """

    def end(text):
        (key, port) = text.split('.')
        id_node     = 'dfn_{stem}.{key}'.format(stem = stem, key = key)
        id_port     = 'icm_x.' + port
        return {'id_dataflow_node':   id_node,
                'guid_dataflow_node': map_guid.get(id_node) or _guid_of(root, id_node),
                'id_port':            id_port,
                'guid_port':          _guid_of(root, id_port)}

    if not (root / '_data/interface_control_document/icd_x.yaml').exists():
        _step(root, map_extra = map_port)
    map_guid = {'dfn_{stem}.{key}'.format(stem = stem, key = key): _guid('dfn')
                for key in ('a', 'b', 'c')}
    edge     = _edge(root, 'r_realizes', 'icd_x')
    document = _fields(root, 'dfg_' + stem)
    document.update({
        'host':          {'local': {'hostname': 'localhost'}},
        'os_process':    {'main':  {'host': 'local'}},
        'dataflow_node': {key: {'id_self':    id_node,
                                'guid_self':  map_guid[id_node],
                                'brief':      'Node {key}.'.format(key = key),
                                'os_process': 'main',
                                'relation':   [edge],
                                **(map_node or {}).get(key, {})}
                          for (id_node, key) in ((id_node, id_node.split('.')[1])
                                                 for id_node in map_guid)},
        'dataflow_edge': [{'source': end(flow[0]),
                           'target': end(flow[1]),
                           **({'direction': flow[2]} if len(flow) > 2 else {})}
                          for flow in list_flow],
        **(map_extra or {})})
    return _item_document(root, '_data/dataflow_graph/dfg_{stem}.yaml'.format(stem = stem),
                          document)


# -----------------------------------------------------------------------------
def _rows(root, relation, arity):
    """
    Return the sorted rows of the derived relation in the tree under
    root, less those that name a node of a dataflow graph other
    than dfg_x.

    """

    facts = cc_public.graph.extract.extract(root)
    rules = '#show {relation}/{arity}.'.format(relation = relation, arity = arity)
    return sorted(row for row in cc_public.graph.logic.run(facts, rules)[relation]
                  if all(not each.startswith('dfn_') or each.startswith('dfn_x.') for each in row))


# A ring of three nodes, closed by a feedback edge, that feeds every
# input once.
#
LIST_RING = [('a.out', 'b.inp'), ('b.out', 'c.inp'), ('c.out', 'a.inp', 'feedback')]


def test_a_system_whose_edges_meet_the_ports_of_its_nodes_passes(tree):
    _system(tree, LIST_RING)
    assert _check(tree) == {}


def test_downstream_follows_data_through_every_edge(tree):
    _system(tree, [('a.out', 'b.inp'), ('b.out', 'c.inp')])
    assert _rows(tree, 'downstream', 2) == [('dfn_x.a', 'dfn_x.b'),
                                            ('dfn_x.a', 'dfn_x.c'),
                                            ('dfn_x.b', 'dfn_x.c')]


def test_upstream_is_downstream_reversed(tree):
    _system(tree, [('a.out', 'b.inp'), ('b.out', 'c.inp')])
    assert _rows(tree, 'upstream', 2) == [('dfn_x.b', 'dfn_x.a'),
                                          ('dfn_x.c', 'dfn_x.a'),
                                          ('dfn_x.c', 'dfn_x.b')]


def test_the_blast_radius_of_a_port_is_every_node_that_presents_it_and_beyond(tree):
    _system(tree, [('a.out', 'b.inp')])
    assert {node for (item, node) in _rows(tree, 'blast_radius', 2)
            if item == 'icm_x.inp'} == {'dfn_x.a', 'dfn_x.b', 'dfn_x.c'}
    assert {node for (item, node) in _rows(tree, 'blast_radius', 2)
            if item == 'dfn_x.b'} == {'dfn_x.b'}
    assert {node for (item, node) in _rows(tree, 'blast_radius', 2)
            if item == 'dfn_x.a'} == {'dfn_x.a', 'dfn_x.b'}


def test_a_node_named_for_another_place_is_reported(tree):
    path = tree / _system(tree, LIST_RING)
    path.write_text(path.read_text().replace('dfn_x.c', 'dfn_x.d'))
    assert _check(tree) == {'misnamed_node': [('dfn_x.d', 'dfn_x.c')]}


def test_a_node_that_presents_no_interface_is_reported(tree):
    _system(tree, LIST_RING, map_node = {'a': {'relation': []}})
    assert _check(tree) == {'interface_count': [('dfn_x.a', '0')]}


def test_an_edge_to_a_node_of_another_system_is_reported(tree):
    _system(tree, LIST_RING, stem = 'y')
    location = _system(tree, LIST_RING)
    _replace(tree, location, 'id_dataflow_node: dfn_x.a\n',
             'id_dataflow_node: dfn_y.a\n')
    _replace(tree, location, 'guid_dataflow_node: ' + _guid_of(tree, 'dfn_x.a'),
             'guid_dataflow_node: ' + _guid_of(tree, 'dfn_y.a'))
    assert _check(tree) == {'foreign_node': [('dfg_x', 'source', 'dfn_y.a', location,
                                              _line(tree, location, '- source:'))]}


def test_an_edge_from_an_input_is_reported(tree):
    location = _system(tree, [('a.inp', 'b.inp'), ('b.out', 'c.inp'),
                              ('c.out', 'a.inp', 'feedback')])
    assert _check(tree) == {'unknown_port': [('dfn_x.a', 'icm_x.inp', 'output', location,
                                              _line(tree, location, '- source:'))]}


def test_an_input_fed_by_two_edges_is_reported(tree):
    _system(tree, LIST_RING + [('a.out', 'c.inp')])
    assert _check(tree) == {'input_fed_twice': [('dfn_x.c', 'icm_x.inp', '2')]}


def test_an_input_no_edge_feeds_is_reported_unless_it_is_optional(tree):
    _system(tree, LIST_RING[:2])
    assert _check(tree) == {'unfed_input': [('dfn_x.a', 'icm_x.inp')]}


def test_an_edge_between_ports_of_two_types_is_reported(tree):
    location = _system(tree, [('a.text', 'b.inp'), ('b.out', 'c.inp'),
                              ('c.out', 'a.inp', 'feedback')],
                       map_port = {'output': {'text': ('str',)}})
    assert _check(tree) == {'port_type_mismatch': [('icm_x.text', 'str', 'icm_x.inp', 'int',
                                                    location, _line(tree, location, '- source:'))]}


def test_a_loop_of_feedforward_edges_is_reported(tree):
    _system(tree, LIST_RING[:2] + [('c.out', 'a.inp')])
    assert _check(tree) == {'feedforward_loop': [('dfn_x.a',), ('dfn_x.b',), ('dfn_x.c',)]}


def test_a_loop_closed_by_a_feedback_edge_reaches_back_to_where_it_began(tree):
    _system(tree, LIST_RING)
    assert ('dfn_x.b', 'dfn_x.b') in _rows(tree, 'downstream', 2)


def test_a_setting_the_interface_does_not_declare_is_reported(tree):
    _system(tree, LIST_RING, map_node = {'a': {'settings': {'rate': 2.0, 'speed': 1}}})
    assert _check(tree) == {'unknown_setting': [('dfn_x.a', 'speed')]}


def test_a_setting_the_interface_needs_is_reported_when_left_out(tree):
    _system(tree, LIST_RING, map_node = {'a': {'settings': {'size': 3}}},
            map_port = {'settings': {'size': ('int',)}})
    assert _check(tree) == {'missing_setting': [('dfn_x.b', 'size'), ('dfn_x.c', 'size')]}


def test_a_node_on_a_process_the_system_does_not_list_is_reported(tree):
    _system(tree, LIST_RING, map_node  = {'c': {'os_process': 'other'}},
            map_extra = {'os_process': {'main': {'host': 'remote'}}})
    assert _check(tree) == {'unplaced': [('dfg_x', 'dfn_x.c', 'other'),
                                         ('dfg_x', 'main', 'remote')]}
