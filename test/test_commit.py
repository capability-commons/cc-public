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
relation:               []

...
"""

import re

import pytest

import cc_public.commit
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load.git
from conftest import git








def test_commit_carries_a_valid_record(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'budget', value = 4)
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
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'budget', value = 0)      # minimum is 1
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
    for n in (5, 6):
        cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                       'budget', value = n)
        ids.append(cc_public.commit.commit(repo, 'Budget {n}'.format(n = n))[1])
    assert ids == sorted(ids)


class Raising:
    """A check that cannot run, standing in for a defect in the tool."""

    ID_CHECK = 'raising'
    TITLE    = 'A check that raises'
    NOUN     = 'thing'

    @staticmethod
    def check(_context):
        raise RuntimeError('the check fell over')


def test_commit_refuses_an_incomplete_analysis_even_as_a_checkpoint(repo, monkeypatch):
    monkeypatch.setattr(cc_public.check, 'CHECK', (*cc_public.check.CHECK, Raising))
    (repo / 'NOTES.md').write_text('a note\n')
    for is_checkpoint in (False, True):
        with pytest.raises(cc_public.commit.ErrorCommit) as caught:
            cc_public.commit.commit(repo, 'Blind', is_checkpoint = is_checkpoint)
        assert 'did not complete' in str(caught.value)
        assert 'the check fell over' in str(caught.value)
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '1'
    assert git(repo, 'status', '--porcelain').split() == ['??', 'NOTES.md']


def test_awkward_paths_are_read_exactly_and_committed(repo):
    for name in ('two words.txt', 'quote"d.txt', 'naïve.txt', '-dash.txt',
                 'tab\there.txt'):
        (repo / name).write_text('x\n')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'awkward')
    git(repo, 'mv', 'two words.txt', 'three more words.txt')
    (repo / 'naïve.txt').write_text('y\n')
    (repo / '-dash.txt').unlink()
    (repo / 'new one.txt').write_text('x\n')

    assert sorted(cc_public.commit.changed(repo)) == [
        ('??', 'new one.txt'), ('D', '-dash.txt'), ('M', 'naïve.txt'),
        ('R', 'three more words.txt')]

    cc_public.commit.commit(repo, 'Awkward names')
    assert git(repo, 'status', '--porcelain') == ''
    listed = git(repo, 'ls-files', '-z').split('\0')
    assert 'three more words.txt' in listed and 'new one.txt' in listed
    assert 'two words.txt' not in listed and '-dash.txt' not in listed


def test_commit_lints_a_tree_that_configures_a_linter(repo):
    tree = cc_public.edit.tree.Tree([repo])
    bad  = cc_public.edit.new.new(tree, 't_python_module', 'pym_cc_public.unused',
                                  tree.defaults())
    for field in ('title', 'brief', 'description'):
        cc_public.edit.field.set_field(tree, 'pym_cc_public.unused', field, value = 'Unused')
    head = bad.read_text()
    bad.write_text(head + '\nimport os\n')
    with pytest.raises(cc_public.commit.ErrorCommit) as caught:
        cc_public.commit.commit(repo, 'Lint fails')
    assert 'lint' in str(caught.value) and 'F401' in str(caught.value)
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '1'

    cc_public.commit.commit(repo, 'Lint fails, knowingly', is_checkpoint = True)
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '2'

    bad.write_text(head + '\nimport os\n\nprint(os.sep)\n')
    cc_public.commit.commit(repo, 'Lint passes')
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '3'

    # A tree that configures no linter is data alone and is not linted.
    text = (repo / 'pyproject.toml').read_text()
    (repo / 'pyproject.toml').write_text(text.split('[tool.ruff]')[0])
    bad.write_text(head + '\nimport os\n')
    cc_public.commit.commit(repo, 'No linter asked for')
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '4'


def test_commit_refuses_an_import_against_the_layers(repo):
    tree = cc_public.edit.tree.Tree([repo])
    bad  = cc_public.edit.new.new(tree, 't_python_module', 'pym_cc_public.check.upward',
                                  tree.defaults())
    for field in ('title', 'brief', 'description'):
        cc_public.edit.field.set_field(tree, 'pym_cc_public.check.upward', field, value = 'Upward')
    head = bad.read_text()
    bad.write_text(head + '\nimport cc_public.workflow\n\nprint(cc_public.workflow.Stop)\n')
    with pytest.raises(cc_public.commit.ErrorCommit) as caught:
        cc_public.commit.commit(repo, 'A check that imports a workflow')
    assert 'lint' in str(caught.value)
    assert 'cc_public.check.upward -> cc_public.workflow' in str(caught.value)
    assert git(repo, 'rev-list', '--count', 'HEAD').strip() == '1'


def test_commit_checks_a_consumer_beside_the_core_it_names(repo, tmp_path):
    consumer = tmp_path.parent / (tmp_path.name + '-consumer')   # beside the core, not in it
    consumer.mkdir()
    (consumer / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright 2026 William Payne"\n'
        'license = "Apache-2.0"\nid_mark = "mark_public"\n')
    git(consumer, 'init', '-q')
    tree = cc_public.edit.tree.Tree([consumer, repo])
    cc_public.edit.new.new(tree, 't_segment', 'seg_consumer', tree.defaults(),
                           dirpath_out = consumer / 'segment')
    for (field, value) in (('title', 'A consumer'), ('role', 'segment')):
        cc_public.edit.field.set_field(tree, 'seg_consumer', field, value = value)
    for (field, value) in (('brief', 'A segment beside the core, consuming it.'),
                           ('description', 'It holds nothing but itself.')):
        cc_public.edit.field.set_field(tree, 'seg_consumer', field, prose = value)
    cc_public.edit.link.link(tree, 'seg_consumer', 'r_consumes', 'seg_cc_public')

    with pytest.raises(cc_public.commit.ErrorCommit, match = 'did not complete'):
        cc_public.commit.commit(consumer, 'Declare the segment')   # no type register here

    (hash, id_self) = cc_public.commit.commit(consumer, 'Declare the segment',
                                              list_path = [repo])
    assert git(consumer, 'status', '--porcelain') == ''
    c = next(cc_public.load.git.iter_commit(consumer, 1))
    assert c.hash == hash and c.document['id_self'] == id_self
    assert c.document['check']['critical'] == 0
    assert git(repo, 'status', '--porcelain') == ''                 # the core is untouched
