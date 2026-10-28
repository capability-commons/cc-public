"""
---

id_self:                pym_cctool.edit._test.test_edit
guid_self:              pym_212ff8ff7b2a4a69986a41ecd85d4c3e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Edit tests
brief:                  |
                        Tests of the edits, and of the layout they
                        write.
description:            |
                        Each test makes an edit over a copy of the
                        repository, and checks the text it writes and
                        the failures it adds. A new guid is made from
                        zeros, so that the text is known.
edge:                   []

...
"""


import pathlib
import re

import pytest
import ruamel.yaml.scalarstring

import cctool.check.check
import cctool.edit.edit
import cctool.check.layout
import cctool.graph.extract
import cctool.graph.logic
from cctool.conftest import DIR_REPO


HEX_ZERO      = '0' * 32
GUID_CONCEPT  = 'concept_4c11efe184cd47289cfa3941377d4807'
TEXT_ABOUT    = ('edge:\n'
                 '\n'
                 '  - id_relation:        relation_is_about\n'
                 '    guid_relation:      relation_1bb0463a053f42c498e3e9285df99c8f\n'
                 '    id_target:          concept_concept\n'
                 '    guid_target:        concept_4c11efe184cd47289cfa3941377d4807\n')
TEXT_RIGHTS   = ('copyright:              Copyright 2026 William Payne\n'
                 'license:                Apache-2.0\n'
                 '\n'
                 'protective_mark:\n'
                 '\n'
                 '  - id_mark:            mark_public\n'
                 '    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f\n')
# A logical component with no drivers, for a decision to be about.
#
NEW_SUBJECT   = {'new': 'lco_x', 'field': {'title': 'Subject',
                                          'brief': 'A logical component for a decision.'}}
FIELD_ANN     = {'title': 'Edits work',
                 'brief': 'The editing commands keep the tree free of new failures, '
                          'whatever they change.'}
FIELD_HEADER  = {'title':       'Extra',
                 'brief':       'An extra module.',
                 'description': 'It is extra.'}
FIELD_CONCERN = {'title':       'Reviewability',
                 'brief':       'Whether a change can be reviewed.',
                 'description': 'Reviewability covers how easily a change is read.',
                 'question':    ['Can a change be read in one sitting?'],
                 'measure':     ['Lines changed, per change.']}


# -----------------------------------------------------------------------------
@pytest.fixture
def zero(monkeypatch):
    """
    Make every new guid from zeros.

    """

    monkeypatch.setattr(cctool.edit.edit.uuid, 'uuid4', lambda: type('U', (), {'hex': HEX_ZERO}))


# -----------------------------------------------------------------------------
def _edit(tree, *list_operation, is_written = True):
    """
    Make the operations over tree as one edit, and return the failures
    it adds.

    """

    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, list(list_operation))
    return cctool.edit.edit.apply(edited, is_written = is_written)


def test_an_edit_that_cannot_be_written_changes_nothing(tree, monkeypatch):
    write_text = pathlib.Path.write_text

    def _refuse(path, *list_arg, **map_arg):
        if path.name.startswith('opt_x'):
            raise OSError('No space left on device')
        return write_text(path, *list_arg, **map_arg)

    monkeypatch.setattr(pathlib.Path, 'write_text', _refuse)
    with pytest.raises(cctool.edit.edit.ErrorEdit, match = 'nothing was changed'):
        _edit(tree, NEW_SUBJECT,
                    {'new': 'dec_x', 'field': FIELD_ANN, 'link': [['relation_is_about', 'lco_x']]},
                    {'new': 'opt_x', 'field': FIELD_ANN, 'link': [['relation_is_option_for', 'dec_x']]})
    assert [path for path in (tree / '_data/decision/dec_x').rglob('*') if path.is_file()] == []
    assert list(tree.rglob('*' + cctool.edit.edit.SUFFIX_STAGED)) == []


def test_a_new_standalone_item_is_written_in_a_file_of_its_own(tree, zero):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['relation_is_about', 'concept_concept']]}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text() == (
        'id_self:                ann_x\n'
        'guid_self:              ann_' + HEX_ZERO + '\n'
        + TEXT_RIGHTS
        + '\n'
        'title:                  Edits work\n'
        'brief:                  |\n'
        '                        The editing commands keep the tree free of new\n'
        '                        failures, whatever they change.\n'
        '\n'
        + TEXT_ABOUT)


def test_a_new_entry_is_written_at_the_end_of_its_register(tree, zero):
    text = (tree / '_data/register/reg_concern.yaml').read_text()
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN},
                       {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['relation_is_about', 'concern_x']]}) == {}
    assert (tree / '_data/register/reg_concern.yaml').read_text() == text + (
        '\n'
        '  # ---------------------------------------------------------------------------\n'
        '  # concern_x -- Reviewability\n'
        '  #\n'
        '  concern_x:\n'
        '    id_self:            concern_x\n'
        '    guid_self:          concern_' + HEX_ZERO + '\n'
        '    title:              Reviewability\n'
        '    brief:              |\n'
        '                        Whether a change can be reviewed.\n'
        '    description:        |\n'
        '                        Reviewability covers how easily a change is\n'
        '                        read.\n'
        '\n'
        '    question:\n'
        '      - Can a change be read in one sitting?\n'
        '\n'
        '    measure:\n'
        '      - Lines changed, per change.\n'
        '\n'
        '    alias:              []\n'
        '    edge:               []\n')


def test_a_new_entry_is_written_as_the_first_in_an_empty_register(tree, zero):
    path = tree / '_data/register/reg_concern.yaml'
    head = path.read_text().split('entries:')[0]
    path.write_text(head + 'entries:                {}\n')
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN}) == {}
    assert path.read_text() == head + (
        'entries:\n'
        '\n'
        '  # ---------------------------------------------------------------------------\n'
        '  # concern_x -- Reviewability\n'
        '  #\n'
        '  concern_x:\n'
        '    id_self:            concern_x\n'
        '    guid_self:          concern_' + HEX_ZERO + '\n'
        '    title:              Reviewability\n'
        '    brief:              |\n'
        '                        Whether a change can be reviewed.\n'
        '    description:        |\n'
        '                        Reviewability covers how easily a change is\n'
        '                        read.\n'
        '\n'
        '    question:\n'
        '      - Can a change be read in one sitting?\n'
        '\n'
        '    measure:\n'
        '      - Lines changed, per change.\n'
        '\n'
        '    alias:              []\n'
        '    edge:               []\n')


def test_an_edit_that_adds_a_failure_is_refused_and_not_written(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN}) == {'missing_about': [('ann_x',)]}
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_a_failure_the_tree_already_has_is_not_added(tree):
    path = tree / '_data/register/reg_concept.yaml'
    text = path.read_text()
    path.write_text(text.replace('guid_self:          {guid}'.format(guid = GUID_CONCEPT),
                                 'guid_self:          concept_' + HEX_ZERO))
    assert 'guid_mismatch' in cctool.check.check.check(tree)
    assert _edit(tree, {'set': ['concept_concept', 'note', 'A note.']}) == {}


def test_a_new_concept_needs_an_item_that_names_it(tree):
    field = {'title': 'X', 'brief': 'X.', 'description': 'X.', 'term_preferred': 'x'}
    assert _edit(tree, {'new': 'concept_x', 'field': field}) == {'unused_concept': [('concept_x',)]}
    assert _edit(tree, {'new': 'concept_x', 'field': field},
                       {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['relation_is_about', 'concept_x']]}) == {}


def test_a_new_schema_opens_with_its_dialect_and_keeps_structured_values(tree, zero):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'new':   'sch_x',
                                     'field': {'title':    'X',
                                               'brief':    'X.',
                                               '$id':      'https://x/sch_x.yaml',
                                               '$schema':  'https://x/dialect',
                                               'allOf':    [{'$ref': 'https://x/sch_y.yaml'}],
                                               'required': ['brief'],
                                               'unevaluatedProperties': False}}])
    text = edited.text('_data/schema/sch_x.yaml')
    assert text.startswith('$schema:                https://x/dialect\n'
                           '$id:                    https://x/sch_x.yaml\n'
                           'id_self:                sch_x\n')
    assert ('allOf:\n'
            '  - $ref:               https://x/sch_y.yaml\n') in text
    assert 'unevaluatedProperties:  false\n' in text


def test_an_embedded_item_given_in_a_field_is_given_a_guid(tree, zero):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'set': ['concept_concept', 'example',
                                             {'id_self': 'concept_x', 'name': 'x'}]}])
    assert ('    example:\n'
            '      id_self:          concept_x\n'
            '      guid_self:        concept_' + HEX_ZERO + '\n'
            '      name:             x\n') in edited.edit['_data/register/reg_concept.yaml']


def test_a_new_field_that_names_an_item_is_given_its_guid(tree, zero):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'new':   'type_x',
                                     'field': {'title':      'X type',
                                               'brief':      'X.',
                                               'id_concept': 'concept_concept'}}])
    assert ('    id_concept:         concept_concept\n'
            '    guid_concept:       concept_4c11efe184cd47289cfa3941377d4807\n') in (
        edited.text('_data/register/reg_data_item_type.yaml'))


def test_a_field_that_names_an_item_at_any_depth_is_given_its_guid(tree, zero):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'new':   'icd_x',
                                     'field': {'title':   'X interface',
                                               'brief':   'X.',
                                               'example': {'member': {'id_self': 'icm_x.y'},
                                                           'edges':  [{'id_member': 'icm_x.y',
                                                                       'id_owner':  'lco_tooling'}]}}}])
    text = edited.text('_data/interface_control_document/icd_x.yaml')
    list_pair = [line.split() for line in text.splitlines()]
    assert ['guid_member:', 'icm_' + HEX_ZERO] in list_pair
    assert ['guid_owner:', cctool.edit.edit.Tree(tree).guid('lco_tooling')] in list_pair


def test_a_link_turns_an_empty_edge_field_into_a_list(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN, 'link': []},
                       {'link': ['ann_x', 'relation_is_about', 'concept_concept']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        'whatever they change.\n\n' + TEXT_ABOUT)


def test_a_link_is_added_after_the_edges_there_are(tree):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['relation_is_about', 'concept_concept']]},
                       {'link': ['ann_x', 'relation_is_about', 'concept_relation']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        TEXT_ABOUT
        + '\n'
        '  - id_relation:        relation_is_about\n'
        '    guid_relation:      relation_1bb0463a053f42c498e3e9285df99c8f\n'
        '    id_target:          concept_relation\n'
        '    guid_target:        concept_42a4bd80300849a98bf9649ad97d10d9\n')


def test_remove_takes_out_a_register_entry_and_its_banner(tree, zero):
    path = tree / '_data/register/reg_concern.yaml'
    text = path.read_text()
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN}) == {}
    assert path.read_text() != text
    assert _edit(tree, {'remove': 'concern_x'}) == {}
    assert path.read_text() == text


def test_remove_takes_out_the_file_of_a_standalone_item(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'concept_concept']]}) == {}
    assert _edit(tree, {'remove': 'ann_x'}) == {}
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_removing_an_item_that_is_named_is_refused(tree):
    text = (tree / '_data/register/reg_concept.yaml').read_text()
    assert _edit(tree, {'remove': 'concept_annotation'}) != {}
    assert (tree / '_data/register/reg_concept.yaml').read_text() == text


def test_rename_changes_an_entry_and_what_names_it_and_keeps_an_alias(tree):
    assert _edit(tree, {'rename': ['concept_annotation', 'concept_remark']}) == {}
    text = (tree / '_data/register/reg_concept.yaml').read_text()
    assert '  concept_remark:\n    id_self:            concept_remark\n' in text
    assert '  # concept_remark -- Annotation\n' in text
    assert '    alias:\n      - concept_annotation\n' in text
    assert 'concept_annotation' not in text.replace('      - concept_annotation\n', '')
    assert 'id_concept:         concept_remark\n' in (
        tree / '_data/register/reg_data_item_type.yaml').read_text()


def test_rename_of_a_decision_moves_its_folder(tree):
    assert _edit(tree, NEW_SUBJECT,
                       {'new': 'dec_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'lco_x']]},
                       {'new': 'opt_x', 'field': FIELD_ANN,
                        'link': [['relation_is_option_for', 'dec_x']]}) == {}
    assert _edit(tree, {'rename': ['dec_x', 'dec_y']}) == {}
    assert sorted(path.name for path in (tree / '_data/decision/dec_y').iterdir()) == [
        'dec_y.yaml', 'opt_x.yaml']
    assert not (tree / '_data/decision/dec_x').exists() or not any(
        (tree / '_data/decision/dec_x').iterdir())
    assert 'id_target:          dec_y\n' in (tree / '_data/decision/dec_y/opt_x.yaml').read_text()


def test_rename_of_a_relation_changes_the_rules_that_name_it(tree):
    assert _edit(tree, {'rename': ['relation_upholds', 'relation_endorses']}) == {}
    text = (tree / 'src/cctool/check/check.lp').read_text()
    assert '"relation_endorses"' in text
    assert '"relation_upholds"' not in text


def test_rename_moves_the_file_of_a_standalone_item_and_its_references(tree):
    assert _edit(tree, NEW_SUBJECT,
                       {'new': 'dec_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'lco_x']]},
                       {'new': 'opt_x', 'field': FIELD_ANN,
                        'link': [['relation_is_option_for', 'dec_x']]},
                       {'new': 'ann_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'opt_x']]}) == {}
    assert _edit(tree, {'rename': ['opt_x', 'opt_y']}) == {}
    assert not (tree / '_data/decision/dec_x/opt_x.yaml').exists()
    assert 'id_self:                opt_y\n' in (tree / '_data/decision/dec_x/opt_y.yaml').read_text()
    assert 'id_target:          opt_y\n' in (tree / '_data/annotation/ann_x.yaml').read_text()


ICD           = '_data/interface_control_document/icd_cctool_check.yaml'
DFG           = '_data/dataflow_graph/dfg_stableflow_smoketest.yaml'
GUID_MEMBER   = 'icm_e34e682f8f4343da97c01c1b04594c92'
GUID_ROOT     = 'icm_e58153d9700745929efb45b4d8873fe4'
GUID_NODE     = 'dfn_1ddea9503ffe480f8f98787c422c5b98'


def test_rename_of_an_interface_member_keeps_its_guid_and_adds_no_alias(tree):
    assert _edit(tree, {'rename': ['icm_cctool_check.failures',
                                   'icm_cctool_check.failure_map']}) == {}
    text = (tree / ICD).read_text()
    assert ('    id_self:            icm_cctool_check.failure_map\n'
            '    guid_self:          ' + GUID_MEMBER + '\n') in text
    assert 'icm_cctool_check.failures' not in text
    assert 'alias:' not in text


def test_rename_of_an_interface_member_renames_the_members_it_holds(tree):
    assert _edit(tree, {'rename': ['icm_cctool_check.check',
                                   'icm_cctool_check.check_tree']}) == {}
    text = (tree / ICD).read_text()
    assert ('- id_self:  icm_cctool_check.check_tree.root\n'
            '              guid_self:  ' + GUID_ROOT + '\n') in text
    assert 'icm_cctool_check.check.' not in text
    assert 'icm_cctool_check.check_documents' in text


def test_rename_of_a_dataflow_node_changes_its_key_and_what_names_it(tree):
    assert _edit(tree, {'rename': ['dfn_stableflow_smoketest.ctrl_proc',
                                   'dfn_stableflow_smoketest.proc_ctrl']}) == {}
    text = (tree / DFG).read_text()
    assert ('  proc_ctrl:\n'
            '    id_self:            dfn_stableflow_smoketest.proc_ctrl\n'
            '    guid_self:          ' + GUID_NODE + '\n') in text
    assert text.count('id_dataflow_node:  dfn_stableflow_smoketest.proc_ctrl\n') == 3
    assert 'ctrl_proc' not in text
    assert 'alias' not in text


def test_rename_of_an_interface_control_document_renames_its_members(tree):
    assert _edit(tree, {'rename': ['icd_cctool_check', 'icd_cctool_checks']}) == {}
    assert not (tree / ICD).exists()
    text = (tree / '_data/interface_control_document/icd_cctool_checks.yaml').read_text()
    assert 'id_self:                icd_cctool_checks\n' in text
    assert ('    id_self:            icm_cctool_checks.failures\n'
            '    guid_self:          ' + GUID_MEMBER + '\n') in text
    assert 'icm_cctool_checks.check.root\n' in text
    assert 'cctool_check.' not in text
    assert 'cctool_check\n' not in text


def test_rename_of_a_dataflow_graph_renames_its_nodes(tree):
    assert _edit(tree, {'rename': ['dfg_stableflow_smoketest', 'dfg_stableflow_smoke']}) == {}
    assert not (tree / DFG).exists()
    text = (tree / '_data/dataflow_graph/dfg_stableflow_smoke.yaml').read_text()
    assert ('  ctrl_proc:\n'
            '    id_self:            dfn_stableflow_smoke.ctrl_proc\n'
            '    guid_self:          ' + GUID_NODE + '\n') in text
    assert 'stableflow_smoketest' not in text


def test_set_changes_a_field_of_an_interface_member(tree):
    assert _edit(tree, {'set': ['icm_cctool_check.failures', 'name', 'FailureMap']}) == {}
    assert ('    id_self:            icm_cctool_check.failures\n'
            '    guid_self:          ' + GUID_MEMBER + '\n'
            '    name:               FailureMap\n') in (tree / ICD).read_text()


def test_new_writes_the_items_of_a_decision_in_its_folder(tree):
    assert _edit(tree, NEW_SUBJECT,
                       {'new': 'dec_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'lco_x']]},
                       {'new': 'opt_x', 'field': FIELD_ANN,
                        'link': [['relation_is_option_for', 'dec_x']]},
                       {'new': 'ann_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'dec_x']]},
                       {'new': 'ruling_x', 'field': FIELD_ANN,
                        'link': [['relation_upholds', 'opt_x']]}) == {}
    assert sorted(path.name for path in (tree / '_data/decision/dec_x').iterdir()) == [
        'ann_x.yaml', 'dec_x.yaml', 'opt_x.yaml', 'ruling_x.yaml']


def test_new_follows_an_edge_to_a_decision_made_later_in_the_batch(tree):
    assert _edit(tree, NEW_SUBJECT,
                       {'new': 'dec_x', 'field': FIELD_ANN,
                        'link': [['relation_is_about', 'lco_x']]},
                       {'new': 'ann_x', 'field': FIELD_ANN},
                       {'link': ['ann_x', 'relation_is_about', 'dec_x']}) == {}
    assert sorted(path.name for path in (tree / '_data/decision/dec_x').iterdir()) == [
        'ann_x.yaml', 'dec_x.yaml']
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


@pytest.mark.parametrize(('operation', 'message'), [
    ({'rename': ['concept_concept', 'sch_concept']},
     'A rename keeps the type, so sch_concept must have the prefix of concept_concept.'),
    ({'rename': ['concept_concept', 'concept_relation']}, 'An item with the id concept_relation exists.'),
    ({'rename': ['pym_cctool.edit.edit', 'pym_x']},
     'An item of type_python_module lives in the file it names, so move or remove the file '
     'by hand.'),
    ({'remove': 'pyf_cctool.check.check.check'},
     'An item of type_python_function lives in the file it names, so move or remove the file '
     'by hand.'),
    ({'remove': 'concept_none'}, 'No item has the id concept_none.'),
    ({'remove': 'icm_cctool_check.failures'},
     'icm_cctool_check.failures is embedded in icd_cctool_check and is not one of '
     'its entries, so take it out of icd_cctool_check with cctool unset.'),
])
def test_a_rename_or_removal_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(cctool.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_move_of_a_module_gives_its_items_the_ids_of_its_new_place(tree):
    guid = 'pym_' + (tree / 'src/cctool/check/layout.py').read_text().split(
                                                'guid_self:              pym_')[1][:32]
    assert _edit(tree, {'move': ['src/cctool/check/layout.py',
                                 'src/cctool/edit/printer.py']}) == {}
    assert not (tree / 'src/cctool/check/layout.py').exists()
    text = (tree / 'src/cctool/edit/printer.py').read_text()
    assert ('id_self:                pym_cctool.edit.printer\n'
            'guid_self:              ' + guid + '\n') in text
    text = (tree / 'src/cctool/check/check.py').read_text()
    assert 'import cctool.edit.printer\n' in text
    assert 'cctool.check.layout' not in text
    assert 'pym_cctool.check.layout' not in (tree / 'src/cctool/edit/edit.py').read_text()


def test_move_of_a_package_moves_its_files_and_renames_what_they_hold(tree):
    assert _edit(tree, {'move': ['src/cctool/check',
                                 'src/cctool/audit']}) == {}
    assert not (tree / 'src/cctool/check').exists()
    text = (tree / 'src/cctool/audit/__init__.py').read_text()
    assert 'id_self:                pyp_cctool.audit\n' in text
    text = (tree / 'src/cctool/audit/check.py').read_text()
    assert 'id_self:                pym_cctool.audit.check\n' in text
    text = (tree / 'src/cctool/audit/check.lp').read_text()
    assert 'id_self:                lpf_cctool.audit.check\n' in text
    assert re.search(r'cctool\.check\b', (tree / 'src/cctool/edit/edit.py').read_text()) is None


def test_move_of_a_module_changes_the_spelling_of_the_types_it_holds(tree):
    assert _edit(tree, {'move': ['src/cctool/graph/extract.py',
                                 'src/cctool/graph/reading.py']}) == {}
    text = (tree / '_data/interface_control_document/icd_cctool_check.yaml').read_text()
    assert 'spelling:  cctool.graph.reading.Documents\n' in text


def test_another_copy_of_a_module_does_not_change_what_an_edit_finds(tree, tmp_path_factory):
    cctool.check.check.check(tree)
    path = tmp_path_factory.mktemp('other') / 'check.py'
    path.write_text((tree / 'src/cctool/check/check.py').read_text().replace(
        'cctool.graph.extract.Documents', 'cctool.graph.reading.Documents'))
    cctool.graph.extract.read(path, pathlib.Path('src/cctool/check/check.py'))
    assert _edit(tree, {'set': ['concept_concept', 'term_admitted', ['idea']]}) == {}


def test_a_moved_name_keeps_the_lines_aligned_inside_its_brackets():
    text  = ('x = stableflo.a.f(alpha,\n'
             '                  beta(stableflo.b.g(1,\n'
             '                                     2)),\n'
             '                  gamma)\n'
             'y = (1,\n'
             '     2)\n')
    regex = re.compile(cctool.edit.edit.PATTERN_DOTTED.format(name = 'stableflo'))
    assert cctool.edit.edit._realigned(text, regex, 'flowan') == (
             'x = flowan.a.f(alpha,\n'
             '               beta(flowan.b.g(1,\n'
             '                               2)),\n'
             '               gamma)\n'
             'y = (1,\n'
             '     2)\n')


@pytest.mark.parametrize(('operation', 'message'), [
    ({'move': ['src/cctool/none.py', 'src/cctool/some.py']},
     'No file of the tree is at src/cctool/none.py.'),
    ({'move': ['src/cctool/check/layout.py', 'src/cctool/edit/edit.py']},
     'A file is at src/cctool/edit/edit.py already.'),
])
def test_a_move_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(cctool.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_header_puts_a_module_docstring_above_the_code(tree, zero):
    path = tree / 'src/cctool/edit/extra.py'
    path.write_text('import os\n')
    assert _edit(tree, {'header': 'src/cctool/edit/extra.py', 'field': FIELD_HEADER}) == {}
    assert path.read_text() == ('"""\n'
                                '---\n'
                                '\n'
                                'id_self:                pym_cctool.edit.extra\n'
                                'guid_self:              pym_' + HEX_ZERO + '\n'
                                + TEXT_RIGHTS +
                                '\n'
                                'title:                  Extra\n'
                                'brief:                  |\n'
                                '                        An extra module.\n'
                                'description:            |\n'
                                '                        It is extra.\n'
                                'edge:                   []\n'
                                '\n'
                                '...\n'
                                '"""\n'
                                '\n'
                                '\n'
                                'import os\n')


def test_header_writes_a_comment_header_after_the_interpreter_line(tree, zero):
    path = tree / 'tool/run'
    path.parent.mkdir()
    path.write_text('#!/bin/sh\necho run\n')
    assert _edit(tree, {'header': 'tool/run', 'id': 'file_tool_run', 'field': FIELD_HEADER}) == {}
    text = path.read_text()
    assert text.startswith('#!/bin/sh\n# ---\n#\n# id_self:                file_tool_run\n')
    assert text.endswith('#\n# ...\n\necho run\n')


def test_header_writes_a_style_sheet_header_in_a_comment_block_of_its_own(tree, zero):
    path = tree / 'tool/look.css'
    path.parent.mkdir()
    path.write_text('p {\n  color: black;\n}\n')
    assert _edit(tree, {'header': 'tool/look.css', 'id': 'file_tool_look',
                        'field': FIELD_HEADER}) == {}
    text = path.read_text()
    assert text.startswith('/*\n * ---\n *\n * id_self:                file_tool_look\n')
    assert text.endswith(' *\n * ...\n */\n\np {\n  color: black;\n}\n')


def test_header_writes_a_style_sheet_header_into_the_block_it_opens_with(tree, zero):
    path = tree / 'tool/look.css'
    path.parent.mkdir()
    path.write_text('/*\n * Plain.\n */\n\np {}\n')
    assert _edit(tree, {'header': 'tool/look.css', 'id': 'file_tool_look',
                        'field': FIELD_HEADER}) == {}
    text = path.read_text()
    assert text.startswith('/*\n * ---\n')
    assert text.endswith(' * ...\n *\n * Plain.\n */\n\np {}\n')


def test_header_writes_a_script_header_after_its_line_marker(tree, zero):
    path = tree / 'tool/run.js'
    path.parent.mkdir()
    path.write_text('var x = 1;\n')
    assert _edit(tree, {'header': 'tool/run.js', 'id': 'file_tool_run',
                        'field': FIELD_HEADER}) == {}
    text = path.read_text()
    assert text.startswith('// ---\n//\n// id_self:                file_tool_run\n')
    assert text.endswith('//\n// ...\n\nvar x = 1;\n')


def test_header_makes_a_logic_program_file_that_is_not_there(tree, zero):
    assert _edit(tree, {'header': 'src/cctool/edit/extra.lp', 'field': FIELD_HEADER}) == {}
    text = (tree / 'src/cctool/edit/extra.lp').read_text()
    assert text.startswith('% ---\n%\n% id_self:                lpf_cctool.edit.extra\n')
    assert text.endswith('% edge:                   []\n%\n% ...\n')


@pytest.mark.parametrize(('operation', 'message'), [
    ({'header': 'README.md', 'id': 'file_readme'}, ('README.md cannot hold a header. A YAML, JSON or Markdown file is a '
                                                     'document: make its items with cctool new.')),
    ({'header': 'src/cctool/edit/extra.py', 'id': 'pym_extra'},
     'The item of src/cctool/edit/extra.py has the id pym_cctool.edit.extra, not pym_extra.'),
    ({'header': 'tool/run'}, 'Give the id of the item of tool/run.'),
    ({'header': 'src/cctool/edit/edit.py'}, 'src/cctool/edit/edit.py already holds an item.'),
    ({'header': 'tool/run', 'id': 'zzz_run'}, 'No type has the prefix zzz. reg_data_item_type.yaml lists the types.'),
])
def test_a_header_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(cctool.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_header_turns_the_docstring_of_a_method_into_its_item(tree, zero):
    path = tree / 'src/cctool/edit/extra.py'
    path.write_text('class Extra:\n'
                    '\n'
                    '    def run(self):\n'
                    '        """\n'
                    '        Run it.\n'
                    '\n'
                    '        """\n'
                    '\n'
                    '        return 1\n')
    assert _edit(tree, {'header': 'src/cctool/edit/extra.py', 'field': FIELD_HEADER},
                       {'header': 'src/cctool/edit/extra.py::Extra::run',
                        'field':  {'title': 'Run'}}) == {}
    text = path.read_text()
    assert text[text.index('class Extra'):] == (
        'class Extra:\n'
        '\n'
        '    def run(self):\n'
        '        """\n'
        '        ---\n'
        '\n'
        '        id_self:                pyf_cctool.edit.extra.extra.run\n'
        '        guid_self:              pyf_' + HEX_ZERO + '\n'
        + ''.join('        ' + line if line.strip() else line
                  for line in TEXT_RIGHTS.splitlines(True)) +
        '\n'
        '        title:                  Run\n'
        '        brief:                  |\n'
        '                                Run it.\n'
        '        edge:                   []\n'
        '\n'
        '        ...\n'
        '        """\n'
        '\n'
        '        return 1\n')


def test_header_writes_a_docstring_for_a_function_without_one(tree, zero):
    path = tree / 'src/cctool/edit/extra.py'
    path.write_text('def run():\n    return 1\n')
    assert _edit(tree, {'header': 'src/cctool/edit/extra.py', 'field': FIELD_HEADER},
                       {'header': 'src/cctool/edit/extra.py::run',
                        'field':  {'title': 'Run', 'brief': 'Run it.'}}) == {}
    text = path.read_text()
    assert text[text.index('def run'):].startswith('def run():\n    """\n    ---\n\n')
    assert text.endswith('    ...\n    """\n\n    return 1\n')


def test_a_link_from_the_item_of_a_function_keeps_its_indentation(tree):
    path = tree / 'src/cctool/check/check.py'
    assert _edit(tree, {'link': ['pyf_cctool.check.check.check', 'relation_realizes',
                                 'lco_tooling']}) == {}
    assert ('    edge:\n'
            '\n'
            '      - id_relation:        relation_realizes\n') in path.read_text()


@pytest.mark.parametrize(('operation', 'message'), [
    ({'header': 'src/cctool/check/check.py::nothing'},
     'src/cctool/check/check.py has no class or function nothing there.'),
    ({'header': 'src/cctool/graph/jq.py::query', 'id': 'pyf_x'},
     'The item of src/cctool/graph/jq.py::query has the id '
     'pyf_cctool.graph.jq.query, not pyf_x.'),
    ({'header': 'src/cctool/check/check.py::check'},
     'src/cctool/check/check.py::check already holds an item.'),
    ({'header': 'README.md::check'},
     'README.md is not a python module or a logic program.'),
    ({'header': 'src/cctool/check/check.lp::nothing'},
     'src/cctool/check/check.lp declares no predicate nothing.'),
    ({'header': 'src/cctool/check/check.lp::bad_id'},
     'src/cctool/check/check.lp::bad_id already holds an item.'),
])
def test_a_header_on_a_definition_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(cctool.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_header_turns_the_comment_above_a_predicate_into_its_item(tree, zero):
    path = tree / 'src/cctool/edit/extra.lp'
    assert _edit(tree, {'header': 'src/cctool/edit/extra.lp', 'field': FIELD_HEADER}) == {}
    path.write_text(path.read_text()
                    + '\n\n% ' + '-' * 77 + '\n'
                    + '% Every item is odd.\n'
                    + '%\n'
                    + '% decl odd(id: symbol)\n'
                    + '#show odd/1.\n')
    assert _edit(tree, {'header': 'src/cctool/edit/extra.lp::odd',
                        'field':  {'did': '{id} is odd, and stays odd.',
                                   'fix': 'Make it even.'}}) == {}
    text = path.read_text()
    assert text[text.index('% ' + '-' * 77):] == (
        '% ' + '-' * 77 + '\n'
        '% ---\n'
        '%\n'
        '% id_self:                lpp_cctool.edit.extra.odd\n'
        '% guid_self:              lpp_' + HEX_ZERO + '\n'
        + ''.join('% ' + line if line.strip() else '%\n'
                  for line in TEXT_RIGHTS.splitlines(True)) +
        '%\n'
        '% title:                  Odd\n'
        '% brief:                  |\n'
        '%                         Every item is odd.\n'
        "% did:                    '{id} is odd, and stays odd.'\n"
        '% fix:                    Make it even.\n'
        '% edge:                   []\n'
        '%\n'
        '% ...\n'
        '%\n'
        '% decl odd(id: symbol)\n'
        '#show odd/1.\n')
    documents = cctool.graph.extract.documents(tree)
    assert documents['src/cctool/edit/extra.lp::odd'][0]['id_self'] == \
        'lpp_cctool.edit.extra.odd'
    assert cctool.graph.logic.worded(text) == {'odd': {'did': '{id} is odd, and stays odd.',
                                                       'fix': 'Make it even.'}}


def test_the_document_of_a_function_is_laid_out_at_its_indentation():
    text = ('def run():\n'
            '    """\n'
            '    ---\n'
            '    id_self: pyf_x.run\n'
            '    brief: |\n'
            '      Run it.\n'
            '    ...\n'
            '    """\n')
    assert cctool.check.layout.format_file(text, pathlib.Path('src/x.py')) == (
        'def run():\n'
        '    """\n'
        '    ---\n'
        '\n'
        '    id_self:                pyf_x.run\n'
        '    brief:                  |\n'
        '                            Run it.\n'
        '\n'
        '    ...\n'
        '    """\n')


def test_header_refuses_a_module_with_a_docstring_already(tree):
    (tree / 'src/cctool/edit/extra.py').write_text('"""Extra."""\n')
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(cctool.edit.edit.Tree(tree),
                               [{'header': 'src/cctool/edit/extra.py'}])
    assert str(info.value).startswith('src/cctool/edit/extra.py has a module docstring that '
                                      'is not an item.')


def test_set_rewrites_a_field_in_a_comment_header(tree):
    path = tree / 'src/cctool/graph/derive.lp'
    text = path.read_text()
    assert _edit(tree, {'set': ['lpf_cctool.graph.derive', 'brief', 'Derived predicates.']}) == {}
    assert path.read_text() == text.replace(
        '% brief:                  |\n'
        '%                         The predicates derived from the base ones, for\n'
        '%                         every program over the graph of data items.\n',
        '% brief:                  |\n'
        '%                         Derived predicates.\n')


def test_set_adds_a_field_after_the_one_before_it_in_order(tree):
    path = tree / 'src/cctool/edit/_test/test_edit.py'
    text = path.read_text()
    assert _edit(tree, {'set': ['pym_cctool.edit._test.test_edit', 'usage', 'By pytest.']}) == {}
    assert path.read_text() == text.replace(
        '                        zeros, so that the text is known.\n',
        '                        zeros, so that the text is known.\n'
        'usage:                  |\n'
        '                        By pytest.\n', 1)


def test_unlink_takes_one_edge_out_and_keeps_the_others(tree):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['relation_is_about', 'concept_concept'], ['relation_is_about', 'concept_relation']]},
                       {'unlink': ['ann_x', 'relation_is_about', 'concept_relation']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        'whatever they change.\n\n' + TEXT_ABOUT)


def test_unlink_of_the_last_edge_leaves_an_empty_edge_field(tree):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'new': 'ann_x', 'field': FIELD_ANN,
                                     'link': [['relation_is_about', 'concept_concept']]},
                                    {'unlink': ['ann_x', 'relation_is_about', 'concept_concept']}])
    assert edited.edit['_data/annotation/ann_x.yaml'].endswith(
        'whatever they change.\nedge:                   []\n')


def test_unset_takes_out_a_field_that_set_added(tree):
    path = tree / 'src/cctool/edit/_test/test_edit.py'
    text = path.read_text()
    assert _edit(tree, {'set': ['pym_cctool.edit._test.test_edit', 'usage', 'By pytest.']},
                       {'unset': ['pym_cctool.edit._test.test_edit', 'usage']}) == {}
    assert path.read_text() == text


def test_set_takes_a_structured_value_and_a_path_into_one(tree, zero):
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN},
                       {'set': ['concern_x', 'measure', ['Lines changed.', 'Files changed.']]},
                       {'set': ['concern_x', 'question.0', 'Can it be read?']}) == {}
    text = (tree / '_data/register/reg_concern.yaml').read_text()
    assert ('    question:\n      - Can it be read?\n\n'
            '    measure:\n      - Lines changed.\n      - Files changed.\n') in text


def test_set_by_path_keeps_prose_as_a_block(tree):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'set': ['sch_commit',
                                             'allOf.3.properties.title.description',
                                             'A subject line.']}])
    assert ('        description:    |\n'
            '                        A subject line.\n') in (
                edited.edit['_data/schema/sch_commit.yaml'])


def test_a_field_that_names_an_item_keeps_its_guid_beside_it(tree):
    path   = 'src/cctool/check/layout.py'
    id_pym = 'pym_cctool.check.layout'
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'unset': [id_pym, 'protective_mark.0.id_mark']}])
    assert 'protective_mark:\n  - {}\n' in edited.edit[path]
    assert 'id_mark' not in edited.edit[path]
    cctool.edit.edit.batch(edited, [{'set': [id_pym, 'protective_mark.0.id_mark',
                                             'mark_public']}])
    assert edited.edit[path] == (tree / path).read_text()


def test_set_of_a_field_that_names_an_item_changes_its_guid(tree):
    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'set': ['type_annotation', 'id_concept', 'concept_concept']}])
    assert ('    id_concept:         concept_concept\n'
            '    guid_concept:       concept_4c11efe184cd47289cfa3941377d4807\n') in (
                edited.edit['_data/register/reg_data_item_type.yaml'])


@pytest.mark.parametrize(('operation', 'message'), [
    ({'new': 'zzz_x'}, 'No type has the prefix zzz. reg_data_item_type.yaml lists the types.'),
    ({'new': 'concept_concept'}, 'An item with the id concept_concept exists.'),
    ({'new': 'pym_x'}, 'An item of type_python_module is written in the file it names: give the '
                       'file its item with header.'),
    ({'new': 'ann_x', 'link': [['relation_is_about', 'concept_none']]}, 'No item has the id concept_none.'),
    ({'link': ['concept_concept', 'relation_is_about', 'concept_concept']}, 'concept_concept already has that edge.'),
    ({'set': ['concept_concept', 'id_self', 'concept_y']}, 'The field id_self is not set this way: cctool rename changes an id.'),
    ({'set': ['concept_none', 'note', 'x']}, 'No item has the id concept_none.'),
    ({'unlink': ['concept_concept']}, "An operation of a batch is not one of new, header, link, "
                                  "unlink, set, unset, remove, rename or move: "
                                  "{'unlink': ['concept_concept']}"),
    ({'unlink': ['concept_concept', 'relation_is_about', 'concept_type']},
     'concept_concept has no edge of relation_is_about to concept_type.'),
    ({'unset': ['concept_type', 'note']}, 'concept_type has no field note.'),
    ({'unset': ['concept_concept', 'alias']}, ('The field alias is not set this way: cctool rename keeps the old id '
                                                  'as an alias.')),
    ({'set': ['concept_register_entry', 'term_admitted.9', 'x']},
     '9 is not the index of an element of a list of 2.'),
    ({'set': ['concept_concept', 'title.x', 'x']},
     'The path goes into Concept, which has no fields.'),
])
def test_an_edit_that_cannot_be_made_says_why(tree, operation, message):
    edited = cctool.edit.edit.Tree(tree)
    if operation.get('link') and operation['link'][0] == 'concept_concept':
        cctool.edit.edit.batch(edited, [{'link': ['concept_concept', 'relation_is_about', 'concept_concept']}])
    with pytest.raises(cctool.edit.edit.ErrorEdit) as info:
        cctool.edit.edit.batch(edited, [operation])
    assert str(info.value) == message


# -----------------------------------------------------------------------------
def _params_document() -> list:
    """
    Return a parameter for each file of the repository that holds a YAML
    document. All but the first file of each folder are marked slow, so
    that the gate lays out one file of each kind and the slow run all.

    """

    list_param  = []
    set_folder  = set()

    for relative in cctool.graph.extract.files(cctool.graph.extract.documents(DIR_REPO)):
        folder = str(pathlib.Path(relative).parent)
        if folder in set_folder:
            list_param.append(pytest.param(relative, marks = pytest.mark.slow))
        else:
            set_folder.add(folder)
            list_param.append(relative)

    return list_param


@pytest.mark.reads_data
@pytest.mark.parametrize('relative', _params_document())
def test_layout_keeps_the_data_and_is_a_fixpoint(relative):
    text     = (DIR_REPO / relative).read_text()
    laid_out = cctool.check.layout.format_file(text, pathlib.Path(relative))
    assert cctool.check.layout.format_file(laid_out, pathlib.Path(relative)) == laid_out
    assert _shapes(laid_out, relative) == _shapes(text, relative)


def test_prose_is_refilled_by_paragraph_and_other_scalars_are_left_alone():
    text = ('note:                   |\n'
            '                        One\n'
            '                        two.\n'
            '\n'
            '                        Three.\n'
            'pattern:                ^(a b|c d)[0-9]{4} ' + 'x' * 70 + '$\n')
    assert cctool.check.layout.format(text) == (
            'note:                   |\n'
            '                        One two.\n'
            '\n'
            '                        Three.\n'
            'pattern:                ^(a b|c d)[0-9]{4} ' + 'x' * 70 + '$\n')


@pytest.mark.parametrize(('text', 'message'), [
    ('a: 1  # why\nb: 2\n',          'The document has a comment at the end of line 1.'),
    ('a:\n  - x\n  - y  # why\n',   'The document has a comment at the end of line 3.'),
    ('a: &n 1\nb: 2\n',              'The document has an anchor, &n.'),
    ('a: !t 1\n',                    'The document has a tag, !t.'),
    ('a: !t {k: 1}\n',               'The document has a tag, !t.'),
])
def test_what_the_printer_would_drop_or_expand_is_refused(text, message):
    with pytest.raises(cctool.check.layout.Unsupported) as info:
        cctool.check.layout.format(text)
    assert str(info.value) == message


def test_a_comment_on_a_line_of_its_own_is_kept():
    text = 'a:                      1\n\n# Why b.\nb:                      2\n'
    assert cctool.check.layout.format(text) == text


def test_set_keeps_a_field_written_as_a_block_as_a_block(tree):
    assert _edit(tree, {'set': ['style_write_for_the_reader', 'follows', 'One. Two.']}) == {}
    text = (tree / '_data/register/reg_writing_style_rule.yaml').read_text()
    assert '    follows:            |\n                        One. Two.\n' in text


def test_a_filled_line_never_opens_with_a_list_marker():
    text = ('note:                   |\n'
            '                        wordy ' + 'word ' * 7 + 'and 2. more words to fill the line up.\n')
    laid_out = cctool.check.layout.format(text)
    assert [line.split()[0] for line in laid_out.split('\n')[1:] if line] == ['wordy', 'and']
    assert cctool.check.layout.format(laid_out) == laid_out


def test_a_link_to_a_concept_is_never_broken_across_lines():
    text = ('note:                   |\n'
            '                        A function or method defined in a [[python module]],\n'
            '                        at the top.\n')
    laid_out = cctool.check.layout.format(text)
    assert '[[python module]],' in laid_out
    assert cctool.check.layout.format(laid_out) == laid_out


def test_each_item_of_a_list_in_prose_is_filled_on_its_own():
    text = ('note:                   |\n'
            '                        A list:\n'
            '                        - one\n'
            '                        - two, which goes on ' + 'and on ' * 6 + 'to the end.\n'
            '                        1. three\n')
    laid_out = cctool.check.layout.format(text)
    assert laid_out == (
            'note:                   |\n'
            '                        A list:\n'
            '                        - one\n'
            '                        - two, which goes on and on and on and on and\n'
            '                          on and on and on to the end.\n'
            '                        1. three\n')
    assert cctool.check.layout.format(laid_out) == laid_out


def test_blank_lines_set_apart_lists_and_comments():
    text = ('a: 1\nlist: [x, y]\nb: 2\n# A comment.\nc: 3\n')
    assert cctool.check.layout.format(text) == ('a:                      1\n'
                                                '\n'
                                                'list:\n'
                                                '  - x\n'
                                                '  - y\n'
                                                '\n'
                                                'b:                      2\n'
                                                '\n'
                                                '# A comment.\n'
                                                'c:                      3\n')


def test_a_comment_header_is_laid_out_inside_its_markers():
    text = '% ---\n% id_self: lpf_x\n% ...\n\n% decl x(id)\n'
    assert cctool.check.layout.format_file(text, pathlib.Path('src/x.lp')) == (
        '% ---\n%\n% id_self:                lpf_x\n%\n% ...\n\n% decl x(id)\n')


def test_a_comment_header_after_an_interpreter_line_is_laid_out():
    text = '#!/bin/sh\n# ---\n# id_self: file_x\n# ...\n\nexit 0\n'
    assert cctool.check.layout.format_file(text, pathlib.Path('x')) == (
        '#!/bin/sh\n# ---\n#\n# id_self:                file_x\n#\n# ...\n\nexit 0\n')


def test_an_empty_mapping_in_a_list_is_kept():
    assert cctool.check.layout.format('a:\n  - {}\n') == 'a:\n  - {}\n'


def test_a_document_outside_the_subset_is_refused():
    with pytest.raises(cctool.check.layout.Unsupported):
        cctool.check.layout.format('- a\n- b\n')


# -----------------------------------------------------------------------------
def _shapes(text, relative):
    """
    Return the shape of each YAML document text holds, as the content of
    the file at relative, by its key.

    """

    return {key: _shape(document) for (key, (document, _))
            in cctool.graph.extract.parse_all(text, pathlib.Path(relative)).items()}


# -----------------------------------------------------------------------------
def _shape(node):
    """
    Return node with each literal block reduced to its words, so that
    two YAML documents compare equal when only the breaks in their prose
    differ.

    """

    if isinstance(node, dict):
        return {key: _shape(value) for (key, value) in node.items()}
    if isinstance(node, list):
        return [_shape(value) for value in node]
    if isinstance(node, ruamel.yaml.scalarstring.LiteralScalarString):
        return ('|', ' '.join(node.split()))
    return node
