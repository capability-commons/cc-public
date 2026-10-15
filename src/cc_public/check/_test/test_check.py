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
import re
import uuid

import click.testing
import ruamel.yaml

import cc_public.check.check
import cc_public.cli.command
import cc_public.commit.change
import cc_public.graph.datalog
import cc_public.graph.extract
from cc_public.conftest import DIR_REPO


ID_ABOUT     = 'concern_safety'
DIR_ISSUE    = '_data/issue/iss_x/'
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
def _decision(root, id_self, list_edge = (), guid = None):
    """
    Write a decision that answers iss_x, in the folder of iss_x, and
    return its location. iss_x is written too, about ID_ABOUT, if it
    is not there yet.

    """

    if not (root / DIR_ISSUE / 'iss_x.yaml').exists():
        _item(root, DIR_ISSUE + 'iss_x.yaml', 'iss_x', [_edge(root, 'r_is_about', ID_ABOUT)])
    return _item(root, DIR_ISSUE + id_self + '.yaml', id_self,
                 [_edge(root, 'r_answers', 'iss_x'), *list_edge], guid)


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
    _decision(tree, 'dec_x')
    _replace(tree, DIR_ISSUE + 'dec_x.yaml', 'title: Test item', 'title: "Test item\\n"')
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


def test_an_annotation_and_a_decision_about_an_item_pass(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', 'dec_x'),
                                                         _edge(tree, 'r_argues_for_concern', ID_ABOUT)])
    assert _check(tree) == {}


def test_an_annotation_about_nothing_is_reported(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x')
    assert _check(tree) == {'missing_about': [('ann_x',)]}


def test_a_decision_that_answers_no_issue_is_reported(tree):
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x')
    assert _check(tree) == {'answer_count': [('dec_x', '0')]}


def test_an_issue_about_nothing_is_reported(tree):
    _item(tree, DIR_ISSUE + 'iss_x.yaml', 'iss_x')
    assert _check(tree) == {'missing_about': [('iss_x',)]}


def test_a_decision_outside_the_folder_of_its_issue_is_reported(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/decision/dec_y.yaml', 'dec_y', [_edge(tree, 'r_answers', 'iss_x')])
    assert _check(tree) == {'misplaced_document': [
        ('dec_y', '_data/decision/dec_y.yaml', DIR_ISSUE + 'dec_y.yaml')]}


def test_an_annotation_about_an_issue_is_kept_in_its_folder(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'iss_x')])
    assert _check(tree) == {'misplaced_document': [
        ('ann_x', '_data/annotation/ann_x.yaml', DIR_ISSUE + 'ann_x.yaml')]}


def test_a_determination_that_upholds_a_decision_passes(tree):
    _decision(tree, 'dec_x')
    _decision(tree, 'dec_y')
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x'),
                                                    _edge(tree, 'r_rejects', 'dec_y')])
    assert _check(tree) == {}


def test_a_determination_across_two_issues_is_reported(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/issue/iss_y/iss_y.yaml', 'iss_y', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/issue/iss_y/dec_y.yaml', 'dec_y', [_edge(tree, 'r_answers', 'iss_y')])
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x'),
                                                    _edge(tree, 'r_rejects', 'dec_y')])
    failures = _check(tree)
    assert failures['determination_across_issues'] == [('det_x', 'iss_x', 'iss_y')]


def _two_determinations(tree, is_superseding):
    """
    Write two decisions that answer iss_x, det_x upholding dec_x, and
    det_y upholding dec_y, and superseding det_x if is_superseding.

    """

    _decision(tree, 'dec_x')
    _decision(tree, 'dec_y')
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x')])
    list_edge = [_edge(tree, 'r_upholds', 'dec_y')]
    if is_superseding:
        list_edge.append(_edge(tree, 'r_supersedes', 'det_x'))
    _item(tree, DIR_ISSUE + 'det_y.yaml', 'det_y', list_edge)


def test_a_determination_that_supersedes_the_one_before_passes(tree):
    _two_determinations(tree, is_superseding = True)
    assert _check(tree) == {}


def test_two_current_determinations_of_an_issue_are_reported(tree):
    _two_determinations(tree, is_superseding = False)
    assert _check(tree) == {'competing_determinations': [('iss_x', 'det_x', 'det_y')]}


def test_a_decision_that_supersedes_a_determination_is_reported(tree):
    _decision(tree, 'dec_x')
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x')])
    _decision(tree, 'dec_y', [_edge(tree, 'r_supersedes', 'det_x')])
    assert _check(tree) == {'supersession_across_types': [('dec_y', 'det_x')]}


def test_a_determination_of_nothing_is_reported(tree):
    _item(tree, '_data/determination/det_x.yaml', 'det_x')
    assert _check(tree) == {'determination_without_decision': [('det_x',)]}


def _driven_decisions(tree):
    """
    Write lc_x, driven by concern_cost, an issue about it, and two
    decisions that answer the issue.

    """

    _item(tree, '_data/logical_component/lc_x.yaml', 'lc_x',
          [_edge(tree, 'r_is_driven_by', 'concern_cost')])
    _item(tree, DIR_ISSUE + 'iss_x.yaml', 'iss_x', [_edge(tree, 'r_is_about', 'lc_x')])
    _decision(tree, 'dec_x')
    _decision(tree, 'dec_y')


def test_a_determination_with_a_driver_unargued_is_reported(tree):
    _driven_decisions(tree)
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x')])
    assert _check(tree) == {'unargued_driver': [('det_x', 'dec_x', 'concern_cost')]}


def test_a_driver_argued_only_in_another_issue_is_unargued(tree):
    _driven_decisions(tree)
    _item(tree, '_data/issue/iss_y/iss_y.yaml', 'iss_y', [_edge(tree, 'r_is_about', 'lc_x')])
    _item(tree, '_data/issue/iss_y/dec_z.yaml', 'dec_z', [_edge(tree, 'r_answers', 'iss_y')])
    _item(tree, '_data/issue/iss_y/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'iss_y'),
                                                          _edge(tree, 'r_challenges', 'dec_z'),
                                                          _edge(tree, 'r_argues_for_concern',
                                                                'concern_cost')])
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x')])
    assert _check(tree) == {'unargued_driver': [('det_x', 'dec_x', 'concern_cost')]}


def test_a_driver_argued_for_an_alternative_passes(tree):
    _driven_decisions(tree)
    _item(tree, DIR_ISSUE + 'ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', 'iss_x'),
                                                    _edge(tree, 'r_challenges', 'dec_y'),
                                                    _edge(tree, 'r_argues_for_concern',
                                                          'concern_cost')])
    _item(tree, DIR_ISSUE + 'det_x.yaml', 'det_x', [_edge(tree, 'r_upholds', 'dec_x')])
    assert _check(tree) == {}


def test_an_open_decision_with_a_driver_unargued_passes(tree):
    _driven_decisions(tree)
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
             'prefix:             dec\n', 'prefix:             ann\n')
    assert _check(tree)['duplicate_prefix'] == [('ann', 't_annotation', 't_decision'),
                                                ('ann', 't_decision', 't_annotation')]


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


def test_a_reference_with_a_stale_guid_is_reported(tree):
    edge = dict(_edge(tree, 'r_is_about', ID_ABOUT), guid_target = _guid('concern'))
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert _check(tree) == {'stale_guid': [('ann_x', 'target', ID_ABOUT,
                                                 edge['guid_target'], location, LINE_TARGET)]}


def test_an_edge_from_outside_the_domain_is_reported(tree):
    # Support runs from an annotation. A decision gives no reasons.
    _decision(tree, 'dec_x')
    _decision(tree, 'dec_y', [_edge(tree, 'r_supports', 'dec_x')])
    assert _check(tree) == {'domain_violation': [('dec_y', 'r_supports', 't_decision')]}


def test_an_edge_to_outside_the_range_is_reported(tree):
    # Support runs to an assertion or a choice, not to a concern.
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', ID_ABOUT)])
    assert _check(tree) == {'range_violation': [(ID_ABOUT, 'r_supports', 't_concern')]}


def test_an_edge_recorded_through_an_inverse_is_read_in_reverse(tree):
    # dec_x records that it is the subject of ann_x, which is ann_x
    # being about dec_x, so ann_x is about something.
    path     = tree / '_data/register/reg_relation.yaml'
    register = ruamel.yaml.YAML().load(path.read_text())
    register['table']['r_is_about']['inverse'] = {'id_self':   'r_is_subject_of',
                                                  'guid_self': _guid('r'),
                                                  'brief':     'SUBJ is the subject of OBJ'}
    path.write_text(_dump(register))
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x')
    _decision(tree, 'dec_x', [_edge(tree, 'r_is_subject_of', 'ann_x')])
    assert _check(tree) == {}


def test_a_module_named_for_its_place_passes(tree):
    _module(tree, 'src/x/_test/test_y.py', 'pym_x._test.test_y')
    assert _check(tree) == {}


def test_a_module_named_for_another_place_is_reported(tree):
    _module(tree, 'src/x/y.py', 'pym_x.z')
    assert _check(tree) == {'misplaced_module': [('pym_x.z', 'pym_x.y')]}


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
        'schema_violation': [('file_tool', 'sch_file', 'tool.cfg', '3', 'guid_self',
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
    _decision(tree, 'dec_x')
    _replace(tree, '_data/schema/sch_decision.yaml', '  - type:               object',
                                                     '  - type:               objct')
    line = _line(tree, '_data/schema/sch_decision.yaml', '  - type:               objct')
    assert _check(tree) == {'schema_violation': [
        ('sch_decision', 'sch_schema', '_data/schema/sch_decision.yaml', line, 'allOf/2/type',
         "'objct' is not valid under any of the given schemas")]}


def test_a_schema_with_a_string_for_a_subschema_is_reported(tree):
    _replace(tree, '_data/schema/sch_decision.yaml',
             '  - $ref:               https://capability-commons.org/schema/sch_trait_relation.yaml',
             '  - https://capability-commons.org/schema/sch_trait_relation.yaml')
    line = _line(tree, '_data/schema/sch_decision.yaml',
                 '  - https://capability-commons.org/schema/sch_trait_relation.yaml')
    assert _check(tree) == {'schema_violation': [
        ('sch_decision', 'sch_schema', '_data/schema/sch_decision.yaml', line, 'allOf/1',
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
    for path in (cc_public.check.check.RULES, cc_public.commit.change.RULES):
        text = path.read_text()
        assert set(cc_public.graph.datalog.output(text)) <= set(
            cc_public.graph.datalog.declared(text))


def test_a_document_in_the_wrong_folder_is_reported(tree):
    location = _item(tree, '_data/decision/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    assert _check(tree) == {'misplaced_document': [
        ('ann_x', location, '_data/annotation/ann_x.yaml')]}


def test_a_python_file_without_an_item_is_reported(tree):
    (tree / 'src/x').mkdir(parents = True)
    (tree / 'src/x/y.py').write_text('"""A module with no item."""\n')
    assert _check(tree) == {'unrecorded_module': [('src/x/y.py',)]}


def test_a_cycle_of_supersession_is_reported(tree):
    (gx, gy) = (_guid('dec'), _guid('dec'))
    edge     = {'id_relation': 'r_supersedes', 'guid_relation': _guid_of(tree, 'r_supersedes')}
    _decision(tree, 'dec_x', [dict(edge, id_target = 'dec_y', guid_target = gy)], guid = gx)
    _decision(tree, 'dec_y', [dict(edge, id_target = 'dec_x', guid_target = gx)], guid = gy)
    assert _check(tree) == {'cycle': [('r_supersedes', 'dec_x'),
                                                           ('r_supersedes', 'dec_y')]}


def test_an_argument_about_a_decision_without_a_concern_is_reported(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'dec_x')])
    assert _check(tree) == {'argument_without_concern': [('ann_x',)]}


def test_an_argument_about_a_decision_with_two_concerns_passes(tree):
    _decision(tree, 'dec_x')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'dec_x'),
                                                         _edge(tree, 'r_argues_for_concern',
                                                               'concern_cost'),
                                                         _edge(tree, 'r_argues_for_concern',
                                                               'concern_schedule')])
    assert _check(tree) == {}


def test_an_argument_about_an_annotation_with_a_concern_is_reported(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'ann_x'),
                                                         _edge(tree, 'r_argues_for_concern',
                                                               'concern_cost')])
    assert _check(tree) == {'concern_without_decision': [('ann_y', 'concern_cost')]}


def test_an_argument_about_an_annotation_without_a_concern_passes(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', 'ann_x')])
    assert _check(tree) == {}


def test_a_type_that_names_no_schema_for_its_items_is_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'r_has_items_specified_by_schema\n        guid_relation:  '
             'r_c233cc9d78af4ec6bbaec8a4bbc43344\n        id_target:      sch_file\n',
             'r_is_specified_by_schema\n        guid_relation:  '
             'r_d70024bd40444f93b4fc1903379ded81\n        id_target:      sch_file\n')
    assert _check(tree) == {
        'domain_violation': [('t_file', 'r_is_specified_by_schema', 't_type')],
        'schema_count':     [('t_file', '0')]}


def test_a_schema_nothing_uses_is_reported(tree):
    text = (tree / '_data/schema/sch_file.yaml').read_text()
    text = text.replace('sch_file', 'sch_x').replace(_guid_of(tree, 'sch_file'), _guid('sch'))
    (tree / '_data/schema/sch_x.yaml').write_text(text)
    assert _check(tree) == {'unused_schema': [('sch_x',)]}


def test_a_concept_nothing_names_is_reported(tree):
    _replace(tree, '_data/schema/sch_register_entry.yaml',
             'con_register_entry.', 'a register entry.')
    assert _check(tree) == {'unused_concept': [('con_register_entry',)]}


def test_a_register_entry_of_a_type_the_register_does_not_hold_is_reported():
    facts = {name: set() for name in cc_public.graph.extract.RELATION}
    facts['item'].update({('reg_x', 'reg_1', '', 'f', '1'), ('ann_x', 'ann_1', 'reg_x', 'f', '2')})
    facts['type_prefix'].update({('t_register', 'reg', '.*'), ('t_annotation', 'ann', '.*')})
    facts['register_entry_key'].add(('reg_x', 'ann_x', 'ann_x'))
    rows  = cc_public.graph.datalog.run(facts, cc_public.check.check.RULES.read_text())
    assert rows['misplaced_register_entry'] == [('reg_x', 'ann_x', 't_annotation')]
