"""
---

id_self:                pym_cc_public.web.network
guid_self:              pym_9d3a56e20c884eda811fa17d7bceadbf
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Graph of an argument
brief:                  |
                        Draw the argument on a decision as a tree for
                        each option: its concerns as small ports
                        beside it, and from each port the annotations
                        that argue for that concern on it, with the
                        annotations that answer them beyond.
description:            |
                        The drawing follows the diagrams of Mark
                        Lombardi: circles joined by thin lines, with
                        room to spare. Each option is a large circle
                        with its title to its left. Each concern
                        argued on it is a small circle beside it,
                        joined to it by a short spoke, and named only
                        while it is lit. From each concern run lines
                        to the annotations that argue for it on that
                        option, and from each annotation to those that
                        answer it. As in the Sankey diagram, an
                        annotation is drawn once for each place it
                        argues, so no two lines cross. A leaf has its
                        title to its right, and an annotation with
                        answers has its title above it.
relation:               []

...
"""


import math
import typing

import htpy

import cc_public.web.argument
import cc_public.web.light
import cc_public.web.sankey


Graph   = cc_public.web.argument.Graph
Outline = cc_public.web.sankey.Outline

# Sizes, in units of the drawing.
#
RADIUS_OPTION     = 24
RADIUS_ANNOTATION = 10
RADIUS_CONCERN    = 4.5
SPOKE             = 12
ANGLE_STEP        = 0.42
ANGLE_MAX         = 1.15
ROW               = 30
GAP_PARENT        = 20
GAP_OPTION        = 44
HEIGHT_OPTION     = 72
X_OPTION          = 250
X_FIRST           = X_OPTION + 190
COLUMN            = 250
CHARS_OPTION      = 26
LINE_OPTION       = 17
WIDTH_CHAR        = 6.4
MARGIN            = 16
DELIM_HUB         = '--'
ROLE_FOR          = cc_public.web.sankey.ROLE_FOR
ROLE_AGAINST      = cc_public.web.sankey.ROLE_AGAINST
ROLE_LINK         = 'link'
KIND_OPTION       = 'option'
KIND_CONCERN      = 'concern'
KIND_ANNOTATION   = 'annotation'
MAP_MARK          = {ROLE_FOR: '\u2713', ROLE_AGAINST: '\u2717'}


# -----------------------------------------------------------------------------
class _Tree:
    """
    The marks of the graph of one argument, placed branch by branch
    from the top down.

    """

    # -------------------------------------------------------------------------
    def __init__(self, graph: Graph, outline: Outline) -> None:
        """
        Place the trees of the options of outline.

        """

        self.graph      = graph
        self.outline    = outline
        (self.map_kind, self.list_edge) = _graph(outline)
        (map_name, set_pick, list_concern) = _chains(self.map_kind, self.list_edge)
        (self.map_sign, self.map_sign_edge) = _lighting(
            self.list_edge, self.map_kind, map_name, set_pick, list_concern)
        self.set_pick   = set_pick
        self.set_id     = set()
        self.y          = 0.0
        self.right      = X_OPTION
        self.list_path  = []
        self.list_node  = []
        self.list_label = []
        for id_option in outline.list_option:
            self._option(id_option)
            self.y += GAP_OPTION

    # -------------------------------------------------------------------------
    def _option(self, id_option: str) -> None:
        """
        Place the tree of id_option: its ports, one for each concern
        argued on it, and the branches beyond them.

        """

        list_concern = [id_concern for id_concern in self.outline.list_concern
                        if self.outline.units(option = id_option, concern = id_concern)]
        top          = self.y
        list_branch  = []
        for id_concern in list_concern:
            list_place = []
            for id_annotation in self.outline.map_annotation[id_concern]:
                for unit in self.outline.units(option     = id_option,
                                               concern    = id_concern,
                                               annotation = id_annotation):
                    key = cc_public.web.sankey.DELIM_KEY.join((id_concern, id_annotation))
                    list_place.append((self._annotation(id_annotation, 0, {id_annotation}, key),
                                       id_annotation, unit.role))
            list_branch.append((id_concern, list_place))
        bottom = max(self.y - ROW, top)
        y      = (top + bottom) / 2
        self.y = max(self.y, y + HEIGHT_OPTION / 2)
        self._node_option(id_option, y)

        count = len(list_branch)
        step  = min(ANGLE_STEP, 2 * ANGLE_MAX / max(count - 1, 1))
        for (index, (id_concern, list_place)) in enumerate(list_branch):
            angle  = (index - (count - 1) / 2) * step
            reach  = RADIUS_OPTION + SPOKE + RADIUS_CONCERN
            (x, y_port) = (X_OPTION + reach * math.cos(angle), y + reach * math.sin(angle))
            list_hub = [_hub(id_option, id_concern, role) for role in (ROLE_FOR, ROLE_AGAINST)
                        if _hub(id_option, id_concern, role) in self.map_sign]
            map_sign = _merged([self.map_sign[id_hub] for id_hub in list_hub]
                               + [self.map_sign_edge[(id_hub, id_option,
                                                      id_hub.split(DELIM_HUB)[2])]
                                  for id_hub in list_hub])
            list_css = cc_public.web.light.css(map_sign)
            self.list_path.append(htpy.line(
                x1 = _num(X_OPTION + RADIUS_OPTION * math.cos(angle)),
                y1 = _num(y + RADIUS_OPTION * math.sin(angle)),
                x2 = _num(x - RADIUS_CONCERN * math.cos(angle)),
                y2 = _num(y_port - RADIUS_CONCERN * math.sin(angle)),
                class_ = ' '.join(['spoke', cc_public.web.light.CSS_DIMS] + list_css)))
            for (y_to, id_annotation, role) in list_place:
                edge = (id_annotation, _hub(id_option, id_concern, role), ROLE_LINK)
                self._path(x + RADIUS_CONCERN, y_port, X_FIRST - RADIUS_ANNOTATION, y_to, role,
                           self.map_sign_edge[edge])
            self._node_concern(id_concern, x, y_port, list_css)

    # -------------------------------------------------------------------------
    def _annotation(self, id_annotation: str, depth: int, set_path: set[str], key: str) -> float:
        """
        Place a copy of id_annotation at depth, with the branches of
        the annotations that answer it, and return its height. It
        stands level with its first answer, if it has any. key names
        the same place in the argument under the decision matrix.

        """

        x           = X_FIRST + depth * COLUMN
        list_answer = [(id_answer, role)
                       for (id_answer, role) in self.outline.answers(id_annotation)
                       if id_answer not in set_path]
        if not list_answer:
            y      = self.y
            self.y = y + ROW
            self._node_annotation(id_annotation, x, y, False, key)
            return y
        self.y   += GAP_PARENT
        list_y    = [(self._annotation(id_answer, depth + 1, set_path | {id_answer},
                                       cc_public.web.sankey.DELIM_KEY.join((key, id_answer))),
                      id_answer, role)
                     for (id_answer, role) in list_answer]
        y         = list_y[0][0]
        for (y_to, id_answer, role) in list_y:
            self._path(x + RADIUS_ANNOTATION, y, x + COLUMN - RADIUS_ANNOTATION, y_to, role,
                       self.map_sign_edge[(id_answer, id_annotation, role)])
        self._node_annotation(id_annotation, x, y, True, key)
        return y

    # -------------------------------------------------------------------------
    def _path(self,
              x1:       float,
              y1:       float,
              x2:       float,
              y2:       float,
              role:     str,
              map_sign: dict[str, set[str]]) -> None:
        """
        Add a line of role from x1, y1 to x2, y2, leaving and arriving
        level.

        """

        x_mid = (x1 + x2) / 2
        path  = 'M{x1},{y1} C{xm},{y1} {xm},{y2} {x2},{y2}'.format(x1 = _num(x1),
                                                                 y1 = _num(y1),
                                                                 xm = _num(x_mid),
                                                                 x2 = _num(x2),
                                                                 y2 = _num(y2))
        self.list_path.append(htpy.path(
            d = path, class_ = ' '.join(['edge-' + role, cc_public.web.light.CSS_DIMS]
                                        + cc_public.web.light.css(map_sign))))

    # -------------------------------------------------------------------------
    def _id(self, id_item: str) -> str | None:
        """
        Return the id of the element of id_item the first time it is
        drawn, and None for each copy after.

        """

        if id_item in self.set_id:
            return None
        self.set_id.add(id_item)
        return 'node-' + id_item

    # -------------------------------------------------------------------------
    def _css(self, kind: str, list_css: list[str]) -> str:
        """
        Return the classes of a node of kind.

        """

        return ' '.join(['node', kind, cc_public.web.light.CSS_DIMS] + list_css)

    # -------------------------------------------------------------------------
    def _pick(self, id_item: str, node: typing.Any, key: str | None = None) -> typing.Any:
        """
        Return node, linked to the page with every chain into id_item
        lit if id_item is picked. A key, if given, names the entry of
        the argument under the decision matrix that a click chooses
        (see review.js).

        """

        if id_item not in self.set_pick:
            return node
        name = cc_public.web.light.chain(id_item)
        return htpy.a({'data-key': key} if key else {},
                      href = '#' + name, class_ = 'pick ' + cc_public.web.light.show(name))[node]

    # -------------------------------------------------------------------------
    def _node_option(self, id_option: str, y: float) -> None:
        """
        Add the circle of id_option at y, with its title to its left.

        """

        list_line = _lines(self.graph.title(id_option), CHARS_OPTION)
        y_first   = y + 5 - LINE_OPTION * (len(list_line) - 1) / 2
        x_title   = X_OPTION - RADIUS_OPTION - 12
        node      = htpy.g(class_ = self._css(KIND_OPTION,
                                              cc_public.web.light.css(self.map_sign[id_option])),
                           id     = self._id(id_option))[
            htpy.title[self.graph.title(id_option)],
            htpy.circle(cx = _num(X_OPTION), cy = _num(y), r = str(RADIUS_OPTION),
                        class_ = 'shape'),
            [htpy.text(x = _num(x_title), y = _num(y_first + LINE_OPTION * index),
                       class_ = 'name')[line]
             for (index, line) in enumerate(list_line)]]
        self.list_node.append(self._pick(id_option, node))
        self._tally(id_option, y)

    # -------------------------------------------------------------------------
    def _tally(self, id_option: str, y: float) -> None:
        """
        Add, inside the circle of id_option at y, how many units of
        weight support it and how many challenge it. Each count lights
        the chains that reach the option in its role while it is
        hovered over, and pins them when it is clicked.

        """

        list_unit = self.outline.units(option = id_option)
        list_css  = cc_public.web.light.css(self.map_sign[id_option])
        for (index, role) in enumerate((ROLE_FOR, ROLE_AGAINST)):
            count = sum(1 for unit in list_unit if unit.role == role)
            name  = cc_public.web.light.chain(id_option, role)
            css   = ' '.join(['tally', 'tally-' + role, cc_public.web.light.CSS_DIMS, *list_css,
                              cc_public.web.light.show(name)])
            self.list_node.append(htpy.a(href = '#' + name, class_ = css)[
                htpy.title['{count} {verb} this'.format(
                    count = count, verb = 'support' if role == ROLE_FOR else 'challenge')],
                htpy.text(x = _num(X_OPTION), y = _num(y - 2 + 14 * index))[
                    '{count}{mark}'.format(count = count, mark = MAP_MARK[role])]])

    # -------------------------------------------------------------------------
    def _node_concern(self, id_concern: str, x: float, y: float, list_css: list[str]) -> None:
        """
        Add the port of id_concern at x, y: a small circle, named by a
        label above the other marks only while it is lit.

        """

        name = cc_public.web.light.chain(id_concern)
        css  = self._css(KIND_CONCERN, list_css + [cc_public.web.light.show(name)])
        self.list_node.append(htpy.g(class_ = css, id = self._id(id_concern))[
            htpy.title[self.graph.title(id_concern)],
            htpy.circle(cx = _num(x), cy = _num(y), r = str(RADIUS_CONCERN + 5), class_ = 'area'),
            htpy.circle(cx = _num(x), cy = _num(y), r = str(RADIUS_CONCERN), class_ = 'shape')])
        self.list_label.append(htpy.text(x = _num(x + RADIUS_CONCERN + 5),
                                         y = _num(y - RADIUS_CONCERN - 3),
                                         class_ = 'concern ' + cc_public.web.light.show(name))[
            self.graph.title(id_concern)])

    # -------------------------------------------------------------------------
    def _node_annotation(self,
                         id_annotation: str,
                         x:             float,
                         y:             float,
                         is_parent:     bool,
                         key:           str) -> None:
        """
        Add a copy of the circle of id_annotation at x, y, with its
        number inside and its title above it if is_parent, and
        otherwise to its right. key names its entry under the matrix.

        """

        number = str(self.outline.map_number[id_annotation])
        title  = self.graph.title(id_annotation)
        if is_parent:
            text  = htpy.text(x = _num(x), y = _num(y - RADIUS_ANNOTATION - 7),
                              class_ = 'name above')[title]
            right = x + WIDTH_CHAR * len(title) / 2
        else:
            text  = htpy.text(x = _num(x + RADIUS_ANNOTATION + 8), y = _num(y + 4),
                              class_ = 'name beside')[title]
            right = x + RADIUS_ANNOTATION + 8 + WIDTH_CHAR * len(title)
        self.right = max(self.right, right)
        node = htpy.g(class_ = self._css(KIND_ANNOTATION,
                                         cc_public.web.light.css(self.map_sign[id_annotation])),
                      id     = self._id(id_annotation))[
            htpy.title['{number} {title}'.format(number = number, title = title)],
            htpy.circle(cx = _num(x), cy = _num(y), r = str(RADIUS_ANNOTATION), class_ = 'shape'),
            htpy.text(x = _num(x), y = _num(y + 3.5), class_ = 'number')[number],
            text]
        self.list_node.append(self._pick(id_annotation, node, key))


# -----------------------------------------------------------------------------
def figure(graph: Graph, outline: Outline) -> typing.Any:
    """
    Return the graph of the argument in outline, a tree for each
    option.

    Hovering over or clicking an option or an annotation lights every
    chain into it and dims the rest; each annotation in the chain is
    shaded by its net effect, the product of the roles along its paths.
    Each copy of an annotation lights with the others. Hovering over a
    concern lights the chains through it, on every option, and names
    each of its ports. Clicking anywhere else in the graph unpins: the
    link names no element, so the page does not move. The page holds
    the rules that light the chains and the elements that pin them (see
    cc_public.web.light).

    The chains are traced through a hub for each concern on each
    option, in each role, so an annotation lights for the options
    it argues on and no others.

    """

    tree   = _Tree(graph, outline)
    top    = -MARGIN - GAP_PARENT
    left   = -MARGIN
    width  = tree.right + 2 * MARGIN
    height = tree.y - top
    return htpy.figure(class_ = 'map network')[
        htpy.svg(class_  = cc_public.web.light.CSS_REGION,
                 viewBox = '{left} {top} {width} {height}'.format(left   = left,
                                                                  top    = _num(top),
                                                                  width  = _num(width),
                                                                  height = _num(height)),
                 width   = _num(width),
                 height  = _num(height),
                 role    = 'img')[
            htpy.a(href = '#' + cc_public.web.light.KEY_UNPIN, class_ = 'unpin')[
                htpy.rect(x = str(left), y = _num(top), width = _num(width),
                          height = _num(height))],
            htpy.g(class_ = 'edges')[tree.list_path],
            htpy.g(class_ = 'nodes')[tree.list_node],
            htpy.g(class_ = 'labels')[tree.list_label]]]


# -----------------------------------------------------------------------------
def names(outline: Outline) -> list[str]:
    """
    Return the names of the chains the graph of the argument in outline
    can light: one into each option or annotation in each role, each
    option or annotation that is picked, and each concern.

    """

    (map_name, set_pick, list_concern) = _chains(*_graph(outline))
    return (list(map_name.values())
            + [cc_public.web.light.chain(id_item) for id_item in sorted(set_pick)]
            + [cc_public.web.light.chain(id_concern) for id_concern in list_concern])


# -----------------------------------------------------------------------------
def _graph(outline: Outline) -> tuple:
    """
    Return the kind of each option and annotation of the argument in
    outline, and its edges.

    """

    list_row = sorted(outline.map_number, key = outline.map_number.get)
    map_kind = ({id_annotation: KIND_ANNOTATION for id_annotation in list_row}
                | {id_option: KIND_OPTION for id_option in outline.list_option})
    return (map_kind, _edges(outline, list_row))


# -----------------------------------------------------------------------------
def _chains(map_kind: dict[str, str], list_edge: list[tuple[str, str, str]]) -> tuple:
    """
    Return the name of the chains into each option and annotation in
    each role, the options and annotations a click picks, and the
    concerns argued for.

    """

    set_into = {edge[1:] for edge in list_edge}
    map_name = {(id_item, role): cc_public.web.light.chain(id_item, role)
                for id_item in map_kind for role in (ROLE_FOR, ROLE_AGAINST)
                if (id_item, role) in set_into}
    set_pick = ({id_to for (_, id_to, _) in list_edge if id_to in map_kind}
                | {id_item for (id_item, kind) in map_kind.items() if kind == KIND_ANNOTATION})
    list_concern = []
    for (_, id_to, _) in list_edge:
        if DELIM_HUB in id_to and _unhub(id_to) not in list_concern:
            list_concern.append(_unhub(id_to))
    return (map_name, set_pick, list_concern)


# -----------------------------------------------------------------------------
def _edges(outline: Outline, list_row: list[str]) -> list[tuple[str, str, str]]:
    """
    Return the edges of the argument, each from its source to its target
    with its role: from an annotation to what it answers, from an
    annotation to the hub of each concern it argues for on an option
    in each role, and from each hub to its option in that role. The
    edge into a hub passes the effect on unchanged.

    """

    list_edge = []
    for id_annotation in list_row:
        for (id_target, role) in _answered(outline, id_annotation):
            list_edge.append((id_annotation, id_target, role))
        for unit in outline.units(annotation = id_annotation):
            edge = (id_annotation, _hub(unit.option, unit.concern, unit.role), ROLE_LINK)
            if edge not in list_edge:
                list_edge.append(edge)
    for unit in outline.list_unit:
        edge = (_hub(unit.option, unit.concern, unit.role), unit.option, unit.role)
        if edge not in list_edge:
            list_edge.append(edge)
    return list_edge


# -----------------------------------------------------------------------------
def _lighting(list_edge:    list[tuple[str, str, str]],
              map_kind:     dict[str, str],
              map_name:     dict[tuple[str, str], str],
              set_pick:     set[str],
              list_concern: list[str]) -> tuple:
    """
    Return, for each option, annotation and hub, and for each edge,
    the names of the chains that light it, each with the net effects
    that shade it there. The chains of a concern are those through its
    hubs, each net effect taken on to the option of the hub. The
    chain of a picked item also holds, unshaded, the path onward from
    it to each option it bears on, as in the Sankey diagram. A hub
    is never shaded.

    """

    map_sign_node = ({id_item: {} for id_item in map_kind}
                     | {edge[0]: {} for edge in list_edge if DELIM_HUB in edge[0]})
    map_sign_edge = {edge: {} for edge in list_edge}
    list_light    = ([(name, port[0], {port[1]}) for (port, name) in map_name.items()]
                     + [(cc_public.web.light.chain(id_item), id_item, None) for id_item in map_kind
                        if id_item in set_pick])
    for (key, id_item_lit, set_role) in list_light:
        cc_public.web.light.add(map_sign_node[id_item_lit], key, None)
        _light(map_sign_node, map_sign_edge, key, *_chain(list_edge, id_item_lit, set_role),
               ROLE_FOR)
        if set_role is None:
            for edge in _onward(list_edge, id_item_lit):
                cc_public.web.light.add(map_sign_edge[edge], key, None)
                cc_public.web.light.add(map_sign_node[edge[1]], key, None)
    for id_concern in list_concern:
        key = cc_public.web.light.chain(id_concern)
        for edge in list_edge:
            (id_hub, id_option, role) = edge
            if DELIM_HUB in id_hub and _unhub(id_hub) == id_concern:
                cc_public.web.light.add(map_sign_node[id_hub], key, None)
                cc_public.web.light.add(map_sign_node[id_option], key, None)
                cc_public.web.light.add(map_sign_edge[edge], key, None)
                _light(map_sign_node, map_sign_edge, key, *_chain(list_edge, id_hub, None), role)
    return (map_sign_node, map_sign_edge)


# -----------------------------------------------------------------------------
def _light(map_sign_node: dict[str, dict[str, set[str]]],
           map_sign_edge: dict[tuple, dict[str, set[str]]],
           key:           str,
           map_sign:      dict[str, set[str]],
           set_edge:      set[tuple],
           role:          str) -> None:
    """
    Put the nodes of map_sign and the edges of set_edge in the chain at
    key, each node shaded by its net effect carried on through role. A
    hub is put in the chain unshaded.

    """

    for (id_item, set_sign) in map_sign.items():
        if DELIM_HUB in id_item:
            cc_public.web.light.add(map_sign_node[id_item], key, None)
            continue
        for sign in set_sign:
            cc_public.web.light.add(map_sign_node[id_item], key,
                                    cc_public.web.light.times(role, sign))
    for edge in set_edge:
        cc_public.web.light.add(map_sign_edge[edge], key, None)


# -----------------------------------------------------------------------------
def _onward(list_edge: list[tuple[str, str, str]], id_node: str) -> set[tuple]:
    """
    Return the edges of the paths from id_node onward: to what it
    answers, through the hubs it argues through, to the options.

    """

    set_edge  = set()
    list_todo = [id_node]
    set_seen  = {id_node}
    while list_todo:
        id_from = list_todo.pop()
        for edge in list_edge:
            if edge[0] == id_from:
                set_edge.add(edge)
                if edge[1] not in set_seen:
                    set_seen.add(edge[1])
                    list_todo.append(edge[1])
    return set_edge


# -----------------------------------------------------------------------------
def _merged(list_map_sign: list[dict[str, set[str]]]) -> dict[str, set[str]]:
    """
    Return the chains of all the marks of list_map_sign, as of one mark.

    """

    map_sign = {}
    for map_one in list_map_sign:
        for (name, set_sign) in map_one.items():
            map_sign.setdefault(name, set()).update(set_sign)
    return map_sign


# -----------------------------------------------------------------------------
def _hub(id_option: str, id_concern: str, role: str) -> str:
    """
    Return the id of the hub of id_concern argued in role on
    id_option: the bundle of edges it carries through the port of
    the concern.

    """

    return DELIM_HUB.join((id_option, id_concern, role))


# -----------------------------------------------------------------------------
def _unhub(id_item: str) -> str:
    """
    Return the concern of id_item if it is a hub, and otherwise
    id_item.

    """

    if DELIM_HUB not in id_item:
        return id_item
    return id_item.split(DELIM_HUB)[1]


# -----------------------------------------------------------------------------
def _chain(list_edge: list[tuple[str, str, str]],
           id_node:   str,
           set_role:  set[str] | None) -> tuple[dict[str, set[str]], set[tuple]]:
    """
    Return the nodes whose paths reach id_node through edges of a role
    in set_role (any role if None), each with the net effects of those
    paths on id_node, and the edges of the paths. A path is for id_node
    when it holds an even number of challenges.

    """

    map_sign  = {}
    set_edge  = set()
    list_todo = [(id_from, role != ROLE_AGAINST, {id_node}, (id_from, id_to, role))
                 for (id_from, id_to, role) in list_edge
                 if id_to == id_node and (set_role is None or role in set_role)]
    while list_todo:
        (id_item, is_for, set_path, edge) = list_todo.pop()
        if id_item in set_path:
            continue
        set_edge.add(edge)
        map_sign.setdefault(id_item, set()).add(ROLE_FOR if is_for else ROLE_AGAINST)
        list_todo.extend((id_from, is_for == (role != ROLE_AGAINST), set_path | {id_item},
                          (id_from, id_to, role))
                         for (id_from, id_to, role) in list_edge
                         if id_to == id_item)
    return (map_sign, set_edge)


# -----------------------------------------------------------------------------
def _answered(outline: Outline, id_annotation: str) -> list[tuple[str, str]]:
    """
    Return the annotations id_annotation answers, each with its role.

    """

    return [(id_target, role)
            for (id_target, list_answer) in outline.map_answer.items()
            for (id_answer, role) in list_answer
            if id_answer == id_annotation and id_target in outline.map_number]


# -----------------------------------------------------------------------------
def _lines(text: str, chars: int) -> list[str]:
    """
    Return text broken into lines of at most chars, but for a word
    longer than that.

    """

    list_line = ['']
    for word in text.split():
        if list_line[-1] and len(list_line[-1]) + 1 + len(word) > chars:
            list_line.append('')
        list_line[-1] = (list_line[-1] + ' ' + word).strip()
    return list_line


# -----------------------------------------------------------------------------
def _num(value: float) -> str:
    """
    Return value as a coordinate of the drawing.

    """

    return '{value:.1f}'.format(value = value)
