"""
---

id_self:                pym_cctool.commit.change
guid_self:              pym_538a536ce0f34b61a7e2cda6a3ece5f7
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit change
brief:                  |
                        Check a commit against the graph before and
                        after it.
description:            |
                        The graph before the commit is read from HEAD,
                        and the graph after it from the staged
                        content. change.lp is evaluated over the graph
                        after the commit, the items before it, and the
                        verb and the mentions of the commit item. Each
                        shown predicate of change.lp is one check, and
                        each row of it is one failure.

                        Before the first commit there is no HEAD, and
                        the graph before it is empty. check_trees
                        checks the change between any two trees, which
                        is how a commit already made is checked
                        against its parent.
usage:                  |
                        Run by cctool message check, and so by the
                        commit-msg hook, and by cctool history check.
edge:                   []

...
"""


import contextlib
import pathlib
import re
import subprocess
import tempfile
import typing

import cctool.check.layout
import cctool.gate.gate
import cctool.graph.extract
import cctool.graph.logic


RULES           = pathlib.Path(__file__).with_name('change.lp')
TUPLE_KEY_TEXT  = ('title', 'brief', 'description')
KEY_TITLE       = 'title'

# The sentence that git's revert writes in the message, naming the
# commit reverted.
#
REGEX_REVERTS   = re.compile(r'This reverts commit ([0-9a-f]{7,40})\.')

Failures        = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def check(root: pathlib.Path, item: dict) -> Failures:
    """
    Return the failures of the commit that item records, as a commit of
    the staged content of the repository at root onto its HEAD.

    """

    with staged_trees(root) as (dir_before, dir_after, _):
        return check_trees(dir_before, dir_after, item, reverted(root, item, 'HEAD'))


# -----------------------------------------------------------------------------
@contextlib.contextmanager
def staged_trees(root: pathlib.Path) -> typing.Iterator[tuple[pathlib.Path, pathlib.Path, bool]]:
    """
    Yield a copy of the HEAD of the repository at root and a copy of its
    staged content, the trees before and after a commit of what is
    staged, and whether HEAD is a commit. An empty tree stands for HEAD
    before the first commit. Both are removed afterwards.

    """

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        is_head    = is_commit(root, 'HEAD')
        if is_head:
            cctool.gate.gate.copy_commit(root, 'HEAD', dir_before)
        cctool.gate.gate.copy_staged(root, dir_after)
        yield (dir_before, dir_after, is_head)


# -----------------------------------------------------------------------------
def reverted(root: pathlib.Path, item: dict, base: str) -> set[str]:
    """
    Return each commit that item says, as git's revert writes, that the
    commit it records reverts, if that commit is base or an ancestor of
    it, in the repository at root.

    """

    text = ' '.join(' '.join(str(item.get(key, '')) for key in TUPLE_KEY_TEXT).split())
    if not is_commit(root, base):
        return set()

    return {commit for commit in REGEX_REVERTS.findall(text)
            if subprocess.run(['git', 'merge-base', '--is-ancestor', commit, base],
                              cwd            = root,
                              capture_output = True,
                              check          = False).returncode == 0}


# -----------------------------------------------------------------------------
def check_trees(dir_before:   pathlib.Path,
                dir_after:    pathlib.Path,
                item:         dict,
                set_reverted: set[str] | None = None) -> Failures:
    """
    Return the failures of the commit that item records, as the change
    from the tree in dir_before to the tree in dir_after. set_reverted
    holds each earlier commit that the commit is known to revert.

    """

    facts = facts_of(dir_before, dir_after, item, set_reverted)
    rows  = cctool.graph.logic.run(facts, RULES.read_text(encoding = 'utf-8'))

    return {name: list_row for (name, list_row) in rows.items() if list_row}


# -----------------------------------------------------------------------------
def described(failures: Failures) -> list[str]:
    """
    Return a line for each failure, worded as change.lp words it, and
    then what to do about the failures of each check.

    """

    text = RULES.read_text(encoding = 'utf-8')
    return cctool.graph.logic.described(
               failures,
               {name: tuple(column for (column, _) in tuple_column)
                for (name, tuple_column) in cctool.graph.logic.declared(text).items()},
               cctool.graph.logic.worded(text))


# -----------------------------------------------------------------------------
def is_commit(root: pathlib.Path, rev: str) -> bool:
    """
    Return True if rev names a commit in the repository at root.

    """

    return subprocess.run(['git', 'rev-parse', '--verify', '--quiet', rev + '^{commit}'],
                          cwd            = root,
                          capture_output = True,
                          check          = False).returncode == 0


# -----------------------------------------------------------------------------
def facts_of(dir_before:   pathlib.Path,
             dir_after:    pathlib.Path,
             item:         dict,
             set_reverted: set[str] | None = None) -> cctool.graph.extract.Facts:
    """
    Return the facts that change.lp is evaluated over: those of the
    tree in dir_after, the items and edges of the tree in dir_before,
    the facts of the commit item, each commit of set_reverted, and each
    file that the commit removes which held no item.

    """

    facts        = cctool.graph.extract.extract(dir_after)
    before       = cctool.graph.extract.extract(dir_before)
    text         = ' '.join(str(item.get(key, '')) for key in TUPLE_KEY_TEXT)
    list_removed = _removed_files(dir_before, dir_after,
                                  {cctool.graph.extract.file_of(row[3]) for row in before['item']})

    facts['before_item']       = {(row[0], row[1]) for row in before['item']}
    facts['before_edge']       = before['edge']
    facts['commit_verb']       = {(str(item.get(KEY_TITLE, '')).partition(' ')[0],)}
    facts['commit_mention']    = {(id_item,) for id_item
                                  in cctool.graph.extract.REGEX_MENTION.findall(text)}
    facts['content_change']    = {(file,) for file in _changed(dir_before, dir_after)}
    facts['reverted_ancestor'] = {(commit,) for commit in set_reverted or ()}
    facts['removed_file']      = {(file,) for file in list_removed}
    facts['named_file']        = {(file,) for file in list_removed if file in text}

    return facts


# -----------------------------------------------------------------------------
def _files(root: pathlib.Path) -> set[str]:
    """
    Return each file of the tree at root, relative to it.

    """

    return {str(path.relative_to(root)) for path in root.rglob('*') if path.is_file()}


# -----------------------------------------------------------------------------
def _removed_files(dir_before: pathlib.Path,
                   dir_after:  pathlib.Path,
                   set_held:   set[str]) -> list[str]:
    """
    Return each file of the tree in dir_before that the tree in
    dir_after lacks, and that holds no item, by set_held, the files that
    hold items. A file whose content the tree after holds in a file it
    adds is moved, not removed.

    """

    set_before = _files(dir_before)
    set_after  = _files(dir_after)
    set_moved  = {_read(dir_after, file) for file in set_after - set_before}

    return sorted(file for file in set_before - set_after
                  if file not in set_held and _read(dir_before, file) not in set_moved)


# -----------------------------------------------------------------------------
def _changed(dir_before: pathlib.Path, dir_after: pathlib.Path) -> list[str]:
    """
    Return each file that differs between the two trees beyond what
    the layout printer changes, relative to the root of each.

    """

    set_file = _files(dir_before) | _files(dir_after)

    # Laying a file out is slow, and most files are the same byte for
    # byte, so only those that differ are laid out.
    #
    return sorted(file for file in set_file
                  if _read(dir_before, file) != _read(dir_after, file)
                  and _laid_out(dir_before, file) != _laid_out(dir_after, file))


# -----------------------------------------------------------------------------
def _read(root: pathlib.Path, file: str) -> bytes | None:
    """
    Return the bytes of file in the tree at root, or None if there is
    no such file.

    """

    path = root / file
    return path.read_bytes() if path.is_file() else None


# -----------------------------------------------------------------------------
def _laid_out(root: pathlib.Path, file: str) -> str | bytes | None:
    """
    Return the content of file in the tree at root as the layout
    printer would write it, its bytes if it is not text it can lay
    out, or None if there is no such file.

    """

    path = root / file
    if not path.is_file():
        return None

    data = path.read_bytes()
    try:
        return cctool.check.layout.format_file(data.decode('utf-8'), pathlib.Path(file))
    except (UnicodeDecodeError, cctool.check.layout.Unsupported):
        return data
