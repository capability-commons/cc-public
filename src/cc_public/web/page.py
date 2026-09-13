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
                        The projections as HTML: a fragment with one
                        root for each, and the document that wraps a
                        fragment.
description:            |
                        Every function returns an htpy element, which
                        renders to a string when asked and never
                        before. index is the search form and the
                        listing fragment; listing is the fragment
                        alone, which the search route returns for HTMX
                        to swap in place; detail is one item. document
                        wraps a fragment in the head, header and main
                        of a page, with the stylesheet and HTMX from
                        static. Text is escaped by htpy; prose is
                        split into paragraphs at blank lines. A page
                        holds no route and reads no tree.
relation:               []

...
"""


import htpy

import cc_public.web.projection


ID_LISTING  = 'listing'
ID_QUERY    = 'query'
PATH_INDEX  = '/'
PATH_SEARCH = '/search'
PATH_ITEM   = '/item/'
PATH_STATIC = '/static/'


# -----------------------------------------------------------------------------
def document(title, fragment, name_tree):
    """
    Return a whole page: the head, a header naming the tree, and the
    fragment as its main content.

    """

    return htpy.html(lang = 'en')[
        htpy.head[
            htpy.meta(charset = 'utf-8'),
            htpy.meta(name = 'viewport', content = 'width=device-width, initial-scale=1'),
            htpy.title[title],
            htpy.link(rel = 'stylesheet', href = PATH_STATIC + 'style.css'),
            htpy.script(src = PATH_STATIC + 'htmx.min.js', defer = True)],
        htpy.body[
            htpy.header[
                htpy.a(href = PATH_INDEX)['Capability commons'],
                htpy.span('.tree')[name_tree]],
            htpy.main[fragment]]]


# -----------------------------------------------------------------------------
def index(listing):
    """
    Return the index: the kinds, the search form, and the listing it
    fills.

    """

    return htpy.section('#index')[
        htpy.h1['Items'],
        htpy.p('.kind')[_join(', ', (
            htpy.a(href = _path_kind(kind.prefix, listing.query))[
                kind.title, ' ', htpy.span('.count')[str(kind.count)]]
            for kind in listing.kinds))],
        htpy.form('.search', action = PATH_INDEX, method = 'get',
                  hx_get = PATH_SEARCH, hx_target = '#' + ID_LISTING,
                  hx_trigger = 'input changed delay:200ms from:#' + ID_QUERY + ', submit')[
            htpy.label(for_ = ID_QUERY)['Search '],
            htpy.input('#' + ID_QUERY, type = 'search', name = 'q', value = listing.query,
                       placeholder = 'identifier, title or brief'),
            (htpy.input(type = 'hidden', name = 'kind', value = listing.prefix)
             if listing.prefix else None)],
        fragment_listing(listing)]


# -----------------------------------------------------------------------------
def fragment_listing(listing):
    """
    Return the listing alone: what the search found, as a table, or a
    line saying nothing was.

    """

    shown = len(listing.entries)
    count = ('{shown} of {total} items' if shown < listing.total else '{total} items'
             ).format(shown = shown, total = listing.total)

    if not listing.entries:
        return htpy.div('#' + ID_LISTING)[htpy.p('.absent')['Nothing matches.']]

    return htpy.div('#' + ID_LISTING)[
        htpy.p('.count')[count],
        htpy.table[
            htpy.thead[htpy.tr[htpy.th['Identifier'], htpy.th['Title'], htpy.th['Brief']]],
            htpy.tbody[(
                htpy.tr[
                    htpy.td[_link(entry.id_self)],
                    htpy.td[entry.title or _absent()],
                    htpy.td[entry.brief or _absent()]]
                for entry in listing.entries)]]]


# -----------------------------------------------------------------------------
def detail(item):
    """
    Return one item: its heading, its fields, and the edges at it.

    """

    return htpy.article('#item')[
        htpy.p('.kind')[item.kind],
        htpy.h1[item.title or item.id_self],
        htpy.p('.identity')[item.id_self, ' ', item.guid_self, htpy.br,
                            item.location, ('#' + item.path) if item.path else None],
        htpy.h2['Fields'],
        htpy.dl('.field')[(
            (htpy.dt[htpy.code[field.key],
                     htpy.span('.help')[field.help] if field.help else None],
             htpy.dd[_value(field)])
            for field in item.fields)],
        _edges(item)]


# -----------------------------------------------------------------------------
def _value(field):
    if field.kind == cc_public.web.projection.KIND_HELD:
        return htpy.ul[(htpy.li[_link(id_self), (' ', title) if title else None]
                        for (id_self, title) in field.value)]

    if field.kind == cc_public.web.projection.KIND_PROSE:
        return [htpy.p[' '.join(paragraph.split())]
                for paragraph in str(field.value).split('\n\n') if paragraph.strip()]

    if field.value is None:
        return _absent()

    if '\n' in str(field.value):
        return htpy.pre('.datum')[str(field.value)]

    return htpy.code[str(field.value)]


# -----------------------------------------------------------------------------
def _edges(item):
    if not (item.outgoing or item.incoming):
        return [htpy.h2['Edges'], htpy.p('.absent')['No edges.']]

    return [
        htpy.h2['Edges'],
        htpy.table[
            htpy.tbody[
                (htpy.tr[htpy.th['holds'], htpy.td('.relation')[relation],
                         htpy.td[_link(target)]]
                 for (relation, target) in item.outgoing),
                (htpy.tr[htpy.th['pointed at by'], htpy.td[_link(source)],
                         htpy.td('.relation')[relation]]
                 for (source, relation) in item.incoming)]]]


# -----------------------------------------------------------------------------
def _link(name):
    return htpy.a(href = PATH_ITEM + name)[name]


def _absent():
    return htpy.span('.absent')['none']


def _path_kind(prefix, query):
    return '{path}?kind={prefix}&q={query}'.format(path = PATH_INDEX, prefix = prefix,
                                                   query = query)


def _join(separator, iterable):
    out = []
    for element in iterable:
        if out:
            out.append(separator)
        out.append(element)
    return out
