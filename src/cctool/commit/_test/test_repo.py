"""
---

id_self:                pym_cctool.commit._test.test_repo
guid_self:              pym_747e9eedf54c4caebe6ac4bbf2e1ae0e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Repository step tests
brief:                  |
                        Tests of bundling commits.
description:            |
                        Each test bundles the commits of a branch in a
                        small repository, as a remote session does
                        before its work is submitted on atlas.
edge:                   []

...
"""


import pathlib
import subprocess

import pytest

import cctool.commit.repo


def test_the_default_bundle_of_a_branch_with_a_slash_sits_beside_the_repository():
    root = pathlib.Path('/work/cc-public')
    assert cctool.commit.repo.bundle_path(root, 'claude/fix-x') == pathlib.Path(
                                                                    '/work/claude-fix-x.bundle')
    assert cctool.commit.repo.bundle_path(root, 'topic') == pathlib.Path('/work/topic.bundle')


def test_a_bundle_holds_the_commits_of_a_branch_beyond_its_base(dev_repo):
    _git(dev_repo, 'checkout', '--quiet', '-b', 'topic')
    (dev_repo / 'one.txt').write_text('one\n')
    _git(dev_repo, 'add', '--all')
    _git(dev_repo, 'commit', '--quiet', '--no-verify', '--message', 'Add one.txt')
    path = cctool.commit.repo.bundle_path(dev_repo, 'topic')

    [bundled] = cctool.commit.repo.bundle(dev_repo, 'topic', 'dev', path)
    assert bundled.endswith(' Add one.txt')
    assert _git(dev_repo, 'bundle', 'list-heads', str(path)).split()[1] == 'refs/heads/topic'
    with pytest.raises(cctool.commit.repo.ErrorRepo, match = 'holds no commit that topic'):
        cctool.commit.repo.bundle(dev_repo, 'dev', 'topic', path)


# -----------------------------------------------------------------------------
def _git(root, *list_arg):
    """
    Run git with list_arg in root, and return what it prints.

    """

    return subprocess.run(['git', *list_arg],
                          cwd = root, check = True, capture_output = True, text = True).stdout
