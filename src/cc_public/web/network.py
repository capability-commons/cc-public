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
                        through a pipe for each concern argued on the
                        decisions.
description:            |
                        The drawing follows the diagrams of Mark
                        Lombardi: every decision and annotation is a
                        circle of one size with its title beneath, and
                        thin lines run between them with room to
                        spare. Decisions stand on the left. Beside
                        them stand the concerns argued on them, each a
                        pipe of two parallel rules that carries the
                        lines for and against it, much as the concerns
                        of the Sankey diagram gather its bands. An
                        annotation that argues on a decision stands in
                        the first column to the right, and joins the
                        pipe of each concern it argues for on that
                        decision. An annotation that answers another
                        stands one column to the right of the one it
                        answers, and rows follow the numbers of the
                        annotations, so an answer sits just below what
                        it answers.
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
RADIUS            = 22
ROW               = 124
ROW_STAGGER       = 62
ROW_CONCERN       = 64
COLUMN            = 250
X_DECISION        = 110
X_CONCERN         = 440
WIDTH_CONCERN     = 160
X_FIRST           = X_CONCERN + WIDTH_CONCERN + 200
GAP_RAIL          = 8
GAP_LANE          = 3.5
ANGLE_PORT        = 0.6
CHARS_LINE        = 24
LINE_TITLE        = 15
WIDTH_TITLE       = 180
MARGIN            = 16
RADIUS_PORT       = 3
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

    A decision or an annotation has a port on its upper right for what
    supports it and one on its lower right for what challenges it. Hovering over a port,
    or following its link, lights the chain of annotations that reaches
    it and dims the rest; each annotation in the chain is shaded by its
    net effect, the product of the roles along its paths. Hovering over
    or clicking a decision or an annotation does the same for every
    chain into it. Concerns are bundles rather than nodes: each edge
    into a concern leaves it again, in the same role, for its decision.
    They light with the chains through them and are never shaded;
    hovering over one lights the chains through it. Clicking anywhere
    else in the graph unpins: the link names no element, so the page
    does not move. The page holds the rules that light the chains and
    the elements that pin them (see cc_public.web.light).

    The chains are traced through a hub for each concern on each
    decision, so an annotation lights for the decisions it argues on
    and no others, but each concern is drawn once.

    """

    (map_kind, map_place, list_edge)         = _layout(outline)
    (map_name, set_pick, list_concern)       = _chains(map_kind, map_place, list_edge)
    (list_drawn, map_css_node, map_css_edge) = _lighting(
        list_edge, map_place, map_name, set_pick, list_concern)
    for id_concern in list_concern:
        map_css_node[id_concern] = [
            *map_css_node[id_concern],
            cc_public.web.light.show(cc_public.web.light.chain(id_concern))]

    list_path = [_edge(map_kind, map_place, edge, map_css_edge[edge]) for edge in list_drawn]
    list_node = [_node(graph, outline, map_kind[id_item], id_item, map_place[id_item],
                       map_css_node[id_item], id_item in set_pick)
                 for id_item in map_place]
    list_dot  = [_port(map_kind[port[0]], map_place[port[0]], port[1], name)
                 for (port, name) in map_name.items()]

    width  = max(x for (x, _) in map_place.values()) + WIDTH_TITLE / 2 + 2 * MARGIN
    height = max(y for (_, y) in map_place.values()) + RADIUS + 17 + 3 * LINE_TITLE + MARGIN
    top    = min(y for (_, y) in map_place.values()) - RADIUS - 2 * GAP_RAIL - MARGIN
    return htpy.figure(class_ = 'map network')[
        htpy.svg(class_  = cc_public.web.light.CSS_REGION,
                 viewBox = '{left} {top} {width} {height}'.format(left   = -MARGIN,
                                                                  top    = _num(top),
                                                                  width  = width,
                                                                  height = _num(height - top)),
                 width   = str(width),
                 height  = _num(height - top),
                 role    = 'img')[
            htpy.a(href = '#' + cc_public.web.light.KEY_UNPIN, class_ = 'unpin')[
                htpy.rect(x = str(-MARGIN), y = _num(top), width = str(width),
                          height = _num(height - top))],
            htpy.g(class_ = 'edges')[list_path],
            htpy.g(class_ = 'nodes')[list_node],
            htpy.g(class_ = 'ports')[list_dot]]]


# -----------------------------------------------------------------------------
def names(outline: Outline) -> list[str]:
    """
    Return the names of the chains the graph of the argument in outline
    can light: one for each port, each decision or annotation that is
    picked, and each concern.

    """

    (map_name, set_pick, list_concern) = _chains(*_layout(outline))
    return (list(map_name.values())
            + [cc_public.web.light.chain(id_item) for id_item in sorted(set_pick)]
            + [cc_public.web.light.chain(id_concern) for id_concern in list_concern])


# -----------------------------------------------------------------------------
def _layout(outline: Outline) -> tuple:
    """
    Return the kind and the place of each node of the graph of the
    argument in outline, and its edges.

    """

    map_kind  = {}
    map_place = {}
    map_depth = _depths(outline)
    map_last  = {}
    y_last    = None
    list_row  = sorted(outline.map_number, key = outline.map_number.get)
    for id_annotation in list_row:
        depth = map_depth[id_annotation]
        y     = max([0.0]
                    + ([y_last + ROW_STAGGER] if y_last is not None else [])
                    + ([map_last[depth] + ROW] if depth in map_last else []))
        map_kind[id_annotation]  = KIND_ANNOTATION
        map_place[id_annotation] = (X_FIRST + depth * COLUMN, y)
        map_last[depth]          = y
        y_last                   = y

    list_edge = _edges(outline, list_row)

    for (id_concern, y) in _concern_rows(outline, map_place).items():
        map_kind[id_concern]  = KIND_CONCERN
        map_place[id_concern] = (X_CONCERN, y)
    for (id_decision, y) in _decision_rows(outline, map_place).items():
        map_kind[id_decision]  = KIND_DECISION
        map_place[id_decision] = (X_DECISION, y)
    return (map_kind, map_place, list_edge)


# -----------------------------------------------------------------------------
def _chains(map_kind:  dict[str, str],
            map_place: dict[str, tuple[float, float]],
            list_edge: list[tuple[str, str, str]]) -> tuple:
    """
    Return the name of the chains into each port, the decisions and
    annotations a click picks, and the concerns.

    """

    set_into = {edge[1:] for edge in list_edge}
    map_name = {(id_item, role): cc_public.web.light.chain(id_item, role)
                for id_item in map_place for role in (ROLE_FOR, ROLE_AGAINST)
                if (id_item, role) in set_into}
    set_pick = ({id_to for (_, id_to, _) in list_edge if id_to in map_place}
                | {id_item for (id_item, kind) in map_kind.items() if kind == KIND_ANNOTATION})
    list_concern = [id_item for (id_item, kind) in map_kind.items() if kind == KIND_CONCERN]
    return (map_name, set_pick, list_concern)


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
def _lighting(list_edge:    list[tuple[str, str, str]],
              map_place:    dict[str, tuple[float, float]],
              map_name:     dict[tuple[str, str], str],
              set_pick:     set[str],
              list_concern: list[str]) -> tuple:
    """
    Return the edges as drawn, and the classes of each node and drawn
    edge that say which chains light it and with what net effect. The
    chains of a concern are those through its hubs, each net effect
    taken on to the decision of the hub.

    """

    list_drawn = []
    for edge in list_edge:
        if _drawn(edge) not in list_drawn:
            list_drawn.append(_drawn(edge))
    map_sign_node = {id_item: {} for id_item in map_place}
    map_sign_edge = {edge: {} for edge in list_drawn}
    list_light    = ([(name, port[0], {port[1]}) for (port, name) in map_name.items()]
                     + [(cc_public.web.light.chain(id_item), id_item, None) for id_item in map_place
                        if id_item in set_pick])
    for (key, id_item_lit, set_role) in list_light:
        cc_public.web.light.add(map_sign_node[id_item_lit], key, None)
        _light(map_sign_node, map_sign_edge, key, *_chain(list_edge, id_item_lit, set_role),
               ROLE_FOR)
    for id_concern in list_concern:
        key = cc_public.web.light.chain(id_concern)
        cc_public.web.light.add(map_sign_node[id_concern], key, None)
        for edge in list_edge:
            (id_hub, id_decision, role) = edge
            if DELIM_HUB in id_hub and _unhub(id_hub) == id_concern:
                cc_public.web.light.add(map_sign_node[id_decision], key, None)
                cc_public.web.light.add(map_sign_edge[_drawn(edge)], key, None)
                _light(map_sign_node, map_sign_edge, key, *_chain(list_edge, id_hub, None), role)
    map_css_node = {id_item: cc_public.web.light.css(map_sign)
                    for (id_item, map_sign) in map_sign_node.items()}
    map_css_edge = {edge: cc_public.web.light.css(map_sign)
                    for (edge, map_sign) in map_sign_edge.items()}
    return (list_drawn, map_css_node, map_css_edge)


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
    hub lights its concern, unshaded.

    """

    for (id_item, set_sign) in map_sign.items():
        id_drawn = _unhub(id_item)
        if id_drawn != id_item:
            cc_public.web.light.add(map_sign_node[id_drawn], key, None)
            continue
        for sign in set_sign:
            cc_public.web.light.add(map_sign_node[id_item], key,
                                    cc_public.web.light.times(role, sign))
    for edge in set_edge:
        cc_public.web.light.add(map_sign_edge[_drawn(edge)], key, None)


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
    annotations that argue for it, kept in the order of the Sankey
    diagram and pushed down so no two overlap.

    """

    map_mean = {}
    for id_concern in outline.list_concern:
        list_y = [map_place[unit.annotation][1] for unit in outline.units(concern = id_concern)]
        if list_y:
            map_mean[id_concern] = sum(list_y) / len(list_y)
    map_y  = {}
    y_last = None
    for (id_concern, y_mean) in map_mean.items():
        y = y_mean
        if y_last is not None and y < y_last + ROW_CONCERN:
            y = y_last + ROW_CONCERN
        map_y[id_concern] = y
        y_last            = y
    return map_y


# -----------------------------------------------------------------------------
def _decision_rows(outline:   Outline,
                   map_place: dict[str, tuple[float, float]]) -> dict[str, float]:
    """
    Return the row of each decision: the middle of the concerns argued
    on it, each counted once for each unit, kept in the order of the
    Sankey diagram and pushed down so no two overlap.

    """

    map_y = {}
    for id_decision in outline.list_decision:
        list_y = [map_place[unit.concern][1] for unit in outline.units(decision = id_decision)]
        map_y[id_decision] = sum(list_y) / len(list_y) if list_y else 0
    y_last = None
    for id_decision in outline.list_decision:
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
    Return the line of edge, from the left of its source to the port of
    its role on its target. It is an arc that bows up for a support and
    down for a challenge. A line from a concern first runs the length
    of its pipe, in the lane of its role.

    """

    (id_from, id_to, role) = edge
    (x1, y1) = map_place[id_from]
    path     = ''
    if map_kind[id_from] == KIND_CONCERN:
        y1   = y1 + _lane(role)
        path = 'M{x},{y} H{x1} '.format(x  = _num(x1 + WIDTH_CONCERN),
                                        y  = _num(y1),
                                        x1 = _num(x1))
    else:
        x1   = x1 - RADIUS
        path = 'M{x1},{y1} '.format(x1 = _num(x1), y1 = _num(y1))
    (x2, y2) = _inlet(map_kind[id_to], map_place[id_to], role)
    radius   = 1.8 * ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    path    += 'A{r},{r} 0 0 {sweep} {x2},{y2}'.format(r     = _num(radius),
                                                      sweep = 0 if role == ROLE_FOR else 1,
                                                      x2    = _num(x2),
                                                      y2    = _num(y2))
    return htpy.path(d = path, class_ = ' '.join(['edge-' + role, cc_public.web.light.CSS_DIMS]
                                                 + list_css))


# -----------------------------------------------------------------------------
def _lane(role: str) -> float:
    """
    Return the height of the lane of role in a pipe, from its middle.

    """

    return -GAP_LANE if role == ROLE_FOR else GAP_LANE


# -----------------------------------------------------------------------------
def _inlet(kind: str, place: tuple[float, float], role: str) -> tuple[float, float]:
    """
    Return where an edge of role enters a node of kind at place: its
    port for role, on the upper right of the circle for a support and
    the lower right for a challenge. A concern has no ports, but takes
    edges at the right end of the lane of role in its pipe.

    """

    (x, y) = place
    if kind == KIND_CONCERN:
        return (x + WIDTH_CONCERN, y + _lane(role))
    offset = -1 if role == ROLE_FOR else 1
    return (x + RADIUS * math.cos(ANGLE_PORT), y + offset * RADIUS * math.sin(ANGLE_PORT))


# -----------------------------------------------------------------------------
def _port(kind: str, place: tuple[float, float], role: str, name: str) -> typing.Any:
    """
    Return the port of role on the node of kind at place: a dot that
    shows the chain called name while it is hovered over, and pins it
    when clicked.

    """

    (cx, cy) = _inlet(kind, place, role)
    css = 'port port-{role} {show}'.format(role = role, show = cc_public.web.light.show(name))
    return htpy.a(href = '#' + name, class_ = css)[
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
    Return the node of kind for id_item at place. A decision or an
    annotation is a circle with its title beneath, and an annotation
    has its number inside. A concern is a pipe of two rules with its
    title above. If is_pick, the node links to the page with every
    chain into it lit. A concern never does.

    """

    (x, y) = place
    css    = ' '.join(['node', kind, cc_public.web.light.CSS_DIMS] + list_css)
    if kind == KIND_CONCERN:
        node = htpy.g(class_ = css, id = 'node-' + id_item)[
            htpy.rect(x = _num(x), y = _num(y - 2 * GAP_RAIL - 16), width = str(WIDTH_CONCERN),
                      height = str(3 * GAP_RAIL + 16), class_ = 'area'),
            [htpy.line(x1 = _num(x), y1 = _num(y + offset), x2 = _num(x + WIDTH_CONCERN),
                       y2 = _num(y + offset), class_ = 'shape')
             for offset in (-GAP_RAIL, GAP_RAIL)],
            htpy.text(x = _num(x + WIDTH_CONCERN / 2), y = _num(y - GAP_RAIL - 7),
                      class_ = 'name')[graph.title(id_item)]]
    else:
        label  = graph.title(id_item)
        number = None
        if kind == KIND_ANNOTATION:
            number = str(outline.map_number[id_item])
            label  = '{number} {title}'.format(number = number, title = label)
        node = htpy.g(class_ = css, id = 'node-' + id_item)[
            htpy.title[label],
            htpy.circle(cx = _num(x), cy = _num(y), r = str(RADIUS), class_ = 'shape'),
            htpy.text(x = _num(x), y = _num(y + 4.5), class_ = 'number')[
                number] if number else None,
            [htpy.text(x = _num(x), y = _num(y + RADIUS + 17 + LINE_TITLE * index),
                       class_ = 'name')[line]
             for (index, line) in enumerate(_lines(graph.title(id_item), CHARS_LINE))]]
    if not is_pick:
        return node
    name = cc_public.web.light.chain(id_item)
    return htpy.a(href = '#' + name, class_ = 'pick ' + cc_public.web.light.show(name))[node]


# -----------------------------------------------------------------------------
def _lines(text: str, chars: int) -> list[str]:
    """
    Return text broken into at most three lines of chars, the last cut
    short if need be.

    """

    list_line = ['']
    for word in text.split():
        if list_line[-1] and len(list_line[-1]) + 1 + len(word) > chars:
            if len(list_line) == 3:
                list_line[-1] = list_line[-1][:chars - 1].rstrip() + '…'
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
