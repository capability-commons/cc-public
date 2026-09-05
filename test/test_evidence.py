"""
---

id_self:                pym_test.test_evidence
guid_self:              pym_4e8ebd95212045aa9834b06a834dbf20
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Evidence tests
brief:                  |
                        Evidence is observed, stamped with what it
                        observed, and judged current; an attestation
                        stands for inspection.
description:            |
                        Folds instances into outcomes, writes evidence
                        from a scripted pytest session into a copied
                        tree with its own repository, asserts the
                        evidence check reports absence, failure and
                        staleness with the right severities, shows
                        what changes the digest and what does not, and
                        records an attestation.
relation:               []

...
"""


import shutil
import subprocess

import pytest

import cc_public.check
import cc_public.check.evidence
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.evidence
import cc_public.load
from conftest import DEFAULTS, clean


def test_evidence_is_observed_stamped_and_judged_current(tree, tmp_path):
    shutil.rmtree(tmp_path / 'evidence')          # this copy observes from nothing
    tree = cc_public.edit.tree.Tree([tmp_path])
    subprocess.run(['git', '-C', str(tmp_path), 'init', '-q'], check = True)
    (tmp_path / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright 2026 William Payne"\n'
        'license = "Apache-2.0"\nid_mark = "mark_public"\n')
    for args in (['config', 'user.name', 'T'], ['config', 'user.email', 't@t'],
                 ['add', '-A'], ['-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'start']):
        subprocess.run(['git', '-C', str(tmp_path), *args], check = True)

    # Outcomes over instances: any error outranks, then failure, then a hole.
    assert cc_public.evidence.outcome_of([]) == ('not_run', 0, 0)
    assert cc_public.evidence.outcome_of(['passed', 'passed']) == ('passed', 2, 2)
    assert cc_public.evidence.outcome_of(['passed', 'skipped']) == ('skipped', 2, 1)
    assert cc_public.evidence.outcome_of(['failed', 'passed', 'error']) == ('error', 3, 1)
    assert cc_public.evidence.outcome_of(['failed', 'passed']) == ('failed', 2, 1)

    # A requirement accepted with a test verifier and no evidence lacks it,
    # critically in a closed world; then the test observes and it is current.
    req  = 'req_printer_idempotent'
    case = 'pyf_test.test_layout.test_printer_preserves_and_is_fixpoint'
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    cc_public.edit.new.new(tree, 't_python_module', 'pym_test.test_layout', DEFAULTS, tmp_path / 'test')
    for (f, v) in (('title', 'Layout tests'), ('brief', 'Tests.'), ('description', 'Tests of the printer.')):
        cc_public.edit.field.set_field(tree, 'pym_test.test_layout', f, value = v)
    path = tmp_path / 'test' / 'test_layout.py'
    path.write_text(path.read_text() + '\n\ndef test_printer_preserves_and_is_fixpoint():\n    assert True\n')
    tree.refresh(path)
    cc_public.edit.new.new(tree, 't_python_function', case, DEFAULTS)
    for (f, v) in (('title', 'Fixpoint'), ('brief', 'The printer is a fixpoint.'), ('description', 'Lays out twice.')):
        cc_public.edit.field.set_field(tree, case, f, value = v)
    cc_public.edit.link.link(tree, case, 'r_verifies', req)
    cc_public.edit.field.set_field(tree, req, 'status', value = 'accepted')

    def evidence(is_closed = False, about = req):
        rep = cc_public.check.check(list_path = [tmp_path], is_closed_world = is_closed)['report']
        return [(n['severity'], n['message']) for c in rep['check'] if c['id_check'] == 'evidence'
                for n in c['nonconformity'] if about in n['filepath']]

    assert [s for (s, m) in evidence(True)] == ['critical'] and 'no evidence' in evidence(True)[0][1]
    assert [s for (s, m) in evidence(False)] == ['advisory']

    guid_req  = tree.resolve(req).guid_self
    guid_case = tree.resolve(case).guid_self
    written   = cc_public.evidence.from_pytest(
                    tmp_path, {'test/test_layout.py::test_printer_preserves_and_is_fixpoint[a]': 'passed',
                               'test/test_layout.py::test_printer_preserves_and_is_fixpoint[b]': 'passed',
                               'test/test_layout.py::test_nothing_is_an_item': 'failed'}, '9.1.1')
    assert written == tmp_path / 'evidence' / 'evd_pytest.yaml'
    doc = cc_public.load.from_file(written)
    assert doc['method'] == 'test' and doc['observer'] == 'pytest 9.1.1' and doc['revision'] is not None
    (row,) = doc['case'].values()
    assert (row['guid_case'], row['guid_requirement'], row['outcome'], row['count_collected']) \
           == (guid_case, guid_req, 'passed', 2)
    assert evidence(True) == [] and clean(tmp_path) == []



def test_evidence_goes_stale_with_what_it_observed_and_an_attestation_stands_for_inspection(tree, tmp_path):
    shutil.rmtree(tmp_path / 'evidence')          # this copy observes from nothing
    tree = cc_public.edit.tree.Tree([tmp_path])
    subprocess.run(['git', '-C', str(tmp_path), 'init', '-q'], check = True)
    (tmp_path / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright 2026 William Payne"\n'
        'license = "Apache-2.0"\nid_mark = "mark_public"\n')
    for args in (['config', 'user.name', 'T'], ['config', 'user.email', 't@t'],
                 ['add', '-A'], ['-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'start']):
        subprocess.run(['git', '-C', str(tmp_path), *args], check = True)
    req  = 'req_printer_idempotent'
    case = 'pyf_test.test_layout.test_printer_preserves_and_is_fixpoint'
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    cc_public.edit.new.new(tree, 't_python_module', 'pym_test.test_layout', DEFAULTS, tmp_path / 'test')
    for (f, v) in (('title', 'Layout tests'), ('brief', 'Tests.'), ('description', 'Tests of the printer.')):
        cc_public.edit.field.set_field(tree, 'pym_test.test_layout', f, value = v)
    path = tmp_path / 'test' / 'test_layout.py'
    path.write_text(path.read_text() + '\n\ndef test_printer_preserves_and_is_fixpoint():\n    assert True\n')
    tree.refresh(path)
    cc_public.edit.new.new(tree, 't_python_function', case, DEFAULTS)
    for (f, v) in (('title', 'Fixpoint'), ('brief', 'The printer is a fixpoint.'), ('description', 'Lays out twice.')):
        cc_public.edit.field.set_field(tree, case, f, value = v)
    cc_public.edit.link.link(tree, case, 'r_verifies', req)
    cc_public.edit.field.set_field(tree, req, 'status', value = 'accepted')
    guid_req  = tree.resolve(req).guid_self
    guid_case = tree.resolve(case).guid_self
    cc_public.evidence.from_pytest(tmp_path, {'test/test_layout.py::test_printer_preserves_and_is_fixpoint': 'passed'}, '9.1.1')

    def evidence(is_closed = False, about = req):
        rep = cc_public.check.check(list_path = [tmp_path], is_closed_world = is_closed)['report']
        return [(n['severity'], n['message']) for c in rep['check'] if c['id_check'] == 'evidence'
                for n in c['nonconformity'] if about in n['filepath']]

    assert evidence(True) == []

    # What makes it stale: the requirement, its implementation, the case.
    # What does not: an unrelated file, the evidence itself, a rename.
    before = cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case)
    cc_public.edit.field.set_field(tree, 'need_layout_stable', 'priority', value = 'high')
    (tmp_path / 'README.md').write_text('unrelated\n')
    assert cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case) == before
    cc_public.edit.field.set_field(tree, req, 'success_criteria', prose = 'Tighter.')
    after_req = cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case)
    assert after_req != before
    assert [s for (s, m) in evidence(True)] == ['advisory'] and 'stale' in evidence(True)[0][1]
    # Prose and layout in the implementation stale nothing; code does.
    layout = tmp_path / 'src' / 'cc_public' / 'layout.py'
    layout.write_text(layout.read_text() + '\n# a change\n')
    tree.refresh(layout)
    assert cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case) == after_req
    cc_public.edit.field.set_field(tree, 'pym_cc_public.layout', 'brief', prose = 'Reworded.')
    assert cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case) == after_req
    layout.write_text(layout.read_text() + '\nWIDTH_EXTRA = 1\n')
    tree.refresh(layout)
    after_impl = cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case)
    assert after_impl != after_req
    path.write_text(path.read_text().replace('assert True', 'assert 1'))
    tree.refresh(path)
    assert cc_public.check.evidence.digest(tree.context.map_document, guid_req, guid_case) != after_impl

    # Observed again: current. Observed failing: critical.
    cc_public.evidence.from_pytest(tmp_path, {'test/test_layout.py::test_printer_preserves_and_is_fixpoint': 'passed'}, '9.1.1')
    assert evidence(True) == []
    cc_public.evidence.from_pytest(tmp_path, {'test/test_layout.py::test_printer_preserves_and_is_fixpoint': 'failed'}, '9.1.1')
    assert [s for (s, m) in evidence(True)] == ['critical'] and 'failed, not passed' in evidence(True)[0][1]
    cc_public.evidence.from_pytest(tmp_path, {'test/test_layout.py::test_printer_preserves_and_is_fixpoint': 'passed'}, '9.1.1')
    assert evidence(True) == []


def test_an_attestation_stands_for_inspection_and_refuses_a_test(tree, tmp_path):
    shutil.rmtree(tmp_path / 'evidence')          # this copy observes from nothing
    tree = cc_public.edit.tree.Tree([tmp_path])
    subprocess.run(['git', '-C', str(tmp_path), 'init', '-q'], check = True)
    (tmp_path / 'pyproject.toml').write_text(
        '[tool.cctool.new]\ncopyright = "Copyright 2026 William Payne"\n'
        'license = "Apache-2.0"\nid_mark = "mark_public"\n')

    req = 'req_committer_writes_record'

    def evidence(is_closed = False, about = req):
        rep = cc_public.check.check(list_path = [tmp_path], is_closed_world = is_closed)['report']
        return [(n['severity'], n['message']) for c in rep['check'] if c['id_check'] == 'evidence'
                for n in c['nonconformity'] if about in n['filepath']]

    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.evidence.attest(tree, 'req_printer_idempotent', 'passed', 'a person')
    cc_public.edit.field.set_field(tree, 'req_committer_writes_record', 'status', value = 'accepted')
    assert any('no evidence' in m for (_, m) in evidence(True))
    written = cc_public.evidence.attest(tree, 'req_committer_writes_record', 'passed', 'W. Payne',
                                        note = 'Read three messages in the log.')
    doc = cc_public.load.from_file(written)
    assert doc['method'] == 'inspection'
    (row,) = doc['case'].values()
    assert 'guid_case' not in row and row['observer'] == 'W. Payne' and row['outcome'] == 'passed'
    assert evidence(True) == [] and clean(tmp_path) == []
