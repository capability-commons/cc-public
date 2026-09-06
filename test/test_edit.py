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
relation:               []

...
"""

import pathlib
import re

import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load
import cc_public.path
from conftest import DEFAULTS, clean, copy_tree


def test_path_write_sets_and_appends_and_refuses_missing_parent():
    node = {'a': {'b': [1]}}
    cc_public.path.write(node, 'a.c', 2)
    cc_public.path.write(node, 'a.b.1', 3)
    assert node == {'a': {'b': [1, 3], 'c': 2}}
    with pytest.raises(KeyError):
        cc_public.path.write(node, 'x.y', 1)


def test_resolve_top_level_and_embedded(tree):
    assert tree.resolve('wf_design_decision_from_schema').path == ''
    node = tree.resolve('node_design_decision_from_schema.draft')
    assert node.path == 'node.draft'
    assert tree.resolve(node.guid_self).id_self == node.id_self
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        tree.resolve('nothing_here')


def test_set_scalar_prose_and_embedded(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'budget', value = 7)
    cc_public.edit.field.set_field(tree, 'node_design_decision_from_schema.draft',
                                   'brief', prose = 'Drafts it, twice.')
    dep = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_design_decision_from_schema_local.yaml')
    wf  = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'wf_design_decision_from_schema.yaml')
    assert dep['budget'] == 7
    assert wf['node']['draft']['brief'] == 'Drafts it, twice.\n'
    text = (tmp_path / 'workflow' / 'wf_design_decision_from_schema.yaml').read_text()
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
                             'node_design_decision_from_schema.draft')
    doc = cc_public.load.from_file(tmp_path / 'ddr' / 'ddr_component.yaml')
    assert doc['relation'][-1]['id_target'] == 'node_design_decision_from_schema.draft'
    assert doc['relation'][-1]['guid_target'].startswith('node_')

    cc_public.edit.link.link(tree, 'node_design_decision_from_schema.draft',
                             'r_is_judged_by', 'evl_prose_describes')
    wf = cc_public.load.from_file(tmp_path / 'workflow'
                                  / 'wf_design_decision_from_schema.yaml')
    assert any(e['id_relation'] == 'r_is_judged_by'
               for e in wf['node']['draft']['relation'])

    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.link.link(tree, 'ddr_component', 'r_decides',
                                 'node_design_decision_from_schema.draft')   # again
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
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'note', prose = 'A note added late.')
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_design_decision_from_schema_local.yaml')
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
    assert ins(tree, 't_port', 'context', 'cmp_draft_design_decision', 'input') == \
           ('context', 'prt_draft_design_decision.context')
    assert ins(tree, 't_term', 'widget', 'reg_term') == \
           ('term_widget', 'term_widget')
    assert ins(tree, 't_node', 'index', 'wf_design_decision_from_schema', 'node') == \
           ('index', 'node_design_decision_from_schema.index')

    port = tree.resolve('prt_draft_design_decision.context')
    assert port.path == 'input.context'
    term = cc_public.load.from_file(tmp_path / 'register' / 'reg_term.yaml')
    assert term['table']['term_widget']['id_self'] == 'term_widget'
    assert term['table']['term_widget']['term'] == ''
    wf = cc_public.load.from_file(tmp_path / 'workflow'
                                  / 'wf_design_decision_from_schema.yaml')
    assert wf['node']['index']['relation'] == []

    cc_public.edit.field.set_field(tree, 'prt_draft_design_decision.context',
                                   'title', value = 'Context')
    # Empty fields fail their schema, and an empty node names no
    # component, which the workflow check rightly reports too.
    faults = clean(tmp_path)
    assert faults and {c for (c, _) in faults} <= {'schema', 'workflow'}

    with pytest.raises(cc_public.edit.tree.ErrorItem):     # key taken
        ins(tree, 't_port', 'subject', 'cmp_draft_design_decision', 'input')
    with pytest.raises(cc_public.edit.tree.ErrorItem):     # --at needed
        ins(tree, 't_port', 'x', 'cmp_draft_design_decision')
    with pytest.raises(cc_public.edit.tree.ErrorItem):     # not a collection
        ins(tree, 't_port', 'x', 'cmp_draft_design_decision', 'title')


def test_insert_appends_to_a_list(tree, tmp_path):
    (key, made) = cc_public.edit.insert.insert(
                    tree, 't_protective_mark', 'second',
                    'dep_design_decision_from_schema_local', 'protective_mark')
    assert made is None                                     # no identity in a reference
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_design_decision_from_schema_local.yaml')
    assert len(doc['protective_mark']) == 2
    assert set(doc['protective_mark'][1]) == {'id_mark', 'guid_mark'}


def test_unset_removes_a_field_and_refuses_a_missing_one(tree, tmp_path):
    cc_public.edit.field.unset_field(tree, 'dep_design_decision_from_schema_local',
                                     'description')
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_design_decision_from_schema_local.yaml')
    assert 'description' not in doc
    with pytest.raises(KeyError):
        cc_public.edit.field.unset_field(tree, 'dep_design_decision_from_schema_local',
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
                       and 'question' not in tree.context.map_document[item.location])
    (key, made) = cc_public.edit.insert.insert(tree, 't_question', 'first',
                                               id_record, 'question')
    assert made == 'qst_' + id_record.split('_', 1)[1] + '.first'
    doc = cc_public.load.from_file(tree.resolve(id_record).filepath)
    assert list(doc['question']) == ['first']


def test_path_steps_are_plain():
    assert cc_public.path.join('edge', 'draft_to_review') == 'edge.draft_to_review'
    assert cc_public.path.split('edge.draft_to_review.guard') == \
           ['edge', 'draft_to_review', 'guard']
    node = {'edge': {'draft_to_review': {'to': 'x'}}}
    cc_public.path.write(node, 'edge.draft_to_review.guard', 'met')
    assert node['edge']['draft_to_review']['guard'] == 'met'


def test_unset_last_key_leaves_an_empty_mapping(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'extra', value = {'only': 1})
    cc_public.edit.field.unset_field(tree, 'dep_design_decision_from_schema_local',
                                     'extra.only')
    doc = cc_public.load.from_file(tmp_path / 'workflow'
                                   / 'dep_design_decision_from_schema_local.yaml')
    assert doc['extra'] == {}
    cc_public.edit.field.unset_field(tree, 'dep_design_decision_from_schema_local', 'extra')


def test_rename_carries_to_qualified_items_references_and_file(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_edit.test_rename_carries_to_qualified_items_references_and_file
    guid_self:              pyf_735385cfb85b4e9eb1381957b9f6f751
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A rename carries to qualified items, references and the file
    brief:                  |
                            A rename carries to qualified items,
                            references and the file.
    description:            |
                            Renames a component and asserts its guid is
                            unchanged, its file and the ids it qualifies
                            follow, every reference is repointed, a local
                            key can change only its last step, and a
                            python item is refused.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_renamer_keeps_guid
        guid_target:        req_9e78e8f7be56415a87394b2065de11e8

    ...
    """

    import cc_public.edit.rename
    guid   = tree.resolve('cmp_draft_design_decision').guid_self
    report = cc_public.edit.rename.rename(tree, 'cmp_draft_design_decision',
                                          'cmp_draft_thing')
    assert report.map_rename['prt_draft_design_decision.decision'] == 'prt_draft_thing.decision'
    assert not (tmp_path / 'workflow' / 'cmp_draft_design_decision.yaml').exists()
    doc = cc_public.load.from_file(tmp_path / 'workflow' / 'cmp_draft_thing.yaml')
    assert doc['id_self'] == 'cmp_draft_thing'
    assert doc['guid_self'] == guid                 # the guid is the identity; it stays
    assert doc['output']['decision']['id_self'] == 'prt_draft_thing.decision'
    wf = cc_public.load.from_file(tmp_path / 'workflow' / 'wf_design_decision_from_schema.yaml')
    edge = next(e for e in wf['node']['draft']['relation']
                if e['id_relation'] == 'r_instantiates')
    assert edge['id_target'] == 'cmp_draft_thing'
    assert clean(tmp_path) == []
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.rename.rename(tree, 'prt_draft_thing.decision', 'prt_x.y')
    cc_public.edit.rename.rename(tree, 'prt_draft_thing.decision',
                                 'prt_draft_thing.made')
    doc = cc_public.load.from_file(tmp_path / 'workflow' / 'cmp_draft_thing.yaml')
    assert list(doc['output']) == ['made']
    assert doc['output']['made']['id_self'] == 'prt_draft_thing.made'
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.rename.rename(tree, 'cmp_draft_thing', 'zzz_draft')


def test_rename_register_entry_rekeys_in_place(tree, tmp_path):
    import cc_public.edit.rename
    doc  = cc_public.load.from_file(tmp_path / 'register' / 'reg_term.yaml')
    keys = list(doc['table'])
    cc_public.edit.rename.rename(tree, keys[1], 'term_renamed')
    doc  = cc_public.load.from_file(tmp_path / 'register' / 'reg_term.yaml')
    assert list(doc['table'])[1] == 'term_renamed'
    assert doc['table']['term_renamed']['id_self'] == 'term_renamed'
    assert clean(tmp_path) == []


def test_set_value_with_a_line_break_becomes_a_block_scalar(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'extra', value = [{'input': 'one\ntwo', 'n': 1}])
    text = (tmp_path / 'workflow' / 'dep_design_decision_from_schema_local.yaml').read_text()
    assert re.search(r'input: +\\|\n', text)
    doc = cc_public.load.from_file(tmp_path / 'workflow' / 'dep_design_decision_from_schema_local.yaml')
    assert doc['extra'][0]['input'] == 'one two\n'    # refilled by the printer
    cc_public.edit.field.unset_field(tree, 'dep_design_decision_from_schema_local', 'extra')


def test_an_execution_may_name_what_has_gone(tree, tmp_path):
    import cc_public.check.reference
    exe = next(p for p in (tmp_path / 'execution').glob('exe_*.yaml'))
    doc = cc_public.load.from_file(exe)
    gone = next(b['guid_node'] for b in doc['binding'].values())
    # take the declaration away by deleting the workflow that holds the node
    wf = next(p for p in (tmp_path / 'workflow').glob('wf_*.yaml') if gone in p.read_text())
    wf.unlink()
    rep = cc_public.check.check(list_path = [tmp_path])['report']
    ref = next(c for c in rep['check'] if c['id_check'] == 'reference')
    assert not [n for n in ref['nonconformity'] if gone in n['message']]
    assert [n for n in ref['note'] if gone in n['message']]


def test_a_need_composes_its_statement_and_a_requirement_must_trace(tree, tmp_path):
    import cc_public.need
    import cc_public.eval.select
    doc = cc_public.load.from_file(tmp_path / 'need' / 'need_runs_bounded.yaml')
    text = cc_public.need.statement(doc)
    assert text.startswith('In Workflows with back edges') and 'need A run that loops' in text \
           and text.endswith('before it starts.')
    assert 'statement' not in doc
    rendered = cc_public.eval.select.render((('need_runs_bounded', doc),), {'scope': {'include': ['statement']}})
    assert 'statement:' in rendered and 'in order to' in rendered
    cc_public.edit.field.set_field(tree, 'req_executor_honours_budget', 'status', value = 'proposed')
    cc_public.edit.field.unset_field(tree, 'req_executor_honours_budget', 'relation')
    rep = cc_public.check.check(list_path = [tmp_path])['report']
    trace = next(c for c in rep['check'] if c['id_check'] == 'trace')
    derived = [n for n in trace['nonconformity']
                 if n['path'] == 'relation' and n['message'].startswith('Derives from nothing')]
    assert [n['severity'] for n in derived] == ['advisory']
    assert 'req_executor_honours_budget' in derived[0]['filepath']
    # This copy holds no tests, so every requirement verified by test says
    # no test names it; the tree itself says otherwise.
    verified = [n for n in trace['nonconformity'] if n['path'] == 'verification']
    count_test = sum(1 for d in tree.context.map_document.values()
                     if isinstance(d, dict) and str(d.get('id_self', '')).startswith('req_')
                     and d.get('verification') == 'test')
    assert len(verified) == count_test and all(n['severity'] == 'advisory' for n in verified)


def test_a_tree_that_cannot_be_read_entirely_refuses_to_be_edited(tmp_path):
    copy_tree(tmp_path)
    (tmp_path / 'ddr' / 'ddr_broken.yaml').write_text('id_self: [unclosed\n')
    with pytest.raises(cc_public.edit.tree.ErrorItem) as caught:
        cc_public.edit.tree.Tree([tmp_path])
    assert 'ddr_broken.yaml' in str(caught.value)
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.tree.Tree([tmp_path / 'nowhere'])
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.tree.Tree([])


def test_defaults_come_from_the_tree_and_not_from_where_the_command_runs(tmp_path, monkeypatch):
    target = tmp_path / 'target'
    target.mkdir()
    copy_tree(target)
    (target / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright of the target"\n'
        'license = "Apache-2.0"\nid_mark = "mark_public"\n')
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    (elsewhere / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright of elsewhere"\n'
        'license = "MIT"\nid_mark = "mark_public"\n')
    monkeypatch.chdir(elsewhere)
    tree = cc_public.edit.tree.Tree([target])
    assert tree.defaults()['copyright'] == 'Copyright of the target'
    path = cc_public.edit.new.new(tree, 't_ddr', 'ddr_made_from_elsewhere',
                                  tree.defaults())
    assert cc_public.load.from_file(path)['copyright'] == 'Copyright of the target'
    (target / 'pyproject.toml').unlink()
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.tree.Tree([target]).defaults()


def test_a_failed_rename_puts_every_file_back(tree, tmp_path, monkeypatch):
    import cc_public.edit.rename
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.yaml')}
    saved  = []
    real   = cc_public.edit.tree.save

    def failing_save(filepath, document):
        if len(saved) == 2:
            raise OSError('disk full')
        saved.append(filepath)
        real(filepath, document)

    monkeypatch.setattr(cc_public.edit.tree, 'save', failing_save)
    with pytest.raises(OSError):
        cc_public.edit.rename.rename(tree, 'cmp_draft_design_decision', 'cmp_draft_decision')
    assert len(saved) == 2
    after = {p: p.read_bytes() for p in tmp_path.rglob('*.yaml')}
    assert after == before

    monkeypatch.setattr(cc_public.edit.tree, 'save', real)
    monkeypatch.setattr(pathlib.Path, 'rename',
                        lambda _self, _target: (_ for _ in ()).throw(OSError("cannot move")))
    with pytest.raises(OSError):
        cc_public.edit.rename.rename(tree, 'cmp_draft_design_decision', 'cmp_draft_decision')
    after = {p: p.read_bytes() for p in tmp_path.rglob('*.yaml')}
    assert after == before
    assert (tmp_path / 'workflow' / 'cmp_draft_design_decision.yaml').exists()


def test_a_write_is_the_old_file_or_the_new_one_and_keeps_its_mode(tmp_path, monkeypatch):
    import os
    target = tmp_path / 'thing.yaml'
    target.write_text('old\n')
    target.chmod(0o640)
    cc_public.edit.tree.write_text(target, 'new\n')
    assert target.read_text() == 'new\n'
    assert (target.stat().st_mode & 0o777) == 0o640
    assert list(tmp_path.iterdir()) == [target]

    monkeypatch.setattr(os, 'replace',
                        lambda _src, _dst: (_ for _ in ()).throw(OSError("interrupted")))
    with pytest.raises(OSError):
        cc_public.edit.tree.write_text(target, 'newer\n')
    assert target.read_text() == 'new\n'
    assert list(tmp_path.iterdir()) == [target]


def test_an_edge_runs_between_what_its_relation_allows(tree, tmp_path):
    def faults():
        return [m for (c, m) in clean(tmp_path) if c == 'relation']

    assert faults() == []

    # A requirement may derive from a need or a requirement, not a register.
    def last(item):
        doc = tree.context.map_document[tree.resolve(item).location]
        return 'relation.{n}'.format(n = len(doc['relation']) - 1)

    cc_public.edit.link.link(tree, 'req_printer_idempotent', 'r_is_derived_from', 'reg_type')
    assert any('runs to t_need or t_textual_requirement' in m for m in faults())
    edge = last('req_printer_idempotent')
    cc_public.edit.field.set_field(tree, 'req_printer_idempotent', edge + '.guid_target',
                                   value = tree.resolve('req_renamer_keeps_guid').guid_self)
    cc_public.edit.field.set_field(tree, 'req_printer_idempotent', edge + '.id_target',
                                   value = 'req_renamer_keeps_guid')
    assert faults() == []

    # Derivation forms no cycle, and an item does not derive from itself.
    cc_public.edit.link.link(tree, 'req_renamer_keeps_guid', 'r_is_derived_from',
                             'req_printer_idempotent')
    assert any('cycle' in m and 'req_printer_idempotent -> req_renamer_keeps_guid' in m
               for m in faults())
    edge = last('req_renamer_keeps_guid')
    cc_public.edit.field.set_field(tree, 'req_renamer_keeps_guid', edge + '.guid_target',
                                   value = tree.resolve('req_renamer_keeps_guid').guid_self)
    cc_public.edit.field.set_field(tree, 'req_renamer_keeps_guid', edge + '.id_target',
                                   value = 'req_renamer_keeps_guid')
    assert any('cycle' in m and 'req_renamer_keeps_guid -> req_renamer_keeps_guid' in m
               for m in faults())

    # A relation that constrains nothing constrains nothing; a constraint
    # naming no type is a fault at the entry.
    cc_public.edit.link.link(tree, 'ddr_fail_closed', 'r_decides', 'req_printer_idempotent')
    assert not any('r_decides' in m for m in faults())
    cc_public.edit.field.set_field(tree, 'r_decides', 'range', value = ['t_nonsense'])
    assert any('t_nonsense' in m and 'not a type' in m for m in faults())


def test_an_item_naming_two_schemas_is_a_fault(tree, tmp_path):
    cc_public.edit.link.link(tree, 'reg_framing', 'r_is_specified_by_schema', 'sch_register')
    faults = [(c, m) for (c, m) in clean(tmp_path) if c == 'schema']
    assert len(faults) == 1 and 'Names 2 schemas' in faults[0][1]


def test_a_plain_register_refuses_a_field_its_entries_do_not_declare(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'frame_supply', 'bogus', value = 1)
    faults = [(c, m) for (c, m) in clean(tmp_path) if c == 'schema']
    assert len(faults) == 1 and 'bogus' in faults[0][1]
    cc_public.edit.field.unset_field(tree, 'frame_supply', 'bogus')
    assert clean(tmp_path) == []


def test_a_concrete_schema_refuses_a_field_it_does_not_declare(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_edit.test_a_concrete_schema_refuses_a_field_it_does_not_declare
    guid_self:              pyf_352156764ce54b61b1b011e7896f4e60
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A concrete schema refuses a field it does not declare
    brief:                  |
                            A concrete schema refuses a field it does not
                            declare.
    description:            |
                            Writes a misspelled field into a decision, a
                            question, a port and a type entry, and asserts
                            each is reported once, at the path where it
                            was written, and never as its parent's fault.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_checker_locates_each_finding
        guid_target:        req_9186d8b81a574b2cbbe0f1cf370d2cf9

    ...
    """

    def schema_faults():
        return [(m.split("'")[1], p) for (c, m, p) in
                [(c, n['message'], n['path']) for c in cc_public.check.check(
                    list_path = [tmp_path])['report']['check'] if c['id_check'] == 'schema'
                 for n in c['nonconformity']]
                if 'Unevaluated' in m]

    assert schema_faults() == []
    cc_public.edit.field.set_field(tree, 'ddr_fail_closed', 'descripton', value = 'x')
    cc_public.edit.field.set_field(tree, 'qst_code_quality.trace', 'bogus', value = 'x')
    cc_public.edit.field.set_field(tree, 'prt_draft_design_decision.decision', 'optinal', value = True)
    cc_public.edit.field.set_field(tree, 't_ddr', 'prefx', value = 'x')
    # Each is reported once, at its own path, and never as its parent's fault.
    assert sorted(schema_faults()) == [('bogus', 'question.trace'), ('descripton', ''),
                                       ('optinal', 'output.decision'), ('prefx', 'table.t_ddr')]


def test_an_item_may_narrow_its_type_schema_and_not_replace_it(tree, tmp_path):
    def faults():
        return [n['message'] for c in cc_public.check.check(list_path = [tmp_path])['report']['check']
                if c['id_check'] == 'schema' for n in c['nonconformity']]

    cc_public.edit.new.new(tree, 't_schema', 'sch_other', DEFAULTS)
    for (k, v) in (('$schema', 'https://json-schema.org/draft/2020-12/schema'),
                   ('$id', 'https://capability-commons.org/schema/sch_other.yaml'),
                   ('title', 'Other'), ('brief', 'Other.'), ('description', 'Other.'),
                   ('type', 'object')):
        cc_public.edit.field.set_field(tree, 'sch_other', k, value = v)
    cc_public.edit.link.link(tree, 'need_runs_bounded', 'r_is_specified_by_schema', 'sch_other')
    assert any('does not compose sch_need' in m for m in faults())

    cc_public.edit.field.set_field(tree, 'sch_other', 'allOf',
                                   value = [{'$ref': 'https://capability-commons.org/schema/sch_need.yaml'}])
    assert not any('does not compose' in m for m in faults())


def test_unsetting_the_last_edge_leaves_an_empty_list(tree, tmp_path):
    cc_public.edit.field.unset_field(tree, 'ddr_fail_closed', 'relation.0')
    n = len(cc_public.load.from_file(tmp_path / 'ddr' / 'ddr_fail_closed.yaml')['relation'])
    for i in reversed(range(n)):
        cc_public.edit.field.unset_field(tree, 'ddr_fail_closed', 'relation.{n}'.format(n = i))
    doc = cc_public.load.from_file(tmp_path / 'ddr' / 'ddr_fail_closed.yaml')
    assert doc['relation'] == []
    cc_public.edit.link.link(tree, 'ddr_fail_closed', 'r_decides', 'pym_cc_public.commit')
    assert [(c, m) for (c, m) in clean(tmp_path) if c != 'source'] == []


def test_set_stores_a_string_as_prose_where_the_schema_says_so(tree, tmp_path):
    cc_public.edit.field.set_field(tree, 'need_runs_bounded', 'entity', value = 'Executor')
    cc_public.edit.field.set_field(tree, 'need_runs_bounded', 'purpose', value = 'Keep a run paid for.')
    text = (tmp_path / 'need' / 'need_runs_bounded.yaml').read_text()
    assert 'entity:                 Executor\n' in text                 # bounded: a datum
    assert 'purpose:                |\n' in text                        # unbounded: prose
    cc_public.edit.field.set_field(tree, 'ddr_fail_closed', 'title', value = 'Fail closed, again')
    cc_public.edit.field.set_field(tree, 'ddr_fail_closed', 'brief', value = 'One sentence of brief.')
    text = (tmp_path / 'ddr' / 'ddr_fail_closed.yaml').read_text()
    assert 'title:                  Fail closed, again\n' in text
    assert 'brief:                  |\n' in text
    # an embedded item's field, by the entry schema; and a deeper path, by the value
    cc_public.edit.field.set_field(tree, 'term_location', 'brief', value = 'Where a document sits.')
    cc_public.edit.field.set_field(tree, 't_query', 'prefix', value = 'qry')
    text = (tmp_path / 'register' / 'reg_term.yaml').read_text()
    assert '    brief:              |\n                        Where a document sits.\n' in text
    assert 'prefix:             qry\n' in (tmp_path / 'register' / 'reg_type.yaml').read_text()
    cc_public.edit.field.set_field(tree, 'sch_deployment', 'allOf.2.properties.confirm.description',
                                   value = 'One line, no break.')
    assert re.search(r'description:\s+One line, no break\.\n',
                     (tmp_path / 'schema' / 'sch_deployment.yaml').read_text())
    assert clean(tmp_path) == []
