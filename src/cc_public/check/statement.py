"""
---

id_self:                pym_cc_public.check.statement
guid_self:              pym_61abdd2b32184cb1b4fc4e1c1e16523f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Statement check
brief:                  |
                        Check what a check can tell of a requirement
                        statement: its quantities carry units and
                        bounds, its acronyms are defined, and its verb
                        names a process.
description:            |
                        Reads the object and qualifier slots of every
                        requirement and candidate. A number is
                        followed by a unit the unit register holds, by
                        the thing it counts, or by nothing, which is a
                        finding; a number with a unit and no bound
                        before it is a point value, which is a
                        question; a unit the register lacks is a
                        question. An acronym no glossary defines is a
                        finding. A process word whose entry names a
                        state, a permission or a management word
                        rather than a process, a light verb before a
                        noun, and an object that opens with a
                        nominalised process, are the questions SOPHIST
                        asks of the verb. What was a judgement on
                        these rules is a check, and the evals that
                        judged them are narrowed to what a check
                        cannot tell.
relation:               []

...
"""


import re

import cc_public.check.requirement
import cc_public.check.result
import cc_public.requirement


ID_CHECK        = 'statement'
TITLE           = 'Statements carry units, bounds, defined acronyms and a process verb'
NOUN            = 'statement'

KEY_ID_SELF     = 'id_self'
KEY_TABLE       = 'table'
KEY_STATUS      = 'status'
KEY_SYMBOL      = 'symbol'
KEY_ALSO        = 'also'
KEY_TERM        = 'term'
KEY_KIND        = 'kind'
KEY_PROCESS     = cc_public.requirement.KEY_PROCESS
KEY_OBJECT      = cc_public.requirement.KEY_OBJECT
KEY_QUALIFIER   = cc_public.requirement.KEY_QUALIFIER
PREFIX_UNIT     = 'unit'
PREFIX_VERB     = 'verb'
PREFIX_TERM     = 'term'
PREFIX_DOC      = 'doc'
KIND_PROCESS    = 'process'
STATUS_ACCEPTED = 'accepted'
SEPARATOR       = '_'

RULE_UNIT       = 'rule_r06_common_units'
RULE_BOUND      = 'rule_r33_range_of_values'
RULE_ACRONYM    = 'rule_r37_acronyms'
RULE_VERB       = 'rule_s02_main_verb'
RULE_POSSIBLE   = 'rule_s13_possibility'
RULE_LIGHT      = 'rule_s04_light_verb'
RULE_NOMINAL    = 'rule_s03_nominalisation'

# A number, with a space or a comma as a thousands separator, a decimal
# point, and an optional sign or tolerance mark before it.
#
RE_NUMBER       = re.compile(r'[±+-]?\d+(?:[ ,]\d{3})*(?:\.\d+)?')
RE_ACRONYM      = re.compile(r'(?<![A-Za-z0-9-])[A-Z]{2,6}(?![A-Za-z0-9-])')
RE_WORD         = re.compile(r"[A-Za-z°%][A-Za-z0-9°%/()_-]*")

# Words before a number that make it a bound, a range or a tolerance
# rather than a point value, looked for in the four words before it.
#
BOUND           = frozenset(('least', 'most', 'more', 'less', 'than', 'exceeding', 'exceed',
                             'within', 'below', 'above', 'under', 'over', 'up', 'to', 'between',
                             'minimum', 'maximum', 'from', 'or', 'fewer', 'greater', 'beyond',
                             'until', 'after', 'before', 'per', 'every', 'each', 'of', 'by',
                             'than', 'not', 'no', 'about', 'plus', 'minus'))
LIGHT           = frozenset(('perform', 'carry out', 'undertake', 'conduct', 'do', 'make',
                             'effect'))
NOT_NOMINAL     = frozenset(('the', 'a', 'an', 'each', 'every', 'all', 'any', 'its', 'no',
                             'at', 'in', 'on', 'of', 'to', 'from', 'with', 'for', 'and', 'or'))
WINDOW          = 4
AFTER           = frozenset(('or', 'maximum', 'minimum', 'at'))


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming, for every requirement and candidate, what a
    check can tell of its statement: a number no unit follows, a point
    value with no bound, a unit the register lacks, an acronym no
    glossary defines, a process word that names no process, a light
    verb, and an object that opens with a nominalised process.

    Each is what a judge was asked before; a check says it for nothing
    and says it the same way every time. Advisory while the requirement
    is proposed or a candidate, since each finding is a question to its
    author; critical once accepted.

    """

    units    = _units(context.map_document)
    verbs    = _verbs(context.map_document)
    known    = _known(context.map_document, units)
    count    = 0
    list_bad = []

    for (location, path, document) in cc_public.check.requirement.iter_subject(
                                                                context.map_document):
        count   += 1
        severe   = (cc_public.check.result.SEVERITY_CRITICAL
                    if document.get(KEY_STATUS) == STATUS_ACCEPTED
                    else cc_public.check.result.SEVERITY_ADVISORY)
        text     = ' '.join(str(document.get(KEY_OBJECT) or '').split())
        after    = ' '.join(str(document.get(KEY_QUALIFIER) or '').split())
        messages = (_quantities(text + ' ' + after, units)
                    + _acronyms(text + ' ' + after, known)
                    + _verb(document, verbs)
                    + _nominal(document, verbs))
        list_bad.extend(cc_public.check.result.Nonconformity(
                            filepath = str(location.filepath), path = path,
                            message = m, severity = severe) for m in messages)

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _quantities(text, units):
    """
    Return a message for each number the text holds that no unit and
    no counted thing follows, each point value no bound precedes, and
    each unit-like word the register lacks.

    """

    out    = []
    tokens = _tokens(text)

    for (n, token) in enumerate(tokens):
        if not RE_NUMBER.fullmatch(token) or _is_designation(tokens, n):
            continue
        following = _following(tokens, n, units)
        if following is None:
            out.append('The number {n} is followed by no unit and by nothing it counts. State '
                       'the unit. {rule}.'.format(n = token, rule = RULE_UNIT))
            continue
        (unit, is_unit) = following
        if not is_unit:
            continue                         # a count: its unit is what it counts
        before = {t.lower() for t in tokens[max(0, n - WINDOW):n]}
        after  = {t.lower() for t in tokens[n + 1:n + WINDOW]}
        if not (before & BOUND) and not (after & AFTER) \
                and not token.startswith(('±', '+', '-')):
            out.append('{n} {unit} is a point value: is it a limit, a range, or a nominal with a '
                       'tolerance? {rule}.'.format(n = token, unit = unit, rule = RULE_BOUND))

    for token in tokens:
        if _looks_like_unit(token) and token.lower() not in units \
                and not RE_NUMBER.fullmatch(token):
            out.append('{unit} reads as a unit and the unit register does not hold it: add it '
                       'there, or write the unit as the register has it. {rule}.'.format(
                                                    unit = token, rule = RULE_UNIT))

    return out


# -----------------------------------------------------------------------------
def _is_designation(tokens, n):
    """
    Return whether the number at n names something rather than
    measuring it: IEC 62133-2, STANAG 2895, a 24-hour period.

    """

    before = tokens[n - 1] if n else ''
    after  = tokens[n + 1] if n + 1 < len(tokens) else ''

    return (len(before) >= 2 and before.isupper()) or after == '-'


# -----------------------------------------------------------------------------
def _following(tokens, n, units):
    """
    Return (unit, True) where a unit follows the number at n, (word,
    False) where a counted thing does, and None where nothing does.
    A unit may be two words, square metres.

    """

    rest = tokens[n + 1:n + 3]

    if not rest:
        return None

    two = ' '.join(rest).lower()

    if two in units:
        return (two, True)

    one = rest[0]

    if one.lower() in units:
        return (one, True)

    if RE_NUMBER.fullmatch(one) or not RE_WORD.fullmatch(one):
        return None                          # a second number, or punctuation alone

    return (one, False)


# -----------------------------------------------------------------------------
def _looks_like_unit(token):
    """
    Return whether a token has the shape of a unit symbol: short, with
    a letter, and holding a slash, a degree sign or a mixed case that a
    word does not.

    """

    return (len(token) <= 6 and any(c.isalpha() for c in token)
            and ('/' in token or '°' in token
                 or (token[:1].islower() and any(c.isupper() for c in token[1:]))))


# -----------------------------------------------------------------------------
def _acronyms(text, known):
    """
    Return a message for each acronym, two to six capitals, that no
    glossary, document register or unit defines.

    """

    return ['The acronym {a} is not defined in a glossary the item can see: define it as a '
            'term, or write it out. {rule}.'.format(a = a, rule = RULE_ACRONYM)
            for a in sorted(set(RE_ACRONYM.findall(text)))
            if a.lower() not in known and a not in known]


# -----------------------------------------------------------------------------
def _verb(document, verbs):
    """
    Return a message where the process word's entry names a state, a
    permission or a management word rather than a process, or where
    it is a light verb whose process is the noun after it.

    """

    process = ' '.join(str(document.get(KEY_PROCESS) or '').split()).lower()
    kind    = verbs.get(process)

    if process in LIGHT:
        return ['{verb} is a light verb: the process is the noun after it. What does the '
                'entity do? {rule}.'.format(verb = process, rule = RULE_LIGHT)]

    if kind is None or kind == KIND_PROCESS:
        return []

    rule = RULE_POSSIBLE if kind == 'permission' else RULE_VERB

    return ['{verb} names a {kind}, not a process the entity performs: what does the entity '
            'do? {rule}.'.format(verb = process, kind = kind, rule = rule)]


# -----------------------------------------------------------------------------
def _nominal(document, verbs):
    """
    Return a message where the object opens with a noun made from a
    process word the register defines: the registration of, the
    calculation. A noun that is not one of a defined verb's forms is
    left alone, since only the glossary can say what stands for a
    process.

    """

    words = [w for w in re.findall(r'[a-z]+', str(document.get(KEY_OBJECT) or '').lower())
             if w not in NOT_NOMINAL]

    if not words:
        return []

    head = words[0]
    verb = next((v for v in verbs if head in _forms(v)), None)

    if verb is None:
        return []

    return ['The object opens with {noun}, a noun standing for the process {verb}: is the '
            'process written elsewhere with its own verb, or is this it? {rule}.'.format(
                                            noun = head, verb = verb, rule = RULE_NOMINAL)]


def _forms(verb):
    """
    Return the nouns a verb is commonly turned into: calculation,
    registration, judgement, listing, approval, maintenance.

    """

    stem = verb.split()[-1]
    root = stem.removesuffix('e')

    return {stem + 'ation', root + 'ation', root + 'ion', stem + 'ment', root + 'ment',
            root + 'ing', stem + 'al', root + 'al', stem + 'ance', root + 'ance', root + 'ence'}


# -----------------------------------------------------------------------------
def _tokens(text):
    """
    Split text into words, numbers and marks, a thousands group joined
    to its number, so that 10 000 kg reads as one number and a unit.

    """

    text = RE_NUMBER.sub(lambda m: m.group(0).replace(' ', '').replace(',', ''), text)

    # A number glued to letters, 3D, IP65, MIL-STD-461G, is a word; a number
    # over a slash, 24/7, is a ratio; neither is a quantity.
    return re.findall(r'[±+-]?\d+(?:\.\d+)?/\d+|\d+[A-Za-z][A-Za-z0-9°%/()_-]*'
                      r'|[±+-]?\d+(?:\.\d+)?(?![A-Za-z0-9/])|[A-Za-z°%][A-Za-z0-9°%/()_-]*'
                      r'|[^\sA-Za-z0-9]', text)


# -----------------------------------------------------------------------------
def _entries(map_document, prefix):
    """
    Yield every register entry whose id carries the prefix.

    """

    for document in map_document.values():
        if not isinstance(document, dict) or not isinstance(document.get(KEY_TABLE), dict):
            continue
        for entry in document[KEY_TABLE].values():
            if isinstance(entry, dict) \
                    and str(entry.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] == prefix:
                yield entry


def _units(map_document):
    """
    Return {spelling: symbol} over every unit register in the tree,
    spellings lower case.

    """

    out = {}

    for entry in _entries(map_document, PREFIX_UNIT):
        symbol = str(entry.get(KEY_SYMBOL) or '')
        for spelling in [symbol, *(entry.get(KEY_ALSO) or [])]:
            out[str(spelling).lower()] = symbol

    return out


def _verbs(map_document):
    """
    Return {term: kind} over every process word register in the tree.

    """

    return {' '.join(str(entry.get(KEY_TERM) or '').split()).lower():
                entry.get(KEY_KIND) or KIND_PROCESS
            for entry in _entries(map_document, PREFIX_VERB)}


def _known(map_document, units):
    """
    Return every word a glossary defines, lower case: the terms and
    their other forms, the document identifiers, and the unit symbols.

    """

    out = set(units)

    for entry in _entries(map_document, PREFIX_TERM):
        for word in [entry.get(KEY_TERM), *(entry.get(KEY_ALSO) or [])]:
            if word:
                out.add(str(word).lower())

    for entry in _entries(map_document, PREFIX_DOC):
        for word in RE_ACRONYM.findall(str(entry.get('id_external') or '')
                                       + ' ' + str(entry.get('title') or '')):
            out.add(word.lower())

    return out
