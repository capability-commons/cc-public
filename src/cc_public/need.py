"""
---

id_self:                pym_cc_public.need
guid_self:              pym_92b7b4aa5b164a388cbcb7bf61736988
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Need statement
brief:                  |
                        Compose the statement of a need from its
                        slots.
description:            |
                        A need statement is exactly its slots in
                        order: in the context, the subject needs the
                        outcome, in order to the purpose. It is
                        composed wherever a need is rendered, for a
                        judge, a model or a reader, and never stored,
                        so that it cannot say something the slots do
                        not.
relation:               []

...
"""


KEY_SUBJECT  = 'subject'
KEY_OUTCOME  = 'outcome'
KEY_PURPOSE  = 'purpose'
KEY_CONTEXT  = 'context'
KEY_EVIDENCE = 'evidence'
KEY_ENTITY   = 'entity'
KEY_STATEMENT = 'statement'
KEY_ID_SELF  = 'id_self'
PREFIX_NEED  = 'need'
SLOTS        = (KEY_SUBJECT, KEY_OUTCOME, KEY_PURPOSE, KEY_CONTEXT, KEY_EVIDENCE)


# -----------------------------------------------------------------------------
def is_need(document):
    """
    Return whether document is a need: a mapping with the need prefix
    and every slot.

    """

    return (isinstance(document, dict)
            and str(document.get(KEY_ID_SELF, '')).split('_', 1)[0] == PREFIX_NEED
            and all(document.get(k) for k in SLOTS))


# -----------------------------------------------------------------------------
def statement(document):
    """
    Return the statement of a need, composed from its slots.

    """

    def clean(key):
        return ' '.join(str(document[key]).split()).rstrip('.')

    entity = ' from the ' + clean(KEY_ENTITY) if document.get(KEY_ENTITY) else ''

    return 'In {context}, {subject} need {outcome}{entity}, in order to {purpose}.'.format(
                context = clean(KEY_CONTEXT), subject = clean(KEY_SUBJECT),
                outcome = clean(KEY_OUTCOME), entity = entity,
                purpose = clean(KEY_PURPOSE))


# -----------------------------------------------------------------------------
def compose(document):
    """
    Return document with its statement composed in front of its slots,
    where it is a need; otherwise document itself.

    """

    if not is_need(document) or KEY_STATEMENT in document:
        return document

    out = {}

    for (key, value) in document.items():
        if key == KEY_SUBJECT:
            out[KEY_STATEMENT] = statement(document) + '\n'
        out[key] = value

    return out
