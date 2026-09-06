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
relation:               []

...
"""


import pytest

import cc_public.check
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.control
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.evidence
import cc_public.load
import cc_public.load.git
import cc_public.workflow.produce
import cc_public.workflow.run
from conftest import git



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
        self.prompts = []

    def produce(self, prompt, map_input, list_field, want_slug):
        self.calls.append((sorted(map_input), list(list_field), want_slug))
        self.prompts.append(prompt)
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






def deploy(repo, **kw):
    tree = cc_public.edit.tree.Tree([repo])
    kw.setdefault('admit_unmeasured', True)     # the scripted judge is measured nowhere
    for (k, v) in kw.items():
        cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local', k, value = v)
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'deploy')


def clean(root):
    rep = cc_public.check.check(list_path = [root])['report']
    return [n['message'] for c in rep['check'] for n in c['nonconformity']
            if n['severity'] == 'critical']


BIND = {'draft.input.subject': 'sch_identity',
        'draft.input.guide':   'reg_writing_style_rule'}

EVALS = ['evl_decision_decides', 'evl_decision_stated', 'evl_plain_text',
         'evl_prose_matches_structure', 'evl_records_the_decision']


def test_dry_run_plans_and_writes_nothing(repo):
    before = git(repo, 'status', '--porcelain')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   None, None, is_dry = True)
    assert r['order'] == ['draft']
    assert r['node'][0]['output'] == {'decision': 'revises prior'}
    assert r['execution'] is None
    assert git(repo, 'status', '--porcelain') == before


def test_run_makes_judges_and_commits(repo):
    deploy(repo, judge = 'always', commit = 'run')
    gen = Scripted()
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   gen, Judge('met'))
    assert r['stopped'] is None
    (draft,) = r['node']
    assert draft['made'] == ['ddr_identity_trait'] and draft['revised'] == []
    assert sorted(draft['verdict']['decision']) == [(e, 'met') for e in EVALS]
    assert sorted(draft['declined']) == ['draft.input.judgement', 'draft.input.prior']

    # the generator was asked exactly the empty prose fields, with the input by port
    assert gen.calls[0] == (['guide', 'subject'], ['title', 'brief', 'context', 'decision',
                                          'rationale', 'alternative', 'consequence'], True)

    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    assert doc['title'] == 'Identity trait'
    assert [(r['id_relation'], r['id_target']) for r in doc['relation']] == \
           [('r_decides', 'sch_identity')]                 # the port says decides: subject

    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert exe['id_self'].startswith('exe_') and len(exe['binding']) == 3
    assert exe['outcome'] == 'completed' and r['outcome'] == 'completed'
    assert {b['id_port'] for b in exe['binding'].values()} == {
        'prt_draft_design_decision.subject', 'prt_draft_design_decision.guide',
        'prt_draft_design_decision.decision'}

    assert clean(repo) == []
    c = next(cc_public.load.git.iter_commit(repo, 1))
    assert c.document['title'].startswith('Run wf_design_decision_from_schema')
    assert [e['id_relation'] for e in c.document['relation']] == ['r_results_from']
    assert git(repo, 'status', '--porcelain') == ''


def test_guards_mode_judges_only_a_gated_port_and_loops_to_the_budget(repo):
    deploy(repo, judge = 'guards', commit = 'never', budget = 2)
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('unmet'))
    assert r['stopped'] is None
    assert [(e['node'], e['pass']) for e in r['node']] == [('draft', 1), ('draft', 2)]
    assert r['node'][0]['back'] == ['draft', 'draft']
    assert sorted(r['node'][1]['exhausted']) == ['draft.input.judgement', 'draft.input.prior']
    assert (repo / 'ddr' / 'ddr_identity_trait.yaml').exists()


def test_critical_stops_and_restores(repo):
    deploy(repo, judge = 'always', commit = 'never')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted({'title': ''}), Judge('met'))
    assert r['stopped'] and 'critical' in r['stopped']
    assert git(repo, 'status', '--porcelain') == ''
    assert not (repo / 'ddr' / 'ddr_identity_trait.yaml').exists()


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
    cc_public.edit.field.set_field(tree, 'wf_design_decision_from_schema', 'edge_back.again',
                                   value = {'from': 'draft.output.decision',
                                            'to':   'draft.input.prior'})
    assert any('same two ports' in m for m in clean(repo))


def test_back_edge_fires_and_the_draft_revises_its_prior_in_place(repo):
    deploy(repo, judge = 'always', commit = 'run', budget = 3)
    gen = Scripted()
    # pass 1 unmet on every eval, pass 2 met
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   gen, Judge(['unmet'] * 5))
    assert r['stopped'] is None
    assert [(e['node'], e['pass']) for e in r['node']] == [('draft', 1), ('draft', 2)]
    (d1, d2) = r['node']
    assert d1['made'] == ['ddr_identity_trait'] and d1['revised'] == []
    assert sorted(d1['fired']) == ['draft.input.judgement', 'draft.input.prior']
    assert d1['back'] == ['draft', 'draft']
    assert d2['made'] == [] and d2['revised'] == ['ddr_identity_trait']
    assert gen.calls[1][0] == ['guide', 'judgement', 'prior', 'subject'] and gen.calls[1][2] is False
    assert sorted(d2['declined']) == ['draft.input.judgement', 'draft.input.prior'] and d2['back'] == []
    assert len(list((repo / 'ddr').glob('ddr_identity_trait*.yaml'))) == 1
    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert sorted({b['pass'] for b in exe['binding'].values()}) == [1, 2]
    # the judgement is on the binding it judged, and the next pass's judgement input binds that binding
    out1 = exe['binding']['draft_output_decision_1']
    assert {j['verdict'] for j in out1['judgement']} == {'unmet'}
    assert all(j['reason'].strip() == 'scripted' for j in out1['judgement'])
    assert all(j['criterion'].strip() for j in out1['judgement'])   # the rule travels too
    jdg2 = exe['binding']['draft_input_judgement_2']
    assert jdg2['relation'][0]['id_target'] == out1['id_self']
    assert clean(repo) == []


def test_back_edge_is_exhausted_when_the_budget_is_spent(repo):
    """
    ---

    id_self:                pyf_test.test_run.test_back_edge_is_exhausted_when_the_budget_is_spent
    guid_self:              pyf_f940333d706a4646904867a7cca8ab74
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A back edge is exhausted when the budget is spent
    brief:                  |
                            A back edge is exhausted when the budget is
                            spent.
    description:            |
                            Runs the one node workflow with a budget of
                            one and a judge that always answers unmet, and
                            asserts the node ran once, both back edges
                            were reported exhausted, nothing fired, and
                            the execution says it ended exhausted.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_executor_honours_budget
        guid_target:        req_a1428b3ae8ec4b5687e58895592accad

    ...
    """

    deploy(repo, judge = 'always', commit = 'never', budget = 1)
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge(['unmet'] * 5))
    assert r['stopped'] is None
    assert [e['node'] for e in r['node']] == ['draft']
    assert sorted(r['node'][0]['exhausted']) == ['draft.input.judgement', 'draft.input.prior']
    assert r['node'][0]['fired'] == []
    assert r['outcome'] == 'exhausted'
    exe = cc_public.load.from_file(cc_public.edit.tree.Tree([repo]).resolve(r['execution']).filepath)
    assert exe['outcome'] == 'exhausted'


def test_a_bounded_field_is_told_its_bound_and_cut_to_it_if_overrun(repo):
    deploy(repo, judge = 'always', commit = 'never')
    gen = Scripted({'title': 'A title that goes on and on, well past the eighty characters the schema allows for a title'})
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   gen, Judge('met'))
    assert r['stopped'] is None
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    assert len(doc['title']) <= 80 and doc['title'].endswith('the schema allows')
    assert 'title is one line of at most 80 characters' in gen.prompts[0]


def test_a_cut_line_drops_a_dangling_word_and_a_slug_is_normalised():
    line = cc_public.workflow.produce._line
    assert line('Define port schema with identity, prompts, and relations', 47) == \
           'Define port schema with identity, prompts'
    assert line('short', 80) == 'short'
    slug = cc_public.workflow.produce._slug
    assert slug('Port Schema: Design-Decision!', 'ddr') == 'port_schema_design_decision'
    assert slug('ddr_port_schema', 'ddr') == 'port_schema'
    assert slug('', 'ddr') == ''


def test_a_taken_slug_keeps_its_name_and_adds_a_tag(repo):
    deploy(repo, judge = 'always', commit = 'never')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted({'slug': 'glossary'}), Judge('met'))
    made = r['node'][0]['made'][0]
    assert made.startswith('ddr_glossary_') and len(made) == len('ddr_glossary_') + 6
    assert r['node'][0]['note'] and 'is taken' in r['node'][0]['note'][0]


def test_a_port_names_its_fields_and_fills_a_table_and_a_record_is_proposed(repo):
    deploy(repo, judge = 'always', commit = 'never')
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'prt_draft_design_decision.decision', 'field',
        value = ['title', 'brief', 'context', 'decision', 'rationale', 'alternative', 'consequence', 'assumption'])
    gen = Scripted({'assumption': '[{"key": "guids_hold", "statement": "A guid is never reused.", '
                                  '"evidence": "Minted from 128 random bits; ddr_identity_field_naming."}]'})
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND, gen, Judge('met'))
    assert r['stopped'] is None
    assert 'assumption is a JSON list' in gen.prompts[0]
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    asm = doc['assumption']['guids_hold']
    assert asm['id_self'] == 'asm_identity_trait.guids_hold' and asm['statement'].startswith('A guid')
    assert doc['status'] == 'proposed'
    assert clean(repo) == []


def test_a_challenging_node_needs_a_second_model_and_runs_on_it(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'wf_design_decision_from_schema', 'node.draft.challenger', value = True)
    deploy(repo, judge = 'always', commit = 'never')
    with pytest.raises(cc_public.workflow.run.Stop):
        cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND, Scripted(), Judge('met'))
    deploy(repo, model_challenge = 'openai/gpt-4.1-mini')
    with pytest.raises(cc_public.workflow.run.Stop):
        cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND, Scripted(), Judge('met'))
    deploy(repo, model_challenge = 'other/model')
    (a, b) = (Scripted(), Scripted())
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND, a, Judge('met'),
                                   generator_challenge = b)
    assert r['stopped'] is None and b.calls and not a.calls


def test_budget_follows_the_priority_of_what_is_bound_and_a_need_names_its_entity(repo):
    import cc_public.need
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'need_runs_bounded', 'priority', value = 'high')
    cc_public.edit.field.set_field(tree, 'need_runs_bounded', 'entity', value = 'Executor')
    dep = {'budget': 1, 'budget_by_priority': {'high': 3, 'low': 1}}
    assert cc_public.workflow.run._budget(tree, dep, ['need_runs_bounded', 'sch_identity']) == 3
    assert cc_public.workflow.run._budget(tree, {'budget': 2}, ['need_runs_bounded']) == 2
    doc = cc_public.load.from_file(repo / 'need' / 'need_runs_bounded.yaml')
    assert 'from the Executor, in order to' in cc_public.need.statement(doc)


def test_a_table_is_updated_in_place_on_a_later_pass(repo):
    deploy(repo, judge = 'always', commit = 'never', budget = 3)
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'prt_draft_design_decision.decision', 'field',
        value = ['title', 'brief', 'context', 'decision', 'rationale', 'alternative', 'consequence', 'assumption'])
    first  = '[{"key": "a", "statement": "A.", "evidence": "E1."}, {"key": "b", "statement": "B.", "evidence": "E2."}]'
    second = '[{"key": "a", "statement": "A revised.", "evidence": "E1."}, {"key": "c", "statement": "C.", "evidence": "E3."}]'
    class Gen(Scripted):
        def produce(self, prompt, map_input, list_field, want_slug):
            out = super().produce(prompt, map_input, list_field, want_slug)
            out['assumption'] = second if 'prior' in map_input else first
            return out
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND, Gen(), Judge(['unmet'] * 5))
    assert [e['pass'] for e in r['node']] == [1, 2] and not r['node'][1]['note']
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_identity_trait.yaml')
    assert list(doc['assumption']) == ['a', 'c']
    assert doc['assumption']['a']['statement'].startswith('A revised')
    assert clean(repo) == []


def test_a_check_that_cannot_run_stops_the_run_and_restores(repo, monkeypatch):
    class Raising:
        ID_CHECK = 'raising'
        TITLE    = 'A check that raises'
        NOUN     = 'thing'

        @staticmethod
        def check(_context):
            raise RuntimeError('the check fell over')

    deploy(repo, judge = 'always', commit = 'never')
    monkeypatch.setattr(cc_public.check, 'CHECK', (*cc_public.check.CHECK, Raising))
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('met'))
    assert r['stopped'] and 'did not complete' in r['stopped']
    assert not (repo / 'ddr' / 'ddr_identity_trait.yaml').exists()
    assert git(repo, 'status', '--porcelain') == ''


def test_a_deployment_cannot_confirm_over_an_even_count(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'confirm', value = 2)
    assert any('multipleOf' in m or 'not' in m for m in clean(repo))
    cc_public.edit.field.set_field(tree, 'dep_design_decision_from_schema_local',
                                   'confirm', value = 3)
    assert clean(repo) == []


def test_a_declined_edge_withdraws_its_delivery_and_the_unfed_node_is_skipped(repo):
    # Guard the forward edge of the decomposition workflow, and judge the
    # proposal met on the first pass and unmet on the second: the
    # challenger must not consume the first pass's proposal on the second.
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'wf_decomposition_from_need',
                                   'edge.propose_to_challenge.guard', value = 'met')
    cc_public.edit.field.set_field(tree, 'dep_decomposition_local', 'commit', value = 'never')
    cc_public.edit.field.set_field(tree, 'dep_decomposition_local', 'judge', value = 'guards')
    cc_public.edit.field.set_field(tree, 'dep_decomposition_local', 'budget', value = 2)
    cc_public.edit.field.set_field(tree, 'dep_decomposition_local', 'admit_unmeasured', value = True)
    cc_public.edit.field.set_field(tree, 'dep_decomposition_local', 'budget_by_priority',
                                   value = {'high': 2, 'medium': 2, 'low': 2})
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'guarded')

    class Sequence(Judge):
        """met on the proposal, unmet on the challenge, then unmet on the proposal."""
        def __init__(self):
            super().__init__('met')
            self.by_port = {}
        def run(self, task):
            n       = self.by_port[task.id_eval] = self.by_port.get(task.id_eval, 0) + 1
            verdict = 'unmet' if (n > 1 or 'challenge' in task.id_eval) else 'met'
            return cc_public.eval.runner.Verdict(task.id_eval, task.id_subject,
                                                 verdict, 'scripted', self.id_model)

    r = cc_public.workflow.run.run(repo, 'wf_decomposition_from_need',
                                   'dep_decomposition_local',
                                   {'propose.input.need':    'need_runs_bounded',
                                    'propose.input.framing': 'frame_dependency',
                                    'propose.input.guide':   'reg_writing_style_rule',
                                    'challenge.input.need':  'need_runs_bounded',
                                    'challenge.input.guide': 'reg_writing_style_rule'},
                                   Scripted(), Sequence(),
                                   generator_challenge = Scripted())
    assert r['stopped'] is None
    passes = [(e['node'], e['pass'], bool(e['skipped'])) for e in r['node']]
    assert passes == [('propose', 1, False), ('challenge', 1, False),
                      ('propose', 2, False), ('challenge', 2, True)]
    assert r['node'][2]['declined'] == ['challenge.input.proposal']
    assert 'did not fire' in r['node'][3]['skipped']
    assert 'skipped' in cc_public.workflow.run._summary(r['node'])

    # The port says derives: need, so the proposal derives from the need.
    made = cc_public.load.from_file(cc_public.edit.tree.Tree([repo]).resolve(r['node'][0]['made'][0]).filepath)
    assert ('r_is_derived_from', 'need_runs_bounded') in \
           [(e['id_relation'], e['id_target']) for e in made['relation']]


def test_two_forward_edges_into_one_input_are_a_fault(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'wf_decomposition_from_need', 'edge.again',
                                   value = {'from': 'challenge.output.decision',
                                            'to':   'challenge.input.proposal'})
    assert any('one forward edge' in m for m in clean(repo))


def test_a_guard_is_refused_to_a_judge_the_eval_was_not_measured_for(repo):
    deploy(repo, judge = 'guards', commit = 'never', admit_unmeasured = False)
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('met'))
    assert r['stopped'] and 'no current confidence for judge' in r['stopped']
    assert git(repo, 'status', '--porcelain') == ''

    # Measured for this judge, and current: admitted.
    tree = cc_public.edit.tree.Tree([repo])
    for ev in EVALS:
        rows = [{'origin': 'all', 'cases': 1, 'samples': 3, 'false_positive': 0.0,
                 'false_negative': 0.0, 'unanimous': 1.0}]
        cc_public.eval.measure.record(tree, ev, rows, 'judge')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'measured')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('met'))
    assert r['stopped'] is None

    # The criterion changes: the confidence is stale, and the guard is refused again.
    cc_public.edit.field.set_field(tree, EVALS[0], 'criterion', prose = 'Something else.\n')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'changed')
    r = cc_public.workflow.run.run(repo, 'wf_design_decision_from_schema',
                                   'dep_design_decision_from_schema_local', BIND,
                                   Scripted(), Judge('met'))
    assert r['stopped'] and EVALS[0] in r['stopped']


def test_a_component_in_code_runs_its_function_once_and_revises_its_input(repo):
    """
    The accept workflow's one node is a function: it is called with the
    bound ids, no prompt is asked, and the requirement leaves accepted.

    """
    tree = cc_public.edit.tree.Tree([repo])
    req  = 'req_committer_writes_record'
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    cc_public.evidence.attest(tree, req, 'passed', 'a test', note = 'Attested here.')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'proposed')

    gen = Scripted()
    r   = cc_public.workflow.run.run(repo, 'wf_accept_requirement', 'dep_accept_local',
                                     {'accept.input.requirement': req}, gen, Judge())
    assert r['stopped'] is None, r['stopped']
    (node,) = r['node']
    assert node['revised'] == [req] and node['made'] == []
    assert gen.calls == []
    assert cc_public.load.from_file(repo / 'requirement' / (req + '.yaml'))['status'] == 'accepted'

    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert {b['id_port'] for b in exe['binding'].values()} == {
        'prt_accept_requirement.requirement', 'prt_accept_requirement.accepted'}
    assert clean(repo) == []


def test_a_function_that_refuses_stops_the_run_and_restores(repo):
    """
    Accepting what is accepted already is refused by the edit tier; the
    refusal stops the run and the tree is put back.

    """
    r = cc_public.workflow.run.run(repo, 'wf_accept_requirement', 'dep_accept_local',
                                   {'accept.input.requirement': 'req_committer_writes_record'},
                                   Scripted(), Judge())
    assert r['stopped'] and 'accepted already' in r['stopped']
    assert git(repo, 'status', '--porcelain') == ''


def test_a_component_in_code_names_a_function_and_carries_no_prompt(repo):
    """
    The workflow check reports an implementation that is not a
    function, and a prompt beside an implementation.

    """
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.link.unlink(tree, 'cmp_accept_requirement', 'r_is_implemented_by',
                               'pyf_cc_public.workflow.component.accept')
    cc_public.edit.link.link(tree, 'cmp_accept_requirement', 'r_is_implemented_by',
                             'pym_cc_public.workflow.component')
    cc_public.edit.field.set_field(tree, 'prt_accept_requirement.accepted', 'prompt',
                                   prose = 'Accept it.')
    faults = clean(repo)
    assert any('is not a function' in f for f in faults), faults
    assert any('not both' in f for f in faults), faults


def perform(repo, req, body = '    if 1 + 1 != 2:\n        raise AssertionError(\'no\')\n'):
    """
    Do what the implement node's brief asks, as a performer would: put
    a function into the tree, make it an item, and link it as the
    requirement's verifier.

    """
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.new.new(tree, 't_python_module', 'pym_cc_public.probe', tree.defaults())
    for (field, text) in (('title', 'Probe'), ('brief', 'A stand-in.'),
                          ('description', 'Holds a stand-in for a test.')):
        cc_public.edit.field.set_field(tree, 'pym_cc_public.probe', field, value = text)
    path = repo / 'src' / 'cc_public' / 'probe.py'
    path.write_text(path.read_text() + '\n\ndef test_probe():\n    """\n    Proves it.\n\n    """\n'
                    + body)
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.new.new(tree, 't_python_function', 'pyf_cc_public.probe.test_probe',
                           tree.defaults())
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.probe.test_probe', 'title',
                                   value = 'Probe')
    cc_public.edit.field.set_field(tree, 'pyf_cc_public.probe.test_probe', 'description',
                                   prose = 'A stand-in for a test.')
    cc_public.edit.link.link(tree, 'pyf_cc_public.probe.test_probe', 'r_verifies', req)


def test_an_agent_node_parks_the_run_and_resume_reads_its_outputs_from_the_tree(repo):
    """
    The implement workflow parks at its agent node with a brief and its
    state on the record; resumed too soon it stops and stays waiting;
    once the tree holds the test the brief asked for, resume finds it,
    accepts the requirement and closes the record.

    """
    tree = cc_public.edit.tree.Tree([repo])
    req  = 'req_committer_writes_record'
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'proposed')
    bind = {'implement.input.requirement': req}

    r = cc_public.workflow.run.run(repo, 'wf_implement_requirement', 'dep_implement_local',
                                   bind, Scripted(), Judge())
    assert r['stopped'] is None and r['outcome'] == 'waiting'
    (entry,) = r['node']
    assert entry['node'] == 'implement' and 'cctool resume' in entry['waiting']
    assert git(repo, 'status', '--porcelain') == ''            # the park is committed
    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert exe['outcome'] == 'waiting' and exe['waiting']['node'] == 'implement'
    assert exe['state']['queue'] == ['verify', 'accept']
    assert exe['state']['pass'] == {'implement': 1, 'verify': 0, 'accept': 0}
    assert [(b['port'], b['id_item']) for b in exe['state']['bound']] == \
           [('implement.input.requirement', req)]

    # Too soon: nothing verifies the requirement, so the run stops and
    # the record is as it was.
    r2 = cc_public.workflow.run.resume(repo, r['execution'], Scripted(), Judge())
    assert r2['stopped'] and 'finds nothing' in r2['stopped']
    assert cc_public.load.from_file(tree.resolve(r['execution']).filepath)['outcome'] == 'waiting'
    assert git(repo, 'status', '--porcelain') == ''

    perform(repo, req)
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'performed')

    r3 = cc_public.workflow.run.resume(repo, r['execution'], Scripted(), Judge())
    assert r3['stopped'] is None, r3['stopped']
    assert [e['node'] for e in r3['node']] == ['implement', 'verify', 'accept']
    assert r3['node'][1]['revised'] == [req]
    evidence = cc_public.load.from_file(repo / 'evidence' / 'evd_pytest.yaml')
    (row,) = [c for c in evidence['case'].values() if c['id_requirement'] == req]
    assert row['outcome'] == 'passed' and row['id_case'] == 'pyf_cc_public.probe.test_probe'
    assert r3['node'][0]['revised'] == [req]
    assert r3['node'][0]['made'] == ['pyf_cc_public.probe.test_probe']
    assert r3['node'][0]['fired'] == ['verify.input.requirement']
    assert r3['node'][1]['fired'] == ['accept.input.requirement']
    assert r3['outcome'] == 'completed'
    assert cc_public.load.from_file(repo / 'requirement' / (req + '.yaml'))['status'] == 'accepted'
    exe = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert exe['outcome'] == 'completed' and 'waiting' not in exe and 'state' not in exe
    assert git(repo, 'status', '--porcelain') == ''
    assert clean(repo) == []

    with pytest.raises(cc_public.workflow.run.Stop):     # not waiting any more
        cc_public.workflow.run.resume(repo, r['execution'], Scripted(), Judge())


def test_each_performer_is_held_to_its_form(repo):
    """
    The workflow check reports a model's output that says how it is
    found, an agent's output that says neither, and a prompt missing
    where a performer is asked one.

    """
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.field.set_field(tree, 'prt_draft_design_decision.decision', 'found',
                                   value = {'port': 'subject', 'relation': 'r_decides',
                                            'direction': 'out'})
    cc_public.edit.field.unset_field(tree, 'prt_implement_requirement.implemented', 'revises')
    cc_public.edit.field.unset_field(tree, 'prt_implement_requirement.test', 'prompt')
    faults = clean(repo)
    assert any("only an agent's output does" in f for f in faults), faults
    assert any('says neither what it revises nor how' in f for f in faults), faults
    assert any('test carries no prompt' in f for f in faults), faults


def test_a_failing_test_stops_the_run_at_verify_and_restores_the_evidence(repo):
    """
    The verify node runs the requirement's tests; one that fails stops
    the run, which says which, leaves the record waiting and puts the
    evidence back as it was.

    """
    tree = cc_public.edit.tree.Tree([repo])
    req  = 'req_committer_writes_record'
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'proposed')
    r = cc_public.workflow.run.run(repo, 'wf_implement_requirement', 'dep_implement_local',
                                   {'implement.input.requirement': req}, Scripted(), Judge())
    assert r['outcome'] == 'waiting'
    perform(repo, req, body = '    raise AssertionError(\'no\')\n')
    git(repo, 'add', '-A')
    git(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'performed badly')
    before = (repo / 'evidence' / 'evd_pytest.yaml').read_bytes()

    r2 = cc_public.workflow.run.resume(repo, r['execution'], Scripted(), Judge())
    assert r2['stopped'] and 'did not pass' in r2['stopped'] and 'test_probe failed' in r2['stopped']
    assert (repo / 'evidence' / 'evd_pytest.yaml').read_bytes() == before
    assert git(repo, 'status', '--porcelain') == ''
    tree = cc_public.edit.tree.Tree([repo])
    exe  = cc_public.load.from_file(tree.resolve(r['execution']).filepath)
    assert exe['outcome'] == 'waiting'
    assert cc_public.load.from_file(repo / 'requirement' / (req + '.yaml'))['status'] == 'proposed'
