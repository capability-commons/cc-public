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
                        A commit record lives in the message of the
                        commit it describes: a plain first line, a
                        blank line, and a YAML document between the
                        markers a docstring uses. Reads one message
                        into its document, and walks the log for every
                        commit that carries one.

...
"""


import subprocess
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
