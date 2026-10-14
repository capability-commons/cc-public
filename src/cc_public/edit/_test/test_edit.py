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
                        the failures it adds. A new guid is made
                        from zeros, so that the text is known.
relation:               []

...
"""


import pytest

import cc_public.edit.edit
import cc_public.edit.layout


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


def test_set_rewrites_a_field_in_a_comment_header(tree):
    path = tree / 'src/cc_public/graph/derive.dl'
    text = path.read_text()
    assert _edit(tree, {'set': ['dls_cc_public.graph.derive', 'brief', 'Derived relations.']}) == {}
    assert path.read_text() == text.replace(
        '// brief:                  |\n'
        '//                         Relations derived from the base relations,\n'
        '//                         for every Datalog program over the graph of\n'
        '//                         data items.\n',
        '// brief:                  |\n'
        '//                         Derived relations.\n')


def test_set_adds_a_field_after_the_one_before_it_in_order(tree):
    path = tree / 'src/cc_public/edit/layout.py'
    text = path.read_text()
    assert _edit(tree, {'set': ['pym_cc_public.edit.layout', 'usage', 'Used by edit.']}) == {}
    assert path.read_text() == text.replace(
        '                        blank line before it and after each mapping.\n',
        '                        blank line before it and after each mapping.\n'
        'usage:                  |\n'
        '                        Used by edit.\n')


@pytest.mark.parametrize(('operation', 'message'), [
    ({'new': 'zzz_x'}, 'No type has the prefix zzz.'),
    ({'new': 'con_concept'}, 'An item with the id con_concept exists.'),
    ({'new': 'pym_x'}, 'An item of t_python_module is written in the file it names, by hand.'),
    ({'new': 'ann_x', 'link': [['r_is_about', 'con_none']]}, 'No item has the id con_none.'),
    ({'link': ['con_concept', 'r_is_about', 'con_concept']}, 'con_concept already has that edge.'),
    ({'set': ['con_concept', 'id_self', 'con_y']}, 'The field id_self is not set this way.'),
    ({'set': ['con_none', 'note', 'x']}, 'No item has the id con_none.'),
    ({'unlink': ['con_concept']}, "An operation of a batch is not one of new, link or set: "
                                  "{'unlink': ['con_concept']}"),
])
def test_an_edit_that_cannot_be_made_says_why(tree, operation, message):
    edited = cc_public.edit.edit.Tree(tree)
    if operation.get('link') and operation['link'][0] == 'con_concept':
        cc_public.edit.edit.batch(edited, [{'link': ['con_concept', 'r_is_about', 'con_concept']}])
    with pytest.raises(cc_public.edit.edit.ErrorEdit) as info:
        cc_public.edit.edit.batch(edited, [operation])
    assert str(info.value) == message


def test_prose_is_wrapped_by_paragraph():
    assert cc_public.edit.layout.lines_of_field('note', 'One two.\n\nThree\nfour.', 4) == [
        '    note:               |',
        '                        One two.',
        '',
        '                        Three four.']


def test_a_scalar_is_quoted_only_where_it_must_be():
    assert cc_public.edit.layout.lines_of_field('title', 'Plain', 0) == [
        'title:                  Plain']
    assert cc_public.edit.layout.lines_of_field('title', 'Not: plain', 0) == [
        "title:                  'Not: plain'"]
