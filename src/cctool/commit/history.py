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
                        sch_commit as its own tree holds it, its
                        author and signature against the team members
                        that tree holds, and its change against its
                        first parent with check_trees in
                        pym_cctool.commit.change. A commit item whose
                        id another commit's item has, as a cherry-pick
                        makes, is reported. pushed reads the lines git
                        gives a pre-push hook, and selects the commits
                        the remote does not have, passing over a tip
                        that cctool repo push has just checked. A
                        pushed tag is not checked: it names history
                        already made, and a commit it names is checked
                        when a branch brings it in.
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
MARK_RELEASE  = 'v'

# The variable by which cctool repo push tells the pre-push hook the
# commit it has just checked as the hook would, so that the hook does
# not check it again while git holds the connection to the remote open.
#
ENV_CHECKED   = 'CCTOOL_PUSH_CHECKED'

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
def pushed(root:    pathlib.Path,
           remote:  str,
           text:    str,
           checked: str | None = None) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    """
    Return the commits that a push to remote would send, oldest first,
    the tip of each ref it updates, and each release tag it sets, as
    the name of the tag and the commit it names, from text, the lines
    that git gives a pre-push hook. A commit any ref of remote already
    has is not sent.

    What a line updates is told by the ref of the remote, since a local
    tag may be pushed to a branch. A tag of the remote names history
    already made, so its commits are passed over, but a release tag,
    one whose name starts with v, is returned to be verified. So is a
    branch whose new tip is checked, the commit that cctool repo push
    has just checked, as this would, before git connected to remote.

    """

    list_commit = []
    list_tip    = []
    list_tag    = []

    for line in text.splitlines():
        list_part = line.split()
        if len(list_part) != 4 or list_part[1] == ZERO:
            continue
        if list_part[2].startswith(PREFIX_TAG):
            tag = list_part[2].removeprefix(PREFIX_TAG)
            if tag.startswith(MARK_RELEASE):
                list_tag.append((tag, _git(root, 'rev-parse',
                                           list_part[1] + '^{commit}').strip()))
            continue
        if list_part[1] == checked:
            continue
        list_tip.append(list_part[1])
        for commit in commits(root, [list_part[1], '--not', '--remotes=' + remote]):
            if commit not in list_commit:
                list_commit.append(commit)

    return (list_commit, list_tip, list_tag)


# -----------------------------------------------------------------------------
def check(root: pathlib.Path, commit: str) -> list[str]:
    """
    Return a sentence for each way the commit fails: its message,
    checked against sch_commit as its own tree holds it, its author and
    its signature, checked against the team members that its first
    parent holds, or its own tree if it has none, and its change,
    checked against its first parent. A commit that changes the team
    member register is judged by the register as it was, so that it
    cannot admit its own author or key.

    """

    text      = _git(root, 'log', '-1', '--format=%B', commit)
    author    = _git(root, 'log', '-1', '--format=%an <%ae>', commit)
    signature = _git(root, 'log', '-1', '--format=%G?%x00%GK%x00%GF%x00%GP', commit)
    (status, *list_key) = signature.strip('\n').split('\x00')

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        cctool.gate.gate.copy_commit(root, commit, dir_after)
        dir_judge = dir_after
        if cctool.commit.change.is_commit(root, commit + '^'):
            cctool.gate.gate.copy_commit(root, commit + '^', dir_before)
            dir_judge = dir_before

        list_found = (cctool.commit.message.violations(dir_after, text)
                      + cctool.commit.message.author_violations(dir_judge, author)
                      + cctool.commit.message.signature_violations(dir_judge, status, list_key))
        if list_found and cctool.commit.message.LINE_OPEN not in text.split('\n'):
            return ['{found} {hint}'.format(found = list_found[0], hint = HINT_CUT),
                    *list_found[1:]]
        if list_found:
            return list_found

        (_, item) = cctool.commit.message.parse(text)
        failures  = cctool.commit.change.check_trees(
                        dir_before, dir_after, item,
                        cctool.commit.change.reverted(root, item, commit + '^'))

    return cctool.commit.change.described(failures)


# -----------------------------------------------------------------------------
def failures(root: pathlib.Path, list_commit: list[str]) -> list[str]:
    """
    Return a line for each failure of each commit of list_commit, and
    for each commit id held by more than one commit.

    """

    list_found = []

    for commit in list_commit:
        head = short(root, commit)
        list_found += ['{head}: {found}'.format(head = head, found = found)
                       for found in check(root, commit)]

    for (id_item, list_holder) in duplicates(root, list_commit):
        list_found.append('{id} is the id of the items of more than one commit: {list}'.format(
            id = id_item, list = ', '.join(holder[:LENGTH_SHORT]
                                           for holder in list_holder)))

    return list_found


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
