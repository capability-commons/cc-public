"""
---

id_self:                pym_cc_public.check.store
guid_self:              pym_cde47779a20743ac81155e72c64f2836
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Store of verdicts
brief:                  |
                        Keep what the layout check and schema
                        validation found from one run of the checker
                        to the next.
description:            |
                        The store is a directory, named by the
                        environment variable CC_PUBLIC_STORE, which
                        the gate of a commit sets. With no store,
                        nothing is kept beyond the run. A verdict is
                        kept under the digest of the text it was found
                        in, and under a digest of the code of
                        cc_public and the versions of what it runs
                        with, so a verdict is reused only for the same
                        text checked by the same code.

                        Each kind of verdict is one JSON file. A run
                        writes back only the verdicts it used, so the
                        store holds no more than the tree needs. The
                        gate of a push sets no store: the check of
                        record finds every verdict afresh.
edge:                   []

...
"""


import functools
import hashlib
import importlib.metadata
import json
import os
import pathlib
import sys
import tempfile


ENV_STORE     = 'CC_PUBLIC_STORE'
DIR_PACKAGE   = pathlib.Path(__file__).resolve().parents[1]
TUPLE_SUFFIX  = ('.py', '.lp')
TUPLE_DIST    = ('ruamel.yaml', 'jsonschema', 'referencing', 'clingo')
SUFFIX_STORE  = '.json'
DELIM_KEY     = '\0'


# -----------------------------------------------------------------------------
def directory() -> pathlib.Path | None:
    """
    Return the directory of the store, or None if there is none.

    """

    name = os.environ.get(ENV_STORE)
    return pathlib.Path(name) if name else None


# -----------------------------------------------------------------------------
@functools.cache
def code() -> str:
    """
    Return the digest of the code that finds the verdicts: each python
    module and logic program of cc_public, and the versions of python
    and of the libraries it checks with.

    """

    digest = hashlib.blake2b(digest_size = 16)
    digest.update(sys.version.encode('utf-8'))
    for name in TUPLE_DIST:
        digest.update('{name}={version}\n'.format(
                          name = name, version = importlib.metadata.version(name)).encode())
    for path in sorted(DIR_PACKAGE.rglob('*')):
        if path.suffix in TUPLE_SUFFIX and '__pycache__' not in path.parts:
            digest.update(str(path.relative_to(DIR_PACKAGE)).encode('utf-8') + b'\0')
            digest.update(path.read_bytes() + b'\0')

    return digest.hexdigest()


# -----------------------------------------------------------------------------
def digest(text: str) -> str:
    """
    Return the digest of text, as a key of the store uses it.

    """

    return hashlib.blake2b(text.encode('utf-8'), digest_size = 16).hexdigest()


# -----------------------------------------------------------------------------
def key(*list_part: str) -> str:
    """
    Return the key of the store made of list_part.

    """

    return DELIM_KEY.join(list_part)


# -----------------------------------------------------------------------------
def load(kind: str) -> dict:
    """
    Return the verdicts of kind that the store keeps for this code,
    keyed as key makes them, or nothing if there is no store or it
    cannot be read.

    """

    dir_store = directory()
    if dir_store is None:
        return {}

    try:
        found = json.loads((dir_store / (kind + SUFFIX_STORE)).read_text(encoding = 'utf-8'))
    except (OSError, ValueError):
        return {}

    if not isinstance(found, dict) or found.get('code') != code():
        return {}

    return found.get('verdict', {})


# -----------------------------------------------------------------------------
def save(kind: str, map_verdict: dict) -> None:
    """
    Write map_verdict to the store as the verdicts of kind, in place of
    those it held. A run that cannot write the store goes on without it.

    """

    dir_store = directory()
    if dir_store is None:
        return

    text = json.dumps({'code': code(), 'verdict': map_verdict}, sort_keys = True)
    try:
        dir_store.mkdir(parents = True, exist_ok = True)
        (handle, name) = tempfile.mkstemp(dir = dir_store, suffix = SUFFIX_STORE)
        with os.fdopen(handle, 'w', encoding = 'utf-8') as file:
            file.write(text)
        os.replace(name, dir_store / (kind + SUFFIX_STORE))
    except OSError:
        return
