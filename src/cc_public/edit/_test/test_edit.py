"""
---

id_self:                pym_cc_public.edit._test.test_edit
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
relation:               []

...
"""


import pathlib

import pytest
import ruamel.yaml.scalarstring

import cc_public.edit.edit
import cc_public.edit.layout
import cc_public.graph.extract
from cc_public.conftest import DIR_REPO


HEX_ZERO      = '0' * 32
TEXT_ABOUT    = ('relation:\n'
                 '\n'
                 '  - id_relation:        r_is_about\n'
                 '    guid_relation:      r_17ca99102b0b431b85235445a4635ae8\n'
                 '    id_target:          con_concept\n'
                 '    guid_target:        con_820f9604e6134b9fbefd5a75146d4c40\n')
TEXT_RIGHTS   = ('copyright:              Copyright 2026 William Payne\n'
                 'license:                Apache-2.0\n'
                 '\n'
                 'protective_mark:\n'
                 '\n'
                 '  - id_mark:            mark_public\n'
                 '    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f\n')
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

    monkeypatch.setattr(cc_public.edit.edit.uuid, 'uuid4', lambda: type('U', (), {'hex': HEX_ZERO}))


# -----------------------------------------------------------------------------
def _edit(tree, *list_operation, is_written = True):
    """
    Make the operations over tree as one edit, and return the failures
    it adds.

    """

    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, list(list_operation))
    return cc_public.edit.edit.apply(edited, is_written = is_written)


def test_a_new_standalone_item_is_written_in_a_file_of_its_own(tree, zero):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['r_is_about', 'con_concept']]}) == {}
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
                        'link':  [['r_is_about', 'concern_x']]}) == {}
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
        '    relation:           []\n')


def test_an_edit_that_adds_a_failure_is_refused_and_not_written(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN}) == {'missing_about': [('ann_x',)]}
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_a_failure_the_tree_already_has_is_not_added(tree):
    path = tree / '_data/register/reg_concept.yaml'
    path.write_text(path.read_text().replace('guid_self:          con_820f9604',
                                             'guid_self:          con_820f9605'))
    assert _edit(tree, {'set': ['con_concept', 'note', 'A note.']}) == {}


def test_a_new_concept_needs_an_item_that_names_it(tree):
    field = {'title': 'X', 'brief': 'X.', 'description': 'X.', 'term_preferred': 'x'}
    assert _edit(tree, {'new': 'con_x', 'field': field}) == {'unused_concept': [('con_x',)]}
    assert _edit(tree, {'new': 'con_x', 'field': field},
                       {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['r_is_about', 'con_x']]}) == {}


def test_a_new_schema_opens_with_its_dialect_and_keeps_structured_values(tree, zero):
    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, [{'new':   'sch_x',
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


def test_a_new_field_that_names_an_item_is_given_its_guid(tree, zero):
    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, [{'new':   't_x',
                                        'field': {'title':      'X type',
                                                  'brief':      'X.',
                                                  'id_concept': 'con_concept'}}])
    assert ('    id_concept:         con_concept\n'
            '    guid_concept:       con_820f9604e6134b9fbefd5a75146d4c40\n') in (
        edited.text('_data/register/reg_data_item_type.yaml'))


def test_a_link_turns_an_empty_relation_into_a_list(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN, 'link': []},
                       {'link': ['ann_x', 'r_is_about', 'con_concept']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        'whatever they change.\n\n' + TEXT_ABOUT)


def test_a_link_is_added_after_the_edges_there_are(tree):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['r_is_about', 'con_concept']]},
                       {'link': ['ann_x', 'r_is_about', 'con_relation']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        TEXT_ABOUT
        + '\n'
        '  - id_relation:        r_is_about\n'
        '    guid_relation:      r_17ca99102b0b431b85235445a4635ae8\n'
        '    id_target:          con_relation\n'
        '    guid_target:        con_58ca7869cf9443168d8d96d8d70b972c\n')


def test_remove_takes_out_a_register_entry_and_its_banner(tree, zero):
    path = tree / '_data/register/reg_concern.yaml'
    text = path.read_text()
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN}) == {}
    assert path.read_text() != text
    assert _edit(tree, {'remove': 'concern_x'}) == {}
    assert path.read_text() == text


def test_remove_takes_out_the_file_of_a_standalone_item(tree):
    assert _edit(tree, {'new': 'ann_x', 'field': FIELD_ANN,
                        'link': [['r_is_about', 'con_concept']]}) == {}
    assert _edit(tree, {'remove': 'ann_x'}) == {}
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_removing_an_item_that_is_named_is_refused(tree):
    text = (tree / '_data/register/reg_concept.yaml').read_text()
    assert _edit(tree, {'remove': 'con_annotation'}) != {}
    assert (tree / '_data/register/reg_concept.yaml').read_text() == text


def test_rename_changes_an_entry_and_what_names_it_and_keeps_an_alias(tree):
    assert _edit(tree, {'rename': ['con_annotation', 'con_remark']}) == {}
    text = (tree / '_data/register/reg_concept.yaml').read_text()
    assert '  con_remark:\n    id_self:            con_remark\n' in text
    assert '  # con_remark -- Annotation\n' in text
    assert '    alias:\n      - con_annotation\n' in text
    assert 'con_annotation' not in text.replace('      - con_annotation\n', '')
    assert 'id_concept:         con_remark\n' in (
        tree / '_data/register/reg_data_item_type.yaml').read_text()


def test_rename_moves_the_file_of_a_standalone_item_and_its_references(tree):
    assert _edit(tree, {'new': 'dec_x', 'field': FIELD_ANN,
                        'link': [['r_is_about', 'con_concept']]},
                       {'new': 'ann_x', 'field': FIELD_ANN,
                        'link': [['r_is_about', 'dec_x']]}) == {}
    assert _edit(tree, {'rename': ['dec_x', 'dec_y']}) == {}
    assert not (tree / '_data/decision/dec_x.yaml').exists()
    assert 'id_self:                dec_y\n' in (tree / '_data/decision/dec_y.yaml').read_text()
    assert 'id_target:          dec_y\n' in (tree / '_data/annotation/ann_x.yaml').read_text()


@pytest.mark.parametrize(('operation', 'message'), [
    ({'rename': ['con_concept', 'sch_concept']},
     'A rename keeps the type, so sch_concept must have the prefix of con_concept.'),
    ({'rename': ['con_concept', 'con_relation']}, 'An item with the id con_relation exists.'),
    ({'rename': ['pym_cc_public.edit.edit', 'pym_x']},
     'An item of t_python_module lives in the file it names, so move or remove the file '
     'by hand.'),
    ({'remove': 'con_none'}, 'No item has the id con_none.'),
])
def test_a_rename_or_removal_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cc_public.edit.edit.ErrorEdit) as info:
        cc_public.edit.edit.batch(cc_public.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_header_puts_a_module_docstring_above_the_code(tree, zero):
    path = tree / 'src/cc_public/edit/extra.py'
    path.write_text('import os\n')
    assert _edit(tree, {'header': 'src/cc_public/edit/extra.py', 'field': FIELD_HEADER}) == {}
    assert path.read_text() == ('"""\n'
                                '---\n'
                                '\n'
                                'id_self:                pym_cc_public.edit.extra\n'
                                'guid_self:              pym_' + HEX_ZERO + '\n'
                                + TEXT_RIGHTS +
                                '\n'
                                'title:                  Extra\n'
                                'brief:                  |\n'
                                '                        An extra module.\n'
                                'description:            |\n'
                                '                        It is extra.\n'
                                'relation:               []\n'
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
    assert text.endswith('#\n# ...\n\n\necho run\n')


def test_header_makes_a_datalog_file_that_is_not_there(tree, zero):
    assert _edit(tree, {'header': 'src/cc_public/edit/extra.dl', 'field': FIELD_HEADER}) == {}
    text = (tree / 'src/cc_public/edit/extra.dl').read_text()
    assert text.startswith('// ---\n//\n// id_self:                dls_cc_public.edit.extra\n')
    assert text.endswith('// relation:               []\n//\n// ...\n')


@pytest.mark.parametrize(('operation', 'message'), [
    ({'header': 'README.md', 'id': 'file_readme'}, 'README.md cannot hold a header.'),
    ({'header': 'src/cc_public/edit/extra.py', 'id': 'pym_extra'},
     'The item of src/cc_public/edit/extra.py has the id pym_cc_public.edit.extra, not pym_extra.'),
    ({'header': 'tool/run'}, 'Give the id of the item of tool/run.'),
    ({'header': 'src/cc_public/edit/edit.py'}, 'src/cc_public/edit/edit.py already holds an item.'),
    ({'header': 'tool/run', 'id': 'zzz_run'}, 'No type has the prefix zzz.'),
])
def test_a_header_that_cannot_be_made_says_why(tree, operation, message):
    with pytest.raises(cc_public.edit.edit.ErrorEdit) as info:
        cc_public.edit.edit.batch(cc_public.edit.edit.Tree(tree), [operation])
    assert str(info.value) == message


def test_header_refuses_a_module_with_a_docstring_already(tree):
    (tree / 'src/cc_public/edit/extra.py').write_text('"""Extra."""\n')
    with pytest.raises(cc_public.edit.edit.ErrorEdit) as info:
        cc_public.edit.edit.batch(cc_public.edit.edit.Tree(tree),
                                  [{'header': 'src/cc_public/edit/extra.py'}])
    assert str(info.value).startswith('src/cc_public/edit/extra.py has a module docstring that '
                                      'is not an item.')


def test_set_rewrites_a_field_in_a_comment_header(tree):
    path = tree / 'src/cc_public/graph/derive.dl'
    text = path.read_text()
    assert _edit(tree, {'set': ['dls_cc_public.graph.derive', 'brief', 'Derived relations.']}) == {}
    assert path.read_text() == text.replace(
        '// brief:                  |\n'
        '//                         Relations derived from the base relations, for\n'
        '//                         every Datalog program over the graph of data\n'
        '//                         items.\n',
        '// brief:                  |\n'
        '//                         Derived relations.\n')


def test_set_adds_a_field_after_the_one_before_it_in_order(tree):
    path = tree / 'src/cc_public/edit/_test/test_edit.py'
    text = path.read_text()
    assert _edit(tree, {'set': ['pym_cc_public.edit._test.test_edit', 'usage', 'By pytest.']}) == {}
    assert path.read_text() == text.replace(
        '                        zeros, so that the text is known.\n',
        '                        zeros, so that the text is known.\n'
        'usage:                  |\n'
        '                        By pytest.\n', 1)


def test_unlink_takes_one_edge_out_and_keeps_the_others(tree):
    assert _edit(tree, {'new':   'ann_x',
                        'field': FIELD_ANN,
                        'link':  [['r_is_about', 'con_concept'], ['r_is_about', 'con_relation']]},
                       {'unlink': ['ann_x', 'r_is_about', 'con_relation']}) == {}
    assert (tree / '_data/annotation/ann_x.yaml').read_text().endswith(
        'whatever they change.\n\n' + TEXT_ABOUT)


def test_unlink_of_the_last_edge_leaves_an_empty_relation(tree):
    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, [{'new': 'ann_x', 'field': FIELD_ANN,
                                        'link': [['r_is_about', 'con_concept']]},
                                       {'unlink': ['ann_x', 'r_is_about', 'con_concept']}])
    assert edited.edit['_data/annotation/ann_x.yaml'].endswith(
        'whatever they change.\nrelation:               []\n')


def test_unset_takes_out_a_field_that_set_added(tree):
    path = tree / 'src/cc_public/edit/_test/test_edit.py'
    text = path.read_text()
    assert _edit(tree, {'set': ['pym_cc_public.edit._test.test_edit', 'usage', 'By pytest.']},
                       {'unset': ['pym_cc_public.edit._test.test_edit', 'usage']}) == {}
    assert path.read_text() == text


def test_set_takes_a_structured_value_and_a_path_into_one(tree, zero):
    assert _edit(tree, {'new': 'concern_x', 'field': FIELD_CONCERN},
                       {'set': ['concern_x', 'measure', ['Lines changed.', 'Files changed.']]},
                       {'set': ['concern_x', 'question.0', 'Can it be read?']}) == {}
    text = (tree / '_data/register/reg_concern.yaml').read_text()
    assert ('    question:\n      - Can it be read?\n\n'
            '    measure:\n      - Lines changed.\n      - Files changed.\n') in text


def test_a_field_that_names_an_item_keeps_its_guid_beside_it(tree):
    path   = 'src/cc_public/edit/layout.py'
    id_pym = 'pym_cc_public.edit.layout'
    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, [{'unset': [id_pym, 'protective_mark.0.id_mark']}])
    assert 'protective_mark:\n  - {}\n' in edited.edit[path]
    assert 'id_mark' not in edited.edit[path]
    cc_public.edit.edit.batch(edited, [{'set': [id_pym, 'protective_mark.0.id_mark',
                                                'mark_public']}])
    assert edited.edit[path] == (tree / path).read_text()


def test_set_of_a_field_that_names_an_item_changes_its_guid(tree):
    edited = cc_public.edit.edit.Tree(tree)
    cc_public.edit.edit.batch(edited, [{'set': ['t_annotation', 'id_concept', 'con_concept']}])
    assert ('    id_concept:         con_concept\n'
            '    guid_concept:       con_820f9604e6134b9fbefd5a75146d4c40\n') in (
                edited.edit['_data/register/reg_data_item_type.yaml'])


@pytest.mark.parametrize(('operation', 'message'), [
    ({'new': 'zzz_x'}, 'No type has the prefix zzz.'),
    ({'new': 'con_concept'}, 'An item with the id con_concept exists.'),
    ({'new': 'pym_x'}, 'An item of t_python_module is written in the file it names: give the '
                       'file its item with header.'),
    ({'new': 'ann_x', 'link': [['r_is_about', 'con_none']]}, 'No item has the id con_none.'),
    ({'link': ['con_concept', 'r_is_about', 'con_concept']}, 'con_concept already has that edge.'),
    ({'set': ['con_concept', 'id_self', 'con_y']}, 'The field id_self is not set this way.'),
    ({'set': ['con_none', 'note', 'x']}, 'No item has the id con_none.'),
    ({'unlink': ['con_concept']}, "An operation of a batch is not one of new, header, link, "
                                  "unlink, set, unset, remove or rename: "
                                  "{'unlink': ['con_concept']}"),
    ({'unlink': ['con_concept', 'r_is_about', 'con_type']},
     'con_concept has no edge of r_is_about to con_type.'),
    ({'unset': ['con_concept', 'note']}, 'con_concept has no field note.'),
    ({'unset': ['con_concept', 'alias']}, 'The field alias is not set this way.'),
    ({'set': ['con_register_entry', 'term_admitted.9', 'x']},
     '9 is not the index of an element of a list of 1.'),
    ({'set': ['con_concept', 'title.x', 'x']},
     'The path goes into Concept, which has no fields.'),
])
def test_an_edit_that_cannot_be_made_says_why(tree, operation, message):
    edited = cc_public.edit.edit.Tree(tree)
    if operation.get('link') and operation['link'][0] == 'con_concept':
        cc_public.edit.edit.batch(edited, [{'link': ['con_concept', 'r_is_about', 'con_concept']}])
    with pytest.raises(cc_public.edit.edit.ErrorEdit) as info:
        cc_public.edit.edit.batch(edited, [operation])
    assert str(info.value) == message


@pytest.mark.parametrize('relative', sorted(
    relative for (relative, (document, _))
    in cc_public.graph.extract.documents(DIR_REPO).items() if document is not None))
def test_layout_keeps_the_data_and_is_a_fixpoint(relative):
    text     = (DIR_REPO / relative).read_text()
    laid_out = cc_public.edit.layout.format_file(text, pathlib.Path(relative))
    assert cc_public.edit.layout.format_file(laid_out, pathlib.Path(relative)) == laid_out
    assert _shape(cc_public.graph.extract.parse(laid_out, pathlib.Path(relative))[0]) == (
           _shape(cc_public.graph.extract.parse(text, pathlib.Path(relative))[0]))


def test_prose_is_refilled_by_paragraph_and_other_scalars_are_left_alone():
    text = ('note:                   |\n'
            '                        One\n'
            '                        two.\n'
            '\n'
            '                        Three.\n'
            'pattern:                ^(a b|c d)[0-9]{4} ' + 'x' * 70 + '$\n')
    assert cc_public.edit.layout.format(text) == (
            'note:                   |\n'
            '                        One two.\n'
            '\n'
            '                        Three.\n'
            'pattern:                ^(a b|c d)[0-9]{4} ' + 'x' * 70 + '$\n')


def test_blank_lines_set_apart_lists_and_comments():
    text = ('a: 1\nlist: [x, y]\nb: 2\n# A comment.\nc: 3\n')
    assert cc_public.edit.layout.format(text) == ('a:                      1\n'
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
    text = '// ---\n// id_self: dls_x\n// ...\n\n.decl x(id: symbol)\n'
    assert cc_public.edit.layout.format_file(text, pathlib.Path('src/x.dl')) == (
        '// ---\n//\n// id_self:                dls_x\n//\n// ...\n\n.decl x(id: symbol)\n')


def test_a_comment_header_after_an_interpreter_line_is_laid_out():
    text = '#!/bin/sh\n# ---\n# id_self: file_x\n# ...\n\nexit 0\n'
    assert cc_public.edit.layout.format_file(text, pathlib.Path('x')) == (
        '#!/bin/sh\n# ---\n#\n# id_self:                file_x\n#\n# ...\n\nexit 0\n')


def test_an_empty_mapping_in_a_list_is_kept():
    assert cc_public.edit.layout.format('a:\n  - {}\n') == 'a:\n  - {}\n'


def test_a_document_outside_the_subset_is_refused():
    with pytest.raises(cc_public.edit.layout.Unsupported):
        cc_public.edit.layout.format('- a\n- b\n')


# -----------------------------------------------------------------------------
def _shape(node):
    """
    Return node with each literal block reduced to its words, so that
    two documents compare equal when only the breaks in their prose
    differ.

    """

    if isinstance(node, dict):
        return {key: _shape(value) for (key, value) in node.items()}
    if isinstance(node, list):
        return [_shape(value) for value in node]
    if isinstance(node, ruamel.yaml.scalarstring.LiteralScalarString):
        return ('|', ' '.join(node.split()))
    return node
