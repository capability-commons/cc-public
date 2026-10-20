"""
---

id_self:                pym_cc_public.web.sankey
guid_self:              pym_db8bea482e884ad792303ef77afbe949
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Sankey diagram of an argument
brief:                  |
                        Draw the weight of the argument on an issue as
                        a Sankey diagram, from its options to the
                        concerns argued on them.
description:            |
                        A unit of weight is one annotation arguing for
                        one concern, for or against one option.
                        Options stand on the left and concerns on the
                        right, joined by a band for each unit, with
                        support above challenge throughout: options,
                        concerns and annotations are each ordered from
                        most supported to most opposed. Each concern
                        is open by default, showing its annotations,
                        and an annotation opens into the annotations
                        that answer it. Links that name the parts
                        toggled from their default in the address of
                        the page open and close them, so no script is
                        needed. The title of an annotation links to
                        the same annotation opened in the list below
                        the diagram.
relation:               []

...
"""


import dataclasses
import textwrap
import typing
import urllib.parse

import htpy

import cc_public.web.argument
import cc_public.web.light


ROLE_FOR          = 'for'
ROLE_AGAINST      = 'against'
MAP_ROLE          = {cc_public.web.argument.R_SUPPORTS:   ROLE_FOR,
                     cc_public.web.argument.R_CHALLENGES: ROLE_AGAINST}

# Sizes, in units of the drawing. A unit of weight is one annotation
# arguing for one concern on one option.
#
UNIT              = 9
WIDTH_BAR         = 7
GAP               = 12
GAP_OPTION        = 30
ROW               = 18
ROOM_LABEL        = 16
ROOM_TITLE        = 300
CHARS_OPTION      = 38
LINE_OPTION       = 15
LIST_X            = (270, 500, 730, 960, 1190)

DELIM_KEY         = '/'
KEY_TOGGLE        = 'toggle'
KEY_SHOW          = 'show'
MARK_OPEN         = '▾'
MARK_CLOSED       = '▸'

Graph             = cc_public.web.argument.Graph
Issue             = cc_public.web.argument.Issue


# -----------------------------------------------------------------------------
@dataclasses.dataclass(frozen = True)
class Unit:
    """
    One unit of weight: the annotation argues for the concern, for or
    against the option.

    """

    option:     str
    concern:    str
    annotation: str
    role:       str

    # -------------------------------------------------------------------------
    def is_for(self) -> bool:
        """
        Return True if the unit supports its option.

        """

        return self.role == ROLE_FOR


# -----------------------------------------------------------------------------
def figure(graph:      Graph,
           outline:    'Outline',
           set_toggle: set[str],
           set_show:   set[str]) -> typing.Any:
    """
    Return the Sankey diagram of the argument in outline: its options
    on the left, each joined to the concerns that are argued on it,
    with support above challenge. A concern opens into its
    annotations, and an annotation into the annotations that answer
    it. The title of an annotation links to it, opened, in the list
    below; set_show holds those the page shows opened.

    Hovering over an option, either part of its bar, a concern argued
    for, or an annotation lights the chains that reach it and dims the
    rest, each annotation in them inked by its net effect on what was
    hovered over; clicking a bar or the name of an option pins the
    chains, and clicking anywhere else unpins them. The page holds the
    rules that light the chains and the elements that pin them (see
    cc_public.web.light), as the matrix and the graph share them.

    """

    drawing = _Drawing(graph, outline, set_toggle, set_show)
    height  = drawing.draw()
    width   = LIST_X[drawing.index_column_last] + ROOM_TITLE

    return htpy.figure(class_ = 'map sankey')[
        htpy.svg(class_  = cc_public.web.light.CSS_REGION,
                 viewBox = '0 {top} {width} {height}'.format(top    = -ROOM_LABEL,
                                                             width  = width,
                                                             height = height + ROOM_LABEL),
                 width   = str(width),
                 height  = str(height + ROOM_LABEL),
                 role    = 'img')[
            htpy.a(href = '#' + cc_public.web.light.KEY_UNPIN, class_ = 'unpin')[
                htpy.rect(x = '0', y = str(-ROOM_LABEL), width = str(width),
                          height = str(height + ROOM_LABEL))],
            drawing.list_band,
            drawing.list_bar,
            drawing.list_label]]


# -----------------------------------------------------------------------------
def units(issue: Issue) -> list[Unit]:
    """
    Return the units of weight of the argument on issue.

    """

    set_option = {option.id for option in issue.list_option}
    return [Unit(id_target, id_concern, annotation.id, role)
            for annotation in issue.list_annotation
            for (id_relation, role) in MAP_ROLE.items()
            for id_target in annotation.targets(id_relation)
            if id_target in set_option
            for id_concern in annotation.targets(cc_public.web.argument.R_ARGUES_FOR)]


# -----------------------------------------------------------------------------
def ordered_options(issue: Issue) -> list[cc_public.web.argument.Item]:
    """
    Return the options of issue from most supported to most opposed:
    by the share of their weight that supports them, then by how much
    supports them.

    """

    list_unit = units(issue)

    def key(option: cc_public.web.argument.Item) -> tuple:
        list_own = [unit for unit in list_unit if unit.option == option.id]
        return (lean(list_own), -sum(1 for unit in list_own if unit.is_for()), option.id)

    return sorted(issue.list_option, key = key)


# -----------------------------------------------------------------------------
class Outline:
    """
    The order in which the diagram shows the argument on an issue, and
    the numbers of its annotations.

    The concerns run from most supportive to most opposed, then drivers
    no annotation argues for. Each concern holds its annotations, most
    supportive first, and each annotation the annotations that answer
    it, support first. An annotation is numbered where it first
    appears with everything open, read from the top down; those the
    concerns do not reach come last.

    """

    # -------------------------------------------------------------------------
    def __init__(self, graph: Graph, issue: Issue) -> None:
        """
        Order the argument on issue.

        """

        self.issue         = issue
        self.list_unit     = units(issue)
        self.list_option   = [option.id for option in ordered_options(issue)]

        map_annotation = {annotation.id: annotation for annotation in issue.list_annotation}
        self.map_title = {id_item: item.title for (id_item, item) in map_annotation.items()}

        self.map_answer = {}
        for annotation in issue.list_annotation:
            for (id_relation, role) in MAP_ROLE.items():
                for id_target in annotation.targets(id_relation):
                    if id_target in map_annotation:
                        self.map_answer.setdefault(id_target, []).append((annotation.id, role))
        for list_answer in self.map_answer.values():
            list_answer.sort(key = lambda answer: (answer[1] != ROLE_FOR,
                                                   self.map_title[answer[0]]))

        set_argued        = {unit.concern for unit in self.list_unit}
        self.list_concern = (sorted(set_argued,
                                    key = lambda id_concern: (
                                              lean(self.units(concern = id_concern)),
                                              id_concern not in issue.list_driver,
                                              graph.title(id_concern)))
                             + [id_concern for id_concern in issue.list_driver
                                if id_concern not in set_argued])

        self.map_annotation = {id_concern: self._annotations(id_concern)
                               for id_concern in self.list_concern}

        self.map_number = {}
        for id_concern in self.list_concern:
            for id_annotation in self.map_annotation[id_concern]:
                self._number(id_annotation, set())
        self.list_other = [annotation.id for annotation in issue.list_annotation
                           if annotation.id not in self.map_number]
        for id_annotation in self.list_other:
            self._number(id_annotation, set())

    # -------------------------------------------------------------------------
    def answers(self, id_annotation: str) -> list[tuple[str, str]]:
        """
        Return the annotations that answer id_annotation, each with its
        role, support first.

        """

        return self.map_answer.get(id_annotation, [])

    # -------------------------------------------------------------------------
    def units(self,
              option:     str | None   = None,
              concern:    str | None = None,
              annotation: str | None = None) -> list[Unit]:
        """
        Return the units on option, concern and annotation, for those
        given.

        """

        return [unit for unit in self.list_unit
                if option in (None, unit.option)
                and concern in (None, unit.concern)
                and annotation in (None, unit.annotation)]

    # -------------------------------------------------------------------------
    def _annotations(self, id_concern: str) -> list[str]:
        """
        Return the annotations that argue for id_concern, most
        supportive first, then by the first option they bear on.

        """

        def key(id_annotation: str) -> tuple:
            list_own = self.units(concern = id_concern, annotation = id_annotation)
            return (lean(list_own),
                    min(self.list_option.index(unit.option) for unit in list_own),
                    self.map_title[id_annotation])

        return sorted({unit.annotation for unit in self.units(concern = id_concern)},
                      key = key)

    # -------------------------------------------------------------------------
    def _number(self, id_annotation: str, set_path: set[str]) -> None:
        """
        Number id_annotation if it has no number yet, then the
        annotations that answer it, in order. set_path holds those
        above it, so a loop of answers stops.

        """

        if id_annotation in set_path:
            return
        self.map_number.setdefault(id_annotation, len(self.map_number) + 1)
        for (id_answer, _) in self.answers(id_annotation):
            self._number(id_answer, set_path | {id_annotation})


# -----------------------------------------------------------------------------
def parse_toggle(query: str) -> set[str]:
    """
    Return the keys of the parts of a diagram toggled from their
    default, read from the query of a page address. A concern is open
    by default, and an annotation closed.

    """

    return set(urllib.parse.parse_qs(query).get(KEY_TOGGLE, []))


# -----------------------------------------------------------------------------
def parse_show(query: str) -> set[str]:
    """
    Return the keys of the annotations the list shows opened, read from
    the query of a page address.

    """

    return set(urllib.parse.parse_qs(query).get(KEY_SHOW, []))


# -----------------------------------------------------------------------------
class _Drawing:
    """
    The marks of one Sankey diagram, built column by column.

    """

    # -------------------------------------------------------------------------
    def __init__(self,
                 graph:      Graph,
                 outline:    Outline,
                 set_toggle: set[str],
                 set_show:   set[str]) -> None:
        """
        Start an empty drawing of the argument in outline.

        """

        self.graph         = graph
        self.outline       = outline
        self.issue         = outline.issue
        self.map_number    = outline.map_number
        self.map_title     = outline.map_title
        self.list_option   = outline.list_option
        self.list_concern  = outline.list_concern
        self.set_toggle    = set_toggle
        self.set_show      = set_show
        self.list_band     = []
        self.list_bar      = []
        self.list_label    = []
        self.index_column_last = 1
        self.map_closure   = {id_annotation: self._closure(id_annotation, set())
                              for id_annotation in self.map_number}

    # -------------------------------------------------------------------------
    def draw(self) -> float:
        """
        Draw the diagram, and return its height.

        """

        (map_top_concern, bottom) = self._column_concerns()
        height_option             = (sum(self._extent(id_option)
                                         for id_option in self.list_option)
                                     + GAP_OPTION * (len(self.list_option) - 1))
        map_top_option          = self._column_options(max(0.0,
                                                               (bottom - height_option) / 2))
        self._bands_to_concerns(map_top_option, map_top_concern)

        return max(bottom, height_option) + GAP

    # -------------------------------------------------------------------------
    def _column_options(self, top: float) -> dict[str, float]:
        """
        Draw the options from top down, each a bar of its support
        above its challenge, labelled with its standing and its tally.
        Return the top of each.

        """

        map_top = {}
        y       = top

        for option in ordered_options(self.issue):
            list_unit   = self._units(option = option.id)
            count_for   = sum(1 for unit in list_unit if unit.is_for())
            count_total = len(list_unit)
            height      = self._height(list_unit)
            extent      = self._extent(option.id)
            y_next      = y + extent + GAP_OPTION
            y          += (extent - height) / 2
            map_top[option.id] = y

            list_css = self.css_option(option.id)
            self._bar(LIST_X[0], y, count_for * UNIT, ROLE_FOR, list_css,
                      cc_public.web.light.chain(option.id, ROLE_FOR))
            self._bar(LIST_X[0], y + count_for * UNIT, (count_total - count_for) * UNIT,
                      ROLE_AGAINST, list_css,
                      cc_public.web.light.chain(option.id, ROLE_AGAINST))
            if not count_total:
                self._bar(LIST_X[0], y, 2, 'none', list_css)

            stance    = self.issue.map_stance[option.id]
            list_line = _lines_option(option.title)
            top_text  = y + height / 2 - 2 - LINE_OPTION * (len(list_line) - 1) / 2
            name      = cc_public.web.light.chain(option.id)
            css       = ' '.join(['option', cc_public.web.light.CSS_DIMS,
                                  cc_public.web.light.show(name)]
                                 + list_css)
            self.list_label.append(htpy.a(href = '#' + name, class_ = 'pin')[
                htpy.text(x = str(LIST_X[0] - 10), y = _num(top_text),
                          class_ = css, text_anchor = 'end')[
                    [htpy.tspan(x = str(LIST_X[0] - 10),
                                dy = '0' if index == 0 else str(LINE_OPTION))[line]
                     for (index, line) in enumerate(list_line)]]])
            self.list_label.append(
                htpy.text(x = str(LIST_X[0] - 10),
                          y = _num(top_text + LINE_OPTION * (len(list_line) - 1) + 16),
                          class_ = ' '.join(['tally', cc_public.web.light.CSS_DIMS] + list_css),
                          text_anchor = 'end')[
                    htpy.tspan(class_ = 'stance-' + stance)['● ' + stance],
                    ' ',
                    htpy.tspan(class_ = 'for')[
                        '{mark}{count}'.format(mark  = cc_public.web.light.MARK_FOR,
                                               count = count_for)],
                    ' ',
                    htpy.tspan(class_ = 'against')[
                        '{mark}{count}'.format(mark  = cc_public.web.light.MARK_AGAINST,
                                               count = count_total - count_for)]])
            y = y_next

        return map_top

    # -------------------------------------------------------------------------
    def _extent(self, id_option: str) -> float:
        """
        Return the height id_option takes in its column: its bar, or
        its label if that is taller.

        """

        list_line = _lines_option(self.graph.title(id_option))
        return max(self._height(self._units(option = id_option)),
                   LINE_OPTION * (len(list_line) + 1))

    # -------------------------------------------------------------------------
    def _column_concerns(self) -> tuple[dict[str, float], float]:
        """
        Draw the concerns, each a bar as tall as its weight, labelled
        with a link that opens or closes it, and beside each open one
        its annotations. Return the top of each concern, and the bottom
        of what is drawn.

        """

        map_top = {}
        y       = 0.0

        for id_concern in self.list_concern:
            list_unit = self._units(concern = id_concern)
            is_open   = self._open(id_concern) and bool(list_unit)
            y        += ROOM_LABEL if is_open else 0
            height    = self._height(list_unit)
            map_top[id_concern] = y

            css      = 'concern' if id_concern in self.issue.list_driver else 'concern other'
            list_css = self.css_concern(id_concern)
            if list_unit:
                list_css = [*list_css,
                            cc_public.web.light.show(cc_public.web.light.chain(id_concern))]
            css      = ' '.join([css, cc_public.web.light.CSS_DIMS] + list_css)
            title    = self.graph.title(id_concern)
            self._bar(LIST_X[1], y, height, 'driver' if id_concern in self.issue.list_driver
                                            else 'other', list_css)

            if not list_unit:
                self.list_label.append(
                    htpy.text(x = str(LIST_X[1] + WIDTH_BAR + 8), y = _num(y + 5),
                              class_ = css)[title, ' ', htpy.tspan(class_ = 'note')['not argued']])
            elif is_open:
                self.list_label.append(self._toggle(
                    id_concern, LIST_X[1] - 2, y - 4, css,
                    [MARK_OPEN, ' ', title]))
            else:
                count = len({unit.annotation for unit in list_unit})
                self.list_label.append(self._toggle(
                    id_concern, LIST_X[1] + WIDTH_BAR + 8, y + height / 2 + 4, css,
                    [title, ' ', htpy.tspan(class_ = 'note')[
                                     '{mark} {count}'.format(mark = MARK_CLOSED,
                                                             count = count)]]))
            bottom = self._annotations(id_concern, y) if is_open else 0.0
            y      = max(y + height, bottom) + GAP

        return (map_top, y)

    # -------------------------------------------------------------------------
    def _bands_to_concerns(self,
                           map_top_option:   dict[str, float],
                           map_top_concern:  dict[str, float]) -> None:
        """
        Draw a band for each unit from its option to its concern. On
        each side the units are stacked support first, so the bands of
        one option and concern lie together.

        """

        map_y_option = {}
        for id_option in self.list_option:
            list_unit = sorted(self._units(option = id_option),
                               key = lambda unit: (not unit.is_for(),
                                                   self.list_concern.index(unit.concern),
                                                   unit.annotation))
            for (index, unit) in enumerate(list_unit):
                map_y_option[unit] = map_top_option[id_option] + index * UNIT

        for id_concern in self.list_concern:
            list_unit = sorted(self._units(concern = id_concern),
                               key = lambda unit: (not unit.is_for(),
                                                   self.list_option.index(unit.option),
                                                   unit.annotation))
            for (index, unit) in enumerate(list_unit):
                self._band(LIST_X[0] + WIDTH_BAR, map_y_option[unit],
                           LIST_X[1], map_top_concern[id_concern] + index * UNIT,
                           UNIT, unit.role, self.css_unit(unit))

    # -------------------------------------------------------------------------
    def _annotations(self, id_concern: str, top: float) -> float:
        """
        Draw the annotations of the open concern whose bar starts at
        top, most supportive first, each fed by a strand for each of its
        units. Return the bottom of what is drawn.

        """

        y      = top
        y_from = top

        for id_annotation in self.outline.map_annotation[id_concern]:
            key = DELIM_KEY.join((id_concern, id_annotation))
            y  += ROOM_LABEL if self._is_open(key, id_annotation) else 0
            list_own = sorted(self._units(concern = id_concern, annotation = id_annotation),
                              key = lambda unit: (not unit.is_for(),
                                                  self.list_option.index(unit.option)))
            for (index, unit) in enumerate(list_own):
                list_css = self.css_unit(unit)
                self._band(LIST_X[1] + WIDTH_BAR, y_from, LIST_X[2], y + index * UNIT,
                           UNIT, unit.role, list_css)
                self._bar(LIST_X[2], y + index * UNIT, UNIT, unit.role, list_css,
                          cc_public.web.light.chain(id_annotation))
                y_from += UNIT

            height = len(list_own) * UNIT
            self._label(key, id_annotation, 2, y, height)
            y = self._answers(key, id_annotation, 3, y, height,
                              y + max(height, ROW) + 4)

        return y

    # -------------------------------------------------------------------------
    def _answers(self,
                 key:           str,
                 id_annotation: str,
                 index_column:  int,
                 top:           float,
                 height:        float,
                 bottom:        float) -> float:
        """
        If the annotation at key is open, draw the annotations that
        answer it in column index_column, splitting its height among
        them, support first. Return the bottom of what is drawn.

        """

        if not self._is_open(key, id_annotation) or index_column >= len(LIST_X):
            return bottom

        list_answer = self.outline.answers(id_annotation)
        width       = height / len(list_answer)
        y           = top

        for (index, (id_answer, role)) in enumerate(list_answer):
            key_answer = DELIM_KEY.join((key, id_answer))
            y         += ROOM_LABEL if self._is_open(key_answer, id_answer) else 0
            list_css   = self.css_path(key_answer)
            self._band(LIST_X[index_column - 1] + WIDTH_BAR, top + index * width,
                       LIST_X[index_column], y, width, role, list_css)
            self._bar(LIST_X[index_column], y, width, role, list_css,
                      cc_public.web.light.chain(id_answer))
            self._label(key_answer, id_answer, index_column, y, width)
            y = self._answers(key_answer, id_answer, index_column + 1, y, width,
                              y + max(width, ROW) + 4)

        return max(bottom, y)

    # -------------------------------------------------------------------------
    def _label(self,
               key:           str,
               id_annotation: str,
               index_column:  int,
               top:           float,
               height:        float) -> None:
        """
        Label the annotation at key with its number and title, linked to
        the annotation opened in the list: above its bar if it is open,
        beside it otherwise. If anything answers it, a mark beside the
        title opens or closes it in the diagram.

        """

        x       = LIST_X[index_column]
        self.index_column_last = max(self.index_column_last, index_column)
        count   = len(self.outline.answers(id_annotation))
        css     = ' '.join(['annotation shown' if key in self.set_show else 'annotation',
                            cc_public.web.light.CSS_DIMS,
                            cc_public.web.light.show(cc_public.web.light.chain(id_annotation))]
                           + self.css_path(key))
        title   = htpy.a(href = self._href_show(key))[
                      htpy.tspan(class_ = 'number')[
                          str(self.map_number.get(id_annotation, ''))],
                      ' ',
                      self.map_title.get(id_annotation, id_annotation)]

        if self._is_open(key, id_annotation):
            content = [htpy.a(href = self._href_toggle(key))[MARK_OPEN], ' ', title]
            (x, y)  = (x - 2, top - 4)
        elif count:
            content = [title, ' ', htpy.a(href = self._href_toggle(key))[
                                       htpy.tspan(class_ = 'note')[
                                           '{mark} {count}'.format(mark  = MARK_CLOSED,
                                                                   count = count)]]]
            (x, y)  = (x + WIDTH_BAR + 8, top + height / 2 + 4)
        else:
            content = [title]
            (x, y)  = (x + WIDTH_BAR + 8, top + height / 2 + 4)

        self.list_label.append(htpy.text(x = _num(x), y = _num(y), class_ = css)[content])

    # -------------------------------------------------------------------------
    def names(self) -> list[str]:
        """
        Return the names of the chains that can be lit: one for each
        option, each part of the bar of an option, each concern
        argued for, and each annotation.

        """

        chain = cc_public.web.light.chain
        return ([chain(id_option) for id_option in self.list_option]
                + [chain(id_option, role) for id_option in self.list_option
                   for role in (ROLE_FOR, ROLE_AGAINST)]
                + [chain(id_concern) for id_concern in self.list_concern
                   if self._units(concern = id_concern)]
                + [chain(id_annotation) for id_annotation in self.map_number])

    # -------------------------------------------------------------------------
    def _closure(self, id_annotation: str, set_path: set[str]) -> set[str]:
        """
        Return id_annotation and every annotation that answers it,
        directly or not. set_path holds those above it, so a loop of
        answers stops.

        """

        set_out = {id_annotation}
        for (id_answer, _) in self.outline.answers(id_annotation):
            if id_answer not in set_path:
                set_out |= self._closure(id_answer, set_path | {id_annotation})
        return set_out

    # -------------------------------------------------------------------------
    def css_unit(self, unit: Unit) -> list[str]:
        """
        Return the classes of a mark of unit: in the chains of its
        option and of the part of its bar for its role, inked by its
        role, as it is in the chains of its concern, and in the chains
        of its annotation and of every annotation that answers it,
        unshaded.

        """

        map_sign = {}
        add      = cc_public.web.light.add
        chain    = cc_public.web.light.chain
        add(map_sign, chain(unit.option), unit.role)
        add(map_sign, chain(unit.option, unit.role), unit.role)
        add(map_sign, chain(unit.concern), unit.role)
        for id_annotation in self.map_closure[unit.annotation]:
            add(map_sign, chain(id_annotation), None)
        return cc_public.web.light.css(map_sign)

    # -------------------------------------------------------------------------
    def css_path(self, key: str) -> list[str]:
        """
        Return the classes of a mark of the annotation at key: in the
        chains of each option it bears on through the first
        annotation of key, of the concern of key, and of each
        annotation above it in key, each inked by its net effect
        there; and, unshaded, in its own chain and the chains of the
        annotations that answer it.

        """

        list_part  = key.split(DELIM_KEY)
        id_concern = list_part[0]
        list_path  = list_part[1:]
        list_role  = [dict(self.outline.answers(id_above)).get(id_below, ROLE_FOR)
                      for (id_above, id_below) in zip(list_path, list_path[1:], strict = False)]

        def net(list_role_part: list[str]) -> str:
            role = ROLE_FOR
            for role_part in list_role_part:
                role = cc_public.web.light.times(role, role_part)
            return role

        map_sign = {}
        add      = cc_public.web.light.add
        chain    = cc_public.web.light.chain
        for unit in self._units(concern = id_concern, annotation = list_path[0]):
            sign = cc_public.web.light.times(unit.role, net(list_role))
            add(map_sign, chain(unit.option), sign)
            add(map_sign, chain(unit.option, unit.role), sign)
            add(map_sign, chain(id_concern), sign)
        for (index, id_above) in enumerate(list_path[:-1]):
            add(map_sign, chain(id_above), net(list_role[index:]))
        for id_annotation in self.map_closure.get(list_path[-1], {list_path[-1]}):
            add(map_sign, chain(id_annotation), None)
        return cc_public.web.light.css(map_sign)

    # -------------------------------------------------------------------------
    def css_option(self, id_option: str) -> list[str]:
        """
        Return the classes of a mark of id_option: in its own chains,
        and in those of every concern and annotation that bears on it,
        unshaded.

        """

        map_sign = {}
        add      = cc_public.web.light.add
        chain    = cc_public.web.light.chain
        add(map_sign, chain(id_option), None)
        for role in (ROLE_FOR, ROLE_AGAINST):
            add(map_sign, chain(id_option, role), None)
        for unit in self._units(option = id_option):
            add(map_sign, chain(unit.concern), None)
            for id_annotation in self.map_closure[unit.annotation]:
                add(map_sign, chain(id_annotation), None)
        return cc_public.web.light.css(map_sign)

    # -------------------------------------------------------------------------
    def css_concern(self, id_concern: str) -> list[str]:
        """
        Return the classes of a mark of id_concern: in its own chains,
        in the chains of the options and parts of bars it carries,
        and of every annotation argued on it, unshaded.

        """

        map_sign = {}
        add      = cc_public.web.light.add
        chain    = cc_public.web.light.chain
        add(map_sign, chain(id_concern), None)
        for unit in self._units(concern = id_concern):
            add(map_sign, chain(unit.option), None)
            add(map_sign, chain(unit.option, unit.role), None)
            for id_annotation in self.map_closure[unit.annotation]:
                add(map_sign, chain(id_annotation), None)
        return cc_public.web.light.css(map_sign)

    # -------------------------------------------------------------------------
    def _toggle(self, key: str, x: float, y: float, css: str, content: list) -> typing.Any:
        """
        Return a label at x and y that links to the page with the part
        at key opened, or closed if it is open.

        """

        return htpy.a(href = self._href_toggle(key))[
            htpy.text(x = _num(x), y = _num(y), class_ = css)[content]]

    # -------------------------------------------------------------------------
    def _href_toggle(self, key: str) -> str:
        """
        Return the address of the page with the part at key opened, or
        closed if it is open. Closing a part closes everything opened
        within it.

        """

        set_next = self.set_toggle ^ {key}
        if self._open(key):
            set_next = {key_toggle for key_toggle in set_next
                        if not key_toggle.startswith(key + DELIM_KEY)}

        list_param = [(KEY_TOGGLE, key_toggle) for key_toggle in sorted(set_next)]
        list_param += [(KEY_SHOW, key_show) for key_show in sorted(self.set_show)]
        return '?' + urllib.parse.urlencode(list_param)

    # -------------------------------------------------------------------------
    def _href_show(self, key: str) -> str:
        """
        Return the address of the page with the annotation at key
        opened in the list, and the diagram as it is.

        """

        list_param = [(KEY_TOGGLE, key_toggle) for key_toggle in sorted(self.set_toggle)]
        list_param.append((KEY_SHOW, key))
        return '?{query}#{key}'.format(query = urllib.parse.urlencode(list_param), key = key)

    # -------------------------------------------------------------------------
    def _is_open(self, key: str, id_annotation: str) -> bool:
        """
        Return True if the annotation at key is open and has answers.

        """

        return self._open(key) and bool(self.outline.answers(id_annotation))

    # -------------------------------------------------------------------------
    def _open(self, key: str) -> bool:
        """
        Return True if the part at key is open. A concern is open unless
        toggled, and an annotation is closed unless toggled.

        """

        return (key in self.set_toggle) != (DELIM_KEY not in key)

    # -------------------------------------------------------------------------
    def _units(self, **map_given: str) -> list[Unit]:
        """
        Return the units of the outline on the option, concern and
        annotation given.

        """

        return self.outline.units(**map_given)

    # -------------------------------------------------------------------------
    def _height(self, list_unit: list[Unit]) -> float:
        """
        Return the height of a bar of list_unit, never less than a
        hairline.

        """

        return max(len(list_unit) * UNIT, 2)

    # -------------------------------------------------------------------------
    def _bar(self,
             x:        float,
             y:        float,
             height:   float,
             css:      str,
             list_css: list[str] = (),
             name:     str | None = None) -> None:
        """
        Add a bar at x and y of height, in the chains of list_css. If
        name is given, the bar shows the chain called name while it is
        hovered over, and pins it when clicked.

        """

        if height <= 0:
            return
        list_class = ['bar-' + css, cc_public.web.light.CSS_DIMS, *list_css]
        if name:
            list_class.append(cc_public.web.light.show(name))
        bar = htpy.rect(x = _num(x), y = _num(y), width = str(WIDTH_BAR),
                        height = _num(height), class_ = ' '.join(list_class))
        if name:
            bar = htpy.a(href = '#' + name, class_ = 'pin')[bar]
        self.list_bar.append(bar)

    # -------------------------------------------------------------------------
    def _band(self,
              x_from: float,
              y_from: float,
              x_to:   float,
              y_to:   float,
              width:    float,
              role:     str,
              list_css: list[str] = ()) -> None:
        """
        Add a band of width from x_from and y_from to x_to and y_to, in
        the colour of role.

        """

        x_mid = (x_from + x_to) / 2
        path  = ('M{x1},{y1} C{xm},{y1} {xm},{y2} {x2},{y2} L{x2},{y3} '
                 'C{xm},{y3} {xm},{y4} {x1},{y4} Z').format(x1 = _num(x_from),
                                                            y1 = _num(y_from),
                                                            xm = _num(x_mid),
                                                            x2 = _num(x_to),
                                                            y2 = _num(y_to),
                                                            y3 = _num(y_to + width),
                                                            y4 = _num(y_from + width))
        self.list_band.append(htpy.path(d = path, class_ = ' '.join(
            ['band-' + role, cc_public.web.light.CSS_DIMS, *list_css])))


# -----------------------------------------------------------------------------
def lighting(graph: Graph, outline: Outline) -> _Drawing:
    """
    Return an undrawn diagram of the argument in outline, whose
    css_concern and css_path give the classes that light a mark outside
    the diagram, such as a row of the decision matrix, with the chains
    of the diagram.

    """

    return _Drawing(graph, outline, set(), set())


# -----------------------------------------------------------------------------
def _lines_option(title: str) -> list[str]:
    """
    Return title broken into lines short enough for the room left of
    the column of options.

    """

    return textwrap.wrap(title, CHARS_OPTION) or ['']


# -----------------------------------------------------------------------------
def lean(list_unit: list[Unit]) -> float:
    """
    Return how far list_unit leans to challenge: 0 if every unit
    supports, 1 if every unit challenges.

    """

    if not list_unit:
        return 1.0
    return sum(1 for unit in list_unit if not unit.is_for()) / len(list_unit)


# -----------------------------------------------------------------------------
def _num(value: float) -> str:
    """
    Return value as a coordinate of the drawing.

    """

    return '{value:.1f}'.format(value = value)
