"""
---

id_self:                pym_cctool.check._test.test_store
guid_self:              pym_2c3a352f2fe345e6b4cc3a13bbfa4438
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Store tests
brief:                  |
                        Tests of the store of verdicts that the
                        checker keeps from one run to the next.
description:            |
                        A test that a verdict is reused writes a
                        verdict into the store that the check would
                        not find, and empties the caches of the OS
                        process, so that the check can only have it
                        from the store.
edge:                   []

...
"""


import json

import pytest

import cctool.check.check
import cctool.check.schema
import cctool.check.store
import cctool.edit.layout
import cctool.graph.extract


# -----------------------------------------------------------------------------
@pytest.fixture
def dir_store(tmp_path_factory, monkeypatch):
    """
    Return the directory of a store that the checker uses, with the
    caches of the OS process emptied.

    """

    dir_store = tmp_path_factory.mktemp('store')
    monkeypatch.setenv(cctool.check.store.ENV_STORE, str(dir_store))
    _forget(monkeypatch)
    return dir_store


# -----------------------------------------------------------------------------
def _forget(monkeypatch):
    """
    Empty what the checker keeps in the OS process from one check to the
    next.

    """

    monkeypatch.setattr(cctool.edit.layout, 'MAP_VIOLATION', {})
    monkeypatch.setattr(cctool.check.check, 'CACHE_SCHEMA', {})
    monkeypatch.setattr(cctool.check.check, 'CACHE_REVIEW', {})


# -----------------------------------------------------------------------------
def _rewrite(dir_store, kind, change):
    """
    Rewrite the verdicts of kind in the store with change, which takes
    them and returns what was changed.

    """

    path   = dir_store / (kind + cctool.check.store.SUFFIX_STORE)
    stored = json.loads(path.read_text())
    found  = change(stored['verdict'])
    path.write_text(json.dumps(stored))
    return found


def test_what_is_saved_is_loaded_by_the_same_code(dir_store):
    cctool.check.store.save('kind', {'key': ['row']})
    assert cctool.check.store.load('kind') == {'key': ['row']}


def test_what_other_code_saved_is_not_loaded(dir_store, monkeypatch):
    cctool.check.store.save('kind', {'key': ['row']})
    monkeypatch.setattr(cctool.check.store, 'code', lambda: 'other')
    assert cctool.check.store.load('kind') == {}


def test_with_no_store_nothing_is_kept(tmp_path, monkeypatch):
    monkeypatch.delenv(cctool.check.store.ENV_STORE, raising = False)
    cctool.check.store.save('kind', {'key': ['row']})
    assert cctool.check.store.load('kind') == {}


def test_the_layout_check_reuses_the_verdict_the_store_keeps(tree, dir_store, monkeypatch):
    map_document = cctool.graph.extract.documents(tree)
    assert cctool.edit.layout.violations(tree, map_document) == []

    def change(map_verdict):
        key              = min(map_verdict)
        relative         = key.split(cctool.check.store.DELIM_KEY)[0]
        map_verdict[key] = [relative, '1', 'Kept.']
        return relative

    relative = _rewrite(dir_store, cctool.edit.layout.KIND_STORE, change)
    _forget(monkeypatch)
    assert cctool.edit.layout.violations(tree, map_document) == [(relative, '1', 'Kept.')]


def test_the_layout_check_lays_out_a_file_changed_since(tree, dir_store, monkeypatch):
    map_document = cctool.graph.extract.documents(tree)
    cctool.edit.layout.violations(tree, map_document)
    relative = next(file for file in cctool.graph.extract.files(map_document)
                    if file.endswith(cctool.graph.extract.SUFFIX_YAML))
    path     = tree / relative
    path.write_text(path.read_text() + '\n')
    _forget(monkeypatch)
    [(file, _, _)] = cctool.edit.layout.violations(tree,
                                                   cctool.graph.extract.documents(tree))
    assert file == relative


def test_schema_validation_reuses_the_verdict_the_store_keeps(tree, dir_store, monkeypatch):
    assert cctool.check.check.check(tree).get('schema_violation') is None

    def change(map_verdict):
        key              = min(map_verdict)
        row              = [*key.split(cctool.check.store.DELIM_KEY)[:3], '1', 'title', 'Kept.']
        map_verdict[key] = [row]
        return tuple(row)

    row = _rewrite(dir_store, cctool.check.schema.KIND_STORE, change)
    _forget(monkeypatch)
    assert cctool.check.check.check(tree)['schema_violation'] == [row]
