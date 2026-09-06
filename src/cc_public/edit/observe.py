"""
---

id_self:                pym_cc_public.edit.observe
guid_self:              pym_58694ae0420845bdb2b9df2929ec658d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Observation import
brief:                  |
                        Makes an observation item from a capture of a
                        public source, deterministically.
description:            |
                        Reads a capture in the platform-neutral form,
                        canonicalises its text, digests it, and makes
                        the observation item with the content as
                        captured, the locator, the attribution, the
                        times and the digest. A capture whose digest
                        an observation already carries is reused. No
                        model takes part, and nothing the content says
                        is acted on.
relation:               []

...
"""


import contextlib
import datetime
import hashlib
import re
import unicodedata

import cc_public.edit.field
import cc_public.edit.new
import cc_public.edit.tree


ID_TYPE          = 't_observation'
PREFIX           = 'obs'
DIR_OBSERVATION  = 'observation'
SCHEMA_VERSION   = 1
KEY_ID_SELF      = 'id_self'
KEY_DIGEST       = 'content_digest'
KEY_CONTENT      = 'content'
KEY_NOTE         = 'note'
CAPTURE_REQUIRED = ('schema_version', 'source_kind', 'source_uri', 'text', 'captured_at')
CAPTURE_METHOD   = 'supplied_scrape'
ALGORITHM        = 'sha256'
SEPARATOR        = '_'


# -----------------------------------------------------------------------------
def observe(tree, capture, id_self = None, title = None, dirpath_out = None):
    """
    Make an observation item from a capture, in the platform-neutral
    form, and return (item, is_new). A capture whose digest an
    observation already carries returns that observation, so that a
    retried import is not a second, independent-looking source.

    The importer does nothing the content says: the text is stored as
    it was, canonicalised only for the digest, and the item's marking
    comes from the tree's defaults, never from the capture.

    """

    _validate(capture)

    attribution = _attribution(capture)
    canonical   = canonicalise(capture['text'])
    digest      = digest_of(capture, attribution, canonical)
    found       = _by_digest(tree, digest)

    if found is not None:
        return (found, False)

    id_self = id_self or _id_default(capture)
    title   = title or _title_default(capture, attribution)
    cc_public.edit.new.new(tree, ID_TYPE, id_self, tree.defaults(),
                           dirpath_out = dirpath_out or tree.root / DIR_OBSERVATION)

    for (field, value) in (('title',          title),
                           ('source_kind',    capture['source_kind']),
                           ('source_uri',     capture['source_uri']),
                           ('attribution',    attribution),
                           ('published_at',   capture.get('published_at')),
                           ('observed_at',    capture['captured_at']),
                           ('capture_method', capture.get('capture_method', CAPTURE_METHOD)),
                           (KEY_DIGEST,       digest)):
        if value is not None:
            cc_public.edit.field.set_field(tree, id_self, field, value = value)

    cc_public.edit.field.set_field(tree, id_self, KEY_CONTENT, prose = canonical)

    if capture.get(KEY_NOTE):
        cc_public.edit.field.set_field(tree, id_self, KEY_NOTE, prose = capture[KEY_NOTE])

    return (tree.resolve(id_self), True)


# -----------------------------------------------------------------------------
def canonicalise(text):
    """
    Return the text in the one form that is digested and stored: its
    words and its paragraphs. Unicode NFC; a run of whitespace within
    a paragraph, newlines included, becomes one space; paragraphs,
    separated by a blank line, stay separate. That is what the printer
    preserves when it refills prose, so the stored content digests the
    same as the capture. Anything else a platform adds around the words
    is not the words.

    """

    text       = unicodedata.normalize('NFC', str(text)).replace('\r\n', '\n').replace('\r', '\n')
    paragraphs = [' '.join(block.split()) for block in re.split(r'\n\s*\n', text)]

    return '\n\n'.join(block for block in paragraphs if block)


# -----------------------------------------------------------------------------
def digest_of(capture, attribution, canonical):
    """
    Return the digest that names this capture: over the contract
    version, the locator, the attribution, the publication time and
    the canonical text, so that the same post captured twice digests
    the same and an edited post does not.

    """

    parts = [str(capture['schema_version']), capture['source_uri'], attribution,
             capture.get('published_at') or '', canonical]

    return ALGORITHM + ':' + hashlib.sha256('\n'.join(parts).encode('utf-8')).hexdigest()


# -----------------------------------------------------------------------------
def _validate(capture):
    """
    Refuse a capture that is not the contract.

    """

    if not isinstance(capture, dict):
        raise cc_public.edit.tree.ErrorItem('A capture is a mapping.')

    missing = [key for key in CAPTURE_REQUIRED if not capture.get(key)]
    if missing:
        raise cc_public.edit.tree.ErrorItem(
                'The capture lacks {keys}.'.format(keys = ', '.join(missing)))

    if capture['schema_version'] != SCHEMA_VERSION:
        raise cc_public.edit.tree.ErrorItem(
                'The capture is version {v}; this importer reads version {ours}.'.format(
                        v = capture['schema_version'], ours = SCHEMA_VERSION))

    if not _attribution(capture):
        raise cc_public.edit.tree.ErrorItem(
                'The capture names no author: give author_handle, author_display or '
                'attribution.')


# -----------------------------------------------------------------------------
def _attribution(capture):
    """
    Return how the source attributes itself, as one line.

    """

    text = capture.get('author_handle') or capture.get('author_display') \
           or capture.get('attribution') or ''

    return ' '.join(str(text).split())


# -----------------------------------------------------------------------------
def _by_digest(tree, digest):
    """
    Return the observation carrying this digest, or None.

    """

    for item in tree.map_id.values():
        if item.path or item.id_self.split(SEPARATOR, 1)[0] != PREFIX:
            continue
        if tree.context.map_document[item.location].get(KEY_DIGEST) == digest:
            return item

    return None


# -----------------------------------------------------------------------------
def _id_default(capture):
    """
    Return the readable id a capture gets when none is given: the
    platform and post id, or the tail of the locator.

    """

    where = capture['source_uri'].rstrip('/').rsplit('/', 1)[-1]
    tail  = '{p}_{i}'.format(p = capture.get('platform') or capture['source_kind'],
                             i = capture.get('post_id') or where)
    slug = re.sub(r'[^a-z0-9]+', '_', tail.lower()).strip('_')

    return PREFIX + SEPARATOR + (slug or 'capture')


# -----------------------------------------------------------------------------
def _title_default(capture, attribution):
    """
    Return the title a capture gets when none is given.

    """

    kind = capture['source_kind'].replace('_', ' ').capitalize()
    when = capture.get('published_at')

    if when:
        with contextlib.suppress(ValueError):
            when = datetime.datetime.fromisoformat(when).strftime('%-d %B %Y')

    return '{kind} by {who}{when}'.format(kind = kind, who = attribution,
                                          when = ', ' + when if when else '')
