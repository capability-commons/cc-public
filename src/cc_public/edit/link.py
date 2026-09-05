"""
---

id_self:                pym_cc_public.edit.link
guid_self:              pym_8f0aedf9a1f74dab9b23f7659338df86
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Link two items
brief:                  |
                        Add a relation edge from one item to another.
description:            |
                        Both items are named, wherever they live. The
                        relation must be an entry in the relation
                        register. The edge is the four fields every
                        edge has, with both guids looked up rather
                        than typed, and it is appended to the source
                        item's relation list, which is created where
                        absent.
relation:               []

...
"""


import ruamel.yaml.comments

import cc_public.edit.tree
import cc_public.path


KEY_RELATION = 'relation'
KEY_TABLE    = 'table'


# -----------------------------------------------------------------------------
def link(tree, name_source, id_relation, name_target):
    """
    Append an edge to the source item, and write the file back.

    """

    table = tree.relation_register()[KEY_TABLE]

    if id_relation not in table:
        raise cc_public.edit.tree.ErrorItem(
                '{rel} is not in the relation register.'.format(
                                                        rel = id_relation))

    source = tree.resolve(name_source)
    target = tree.resolve(name_target)
    edge   = ruamel.yaml.comments.CommentedMap()

    edge['id_relation']   = id_relation
    edge['guid_relation'] = table[id_relation]['guid_self']
    edge['id_target']     = target.id_self
    edge['guid_target']   = target.guid_self

    # Walk the document itself to the source item. select would return
    # a pruned copy, and an edge appended to a copy is an edge lost.
    #
    document = tree.document(source)
    node     = document
    for step in cc_public.path.split(source.path):
        node = node[int(step)] if isinstance(node, list) else node[step]

    existing = node.get(KEY_RELATION)

    if not isinstance(existing, list):
        existing = ruamel.yaml.comments.CommentedSeq()
        node[KEY_RELATION] = existing

    for other in existing:
        if (other.get('id_relation') == id_relation
                and other.get('guid_target') == target.guid_self):
            raise cc_public.edit.tree.ErrorItem(
                    '{src} already {rel} {dst}.'.format(src = source.id_self,
                                                        rel = id_relation,
                                                        dst = target.id_self))

    existing.append(edge)

    cc_public.edit.tree.save(source.filepath, document)
    tree.refresh(source.filepath)

    return (source, target)
