"""
---

id_self:                pym_cc_public.web.step
guid_self:              pym_bbe3fa5d6c534cd8bb372881890740b1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Drawing of a dataflow step
brief:                  |
                        Draw a dataflow step as a box with its inputs,
                        outputs and state as named arrows.
description:            |
                        figure draws the step of a dataflow step
                        surface, read by pym_cc_public.web.contract,
                        as a box named by the interface. Each input is
                        an arrow into the box from the left and each
                        output an arrow out of it to the right, spread
                        evenly down its sides, and each part of its
                        state a two-headed arrow under it, since a
                        step both reads and writes its state. Each
                        arrow is named by its port and the type the
                        port carries, links to the row of the port in
                        the table that follows the drawing, and is
                        dashed if the port is optional.
edge:                   []

...
"""


import htpy

import cc_public.web.contract


WIDTH             = 600
X_IN              = 10
X_BOX             = 210
X_OUT             = 590
WIDTH_BOX         = 180
TOP               = 14
ROW               = 52
ROOM_STATE        = 74
GAP_TEXT          = 6
ID_ARROW          = 'step-arrow'
CSS_OPTIONAL      = 'optional'

Surface           = cc_public.web.contract.Surface
Member            = cc_public.web.contract.Member


# -----------------------------------------------------------------------------
def figure(title: str, surface: Surface) -> htpy.Element:
    """
    Return the drawing of a dataflow step: the step as a box named
    title, each input an arrow into it from the left and each output
    an arrow out of it to the right, and each part of its state a
    two-headed arrow under it, read and written. Each arrow is named by
    its port and the type it carries, and links to the row of the port.
    An optional port is drawn dashed.

    """

    map_group = dict(surface.list_group)
    list_in   = map_group.get('input', [])
    list_out  = map_group.get('output', [])
    list_held = map_group.get('state', [])
    height    = ROW * max(len(list_in), len(list_out), 1)
    bottom    = TOP + height
    total     = bottom + (ROOM_STATE if list_held else TOP)

    list_mark = [htpy.rect(x = str(X_BOX), y = str(TOP), width = str(WIDTH_BOX),
                           height = str(height), class_ = 'box'),
                 htpy.text(x = str(X_BOX + WIDTH_BOX // 2), y = str(TOP + height // 2 + 5),
                           class_ = 'name', text_anchor = 'middle')[title]]

    for (index, member) in enumerate(list_in):
        y = _spread(index, len(list_in), height)
        list_mark.append(_port(member, (X_IN, y), (X_BOX, y), X_IN, 'start'))

    for (index, member) in enumerate(list_out):
        y = _spread(index, len(list_out), height)
        list_mark.append(_port(member, (X_BOX + WIDTH_BOX, y), (X_OUT, y), X_OUT, 'end'))

    for (index, member) in enumerate(list_held):
        x = X_BOX + round(WIDTH_BOX * (index + 0.5) / len(list_held))
        list_mark.append(_port(member, (x, bottom + 34), (x, bottom), x, 'middle',
                               is_held = True))

    return htpy.figure(class_ = 'step')[
        htpy.svg(viewBox = '0 0 {width} {height}'.format(width = WIDTH, height = total),
                 width   = str(WIDTH),
                 height  = str(total),
                 role    = 'img')[
            htpy.defs[htpy.marker(id = ID_ARROW, viewBox = '0 0 8 8', refX = '8', refY = '4',
                                  markerWidth = '7', markerHeight = '7',
                                  orient = 'auto-start-reverse')[
                htpy.path(d = 'M0,0 L8,4 L0,8 z', class_ = 'head')]],
            list_mark]]


# -----------------------------------------------------------------------------
def _spread(index: int, count: int, height: int) -> int:
    """
    Return the height at which the port at index of count ports meets
    the side of a box of height.

    """

    return TOP + round(height * (index + 0.5) / count)


# -----------------------------------------------------------------------------
def _port(member:   Member,
          start:    tuple[int, int],
          end:      tuple[int, int],
          x_text:   int,
          anchor:   str,
          is_held:  bool = False) -> htpy.Element:
    """
    Return the arrow of a port from start to end, its name and type
    set at x_text, aligned by anchor: over and under the arrow, or under
    its foot if the port is held state, whose arrow has two heads.

    """

    css     = ' '.join(['port', CSS_OPTIONAL if member.node.get('optional') else '']).strip()
    spelling = (member.node.get('type') or {}).get('spelling', '')
    if is_held:
        (y_name, y_type) = (start[1] + 16, start[1] + 31)
    else:
        (y_name, y_type) = (start[1] - GAP_TEXT, start[1] + GAP_TEXT + 11)

    return htpy.a(href = '#port-' + member.id)[
        htpy.g(class_ = css)[
            htpy.line(x1 = str(start[0]), y1 = str(start[1]), x2 = str(end[0]),
                      y2 = str(end[1]), marker_end = 'url(#{id})'.format(id = ID_ARROW),
                      marker_start = 'url(#{id})'.format(id = ID_ARROW) if is_held else None),
            htpy.text(x = str(x_text), y = str(y_name), text_anchor = anchor,
                      class_ = 'name')[member.name],
            htpy.text(x = str(x_text), y = str(y_type), text_anchor = anchor,
                      class_ = 'type')[spelling] if spelling else None]]
