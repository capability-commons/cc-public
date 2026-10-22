"""
---

id_self:                pym_cc_public.web.catalog
guid_self:              pym_820ea2930ade48d39861404415003454
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Catalog of every item
brief:                  |
                        Sort every item of a tree by its type and by
                        its subject, and find items by their words,
                        for the index of the review pages.
description:            |
                        A catalog reads the type of each item from the
                        prefix of its id, as the type register sets
                        it, and gathers the items of each type. It
                        groups the types by what they are for, as
                        TUPLE_GROUP lists them; a type the list does
                        not name falls under Other, so that a new type
                        shows in the index with nothing more to do.

                        The components are the logical components. The
                        items about a subject are those with an edge
                        to it, of any relation, gathered by type.

                        search finds the items whose id, title or
                        brief hold every word of a query, those that
                        match by id or title first.
edge:                   []

...
"""


import collections
import re

import cc_public.web.argument


KEY_PREFIX        = 'prefix'
PREFIX_TYPE       = 'type_'
PREFIX_SUBJECT    = 'lco_'
ID_COMPONENT_TYPE = 'type_logical_component'
DELIM_PREFIX      = '_'
NAME_OTHER        = 'Other'
COUNT_FOUND       = 200

# The groups of types the index shows, in order, each with its types
# in the order they are listed under it.
#
TUPLE_GROUP       = (
    ('Deliberation',     ('type_decision', 'type_option', 'type_annotation', 'type_ruling',
                          'type_concern')),
    ('Requirements and architecture',
                         ('type_requirement', 'type_logical_component',
                          'type_interface_control_document', 'type_interface_member')),
    ('Vocabulary',       ('type_concept', 'type_design_rule', 'type_writing_style_rule',
                          'type_relation', 'type_role', 'type_relation_constraint')),
    ('Structure',        ('type_type', 'type_schema', 'type_register', 'type_protective_mark')),
    ('Code and history', ('type_python_package', 'type_python_module', 'type_python_class',
                          'type_python_function', 'type_logic_program_file',
                          'type_file', 'type_shell_script', 'type_commit')))

Graph             = cc_public.web.argument.Graph


# -----------------------------------------------------------------------------
class Catalog:
    """
    The items of a graph sorted by type and by subject.

    """

    # -------------------------------------------------------------------------
    def __init__(self, graph: Graph) -> None:
        """
        Sort the items of graph.

        """

        self.graph      = graph
        self.map_prefix = {item.node[KEY_PREFIX]: item.id
                           for item in graph.map_item.values()
                           if item.id.startswith(PREFIX_TYPE)
                           and isinstance(item.node.get(KEY_PREFIX), str)}
        self.map_type   = collections.defaultdict(list)
        for id_item in sorted(graph.map_item, key = self._order):
            self.map_type[self.has_type(id_item)].append(id_item)

        self.map_about = collections.defaultdict(list)
        for ((_, id_target), list_source) in graph.map_source.items():
            if id_target.startswith(PREFIX_SUBJECT):
                self.map_about[id_target] += list_source

    # -------------------------------------------------------------------------
    def has_type(self, id_item: str) -> str:
        """
        Return the type of the item id_item, read from the prefix of its
        id, or '' if no type has that prefix.

        """

        return self.map_prefix.get(id_item.partition(DELIM_PREFIX)[0], '')

    # -------------------------------------------------------------------------
    def items(self, id_type: str) -> list[str]:
        """
        Return the ids of the items of the type id_type, in the order of
        their titles.

        """

        return list(self.map_type.get(id_type, []))

    # -------------------------------------------------------------------------
    def groups(self) -> list[tuple[str, list[str]]]:
        """
        Return the groups of types, each with its types: those of
        TUPLE_GROUP that the tree has, and then any other type the tree
        has, or that has items, under Other.

        """

        set_listed = {id_type for (_, tuple_type) in TUPLE_GROUP for id_type in tuple_type}
        set_type   = set(self.map_prefix.values())
        list_group = [(name, [id_type for id_type in tuple_type if id_type in set_type])
                      for (name, tuple_type) in TUPLE_GROUP]
        list_other = sorted((set_type | set(self.map_type)) - set_listed,
                            key = self._order)
        if list_other:
            list_group.append((NAME_OTHER, list_other))
        return [(name, list_type) for (name, list_type) in list_group if list_type]

    # -------------------------------------------------------------------------
    def components(self) -> list[str]:
        """
        Return the ids of the logical components, in the
        order of their titles.

        """

        return self.items(ID_COMPONENT_TYPE)

    # -------------------------------------------------------------------------
    def about(self, id_component: str) -> list[tuple[str, list[str]]]:
        """
        Return the items with an edge to the subject id_component, gathered
        by type in the order of the groups, each type with its items in
        the order of their titles.

        """

        set_about = set(self.map_about.get(id_component, []))
        list_type = [id_type for (_, list_group) in self.groups() for id_type in list_group]
        return [(id_type, [id_item for id_item in self.map_type[id_type]
                           if id_item in set_about])
                for id_type in list_type
                if set_about.intersection(self.map_type[id_type])]

    # -------------------------------------------------------------------------
    def search(self, text: str) -> list[str]:
        """
        Return the ids of the items whose id, title or brief hold every
        word of text, ignoring case: an item whose id or title holds
        them first, then the rest, each in the order of their titles.
        At most COUNT_FOUND are returned.

        """

        list_word = re.findall(r'[\w.]+', text.casefold())
        if not list_word:
            return []

        list_near = []
        list_far  = []
        for id_item in sorted(self.graph.map_item, key = self._order):
            item = self.graph.map_item[id_item]
            near = ' '.join((item.id, item.title)).casefold()
            far  = ' '.join((near, item.brief)).casefold()
            if all(word in near for word in list_word):
                list_near.append(id_item)
            elif all(word in far for word in list_word):
                list_far.append(id_item)
        return (list_near + list_far)[:COUNT_FOUND]

    # -------------------------------------------------------------------------
    def _order(self, id_item: str) -> tuple[str, str]:
        """
        Return the key that orders the item id_item by its title, then
        by its id.

        """

        return (self.graph.title(id_item).casefold(), id_item)
