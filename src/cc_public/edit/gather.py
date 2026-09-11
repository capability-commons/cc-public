"""
---

id_self:                pym_cc_public.edit.gather
guid_self:              pym_7ce2dfe42b444418859833885b385a35
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gather
brief:                  |
                        Make a requirement set from the requirements
                        derived from a concept.
description:            |
                        Makes a requirement set data item on the
                        entity of a concept, including by r_includes
                        every requirement that derives from the
                        concept, so that the set-level rules have a
                        set to judge. Membership is held as edges; a
                        later gather over the same set adds what is
                        new.
relation:               []

...
"""


import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.item


TYPE_SET      = 't_requirement_set'
PREFIX_SET    = 'rqs'
PREFIX_REQ    = 'req'
REL_DERIVED   = 'r_is_derived_from'
REL_INCLUDES  = 'r_includes'
KEY_ID_SELF   = 'id_self'
KEY_ENTITY    = 'entity'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_GUID_TGT  = 'guid_target'
KEY_ID_TARGET = 'id_target'
STATUS        = 'proposed'
SEPARATOR     = '_'


# -----------------------------------------------------------------------------
def gather(tree, id_concept, id_self = None, entity = None, title = None):
    """
    Make, or extend, a requirement set holding every requirement that
    derives from the concept, on the concept's entity, and return
    (Item, list of the ids included now).

    A set that exists already gains what it lacks; a member it holds
    is left alone, so that gathering twice is gathering once.

    """

    concept  = tree.resolve(id_concept)
    document = tree.context.map_document[concept.location]
    entity   = entity or document.get(KEY_ENTITY)
    id_self  = id_self or SEPARATOR.join([PREFIX_SET, id_concept.split(SEPARATOR, 1)[1]])

    list_member = sorted(
        doc[KEY_ID_SELF] for doc in tree.context.map_document.values()
        if isinstance(doc, dict)
           and cc_public.item.prefix_of(doc.get(KEY_ID_SELF)) == PREFIX_REQ
           and any(isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_DERIVED
                   and edge.get(KEY_GUID_TGT) == concept.guid_self
                   for edge in doc.get(KEY_RELATION) or []))

    if not list_member:
        raise cc_public.edit.tree.ErrorItem(
                'No requirement derives from {concept}; promote it first.'.format(
                                                            concept = id_concept))

    if id_self not in tree.map_id:
        cc_public.edit.new.new(tree, TYPE_SET, id_self, tree.defaults())
        cc_public.edit.field.set_field(tree, id_self, 'title', value = title or (
                    'Requirements on the {entity}'.format(entity = entity.replace('_', ' ')))[:80])
        cc_public.edit.field.set_field(tree, id_self, 'brief', prose = (
                    'The requirements on the {entity} promoted from {concept}, taken '
                    'together.'.format(entity = entity, concept = id_concept)))
        cc_public.edit.field.set_field(tree, id_self, KEY_ENTITY, value = entity)
        cc_public.edit.field.set_field(tree, id_self, 'status', value = STATUS)

    held = {edge.get(KEY_ID_TARGET)
            for edge in tree.context.map_document[tree.resolve(id_self).location]
                            .get(KEY_RELATION) or []
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_INCLUDES}

    added = []

    for id_member in list_member:
        if id_member not in held:
            cc_public.edit.link.link(tree, id_self, REL_INCLUDES, id_member)
            added.append(id_member)

    return (tree.resolve(id_self), added)
