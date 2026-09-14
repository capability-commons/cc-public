"""
---

id_self:                pym_test.test_rights
guid_self:              pym_8137560b15b14f6daa9ebe723577a384
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  |
                        Item rights tests
brief:                  |
                        An item takes the rights of the tree it is
                        written to, and a check says so when one does
                        not.
description:            |
                        These tests exercise the three things
                        ddr_item_rights decides. A command asked to
                        write outside every root it was given refuses,
                        rather than writing the item with the rights
                        of a tree it is not in. A command whose type
                        names no home looks for one within the first
                        root alone, so a second tree holding more
                        items of that prefix does not attract it. And
                        the check reports an item whose copyright or
                        licence differs from the rest of its segment,
                        judging each segment against its own.
relation:               []

...
"""


import re
import shutil

import pytest

import cc_public.check
import cc_public.check.rights
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load


@pytest.fixture
def beside(tmp_path):
    """
    Return a maker of directories beside the copied tree, since the
    repo fixture is tmp_path itself and anything under it is within the
    root rather than outside it.

    """

    def make(name):
        path = tmp_path.parent / '{stem}-{name}'.format(stem = tmp_path.name,
                                                        name = name)
        path.mkdir(parents = True, exist_ok = True)
        return path

    return make


def rights_of(repo):
    """
    Return the findings the rights check makes over the trees given.

    """

    report = cc_public.check.check(list_path = list(repo), is_closed_world = True)
    return [entry for entry in report['report']['check']
            if entry['id_check'] == cc_public.check.rights.ID_CHECK][0]


def test_an_item_is_refused_where_it_would_fall_outside_every_root(repo, beside):
    outside = beside('outside')
    tree = cc_public.edit.tree.Tree([repo])

    with pytest.raises(cc_public.edit.tree.ErrorItem) as err:
        cc_public.edit.new.new(tree, 't_annotation', 'ann_outside',
                               tree.defaults(), outside)

    assert 'outside every root' in str(err.value)
    assert not list(outside.iterdir())


def test_a_home_is_sought_in_the_first_root_and_not_the_larger_one(repo, beside):
    """
    A second tree holding more items of a prefix must not attract the
    item. t_need names no home, so the majority rule decides, and the
    majority across both trees is the copied repository.

    """

    consumer = beside('consumer')
    (consumer / 'need').mkdir(parents = True)
    shutil.copy(repo / 'pyproject.toml', consumer / 'pyproject.toml')
    shutil.copytree(repo / 'segment', consumer / 'segment')

    # One need there, many here. It is renamed rather than copied as it
    # stands, since two items may not share an identity.
    #
    one  = next((repo / 'need').glob('*.yaml'))
    text = one.read_text(encoding = 'utf-8')
    text = re.sub(r'^(id_self:\s+)\S+',   r'\1need_only_in_the_consumer', text, count = 1, flags = re.MULTILINE)
    text = re.sub(r'^(guid_self:\s+)\S+', r'\1need_' + '0' * 32,          text, count = 1, flags = re.MULTILINE)
    (consumer / 'need' / 'need_only_in_the_consumer.yaml').write_text(text, encoding = 'utf-8')
    assert len(list((repo / 'need').glob('*.yaml'))) > 1

    tree     = cc_public.edit.tree.Tree([consumer, repo])
    filepath = cc_public.edit.new.new(tree, 't_need', 'need_lands_here',
                                      tree.defaults())

    assert filepath.resolve().is_relative_to(consumer.resolve())


def test_the_check_reports_an_item_whose_rights_differ_from_its_segment(repo):
    assert rights_of([repo])['nonconformity'] == []

    path = next((repo / 'need').glob('*.yaml'))
    path.write_text(path.read_text(encoding = 'utf-8').replace(
                        'license:                Apache-2.0',
                        'license:                LicenseRef-Somebody-Else'),
                    encoding = 'utf-8')

    (found,) = rights_of([repo])['nonconformity']
    assert found['severity'] == 'critical'
    assert 'LicenseRef-Somebody-Else' in found['message']
    assert str(path) == found['filepath']
