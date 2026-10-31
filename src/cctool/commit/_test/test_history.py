"""
---

id_self:                pym_cctool.commit._test.test_history
guid_self:              pym_9f8b1e62c6a04c078f2f008d2ab77295
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit history tests
brief:                  |
                        Tests of checking commits already made.
description:            |
                        Each test commits a copy of the repository
                        without hooks, as a rebase, a cherry-pick or a
                        clone without hooks would, and checks the
                        commits it made.
edge:                   []

...
"""


import os
import subprocess

import click.testing
import pytest

import cctool.cli.command
import cctool.commit.history
import cctool.commit.message
import cctool.conftest
import cctool.gate.gate
import cctool.gate.result


pytestmark = pytest.mark.prepush


# The identity of the maintainer, as git takes it, which the team member
# register gives as his git_author.
#
IDENT_MAINTAINER = ('-c', 'user.name=William Payne', '-c', 'user.email=wtpayne@gmail.com')


# -----------------------------------------------------------------------------
@pytest.fixture
def repo(signed_repo):
    """
    Return the root of a copy of the repository, committed and signed on
    main, as signed_repo gives it.

    """

    return signed_repo


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *IDENT_MAINTAINER, *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout


# -----------------------------------------------------------------------------
def _replace(root, relative, old, new):
    """
    Replace the one old in the file at relative under root with new.

    """

    path = root / relative
    text = path.read_text()
    assert text.count(old) == 1
    path.write_text(text.replace(old, new))


# -----------------------------------------------------------------------------
def _commit(root, message):
    """
    Commit everything in root under message, without hooks, as a
    rebase or a clone without hooks would.

    """

    _git(root, 'add', '--all')
    _git(root, 'commit', '--quiet', '--no-verify', '--allow-empty', '--message', message)


def test_a_history_that_conforms_passes(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cctool.commit.message.compose('Change README.md so that it is short',
                                                'It is short.'))
    list_commit = cctool.commit.history.commits(repo, ['HEAD'])
    assert len(list_commit) == 2
    assert [cctool.commit.history.check(repo, commit) for commit in list_commit] == [[], []]
    assert cctool.commit.history.duplicates(repo, list_commit) == []


def test_a_commit_made_without_the_hooks_is_reported(repo):
    (repo / '_data/register/reg_concern.yaml').unlink()
    _commit(repo, 'Tidy up')
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('A commit message is a subject line, a blank line,')
    assert found.endswith(cctool.commit.history.HINT_CUT)


def test_a_commit_authored_by_no_team_member_is_reported(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, 'commit', '--quiet', '--no-verify',
         '--author', 'Claude <noreply@anthropic.com>',
         '--message', cctool.commit.message.compose('Change README.md so that it is short',
                                                    'It is short.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('The commit is authored by Claude <noreply@anthropic.com>, who '
                            'is not the git_author of a team member')


def test_a_commit_that_is_not_signed_is_reported(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '--message',
         cctool.commit.message.compose('Change README.md so that it is short', 'It is short.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('The commit is not signed, and a team member')


def test_an_attribute_of_the_clone_does_not_change_the_verdict(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '--message',
         cctool.commit.message.compose('Change README.md so that it is short', 'It is short.'))
    (repo / '.git/info').mkdir(exist_ok = True)
    (repo / '.git/info/attributes').write_text(
        '{path} export-ignore\n'.format(path = cctool.conftest.FILE_MEMBERS))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.startswith('The commit is not signed, and a team member')


def test_a_range_that_selects_no_commit_is_an_error(tmp_path):
    subprocess.run(['git', 'init', '--quiet'], cwd = tmp_path, check = True)
    _git(tmp_path, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty',
         '--no-verify', '--message', 'Start')
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['history', 'check', 'HEAD..HEAD',
                                               '--gate', '--root', str(tmp_path)])
    assert result.exit_code == 2
    assert result.stderr == 'HEAD..HEAD selects no commit, so there is nothing to check.\n'


def test_a_commit_signed_with_the_key_of_no_team_member_is_reported(repo, keyring):
    _replace(repo, cctool.conftest.FILE_MEMBERS, keyring[1], 'ABCDEF0123456789')
    _commit(repo, cctool.commit.message.compose('Change the team member register so that it is '
                                                'wrong', 'It is wrong.'))
    assert cctool.commit.history.check(repo, 'HEAD') == []
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cctool.commit.message.compose('Change README.md so that it is short',
                                                'It is short.'))
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found == ('The commit is signed with the key {key}, which is the git_signing_key of '
                     'no team member that a team member register holds.'.format(key = keyring[1]))


def test_a_tree_that_gives_no_signing_key_checks_no_signature(repo, keyring):
    _replace(repo, cctool.conftest.FILE_MEMBERS, '    ' + cctool.conftest.LINE_KEY.replace(cctool.conftest.KEY_MAINTAINER, keyring[1]), '')
    _commit(repo, cctool.commit.message.compose('Change the team member register so that it '
                                                'gives no key', 'It gives no key.'))
    (repo / 'README.md').write_text('Changed.\n')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify', '--message',
         cctool.commit.message.compose('Change README.md so that it is short', 'It is short.'))
    assert cctool.commit.history.check(repo, 'HEAD') == []


def test_a_commit_cannot_admit_its_own_author_or_drop_its_own_key(repo, keyring):
    _replace(repo, cctool.conftest.FILE_MEMBERS, 'wtpayne@gmail.com', 'noreply@anthropic.com')
    _replace(repo, cctool.conftest.FILE_MEMBERS, '    ' + cctool.conftest.LINE_KEY.replace(cctool.conftest.KEY_MAINTAINER, keyring[1]), '')
    _git(repo, 'add', '--all')
    _git(repo, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--no-verify',
         '--author', 'William Payne <noreply@anthropic.com>',
         '--message', cctool.commit.message.compose('Change the team member register so that '
                                                    'it admits another', 'It admits another.'))
    list_found = cctool.commit.history.check(repo, 'HEAD')
    assert [found.split(',')[0] for found in list_found] == [
        'The commit is authored by William Payne <noreply@anthropic.com>',
        'The commit is not signed']


def test_a_commit_copied_with_git_am_is_reported_with_the_cause(repo):
    (repo / 'README.md').write_text('Changed.\n')
    _commit(repo, cctool.commit.message.compose('Change README.md so that it is short',
                                                'It is short.'))
    patch = _git(repo, 'format-patch', '-1', '--stdout', 'HEAD')
    _git(repo, 'reset', '--quiet', '--hard', 'HEAD~1')
    subprocess.run(['git', *IDENT_MAINTAINER, 'am', '--quiet'],
                   cwd = repo, check = True, input = patch, text = True)
    assert _git(repo, 'log', '-1', '--format=%B').strip() == 'Change README.md so that it is short'
    [found] = cctool.commit.history.check(repo, 'HEAD')
    assert found.endswith(cctool.commit.history.HINT_CUT)


def test_a_commit_item_shared_by_two_commits_is_reported(repo):
    message = cctool.commit.message.compose('Change README.md so that it is short',
                                            'It is short.')
    _commit(repo, message)
    _commit(repo, message)
    list_commit = cctool.commit.history.commits(repo, ['HEAD'])
    (_, item)   = cctool.commit.message.parse(message)
    assert cctool.commit.history.duplicates(repo, list_commit[-1:]) == [
        (item['id_self'], list_commit[1:])]


def test_a_push_sends_only_what_the_remote_does_not_have(repo):
    head = _git(repo, 'rev-parse', 'HEAD').strip()
    _git(repo, 'update-ref', 'refs/remotes/origin/main', head)
    _commit(repo, cctool.commit.message.compose('Add nothing', 'Nothing.'))
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = ('refs/heads/main {tip} refs/heads/main {head}\n'
            'refs/heads/old {zero} refs/heads/old {head}\n'
            'refs/tags/old {tip} refs/tags/old {zero}\n').format(
                tip = tip, head = head, zero = cctool.commit.history.ZERO)
    assert cctool.commit.history.pushed(repo, 'origin', text) == ([tip], [tip], [])


def test_a_pushed_tag_is_not_checked(repo):
    _commit(repo, 'An old message with no item')
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = 'refs/tags/old {tip} refs/tags/old {zero}\n'.format(
               tip = tip, zero = cctool.commit.history.ZERO)
    assert cctool.commit.history.pushed(repo, 'origin', text) == ([], [], [])


def test_a_tag_pushed_to_a_branch_is_checked_as_the_branch(repo):
    _commit(repo, 'An old message with no item')
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = 'refs/tags/old {tip} refs/heads/dev {zero}\n'.format(
               tip = tip, zero = cctool.commit.history.ZERO)
    (list_commit, list_tip, list_tag) = cctool.commit.history.pushed(repo, 'origin', text)
    assert (list_commit[-1], list_tip, list_tag) == (tip, [tip], [])


def test_a_pushed_release_tag_is_verified(repo):
    _git(repo, 'tag', '--annotate', '--message', 'A release', 'v9.9.9')
    head = _git(repo, 'rev-parse', 'HEAD').strip()
    tag  = _git(repo, 'rev-parse', 'v9.9.9').strip()
    text = 'refs/tags/v9.9.9 {tag} refs/tags/v9.9.9 {zero}\n'.format(
               tag = tag, zero = cctool.commit.history.ZERO)
    assert cctool.commit.history.pushed(repo, 'origin', text) == ([], [], [('v9.9.9', head)])
    result = click.testing.CliRunner().invoke(cctool.cli.command.main,
                                              ['history', 'check', '--pre-push', 'origin',
                                               '--root', str(repo)], input = text)
    assert result.exit_code == 1
    assert result.stdout.startswith('v9.9.9: The tree at ')


def test_a_branch_whose_tip_cctool_repo_push_checked_is_passed_over(repo):
    head = _git(repo, 'rev-parse', 'HEAD').strip()
    _commit(repo, 'An old message with no item')
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = ('refs/heads/main {tip} refs/heads/main {zero}\n'
            'refs/heads/old {head} refs/heads/old {zero}\n').format(
                tip = tip, head = head, zero = cctool.commit.history.ZERO)
    (list_commit, list_tip, _) = cctool.commit.history.pushed(repo, 'origin', text, tip)
    assert (tip in list_commit, list_tip) == (False, [head])


def test_the_hook_passes_the_push_of_a_tip_that_cctool_repo_push_checked(repo, monkeypatch):
    _commit(repo, 'An old message with no item')
    tip  = _git(repo, 'rev-parse', 'HEAD').strip()
    text = 'refs/heads/main {tip} refs/heads/main {zero}\n'.format(
               tip = tip, zero = cctool.commit.history.ZERO)

    def check():
        return click.testing.CliRunner().invoke(cctool.cli.command.main,
                                                ['history', 'check', '--pre-push', 'origin',
                                                 '--root', str(repo)], input = text)

    assert check().exit_code == 1
    monkeypatch.setenv(cctool.commit.history.ENV_CHECKED, tip)
    result = check()
    assert result.exit_code == 0
    assert result.stdout.startswith('{short} was checked by cctool repo push, so it is not '
                                    'checked again.'.format(
                                        short = cctool.commit.history.short(repo, tip)))


# -----------------------------------------------------------------------------
@pytest.fixture
def pushed(tmp_path, monkeypatch):
    """
    Return the root of a repository of one commit, the lines that git
    gives a pre-push hook for a push of it, and the file that the test
    stage of the gate appends a line to each time it runs, once the gate
    is made of stand-in stages that select the tests as the gate of a
    push does.

    """

    for key in [key for key in os.environ if key.startswith('GIT_')]:
        monkeypatch.delenv(key)

    path = tmp_path / 'ran.txt'
    code = 'open({path!r}, "a").write("ran\\n")'.format(path = str(path))
    monkeypatch.setattr(cctool.gate.gate, 'TUPLE_STAGE',
                        (('check', ('{python}', '-c', 'pass')),
                         ('test',  ('{python}', '-c', code, cctool.gate.gate.MARK_PUSH))))

    root = tmp_path / 'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '--quiet'], cwd = root, check = True)
    _git(root, '-c', 'commit.gpgsign=false', 'commit', '--quiet', '--allow-empty',
         '--no-verify', '--message', 'Start')
    tip  = _git(root, 'rev-parse', 'HEAD').strip()
    text = 'refs/heads/dev {tip} refs/heads/dev {zero}\n'.format(
               tip = tip, zero = cctool.commit.history.ZERO)
    return (root, text, path)


# -----------------------------------------------------------------------------
def _push(root, text):
    """
    Return the run of the checks of the pre-push hook, with the gate, for
    the push that text gives to the repository at root.

    """

    return click.testing.CliRunner().invoke(cctool.cli.command.main,
                                            ['history', 'check', '--gate', '--pre-push', 'origin',
                                             '--root', str(root)], input = text)


# -----------------------------------------------------------------------------
def _write_result(root, text, tuple_stage):
    """
    Write a passing gate result, for the gate of tuple_stage, of the tip
    that text pushes from the repository at root.

    """

    tip = text.split()[1]
    cctool.gate.result.write(root, tip, tip, tuple_stage,
                             [(name, True, '') for (name, _) in tuple_stage])


def test_a_push_of_a_tip_with_a_matching_gate_result_runs_no_tests(pushed):
    """
    ---

    id_self:                pyf_cctool.commit._test.test_history.test_a_push_of_a_tip_with_a_matching_gate_result_runs_no_tests
    guid_self:              pyf_73771ded0fad41e9b06e615508a25ac6
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a push proven by its gate result runs no tests
    brief:                  |
                            A push of a tip whose passing gate result
                            matches the policy and environment of the gate
                            of a push runs no tests.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_push_omits_only_proven_tests
        guid_target:        rqt_bf6506c5f1d44c63b4058e29a97001fa

    ...
    """

    (root, text, path) = pushed
    _write_result(root, text, cctool.gate.gate.TUPLE_STAGE)
    result = _push(root, text)
    assert 'as its gate result shows, so they are not run again.' in result.stdout
    assert not path.exists()


def test_a_push_of_a_tip_with_a_result_of_the_commit_gate_runs_the_tests(pushed):
    """
    ---

    id_self:                pyf_cctool.commit._test.test_history.test_a_push_of_a_tip_with_a_result_of_the_commit_gate_runs_the_tests
    guid_self:              pyf_9f202e3f76914b78b18bef924fc8455b
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Test that a result of the commit gate does not spare a push its tests
    brief:                  |
                            A push of a tip whose gate result comes from
                            the narrower selection of the commit gate runs
                            the tests.

    edge:

      - id_relation:        relation_verifies
        guid_relation:      relation_fc0c6e647b114e2d82abbfb938b09774
        id_target:          rqt_push_omits_only_proven_tests
        guid_target:        rqt_bf6506c5f1d44c63b4058e29a97001fa

    ...
    """

    (root, text, path) = pushed
    _write_result(root, text, tuple(stage for stage in cctool.gate.gate.TUPLE_STAGE
                                    if stage[0] != cctool.gate.gate.NAME_TEST))
    result = _push(root, text)
    assert 'not run again' not in result.stdout
    assert path.read_text() == 'ran\n'
