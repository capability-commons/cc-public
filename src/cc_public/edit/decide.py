"""
---

id_self:                pym_cc_public.edit.decide
guid_self:              pym_b0aa80704c6a4c4a9bc31d6e27ed128d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Decide
brief:                  |
                        Make a decision item over named items, stamped
                        with their digests.
description:            |
                        This module makes a decision data item in the
                        decision directory. The item holds the
                        outcome, the actor with role and authority,
                        the reasons, the condition and expiry where
                        they are given, and one subject for each item
                        named. Each subject carries the digest of that
                        item's content as it stands. This is the one
                        path by which a decision is made.
relation:               []

...
"""


import cc_public.decision
import cc_public.edit.field
import cc_public.edit.new
import cc_public.edit.tree


TYPE_DECISION = 't_decision'
PREFIX        = cc_public.decision.PREFIX
SEPARATOR     = '_'
OUTCOMES      = (cc_public.decision.OUTCOME_WAIVE, cc_public.decision.OUTCOME_SELECT,
                 cc_public.decision.OUTCOME_ACCEPT, cc_public.decision.OUTCOME_LEAD)


# -----------------------------------------------------------------------------
def decide(tree, outcome, list_name, by, brief,
           condition = None, expiry = None, id_self = None, title = None):
    """
    Make a decision item over the items named, stamped with the digest
    of each as it stands, and return its Item. by holds the actor, the
    role and the authority.

    The id defaults to the outcome and the first subject's name; the
    title to the outcome and the subjects.

    """

    if outcome not in OUTCOMES:
        raise cc_public.edit.tree.ErrorItem(
                'outcome is one of {which}, not {outcome}.'.format(
                        which = ', '.join(OUTCOMES), outcome = outcome))

    if not list_name:
        raise cc_public.edit.tree.ErrorItem('A decision is over at least one item.')

    list_subject = []

    for name in list_name:
        item     = tree.resolve(name)
        document = _document(tree, item)
        list_subject.append({
            cc_public.decision.KEY_ID_ITEM:   item.id_self,
            cc_public.decision.KEY_GUID_ITEM: item.guid_self,
            cc_public.decision.KEY_DIGEST:    cc_public.decision.digest_of(document)})

    first   = list_subject[0][cc_public.decision.KEY_ID_ITEM].split(SEPARATOR, 1)[-1]
    id_self = id_self or SEPARATOR.join([PREFIX, outcome, first])
    names   = ', '.join(s[cc_public.decision.KEY_ID_ITEM] for s in list_subject)
    title   = title or '{outcome} {names}'.format(outcome = outcome.capitalize(),
                                                  names   = names)[:80]

    cc_public.edit.new.new(tree, TYPE_DECISION, id_self, tree.defaults())

    for (field, value) in (('title', title), ('actor', by['actor']), ('role', by['role']),
                           ('authority', by['authority']), ('outcome', outcome)):
        cc_public.edit.field.set_field(tree, id_self, field, value = value)

    cc_public.edit.field.set_field(tree, id_self, 'brief', prose = brief)

    if condition:
        cc_public.edit.field.set_field(tree, id_self, 'condition', prose = condition)

    if expiry:
        cc_public.edit.field.set_field(tree, id_self, cc_public.decision.KEY_EXPIRY,
                                       value = str(expiry))

    cc_public.edit.field.set_field(tree, id_self, cc_public.decision.KEY_SUBJECT,
                                   value = list_subject)

    return tree.resolve(id_self)


# -----------------------------------------------------------------------------
def _document(tree, item):
    """
    Return the document of an item, embedded or not.

    """

    node = tree.context.map_document[item.location]

    for step in (item.path.split('.') if item.path else []):
        node = node[step]

    return node
