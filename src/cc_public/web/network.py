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
                        Draw the argument on an issue as a graph, with
                        each decision and each annotation once, and an
                        edge for each support and challenge.
description:            |
                        Decisions stand on the left. An annotation
                        that argues on a decision stands in the first
                        column to their right, and an annotation that
                        answers another stands one column to the right
                        of the one it answers. Rows follow the numbers
                        of the annotations, so an answer sits just
                        below what it answers. Each edge runs from an
                        annotation to what it supports or challenges.
                        The concerns an annotation argues for are
                        named under its title.
relation:               []

...
"""


import typing

import htpy

import cc_public.web.argument
import cc_public.web.sankey


Graph   = cc_public.web.argument.Graph
Outline = cc_public.web.sankey.Outline

# Sizes, in units of the drawing.
#
WIDTH_NODE        = 230
HEIGHT_NODE       = 34
ROW               = 44
GAP_COLUMN        = 70
X_FIRST           = WIDTH_NODE + 2 * GAP_COLUMN
CHARS_TITLE       = 32
MARGIN            = 8
RADIUS_PORT       = 4.5
KEY_UNPIN         = 'unpin'
KEY_PICK          = 'pick-'
ROLE_FOR          = cc_public.web.sankey.ROLE_FOR
ROLE_AGAINST      = cc_public.web.sankey.ROLE_AGAINST


# -----------------------------------------------------------------------------
def figure(graph: Graph, outline: Outline) -> typing.Any:
    """
    Return the graph of the argument in outline.

    Each node has a port on its right for what supports it and one for
    what challenges it. Hovering over a port, or following its link,
    lights the chain of annotations that reaches it and dims the rest;
    each annotation in the chain is shaded by its net effect on the
    node, the product of the roles along its paths. Clicking a node
    lights both its chains at once, each by its net effect on the
    node. Clicking anywhere
    else in the graph unpins it: the link names no element, so the page
    does not move.

    """

    map_depth = _depths(outline)
    list_row  = sorted(outline.map_number, key = outline.map_number.get)
    map_place = {}
    for (index, id_annotation) in enumerate(list_row):
        map_place[id_annotation] = (X_FIRST + map_depth[id_annotation] * (WIDTH_NODE + GAP_COLUMN),
                                    index * ROW)
    for (id_decision, y) in _decision_rows(outline, map_place).items():
        map_place[id_decision] = (0, y)

    list_edge = [(id_annotation, id_target, role)
                 for id_annotation in list_row
                 for (id_target, role) in _targets(outline, id_annotation)]
    list_port = sorted({(id_target, role) for (_, id_target, role) in list_edge},
                       key = lambda port: (list(map_place).index(port[0]), port[1] != ROLE_FOR))
    map_key   = {port: 'port-{id}-{role}'.format(id = port[0], role = port[1])
                 for port in list_port}

    map_pick  = {}
    for port in list_port:
        map_pick.setdefault(port[0], []).append(port)

    map_css_node = {id_item: [] for id_item in map_place}
    map_css_edge = {edge: [] for edge in list_edge}
    list_light   = ([(key, [port]) for (port, key) in map_key.items()]
                    + [(KEY_PICK + id_item, list_port_own)
                       for (id_item, list_port_own) in map_pick.items()])
    for (key, list_port_lit) in list_light:
        map_sign = {}
        for port in list_port_lit:
            (map_sign_port, set_edge) = _chain(list_edge, port)
            for (id_item, set_sign) in map_sign_port.items():
                map_sign.setdefault(id_item, set()).update(set_sign)
            for edge in set_edge:
                if key not in map_css_edge[edge]:
                    map_css_edge[edge].append(key)
        map_css_node[list_port_lit[0][0]].append(key)
        for (id_item, set_sign) in map_sign.items():
            sign = set_sign.pop() if len(set_sign) == 1 else 'mixed'
            map_css_node[id_item].extend([key, key + '-' + sign])

    list_path = [_edge(map_place[id_from], map_place[id_to], role, map_css_edge[edge])
                 for edge in list_edge
                 for (id_from, id_to, role) in [edge]]
    list_node = [_node(graph, outline, id_item, map_place[id_item], map_css_node[id_item],
                       id_item in map_pick)
                 for id_item in map_place]
    list_dot  = [_port(map_place[port[0]], port[1], key) for (port, key) in map_key.items()]

    width  = max(x for (x, _) in map_place.values()) + WIDTH_NODE + 2 * MARGIN
    height = max(y for (_, y) in map_place.values()) + HEIGHT_NODE + 2 * MARGIN
    return htpy.figure(class_ = 'map network')[
        htpy.style[_style([key for (key, _) in list_light])],
        htpy.svg(viewBox = '{left} {left} {width} {height}'.format(left   = -MARGIN,
                                                                   width  = width,
                                                                   height = height),
                 width   = str(width),
                 height  = str(height),
                 role    = 'img')[
            htpy.a(href = '#' + KEY_UNPIN, class_ = 'unpin')[
                htpy.rect(x = str(-MARGIN), y = str(-MARGIN), width = str(width),
                          height = str(height))],
            htpy.g(class_ = 'edges')[list_path],
            htpy.g(class_ = 'nodes')[list_node],
            htpy.g(class_ = 'ports')[list_dot]]]


# -----------------------------------------------------------------------------
def _chain(list_edge: list[tuple[str, str, str]],
           port:      tuple[str, str]) -> tuple[dict[str, set[str]], set[tuple]]:
    """
    Return the annotations whose paths reach port, each with the net
    effects of those paths on the node of port, and the edges of the
    paths. A path is for the node when it holds an even number of
    challenges, counting the role of port itself.

    """

    map_sign = {}
    set_edge = set()
    list_todo = [(id_from, role == ROLE_FOR, {port[0]}, (id_from, id_to, role))
                 for (id_from, id_to, role) in list_edge
                 if (id_to, role) == port]
    while list_todo:
        (id_item, is_for, set_path, edge) = list_todo.pop()
        if id_item in set_path:
            continue
        set_edge.add(edge)
        map_sign.setdefault(id_item, set()).add(ROLE_FOR if is_for else ROLE_AGAINST)
        list_todo.extend((id_from, is_for == (role == ROLE_FOR), set_path | {id_item},
                          (id_from, id_to, role))
                         for (id_from, id_to, role) in list_edge
                         if id_to == id_item)
    return (map_sign, set_edge)


# -----------------------------------------------------------------------------
def _style(list_key: list[str]) -> str:
    """
    Return the rules that light the chain at each key while it is the
    target of the address, or, for a port, while it is hovered over. A
    hovered port wins over the target.

    """

    list_rule = []
    for key in list_key:
        list_state = [(':target', ':not(:has(.port:hover))')]
        if not key.startswith(KEY_PICK):
            list_state.append((':hover', ''))
        for (state, guard) in list_state:
            scope = '.network svg:has(#{key}{state}){guard}'.format(key   = key,
                                                                    state = state,
                                                                    guard = guard)
            list_rule.append('{scope} .{key} {{ opacity: 1; }}'.format(scope = scope, key = key))
            for sign in (ROLE_FOR, ROLE_AGAINST, 'mixed'):
                list_rule.append('{scope} .{key}-{sign} rect {{ fill: var(--net-{sign}); }}'.format(
                    scope = scope, key = key, sign = sign))
    return '\n'.join(list_rule)


# -----------------------------------------------------------------------------
def _targets(outline: Outline, id_annotation: str) -> list[tuple[str, str]]:
    """
    Return what id_annotation supports or challenges, decisions and
    annotations alike, each with its role.

    """

    set_seen = set()
    list_out = []
    for unit in outline.units(annotation = id_annotation):
        if (unit.decision, unit.role) not in set_seen:
            set_seen.add((unit.decision, unit.role))
            list_out.append((unit.decision, unit.role))
    for (id_target, list_answer) in outline.map_answer.items():
        for (id_answer, role) in list_answer:
            if id_answer == id_annotation and id_target in outline.map_number:
                list_out.append((id_target, role))
    return list_out


# -----------------------------------------------------------------------------
def _depths(outline: Outline) -> dict[str, int]:
    """
    Return the column of each annotation: 0 for one that answers no
    annotation, and otherwise one more than the deepest it answers.

    """

    map_answered = {}
    for (id_target, list_answer) in outline.map_answer.items():
        for (id_answer, _) in list_answer:
            map_answered.setdefault(id_answer, []).append(id_target)

    map_depth = {}

    def depth(id_annotation: str, set_path: set[str]) -> int:
        if id_annotation in map_depth:
            return map_depth[id_annotation]
        list_target = [id_target for id_target in map_answered.get(id_annotation, [])
                       if id_target not in set_path]
        value = 1 + max((depth(id_target, set_path | {id_annotation})
                         for id_target in list_target), default = -1)
        map_depth[id_annotation] = value
        return value

    for id_annotation in outline.map_number:
        depth(id_annotation, set())
    return map_depth


# -----------------------------------------------------------------------------
def _decision_rows(outline: Outline,
                   map_place: dict[str, tuple[float, float]]) -> dict[str, float]:
    """
    Return the row of each decision: the middle of the annotations
    that argue on it, pushed apart so no two overlap.

    """

    map_y = {}
    for id_decision in outline.list_decision:
        list_y = [map_place[unit.annotation][1] for unit in outline.units(decision = id_decision)]
        map_y[id_decision] = sum(list_y) / len(list_y) if list_y else 0
    y_last = None
    for id_decision in sorted(map_y, key = map_y.get):
        if y_last is not None and map_y[id_decision] < y_last + ROW:
            map_y[id_decision] = y_last + ROW
        y_last = map_y[id_decision]
    return map_y


# -----------------------------------------------------------------------------
def _edge(place_from: tuple[float, float],
          place_to:   tuple[float, float],
          role:       str,
          list_css:   list[str]) -> typing.Any:
    """
    Return an edge of role from the left of the node at place_from to
    the right of the node at place_to.

    """

    (x1, y1) = (place_from[0], place_from[1] + HEIGHT_NODE / 2)
    (x2, y2) = (place_to[0] + WIDTH_NODE + RADIUS_PORT, place_to[1] + _port_y(role))
    x_mid    = (x1 + x2) / 2
    path     = 'M{x1},{y1} C{xm},{y1} {xm},{y2} {x2},{y2}'.format(x1 = _num(x1),
                                                                y1 = _num(y1),
                                                                xm = _num(x_mid),
                                                                x2 = _num(x2),
                                                                y2 = _num(y2))
    return htpy.path(d = path, class_ = ' '.join(['edge-' + role] + list_css))


# -----------------------------------------------------------------------------
def _port(place: tuple[float, float], role: str, key: str) -> typing.Any:
    """
    Return the port of role on the node at place: a dot on its right
    that links to the page with the chain into it lit.

    """

    return htpy.a(href = '#' + key, id = key, class_ = 'port port-' + role)[
        htpy.title['what {verb} this'.format(verb = 'supports' if role == ROLE_FOR
                                             else 'challenges')],
        htpy.circle(cx = _num(place[0] + WIDTH_NODE), cy = _num(place[1] + _port_y(role)),
                    r = str(RADIUS_PORT))]


# -----------------------------------------------------------------------------
def _port_y(role: str) -> float:
    """
    Return how far below the top of a node its port of role sits.

    """

    return HEIGHT_NODE * (0.3 if role == ROLE_FOR else 0.7)


# -----------------------------------------------------------------------------
def _node(graph:    Graph,
          outline:  Outline,
          id_item:  str,
          place:    tuple[float, float],
          list_css: list[str],
          is_pick:  bool) -> typing.Any:
    """
    Return the node of id_item at place: a decision or an annotation.
    If is_pick, the node links to the page with both chains into it
    lit, as if both its ports were pinned.

    """

    (x, y)   = place
    title    = graph.title(id_item)
    if id_item in outline.map_number:
        css     = 'node annotation'
        label   = '#{number} {title}'.format(number = outline.map_number[id_item],
                                             title  = title)
        under   = ', '.join(graph.title(id_concern).lower()
                            for id_concern in sorted({unit.concern for unit
                                                      in outline.units(annotation = id_item)}))
    else:
        css     = 'node decision'
        label   = title
        under   = ''
    node = htpy.g(class_ = ' '.join([css] + list_css), id = 'node-' + id_item)[
        htpy.title[label],
        htpy.rect(x = _num(x), y = _num(y), width = str(WIDTH_NODE), height = str(HEIGHT_NODE),
                  rx = '3'),
        htpy.text(x = _num(x + 8), y = _num(y + (14 if under else 21)), class_ = 'name')[
            _cut(label)],
        htpy.text(x = _num(x + 8), y = _num(y + 28), class_ = 'note')[_cut(under)]
        if under else None]
    if not is_pick:
        return node
    key = KEY_PICK + id_item
    return htpy.a(href = '#' + key, id = key, class_ = 'pick')[node]


# -----------------------------------------------------------------------------
def _cut(text: str) -> str:
    """
    Return text cut to fit the width of a node.

    """

    if len(text) <= CHARS_TITLE:
        return text
    return text[:CHARS_TITLE - 1].rstrip() + '…'


# -----------------------------------------------------------------------------
def _num(value: float) -> str:
    """
    Return value as a coordinate of the drawing.

    """

    return '{value:.1f}'.format(value = value)
