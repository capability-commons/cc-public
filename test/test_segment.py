"""
---

id_self:                pym_test.test_segment
guid_self:              pym_2ed4892095d0498294ff644eb9f30e5a
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Segment tests
brief:                  |
                        A reference may run into a segment its own
                        consumes, and never the other way.
description:            |
                        A segment declared inside another governs what
                        is beneath it. An item of the inner segment
                        may name an item of the core it consumes; an
                        item of the core that names one of the inner
                        segment is refused, and the finding says which
                        segment does not consume which. A tree that
                        declares no segment is passed over.
relation:               []

...
"""


import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
from conftest import clean


ID_CORE  = 'seg_cc_public'
ID_INNER = 'seg_inner'
ID_NEED  = 'need_runs_bounded'                       # a need of the core


def inner(repo):
    """
    Declare a segment inside the tree, consuming the core, with one
    need of its own. A segment governs what is beneath the directory
    its own directory sits in, so this one governs sub/.

    """
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.new.new(tree, 't_segment', ID_INNER, tree.defaults(),
                           dirpath_out = repo / 'sub' / 'segment')
    for (field, value) in (('title', 'An inner segment'), ('role', 'segment')):
        cc_public.edit.field.set_field(tree, ID_INNER, field, value = value)
    for (field, value) in (('brief', 'A segment beneath the core, consuming it.'),
                           ('description', 'It holds one need, derived from a need of the core.')):
        cc_public.edit.field.set_field(tree, ID_INNER, field, prose = value)
    cc_public.edit.link.link(tree, ID_INNER, 'r_consumes', ID_CORE)

    cc_public.edit.new.new(tree, 't_need', 'need_inner_thing', tree.defaults(),
                           dirpath_out = repo / 'sub' / 'need')
    for (field, value) in (('title', 'Something the inner segment needs'),
                           ('subject', 'a reader of the inner segment'),
                           ('outcome', 'a need of its own to read'),
                           ('purpose', 'show that a segment may hold items'),
                           ('context', 'a tree of two segments'),
                           ('evidence', 'None; this need exists to be checked.')):
        cc_public.edit.field.set_field(tree, 'need_inner_thing', field, value = value)
    cc_public.edit.link.link(tree, 'need_inner_thing', 'r_is_derived_from', ID_NEED)
    return tree


def test_a_reference_may_run_into_a_segment_its_own_consumes(repo):
    inner(repo)
    assert clean(repo) == []
    report = cc_public.check.check(list_path = [repo])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'segment']
    assert found['count_item'] > 0 and found['nonconformity'] == []


def test_a_reference_out_of_the_core_into_a_segment_that_consumes_it_is_refused(repo):
    tree = inner(repo)
    cc_public.edit.link.link(tree, ID_NEED, 'r_is_derived_from', 'need_inner_thing')
    report = cc_public.check.check(list_path = [repo])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'segment']
    (fault,) = found['nonconformity']
    assert fault['severity'] == 'critical'
    assert ID_NEED in fault['filepath'] and ID_INNER in fault['message']
    assert 'does not consume it' in fault['message']


def test_a_tree_that_declares_no_segment_is_passed_over(repo):
    (repo / 'segment' / (ID_CORE + '.yaml')).unlink()
    report = cc_public.check.check(list_path = [repo])['report']
    (found,) = [c for c in report['check'] if c['id_check'] == 'segment']
    assert found['count_item'] == 0 and found['nonconformity'] == []
