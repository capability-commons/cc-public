"""
---

id_self:                pym_cc_public.commit.change
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
                        shown relation of change.lp is one check, and
                        each row of it is one failure.

                        Before the first commit there is no HEAD, and
                        the graph before it is empty. check_trees
                        checks the change between any two trees, which
                        is how a commit already made is checked
                        against its parent.
usage:                  |
                        Run by cctool message check, and so by the
                        commit-msg hook, and by cctool history check.
relation:               []

...
"""


import pathlib
import subprocess
import tempfile

import cc_public.edit.layout
import cc_public.gate.gate
import cc_public.graph.datalog
import cc_public.graph.extract


RULES           = pathlib.Path(__file__).with_name('change.lp')
TUPLE_KEY_TEXT  = ('title', 'brief', 'description')
KEY_TITLE       = 'title'

Failures        = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def check(root: pathlib.Path, item: dict) -> Failures:
    """
    Return the failures of the commit that item records, as a commit of
    the staged content of the repository at root onto its HEAD.

    """

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        if is_commit(root, 'HEAD'):
            cc_public.gate.gate.copy_commit(root, 'HEAD', dir_before)
        cc_public.gate.gate.copy_staged(root, dir_after)
        return check_trees(dir_before, dir_after, item)


# -----------------------------------------------------------------------------
def check_trees(dir_before: pathlib.Path, dir_after: pathlib.Path, item: dict) -> Failures:
    """
    Return the failures of the commit that item records, as the change
    from the tree in dir_before to the tree in dir_after.

    """

    facts = facts_of(dir_before, dir_after, item)
    rows  = cc_public.graph.datalog.run(facts, RULES.read_text(encoding = 'utf-8'))

    return {name: list_row for (name, list_row) in rows.items() if list_row}


# -----------------------------------------------------------------------------
def described(failures: Failures) -> list[str]:
    """
    Return a line for each failure, worded as change.lp words it, and
    then what to do about the failures of each check.

    """

    text = RULES.read_text(encoding = 'utf-8')
    return cc_public.graph.datalog.described(
               failures,
               {name: tuple(column for (column, _) in tuple_column)
                for (name, tuple_column) in cc_public.graph.datalog.declared(text).items()},
               cc_public.graph.datalog.worded(text))


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
def facts_of(dir_before: pathlib.Path,
             dir_after:  pathlib.Path,
             item:       dict) -> cc_public.graph.extract.Facts:
    """
    Return the facts that change.lp is evaluated over: those of the
    tree in dir_after, the items of the tree in dir_before, and the
    facts of the commit item.

    """

    facts  = cc_public.graph.extract.extract(dir_after)
    before = cc_public.graph.extract.extract(dir_before)
    text   = ' '.join(str(item.get(key, '')) for key in TUPLE_KEY_TEXT)

    facts['before_item']    = {(row[0], row[1]) for row in before['item']}
    facts['commit_verb']    = {(str(item.get(KEY_TITLE, '')).partition(' ')[0],)}
    facts['commit_mention'] = {(id_item,) for id_item
                               in cc_public.graph.extract.REGEX_MENTION.findall(text)}
    facts['content_change'] = {(file,) for file in _changed(dir_before, dir_after)}

    return facts


# -----------------------------------------------------------------------------
def _changed(dir_before: pathlib.Path, dir_after: pathlib.Path) -> list[str]:
    """
    Return each file that differs between the two trees beyond what
    the layout printer changes, relative to the root of each.

    """

    set_file = {str(path.relative_to(root))
                for root in (dir_before, dir_after)
                for path in root.rglob('*') if path.is_file()}

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
        return cc_public.edit.layout.format_file(data.decode('utf-8'), pathlib.Path(file))
    except (UnicodeDecodeError, cc_public.edit.layout.Unsupported):
        return data
