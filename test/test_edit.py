"""
---

id_self:                pym_test.test_edit
guid_self:              pym_bdcca95e7ee04a7998c895d39eae49d4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Edit tests
brief:                  |
                        new, set and link make well formed changes and
                        refuse what they should.
description:            |
                        Copies the tree, then makes items, sets fields
                        and links items through the edit package,
                        asserting each change is well formed and each
                        refusal is refused.

...
"""

import pathlib
import shutil

import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load
import cc_public.path


ROOT     = pathlib.Path(__file__).resolve().parent.parent
DEFAULTS = {'copyright': 'Copyright 2026 William Payne',
            'license':   'Apache-2.0',
            'id_mark':   'mark_public'}
KEEP     = ('ddr', 'schema', 'register', 'eval', 'workflow', 'src')


@pytest.fixture
def tree(tmp_path):
    for name in KEEP:
        shutil.copytree(ROOT / name, tmp_path / name)
    return cc_public.edit.tree.Tree([tmp_path])


def clean(root):
    report = cc_public.check.check(list_path = [root])['report']
    return [(c['id_check'], n['message'])
            for c in report['check'] for n in c['nonconformity']
            if n['severity'] == 'critical']


def test_path_write_sets_and_appends_and_refuses_missing_parent():
    node = {'a': {'b': [1]}}
    cc_public.path.write(node, 'a.c', 2)
    cc_public.path.write(node, 'a.b.1', 3)
    assert node == {'a': {'b': [1, 3], 'c': 2}}
    with pytest.raises(KeyError):
        cc_public.path.write(node, 'x.y', 1)


def test_resolve_top_level_and_embedded(tree):
    assert tree.resolve('wf_record_from_schema').path == ''
    node = tree.resolve('node_record_from_schema.draft')
    assert node.path == 'node.draft'
    assert tree.resolve(node.guid_self).id_self == node.id_self
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        tree.resolve('nothing_here')


def test_set_scalar_prose_and_embedded(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'dep_record_from_schema_local',
                                   'budget', value = '7')
    cc_public.edit.field.set_field(tree, 'node_record_from_schema.draft',
                                   'brief', prose = 'Drafts it, twice.')
    dep = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_record_from_schema_local.yaml')
    wf  = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'wf_record_from_schema.yaml')
    assert dep['budget'] == 7
    assert wf['node']['draft']['brief'] == 'Drafts it, twice.\n'
    text = (tmp_path / 'workflow' / 'wf_record_from_schema.yaml').read_text()
    assert '    brief:              |\n' in text
    assert clean(tmp_path) == []


def test_set_on_a_python_docstring(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'pym_cc_public.path', 'title',
                                   value = 'Paths')
    p = tmp_path / 'src' / 'cc_public' / 'path.py'
    assert cc_public.load.from_file(p)['title'] == 'Paths'
    assert 'def select(' in p.read_text()
    assert clean(tmp_path) == []


def test_link_top_level_and_embedded_and_refusals(tree, tmp_path):
    cc_public.edit.link.link(tree, 'ddr_component', 'r_decides',
                             'node_record_from_schema.draft')
    doc = cc_public.load.from_file(tmp_path / 'ddr' / 'ddr_component.yaml')
    assert doc['relation'][-1]['id_target'] == 'node_record_from_schema.draft'
    assert doc['relation'][-1]['guid_target'].startswith('node_')

    cc_public.edit.link.link(tree, 'node_record_from_schema.draft',
                             'r_is_judged_by', 'evl_prose_describes')
    wf = cc_public.load.from_file(tmp_path / 'workflow'
                                  / 'wf_record_from_schema.yaml')
    assert any(e['id_relation'] == 'r_is_judged_by'
               for e in wf['node']['draft']['relation'])

    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.link.link(tree, 'ddr_component', 'r_decides',
                                 'node_record_from_schema.draft')   # again
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.link.link(tree, 'ddr_component', 'r_nonsense',
                                 'sch_port')
    assert clean(tmp_path) == []


def test_new_makes_a_skeleton_that_fails_until_written(tree, tmp_path):
    path = cc_public.edit.new.new(tree, 't_ddr', 'ddr_example', DEFAULTS)
    assert path == tmp_path / 'ddr' / 'ddr_example.yaml'
    doc = cc_public.load.from_file(path)
    assert doc['guid_self'].startswith('ddr_') and len(doc['guid_self']) == 36
    for key in ('title', 'brief', 'context', 'decision', 'rationale',
                'alternative', 'consequence'):
        assert doc[key] == ''
    assert doc['relation'] == []
    assert doc['protective_mark'][0]['id_mark'] == 'mark_public'
    faults = clean(tmp_path)
    assert faults and all(c == 'schema' for (c, _) in faults)

    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.new.new(tree, 't_ddr', 'bad id', DEFAULTS)
    with pytest.raises(cc_public.edit.tree.ErrorItem):     # no parent package
        cc_public.edit.new.new(tree, 't_python_module', 'pym_x', DEFAULTS)


def test_set_keeps_relation_last(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'dep_record_from_schema_local',
                                   'note', prose = 'A note added late.')
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_record_from_schema_local.yaml')
    assert list(doc)[-1] == 'relation'
    assert clean(tmp_path) == []


def test_new_source_package_then_module(tree, tmp_path):
    import ast
    package = cc_public.edit.new.new(tree, 't_python_package',
                                     'pyp_cc_public.demo', DEFAULTS)
    assert package == tmp_path / 'src' / 'cc_public' / 'demo' / '__init__.py'
    module = cc_public.edit.new.new(tree, 't_python_module',
                                    'pym_cc_public.demo.thing', DEFAULTS)
    assert module == tmp_path / 'src' / 'cc_public' / 'demo' / 'thing.py'

    for (path, id_self) in ((package, 'pyp_cc_public.demo'),
                            (module, 'pym_cc_public.demo.thing')):
        ast.parse(path.read_text())                        # a valid file
        doc = cc_public.load.from_file(path)
        assert doc['id_self'] == id_self and doc['title'] == ''
        assert doc['guid_self'].startswith(id_self.split('_', 1)[0] + '_')

    faults = clean(tmp_path)
    assert faults and all(c == 'schema' for (c, _) in faults)

    cc_public.edit.field.set_field(tree, 'pym_cc_public.demo.thing',
                                   'title', value = 'Thing')
    assert cc_public.load.from_file(module)['title'] == 'Thing'

    with pytest.raises(cc_public.edit.tree.ErrorItem):     # embedded kinds
        cc_public.edit.new.new(tree, 't_python_class',
                               'pyc_cc_public.demo.thing.k', DEFAULTS)


def test_insert_port_term_node_and_refusals(tree, tmp_path):
    ins = cc_public.edit.insert.insert
    assert ins(tree, 't_port', 'context', 'cmp_draft_record', 'input') == \
           ('context', 'prt_draft_record.context')
    assert ins(tree, 't_term', 'widget', 'reg_term') == \
           ('term_widget', 'term_widget')
    assert ins(tree, 't_node', 'index', 'wf_record_from_schema', 'node') == \
           ('index', 'node_record_from_schema.index')

    port = tree.resolve('prt_draft_record.context')
    assert port.path == 'input.context'
    term = cc_public.load.from_file(tmp_path / 'register' / 'reg_term.yaml')
    assert term['table']['term_widget']['id_self'] == 'term_widget'
    assert term['table']['term_widget']['term'] == ''
    wf = cc_public.load.from_file(tmp_path / 'workflow'
                                  / 'wf_record_from_schema.yaml')
    assert wf['node']['index']['relation'] == []

    cc_public.edit.field.set_field(tree, 'prt_draft_record.context',
                                   'title', value = 'Context')
    # Empty fields fail their schema, and an empty node names no
    # component, which the workflow check rightly reports too.
    faults = clean(tmp_path)
    assert faults and {c for (c, _) in faults} <= {'schema', 'workflow'}

    with pytest.raises(cc_public.edit.tree.ErrorItem):     # key taken
        ins(tree, 't_port', 'subject', 'cmp_draft_record', 'input')
    with pytest.raises(cc_public.edit.tree.ErrorItem):     # --at needed
        ins(tree, 't_port', 'x', 'cmp_draft_record')
    with pytest.raises(cc_public.edit.tree.ErrorItem):     # not a collection
        ins(tree, 't_port', 'x', 'cmp_draft_record', 'title')


def test_insert_appends_to_a_list(tree, tmp_path):
    (key, made) = cc_public.edit.insert.insert(
                    tree, 't_protective_mark', 'second',
                    'dep_record_from_schema_local', 'protective_mark')
    assert made is None                                     # no identity in a reference
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_record_from_schema_local.yaml')
    assert len(doc['protective_mark']) == 2
    assert set(doc['protective_mark'][1]) == {'id_mark', 'guid_mark'}


def test_unset_removes_a_field_and_refuses_a_missing_one(tree, tmp_path):
    cc_public.edit.field.unset_field(tree, 'dep_record_from_schema_local',
                                     'description')
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_record_from_schema_local.yaml')
    assert 'description' not in doc
    with pytest.raises(KeyError):
        cc_public.edit.field.unset_field(tree, 'dep_record_from_schema_local',
                                         'nothing')


def test_questions_report_open_and_answered(tree, tmp_path):
    import cc_public.question
    rows = cc_public.question.report(tree.context.map_document)
    assert rows, 'the records carry questions'
    answered = [r for r in rows if r[3]]
    assert answered and all(r[3] for r in answered)
    assert any('ddr_eval_measurement' in r[3] for r in answered)
    (id_record, id_question, text, _) = next(r for r in rows if not r[3])
    cc_public.edit.link.link(tree, 'ddr_question', 'r_answers', id_question)
    rows = cc_public.question.report(tree.context.map_document)
    assert next(r for r in rows if r[1] == id_question)[3] == ['ddr_question']


def test_insert_creates_an_absent_collection(tree, tmp_path):
    # A record that carries no question table yet, whichever that is.
    id_record = next(i for (i, item) in sorted(tree.map_id.items())
                       if i.startswith('ddr_') and not item.path
                       and 'question' not in tree.context.map_document[item.filepath])
    (key, made) = cc_public.edit.insert.insert(tree, 't_question', 'first',
                                               id_record, 'question')
    assert made == 'qst_' + id_record.split('_', 1)[1] + '.first'
    doc = cc_public.load.from_file(tree.resolve(id_record).filepath)
    assert list(doc['question']) == ['first']
