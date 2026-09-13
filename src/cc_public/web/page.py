"""
---

id_self:                pym_cc_public.web.page
guid_self:              pym_0147961598684de18dcbcb372f7d1806
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pages
brief:                  |
                        The projections as HTML: the surface, the rows
                        at a level, the children of a row, and one
                        record read in full.
description:            |
                        Every function returns an htpy element, which
                        renders to a string when asked and never
                        before. The document function wraps a fragment
                        in the head, the header and the main of a
                        page. The surface function is the views to
                        choose between, the filter and the root rows.
                        A row is rendered with a place beneath it for
                        each level it discloses: the brief it opens
                        to, the record it is read as, and the children
                        a view finds under it. Which of those places
                        is filled, and when, is the script's business,
                        so nothing here holds state and nothing here
                        reads the tree.
relation:               []

...
"""


import htpy

import cc_public.web.projection


PATH_SURFACE = '/'
PATH_ROWS    = '/rows'
PATH_GROUPS  = '/groups'
PATH_RECORD  = '/record'
PATH_STATIC  = '/static/'

ID_ROOTS = 'roots'
ID_FILTER = 'filter'

SEPARATOR = ','


# -----------------------------------------------------------------------------
def document(title, fragment, name_tree, stamp = ''):
    """
    Return a whole page: the head, a header naming the tree, and the
    fragment as its content.

    stamp marks the version of the stylesheet and the script, so that a
    reader who returns after they change is not served what a cache
    kept.

    """

    mark = ('?v=' + stamp) if stamp else ''

    return htpy.html(lang = 'en')[
        htpy.head[
            htpy.meta(charset = 'utf-8'),
            htpy.meta(name = 'viewport', content = 'width=device-width, initial-scale=1'),
            htpy.title[title],
            htpy.link(rel = 'stylesheet', href = PATH_STATIC + 'style.css' + mark),
            htpy.script(src = PATH_STATIC + 'htmx.min.js'),
            htpy.script(src = PATH_STATIC + 'surface.js' + mark, defer = True)],
        htpy.body[
            htpy.header[
                htpy.span('.tree')[name_tree],
                htpy.span('.hint')[
                    'click or enter to open, r to read, escape to collapse everything']],
            htpy.main[fragment]]]


# -----------------------------------------------------------------------------
def surface(list_view, view, rows, text):
    """
    Return the whole list: the views to choose between, the filter, and
    the rows at the root of the chosen view.

    """

    return htpy.div('#surface')[
        htpy.nav('.views')[(
            htpy.a('.on' if one.id_self == view.id_self else None,
                   href = '{path}?view={id}'.format(path = PATH_SURFACE, id = one.id_self),
                   title = one.brief or '')[one.title]
            for one in list_view)],
        htpy.form('.filter', action = PATH_SURFACE, method = 'get',
                  hx_get = PATH_ROWS, hx_target = '#' + ID_ROOTS,
                  hx_trigger = 'input changed delay:200ms from:#' + ID_FILTER + ', submit')[
            htpy.input(type = 'hidden', name = 'view', value = view.id_self),
            htpy.label(for_ = ID_FILTER)['Filter '],
            htpy.input('#' + ID_FILTER, type = 'search', name = 'q', value = text,
                       placeholder = 'identifier or title')],
        fragment_rows(rows)]


# -----------------------------------------------------------------------------
def fragment_rows(rows):
    """
    Return the rows at the root of a view, or a line saying there are
    none.

    """

    if not rows:
        return htpy.div('#' + ID_ROOTS)[htpy.p('.absent')['Nothing matches.']]

    return htpy.div('#' + ID_ROOTS)[(_node(row) for row in rows)]


# -----------------------------------------------------------------------------
def fragment_groups(opened):
    """
    Return the children of a row, grouped by the relation that reached
    them, or nothing at all where there are none.

    """

    return htpy.fragment[(
        htpy.div('.group')[
            htpy.p('.glabel')[group.label],
            (_node(row) for row in group.rows)]
        for group in opened.groups)]


# -----------------------------------------------------------------------------
def fragment_record(record):
    """
    Return one item read in full: every field its type adds, labelled
    by its key and described by its schema.

    """

    if not record.fields:
        return htpy.p('.absent')['The envelope and nothing more.']

    return htpy.fragment[
        ((htpy.p('.key')[htpy.code[field.key],
                         htpy.span('.help')[field.help] if field.help else None],
          htpy.div('.val')[_value(field)])
         for field in record.fields),
        htpy.p('.identity')[record.guid_self, htpy.br, record.location]]


# -----------------------------------------------------------------------------
def _node(row):
    """
    Return one item as a row, with a place beneath it for each level it
    discloses: the brief it opens to, the record it is read as, and the
    children a view finds under it.

    """

    path = SEPARATOR.join(row.path)

    return htpy.div('.node', data_path = path)[
        htpy.div('.row' + ('.more' if row.has_child else ''), tabindex = '0',
                 data_path = path, data_id = row.id_self, title = row.id_self)[
            htpy.span('.ttl')[row.title],
            htpy.span('.kind')[row.kind]],
        htpy.div('.sub')[
            htpy.div('.detail')[
                htpy.p('.brief')[row.brief] if row.brief
                else htpy.p('.absent')['No brief.']],
            htpy.div('.record'),
            htpy.div('.groups')]]


# -----------------------------------------------------------------------------
def _value(field):
    if field.kind == cc_public.web.projection.KIND_HELD:
        return htpy.ul[(htpy.li[id_self, (' ', title) if title else None]
                        for (id_self, title) in field.value)]

    if field.kind == cc_public.web.projection.KIND_PROSE:
        return [htpy.p[' '.join(paragraph.split())]
                for paragraph in str(field.value).split('\n\n') if paragraph.strip()]

    if field.value is None:
        return htpy.span('.absent')['none']

    if '\n' in str(field.value):
        return htpy.pre('.datum')[str(field.value)]

    return htpy.code[str(field.value)]
