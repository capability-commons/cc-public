"""
---

id_self:                pym_test.test_run
guid_self:              pym_42cc1fc152dc49b8af7db5e78cfc4c85
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Run tests
brief:                  |
                        A workflow runs end to end against a scripted
                        model and judge.
description:            |
                        Copies the tree into a repository, runs the
                        example workflow with a generator that answers
                        from a table and a judge that answers as told,
                        and asserts what was made, revised, bound,
                        fired, declined, stopped, restored and
                        committed.

...
"""

import pathlib
import shutil
import subprocess

import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.tree
import cc_public.eval.control
import cc_public.eval.runner
import cc_public.load
import cc_public.load.git
import cc_public.workflow.run


ROOT = pathlib.Path(__file__).resolve().parent.parent
KEEP = ('ddr', 'schema', 'register', 'eval', 'workflow', 'src', 'pyproject.toml')

FIELDS = {'title':       'Identity trait',
          'brief':       'What every item declares to be addressable.',
          'context':     'Things needed naming.',
          'decision':    'Two fields declare an identity.',
          'rationale':   'A guid resolves; an id reads.',
          'alternative': 'One field. Rejected.',
          'consequence': 'Every item carries both.',
          'slug':        'identity_trait'}


class Scripted:
    """A generator answering from a table, with a per node override."""

    id_model = 'scripted'

    def __init__(self, table = None):
        self.table = table or {}
        self.calls = []

    def produce(self, prompt, map_input, list_field, want_slug):
        self.calls.append((sorted(map_input), list(list_field), want_slug))
        answer = dict(FIELDS)
        answer.update(self.table)
        return {f: answer.get(f, '') for f in list(list_field) + (['slug'] if want_slug else [])}


class Judge:
    """Answers as told: one verdict for all, or a sequence then met."""

    id_model = 'judge'

    def __init__(self, verdict = 'met'):
        self.verdict = verdict
        self.queue   = list(verdict) if isinstance(verdict, list) else None

    def run(self, task):
        verdict = (self.queue.pop(0) if self.queue else 'met') \
                  if self.queue is not None else self.verdict
        return cc_public.eval.runner.Verdict(task.id_eval, task.id_subject,
                                             verdict, 'scripted', self.id_model)

    def confirm(self, task, verdict, count):
        return verdict

    def sample(self, task, count):
        return [self.verdict] * count


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), '-c', 'user.name=T',
                           '-c', 'user.email=t@t', *args],
                          capture_output = True, text = True, check = True).stdout


@pytest.fixture
def repo(tmp_path):
    for name in KEEP:
        src = ROOT / name
        (shutil.copytree if src.is_dir() else shutil.copy)(src, tmp_path / name)
    git(tmp_path, 'init', '-q'); git(tmp_path, 'add', '-A')
    git(tmp_path, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'start')
    return tmp_path


def deploy(repo, **kw):
    tree = cc_public.edit.tree.Tree([repo])
    for (k, v) in kw.items():
        cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local', k, value = v)
    git(repo, 'add', '-A'); git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'deploy')


def clean(root):
    rep = cc_public.check.check(list_path = [root])['report']
    return [n['message'] for c in rep['check'] for n in c['nonconformity']
            if n['severity'] == 'critical']


BIND = {'draft.input.subject': 'sch_identity',
        'draft.input.guide':   'reg_writing_style_rule',
        'review.input.guide':  'reg_writing_style_rule'}


def test_dry_run_plans_and_writes_nothing(repo):
    before = git(repo, 'status', '--porcelain')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   None, None, is_dry = True)
    assert r['order'] == ['draft', 'review']
    assert r['node'][1]['output'] == {'decision': 'revises draft'}
    assert r['execution'] is None
    assert git(repo, 'status', '--porcelain') == before


def test_run_makes_then_revises_and_commits(repo):
    deploy(repo, judge = 'always', commit = 'run')
    gen = Scripted()
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   gen, Judge('met'))
    assert r['stopped'] is None
    (draft, review) = r['node']
    assert draft['made'] == ['ddr_identity_trait'] and draft['revised'] == []
    assert review['revised'] == ['ddr_identity_trait'] and review['made'] == []
    assert draft['fired'] == ['review.input.draft']
    assert sorted(draft['verdict']['decision']) == [('evl_decision_decides', 'met'),
                                                    ('evl_decision_stated', 'met'),
                                                    ('evl_plain_text', 'met'),
                                                    ('evl_prose_matches_structure', 'met'),
                                                    ('evl_records_the_decision', 'met')]

    # the generator was asked exactly the empty prose fields, with the input by port
    assert gen.calls[0] == (['guide', 'subject'], ['title', 'brief', 'context', 'decision',
                                          'rationale', 'alternative', 'consequence'], True)
    assert gen.calls[1][0] == ['draft', 'guide'] and gen.calls[1][2] is False

    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    assert doc['title'] == 'Identity trait'
    assert [(r['id_relation'], r['id_target']) for r in doc['relation']] == \
           [('r_decides', 'sch_identity')]                 # the port says decides: subject

    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert exe['id_self'].startswith('exe_') and len(exe['binding']) == 6
    ports = {b['id_port'] for b in exe['binding'].values()}
    assert 'prt_draft_design_decision.subject' in ports and 'prt_review_design_decision.decision' in ports
    guids = {b['relation'][0]['guid_target'] for b in exe['binding'].values()
             if b['id_port'] in ('prt_draft_design_decision.decision', 'prt_review_design_decision.decision')}
    assert len(guids) == 1                                 # revised in place

    assert clean(repo) == []
    c = next(cc_public.load.git.iter_commit(repo, 1))
    assert c.document['title'].startswith('Run wf_design_decision_from_schema')
    assert [e['id_relation'] for e in c.document['relation']] == ['r_results_from']
    assert git(repo, 'status', '--porcelain') == ''


def test_guard_declines_and_run_stops_and_restores(repo):
    deploy(repo, judge = 'guards', commit = 'run')
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'wf_design_decision_from_schema',
                                   'edge.draft_to_review.guard', value = 'met')
    git(repo, 'add', '-A'); git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'guard')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('unmet'))
    assert r['stopped'] and 'review.input.draft' in r['stopped']
    assert r['node'][0]['declined'] == ['review.input.draft']
    assert git(repo, 'status', '--porcelain') == ''        # everything put back
    assert not (repo / 'ddr' / 'ddr_identity_trait.yaml').exists()


def test_critical_stops_and_restores(repo):
    deploy(repo, judge = 'never', commit = 'never')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted({'title': ''}), None)
    assert r['stopped'] and 'critical' in r['stopped']
    assert git(repo, 'status', '--porcelain') == ''


def test_refuses_dirty_tree_when_committing(repo):
    deploy(repo, commit = 'run')
    (repo / 'junk.txt').write_text('x')
    with pytest.raises(cc_public.workflow.run.Stop):
        cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge())


def test_missing_bind_is_refused(repo):
    with pytest.raises(cc_public.workflow.run.Stop):
        cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', {},
                                   Scripted(), Judge(), is_dry = True)


def test_a_line_field_is_collapsed_and_markup_is_forbidden(repo):
    import cc_public.workflow.generate
    deploy(repo, judge = 'always', commit = 'never')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted({'title': 'A title: it\ncame back\nas three lines'}),
                                   Judge('met'))
    assert r['stopped'] is None
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    assert doc['title'] == 'A title: it came back as three lines'
    text = cc_public.workflow.generate.instruction('Do the thing.', True)
    assert 'no markdown' in text and 'slug' in text
    assert cc_public.workflow.generate.instruction('x', False).count('slug') == 0


def test_two_edges_joining_the_same_ports_are_a_fault(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'wf_design_decision_from_schema', 'edge.again',
                                   value = {'from': 'draft.output.decision',
                                            'to':   'review.input.draft'})
    assert any('same two ports' in m for m in clean(repo))


def test_back_edge_fires_and_the_draft_revises_its_prior_in_place(repo):
    deploy(repo, judge = 'always', commit = 'run', budget = 3)
    gen = Scripted()
    # draft pass 1 met (5 evals), review pass 1 unmet (5 evals), then met
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   gen, Judge(['met'] * 5 + ['unmet'] * 5))
    assert r['stopped'] is None
    assert [(e['node'], e['pass']) for e in r['node']] == \
           [('draft', 1), ('review', 1), ('draft', 2), ('review', 2)]
    (d1, r1, d2, r2) = r['node']
    assert d1['made'] == ['ddr_identity_trait'] and d1['revised'] == []
    assert r1['back'] == ['draft', 'draft']
    assert d2['made'] == [] and d2['revised'] == ['ddr_identity_trait']
    assert gen.calls[2][0] == ['guide', 'judgement', 'prior', 'subject'] and gen.calls[2][2] is False
    assert r1['fired'] == ['draft.input.prior', 'draft.input.judgement'] or \
           r1['fired'] == ['draft.input.judgement', 'draft.input.prior']
    assert sorted(r2['declined']) == ['draft.input.judgement', 'draft.input.prior'] and r2['back'] == []
    assert len(list((repo / 'ddr').glob('ddr_identity_trait*.yaml'))) == 1
    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert sorted({b['pass'] for b in exe['binding'].values()}) == [1, 2]
    # the review port's judgement is on its binding, and the draft's judgement input binds that binding
    rev1 = exe['binding']['review_output_decision_1']
    assert {j['verdict'] for j in rev1['judgement']} == {'unmet'}
    assert all(j['reason'].strip() == 'scripted' for j in rev1['judgement'])
    jdg2 = exe['binding']['draft_input_judgement_2']
    assert jdg2['relation'][0]['id_target'] == rev1['id_self']
    assert clean(repo) == []


def test_back_edge_is_exhausted_when_the_budget_is_spent(repo):
    deploy(repo, judge = 'always', commit = 'never', budget = 1)
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge(['met'] * 5 + ['unmet'] * 5))
    assert r['stopped'] is None
    assert [e['node'] for e in r['node']] == ['draft', 'review']
    assert sorted(r['node'][1]['exhausted']) == ['draft.input.judgement', 'draft.input.prior']
    assert r['node'][1]['fired'] == []
