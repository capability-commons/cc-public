"""
---

id_self:                pym_cc_public.glossary
guid_self:              pym_dadc95ddc6ad4d4bb610b980d0cbb45b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Glossary projection
brief:                  |
                        What the glossaries in a tree hold, what more
                        than one entry claims, and what prose names
                        that no glossary defines.
description:            |
                        Three readings of the term registers a tree
                        holds. A lookup returns every entry that
                        claims a word, since a word may name several
                        concepts. A sense report names the words more
                        than one entry claims and the readable ids
                        that distinguish a sense by a digit rather
                        than by words. A gap report counts the words
                        prose uses across items and keeps those no
                        glossary defines, which is a candidate list
                        for a person and never a finding.

                        Prose is a string held as a block scalar,
                        which is what the layout convention makes
                        prose. A plain scalar is a datum and is passed
                        over.
relation:               []

...
"""


import collections
import functools
import re
import typing

import cc_public.item


FIELD_NOT_PROSE = ('subject', 'sql', 'example')
KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_TERM      = 'term'
KEY_ALSO      = 'also'
KEY_AVOID     = 'avoid'
KEY_TITLE     = 'title'
KEY_BRIEF     = 'brief'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_GUID_TGT  = 'guid_target'

PREFIX_TERM   = 'term'
REL_DECIDES   = 'r_decides'
MINIMUM       = 10
LENGTH_WORD   = 3

# An identifier: a prefixed readable id, a dotted source id, or a guid.
# Removed before prose is read as words, so that id_term does not read
# as id and term.
#
RE_IDENTIFIER = re.compile(r'\b[a-z][a-z0-9]*[_.][a-z0-9_.]+\b')
RE_WORD       = re.compile(r"[a-z]+(?:'[a-z]+)?")
RE_DIGIT      = re.compile(r'[0-9]$')

# Words that carry no concept. Kept short: a word this list does not
# hold and no glossary defines is a candidate for a person to judge,
# and a long list decides that judgement in advance.
#
STOP          = frozenset((
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'also', 'an', 'and', 'another',
    'any', 'anything', 'are', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below',
    'between', 'both', 'but', 'by', 'came', 'can', 'cannot', 'could', 'did', 'do', 'does',
    'doing', 'done', 'down', 'during', 'each', 'either', 'else', 'enough', 'even', 'ever',
    'every', 'everything', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having',
    'her', 'here', 'hers', 'him', 'his', 'how', 'however', 'if', 'in', 'into', 'is', 'it',
    'its', 'itself', 'just', 'least', 'less', 'like', 'made', 'make', 'makes', 'many', 'may',
    'me', 'might', 'more', 'most', 'much', 'must', 'my', 'neither', 'never', 'no', 'nor',
    'not', 'nothing', 'now', 'of', 'off', 'on', 'once', 'one', 'only', 'onto', 'or', 'other',
    'others', 'ought', 'our', 'out', 'over', 'own', 'per', 'rather', 'said', 'same', 'say',
    'says', 'several', 'shall', 'she', 'should', 'since', 'so', 'some', 'something', 'still',
    'such', 'than', 'that', 'the', 'their', 'theirs', 'them', 'then', 'there', 'these', 'they',
    'thing', 'things', 'this', 'those', 'though', 'three', 'through', 'thus', 'to', 'too',
    'two', 'under', 'until', 'up', 'upon', 'us', 'use', 'used', 'uses', 'using', 'very', 'was',
    'way', 'we', 'were', 'what', 'when', 'where', 'whether', 'which', 'while', 'who', 'whom',
    'whose', 'why', 'will', 'with', 'within', 'without', 'would', 'yet', 'you', 'your'))


# -----------------------------------------------------------------------------
class Term(typing.NamedTuple):
    """
    One term entry: the concept it identifies, and the words used for
    it.

    """

    id_self:  str
    guid:     str
    title:    str
    brief:    str
    term:     str
    also:     tuple
    avoid:    tuple
    decider:  tuple


# -----------------------------------------------------------------------------
def terms(map_document):
    """
    Return one Term per entry of every term register in the tree, by
    readable id.

    """

    map_decider = _map_decider(map_document)
    out         = []

    for entry in _iter_entry(map_document):

        id_self = str(entry.get(KEY_ID_SELF) or '')

        out.append(Term(id_self = id_self,
                        guid    = str(entry.get(KEY_GUID_SELF) or ''),
                        title   = _flat(entry.get(KEY_TITLE)),
                        brief   = _flat(entry.get(KEY_BRIEF)),
                        term    = _flat(entry.get(KEY_TERM)),
                        also    = tuple(_flat(w) for w in entry.get(KEY_ALSO) or ()),
                        avoid   = tuple(_flat(w) for w in entry.get(KEY_AVOID) or ()),
                        decider = tuple(sorted(map_decider.get(
                                        str(entry.get(KEY_GUID_SELF) or ''), ())))))

    return tuple(sorted(out))


# -----------------------------------------------------------------------------
def lookup(map_document, word):
    """
    Return (list_accepted, list_avoided) for one word.

    A word may name several concepts, so both are lists. A word under
    avoid is returned as well, since what to write instead is the
    entry that rejects it.

    """

    wanted   = _flat(word).lower()
    accepted = []
    avoided  = []

    for term in terms(map_document):
        if wanted in {term.term.lower(), *(w.lower() for w in term.also)}:
            accepted.append(term)
        elif wanted in {w.lower() for w in term.avoid}:
            avoided.append(term)

    return (tuple(accepted), tuple(avoided))


# -----------------------------------------------------------------------------
def senses(map_document):
    """
    Return (list_shared, list_numbered).

    list_shared is one (word, list_id) per word more than one entry
    claims, which is the state a lookup must handle. list_numbered is
    every entry whose readable id ends in a digit, which is the state
    a readable id distinguishing a sense in words does not reach.

    """

    map_word = collections.defaultdict(list)
    numbered = []

    for term in terms(map_document):

        for word in {term.term.lower(), *(w.lower() for w in term.also)}:
            map_word[word].append(term.id_self)

        if RE_DIGIT.search(term.id_self):
            numbered.append(term.id_self)

    shared = tuple((word, tuple(sorted(list_id)))
                   for (word, list_id) in sorted(map_word.items())
                   if len(list_id) > 1)

    return (shared, tuple(sorted(numbered)))


# -----------------------------------------------------------------------------
def gaps(map_document, minimum = MINIMUM):
    """
    Return (list_word, list_pair, list_undecided).

    list_word and list_pair are one (phrase, count_item) per single
    word and per pair of neighbouring words that the prose of at least
    minimum items uses and that no glossary defines or rejects, most
    used first. The two are apart because a pair names a concept far
    more often than a word does, and a pair counted with the words
    would sit below all of them.

    Both are candidate lists for a person, never findings: a word is
    not a concept because it is common.

    list_undecided is every term entry no record decides, which
    ddr_glossary asks for and no check reports.

    """

    known     = _known(map_document)
    map_count = collections.defaultdict(set)

    for document in map_document.values():
        for (id_item, text) in _iter_prose(document):
            for phrase in _phrases(text):
                map_count[phrase].add(id_item)

    counted = sorted(((phrase, len(set_item))
                      for (phrase, set_item) in map_count.items()
                      if len(set_item) >= minimum and not _is_known(phrase, known)),
                     key = lambda row: (-row[1], row[0]))

    undecided = tuple(term.id_self for term in terms(map_document) if not term.decider)

    return (tuple(row for row in counted if ' ' not in row[0]),
            tuple(row for row in counted if ' ' in row[0]),
            undecided)


# -----------------------------------------------------------------------------
def _known(map_document):
    """
    Return every word and phrase a glossary in the tree holds, lower
    case: the terms, the other accepted forms, and the rejected ones.

    """

    out = set()

    for term in terms(map_document):
        out.update(w.lower() for w in (term.term, *term.also, *term.avoid) if w)

    return frozenset(out)


# -----------------------------------------------------------------------------
@functools.lru_cache(maxsize = 8)
def _within(known):
    """
    Return every run of words inside a term a glossary holds.

    A pair inside a longer term names no concept of its own, and
    reporting it presents the glossary's own terms back as candidates
    (ddr_glossary).

    """

    out = set()

    for phrase in known:
        word = phrase.split()
        for start in range(len(word)):
            for stop in range(start + 1, len(word) + 1):
                out.add(' '.join(word[start:stop]))

    return frozenset(out)


# -----------------------------------------------------------------------------
def _is_known(phrase, known):
    """
    Return whether a glossary holds the phrase, holds it in the
    singular, or holds a longer term the phrase is a run of words
    within. A plural is the same word.

    """

    if phrase in known or phrase in _within(known):
        return True

    (head, _, last) = phrase.rpartition(' ')

    for (suffix, ending) in (('ies', 'y'), ('sses', 'ss'), ('es', ''), ('s', '')):
        if last.endswith(suffix):
            singular = last[:-len(suffix)] + ending
            if (head + ' ' + singular if head else singular) in known:
                return True

    return False


# -----------------------------------------------------------------------------
def _phrases(text):
    """
    Yield every word and every pair of neighbouring words in the text,
    lower case, with identifiers, stop words and short words left out.

    A pair is yielded whenever neither of its words is a stop word, so
    that control case is counted although case alone is common.

    """

    tokens = RE_WORD.findall(RE_IDENTIFIER.sub(' ', text.lower()))

    for (n, word) in enumerate(tokens):

        if word not in STOP and len(word) >= LENGTH_WORD:
            yield word

        if n + 1 < len(tokens) and word not in STOP and tokens[n + 1] not in STOP:
            yield word + ' ' + tokens[n + 1]


# -----------------------------------------------------------------------------
def _iter_prose(node, id_item = None):
    """
    Yield (id_item, text) for every string held as a block scalar,
    which is what the layout convention makes prose. A plain scalar is
    a datum and says nothing about the words a repository uses.

    A field named in FIELD_NOT_PROSE is a datum written as a block
    scalar because it holds line breaks, not because it is prose
    (ddr_glossary).

    """

    if isinstance(node, dict):

        if isinstance(node.get(KEY_ID_SELF), str):
            id_item = node[KEY_ID_SELF]

        for (key, value) in node.items():
            if key not in FIELD_NOT_PROSE:
                yield from _iter_prose(value, id_item)

    elif isinstance(node, list):

        for value in node:
            yield from _iter_prose(value, id_item)

    elif isinstance(node, str) and '\n' in node and id_item is not None:

        yield (id_item, node)


# -----------------------------------------------------------------------------
def _iter_entry(map_document):
    """
    Yield every entry of every term register in the tree.

    """

    return cc_public.item.iter_entry(map_document, PREFIX_TERM)


# -----------------------------------------------------------------------------
def _map_decider(map_document):
    """
    Return {guid of term: [id of every record deciding it]}.

    """

    out = collections.defaultdict(list)

    for document in map_document.values():
        for (id_self, edge) in _iter_edge(document):
            if edge.get(KEY_ID_REL) == REL_DECIDES:
                out[edge.get(KEY_GUID_TGT)].append(id_self)

    return out


# -----------------------------------------------------------------------------
def _iter_edge(node, id_self = None):
    """
    Yield (id_self of the holder, edge) for every edge in the node.

    """

    if isinstance(node, dict):

        if isinstance(node.get(KEY_ID_SELF), str):
            id_self = node[KEY_ID_SELF]

        for (key, value) in node.items():
            if key == KEY_RELATION and isinstance(value, list):
                for edge in value:
                    if isinstance(edge, dict):
                        yield (id_self, edge)
            else:
                yield from _iter_edge(value, id_self)

    elif isinstance(node, list):

        for value in node:
            yield from _iter_edge(value, id_self)


# -----------------------------------------------------------------------------
def _flat(value):
    """
    Return a string with its whitespace collapsed.

    """

    return ' '.join(str(value or '').split())
