"""
---

id_self:                pym_cctool.gate.result
guid_self:              pym_ef9a39537ef64674a1a3fc4f2fc61836
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate results
brief:                  |
                        Record exactly what a run of the gate over a
                        commit passed, so that a later gate of the
                        same commit can rely on it.
description:            |
                        A gate result is a JSON file in the git
                        directory, one for each commit gated, which
                        every worktree shares and no commit records.
                        It names the commit and the commit it was made
                        on, the policy of the gate, the environment it
                        ran in, each stage with whether it passed, and
                        whether the run passed. The policy is the
                        version of the rules of the gate and each
                        stage with its command, the test selection
                        included. The environment is the version of
                        python, a digest of the distributions
                        installed beside it, the version of each tool
                        the stages run, and the git blob of the lock
                        file of the commit. A result proves a pass
                        only for the same commit, policy and
                        environment, so a result from a narrower
                        selection of tests, or from another
                        environment, never stands for a wider one. The
                        log of timings stays a record of performance,
                        not evidence.
edge:                   []

...
"""


import datetime
import hashlib
import importlib.metadata
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import cctool.gate.gate


# The gate results, a directory in the git directory that each worktree
# shares, as the log of timings is, with one file for each commit gated.
# They are never committed.
#
DIR_RESULT     = 'cctool_gate_result'
SUFFIX_RESULT  = '.json'

# The version of the rules by which a gate decides, which the policy of
# a result names beside its stages. Raise it when the gate decides
# differently with the same stages, such as when a skipped test stops
# failing the test stage, so that no older result stands for a newer
# gate.
#
VERSION_POLICY = 1

# The distribution of cctool itself is left out of the environment: its
# code is that of the commit gated, which the stages run from the copy.
#
NAME_SELF      = 'cc-public'
FILE_LOCK      = 'pixi.lock'
ARG_VERSION    = '--version'
ARG_PYTHON     = '{python}'


# -----------------------------------------------------------------------------
def policy(tuple_stage: tuple) -> dict:
    """
    Return the policy of a gate that runs tuple_stage: the version of
    its rules, and each stage with the command that runs it, its test
    selection included, before the interpreter and the report are put
    in.

    """

    return {'version': VERSION_POLICY,
            'stages':  [[name, *tuple_arg] for (name, tuple_arg) in tuple_stage]}


# -----------------------------------------------------------------------------
def environment(root: pathlib.Path, commit: str, tuple_stage: tuple) -> dict:
    """
    Return the environment in which this process gates commit, of the
    repository at root, with tuple_stage: the version of python, a
    digest of each distribution installed beside it, the version that
    each tool the stages run gives, and the git blob of the lock file
    that commit holds, or None if it holds none.

    """

    list_dist = sorted('{name}=={version}'.format(name = dist.metadata['Name'],
                                                  version = dist.version)
                       for dist in importlib.metadata.distributions()
                       if dist.metadata['Name'] != NAME_SELF)
    map_tool  = {tuple_arg[0]: _version(tuple_arg[0])
                 for (_, tuple_arg) in tuple_stage if tuple_arg[0] != ARG_PYTHON}
    lock      = subprocess.run(['git', 'rev-parse', '--verify', '--quiet',
                                '{commit}:{path}'.format(commit = commit, path = FILE_LOCK)],
                               cwd = root, capture_output = True, text = True, check = False)

    return {'python':        sys.version,
            'distributions': hashlib.blake2b('\n'.join(list_dist).encode('utf-8'),
                                             digest_size = 16).hexdigest(),
            'tools':         map_tool,
            'lock':          lock.stdout.strip() or None}


# -----------------------------------------------------------------------------
def _version(name: str) -> str | None:
    """
    Return what the tool name prints when asked its version, or None if
    it cannot be found.

    """

    path = shutil.which(name)
    if path is None:
        return None
    done = subprocess.run([path, ARG_VERSION], capture_output = True, text = True, check = False)
    return (done.stdout + done.stderr).strip()


# -----------------------------------------------------------------------------
def write(root:        pathlib.Path,
          commit:      str,
          base:        str,
          tuple_stage: tuple,
          list_done:   list[tuple[str, bool, str]]) -> dict:
    """
    Return the gate result of a run of the gate over commit, of the
    repository at root, made on base, with tuple_stage, that came to
    list_done, once it is written in place of any result of commit.

    The result is written whole or not at all, so that a run stopped
    while it wrote leaves no result, and its outcome is unknown. A run
    passes when every stage passes; a skipped test fails the test
    stage, so a pass ran every test it selected.

    """

    result = {'commit':      commit,
              'base':        base,
              'time':        datetime.datetime.now(datetime.UTC).isoformat(timespec = 'seconds'),
              'policy':      policy(tuple_stage),
              'environment': environment(root, commit, tuple_stage),
              'stages':      [{'name': name, 'passed': is_passed}
                              for (name, is_passed, _) in list_done],
              'passed':      all(is_passed for (_, is_passed, _) in list_done)}

    dir_result = directory(root)
    dir_result.mkdir(parents = True, exist_ok = True)
    (handle, name) = tempfile.mkstemp(dir = dir_result, suffix = SUFFIX_RESULT)
    with os.fdopen(handle, 'w', encoding = 'utf-8') as file:
        json.dump(result, file, indent = 2, sort_keys = True)
    os.replace(name, dir_result / (commit + SUFFIX_RESULT))

    return result


# -----------------------------------------------------------------------------
def read(root: pathlib.Path, commit: str) -> dict | None:
    """
    Return the gate result of commit, of the repository at root, or None
    if there is none, or it cannot be read.

    """

    try:
        result = json.loads((directory(root) / (commit + SUFFIX_RESULT)).read_text(
                                                                        encoding = 'utf-8'))
    except (OSError, ValueError):
        return None
    return result if isinstance(result, dict) else None


# -----------------------------------------------------------------------------
def proves(root: pathlib.Path, commit: str, tuple_stage: tuple) -> bool:
    """
    Return whether a gate result shows that commit, of the repository at
    root, passed a gate whose policy is that of tuple_stage, in an
    environment the same as the one this process gates it in. A result
    from a narrower test selection, or another environment, proves
    nothing.

    """

    result = read(root, commit)

    return (result is not None
            and result.get('passed') is True
            and result.get('commit') == commit
            and result.get('policy') == policy(tuple_stage)
            and result.get('environment') == environment(root, commit, tuple_stage))


# -----------------------------------------------------------------------------
def directory(root: pathlib.Path) -> pathlib.Path:
    """
    Return the directory of the gate results of the repository at root,
    in its git directory, which each of its worktrees shares.

    """

    return cctool.gate.gate.git_dir(root) / DIR_RESULT
