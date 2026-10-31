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
                        Bundle commits, to move them to the machine
                        that runs the landing queue.
description:            |
                        Commits made elsewhere, as in a remote
                        session, come to atlas as a git bundle, never
                        as patches, since git am ends a message at the
                        first --- line and so cuts off the commit
                        item. bundle makes a bundle of the commits a
                        branch holds beyond its base. On atlas they
                        are fetched into a branch and submitted to the
                        landing queue, which alone moves dev.
usage:                  |
                        cctool repo bundle BRANCH [--base REF]
                        [--output FILEPATH]
edge:                   []

...
"""


import pathlib
import subprocess

import cctool.commit.history


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


# -----------------------------------------------------------------------------
class ErrorRepo(Exception):
    """
    A step that cannot be taken, and why; the branch is left as it was.

    """


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
