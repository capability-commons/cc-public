"""
---

id_self:                pym_cc_public.check.requirement
guid_self:              pym_ad3bc6ced85b419aa3b2b131c595dfd6
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement check
brief:                  |
                        Check that every requirement and candidate
                        composes a statement and names a defined
                        process word.
description:            |
                        Composes the statement of every textual
                        requirement and every candidate requirement in
                        a concept from its slots, and reports slots
                        that do not compose: an interaction without an
                        actor, an actor without an interaction, a
                        condition without its kind. Resolves the
                        process slot against the process word
                        registers the item can see, its own segment
                        and those it consumes, and reports a verb none
                        defines: advisory on a candidate or a proposed
                        requirement, since the finding is the question
                        what the entity does, and critical on an
                        accepted one, since what is accepted is
                        defined.
relation:               []

...
"""


import cc_public.check.result
import cc_public.check.segment
import cc_public.requirement


ID_CHECK        = 'requirement'
TITLE           = 'Requirements compose and their process words are defined'
NOUN            = 'requirement'

KEY_ID_SELF     = 'id_self'
KEY_TABLE       = 'table'
KEY_TERM        = 'term'
KEY_STATUS      = 'status'
KEY_CANDIDATE   = 'candidate_requirement'
KEY_PROCESS     = cc_public.requirement.KEY_PROCESS
PREFIX_REQ      = cc_public.requirement.PREFIX_REQUIREMENT
PREFIX_CONCEPT  = 'cpt'
PREFIX_VERB     = 'verb'
STATUS_ACCEPTED = 'accepted'
SEPARATOR       = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every requirement or candidate whose slots do
    not compose a statement, and every one whose process word no
    register it can see defines.

    The slots are canonical and the sentence is derived, so slots that
    do not compose are a requirement that cannot be read: critical. A
    verb no register defines is the question SOPHIST asks, what does the
    entity do: advisory while the requirement is proposed or a
    candidate, critical once it is accepted, since what is accepted is
    defined. A register is seen from its own segment and from the
    segments that consume it, as any other reference is; where no
    segment is declared, every register is seen.

    """

    segments = cc_public.check.segment.map_segment(context.map_document)
    visible  = cc_public.check.segment.reach(segments)
    defined  = _defined(context.map_document, segments)

    count    = 0
    list_bad = []

    for (location, path, document) in _iter_subject(context.map_document):

        count += 1
        id_segment = cc_public.check.segment.segment_of(location.filepath, segments)

        try:
            cc_public.requirement.statement(document)
        except cc_public.requirement.ErrorSlot as err:
            list_bad.append(cc_public.check.result.Nonconformity(
                filepath = str(location.filepath), path = path,
                message  = 'The slots do not compose a statement: {err}'.format(err = err)))
            continue

        term = ' '.join(str(document.get(KEY_PROCESS) or '').split())
        seen = visible.get(id_segment, set(segments)) if segments else None

        if any(seen is None or id_seg is None or id_seg in seen
               for id_seg in defined.get(term, [])):
            continue

        is_accepted = document.get(KEY_STATUS) == STATUS_ACCEPTED
        list_bad.append(cc_public.check.result.Nonconformity(
            filepath = str(location.filepath), path = path,
            message  = ('The process word {term} is not defined in a process word '
                        'register this item can see. What does the entity do: define '
                        'the verb in the register, or use one it defines.'.format(
                                                                        term = term)),
            severity = (cc_public.check.result.SEVERITY_CRITICAL if is_accepted
                        else cc_public.check.result.SEVERITY_ADVISORY)))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _iter_subject(map_document):
    """
    Yield (location, path, document) for every textual requirement and
    every candidate requirement embedded in a concept.

    """

    for (location, document) in sorted(map_document.items(), key = lambda kv: str(kv[0])):

        if not isinstance(document, dict):
            continue

        prefix = str(document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0]

        if prefix == PREFIX_REQ:
            yield (location, '', document)

        elif prefix == PREFIX_CONCEPT:
            for (key, entry) in (document.get(KEY_CANDIDATE) or {}).items():
                if isinstance(entry, dict):
                    yield (location, KEY_CANDIDATE + '.' + key, entry)


# -----------------------------------------------------------------------------
def _defined(map_document, segments):
    """
    Return {term: [id_segment of each register defining it]} over every
    process word register in the tree, None standing for a register
    under no segment.

    """

    out = {}

    for (location, document) in map_document.items():

        if not isinstance(document, dict) or not isinstance(document.get(KEY_TABLE), dict):
            continue

        id_segment = cc_public.check.segment.segment_of(location.filepath, segments)

        for entry in document[KEY_TABLE].values():
            if isinstance(entry, dict) \
                    and str(entry.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] == PREFIX_VERB \
                    and entry.get(KEY_TERM):
                out.setdefault(' '.join(str(entry[KEY_TERM]).split()), []).append(id_segment)

    return out
