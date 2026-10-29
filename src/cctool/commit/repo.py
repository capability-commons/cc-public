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


import os
import pathlib
import subprocess
import sys

import cctool.commit.history
import cctool.commit.message


# The folder of the source, and the module that runs cctool, with which
# a fresh process checks the commits that land.
#
DIR_SOURCE     = 'src'
MODULE_COMMAND = 'cctool.cli.command'

# The ref of a branch, as git bundle list-heads names the heads of a
# bundle.
#
PREFIX_HEAD = 'refs/heads/'

# git's advice on what to do next, which names commands a step takes
# for itself, and is left out of what a failure says.
#
PREFIX_HINT = 'hint:'

# The suffix of a bundle file, and what stands in its name for each
# slash of a branch name, such as claude/fix, so that the file is not
# looked for in a folder that does not exist.
#
SUFFIX_BUNDLE = '.bundle'
DELIM_BRANCH  = '/'
DELIM_FILE    = '-'

# The remote whose branches sign takes as pushed when it is given no
# commit to start after.
#
REMOTE_DEFAULT = 'origin'

# The command a replay runs after each commit it makes when the author
# is reset, so that whoever replays the commits becomes their author,
# as when an agent's commits are landed by the maintainer.
#
COMMAND_RESET_AUTHOR = 'git commit --quiet --amend --no-edit --reset-author -S'


# -----------------------------------------------------------------------------
class ErrorRepo(Exception):
    """
    A step that cannot be taken, and why; the branch is left as it was.

    """


# -----------------------------------------------------------------------------
def land(root:         pathlib.Path,
         path:         pathlib.Path,
         branch:       str | None = None,
         reset_author: bool       = False,
         is_gated:     bool       = True) -> list[str]:
    """
    Return the commits, as short hashes and subjects, that the bundle at
    path holds beyond the current branch, once they are signed and the
    current branch is moved forward to them.

    The bundle's branch is the one it holds, or branch if it holds
    more. A bundle made on a commit that the current branch does not
    hold is refused, since replaying it would replay that commit too,
    unless the branch holds the same change of it and of each commit
    before it, as when the bundle it came in has landed: a replay
    leaves out a change the branch already holds.
    Its commits are replayed onto the current branch, so that a branch
    made on an older base lands as if made on this one, and each is
    signed as it is replayed. If reset_author is true, whoever replays
    them also becomes their author. They are then checked as cctool
    history check --gate checks them, which also checks, lints and
    tests the tree they come to, unless is_gated is false. A replay
    that conflicts, or a check that fails, leaves the current branch
    where it was. The check runs in a fresh process with the code the
    commits hold, since they may change the checks themselves.

    """

    base = _branch(root)
    _refuse_changes(root)

    _git(root, 'bundle', 'verify', '--quiet', str(path))
    for commit in prerequisites(path):
        if not _is_held(root, commit, base):
            raise ErrorRepo('The bundle starts after {commit}, which {base} does not hold, so '
                            'nothing is landed. Rebase the branch onto {base} where it was '
                            'made, and bundle it again.'.format(
                                commit = cctool.commit.history.short(root, commit),
                                base   = base))
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
        _git(root, *_replay(reset_author), base, tip)
    except ErrorRepo as error:
        _run(root, 'rebase', '--abort')
        _run(root, 'checkout', '--quiet', base)
        raise ErrorRepo('{branch} cannot be replayed onto {base}, so nothing is landed. '
                        '{error}'.format(branch = branch, base = base, error = error)) from error

    tip         = _git(root, 'rev-parse', 'HEAD').strip()
    list_commit = cctool.commit.history.commits(root, [base + '..' + tip])
    try:
        done = _checked(root, base + '..' + tip, is_gated)
    finally:
        _run(root, 'checkout', '--quiet', base)
    if done.returncode != 0:
        raise ErrorRepo('The commits of {branch}, replayed and signed as {tip}, fail their '
                        'checks, so nothing is landed:\n{found}'.format(
                            branch = branch,
                            tip    = tip[:cctool.commit.history.LENGTH_SHORT],
                            found  = (done.stdout + done.stderr).strip()))

    _git(root, 'merge', '--quiet', '--ff-only', tip)

    return [cctool.commit.history.short(root, commit) for commit in list_commit]


# -----------------------------------------------------------------------------
def prerequisites(path: pathlib.Path) -> list[str]:
    """
    Return the commits that the bundle at path is made on, which it
    needs and does not hold, as its header lists them.

    """

    list_commit = []

    with path.open('rb') as file:
        file.readline()
        for line in file:
            if line == b'\n':
                break
            if line.startswith(b'-'):
                list_commit.append(line[1:].split()[0].decode())

    return list_commit


# -----------------------------------------------------------------------------
def _is_held(root: pathlib.Path, commit: str, base: str) -> bool:
    """
    Return whether the branch base holds commit, or the same change of
    it and of each commit before it that base does not hold, as git
    cherry finds them, so that a replay onto base replays none of them.

    """

    if _run(root, 'merge-base', '--is-ancestor', commit, base).returncode == 0:
        return True

    process = _run(root, 'cherry', base, commit)
    return process.returncode == 0 and not any(line.startswith('+')
                                               for line in process.stdout.splitlines())


# -----------------------------------------------------------------------------
def _checked(root:      pathlib.Path,
             rev_range: str,
             is_gated:  bool) -> subprocess.CompletedProcess:
    """
    Return the run of cctool history check over rev_range, with --gate
    if is_gated, in a fresh process whose python path starts at the
    source checked out at root. The commits that land may change the
    extractor and the rules together, so they are checked with their
    own code, never with the modules this process imported before they
    were checked out.

    """

    env               = dict(os.environ)
    list_path         = [str(root / DIR_SOURCE), env.get('PYTHONPATH', '')]
    env['PYTHONPATH'] = os.pathsep.join(path for path in list_path if path)

    return subprocess.run([sys.executable, '-m', MODULE_COMMAND,
                           'history', 'check', rev_range, '--root', str(root),
                           *(['--gate'] if is_gated else [])],
                          cwd = root, env = env, capture_output = True, text = True,
                          check = False)


# -----------------------------------------------------------------------------
def sign(root:         pathlib.Path,
         since:        str | None = None,
         reset_author: bool       = False) -> tuple[list[str], list[str]]:
    """
    Return the commits, as short hashes and subjects, that the current
    branch holds beyond since, once each is signed again, and the other
    branches removed because they ended at a commit that was replaced.
    If since is not given, the commits signed are those not yet pushed
    to origin, as unsigned selects them, and since is the parent of the
    oldest. They are replayed onto since in a line, as dev keeps them.
    If reset_author is true, whoever signs them also becomes their
    author.

    A branch that ends at one of the commits replaced holds nothing the
    current branch does not now hold, signed, so it would be left
    behind, naming the unsigned copy. It is removed.

    """

    base = _branch(root)
    _refuse_changes(root)

    list_arg = [since + '..HEAD'] if since else _unpushed(root, REMOTE_DEFAULT)
    list_old = cctool.commit.history.commits(root, list_arg)
    if not list_old:
        return ([], [])
    since   = since or list_old[0] + '^'
    set_old = set(list_old)
    try:
        _git(root, *_replay(reset_author), since)
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
    branch holds and remote does not, as _unpushed selects them, and
    that no good signature signs.

    """

    list_commit = cctool.commit.history.commits(root, _unpushed(root, remote))

    return [cctool.commit.history.short(root, commit) for commit in list_commit
            if _git(root, 'log', '-1', '--format=%G?', commit).strip()
            not in cctool.commit.message.SET_STATUS_GOOD]


# -----------------------------------------------------------------------------
def _unpushed(root: pathlib.Path, remote: str) -> list[str]:
    """
    Return the arguments of git rev-list that select the commits the
    current branch holds and remote does not: those beyond the branch
    of the same name on remote or, where remote has no such branch yet,
    those on none of its branches, as the pre-push hook selects them.

    """

    since = '{remote}/{branch}'.format(remote = remote, branch = _branch(root))
    if _run(root, 'rev-parse', '--verify', '--quiet', 'refs/remotes/' + since).returncode:
        return ['HEAD', '--not', '--remotes=' + remote]
    return [since + '..HEAD']


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
def bundle_path(root: pathlib.Path, branch: str) -> pathlib.Path:
    """
    Return the bundle file that cctool repo bundle writes for branch by
    default: beside the repository at root, named for the branch with
    each slash written as a hyphen.

    """

    return root.parent / (branch.replace(DELIM_BRANCH, DELIM_FILE) + SUFFIX_BUNDLE)


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
def _replay(reset_author: bool) -> list[str]:
    """
    Return the arguments of git that replay commits, each signed, and
    each with whoever replays it as its author if reset_author is true.

    """

    list_arg = ['rebase', '--quiet', '--force-rebase', '-S']
    if reset_author:
        list_arg.extend(['--exec', COMMAND_RESET_AUTHOR])
    return list_arg


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
