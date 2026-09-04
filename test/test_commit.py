"""
---

id_self:                pym_test.test_commit
guid_self:              pym_8abb4de956da40bcb04b111b1099985e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit tests
brief:                  |
                        A commit carries a valid record in its
                        message.
description:            |
                        Makes a repository from a copy of the tree,
                        changes it, commits through the tool, and
                        reads the record back from the history.

...
"""

import pathlib
import re
import shutil
import subprocess

import pytest

import cc_public.commit
import cc_public.edit.field
import cc_public.edit.tree
import cc_public.load.git


ROOT = pathlib.Path(__file__).resolve().parent.parent
KEEP = ('ddr', 'schema', 'register', 'eval', 'workflow', 'src', 'pyproject.toml')


def git(root, *args):
    return subprocess.run(['git', '-C', str(root),
                           '-c', 'user.name=Test', '-c', 'user.email=t@t',
                           *args], capture_output = True, text = True,
                          check = True).stdout


@pytest.fixture
def repo(tmp_path):
    for name in KEEP:
        src = ROOT / name
        (shutil.copytree if src.is_dir() else shutil.copy)(src, tmp_path / name)
    git(tmp_path, 'init', '-q')
    git(tmp_path, 'add', '-A')
    git(tmp_path, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'start')
    return tmp_path


def test_commit_carries_a_valid_record(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'dep_record_from_schema_local',
                                   'budget', value = '4')
    (hash, id_self) = cc_public.commit.commit(
                repo, 'Raise the budget', brief = 'Four passes.',
                description = 'Three was not enough.',
                list_trailer = ['Co-Authored-By: Test <t@t>'])

    assert re.fullmatch(r'cmt_[0-9]{14}_[0-9a-f]{6}', id_self)
    assert git(repo, 'status', '--porcelain') == ''

    c = next(cc_public.load.git.iter_commit(repo, 1))
    assert c.hash == hash and c.title == 'Raise the budget'
    assert c.document['id_self'] == id_self
    assert c.document['title'] == c.title
    assert c.document['status'] == 'clean'
    assert c.document['check']['critical'] == 0
    assert c.document['relation'] == []
    assert 'file' not in c.document
    assert c.message.rstrip().endswith('Co-Authored-By: Test <t@t>')
    assert c.message.index('\n---\n') < c.message.index('\n...\n')


def test_commit_refuses_failing_checks_unless_checkpoint(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'dep_record_from_schema_local',
                                   'budget', value = '0')      # minimum is 1
    with pytest.raises(cc_public.commit.ErrorCommit):
        cc_public.commit.commit(repo, 'Break it')

    (hash, id_self) = cc_public.commit.commit(repo, 'Break it, knowingly',
                                              is_checkpoint = True)
    c = next(cc_public.load.git.iter_commit(repo, 1))
    assert c.document['status'] == 'checkpoint'
    assert c.document['check']['critical'] >= 1


def test_commit_refuses_with_nothing_changed(repo):
    with pytest.raises(cc_public.commit.ErrorCommit):
        cc_public.commit.commit(repo, 'Nothing')


def test_link_records_intent_and_refuses_unknown_relation(repo):
    (repo / 'NOTES.md').write_text('a note\n')
    (hash, id_self) = cc_public.commit.commit(
                repo, 'Add a note', list_link = [('r_decides', 'sch_commit')])
    c = next(cc_public.load.git.iter_commit(repo, 1))
    assert [(e['id_relation'], e['id_target']) for e in c.document['relation']] \
           == [('r_decides', 'sch_commit')]
    (repo / 'NOTES.md').write_text('another\n')
    with pytest.raises(cc_public.commit.ErrorCommit):
        cc_public.commit.commit(repo, 'Bad link',
                                list_link = [('r_nonsense', 'sch_commit')])


def test_records_sort_by_time(repo):
    tree = cc_public.edit.tree.Tree([repo])
    ids = []
    for n in ('5', '6'):
        cc_public.edit.field.set_field(tree, 'dep_record_from_schema_local',
                                       'budget', value = n)
        ids.append(cc_public.commit.commit(repo, 'Budget ' + n)[1])
    assert ids == sorted(ids)
