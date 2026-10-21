"""
---

id_self:                pym_cc_public.requirement.compose
guid_self:              pym_a7520a8064e341859d414772e62ac8ae
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Composer of requirement statements
brief:                  |
                        Compose the statement of a requirement from
                        its slots, in the SOPHIST MASTER form.
description:            |
                        The statement opens with the condition, by the
                        keyword of its kind: If, As soon as or As long
                        as. Then come the subject, by its title, and
                        the modal verb. An interaction provides the
                        actor with the ability to do the process, and
                        an interface is able to do it. The process is
                        the preferred term of its concept, and the
                        object and the qualifier follow it. Slots that
                        do not compose are refused with ErrorCompose.
edge:                   []

...
"""


import typing


KEY_CONDITION_KIND   = 'condition_kind'
KEY_CONDITION        = 'condition'
KEY_MODAL_VERB       = 'modal_verb'
KEY_ACTIVITY         = 'activity'
KEY_OBJECT           = 'object'
KEY_QUALIFIER        = 'qualifier'
KEY_TITLE            = 'title'
KEY_TERM_PREFERRED   = 'term_preferred'
KEY_EDGE             = 'edge'
KEY_ID_RELATION      = 'id_relation'
KEY_ID_TARGET        = 'id_target'

PREFIX_REQUIREMENT   = 'rqt_'
SLOT_SUBJECT         = 'subject'
SLOT_PROCESS         = 'process'

R_HAS_SUBJECT        = 'r_has_subject'
R_HAS_ACTOR          = 'r_has_actor'
R_HAS_PROCESS        = 'r_has_process'

ACTIVITY_INTERACTION = 'interaction'
ACTIVITY_INTERFACE   = 'interface'

# The keyword that opens a condition, by the kind of the condition.
#
MAP_KEYWORD          = {'logic': 'If',
                        'event': 'As soon as',
                        'time':  'As long as'}

NodeOf               = typing.Callable[[str], typing.Mapping[str, typing.Any] | None]


# -----------------------------------------------------------------------------
class ErrorCompose(Exception):
    """
    The slots of a requirement do not compose into a statement.

    """


# -----------------------------------------------------------------------------
class Part(typing.NamedTuple):
    """
    A part of a statement: the slot it fills, its words, and the item
    the slot names, or None if the slot is text.

    """

    slot:    str
    text:    str
    id_item: str | None = None


# -----------------------------------------------------------------------------
def statement(requirement: typing.Mapping[str, typing.Any], node_of: NodeOf) -> str:
    """
    Return the statement composed from the slots of requirement, in the
    SOPHIST MASTER form.

    node_of returns the document of the item with a given id, or None.
    The subject and the actor are named by their titles, and the
    process by the preferred term of its concept.

    """

    text = ' '.join(part.text for part in parts(requirement, node_of)) + '.'
    return text[0].upper() + text[1:]


# -----------------------------------------------------------------------------
def parts(requirement: typing.Mapping[str, typing.Any], node_of: NodeOf) -> list[Part]:
    """
    Return the parts of the statement of requirement in their order, as
    statement joins them, before the first is capitalized.

    """

    id_subject = _target(requirement, R_HAS_SUBJECT)
    id_process = _target(requirement, R_HAS_PROCESS)
    subject    = _name(node_of, id_subject, KEY_TITLE)
    process    = _name(node_of, id_process, KEY_TERM_PREFERRED)
    activity   = requirement.get(KEY_ACTIVITY)

    list_part = []
    if KEY_CONDITION in requirement:
        kind = requirement.get(KEY_CONDITION_KIND)
        if kind not in MAP_KEYWORD:
            raise ErrorCompose('The condition has no kind: {kind!r}.'.format(kind = kind))
        list_part.append(Part(KEY_CONDITION,
                              '{keyword} {condition},'.format(
                                  keyword   = MAP_KEYWORD[kind],
                                  condition = requirement[KEY_CONDITION])))

    list_part += [Part(SLOT_SUBJECT, 'the ' + subject, id_subject),
                  Part(KEY_MODAL_VERB, _slot(requirement, KEY_MODAL_VERB))]

    if activity == ACTIVITY_INTERACTION:
        id_actor = _target(requirement, R_HAS_ACTOR)
        actor    = _name(node_of, id_actor, KEY_TITLE)
        list_part.append(Part(KEY_ACTIVITY,
                              'provide the {actor} with the ability to'.format(actor = actor),
                              id_actor))
    elif activity == ACTIVITY_INTERFACE:
        list_part.append(Part(KEY_ACTIVITY, 'be able to'))

    list_part += [Part(SLOT_PROCESS, process, id_process),
                  Part(KEY_OBJECT, _slot(requirement, KEY_OBJECT))]
    if KEY_QUALIFIER in requirement:
        list_part.append(Part(KEY_QUALIFIER, _slot(requirement, KEY_QUALIFIER)))

    return list_part


# -----------------------------------------------------------------------------
def _slot(requirement: typing.Mapping[str, typing.Any], key: str) -> str:
    """
    Return the text slot key of requirement.

    """

    value = requirement.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ErrorCompose('The slot {key} is missing.'.format(key = key))
    return value.strip()


# -----------------------------------------------------------------------------
def _target(requirement: typing.Mapping[str, typing.Any], id_relation: str) -> str:
    """
    Return the target of the one edge of id_relation that requirement
    records.

    """

    list_target = [edge.get(KEY_ID_TARGET)
                   for edge in requirement.get(KEY_EDGE) or []
                   if isinstance(edge, dict) and edge.get(KEY_ID_RELATION) == id_relation]
    if len(list_target) != 1:
        raise ErrorCompose('The requirement has {count} edges of {relation}, not 1.'.format(
                               count    = len(list_target),
                               relation = id_relation))
    return str(list_target[0])


# -----------------------------------------------------------------------------
def _name(node_of: NodeOf, id_item: str, key: str) -> str:
    """
    Return the field key of the item id_item, by which the statement
    names it.

    """

    node  = node_of(id_item)
    value = node.get(key) if node is not None else None
    if not isinstance(value, str) or not value.strip():
        raise ErrorCompose('The item {id} has no {key}.'.format(id = id_item, key = key))
    return value.strip()
