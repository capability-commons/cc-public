"""
---

id_self:                pym_cc_public.load.git
guid_self:              pym_7dcf1d243d8d4c3facdd4b5527f4cd24
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Git loader
brief:                  |
                        Read the commit records held in a repository's
                        history.
description:            |
                        The one place git is run: a runner that
                        reports a failure one way for every caller,
                        the commit checked out, and the files changed
                        since a commit. Reads a commit record out of a
                        message, a plain first line, a blank line, and
                        a YAML document between the markers a
                        docstring uses, and walks the log for every
                        commit that carries one.
relation:               []

...
"""


import subprocess
import pathlib
import typing

import ruamel.yaml


ENCODING_DEFAULT = 'utf-8'

MARKER_OPEN      = '---'
MARKER_CLOSE     = '...'

# Separators git will never put in a message.
#
SEP_COMMIT       = '\x1e'
SEP_FIELD        = '\x1f'


# -----------------------------------------------------------------------------
class Commit(typing.NamedTuple):
    """
    One commit and what its message holds.

    document is None where the message carries no record.

    """

    hash:     str
    title:    str
    document: typing.Any
    message:  str


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the record a commit message holds, or None where it holds none.

    """

    if encoding is None:
        encoding = ENCODING_DEFAULT

    return parse(data.decode(encoding))[1]


# -----------------------------------------------------------------------------
def parse(message):
    """
    Return (first line, document or None) for a commit message.

    The markers must stand alone on their lines, as they must in a
    docstring, so that a line of prose that happens to contain one
    does not open or close anything.

    """

    list_line = message.splitlines()
    title     = list_line[0].strip() if list_line else ''
    first     = next((i for (i, line) in enumerate(list_line)
                        if line.strip() == MARKER_OPEN), None)

    if first is None:
        return (title, None)

    last = next((i for i in range(first + 1, len(list_line))
                   if list_line[i].strip() == MARKER_CLOSE), None)

    if last is None:
        return (title, None)

    text = '\n'.join(list_line[first + 1 : last]) + '\n'

    return (title, ruamel.yaml.YAML(typ = 'safe').load(text))


# -----------------------------------------------------------------------------
class ErrorGit(Exception):
    """
    Raised where git could not do what was asked.

    """



# -----------------------------------------------------------------------------
def git(root, *args, input = None):
    """
    Run one git command at root and return its output, or raise
    ErrorGit with what git said.

    The one place git is run, so that every caller reports its failure
    the same way and none runs it by another path.

    """

    import subprocess

    try:
        done = subprocess.run(['git', '-C', str(root), *args],
                              capture_output = True, text = True, input = input,
                              check = False)
    except OSError as err:
        raise ErrorGit('git could not be run: {err}'.format(err = err)) from err

    if done.returncode != 0:
        raise ErrorGit('git {args}: {err}'.format(args = ' '.join(args[:2]),
                                                  err  = done.stderr.strip()))

    return done.stdout


# -----------------------------------------------------------------------------
def revision(root):
    """
    Return the commit checked out at root, or None where there is none.

    """

    try:
        return git(root, 'rev-parse', 'HEAD').strip()
    except ErrorGit:
        return None


# -----------------------------------------------------------------------------
def changed_since(root, ref):
    """
    Return the files under root changed since ref, committed or not,
    as resolved paths: what a diff against ref touches, and what the
    working tree has changed or added since.

    """

    root  = pathlib.Path(root).resolve()
    names = set(git(root, 'diff', '--name-only', ref, '--').split('\n'))

    for line in git(root, 'status', '--porcelain=v1', '-z',
                    '--untracked-files=all').split('\0'):
        if len(line) > 3:
            names.add(line[3:])

    return {root / name for name in names if name}


# -----------------------------------------------------------------------------
def iter_commit(root, count = None):
    """
    Yield a Commit for each commit in the history of root, newest first.

    """

    command = ['git', '-C', str(root), 'log',
               '--format=%H' + SEP_FIELD + '%B' + SEP_COMMIT]

    if count is not None:
        command.append('-n{count}'.format(count = count))

    text = subprocess.run(command, capture_output = True, text = True,
                          check = True).stdout

    for chunk in text.split(SEP_COMMIT):

        if SEP_FIELD not in chunk:
            continue

        (hash, message) = chunk.lstrip('\n').split(SEP_FIELD, 1)
        (title, document) = parse(message)

        yield Commit(hash = hash.strip(), title = title,
                     document = document, message = message)
