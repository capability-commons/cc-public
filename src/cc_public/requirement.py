"""
---

id_self:                pym_cc_public.requirement
guid_self:              pym_c6597b227de149c5b8df46012f91e2b3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Requirement statement
brief:                  |
                        Compose the statement of a requirement from
                        its slots.
description:            |
                        A requirement statement is exactly its slots
                        in order, in the SOPHIST template: the
                        condition, the entity, the obligation, the
                        activity with its process and object, and the
                        qualifier. It is composed wherever a
                        requirement or a candidate requirement is
                        rendered, for a judge, a model or a reader,
                        and never stored, so that it cannot say
                        something the slots do not.
relation:               []

...
"""


KEY_CONDITION_KIND = 'condition_kind'
KEY_CONDITION      = 'condition'
KEY_ENTITY         = 'entity'
KEY_OBLIGATION     = 'obligation'
KEY_ACTIVITY       = 'activity'
KEY_ACTOR          = 'actor'
KEY_PROCESS        = 'process'
KEY_OBJECT         = 'object'
KEY_QUALIFIER      = 'qualifier'
KEY_STATEMENT      = 'statement'
KEY_ID_SELF        = 'id_self'

PREFIX_REQUIREMENT = 'req'
PREFIX_CANDIDATE   = 'crq'
SLOTS              = (KEY_ENTITY, KEY_OBLIGATION, KEY_ACTIVITY, KEY_PROCESS, KEY_OBJECT)

ACTIVITY_AUTONOMOUS  = 'autonomous'
ACTIVITY_INTERACTION = 'interaction'
ACTIVITY_INTERFACE   = 'interface'

# The keyword each kind of condition opens with, from the SOPHIST
# condition templates: LogicMASTER, EventMASTER and TimeMASTER.
#
KEYWORD_CONDITION  = {'logic': 'If',
                      'event': 'As soon as',
                      'time':  'As long as'}


# -----------------------------------------------------------------------------
class ErrorSlot(Exception):
    """
    Raised when the slots of a requirement do not compose: an actor
    given without an interaction, or an interaction without an actor,
    or a condition without its kind.

    """



# -----------------------------------------------------------------------------
def is_requirement(document):
    """
    Return whether document is a requirement or a candidate
    requirement: a mapping with one of their prefixes and every slot
    the statement needs.

    """

    return (isinstance(document, dict)
            and str(document.get(KEY_ID_SELF, '')).split('_', 1)[0]
                            in (PREFIX_REQUIREMENT, PREFIX_CANDIDATE)
            and all(document.get(k) for k in SLOTS))


# -----------------------------------------------------------------------------
def statement(document):
    """
    Return the statement of a requirement, composed from its slots.

    The condition first, opened by the keyword its kind names; then
    the entity as subject and the obligation; then the activity, the
    process and its object as the SOPHIST functional template gives
    them, autonomous, an interaction that provides the actor with the
    ability, or an interface the entity is able to serve; then the
    qualifier; then the full stop.

    """

    def clean(key):
        return ' '.join(str(document.get(key) or '').split()).rstrip('.')

    activity  = clean(KEY_ACTIVITY)
    actor     = clean(KEY_ACTOR)
    condition = clean(KEY_CONDITION)
    kind      = clean(KEY_CONDITION_KIND)

    if (activity == ACTIVITY_INTERACTION) != bool(actor):
        raise ErrorSlot('An interaction names its actor, and nothing else does: '
                        '{id}.'.format(id = document.get(KEY_ID_SELF)))

    if bool(condition) != bool(kind):
        raise ErrorSlot('A condition is given with its kind: {id}.'.format(
                                                id = document.get(KEY_ID_SELF)))

    if condition:
        head = '{keyword} {condition}, the {entity}'.format(
                    keyword = KEYWORD_CONDITION[kind], condition = condition,
                    entity  = clean(KEY_ENTITY))
    else:
        head = 'The {entity}'.format(entity = clean(KEY_ENTITY))

    action = '{process} {object}'.format(process = clean(KEY_PROCESS),
                                         object  = clean(KEY_OBJECT))

    if activity == ACTIVITY_INTERACTION:
        action = 'provide the {actor} with the ability to {action}'.format(
                                                    actor = actor, action = action)
    elif activity == ACTIVITY_INTERFACE:
        action = 'be able to {action}'.format(action = action)

    qualifier = clean(KEY_QUALIFIER)

    return '{head} {obligation} {action}{qualifier}.'.format(
                head       = head,
                obligation = clean(KEY_OBLIGATION),
                action     = action,
                qualifier  = ' ' + qualifier if qualifier else '')


# -----------------------------------------------------------------------------
def compose(document):
    """
    Return document with its statement composed in front of its slots,
    where it is a requirement or a candidate; otherwise document
    itself. A document whose slots do not compose is returned as it
    is, for the checks to say why.

    """

    if not is_requirement(document) or KEY_STATEMENT in document:
        return document

    try:
        text = statement(document)
    except ErrorSlot:
        return document

    out = {}

    for (key, value) in document.items():
        if key == KEY_ENTITY:
            out[KEY_STATEMENT] = text + '\n'
        out[key] = value

    return out
