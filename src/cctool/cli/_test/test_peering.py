"""
---

id_self:                pym_cctool.cli._test.test_peering
guid_self:              pym_ea150eeac3514018b18c1f75652868c2
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Peer command tests
brief:                  |
                        Tests of the peer commands, as the command
                        line presents them.
description:            |
                        Each test runs a peer command in a new folder,
                        with a copy of the repository as the one tree
                        that a segment may consume, and checks what it
                        writes, what it prints and its exit status.
edge:                   []

...
"""


import click.testing

import cctool.check.check
import cctool.check.segment
import cctool.cli.command


TUPLE_INIT  = ('--title', 'The cc-patrol segment',
               '--brief', 'cc-patrol, a peer of cc-public.',
               '--copyright', 'Copyright 2026 The Peer',
               '--license', 'Apache-2.0')
FILE_PATROL = '_data/federated_segment/segment_cc_patrol.yaml'


# -----------------------------------------------------------------------------
def _run(monkeypatch, tree, *list_arg):
    """
    Return the result of cctool peer with list_arg, with tree as the one
    tree that a segment may consume.

    """

    monkeypatch.setattr(cctool.check.segment, 'trees',
                        lambda: [(cctool.check.segment.PLACE_CHECKOUT, tree)])
    runner = click.testing.CliRunner()
    return runner.invoke(cctool.cli.command.main, ['peer', *list_arg])


def test_init_writes_a_segment_item_that_passes(tree, tmp_path_factory, monkeypatch):
    root   = tmp_path_factory.mktemp('peer')
    result = _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--root', str(root))
    text   = (root / FILE_PATROL).read_text(encoding = 'utf-8')
    (failures, _, notices) = cctool.check.check.review(root)

    assert result.exit_code == 0
    assert result.stdout    == 'Wrote {file}\n'.format(file = FILE_PATROL)
    assert 'id_target:          release_cc_public_0_1_0' in text
    assert 'Copyright 2026 The Peer' in text
    assert failures == {}
    assert notices  == {}


def test_init_of_a_tree_that_holds_a_segment_is_an_error(tree, tmp_path_factory, monkeypatch):
    root = tmp_path_factory.mktemp('peer')
    _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--root', str(root))
    result = _run(monkeypatch, tree, 'init', 'cc_other', *TUPLE_INIT, '--root', str(root))

    assert result.exit_code == 2
    assert 'holds a segment item already' in result.stderr
    assert not (root / '_data' / 'federated_segment' / 'segment_cc_other.yaml').exists()


def test_init_with_a_name_that_is_not_lower_case_words_is_an_error(tree, tmp_path_factory, monkeypatch):
    root   = tmp_path_factory.mktemp('peer')
    result = _run(monkeypatch, tree, 'init', 'CC-Patrol', *TUPLE_INIT, '--root', str(root))

    assert result.exit_code == 2
    assert 'is not a name for a segment' in result.stderr


def test_init_with_a_brief_that_starts_with_a_space_is_an_error(tree, tmp_path_factory,
                                                                monkeypatch):
    root   = tmp_path_factory.mktemp('peer')
    result = _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--brief', ' A peer.',
                  '--root', str(root))

    assert result.exit_code == 2
    assert 'Prose whose first line starts with a space' in result.stderr
    assert 'brief' not in result.stderr
    assert not (root / FILE_PATROL).exists()


def test_init_of_a_segment_item_that_would_fail_its_schema_is_an_error(tree, tmp_path_factory,
                                                                       monkeypatch):
    root   = tmp_path_factory.mktemp('peer')
    result = _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--copyright', '',
                  '--license', 'Not a license', '--root', str(root))

    assert result.exit_code == 2
    assert 'The segment item would fail the checks, so nothing is written' in result.stderr
    assert 'schema_violation' in result.stderr
    assert not (root / FILE_PATROL).exists()


def test_status_reports_the_pinned_release(tree, tmp_path_factory, monkeypatch):
    root = tmp_path_factory.mktemp('peer')
    _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--root', str(root))
    result = _run(monkeypatch, tree, 'status', '--root', str(root))

    assert result.exit_code == 0
    assert result.stdout    == ('segment_cc_patrol pins release_cc_public_0_1_0 of '
                                'segment_cc_public, read from a checkout; the newest is '
                                'release_cc_public_0_1_0.\n')


def test_status_of_a_release_no_tree_holds_is_a_nonconformity(tree, tmp_path_factory, monkeypatch):
    root = tmp_path_factory.mktemp('peer')
    _run(monkeypatch, tree, 'init', 'cc_patrol', *TUPLE_INIT, '--root', str(root))
    path = root / FILE_PATROL
    path.write_text(path.read_text(encoding = 'utf-8')
                        .replace('release_cc_public_0_1_0', 'release_cc_public_9_9_9'),
                    encoding = 'utf-8')
    result = _run(monkeypatch, tree, 'status', '--root', str(root))

    assert result.exit_code == 1
    assert 'pins release_cc_public_9_9_9, which no tree read holds' in result.stdout


def test_status_of_a_tree_with_no_segment_is_an_error(tree, tmp_path_factory, monkeypatch):
    root   = tmp_path_factory.mktemp('peer')
    result = _run(monkeypatch, tree, 'status', '--root', str(root))

    assert result.exit_code == 2
    assert 'holds no segment item' in result.stderr
