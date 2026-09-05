"""
---

id_self:                pym_test.test_command
guid_self:              pym_cefd0724439d4c87938e373c5da841fe
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Command tests
brief:                  |
                        The commands that harden editing: unlink,
                        accept, and new with its fields.
description:            |
                        Copies the tree, evidence included, and
                        exercises each command through its library
                        function and through the command line: an edge
                        removed by name, an acceptance refused for
                        what it lacks, and an item made whole in one
                        command.
relation:               []

...
"""


import pathlib
import shutil

import click.testing
import pytest

import cc_public.check
import cc_public.cli.command
import cc_public.edit.accept
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.tree
import cc_public.evidence
import cc_public.load


ROOT = pathlib.Path(__file__).resolve().parent.parent
KEEP = ('ddr', 'schema', 'register', 'eval', 'workflow', 'requirement', 'need',
        'evidence', 'src', 'pyproject.toml')


@pytest.fixture
def repo(tmp_path):
    for name in KEEP:
        src = ROOT / name
        (shutil.copytree if src.is_dir() else shutil.copy)(src, tmp_path / name)
    return tmp_path


def run(*args):
    return click.testing.CliRunner().invoke(cc_public.cli.command.main, list(args))


def clean(root):
    report = cc_public.check.check(list_path = [root])['report']
    return [(c['id_check'], n['message']) for c in report['check']
            for n in c['nonconformity'] if n['severity'] == 'critical']


def test_unlink_removes_an_edge_and_refuses_one_that_is_not_there(repo):
    tree = cc_public.edit.tree.Tree([repo])
    cc_public.edit.link.link(tree, 'ddr_fail_closed', 'r_decides', 'pym_cc_public.path')
    (source, target) = cc_public.edit.link.unlink(tree, 'ddr_fail_closed', 'r_decides',
                                                  'pym_cc_public.path')
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_fail_closed.yaml')
    assert 'pym_cc_public.path' not in [e['id_target'] for e in doc['relation']]
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.link.unlink(tree, 'ddr_fail_closed', 'r_decides', 'pym_cc_public.path')

    # Every edge gone leaves an empty list the printer accepts.
    n = len(doc['relation'])
    for edge in list(doc['relation']):
        cc_public.edit.link.unlink(tree, 'ddr_fail_closed', edge['id_relation'], edge['id_target'])
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_fail_closed.yaml')
    assert doc['relation'] == [] and n > 0
    assert clean(repo) == []
    out = run('unlink', '--root', str(repo), 'need_runs_bounded', 'r_decides', 'sch_need')
    assert out.exit_code == 2 and 'nothing to unlink' in out.output


def test_accept_is_the_only_path_and_refuses_what_lacks(repo):
    tree = cc_public.edit.tree.Tree([repo])
    req  = 'req_committer_writes_record'

    # Accepted already, and not a requirement.
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.accept.accept(tree, req)
    with pytest.raises(cc_public.edit.tree.ErrorItem):
        cc_public.edit.accept.accept(tree, 'need_runs_bounded')

    # Proposed again: with its attestation in the copy, it is accepted.
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    assert cc_public.edit.accept.accept(tree, req).id_self == req
    assert cc_public.load.from_file(repo / 'requirement' / (req + '.yaml'))['status'] == 'accepted'

    # Without evidence it is refused and stays proposed; the refusal says why.
    cc_public.edit.field.set_field(tree, req, 'status', value = 'proposed')
    (repo / 'evidence' / 'evd_attestation.yaml').unlink()
    tree = cc_public.edit.tree.Tree([repo])
    with pytest.raises(cc_public.edit.tree.ErrorItem) as caught:
        cc_public.edit.accept.accept(tree, req)
    assert 'no evidence' in str(caught.value)
    assert cc_public.load.from_file(repo / 'requirement' / (req + '.yaml'))['status'] == 'proposed'

    # A test-verified requirement whose test is not in this copy lacks its verifier.
    cc_public.edit.field.set_field(tree, 'req_printer_idempotent', 'status', value = 'proposed')
    out = run('accept', '--root', str(repo), 'req_printer_idempotent')
    assert out.exit_code == 2 and 'no test names it' in out.output


def test_new_takes_its_fields_and_edges_in_one_command(repo):
    out = run('new', '--root', str(repo), 't_ddr', 'ddr_made_whole',
              '--set', 'title=Made whole',
              '--prose', 'brief=One command.',
              '--prose', 'context=There was a failing state.\n\nNow there is not.',
              '--prose', 'decision=new takes fields.', '--prose', 'rationale=Fewer steps.',
              '--prose', 'alternative=Five commands.', '--prose', 'consequence=None fail.',
              '--link', 'r_decides', 'pym_cc_public.edit.new')
    assert out.exit_code == 0, out.output
    doc = cc_public.load.from_file(repo / 'ddr' / 'ddr_made_whole.yaml')
    assert doc['title'] == 'Made whole' and doc['context'].count('\n\n') == 1
    assert [e['id_target'] for e in doc['relation']] == ['pym_cc_public.edit.new']
    assert clean(repo) == []
    out = run('new', '--root', str(repo), 't_ddr', 'ddr_half', '--set', 'title')
    assert out.exit_code == 2 and 'PATH=VALUE' in out.output
