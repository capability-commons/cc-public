"""
---

id_self:                pym_cctool.queue.bundle
guid_self:              pym_1d82614a15d2487a813f57c710285f89
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Bundles of the landing queue
brief:                  |
                        Bundle a patch where the queue cannot be
                        reached, and submit bundles to it, from a file
                        or from the inbox the daemon sweeps.
description:            |
                        A remote session cannot reach the queue on
                        atlas, only a shared folder. make writes the
                        commits of a patch beyond dev as a git bundle
                        that holds one ref,
                        refs/cctool-bundle/THREAD/ID_PATCH, which
                        names the thread and the patch, so that no
                        other file need travel with it, and writes it
                        whole or not at all. submit verifies a bundle
                        against the repository, fetches its commits
                        and submits them as a branch is submitted, so
                        that a bundle that overlaps a patch in the
                        queue is refused in the same way. sweep
                        submits each bundle in the inbox that git
                        config queue.inbox names, at each run of the
                        daemon, and moves it to the folder processed
                        under its key, or to the folder rejected with
                        a note that says why.
edge:                   []

...
"""


import datetime
import os
import pathlib
import shutil

import cctool.queue.patch


# The ref that a bundle of the queue holds, which names the thread and
# the patch, so that the queue can submit the bundle with no other file
# beside it.
#
PREFIX_REF     = 'refs/cctool-bundle/'
SUFFIX_BUNDLE  = '.bundle'
SUFFIX_PART    = '.part'
SUFFIX_NOTE    = '.txt'
DELIM_FILE     = '-'

# The folders of the inbox that a bundle is moved to once the daemon has
# taken it in, or has refused it.
#
DIR_PROCESSED  = 'processed'
DIR_REJECTED   = 'rejected'


# -----------------------------------------------------------------------------
def make(root:     pathlib.Path,
         id_patch: str,
         source:   str = 'HEAD',
         thread:   str | None = None,
         base:     str = cctool.queue.patch.DEV,
         path:     pathlib.Path | None = None) -> tuple[pathlib.Path, list[str]]:
    """
    Return the bundle file of the commits that source holds beyond base,
    in the repository at root, as the patch id_patch of thread, and those
    commits as short hashes and subjects, once it is written.

    The bundle holds one ref, which names the thread and the patch, and
    needs base, which whoever submits it must have. It is written to
    path, or else to the inbox that git config queue.inbox names, or
    else beside the repository, as THREAD-ID_PATCH.bundle. It is written
    under another name and then renamed, so that a daemon sweeping the
    inbox never reads one half written.

    """

    thread = thread or cctool.queue.patch.current_thread(root)
    _check_names(thread, id_patch)
    tip         = cctool.queue.patch.rev(root, source)
    list_commit = cctool.queue.patch.commits(root, tip, '--not', base)
    if not list_commit:
        raise cctool.queue.patch.ErrorQueue('{source} holds no commit that {base} does not, so '
                                            'there is nothing to bundle.'.format(source = source,
                                                                                  base   = base))

    name = '{thread}{delim}{patch}{suffix}'.format(thread = thread, delim = DELIM_FILE,
                                                  patch = id_patch, suffix = SUFFIX_BUNDLE)
    if path is None:
        inbox = cctool.queue.patch.try_git(root, 'config', '--get', 'queue.inbox').stdout.strip()
        path  = (pathlib.Path(inbox) if inbox else root.parent) / name

    ref  = ref_of(thread, id_patch)
    part = path.with_name(path.name + SUFFIX_PART)
    cctool.queue.patch.git(root, 'update-ref', ref, tip)
    try:
        cctool.queue.patch.git(root, 'bundle', 'create', '--quiet', str(part),
                               '{base}..{ref}'.format(base = base, ref = ref))
        os.replace(part, path)
    finally:
        cctool.queue.patch.try_git(root, 'update-ref', '-d', ref)
        part.unlink(missing_ok = True)

    return (path, [cctool.queue.patch.git(root, 'log', '-1', '--format=%h %s',
                                          commit).strip() for commit in list_commit])


# -----------------------------------------------------------------------------
def submit(root:  pathlib.Path,
           path:  pathlib.Path,
           agent: str | None = None,
           now:   datetime.datetime | None = None) -> dict:
    """
    Return the record of the patch that the bundle at path holds, once it
    is submitted to the queue of the repository at root as a branch is,
    under the thread and patch its ref names. A file that is not a
    bundle, a bundle that cctool queue bundle did not make, and one made
    on a commit the repository lacks are refused, as is one that
    overlaps a patch in the queue.

    """

    (thread, id_patch) = read(root, path)
    ref = ref_of(thread, id_patch)
    cctool.queue.patch.git(root, 'fetch', '--quiet', '--no-tags', str(path),
                           '+{ref}:{ref}'.format(ref = ref))
    try:
        tip = cctool.queue.patch.rev(root, ref)
        return cctool.queue.patch.submit(root, id_patch, tip, thread, agent, now,
                                         bundle = path.name)
    finally:
        cctool.queue.patch.try_git(root, 'update-ref', '-d', ref)


# -----------------------------------------------------------------------------
def read(root: pathlib.Path, path: pathlib.Path) -> tuple[str, str]:
    """
    Return the thread and the patch that the bundle at path names, once
    git has verified it against the repository at root, or raise
    ErrorQueue saying why it cannot be submitted.

    """

    done = cctool.queue.patch.try_git(root, 'bundle', 'verify', '--quiet', str(path))
    if done.returncode:
        raise cctool.queue.patch.ErrorQueue(
            '{name} cannot be submitted: it is not a bundle, or it is made on a commit that this '
            'repository lacks. Make it again with cctool queue bundle, on dev as it is '
            'here.\n{said}'.format(name = path.name, said = (done.stderr or done.stdout).strip()))

    list_ref = [line.split()[1] for line
                in cctool.queue.patch.git(root, 'bundle', 'list-heads', str(path)).splitlines()
                if len(line.split()) == 2]
    list_part = [ref.removeprefix(PREFIX_REF).split('/') for ref in list_ref
                 if ref.startswith(PREFIX_REF)]
    if len(list_ref) != 1 or len(list_part) != 1 or len(list_part[0]) != 2:
        raise cctool.queue.patch.ErrorQueue(
            '{name} was not made by cctool queue bundle: it holds {refs}, not one ref under '
            '{prefix}THREAD/ID_PATCH.'.format(name   = path.name,
                                              refs   = ', '.join(list_ref) or 'no ref',
                                              prefix = PREFIX_REF))
    (thread, id_patch) = list_part[0]
    _check_names(thread, id_patch)
    return (thread, id_patch)


# -----------------------------------------------------------------------------
def sweep(root:  pathlib.Path,
          inbox: pathlib.Path,
          now:   datetime.datetime | None = None) -> list[str]:
    """
    Return a line for each bundle in the folder inbox, oldest first, once
    each is submitted to the queue of the repository at root and moved
    to the folder processed in inbox under the key of its patch, or, if
    it cannot be submitted, moved to the folder rejected with a note
    beside it that says why.

    """

    list_line = []
    list_path = sorted(inbox.glob('*' + SUFFIX_BUNDLE), key = lambda path: path.stat().st_mtime)

    for path in list_path:
        try:
            record = submit(root, path, agent = 'inbox', now = now)
        except cctool.queue.patch.ErrorQueue as error:
            stamp = cctool.queue.patch.stamp([], now)
            moved = _move(path, inbox / DIR_REJECTED, '{stamp}_{name}'.format(stamp = stamp,
                                                                            name  = path.name))
            moved.with_name(moved.name + SUFFIX_NOTE).write_text(str(error) + '\n',
                                                                 encoding = 'utf-8')
            list_line.append('{name} was refused, and moved to {folder}: {error}'.format(
                                 name   = path.name,
                                 folder = DIR_REJECTED,
                                 error  = str(error).splitlines()[0]))
            continue
        _move(path, inbox / DIR_PROCESSED, record['key'] + SUFFIX_BUNDLE)
        list_line.append('{name} was submitted as {branch}.'.format(
                             name = path.name, branch = cctool.queue.patch.branch(record)))

    return list_line


# -----------------------------------------------------------------------------
def rejected(inbox: pathlib.Path, day: datetime.date) -> list[tuple[str, str]]:
    """
    Return each bundle that the sweep of inbox refused on day, by the
    name it is kept under, with the first line of why.

    """

    dir_rejected = inbox / DIR_REJECTED
    if not dir_rejected.is_dir():
        return []

    prefix = day.strftime('%Y%m%d')
    return [(path.name.removesuffix(SUFFIX_NOTE),
             path.read_text(encoding = 'utf-8').splitlines()[0])
            for path in sorted(dir_rejected.glob('*' + SUFFIX_BUNDLE + SUFFIX_NOTE))
            if path.name.startswith(prefix)]


# -----------------------------------------------------------------------------
def ref_of(thread: str, id_patch: str) -> str:
    """
    Return the ref that a bundle of the patch id_patch of thread holds.

    """

    return '{prefix}{thread}/{patch}'.format(prefix = PREFIX_REF, thread = thread,
                                             patch = id_patch)


# -----------------------------------------------------------------------------
def _check_names(thread: str, id_patch: str) -> None:
    """
    Raise ErrorQueue unless thread and id_patch are each one segment of a
    branch name.

    """

    for (what, name) in (('thread', thread), ('patch', id_patch)):
        if not cctool.queue.patch.PATTERN_NAME.fullmatch(name):
            raise cctool.queue.patch.ErrorQueue(
                'The name of the {what}, {name}, is not one segment of letters, digits, hyphens '
                'and underscores.'.format(what = what, name = name))


# -----------------------------------------------------------------------------
def _move(path: pathlib.Path, folder: pathlib.Path, name: str) -> pathlib.Path:
    """
    Return where the file at path is, once moved into folder as name.

    """

    folder.mkdir(parents = True, exist_ok = True)
    return pathlib.Path(shutil.move(str(path), str(folder / name)))
