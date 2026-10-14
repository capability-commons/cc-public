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

import ruamel.yaml

import cc_public.check.check
import cc_public.graph.datalog
import cc_public.graph.extract
from cc_public.conftest import DIR_REPO


ID_ABOUT     = 'concern_safety'
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
def _datalog(root, relative, id_self):
    """
    Write a Datalog module whose comment header holds an item with
    id_self.

    """

    item = _dump(_fields(root, id_self))
    path = root / relative
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text('// ---\n' + ''.join('// ' + line for line in item.splitlines(True))
                    + '// ...\n')


# -----------------------------------------------------------------------------
def _replace(root, relative, old, new):
    """
    Replace the first old with new in the file at relative.

    """

    path = root / relative
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new, 1))


def test_the_repository_passes_every_check(souffle):
    assert cc_public.check.check.check(DIR_REPO) == {}


def test_an_annotation_and_a_decision_about_an_item_pass(tree):
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', 'dec_x'),
                                                         _edge(tree, 'r_argues_for_concern', ID_ABOUT)])
    assert cc_public.check.check.check(tree) == {}


def test_an_annotation_about_nothing_is_reported(tree):
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x')
    assert cc_public.check.check.check(tree) == {'missing_about': [('ann_x',)]}


def test_a_decision_about_nothing_is_reported(tree):
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x')
    assert cc_public.check.check.check(tree) == {'missing_about': [('dec_x',)]}


def test_an_id_with_no_known_prefix_is_reported(tree):
    location = _item(tree, '_data/x/xyz_x.yaml', 'xyz_x')
    assert cc_public.check.check.check(tree) == {'unknown_prefix': [('xyz_x', location, LINE_ITEM)]}


def test_an_id_against_the_pattern_of_its_type_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_X.yaml', 'ann_X',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    assert cc_public.check.check.check(tree) == {
        'bad_id':           [('ann_X', REGEX_ANN, location, LINE_ITEM)],
        'schema_violation': [('ann_X', 'sch_annotation', location, LINE_ITEM, 'id_self',
                              "'ann_X' does not match " + repr(REGEX_ID))]}


def test_a_malformed_guid_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)], guid = 'ann_123')
    assert cc_public.check.check.check(tree) == {
        'bad_guid':         [('ann_x', 'ann_123', location, LINE_ITEM)],
        'schema_violation': [('ann_x', 'sch_annotation', location, '2', 'guid_self',
                              "'ann_123' does not match " + repr(REGEX_GUID))]}


def test_two_types_sharing_a_prefix_are_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'prefix:             dec\n', 'prefix:             ann\n')
    assert cc_public.check.check.check(tree) == {'duplicate_prefix': [('ann', 't_annotation', 't_decision'),
                                                      ('ann', 't_decision', 't_annotation')]}


def test_an_id_given_to_two_items_is_reported(tree):
    list_edge = [_edge(tree, 'r_is_about', ID_ABOUT)]
    (one, two) = (_guid('ann'), _guid('ann'))
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = one)
    _item(tree, 'src/x/_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = two)
    assert cc_public.check.check.check(tree) == {'duplicate_id': sorted([('ann_x', one, two),
                                                         ('ann_x', two, one)])}


def test_a_guid_given_to_two_items_is_reported(tree):
    list_edge = [_edge(tree, 'r_is_about', ID_ABOUT)]
    guid      = _guid('ann')
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', list_edge, guid = guid)
    _item(tree, '_data/annotation/ann_y.yaml', 'ann_y', list_edge, guid = guid)
    assert cc_public.check.check.check(tree) == {'duplicate_guid': [(guid, 'ann_x', 'ann_y'),
                                                    (guid, 'ann_y', 'ann_x')]}


def test_an_entry_held_under_another_key_is_reported(tree):
    _replace(tree, '_data/register/reg_concern.yaml',
             '  concern_security:\n', '  concern_secure:\n')
    assert cc_public.check.check.check(tree) == {'key_mismatch': [('reg_concern',
                                                   'concern_secure',
                                                   'concern_security')]}


def test_a_reference_to_nothing_is_reported(tree):
    edge = {'id_relation':   'r_is_about',
            'guid_relation': _guid_of(tree, 'r_is_about'),
            'id_target':     'concern_absent',
            'guid_target':   _guid('concern')}
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert cc_public.check.check.check(tree) == {'dangling_reference': [('ann_x', 'target', 'concern_absent',
                                                         location, LINE_TARGET)]}


def test_a_reference_with_a_stale_guid_is_reported(tree):
    edge = dict(_edge(tree, 'r_is_about', ID_ABOUT), guid_target = _guid('concern'))
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert cc_public.check.check.check(tree) == {'stale_guid': [('ann_x', 'target', ID_ABOUT,
                                                 edge['guid_target'], location, LINE_TARGET)]}


def test_an_edge_from_outside_the_domain_is_reported(tree):
    # Support runs from an annotation. A decision gives no reasons.
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/decision/dec_y.yaml', 'dec_y', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                       _edge(tree, 'r_supports', 'dec_x')])
    assert cc_public.check.check.check(tree) == {'domain_violation': [('dec_y', 'r_supports', 't_decision')]}


def test_an_edge_to_outside_the_range_is_reported(tree):
    # Support runs to an assertion or a choice, not to a concern.
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_supports', ID_ABOUT),
                                                         _edge(tree, 'r_argues_for_concern', ID_ABOUT)])
    assert cc_public.check.check.check(tree) == {'range_violation': [(ID_ABOUT, 'r_supports', 't_concern')]}


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
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                       _edge(tree, 'r_is_subject_of', 'ann_x')])
    assert cc_public.check.check.check(tree) == {}


def test_a_module_named_for_its_place_passes(tree):
    _module(tree, 'src/x/_test/test_y.py', 'pym_x._test.test_y')
    assert cc_public.check.check.check(tree) == {}


def test_a_module_named_for_another_place_is_reported(tree):
    _module(tree, 'src/x/y.py', 'pym_x.z')
    assert cc_public.check.check.check(tree) == {'misplaced_module': [('pym_x.z', 'pym_x.y')]}


def test_a_package_named_for_its_place_passes(tree):
    _module(tree, 'src/x/y/__init__.py', 'pyp_x.y')
    assert cc_public.check.check.check(tree) == {}


def test_a_package_named_as_a_module_is_reported(tree):
    _module(tree, 'src/x/y/__init__.py', 'pym_x.y.__init__')
    assert cc_public.check.check.check(tree) == {'misplaced_module': [('pym_x.y.__init__',
                                                                       'pyp_x.y')]}


def test_an_item_in_a_comment_header_is_read(tree):
    item = _dump(_fields(tree, 'file_tool', guid = 'file_123'))
    (tree / 'tool.cfg').write_text('# ---\n' + ''.join('# ' + line for line in item.splitlines(True))
                                   + '# ...\nsetting = 1\n')
    assert cc_public.check.check.check(tree) == {
        'bad_guid':         [('file_tool', 'file_123', 'tool.cfg', '2')],
        'schema_violation': [('file_tool', 'sch_file', 'tool.cfg', '3', 'guid_self',
                              "'file_123' does not match " + repr(REGEX_GUID))]}


def test_files_that_hold_no_item_are_passed_over(tree):
    (tree / 'blob.bin').write_bytes(bytes(range(256)))
    (tree / 'plain.py').write_text('"""A module with no item."""\n')
    (tree / 'loose.yaml').write_text('id_self: xyz_x\n')
    (tree / 'notes.txt').write_text('# A heading, not an item.\n')
    assert cc_public.check.check.check(tree) == {}


def test_a_field_no_schema_allows_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    path     = tree / location
    path.write_text(path.read_text() + 'colour: red\n')
    assert cc_public.check.check.check(tree) == {'schema_violation': [
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
    assert cc_public.check.check.check(tree) == {'schema_violation': [
        ('reg_concern', 'sch_reg_concern', *row),
        ('reg_concern', 'sch_register', *row)]}


def test_a_mention_of_nothing_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    _replace(tree, location, 'description: A test item.', 'description: See concern_absent.')
    assert cc_public.check.check.check(tree) == {'dangling_mention': [
        ('ann_x', 'concern_absent', location, LINE_DESCRIPTION)]}


def test_a_mention_of_a_guid_a_pattern_or_an_unknown_prefix_passes(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    text     = 'See {guid}, sch_regentry_* and xyz_absent.'.format(guid = _guid_of(tree, ID_ABOUT))
    _replace(tree, location, 'description: A test item.', 'description: ' + text)
    assert cc_public.check.check.check(tree) == {}


def test_a_mention_of_an_old_id_is_reported(tree):
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    _replace(tree, location, 'description: A test item.', 'description: See concern_correctness.')
    assert cc_public.check.check.check(tree) == {'outdated_mention': [
        ('ann_x', 'concern_correctness', 'concern_functional_suitability', location,
         LINE_DESCRIPTION)]}


def test_a_reference_by_an_old_id_is_reported(tree):
    edge = dict(_edge(tree, 'r_is_about', 'concern_functional_suitability'),
                id_target = 'concern_correctness')
    location = _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [edge])
    assert cc_public.check.check.check(tree) == {'outdated_reference': [
        ('ann_x', 'target', 'concern_correctness', 'concern_functional_suitability', location,
         LINE_TARGET)]}


def test_an_alias_that_an_item_has_as_its_id_is_reported(tree):
    _replace(tree, '_data/register/reg_concern.yaml',
             '      - concern_correctness\n', '      - concern_cost\n')
    assert cc_public.check.check.check(tree) == {'alias_in_use': [
        ('concern_cost', 'concern_functional_suitability')]}


def test_a_datalog_module_named_for_its_place_passes(tree):
    _datalog(tree, 'src/x/y.dl', 'dlm_x.y')
    assert cc_public.check.check.check(tree) == {}


def test_a_datalog_module_named_for_another_place_is_reported(tree):
    _datalog(tree, 'src/x/y.dl', 'dlm_x.z')
    assert cc_public.check.check.check(tree) == {'misplaced_module': [('dlm_x.z', 'dlm_x.y')]}


def test_a_datalog_file_without_an_item_is_reported(tree):
    (tree / 'src/x').mkdir(parents = True)
    (tree / 'src/x/y.dl').write_text('// Rules with no item.\n')
    assert cc_public.check.check.check(tree) == {'unrecorded_module': [('src/x/y.dl',)]}


def test_a_document_in_the_wrong_folder_is_reported(tree):
    location = _item(tree, '_data/decision/ann_x.yaml', 'ann_x',
                     [_edge(tree, 'r_is_about', ID_ABOUT)])
    assert cc_public.check.check.check(tree) == {'misplaced_document': [
        ('ann_x', location, '_data/annotation/ann_x.yaml')]}


def test_a_python_file_without_an_item_is_reported(tree):
    (tree / 'src/x').mkdir(parents = True)
    (tree / 'src/x/y.py').write_text('"""A module with no item."""\n')
    assert cc_public.check.check.check(tree) == {'unrecorded_module': [('src/x/y.py',)]}


def test_a_cycle_of_supersession_is_reported(tree):
    about    = _edge(tree, 'r_is_about', ID_ABOUT)
    (gx, gy) = (_guid('dec'), _guid('dec'))
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x',
          [about, dict(about, id_relation = 'r_supersedes', id_target = 'dec_y', guid_target = gy,
                       guid_relation = _guid_of(tree, 'r_supersedes'))], guid = gx)
    _item(tree, '_data/decision/dec_y.yaml', 'dec_y',
          [about, dict(about, id_relation = 'r_supersedes', id_target = 'dec_x', guid_target = gx,
                       guid_relation = _guid_of(tree, 'r_supersedes'))], guid = gy)
    assert cc_public.check.check.check(tree) == {'cycle': [('r_supersedes', 'dec_x'),
                                                           ('r_supersedes', 'dec_y')]}


def test_an_argument_without_a_concern_is_reported(tree):
    _item(tree, '_data/decision/dec_x.yaml', 'dec_x', [_edge(tree, 'r_is_about', ID_ABOUT)])
    _item(tree, '_data/annotation/ann_x.yaml', 'ann_x', [_edge(tree, 'r_is_about', ID_ABOUT),
                                                         _edge(tree, 'r_challenges', 'dec_x')])
    assert cc_public.check.check.check(tree) == {'concern_count': [('ann_x', '0')]}


def test_a_type_that_names_no_schema_for_its_items_is_reported(tree):
    _replace(tree, '_data/register/reg_data_item_type.yaml',
             'r_has_items_specified_by_schema\n        guid_relation:  '
             'r_c233cc9d78af4ec6bbaec8a4bbc43344\n        id_target:      sch_file\n',
             'r_is_specified_by_schema\n        guid_relation:  '
             'r_d70024bd40444f93b4fc1903379ded81\n        id_target:      sch_file\n')
    assert cc_public.check.check.check(tree) == {
        'domain_violation': [('t_file', 'r_is_specified_by_schema', 't_type')],
        'schema_count':     [('t_file', '0')]}


def test_a_schema_nothing_uses_is_reported(tree):
    text = (tree / '_data/schema/sch_file.yaml').read_text()
    text = text.replace('sch_file', 'sch_x').replace(_guid_of(tree, 'sch_file'), _guid('sch'))
    (tree / '_data/schema/sch_x.yaml').write_text(text)
    assert cc_public.check.check.check(tree) == {'unused_schema': [('sch_x',)]}


def test_a_concept_nothing_names_is_reported(tree):
    _replace(tree, '_data/schema/sch_register_entry.yaml',
             'con_register_entry.', 'a register entry.')
    assert cc_public.check.check.check(tree) == {'unused_concept': [('con_register_entry',)]}


def test_a_register_entry_of_a_type_the_register_does_not_hold_is_reported(souffle):
    facts = {name: set() for name in cc_public.graph.extract.RELATION}
    facts['item'].update({('reg_x', 'reg_1', '', 'f', '1'), ('ann_x', 'ann_1', 'reg_x', 'f', '2')})
    facts['type_prefix'].update({('t_register', 'reg', '.*'), ('t_annotation', 'ann', '.*')})
    facts['register_entry_key'].add(('reg_x', 'ann_x', 'ann_x'))
    rows  = cc_public.graph.datalog.run(facts, cc_public.check.check.RULES.read_text())
    assert rows['misplaced_register_entry'] == [('reg_x', 'ann_x', 't_annotation')]
