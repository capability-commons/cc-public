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
                        each decision and each annotation once, joined
                        through a small node for each concern argued
                        on each decision.
description:            |
                        Decisions stand on the left. Beside them stand
                        the concerns argued on each decision, as small
                        circles, much as the concerns of the Sankey
                        diagram gather its bands. An annotation that
                        argues on a decision stands in the first
                        column to the right, and joins the circle of
                        each concern it argues for on that decision.
                        An annotation that answers another stands one
                        column to the right of the one it answers, and
                        rows follow the numbers of the annotations, so
                        an answer sits just below what it answers.
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
WIDTH_CONCERN     = 170
X_CONCERN         = WIDTH_NODE + 90
X_FIRST           = X_CONCERN + WIDTH_CONCERN + 110
CHARS_LINE        = 34
MARGIN            = 8
RADIUS_PORT       = 4.5
KEY_UNPIN         = 'unpin'
KEY_PICK          = 'pick-'
DELIM_HUB         = '--'
ROLE_FOR          = cc_public.web.sankey.ROLE_FOR
ROLE_AGAINST      = cc_public.web.sankey.ROLE_AGAINST
ROLE_LINK         = 'link'
KIND_DECISION     = 'decision'
KIND_CONCERN      = 'concern'
KIND_ANNOTATION   = 'annotation'


# -----------------------------------------------------------------------------
def figure(graph: Graph, outline: Outline) -> typing.Any:
    """
    Return the graph of the argument in outline.

    A decision or an annotation has a port on its right for what
    supports it and one for what challenges it. Hovering over a port, or following its
    link, lights the chain of annotations that reaches it and dims the
    rest; each annotation in the chain is shaded by its net effect, the
    product of the roles along its paths. Hovering over or clicking a
    decision or an annotation does the same for every chain into it.
    Concerns are bundles rather than nodes: each edge into a concern
    leaves it again, in the same role, for its decision. They light
    with the chains through them, but are never shaded and do not
    respond themselves. Clicking
    anywhere else in the graph unpins: the link names no element, so
    the page does not move.

    The chains are traced through a hub for each concern on each
    decision, so an annotation lights for the decisions it argues on
    and no others, but each concern is drawn once.

    """

    map_kind  = {}
    map_place = {}
    map_depth = _depths(outline)
    list_row  = sorted(outline.map_number, key = outline.map_number.get)
    for (index, id_annotation) in enumerate(list_row):
        map_kind[id_annotation]  = KIND_ANNOTATION
        map_place[id_annotation] = (X_FIRST + map_depth[id_annotation] * (WIDTH_NODE + GAP_COLUMN),
                                    index * ROW + HEIGHT_NODE / 2)

    list_edge = _edges(outline, list_row)

    for (id_concern, y) in _concern_rows(outline, map_place).items():
        map_kind[id_concern]  = KIND_CONCERN
        map_place[id_concern] = (X_CONCERN, y)
    for (id_decision, y) in _decision_rows(outline, map_place).items():
        map_kind[id_decision]  = KIND_DECISION
        map_place[id_decision] = (0, y)

    list_port = [(id_item, role) for id_item in map_place for role in (ROLE_FOR, ROLE_AGAINST)
                 if (id_item, role) in {edge[1:] for edge in list_edge}]
    map_key   = {port: 'port-{id}-{role}'.format(id = port[0], role = port[1])
                 for port in list_port}
    set_pick  = {id_to for (_, id_to, _) in list_edge if id_to in map_place}

    (list_drawn, map_css_node, map_css_edge, list_light) = _lighting(
        list_edge, map_place, map_key, set_pick)

    list_path = [_edge(map_kind, map_place, edge, map_css_edge[edge]) for edge in list_drawn]
    list_node = [_node(graph, outline, map_kind[id_item], id_item, map_place[id_item],
                       map_css_node[id_item], id_item in set_pick)
                 for id_item in map_place]
    list_dot  = [_port(map_kind[port[0]], map_place[port[0]], port[1], key)
                 for (port, key) in map_key.items()]

    width  = max(x for (x, _) in map_place.values()) + WIDTH_NODE + 2 * MARGIN
    height = max(y for (_, y) in map_place.values()) + HEIGHT_NODE / 2 + 2 * MARGIN
    top    = min(y for (_, y) in map_place.values()) - HEIGHT_NODE / 2 - MARGIN
    return htpy.figure(class_ = 'map network')[
        htpy.style[_style([key for (key, _, _) in list_light])],
        htpy.svg(viewBox = '{left} {top} {width} {height}'.format(left   = -MARGIN,
                                                                  top    = _num(top),
                                                                  width  = width,
                                                                  height = _num(height - top)),
                 width   = str(width),
                 height  = _num(height - top),
                 role    = 'img')[
            htpy.a(href = '#' + KEY_UNPIN, class_ = 'unpin')[
                htpy.rect(x = str(-MARGIN), y = _num(top), width = str(width),
                          height = _num(height - top))],
            htpy.g(class_ = 'edges')[list_path],
            htpy.g(class_ = 'nodes')[list_node],
            htpy.g(class_ = 'ports')[list_dot]]]


# -----------------------------------------------------------------------------
def _edges(outline: Outline, list_row: list[str]) -> list[tuple[str, str, str]]:
    """
    Return the edges of the argument, each from its source to its target
    with its role: from an annotation to what it answers, from an
    annotation to the hub of each concern it argues for on a decision
    in each role, and from each hub to its decision in that role. The
    edge into a hub passes the effect on unchanged.

    """

    list_edge = []
    for id_annotation in list_row:
        for (id_target, role) in _answered(outline, id_annotation):
            list_edge.append((id_annotation, id_target, role))
        for unit in outline.units(annotation = id_annotation):
            edge = (id_annotation, _hub(unit.decision, unit.concern, unit.role), ROLE_LINK)
            if edge not in list_edge:
                list_edge.append(edge)
    for unit in outline.list_unit:
        edge = (_hub(unit.decision, unit.concern, unit.role), unit.decision, unit.role)
        if edge not in list_edge:
            list_edge.append(edge)
    return list_edge


# -----------------------------------------------------------------------------
def _lighting(list_edge: list[tuple[str, str, str]],
              map_place: dict[str, tuple[float, float]],
              map_key:   dict[tuple[str, str], str],
              set_pick:  set[str]) -> tuple:
    """
    Return the edges as drawn, the classes of each node and drawn edge
    that say which chains light it and with what net effect, and the
    keys of the chains with the node and roles each is traced from.

    """

    list_drawn = []
    for edge in list_edge:
        if _drawn(edge) not in list_drawn:
            list_drawn.append(_drawn(edge))
    map_css_node = {id_item: [] for id_item in map_place}
    map_css_edge = {edge: [] for edge in list_drawn}
    list_light   = ([(key, port[0], {port[1]}) for (port, key) in map_key.items()]
                    + [(KEY_PICK + id_item, id_item, None) for id_item in map_place
                       if id_item in set_pick])
    for (key, id_item_lit, set_role) in list_light:
        (map_sign, set_edge) = _chain(list_edge, id_item_lit, set_role)
        map_css_node[id_item_lit].append(key)
        for (id_item, set_sign) in map_sign.items():
            id_drawn = _unhub(id_item)
            if id_drawn != id_item:
                if key not in map_css_node[id_drawn]:
                    map_css_node[id_drawn].append(key)
                continue
            sign = set_sign.pop() if len(set_sign) == 1 else 'mixed'
            map_css_node[id_item].extend([key, key + '-' + sign])
        for edge in set_edge:
            if key not in map_css_edge[_drawn(edge)]:
                map_css_edge[_drawn(edge)].append(key)
    return (list_drawn, map_css_node, map_css_edge, list_light)


# -----------------------------------------------------------------------------
def _hub(id_decision: str, id_concern: str, role: str) -> str:
    """
    Return the id of the hub of id_concern argued in role on
    id_decision: the bundle of edges it carries through the box of the
    concern.

    """

    return DELIM_HUB.join((id_decision, id_concern, role))


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
def _drawn(edge: tuple[str, str, str]) -> tuple[str, str, str]:
    """
    Return edge as it is drawn: through the concern of a hub rather
    than the hub, and in the role of the hub.

    """

    (id_from, id_to, role) = edge
    if DELIM_HUB in id_to:
        role = id_to.split(DELIM_HUB)[2]
    return (_unhub(id_from), _unhub(id_to), role)


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
def _style(list_key: list[str]) -> str:
    """
    Return the rules that light the chain at each key while it is
    hovered over or is the target of the address. Hovering wins over
    the target.

    """

    list_rule = []
    for key in list_key:
        for (state, guard) in ((':hover', ''),
                               (':target', ':not(:has(.port:hover, .pick:hover))')):
            scope = '.network svg:has(#{key}{state}){guard}'.format(key   = key,
                                                                    state = state,
                                                                    guard = guard)
            list_rule.append('{scope} .{key} {{ opacity: 1; }}'.format(scope = scope, key = key))
            for sign in (ROLE_FOR, ROLE_AGAINST, 'mixed'):
                rule = '{scope} .{key}-{sign} .shape {{ fill: var(--net-{sign}); }}'
                list_rule.append(rule.format(scope = scope, key = key, sign = sign))
    return '\n'.join(list_rule)


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
def _concern_rows(outline:   Outline,
                  map_place: dict[str, tuple[float, float]]) -> dict[str, float]:
    """
    Return the row of each concern argued on: the middle of the
    annotations that argue for it, pushed apart so no two overlap.

    """

    map_mean = {}
    for id_concern in outline.list_concern:
        list_y = [map_place[unit.annotation][1] for unit in outline.units(concern = id_concern)]
        if list_y:
            map_mean[id_concern] = sum(list_y) / len(list_y)
    map_y  = {}
    y_last = None
    for id_concern in sorted(map_mean, key = map_mean.get):
        y = map_mean[id_concern]
        if y_last is not None and y < y_last + ROW:
            y = y_last + ROW
        map_y[id_concern] = y
        y_last            = y
    return map_y


# -----------------------------------------------------------------------------
def _decision_rows(outline:   Outline,
                   map_place: dict[str, tuple[float, float]]) -> dict[str, float]:
    """
    Return the row of each decision: the middle of the concerns argued
    on it, each counted once for each unit, pushed apart so no two
    overlap.

    """

    map_y = {}
    for id_decision in outline.list_decision:
        list_y = [map_place[unit.concern][1] for unit in outline.units(decision = id_decision)]
        map_y[id_decision] = sum(list_y) / len(list_y) if list_y else 0
    y_last = None
    for id_decision in sorted(map_y, key = map_y.get):
        if y_last is not None and map_y[id_decision] < y_last + ROW:
            map_y[id_decision] = y_last + ROW
        y_last = map_y[id_decision]
    return map_y


# -----------------------------------------------------------------------------
def _edge(map_kind:  dict[str, str],
          map_place: dict[str, tuple[float, float]],
          edge:      tuple[str, str, str],
          list_css:  list[str]) -> typing.Any:
    """
    Return the path of edge, from the left of its source to the port of
    its role on its target.

    """

    (id_from, id_to, role) = edge
    (x1, y1) = map_place[id_from]
    if map_kind[id_from] == KIND_CONCERN:
        y1 += (-1 if role == ROLE_FOR else 1) * HEIGHT_NODE * 0.2
    (x2, y2) = _inlet(map_kind[id_to], map_place[id_to], role)
    x_mid    = (x1 + x2) / 2
    path     = 'M{x1},{y1} C{xm},{y1} {xm},{y2} {x2},{y2}'.format(x1 = _num(x1),
                                                                y1 = _num(y1),
                                                                xm = _num(x_mid),
                                                                x2 = _num(x2),
                                                                y2 = _num(y2))
    return htpy.path(d = path, class_ = ' '.join(['edge-' + role] + list_css))


# -----------------------------------------------------------------------------
def _inlet(kind: str, place: tuple[float, float], role: str) -> tuple[float, float]:
    """
    Return where an edge of role enters a node of kind at place: its
    port for role. A concern has no ports, but takes edges where its
    ports would be, and they leave its left at the same heights.

    """

    (x, y) = place
    offset = -1 if role == ROLE_FOR else 1
    width  = WIDTH_CONCERN if kind == KIND_CONCERN else WIDTH_NODE
    return (x + width, y + offset * HEIGHT_NODE * 0.2)


# -----------------------------------------------------------------------------
def _port(kind: str, place: tuple[float, float], role: str, key: str) -> typing.Any:
    """
    Return the port of role on the node of kind at place: a dot that
    links to the page with the chain into it lit.

    """

    (cx, cy) = _inlet(kind, place, role)
    return htpy.a(href = '#' + key, id = key, class_ = 'port port-' + role)[
        htpy.title['what {verb} this'.format(verb = 'supports' if role == ROLE_FOR
                                             else 'challenges')],
        htpy.circle(cx = _num(cx), cy = _num(cy), r = str(RADIUS_PORT))]


# -----------------------------------------------------------------------------
def _node(graph:    Graph,
          outline:  Outline,
          kind:     str,
          id_item:  str,
          place:    tuple[float, float],
          list_css: list[str],
          is_pick:  bool) -> typing.Any:
    """
    Return the node of kind for id_item at place. If is_pick, the node
    links to the page with every chain into it lit. A concern never
    does.

    """

    (x, y) = place
    css    = ' '.join(['node', kind] + list_css)
    if kind == KIND_CONCERN:
        node = htpy.g(class_ = css, id = 'node-' + id_item)[
            htpy.rect(x = _num(x), y = _num(y - HEIGHT_NODE / 2), width = str(WIDTH_CONCERN),
                      height = str(HEIGHT_NODE), class_ = 'shape'),
            htpy.text(x = _num(x + WIDTH_CONCERN / 2), y = _num(y + 4.5), class_ = 'name')[
                graph.title(id_item)]]
    else:
        if kind == KIND_ANNOTATION:
            label = '#{number} {title}'.format(number = outline.map_number[id_item],
                                               title  = graph.title(id_item))
        else:
            label = graph.title(id_item)
        list_line = _lines(label)
        y_first   = y + 4.5 - 7 * (len(list_line) - 1)
        node      = htpy.g(class_ = css, id = 'node-' + id_item)[
            htpy.title[label],
            htpy.rect(x = _num(x), y = _num(y - HEIGHT_NODE / 2), width = str(WIDTH_NODE),
                      height = str(HEIGHT_NODE), rx = '3', class_ = 'shape'),
            [htpy.text(x = _num(x + 8), y = _num(y_first + 14 * index), class_ = 'name')[line]
             for (index, line) in enumerate(list_line)]]
    if not is_pick:
        return node
    key = KEY_PICK + id_item
    return htpy.a(href = '#' + key, id = key, class_ = 'pick')[node]


# -----------------------------------------------------------------------------
def _lines(text: str) -> list[str]:
    """
    Return text broken into at most two lines that fit a node, the
    second cut short if need be.

    """

    list_line = ['']
    for word in text.split():
        if list_line[-1] and len(list_line[-1]) + 1 + len(word) > CHARS_LINE:
            if len(list_line) == 2:
                list_line[-1] = list_line[-1][:CHARS_LINE - 1].rstrip() + '…'
                return list_line
            list_line.append('')
        list_line[-1] = (list_line[-1] + ' ' + word).strip()
    return list_line


# -----------------------------------------------------------------------------
def _num(value: float) -> str:
    """
    Return value as a coordinate of the drawing.

    """

    return '{value:.1f}'.format(value = value)
