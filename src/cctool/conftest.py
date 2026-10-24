"""
---

id_self:                pym_cctool.conftest
guid_self:              pym_8c07ee653351466fa401605f3b360b5f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test fixtures
brief:                  |
                        The fixtures the tests share: a copy of the
                        repository to break.
description:            |
                        This module holds the fixtures. Every test
                        runs wherever the environment is installed,
                        since clingo is part of it. A copy keeps only
                        a fixed slice of the deliberations: frozen
                        copies of the decisions the tests name, held
                        in _test/_fixture, in place of every decision
                        of the repository. So the tests neither slow
                        down nor change meaning as the deliberations
                        in the repository grow, are ruled on or are
                        corrected.
edge:                   []

...
"""


import fnmatch
import functools
import os
import pathlib
import shutil

import pytest

import cctool.graph.extract


DIR_REPO  = pathlib.Path(__file__).resolve().parents[2]

# What a copy leaves out: version control, environments, caches, local
# tools and the fixture, which goes in its own place.
#
TUPLE_SKIP = ('.git', '.pixi', '.venv', '_tools', '__pycache__', '.ruff_cache',
              '.pytest_cache', '*.egg-info', '_fixture')


# The decisions of a copy are those of the fixture, frozen copies of the
# decisions the tests name, not those of the repository. The fixture
# leaves out the ruling of dec_tooling_language, so that the tests have
# an open decision to work on. Change the fixture only for a test, and
# never because the repository has changed.
#
DIR_DECISION         = DIR_REPO / '_data' / 'decision'
DIR_FIXTURE_DECISION = pathlib.Path(__file__).resolve().parent / '_test' / '_fixture' / 'decision'


# The source a copy keeps: only the modules and logic programs that the
# rest of the copy names, and those that they name in turn, so that each
# check of a copy reads and checks less.
#
# The source files that the tests name are kept as well.
#
DIR_SOURCE          = DIR_REPO / 'src'
TUPLE_SOURCE_KEPT   = ('src/cctool/cli/__init__.py',
                       'src/cctool/edit/_test/test_edit.py',
                       'src/cctool/edit/edit.py',
                       'src/cctool/edit/layout.py',
                       'src/cctool/graph/jq.py')


# -----------------------------------------------------------------------------
def _ignore(dir_from: str, list_name: list[str]) -> set[str]:
    """
    Return the names in dir_from that a copy leaves out: those that
    match TUPLE_SKIP; in _data/decision, every decision; and in src,
    what _source_kept does not keep.

    """

    set_skip = shutil.ignore_patterns(*TUPLE_SKIP)(dir_from, list_name)
    dir_here = pathlib.Path(dir_from)
    if dir_here == DIR_DECISION:
        set_skip |= set(list_name)
    if dir_here == DIR_SOURCE or DIR_SOURCE in dir_here.parents:
        set_kept  = _source_kept()
        set_skip |= {name for name in list_name if dir_here / name not in set_kept}
    return set_skip


# -----------------------------------------------------------------------------
@functools.cache
def _source_kept() -> frozenset[pathlib.Path]:
    """
    Return the paths under src that a copy keeps: those of
    TUPLE_SOURCE_KEPT, each module or logic program that one of them or
    a file the copy keeps outside src mentions by its id, or by the id
    of a class or function in it, and those that they mention in turn,
    with the folders that hold them.

    """

    map_module = {}
    for path in DIR_SOURCE.rglob('*'):
        if path.suffix in cctool.graph.extract.MAP_PREFIX_MODULE and not _is_skipped(path):
            map_module[cctool.graph.extract.module_name(path.relative_to(DIR_REPO))] = path

    set_kept  = {DIR_REPO / relative for relative in TUPLE_SOURCE_KEPT}
    list_todo = [*(path for path in _outside_source() if path.is_file()), *set_kept]
    while list_todo:
        text = list_todo.pop().read_text(encoding = 'utf-8', errors = 'replace')
        for match in cctool.graph.extract.REGEX_MENTION.finditer(text):
            path = _module_of(match.group(0), map_module)
            if path is not None and path not in set_kept:
                set_kept.add(path)
                list_todo.append(path)

    return frozenset(set_kept | {dir_parent for path in set_kept for dir_parent in path.parents
                                 if DIR_SOURCE in dir_parent.parents})


# -----------------------------------------------------------------------------
def _outside_source() -> list[pathlib.Path]:
    """
    Return each path that a copy keeps outside src.

    """

    list_path = []
    for (name, list_dir, list_file) in os.walk(DIR_REPO):
        dir_here = pathlib.Path(name)
        list_dir[:] = [each for each in list_dir
                       if not _is_skipped(dir_here / each) and dir_here / each != DIR_SOURCE
                       and dir_here != DIR_DECISION]
        list_path.extend(dir_here / each for each in list_file if not _is_skipped(dir_here / each))
    list_path.extend(sorted(DIR_FIXTURE_DECISION.rglob('*')))
    return list_path


# -----------------------------------------------------------------------------
def _is_skipped(path: pathlib.Path) -> bool:
    """
    Return whether path, or a folder it is in, matches TUPLE_SKIP.

    """

    return any(fnmatch.fnmatch(part, pattern)
               for part in path.relative_to(DIR_REPO).parts for pattern in TUPLE_SKIP)


# -----------------------------------------------------------------------------
def _module_of(word: str, map_module: dict[str, pathlib.Path]) -> pathlib.Path | None:
    """
    Return the module or logic program that the id word names, or holds
    the class, function or predicate it names, or None if it names none.

    """

    (prefix, _, name) = word.partition(cctool.graph.extract.DELIM_PREFIX)
    prefix           += cctool.graph.extract.DELIM_PREFIX
    tuple_prefix      = (*cctool.graph.extract.MAP_PREFIX_MODULE.values(),
                         cctool.graph.extract.PREFIX_PACKAGE)
    tuple_prefix      = (prefix,) if prefix in tuple_prefix else tuple_prefix
    if prefix == cctool.graph.extract.PREFIX_PREDICATE:
        tuple_prefix  = (cctool.graph.extract.MAP_PREFIX_MODULE[
                             cctool.graph.extract.SUFFIX_PROGRAM],)
    list_part         = name.split(cctool.graph.extract.DELIM_MODULE)
    while list_part:
        dotted = cctool.graph.extract.DELIM_MODULE.join(list_part)
        for each in tuple_prefix:
            if each + dotted in map_module:
                return map_module[each + dotted]
        list_part.pop()
    return None


# -----------------------------------------------------------------------------
@pytest.fixture
def tree(tmp_path):
    """
    Yield the root of a copy of the repository: its data items, its
    source and the files at its root, without version control,
    environments or caches, and with the decisions of the fixture in
    place of those of the repository.

    The copy is removed when the test ends. A run makes one for each of
    some hundreds of tests, and pytest keeps the temporary folders of
    its last three runs, so copies left behind would fill a disk with
    few inodes.

    """

    shutil.copytree(DIR_REPO, tmp_path,
                    ignore        = _ignore,
                    dirs_exist_ok = True)
    shutil.copytree(DIR_FIXTURE_DECISION, tmp_path / DIR_DECISION.relative_to(DIR_REPO),
                    ignore        = shutil.ignore_patterns(*TUPLE_SKIP),
                    dirs_exist_ok = True)
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors = True)
