"""
---

id_self:                pym_cc_public.web.argument
guid_self:              pym_0a2cc0b820f3484880c20235eb8324ab
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Argument of an issue
brief:                  |
                        Read the items of a tree, and gather on each
                        issue the decisions, annotations and
                        determinations that make its argument.
description:            |
                        Graph reads every item in a tree, with its
                        title, brief, description and edges as
                        written. Graph.issue gathers an issue: the
                        decisions that answer it, the annotations
                        about it, the determinations that settle its
                        decisions, and the driver concerns of its
                        subject. The standing of each decision,
                        upheld, rejected or open, follows from the
                        determinations that no other supersedes.
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

PREFIX_ISSUE      = 'iss_'
PREFIX_DECISION   = 'dec_'
PREFIX_ANNOTATION = 'ann_'

R_ANSWERS         = 'r_answers'
R_IS_ABOUT        = 'r_is_about'
R_SUPPORTS        = 'r_supports'
R_CHALLENGES      = 'r_challenges'
R_UPHOLDS         = 'r_upholds'
R_REJECTS         = 'r_rejects'
R_SUPERSEDES      = 'r_supersedes'
R_ARGUES_FOR      = 'r_argues_for_concern'
R_IS_DRIVEN_BY    = 'r_is_driven_by'

STANCE_UPHELD     = 'upheld'
STANCE_REJECTED   = 'rejected'
STANCE_OPEN       = 'open'


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Item:
    """
    An item of the graph, as the review shows it: its id, its prose,
    and its edges as written, keyed by relation.

    """

    id:          str
    title:       str
    brief:       str
    description: str
    map_edge:    dict[str, list[str]]

    # -------------------------------------------------------------------------
    def targets(self, id_relation: str) -> list[str]:
        """
        Return the targets of the item's edges of id_relation, in the
        order they are written.

        """

        return self.map_edge.get(id_relation, [])


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Issue:
    """
    An issue and the argument gathered on it: the decisions that answer
    it, the annotations about it, and the determinations that settle
    its decisions.

    """

    item:               Item
    list_decision:      list[Item]
    list_annotation:    list[Item]
    list_determination: list[Item]
    list_driver:        list[str]
    map_stance:         dict[str, str]
    set_spoken:         set[str]

    # -------------------------------------------------------------------------
    def is_open(self) -> bool:
        """
        Return True if no determination in force settles the issue.

        """

        return not self.current()

    # -------------------------------------------------------------------------
    def current(self) -> list[Item]:
        """
        Return the determinations in force: those that no other
        determination on the issue supersedes.

        """

        set_superseded = {id_target
                          for determination in self.list_determination
                          for id_target in determination.targets(R_SUPERSEDES)}
        return [determination for determination in self.list_determination
                if determination.id not in set_superseded]

    # -------------------------------------------------------------------------
    def unspoken(self) -> list[str]:
        """
        Return the driver concerns that no annotation on the issue
        argues for.

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

        for (document, _) in cc_public.graph.extract.documents(root).values():
            if cc_public.graph.extract.is_document(document):
                _collect(document, self.map_item)

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
    def list_issue(self) -> list[Issue]:
        """
        Return every issue in the tree, sorted by title.

        """

        list_id = [id_item for id_item in self.map_item if id_item.startswith(PREFIX_ISSUE)]
        return sorted((self.issue(id_item) for id_item in list_id),
                      key = lambda issue: issue.item.title.casefold())

    # -------------------------------------------------------------------------
    def issue(self, id_issue: str) -> Issue | None:
        """
        Return the issue id_issue with its argument, or None if the tree
        has no such issue.

        """

        item = self.map_item.get(id_issue)
        if item is None or not id_issue.startswith(PREFIX_ISSUE):
            return None

        list_decision      = self._items(self.sources(R_ANSWERS, id_issue))
        set_decision       = {decision.id for decision in list_decision}
        list_annotation    = self._items(id_item for id_item in
                                         self.sources(R_IS_ABOUT, id_issue)
                                         if id_item.startswith(PREFIX_ANNOTATION))
        list_determination = self._items(
                                 {id_item
                                  for id_decision in set_decision
                                  for id_relation in (R_UPHOLDS, R_REJECTS)
                                  for id_item in self.sources(id_relation, id_decision)})
        list_driver        = sorted({id_concern
                                     for subject in self._items(item.targets(R_IS_ABOUT))
                                     for id_concern in subject.targets(R_IS_DRIVEN_BY)})
        set_spoken         = {id_concern
                              for annotation in list_annotation
                              for id_concern in annotation.targets(R_ARGUES_FOR)}

        issue = Issue(item               = item,
                      list_decision      = list_decision,
                      list_annotation    = list_annotation,
                      list_determination = list_determination,
                      list_driver        = list_driver,
                      map_stance         = {},
                      set_spoken         = set_spoken)

        issue.map_stance = {decision.id: STANCE_OPEN for decision in list_decision}
        for determination in issue.current():
            for id_decision in determination.targets(R_UPHOLDS):
                issue.map_stance[id_decision] = STANCE_UPHELD
            for id_decision in determination.targets(R_REJECTS):
                issue.map_stance[id_decision] = STANCE_REJECTED

        return issue

    # -------------------------------------------------------------------------
    def _items(self, iter_id: typing.Iterable[str]) -> list[Item]:
        """
        Return the items with the ids in iter_id, sorted by id.

        """

        return [self.map_item[id_item] for id_item in sorted(iter_id)
                if id_item in self.map_item]


# -----------------------------------------------------------------------------
def _collect(node: typing.Any, map_item: dict[str, Item]) -> None:
    """
    Add to map_item an Item for node and for every item nested in it.

    """

    if isinstance(node, list):
        for value in node:
            _collect(value, map_item)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)
    if isinstance(id_self, str):
        map_item[id_self] = Item(id          = id_self,
                                 title       = _text(node.get(KEY_TITLE)),
                                 brief       = _text(node.get(KEY_BRIEF)),
                                 description = _text(node.get(KEY_DESCRIPTION)),
                                 map_edge    = _edges(node.get(KEY_RELATION)))

    for (key, value) in node.items():
        if key != KEY_RELATION:
            _collect(value, map_item)


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
