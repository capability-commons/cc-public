"""
---

id_self:                pym_test.test_annotation
guid_self:              pym_795d03699c984c29822f26f547dea4e6
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Annotation tests
brief:                  |
                        Tests that an annotation is one assertion
                        about something, and that the register alone
                        holds it to that.
description:            |
                        Every rule an annotation is held to is a
                        constraint in the relation register, so each
                        test breaks one and asks the existing checks,
                        never a check written for annotations. What
                        the assertion argues with is an edge too, and
                        the tests walk from an annotation to see it.
relation:               []

...
"""


import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.observe
import cc_public.testing
import cc_public.trace
from conftest import clean


ID_SUBJECT   = 'pyf_cc_public.query.database.path'
ID_OTHER     = 'req_path_reported'

CAPTURE      = {'schema_version': 1,
                'source_kind':    'social_post',
                'platform':       'x',
                'post_id':        '2001',
                'source_uri':     'https://example.invalid/unit/status/2001',
                'author_display': 'Unit (example)',
                'author_handle':  '@unit_example',
                'published_at':   '2026-08-30T06:40:00Z',
                'captured_at':    '2026-09-06T11:00:00Z',
                'text':           'The path query timed out on a large tree.',
                'capture_method': 'supplied_scrape'}


ABSENT       = 'pyf_' + '0' * 32


def _reference(root, is_closed_world):
    """
    Return what the reference check reported over root.

    """

    report = cc_public.check.check(list_path       = [root],
                                   is_closed_world = is_closed_world)['report']

    return [n for c in report['check'] if c['id_check'] == 'reference'
              for n in c['nonconformity']]


def _annotate(tree, id_self, brief, *id_about):
    """
    Make an annotation asserting brief about each item named.

    """

    cc_public.edit.new.new(tree, 't_annotation', id_self, tree.defaults())
    cc_public.edit.field.set_field(tree, id_self, 'title', value = 'Annotation')
    cc_public.edit.field.set_field(tree, id_self, 'brief', prose = brief)

    for name in id_about:
        cc_public.edit.link.link(tree, id_self, 'r_is_about', name)

    return id_self


def _observe(tree):
    """
    Put one observation in the tree and return its readable id.

    """

    (item, _) = cc_public.edit.observe.observe(tree, CAPTURE)

    return item.id_self


def test_an_annotation_about_something_is_accepted(tree, tmp_path):
    _annotate(tree, 'ann_path_cost', 'The path query walks the whole graph.', ID_SUBJECT)
    assert clean(tmp_path) == []


def test_an_annotation_about_nothing_is_reported_by_the_cardinality_it_declares(tree,
                                                                                tmp_path):
    # No annotation specific check: r_is_about declares a minimum of
    # one, and the relation check reads that from the register.
    _annotate(tree, 'ann_floating', 'Something is wrong somewhere.')
    faults = clean(tmp_path)
    assert any(c == 'relation' and 'ann_floating holds 0 r_is_about edge(s)' in m
               for (c, m) in faults), faults


def test_one_assertion_may_be_about_several_kinds_of_item(tree, tmp_path):
    # The range is unconstrained, since an assertion may concern how
    # two items of different kinds meet.
    _annotate(tree, 'ann_pair', 'The requirement and the function disagree on the '
                                'empty case.', ID_SUBJECT, ID_OTHER)
    assert clean(tmp_path) == []


def test_an_annotation_challenges_and_supports_another(tree, tmp_path):
    _annotate(tree, 'ann_concern', 'The path query is unbounded.', ID_SUBJECT)
    _annotate(tree, 'ann_defence', 'The tree is bounded by the segment.', ID_SUBJECT)
    _annotate(tree, 'ann_residual', 'A consumer segment is not bounded.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_defence',  'r_challenges', 'ann_concern')
    cc_public.edit.link.link(tree, 'ann_residual', 'r_supports',   'ann_concern')
    assert clean(tmp_path) == []


def test_neither_argument_relation_runs_to_anything_but_an_annotation(tree, tmp_path):
    # Arguing with a function is not arguing: what is challenged is an
    # assertion, and the range says so.
    _annotate(tree, 'ann_concern', 'The path query is unbounded.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_concern', 'r_challenges', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_concern', 'r_supports',   ID_OTHER)
    faults = clean(tmp_path)
    assert any('An r_challenges edge runs to t_annotation' in m for (_, m) in faults), faults
    assert any('An r_supports edge runs to t_annotation'   in m for (_, m) in faults), faults


def test_a_cycle_of_challenge_and_support_is_not_a_fault(tree, tmp_path):
    # Neither relation is acyclic. Two assertions may each give a
    # reason against the other, and nothing here settles which wins.
    _annotate(tree, 'ann_one', 'The lock is held too long.', ID_SUBJECT)
    _annotate(tree, 'ann_two', 'Releasing it earlier loses the ordering.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_one', 'r_challenges', 'ann_two')
    cc_public.edit.link.link(tree, 'ann_two', 'r_challenges', 'ann_one')
    cc_public.edit.link.link(tree, 'ann_one', 'r_supports',   'ann_one')
    assert clean(tmp_path) == []


def test_an_annotation_cites_an_observation_and_nothing_else(tree, tmp_path):
    id_observation = _observe(tree)
    _annotate(tree, 'ann_reported', 'A user reports the query timing out.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_reported', 'r_cites', id_observation)
    assert clean(tmp_path) == []

    # Naming another annotation is supporting or challenging it, and
    # neither of those is evidence.
    _annotate(tree, 'ann_second', 'It timed out for me too.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_second', 'r_cites', 'ann_reported')
    faults = clean(tmp_path)
    assert any('An r_cites edge runs to t_observation' in m for (_, m) in faults), faults


def test_an_annotation_about_nothing_that_exists_is_reported(tree, tmp_path):
    # By guid, since a reference resolves by guid and changing the
    # readable id alone leaves the edge pointing where it always did.
    _annotate(tree, 'ann_dangling', 'Something about a thing that is not here.',
              ID_SUBJECT)
    cc_public.edit.field.set_field(
        tree, 'ann_dangling', 'relation.0.guid_target', value = ABSENT)

    # Advisory in an open world, where the subject may lie behind a
    # sharing boundary, and critical where the caller says the paths
    # given hold everything. Annotations take that from the reference
    # check as everything else does.
    assert any(n['severity'] == 'advisory' and ABSENT in n['message']
               for n in _reference(tmp_path, is_closed_world = False))
    assert any(n['severity'] == 'critical' and ABSENT in n['message']
               for n in _reference(tmp_path, is_closed_world = True))


def test_walking_an_annotation_reaches_its_subject_and_what_argues_with_it(tree):
    _annotate(tree, 'ann_concern', 'The path query is unbounded.', ID_SUBJECT)
    _annotate(tree, 'ann_defence', 'The tree is bounded by the segment.', ID_SUBJECT)
    cc_public.edit.link.link(tree, 'ann_defence', 'r_challenges', 'ann_concern')

    found = cc_public.trace.neighbourhood(tree.context.map_document, 'ann_concern')
    assert ('r_is_about', ID_SUBJECT) in found.outgoing
    assert ('ann_defence', 'r_challenges') in found.incoming


def test_an_annotation_rests_on_what_it_is_about(tree):
    # r_is_about declares dependency, so the closure of an annotation
    # holds its subject: a change there reaches whatever was computed
    # over the annotation.
    _annotate(tree, 'ann_concern', 'The path query is unbounded.', ID_SUBJECT)
    map_document = tree.context.map_document
    assert 'r_is_about' in cc_public.testing.dependency(map_document)
    assert ID_SUBJECT in cc_public.testing.closure(map_document, ['ann_concern'])
