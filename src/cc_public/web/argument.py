"""
---

id_self:                pym_cc_public.web.argument
guid_self:              pym_0a2cc0b820f3484880c20235eb8324ab
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Argument of a decision
brief:                  |
                        Read the items of a tree, and gather on each
                        decision the options, annotations and rulings
                        that make its argument.
description:            |
                        Graph reads every item in a tree, with its
                        title, brief, description and edges as
                        written. Graph.decision gathers a decision:
                        the options that answer it, the annotations
                        about it, the rulings that settle its options,
                        and the driver concerns of its subject. The
                        standing of each option, upheld, rejected or
                        open, follows from the ruling of the decision,
                        of which there is at most one.
relation:               []

...
"""


import collections
import dataclasses
import pathlib
import re
import typing

import cc_public.graph.extract


KEY_ID_SELF       = 'id_self'
KEY_TITLE         = 'title'
KEY_BRIEF         = 'brief'
KEY_DESCRIPTION   = 'description'
KEY_RELATION      = 'relation'
KEY_ID_RELATION   = 'id_relation'
KEY_ID_TARGET     = 'id_target'

PREFIX_DECISION   = 'dec_'
PREFIX_OPTION     = 'opt_'
PREFIX_ANNOTATION = 'ann_'

R_IS_OPTION_FOR   = 'r_is_option_for'
R_IS_ABOUT        = 'r_is_about'
R_SUPPORTS        = 'r_supports'
R_CHALLENGES      = 'r_challenges'
R_UPHOLDS         = 'r_upholds'
R_REJECTS         = 'r_rejects'
R_SPEAKS_FOR      = 'r_speaks_for_concern'
R_IS_DRIVEN_BY    = 'r_is_driven_by'

STANCE_UPHELD     = 'upheld'
STANCE_REJECTED   = 'rejected'
STANCE_OPEN       = 'open'


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Item:
    """
    An item of the graph, as the review shows it: its id, its prose,
    its edges as written, keyed by relation, and the file that holds
    it.

    """

    id:          str
    title:       str
    brief:       str
    description: str
    map_edge:    dict[str, list[str]]
    node:        dict = dataclasses.field(default_factory = dict, repr = False)
    file:        str = ''

    # -------------------------------------------------------------------------
    def targets(self, id_relation: str) -> list[str]:
        """
        Return the targets of the item's edges of id_relation, in the
        order they are written.

        """

        return self.map_edge.get(id_relation, [])


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Decision:
    """
    A decision and the argument gathered on it: the options that answer
    it, the annotations about it, and the rulings that settle
    its options.

    """

    item:               Item
    list_option:        list[Item]
    list_annotation:    list[Item]
    list_ruling: list[Item]
    list_driver:        list[str]
    map_stance:         dict[str, str]
    set_spoken:         set[str]

    # -------------------------------------------------------------------------
    def is_open(self) -> bool:
        """
        Return True if no ruling settles the decision.

        """

        return not self.list_ruling

    # -------------------------------------------------------------------------
    def unspoken(self) -> list[str]:
        """
        Return the driver concerns that no annotation on the decision
        speaks for.

        """

        return [id_concern for id_concern in self.list_driver
                if id_concern not in self.set_spoken]


# -----------------------------------------------------------------------------
class Graph:
    """
    The items of a tree, read for review.

    """

    # -------------------------------------------------------------------------
    def __init__(self, root: pathlib.Path) -> None:
        """
        Read every item in the tree under root.

        """

        self.map_item = {}

        for (key, (document, _)) in cc_public.graph.extract.documents(root).items():
            if cc_public.graph.extract.is_document(document):
                _collect(document, self.map_item, cc_public.graph.extract.file_of(key))

        self.map_source = collections.defaultdict(list)
        for item in self.map_item.values():
            for (id_relation, list_target) in item.map_edge.items():
                for id_target in list_target:
                    self.map_source[(id_relation, id_target)].append(item.id)

        set_prefix     = {id_item.split('_')[0] for id_item in self.map_item if '_' in id_item}
        self.re_id     = re.compile(r'\b(?:{prefix})_[A-Za-z0-9_.]*[A-Za-z0-9]'.format(
                                        prefix = '|'.join(sorted(set_prefix))))
        self.map_mention = collections.defaultdict(list)
        for item in self.map_item.values():
            for id_target in self.mentions(item.id):
                self.map_mention[id_target].append(item.id)

    # -------------------------------------------------------------------------
    def title(self, id_item: str) -> str:
        """
        Return the title of the item id_item, or its id if it has none
        or is not in the tree.

        """

        item = self.map_item.get(id_item)
        return item.title if (item is not None and item.title) else id_item

    # -------------------------------------------------------------------------
    def node(self, id_item: str) -> dict | None:
        """
        Return the document of the item id_item as written, or None if
        it is not in the tree.

        """

        item = self.map_item.get(id_item)
        return item.node if item is not None else None

    # -------------------------------------------------------------------------
    def sources(self, id_relation: str, id_target: str) -> list[str]:
        """
        Return the ids of the items with an edge of id_relation to
        id_target, sorted.

        """

        return sorted(self.map_source.get((id_relation, id_target), []))

    # -------------------------------------------------------------------------
    def mentions(self, id_item: str) -> list[str]:
        """
        Return the ids of the items that the prose of id_item names, in
        the order first named, leaving out itself and ids not in the
        tree.

        """

        item = self.map_item.get(id_item)
        if item is None:
            return []
        text = '\n'.join((item.title, item.brief, item.description))
        return [id_named for id_named in dict.fromkeys(self.re_id.findall(text))
                if id_named in self.map_item and id_named != id_item]

    # -------------------------------------------------------------------------
    def mentioned_by(self, id_item: str) -> list[str]:
        """
        Return the ids of the items whose prose names id_item, sorted.

        """

        return sorted(self.map_mention.get(id_item, []))

    # -------------------------------------------------------------------------
    def list_decision(self) -> list[Decision]:
        """
        Return every decision in the tree, sorted by title.

        """

        list_id = [id_item for id_item in self.map_item if id_item.startswith(PREFIX_DECISION)]
        return sorted((self.decision(id_item) for id_item in list_id),
                      key = lambda decision: decision.item.title.casefold())

    # -------------------------------------------------------------------------
    def decision(self, id_decision: str) -> Decision | None:
        """
        Return the decision id_decision with its argument, or None if the tree
        has no such decision.

        """

        item = self.map_item.get(id_decision)
        if item is None or not id_decision.startswith(PREFIX_DECISION):
            return None

        list_option        = self._items(self.sources(R_IS_OPTION_FOR, id_decision))
        set_option         = {option.id for option in list_option}
        list_annotation    = self._items(id_item for id_item in
                                         self.sources(R_IS_ABOUT, id_decision)
                                         if id_item.startswith(PREFIX_ANNOTATION))
        list_ruling = self._items(
                                 {id_item
                                  for id_option in set_option
                                  for id_relation in (R_UPHOLDS, R_REJECTS)
                                  for id_item in self.sources(id_relation, id_option)})
        list_driver        = sorted({id_concern
                                     for subject in self._items(item.targets(R_IS_ABOUT))
                                     for id_concern in subject.targets(R_IS_DRIVEN_BY)})
        set_spoken         = {id_concern
                              for annotation in list_annotation
                              for id_concern in annotation.targets(R_SPEAKS_FOR)}

        decision = Decision(item               = item,
                      list_option        = list_option,
                      list_annotation    = list_annotation,
                      list_ruling        = list_ruling,
                      list_driver        = list_driver,
                      map_stance         = {},
                      set_spoken         = set_spoken)

        decision.map_stance = {option.id: STANCE_OPEN for option in list_option}
        for ruling in decision.list_ruling:
            for id_option in ruling.targets(R_UPHOLDS):
                decision.map_stance[id_option] = STANCE_UPHELD
            for id_option in ruling.targets(R_REJECTS):
                decision.map_stance[id_option] = STANCE_REJECTED

        return decision

    # -------------------------------------------------------------------------
    def _items(self, iter_id: typing.Iterable[str]) -> list[Item]:
        """
        Return the items with the ids in iter_id, sorted by id.

        """

        return [self.map_item[id_item] for id_item in sorted(iter_id)
                if id_item in self.map_item]


# -----------------------------------------------------------------------------
def _collect(node: typing.Any, map_item: dict[str, Item], file: str = '') -> None:
    """
    Add to map_item an Item for node and for every item nested in it,
    each held in file.

    """

    if isinstance(node, list):
        for value in node:
            _collect(value, map_item, file)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)
    if isinstance(id_self, str):
        map_item[id_self] = Item(id          = id_self,
                                 title       = _text(node.get(KEY_TITLE)),
                                 brief       = _text(node.get(KEY_BRIEF)),
                                 description = _text(node.get(KEY_DESCRIPTION)),
                                 map_edge    = _edges(node.get(KEY_RELATION)),
                                 node        = node,
                                 file        = file)

    for (key, value) in node.items():
        if key != KEY_RELATION:
            _collect(value, map_item, file)


# -----------------------------------------------------------------------------
def _edges(value: typing.Any) -> dict[str, list[str]]:
    """
    Return the targets of the edges in the relation list value, keyed
    by relation.

    """

    map_edge = collections.defaultdict(list)

    if isinstance(value, list):
        for edge in value:
            if isinstance(edge, dict) and KEY_ID_RELATION in edge and KEY_ID_TARGET in edge:
                map_edge[str(edge[KEY_ID_RELATION])].append(str(edge[KEY_ID_TARGET]))

    return dict(map_edge)


# -----------------------------------------------------------------------------
def _text(value: typing.Any) -> str:
    """
    Return value as prose with its trailing whitespace removed, or an
    empty string if it is not text.

    """

    return value.rstrip() if isinstance(value, str) else ''
