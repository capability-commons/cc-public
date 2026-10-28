"""
---

id_self:                pym_cctool.commit.repo
guid_self:              pym_966c21767d074220bba817eaa73345ad
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Repository steps
brief:                  |
                        Land, sign, push and bundle commits, as the
                        maintainer does each day.
description:            |
                        Commits made elsewhere, as an agent makes
                        them, come to the maintainer as a git bundle,
                        never as patches, since git am ends a message
                        at the first --- line and so cuts off the
                        commit item. land fetches the branch a bundle
                        holds, replays its commits onto the current
                        branch, signs each, checks them as cctool
                        history check does, and moves the branch
                        forward to them only if all of that succeeds.
                        sign signs the commits that the remote does
                        not have yet, and push refuses to push one
                        that is not signed before the pre-push hook
                        runs its own checks. bundle makes a bundle of
                        the commits a branch holds beyond its base.
                        Each step leaves the branch where it was when
                        it fails.
usage:                  |
                        cctool repo land BUNDLE [--branch NAME] cctool
                        repo sign [--since REF] cctool repo push
                        [--remote NAME] cctool repo bundle BRANCH
                        [--base REF] [--output FILEPATH]
edge:                   []

...
"""


import pathlib
import subprocess

import cctool.commit.history
import cctool.commit.message


# The ref of a branch, as git bundle list-heads names the heads of a
# bundle.
#
PREFIX_HEAD = 'refs/heads/'

# git's advice on what to do next, which names commands a step takes
# for itself, and is left out of what a failure says.
#
PREFIX_HINT = 'hint:'


# -----------------------------------------------------------------------------
class ErrorRepo(Exception):
    """
    A step that cannot be taken, and why; the branch is left as it was.

    """


# -----------------------------------------------------------------------------
def land(root: pathlib.Path, path: pathlib.Path, branch: str | None = None) -> list[str]:
    """
    Return the commits, as short hashes and subjects, that the bundle at
    path holds beyond the current branch, once they are signed and the
    current branch is moved forward to them.

    The bundle's branch is the one it holds, or branch if it holds
    more. Its commits are replayed onto the current branch, so that a
    branch made on an older base lands as if made on this one, and each
    is signed as it is replayed. They are then checked as cctool
    history check checks them. A replay that conflicts, or a check
    that fails, leaves the current branch where it was.

    """

    base = _branch(root)
    _refuse_changes(root)

    _git(root, 'bundle', 'verify', '--quiet', str(path))
    list_head = [line.split()[1].removeprefix(PREFIX_HEAD)
                 for line in _git(root, 'bundle', 'list-heads', str(path)).splitlines()
                 if line.split()[1].startswith(PREFIX_HEAD)]
    if branch is None and len(list_head) != 1:
        raise ErrorRepo('The bundle holds the branches {list}; name one with --branch.'.format(
                                                        list = ', '.join(list_head) or 'none'))
    branch = branch or list_head[0]
    if branch not in list_head:
        raise ErrorRepo('The bundle holds no branch {branch}.'.format(branch = branch))

    _git(root, 'fetch', '--quiet', str(path), PREFIX_HEAD + branch)
    tip = _git(root, 'rev-parse', 'FETCH_HEAD').strip()
    if not cctool.commit.history.commits(root, [base + '..' + tip]):
        raise ErrorRepo('{branch} holds no commit that {base} does not.'.format(
                                                                branch = branch, base = base))

    try:
        _git(root, 'rebase', '--quiet', '--force-rebase', '-S', base, tip)
    except ErrorRepo as error:
        _run(root, 'rebase', '--abort')
        _run(root, 'checkout', '--quiet', base)
        raise ErrorRepo('{branch} cannot be replayed onto {base}, so nothing is landed. '
                        '{error}'.format(branch = branch, base = base, error = error)) from error

    tip         = _git(root, 'rev-parse', 'HEAD').strip()
    list_commit = cctool.commit.history.commits(root, [base + '..' + tip])
    list_found  = cctool.commit.history.failures(root, list_commit)
    _git(root, 'checkout', '--quiet', base)
    if list_found:
        raise ErrorRepo('The commits of {branch}, replayed and signed as {tip}, fail their '
                        'checks, so nothing is landed:\n{found}'.format(
                            branch = branch,
                            tip    = tip[:cctool.commit.history.LENGTH_SHORT],
                            found  = '\n'.join(list_found)))

    _git(root, 'merge', '--quiet', '--ff-only', tip)

    return [cctool.commit.history.short(root, commit) for commit in list_commit]


# -----------------------------------------------------------------------------
def sign(root: pathlib.Path, since: str | None = None) -> tuple[list[str], list[str]]:
    """
    Return the commits, as short hashes and subjects, that the current
    branch holds beyond since, once each is signed again, and the other
    branches removed because they ended at a commit that was replaced.
    since is the branch of the same name on origin if not given, so the
    commits signed are those not yet pushed. They are replayed onto
    since in a line, as dev keeps them.

    A branch that ends at one of the commits replaced holds nothing the
    current branch does not now hold, signed, so it would be left
    behind, naming the unsigned copy. It is removed.

    """

    base  = _branch(root)
    since = since or 'origin/' + base
    _refuse_changes(root)

    set_old = set(cctool.commit.history.commits(root, [since + '..HEAD']))
    if not set_old:
        return ([], [])
    try:
        _git(root, 'rebase', '--quiet', '--force-rebase', '-S', since)
    except ErrorRepo as error:
        _run(root, 'rebase', '--abort')
        raise ErrorRepo('The commits after {since} cannot be signed, so none are. '
                        '{error}'.format(since = since, error = error)) from error

    list_branch = []
    for line in _git(root, 'for-each-ref', '--format=%(refname:short) %(objectname)',
                     PREFIX_HEAD).splitlines():
        (name, commit) = line.split()
        if name != base and commit in set_old:
            _git(root, 'branch', '--quiet', '-D', name)
            list_branch.append(name)

    return ([cctool.commit.history.short(root, commit)
             for commit in cctool.commit.history.commits(root, [since + '..HEAD'])],
            list_branch)


# -----------------------------------------------------------------------------
def unsigned(root: pathlib.Path, remote: str) -> list[str]:
    """
    Return the commits, as short hashes and subjects, that the current
    branch holds beyond the branch of the same name on remote and that
    no good signature signs.

    """

    since = '{remote}/{branch}'.format(remote = remote, branch = _branch(root))
    list_commit = cctool.commit.history.commits(root, [since + '..HEAD'])

    return [cctool.commit.history.short(root, commit) for commit in list_commit
            if _git(root, 'log', '-1', '--format=%G?', commit).strip()
            not in cctool.commit.message.SET_STATUS_GOOD]


# -----------------------------------------------------------------------------
def push(root: pathlib.Path, remote: str) -> int:
    """
    Push the current branch to the branch of the same name on remote,
    and return the exit status of git push. Its output, and that of the
    pre-push hook, is shown as it comes. A branch that holds a commit
    no good signature signs is not pushed.

    """

    list_unsigned = unsigned(root, remote)
    if list_unsigned:
        raise ErrorRepo('These commits are not signed, so nothing is pushed; sign them with '
                        'cctool repo sign:\n{list}'.format(list = '\n'.join(list_unsigned)))

    return subprocess.run(['git', 'push', remote, _branch(root)], cwd = root,
                          check = False).returncode


# -----------------------------------------------------------------------------
def bundle(root: pathlib.Path, branch: str, base: str, path: pathlib.Path) -> list[str]:
    """
    Return the commits, as short hashes and subjects, that branch holds
    beyond base, once a bundle of them is written to path.

    """

    list_commit = cctool.commit.history.commits(root, [base + '..' + branch])
    if not list_commit:
        raise ErrorRepo('{branch} holds no commit that {base} does not.'.format(
                                                                branch = branch, base = base))
    _git(root, 'bundle', 'create', '--quiet', str(path), base + '..' + branch)

    return [cctool.commit.history.short(root, commit) for commit in list_commit]


# -----------------------------------------------------------------------------
def _branch(root: pathlib.Path) -> str:
    """
    Return the name of the current branch, or raise ErrorRepo if no
    branch is checked out.

    """

    name = _git(root, 'branch', '--show-current').strip()
    if not name:
        raise ErrorRepo('No branch is checked out; check out the branch to work on.')
    return name


# -----------------------------------------------------------------------------
def _refuse_changes(root: pathlib.Path) -> None:
    """
    Raise ErrorRepo if a tracked file has changes that no commit holds,
    which a replay would carry or lose.

    """

    if _git(root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ErrorRepo('Tracked files have changes that no commit holds; commit or stash '
                        'them first.')


# -----------------------------------------------------------------------------
def _git(root: pathlib.Path, *list_arg: str) -> str:
    """
    Return what git prints when run with list_arg in the repository at
    root, or raise ErrorRepo with what it said if it fails.

    """

    process = _run(root, *list_arg)
    if process.returncode:
        list_line = (process.stderr or process.stdout).strip().splitlines()
        raise ErrorRepo('git {arg} failed: {text}'.format(
            arg  = ' '.join(list_arg),
            text = '\n'.join(line for line in list_line if not line.startswith(PREFIX_HINT))))
    return process.stdout


# -----------------------------------------------------------------------------
def _run(root: pathlib.Path, *list_arg: str) -> subprocess.CompletedProcess:
    """
    Run git with list_arg in the repository at root, and return how it
    went.

    """

    return subprocess.run(['git', *list_arg], cwd = root, capture_output = True, text = True,
                          check = False)
