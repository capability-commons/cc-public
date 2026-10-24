"""
---

id_self:                pym_cctool.release._test.test_record
guid_self:              pym_a5e6c55a549d4b279bf9576a52a985bb
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Release record tests
brief:                  |
                        Tests of reading the version module and the
                        newest release item, and of the check that
                        they agree.
description:            |
                        Each test writes release items and a version
                        module into a copy of the repository, as the
                        release step writes them.
edge:                   []

...
"""


import shutil

import cctool.check.check
import cctool.conftest
import cctool.edit.edit
import cctool.release.record


# -----------------------------------------------------------------------------
def test_the_version_module_and_the_newest_release_disagree(tree):
    _release(tree, '0.1.0')
    _release(tree, '0.10.0')
    (tree / cctool.release.record.PATH_MODULE).write_text("VERSION = '0.9.0'\n")
    map_document = cctool.edit.edit.Tree(tree).map_document
    assert cctool.release.record.disagreements(tree, map_document) == [
        ('_data/release/release_0_10_0.yaml', '1', 'release_0_10_0', '0.10.0', '0.9.0')]
    (tree / cctool.release.record.PATH_MODULE).write_text("VERSION = '0.10.0'\n")
    assert cctool.release.record.disagreements(tree, map_document) == []


# -----------------------------------------------------------------------------
def test_the_check_reports_a_version_module_that_disagrees(tree):
    _module(tree)
    _release(tree, '0.2.0')
    failures = cctool.check.check.check(tree)
    assert failures[cctool.check.check.NAME_VERSION] == [
        ('_data/release/release_0_2_0.yaml', '1', 'release_0_2_0', '0.2.0', '0.1.0')]


# -----------------------------------------------------------------------------
def _module(root):
    """
    Copy the version module of the repository into the tree at root.

    """

    path = root / cctool.release.record.PATH_MODULE
    path.parent.mkdir(parents = True, exist_ok = True)
    shutil.copy(cctool.conftest.DIR_REPO / cctool.release.record.PATH_MODULE, path)


# -----------------------------------------------------------------------------
def _release(root, version):
    """
    Write a release item of version into the tree at root, as the
    release step writes one.

    """

    tree = cctool.edit.edit.Tree(root)
    tree.update(cctool.edit.edit.new(tree,
                                     'release_' + version.replace('.', '_'),
                                     [('title',      'Release ' + version),
                                      ('brief',      'A release.'),
                                      ('version',    version),
                                      ('dependency', [])],
                                     []))
    for (relative, text) in tree.edit.items():
        (root / relative).parent.mkdir(parents = True, exist_ok = True)
        (root / relative).write_text(text)
