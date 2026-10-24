"""
---

id_self:                pym_cctool.commit.history
guid_self:              pym_4a1c1f91ca60499c8fd65f8709bb863a
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit history
brief:                  |
                        Check commits already made, however they were
                        made.
description:            |
                        git runs no commit hook for a rebase or a
                        cherry-pick, and a clone may have no hooks at
                        all, so the hooks cannot be relied on to have
                        checked a commit. A commit is checked here
                        from what it records: its message against
                        sch_commit as its own tree holds it, and its
                        change against its first parent with
                        check_trees in pym_cctool.commit.change. A
                        commit item whose id another commit's item
                        has, as a cherry-pick makes, is reported.
                        pushed reads the lines git gives a pre-push
                        hook, and selects the commits the remote does
                        not have. A pushed tag is not checked: it
                        names history already made, and a commit it
                        names is checked when a branch brings it in.
usage:                  |
                        cctool history check [RANGE] [--gate]
                        [--pre-push REMOTE]
edge:                   []

...
"""


import pathlib
import subprocess
import tempfile

import cctool.commit.change
import cctool.commit.message
import cctool.gate.gate


# The separators of the commits and fields that git log is asked for,
# as git writes them in a format and as they come back.
#
FORMAT_LOG    = '%H%x00%B%x01'
MARK_RECORD   = '\x01'
MARK_FIELD    = '\x00'
LENGTH_SHORT  = 7
ZERO          = '0' * 40
PREFIX_TAG    = 'refs/tags/'

# git am ends a commit message at its first --- line, so a commit
# copied from another machine with format-patch and am loses its item.
#
HINT_CUT      = ('If the commit was copied from another machine with git am, which ends '
                 'a message at its first --- line, copy it with git bundle instead.')


# -----------------------------------------------------------------------------
def commits(root: pathlib.Path, list_arg: list[str]) -> list[str]:
    """
    Return the commits that git rev-list selects with list_arg in the
    repository at root, oldest first.

    """

    return _git(root, 'rev-list', '--reverse', *list_arg).split()


# -----------------------------------------------------------------------------
def pushed(root: pathlib.Path, remote: str, text: str) -> tuple[list[str], list[str]]:
    """
    Return the commits that a push to remote would send, oldest first,
    and the tip of each ref it updates, from text, the lines that git
    gives a pre-push hook. A commit any ref of remote already has is
    not sent. A tag is passed over, since it names history already made.

    """

    list_commit = []
    list_tip    = []

    for line in text.splitlines():
        list_part = line.split()
        if len(list_part) != 4 or list_part[1] == ZERO or list_part[0].startswith(PREFIX_TAG):
            continue
        list_tip.append(list_part[1])
        for commit in commits(root, [list_part[1], '--not', '--remotes=' + remote]):
            if commit not in list_commit:
                list_commit.append(commit)

    return (list_commit, list_tip)


# -----------------------------------------------------------------------------
def check(root: pathlib.Path, commit: str) -> list[str]:
    """
    Return a sentence for each way the commit fails: its message,
    checked against sch_commit as its own tree holds it, and its
    change, checked against its first parent.

    """

    text = _git(root, 'log', '-1', '--format=%B', commit)

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        cctool.gate.gate.copy_commit(root, commit, dir_after)
        if cctool.commit.change.is_commit(root, commit + '^'):
            cctool.gate.gate.copy_commit(root, commit + '^', dir_before)

        list_found = cctool.commit.message.violations(dir_after, text)
        if list_found and cctool.commit.message.LINE_OPEN not in text.split('\n'):
            return ['{found} {hint}'.format(found = list_found[0], hint = HINT_CUT),
                    *list_found[1:]]
        if list_found:
            return list_found

        (_, item) = cctool.commit.message.parse(text)
        failures  = cctool.commit.change.check_trees(dir_before, dir_after, item)

    return cctool.commit.change.described(failures)


# -----------------------------------------------------------------------------
def duplicates(root: pathlib.Path, list_commit: list[str]) -> list[tuple[str, list[str]]]:
    """
    Return each commit id that the item of one of list_commit shares
    with the item of another commit reachable from any of them, as the
    id and the commits that hold it, oldest first.

    """

    if not list_commit:
        return []

    text    = _git(root, 'log', '--reverse', '--format=' + FORMAT_LOG, *list_commit)
    map_id  = {}

    for record in text.split(MARK_RECORD):
        (commit, _, message) = record.strip('\n').partition(MARK_FIELD)
        try:
            (_, item) = cctool.commit.message.parse(message)
        except cctool.commit.message.ErrorMessage:
            continue
        map_id.setdefault(str(item.get(cctool.commit.message.KEY_ID_SELF)), []).append(commit)

    set_commit = set(list_commit)

    return [(id_item, list_holder) for (id_item, list_holder) in map_id.items()
            if len(list_holder) > 1 and set_commit.intersection(list_holder)]


# -----------------------------------------------------------------------------
def short(root: pathlib.Path, commit: str) -> str:
    """
    Return the short hash of commit and its subject line.

    """

    return _git(root, 'log', '-1', '--format=%h %s', '--abbrev={n}'.format(n = LENGTH_SHORT),
                commit).strip()


# -----------------------------------------------------------------------------
def _git(root: pathlib.Path, *list_arg: str) -> str:
    """
    Return what git prints when run with list_arg in the repository at
    root.

    """

    try:
        return subprocess.run(['git', *list_arg],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout
    except subprocess.CalledProcessError as error:
        raise cctool.gate.gate.ErrorGate('git {arg} failed: {text}'.format(
                            arg = ' '.join(list_arg), text = error.stderr.strip())) from error
