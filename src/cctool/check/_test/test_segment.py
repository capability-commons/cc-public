"""
---

id_self:                pym_cctool.check._test.test_segment
guid_self:              pym_721a45c736a141f9b6e52d4de7a2feec
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Segment tests
brief:                  |
                        Tests that a peer is checked with the tree it
                        consumes, fails only on its own items, is
                        edited without changing that tree, and checks
                        its commit messages against the sch_commit of
                        that tree.
description:            |
                        Each test makes a peer, a tree that holds one
                        segment item and consumes
                        release_cc_public_0_1_0, and checks it against
                        a copy of the repository: as a checkout, or
                        laid out as the installed package. A fault is
                        put into the peer or into the consumed copy,
                        and the test expects that fault, as a failure
                        or as a notice, and nothing else.
edge:                   []

...
"""


import pathlib
import shutil
import uuid

import pytest

import cctool.check.check
import cctool.check.layout
import cctool.check.segment
import cctool.commit.message
import cctool.edit.edit
import cctool.graph.extract
import cctool.graph.sql
import cctool.release.shadow


ID_PEER      = 'segment_peer'
FILE_PEER    = '_data/federated_segment/segment_peer.yaml'
FILE_NEWER   = '_data/release/release_cc_public_0_2_0.yaml'
FILE_RELEASE = '_data/release/release_cc_public_0_1_0.yaml'

TEXT_PEER    = """\
id_self:                segment_peer
guid_self:              segment_5d1ae0c6bd3a4d4c9bd2b8e2a5c0f7e1
copyright:              Copyright 2026 The Peer
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  The peer segment
brief:                  |
                        A peer of cc-public, made for a test. Its
                        brief names concept_federated_segment, which
                        cc-public holds{widget}.

edge:

  - id_relation:        relation_consumes
    guid_relation:      relation_6a8073e7f10243148e4eb7e15e10b7fd
    id_target:          {release}
    guid_target:        {guid}
"""


FILE_PEER_CONCEPT = '_data/register/reg_peer_concept.yaml'

TEXT_PEER_CONCEPT = """\
id_self:                reg_peer_concept
guid_self:              reg_3c1f0a7e2b5d4c6e8f9a0b1c2d3e4f50
copyright:              Copyright 2026 The Peer
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Peer concept register
brief:                  |
                        Register of the concepts of the peer.
description:            |
                        The peer concept register holds the concepts
                        that the peer adds to those of cc-public.
usage:                  |
                        The peer names its own concepts here.
note:                   |
                        It is made for a test.

edge:

  - id_relation:        relation_is_specified_by_schema
    guid_relation:      relation_e4f6185af9254a649126e121cb4edf5f
    id_target:          sch_reg_concept
    guid_target:        sch_9c44fa0e85434706a25fb5a892955069
{held}
entries:

  # ---------------------------------------------------------------------------
  # concept_peer_widget -- Peer widget
  #
  concept_peer_widget:
    id_self:            concept_peer_widget
    guid_self:          concept_7d2e4f6a8b0c4d1e9f3a5b7c9d1e3f50
    title:              Peer widget
    brief:              |
                        A widget that the peer makes.
    description:        |
                        It is made for a test.
    term_preferred:     peer widget
    alias:              []
    edge:               []
"""

TEXT_HELD = """\

  - id_relation:        relation_holds_items_of_type
    guid_relation:      relation_ce28906bcbe94695821f8639d3b8e298
    id_target:          type_concept
    guid_target:        type_f90804f7b03149fa9850883bd11b9a28
"""


FILE_PEER_MEMBER = '_data/register/reg_peer_team_member.yaml'

TEXT_PEER_MEMBER = """\
id_self:                reg_peer_team_member
guid_self:              {guid_register}
copyright:              Copyright 2026 The Peer
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Peer team member register
brief:                  |
                        Register of the people who contribute to the
                        peer.
description:            |
                        The peer team member register holds the team
                        members of the peer.
usage:                  |
                        The peer names its own team members here.
note:                   |
                        It is made for a test.

edge:

  - id_relation:        relation_is_specified_by_schema
    guid_relation:      relation_e4f6185af9254a649126e121cb4edf5f
    id_target:          sch_reg_team_member
    guid_target:        sch_375bc1031f934f1698f62fe826a52776

  - id_relation:        relation_holds_items_of_type
    guid_relation:      relation_ce28906bcbe94695821f8639d3b8e298
    id_target:          type_team_member
    guid_target:        type_13a7b952a2714ad5abe092f4b6956154

entries:

  # ---------------------------------------------------------------------------
  # member_peer_person -- Peer Person
  #
  member_peer_person:
    id_self:            member_peer_person
    guid_self:          {guid_member}
    title:              Peer Person
    brief:              |
                        A team member of the peer.
    description:        |
                        It is made for a test.
    git_author:         Peer Person <peer@example.org>
    git_signing_key:    ABCDEF0123456789
    alias:              []
    edge:               []
"""

ID_THIRD           = 'segment_third'
FILE_THIRD         = '_data/federated_segment/segment_third.yaml'
FILE_THIRD_RELEASE = '_data/release/release_third_0_1_0.yaml'
FILE_THIRD_CONCEPT = '_data/register/reg_third_concept.yaml'
GUID_THIRD_RELEASE = 'release_f7371d12049f400c9206b9cadeb4fa7b'

TEXT_THIRD         = TEXT_PEER.format(release = 'release_cc_public_0_1_0',
                                      guid    = 'release_b9909b2c09ac45e08e9e4fd466d0ded3',
                                      widget  = ', and concept_third_gizmo,\n'
                                                '                        which it holds')

TEXT_THIRD_RELEASE = """\
id_self:                release_third_0_1_0
guid_self:              {guid}
copyright:              Copyright 2026 The Third
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Release 0.1.0
brief:                  |
                        The first release of the third segment.
version:                0.1.0
dependency:             []
edge:                   []
""".format(guid = GUID_THIRD_RELEASE)

# Each id, guid and word of the peer that the third segment holds as its
# own in place of them, so that no id or guid is held by both.
#
MAP_THIRD          = {'segment_peer':                            ID_THIRD,
                      'segment_5d1ae0c6bd3a4d4c9bd2b8e2a5c0f7e1': 'segment_c47da76808254dff900d35d9057a702b',
                      'reg_peer_concept':                        'reg_third_concept',
                      'reg_3c1f0a7e2b5d4c6e8f9a0b1c2d3e4f50':     'reg_6140d0cbb32f4407919ff827cb32a7d6',
                      'concept_peer_widget':                     'concept_third_gizmo',
                      'concept_7d2e4f6a8b0c4d1e9f3a5b7c9d1e3f50': 'concept_01866cd22cf948aca106375a3bc866d2',
                      'The Peer':                                'The Third',
                      'The peer segment':                        'The third segment',
                      'A peer of cc-public':                     'A third segment',
                      'Peer concept register':                   'Third concept register',
                      'the peer':                                'the third segment',
                      'Peer widget':                             'Third gizmo',
                      'peer widget':                             'third gizmo',
                      'A widget':                                'A gizmo'}


# -----------------------------------------------------------------------------
def _peer(tmp_path_factory,
          release = 'release_cc_public_0_1_0',
          guid    = 'release_b9909b2c09ac45e08e9e4fd466d0ded3',
          held    = None):
    """
    Return the root of a new peer, which consumes release, with guid.
    With held, the peer also holds a concept register of its own, which
    names the type of its entries with held, and its segment item names
    the concept that register holds.

    """

    root   = tmp_path_factory.mktemp('peer')
    path   = root / FILE_PEER
    widget = '' if held is None else ', and concept_peer_widget,\n                        which the peer holds'
    path.parent.mkdir(parents = True)
    path.write_text(TEXT_PEER.format(release = release, guid = guid, widget = widget),
                    encoding = 'utf-8')
    if held is not None:
        path = root / FILE_PEER_CONCEPT
        path.parent.mkdir(parents = True)
        path.write_text(TEXT_PEER_CONCEPT.format(held = held), encoding = 'utf-8')
    return root


# -----------------------------------------------------------------------------
def _third(tmp_path_factory):
    """
    Return the root of a third segment, a checkout that consumes
    release_cc_public_0_1_0 and holds a release of its own and a concept
    register, made from those of the peer, whose entry its segment item
    names.

    """

    root = tmp_path_factory.mktemp('third')
    for (relative, text_peer) in ((FILE_THIRD,         TEXT_THIRD),
                                  (FILE_THIRD_RELEASE, TEXT_THIRD_RELEASE),
                                  (FILE_THIRD_CONCEPT, TEXT_PEER_CONCEPT.format(held = TEXT_HELD))):
        text = text_peer
        for (old, new) in MAP_THIRD.items():
            text = text.replace(old, new)
        path = root / relative
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_text(cctool.check.layout.lay_out(text, pathlib.PurePosixPath(relative)),
                        encoding = 'utf-8')
    return root


# -----------------------------------------------------------------------------
def _package(tree, tmp_path_factory):
    """
    Return the folder of a cctool package installed from the copy tree:
    its code, with its _data folder inside it, and the file of shadows
    that the build adds to that folder.

    """

    dir_package = tmp_path_factory.mktemp('site') / 'cctool'
    shutil.copytree(tree / 'src' / 'cctool', dir_package)
    shutil.copytree(tree / '_data', dir_package / '_data')
    dir_shadow  = dir_package / '_data' / cctool.graph.extract.DIR_SHADOW
    dir_shadow.mkdir()
    cctool.release.shadow.write(tree, dir_shadow)
    return dir_package


# -----------------------------------------------------------------------------
def _consume(monkeypatch, place, path):
    """
    Make path, read from place, the one tree that a segment may consume.

    """

    monkeypatch.setattr(cctool.check.segment, 'trees', lambda: [(place, path)])


# -----------------------------------------------------------------------------
def _newer(tree):
    """
    Give the copy tree a release item newer than release_cc_public_0_1_0.

    """

    text = (tree / FILE_RELEASE).read_text(encoding = 'utf-8')
    text = (text.replace('release_cc_public_0_1_0', 'release_cc_public_0_2_0')
                .replace('release_b9909b2c09ac45e08e9e4fd466d0ded3',
                         'release_0f4c3b2a19d84e6f8a7b6c5d4e3f2a10')
                .replace('Release 0.1.0', 'Release 0.2.0')
                .replace('version:                0.1.0', 'version:                0.2.0'))
    (tree / FILE_NEWER).write_text(text, encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _without_layout(failures):
    """
    Return failures without unformatted_file, which a copy of the
    repository may have where a test wrote a file by hand.

    """

    return {name: list_row for (name, list_row) in failures.items()
            if name != cctool.check.check.NAME_LAYOUT}


# -----------------------------------------------------------------------------
def test_a_peer_that_consumes_a_checkout_passes(tree, tmp_path_factory, monkeypatch):
    """
    A peer that names only its own items and those of the checkout it
    consumes has no failures, and the checkout has no notices.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory))

    assert failures == {}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_peer_that_consumes_a_release_passes(tree, tmp_path_factory, monkeypatch):
    """
    The installed package does not hold the files at the root of its
    tree, but holds a shadow of each that it names, so nothing it names
    dangles, and the peer has neither failures nor notices.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_RELEASE, _package(tree, tmp_path_factory))
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory))

    assert failures == {}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_peer_register_that_names_its_type_passes(tree, tmp_path_factory, monkeypatch):
    """
    A register in a peer that names a consumed type with the inverse of
    relation_has_items_held_in_register holds entries of that type, and
    the peer has neither failures nor notices.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory, held = TEXT_HELD))

    assert failures == {}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_peer_register_that_names_no_type_fails(tree, tmp_path_factory, monkeypatch):
    """
    A register in a peer that does not name the type of its entries
    holds them out of place.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory, held = ''))

    assert failures == {'misplaced_register_entry': [
        ('reg_peer_concept', 'concept_peer_widget', 'type_concept')]}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_peer_register_with_another_schema_fails(tree, tmp_path_factory, monkeypatch):
    """
    A register in a peer that names a consumed type is specified by the
    schema of the register the type names, so one specified by another
    schema fails.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = _peer(tmp_path_factory, held = TEXT_HELD)
    path = root / FILE_PEER_CONCEPT
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('sch_reg_concept', 'sch_reg_concern')
                        .replace('sch_9c44fa0e85434706a25fb5a892955069', 'sch_cca032062b3f433689d41fb41e306309'),
                    encoding = 'utf-8')
    (failures, _, _) = cctool.check.check.review(root)

    assert failures['peer_register_schema_differs'] == [
        ('reg_peer_concept', 'type_concept', 'reg_concept', 'sch_reg_concept')]


# -----------------------------------------------------------------------------
def test_a_peer_register_without_the_name_of_its_segment_fails(tree, tmp_path_factory,
                                                              monkeypatch):
    """
    The id of a register in a peer carries the name of the segment of
    the peer after the register prefix.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = _peer(tmp_path_factory, held = TEXT_HELD)
    path = root / FILE_PEER_CONCEPT
    path.rename(root / '_data' / 'register' / 'reg_widget_concept.yaml')
    path = root / '_data' / 'register' / 'reg_widget_concept.yaml'
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('reg_peer_concept', 'reg_widget_concept'),
                    encoding = 'utf-8')
    (failures, _, notices) = cctool.check.check.review(root)

    assert failures == {'unqualified_peer_register': [
        ('reg_widget_concept', ID_PEER, 'peer', '_data/register/reg_widget_concept.yaml', '1')]}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_the_effective_register_of_a_peer_is_the_union_along_its_chain(tree, tmp_path_factory,
                                                                      monkeypatch):
    """
    The peer reads the entries of type_concept from its own register
    and from that of cc-public, and cc-public reads only its own.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    facts = cctool.graph.extract.facts_of(
                cctool.check.segment.union(_peer(tmp_path_factory, held = TEXT_HELD)))
    text  = ("SELECT segment, register FROM effective_register WHERE type = 'type_concept' "
             "ORDER BY segment, register")
    entry = ("SELECT segment, register FROM effective_entry "
             "WHERE id IN ('concept_peer_widget', 'concept_federated_segment') "
             "ORDER BY segment, register")

    assert cctool.graph.sql.query(facts, text)[1] == [
        ('segment_cc_public', 'reg_concept'),
        (ID_PEER,             'reg_concept'),
        (ID_PEER,             'reg_peer_concept')]
    assert cctool.graph.sql.query(facts, entry)[1] == [
        ('segment_cc_public', 'reg_concept'),
        (ID_PEER,             'reg_concept'),
        (ID_PEER,             'reg_peer_concept')]


# -----------------------------------------------------------------------------
def test_a_tree_with_no_segment_consumes_nothing(tree, tmp_path_factory, monkeypatch):
    """
    A tree with no segment item reads no consumed tree, and fails
    segment_count.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = tmp_path_factory.mktemp('bare')

    (root / '_data').mkdir()
    (failures, _, notices) = cctool.check.check.review(root)

    assert failures == {'segment_count': [('0',)]}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_fault_in_the_consumed_tree_is_a_notice(tree, tmp_path_factory, monkeypatch):
    """
    A dangling mention in the consumed tree is a notice, and not a
    failure of the peer.

    """

    path = tree / '_data' / 'federated_segment' / 'segment_cc_public.yaml'
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('It consumes nothing.', 'It consumes concept_nowhere.'),
                    encoding = 'utf-8')
    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory))

    assert _without_layout(failures) == {}
    assert notices == {'dangling_mention': [
        ('segment_cc_public', 'concept_nowhere',
         '_consumed/segment_cc_public/_data/federated_segment/segment_cc_public.yaml', '14')]}


# -----------------------------------------------------------------------------
def test_a_peer_that_names_a_segment_it_does_not_consume_fails(tree, tmp_path_factory,
                                                               monkeypatch):
    """
    A reference into a segment that is read beside the peer, but that the
    peer does not consume, fails.

    """

    third = _third(tmp_path_factory)
    monkeypatch.setattr(cctool.check.segment, 'trees',
                        lambda: [(cctool.check.segment.PLACE_CHECKOUT, tree),
                                 (cctool.check.segment.PLACE_CHECKOUT, third)])
    root  = _peer(tmp_path_factory)
    path  = root / FILE_PEER
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('cc-public holds.', 'cc-public holds, and concept_third_gizmo.'),
                    encoding = 'utf-8')
    (failures, _, notices) = cctool.check.check.review(root)

    assert _without_layout(failures) == {'unconsumed_reference': [
        (ID_PEER, 'concept_third_gizmo', ID_PEER, ID_THIRD, FILE_PEER, '15')]}
    assert notices == {}


# -----------------------------------------------------------------------------
def test_a_peer_reads_each_segment_along_its_chain(tree, tmp_path_factory, monkeypatch):
    """
    A peer that consumes the third segment, which consumes cc-public,
    may name the items of both, and its effective register of a type is
    the union of the registers of all three.

    """

    third = _third(tmp_path_factory)
    monkeypatch.setattr(cctool.check.segment, 'trees',
                        lambda: [(cctool.check.segment.PLACE_CHECKOUT, tree),
                                 (cctool.check.segment.PLACE_CHECKOUT, third)])
    root  = _peer(tmp_path_factory, 'release_third_0_1_0', GUID_THIRD_RELEASE, TEXT_HELD)
    (failures, _, notices) = cctool.check.check.review(root)
    facts = cctool.graph.extract.facts_of(cctool.check.segment.union(root))
    text  = ("SELECT register FROM effective_register "
             "WHERE segment = 'segment_peer' AND type = 'type_concept' ORDER BY register")

    assert failures == {}
    assert notices  == {}
    assert cctool.graph.sql.query(facts, text)[1] == [
        ('reg_concept',), ('reg_peer_concept',), ('reg_third_concept',)]


# -----------------------------------------------------------------------------
def test_a_peer_that_names_a_missing_release_fails(tree, tmp_path_factory, monkeypatch):
    """
    A segment item that names a release item no tree holds fails, as a
    reference that dangles, and only so: what the peer names in the
    tree it reads is left to that failure.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root                   = _peer(tmp_path_factory, 'release_cc_public_9_9_9',
                                   'release_9f9e9d9c9b9a49998897969594939291')
    (failures, _, notices) = cctool.check.check.review(root)

    assert failures == {'dangling_reference': [(ID_PEER, 'target', 'release_cc_public_9_9_9',
                                                FILE_PEER, '21')]}
    assert notices  == {}


# -----------------------------------------------------------------------------
def test_a_consumed_item_that_names_the_peer_fails(tree, tmp_path_factory, monkeypatch):
    """
    A reference runs only into a segment that its own consumes, so the
    consumed tree may not name the peer.

    """

    path = tree / '_data' / 'federated_segment' / 'segment_cc_public.yaml'
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('It consumes nothing.', 'It names segment_peer.'),
                    encoding = 'utf-8')
    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory))

    assert _without_layout(failures) == {'unconsumed_reference': [
        ('segment_cc_public', ID_PEER, 'segment_cc_public', ID_PEER,
         '_consumed/segment_cc_public/_data/federated_segment/segment_cc_public.yaml', '14')]}
    assert notices == {}


# -----------------------------------------------------------------------------
@pytest.mark.parametrize(('place', 'is_failure'),
                         [(cctool.check.segment.PLACE_RELEASE,  True),
                          (cctool.check.segment.PLACE_CHECKOUT, False)])
def test_a_release_older_than_the_consumed_tree_disagrees(tree, tmp_path_factory, monkeypatch,
                                                          place, is_failure):
    """
    A peer that names a release older than the newest of the tree it
    consumes fails while that tree is an installed release, and has a
    notice while it is a checkout.

    """

    _newer(tree)
    path = tree if place == cctool.check.segment.PLACE_CHECKOUT else _package(tree,
                                                                              tmp_path_factory)
    _consume(monkeypatch, place, path)
    (failures, _, notices) = cctool.check.check.review(_peer(tmp_path_factory))

    row      = (FILE_PEER, '1', ID_PEER, 'release_cc_public_0_1_0', 'release_cc_public_0_2_0', place)
    expected = {cctool.check.check.NAME_CONSUMED: [row]}

    assert (failures if is_failure else notices).get(cctool.check.check.NAME_CONSUMED) \
        == expected[cctool.check.check.NAME_CONSUMED]
    assert cctool.check.check.NAME_CONSUMED not in (notices if is_failure else failures)
    assert _without_layout(failures).keys() <= {cctool.check.check.NAME_CONSUMED}


# -----------------------------------------------------------------------------
def test_an_edit_in_a_peer_may_name_consumed_items(tree, tmp_path_factory, monkeypatch):
    """
    An edit in a peer is checked with the tree it consumes, so a new
    item that names its items adds no failure, and is written in the
    peer, with the rights of the segment item of the peer.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = _peer(tmp_path_factory)
    edit = cctool.edit.edit.Tree(root)

    edit.update(cctool.edit.edit.new(edit, 'lco_peer_part',
                                     [('title', 'Peer part'),
                                      ('brief', 'A part of the peer, which is a segment.')],
                                     [('relation_is_driven_by', 'concern_security')]))

    assert cctool.edit.edit.apply(edit) == {}
    assert 'Copyright 2026 The Peer' in (root / '_data' / 'logical_component'
                                         / 'lco_peer_part.yaml').read_text(encoding = 'utf-8')


# -----------------------------------------------------------------------------
def test_a_new_entry_in_a_peer_goes_in_the_register_of_the_peer(tree, tmp_path_factory,
                                                                monkeypatch):
    """
    A new item of a consumed type that a register of the peer names is
    an entry of that register, and not of the register of the consumed
    tree.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    edit = cctool.edit.edit.Tree(_peer(tmp_path_factory, held = TEXT_HELD))
    text = cctool.edit.edit.new(edit, 'concept_peer_gadget',
                                [('title', 'Peer gadget'),
                                 ('brief', 'A gadget that the peer makes.'),
                                 ('description', 'It is made for a test.'),
                                 ('term_preferred', 'peer gadget')],
                                [])

    assert list(text) == [FILE_PEER_CONCEPT]
    assert 'concept_peer_gadget:' in text[FILE_PEER_CONCEPT]


# -----------------------------------------------------------------------------
def test_a_new_entry_in_a_peer_with_no_register_of_its_type_is_refused(tree, tmp_path_factory,
                                                                       monkeypatch):
    """
    A new item of a consumed type that no register of the peer names
    would be an entry of the register of the consumed tree, which an
    edit in the peer cannot change.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    edit = cctool.edit.edit.Tree(_peer(tmp_path_factory))

    with pytest.raises(cctool.edit.edit.ErrorEdit, match = 'held by segment_cc_public'):
        cctool.edit.edit.new(edit, 'concept_peer_gadget',
                             [('title', 'Peer gadget'),
                              ('brief', 'A gadget that the peer makes.'),
                              ('description', 'It is made for a test.'),
                              ('term_preferred', 'peer gadget')],
                             [])


# -----------------------------------------------------------------------------
def test_an_edit_in_a_peer_may_not_change_a_consumed_item(tree, tmp_path_factory, monkeypatch):
    """
    The files of a consumed tree are read for an edit, but never
    changed by one.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    edit = cctool.edit.edit.Tree(_peer(tmp_path_factory))

    with pytest.raises(cctool.edit.edit.ErrorEdit, match = 'held by segment_cc_public'):
        cctool.edit.edit.set_field(edit, 'concept_federated_segment', 'title', 'Part')


# -----------------------------------------------------------------------------
def test_a_rename_in_a_peer_changes_only_the_peer(tree, tmp_path_factory, monkeypatch):
    """
    A rename of an item of the peer reads the consumed tree, and changes
    only the files of the peer, which adds no failure.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = _peer(tmp_path_factory, held = TEXT_HELD)
    edit = cctool.edit.edit.Tree(root)

    edit.update(cctool.edit.edit.rename(edit, 'concept_peer_widget', 'concept_peer_sprocket'))

    assert sorted(edit.edit) == [FILE_PEER, FILE_PEER_CONCEPT]
    assert cctool.edit.edit.apply(edit) == {}
    assert 'concept_peer_sprocket' in (root / FILE_PEER).read_text(encoding = 'utf-8')


# -----------------------------------------------------------------------------
def test_a_rename_in_a_peer_of_a_consumed_item_is_refused(tree, tmp_path_factory, monkeypatch):
    """
    An item of a consumed tree is renamed only in that tree.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    edit = cctool.edit.edit.Tree(_peer(tmp_path_factory))

    with pytest.raises(cctool.edit.edit.ErrorEdit, match = 'held by segment_cc_public'):
        cctool.edit.edit.rename(edit, 'concept_federated_segment', 'concept_peer_segment')


# -----------------------------------------------------------------------------
def test_a_peer_checks_a_commit_message_against_the_consumed_schema(tree, tmp_path_factory,
                                                                    monkeypatch):
    """
    A peer holds no sch_commit of its own, so its commit messages are
    checked against that of the tree it consumes.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root = _peer(tmp_path_factory)
    text = cctool.commit.message.compose('Add the peer', 'The first commit of the peer.')

    assert cctool.commit.message.violations(root, text) == []
    assert cctool.commit.message.violations(root, text.replace('Add the peer', 'Peer')) != []


# -----------------------------------------------------------------------------
def test_a_member_of_a_peer_team_member_register_passes_the_commit_checks(tree, tmp_path_factory,
                                                                          monkeypatch):
    """
    A team member that a register in the peer holds, by the inverse of
    relation_has_items_held_in_register, may author and sign a commit
    of the peer and be named in a Contributor trailer, as may a member
    of the team member register of the tree it consumes.

    """

    _consume(monkeypatch, cctool.check.segment.PLACE_CHECKOUT, tree)
    root   = _peer(tmp_path_factory)
    guid   = 'member_' + uuid.uuid4().hex
    path   = root / FILE_PEER_MEMBER
    path.parent.mkdir(parents = True)
    path.write_text(TEXT_PEER_MEMBER.format(guid_register = 'reg_' + uuid.uuid4().hex,
                                            guid_member   = guid),
                    encoding = 'utf-8')
    text   = cctool.commit.message.compose('Add the peer', 'The first commit of the peer.')
    author = 'Peer Person <peer@example.org> 1793091600 +0000'

    assert _without_layout(cctool.check.check.review(root)[0]) == {}
    assert cctool.commit.message.violations(
               root, text + '\nContributor: {guid}\n'.format(guid = guid)) == []
    assert cctool.commit.message.author_violations(root, author) == []
    assert cctool.commit.message.author_violations(
               root, 'William Payne <wtpayne@gmail.com> 1793091600 +0000') == []
    assert cctool.commit.message.signature_violations(root, 'G', ['ABCDEF0123456789']) == []
    assert cctool.commit.message.author_violations(
               _peer(tmp_path_factory), author) != []
