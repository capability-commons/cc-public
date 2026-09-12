"""
---

id_self:                pym_cc_public.eval.burden
guid_self:              pym_4e2ce1f281ae49ae85f2845b714313e4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Reader burden
brief:                  |
                        Mechanical measures of the reading load a
                        prose field puts on a person.
description:            |
                        This module counts, on every prose field, what
                        the classic readability formulas miss:
                        propositions per word, pointers per sentence,
                        participial clauses, dependents per nominal,
                        nominalisations and noun runs. Sentence length
                        and grade are reported beside them as guards.
                        The module is an instrument for a person and a
                        screen for the tail. It sets no threshold and
                        gates nothing.
relation:               []

...
"""
import functools
import re
import statistics

import cc_public.check
import cc_public.edit.field
import cc_public.eval.select
import cc_public.item

MODEL      = 'en_core_web_sm'
MINIMUM    = 25
NAMES      = ('id', 'field', 'words', 'sentences', 'length', 'propositions',
              'density', 'finite', 'nominal', 'participial', 'dependents',
              'runs', 'pointers', 'grade')
NUMERIC    = NAMES[2:]
SKIP       = frozenset(('id_self', 'guid_self', 'copyright', 'license'))
POINTER    = frozenset(('it', 'its', 'they', 'them', 'their', 'this', 'that',
                        'these', 'those', 'such', 'former', 'latter'))
CONTENT    = frozenset(('NOUN', 'PROPN', 'VERB', 'ADJ', 'ADV'))
NOMINAL    = ('tion', 'sion', 'ment', 'ance', 'ence', 'ity', 'ness', 'ism', 'age')
CLAUSE     = frozenset(('acl', 'advcl', 'xcomp', 'ccomp'))
NOUN       = frozenset(('NOUN', 'PROPN'))
RE_NOMINAL = re.compile('(' + '|'.join(NOMINAL) + ')s?$')
RUN        = 3
LONG       = 6


# -----------------------------------------------------------------------------
class Absent(Exception):
    """
    The prose extra, or its english model, is not installed.

    """


# -----------------------------------------------------------------------------
@functools.cache
def load():
    """
    Return the language model, loaded once, or raise Absent.

    """

    try:
        import spacy
        return spacy.load(MODEL, disable = ['ner'])
    except (ImportError, OSError) as err:
        raise Absent('The prose extra is not installed: pip install '
                     '"cc_public[prose]" and the {model} model.'.format(
                                                    model = MODEL)) from err


# -----------------------------------------------------------------------------
def measure(nlp, text):
    """
    Return the measures of one prose text as a dict keyed by NUMERIC.

    words and sentences count; length is words per sentence.
    propositions is per word (Brown et al. 2008, via ideadensity);
    density is content words per word; finite is finite verbs per
    sentence, and a sentence with none is a fragment; nominal is
    nominalised nouns per hundred words; participial is participial
    clauses per sentence; dependents is the mean per nominal (Biber
    and Gray); runs is noun runs of three or more per hundred words;
    pointers is pronouns and demonstratives per sentence; grade is
    Flesch Kincaid, a guard only.

    """

    doc            = nlp(text)
    list_sentence  = [s for s in doc.sents if any(t.is_alpha for t in s)]
    list_token     = [t for t in doc if not t.is_punct and not t.is_space]
    count_sentence = max(len(list_sentence), 1)
    count_word     = max(len(list_token), 1)
    per_word       = 100.0 / count_word

    return {'words':        len(list_token),
            'sentences':    len(list_sentence),
            'length':       count_word / count_sentence,
            'propositions': _propositions(text),
            'density':      sum(1 for t in list_token if _is_content(t)) / count_word,
            'finite':       sum(_finite(s) for s in list_sentence) / count_sentence,
            'nominal':      per_word * sum(1 for t in list_token if _is_nominal(t)),
            'participial':  sum(1 for t in doc if _is_participial(t)) / count_sentence,
            'dependents':   _dependents(doc),
            'runs':         per_word * _runs(doc),
            'pointers':     sum(_pointers(s) for s in list_sentence) / count_sentence,
            'grade':        _grade(text, count_word)}


# -----------------------------------------------------------------------------
def _is_content(token):
    """
    Return whether token is a content word: a noun, verb, adjective
    or adverb, an auxiliary verb excepted.

    """

    return token.pos_ in CONTENT and token.dep_ not in ('aux', 'auxpass')


# -----------------------------------------------------------------------------
def _finite(sentence):
    """
    Return the number of finite verbs in sentence.

    """

    return sum(1 for t in sentence
                        if t.pos_ in ('VERB', 'AUX') and 'Fin' in t.morph.get('VerbForm'))


# -----------------------------------------------------------------------------
def _is_nominal(token):
    """
    Return whether token is a noun made from a verb or adjective, by
    its ending. A heuristic, and a long word only.

    """

    return token.pos_ == 'NOUN' \
                and len(token.text) > LONG \
                and RE_NOMINAL.search(token.text.lower()) is not None


# -----------------------------------------------------------------------------
def _is_participial(token):
    """
    Return whether token heads a participial clause.

    """

    return token.pos_ == 'VERB' \
                and 'Part' in token.morph.get('VerbForm') \
                and token.dep_ in CLAUSE


# -----------------------------------------------------------------------------
def _dependents(doc):
    """
    Return the mean number of dependents on a nominal, or zero.

    """

    list_count = [sum(1 for c in t.children if not c.is_punct)
                                                for t in doc if t.pos_ in NOUN]

    return statistics.mean(list_count) if list_count else 0.0


# -----------------------------------------------------------------------------
def _runs(doc):
    """
    Return the number of runs of RUN or more nouns in a row.

    """

    count = 0
    run   = 0

    for token in doc:
        if token.pos_ in NOUN:
            run += 1
            continue
        count += run >= RUN
        run    = 0

    return count + (run >= RUN)


# -----------------------------------------------------------------------------
def _pointers(sentence):
    """
    Return the number of pronouns and demonstratives in sentence that
    point at something said before.

    """

    return sum(1 for t in sentence
                        if t.pos_ in ('PRON', 'DET') and t.text.lower() in POINTER)


# -----------------------------------------------------------------------------
def _propositions(text):
    """
    Return propositions per word, or nan where the rater cannot say.

    """

    import ideadensity

    try:
        (_, _, density, _) = ideadensity.cpidr(text)
    except Exception:  # the rater's own failure is a nan
        return float('nan')

    return density


# -----------------------------------------------------------------------------
def _grade(text, count_word):
    """
    Return the Flesch Kincaid grade, or zero for a text too short to
    grade.

    """

    import textstat

    return textstat.flesch_kincaid_grade(text) if count_word > 3 else 0.0


# -----------------------------------------------------------------------------
def iter_prose(tree, context):
    """
    Yield (id_self, field, text) for every prose field of every item,
    prose as the repository decides it.

    """

    for (id_self, document, _) in cc_public.eval.select.iter_item(context):

        item = _resolve(tree, id_self)

        for (name, value) in document.items():

            if name in SKIP or not isinstance(value, str):
                continue

            if _is_prose(tree, item, name, value):
                yield (id_self, name, value.strip())


# -----------------------------------------------------------------------------
def _resolve(tree, id_self):
    """
    Return the tree's item for id_self, or None where it has none.

    """

    try:
        return tree.resolve(id_self)
    except Exception:  # an unresolved item is measured by its text
        return None


# -----------------------------------------------------------------------------
def _is_prose(tree, item, name, value):
    """
    Return whether the field is prose, by the schema where the item
    resolves and by a line break where it does not.

    """

    if item is None:
        return '\n' in value

    try:
        return cc_public.edit.field.is_prose(tree, item, name, value)
    except Exception:  # a schema that cannot be read leaves the text to decide
        return '\n' in value


# -----------------------------------------------------------------------------
def rows(tree, context, list_field = (), list_prefix = (), minimum = MINIMUM):
    """
    Return one row per prose field, as a list of dicts keyed by NAMES,
    narrowed to the fields and type prefixes given and to texts of at
    least minimum words.

    """

    nlp       = load()
    list_row  = []

    for (id_self, name, text) in iter_prose(tree, context):

        if list_field and name not in list_field:
            continue

        if list_prefix and cc_public.item.prefix_of(id_self) not in list_prefix:
            continue

        measured = measure(nlp, text)

        if measured['words'] < minimum:
            continue

        list_row.append({'id': id_self, 'field': name, **measured})

    return list_row


# -----------------------------------------------------------------------------
def summarise(list_row, group):
    """
    Return one row per group, the group being 'field' or 'prefix',
    holding the count of rows, their words, and the median of every
    other measure.

    """

    map_group = {}

    for row in list_row:
        key = row['field'] if group == 'field' else cc_public.item.prefix_of(row['id'])
        map_group.setdefault(key, []).append(row)

    list_summary = []

    for (key, list_member) in sorted(map_group.items(), key = lambda kv: -len(kv[1])):
        summary = {group:  key,
                   'rows':  len(list_member),
                   'words': sum(r['words'] for r in list_member)}
        for name in NUMERIC[2:]:
            list_value = [r[name] for r in list_member if r[name] == r[name]]
            summary[name] = statistics.median(list_value) if list_value else float('nan')
        list_summary.append(summary)

    return list_summary
