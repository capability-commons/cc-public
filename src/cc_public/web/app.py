"""
---

id_self:                pym_cc_public.web.app
guid_self:              pym_63963ac772c2402e8a81f35211826e8b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Application
brief:                  |
                        The Starlette application: the routes, what
                        each renders, and the static files.
description:            |
                        The application function opens the tree under
                        the roots given once, indexes it, and reads
                        the views it holds; a tree holding no view is
                        refused, since a view is what says where a
                        tree of rows begins. The surface route renders
                        the whole page for the view chosen, the rows
                        route renders the root rows alone so that the
                        filter fills in place, the groups route
                        renders the children of one row, and the
                        record route renders one item read in full,
                        with the same projection as JSON at a sibling
                        path. An edit to the tree is seen by starting
                        again.
relation:               []

...
"""


import pathlib

import starlette.applications
import starlette.responses
import starlette.routing
import starlette.staticfiles

import cc_public.edit.tree
import cc_public.web.page
import cc_public.web.projection


DIR_STATIC = pathlib.Path(__file__).parent / 'static'
PATH_JSON  = '/record.json'


# -----------------------------------------------------------------------------
def application(list_root):
    """
    Return the Starlette application serving the tree under the roots
    given, read and indexed once here.

    """

    tree   = cc_public.edit.tree.Tree(list_root)
    name   = tree.root.name
    stamp  = str(max((int(path.stat().st_mtime) for path in DIR_STATIC.iterdir()),
                     default = 0))
    graph  = cc_public.web.projection.graph(tree)
    scope  = cc_public.web.projection.views(graph)

    if not scope:
        raise cc_public.edit.tree.ErrorItem(
                'This tree holds no view, so there is nothing to serve. A view '
                'says what sits at the root and which edges are children.')

    def chosen(request):
        wanted = request.query_params.get('view')
        return next((one for one in scope if one.id_self == wanted), scope[0])

    async def surface(request):
        view = chosen(request)
        text = request.query_params.get('q', '')
        rows = cc_public.web.projection.roots(graph, view, text)
        return _html(cc_public.web.page.document(
                        view.title,
                        cc_public.web.page.surface(scope, view, rows, text),
                        name, stamp))

    async def rows(request):
        view = chosen(request)
        return _html(cc_public.web.page.fragment_rows(
                        cc_public.web.projection.roots(
                                graph, view, request.query_params.get('q', ''))))

    async def opened(request):
        view  = chosen(request)
        path  = tuple(p for p in request.query_params.get('path', '').split(
                                    cc_public.web.page.SEPARATOR) if p)
        found = cc_public.web.projection.opened(graph, view, path) if path else None
        if found is None:
            return _not_found(request.query_params.get('path', ''))
        return _html(cc_public.web.page.fragment_groups(found))

    async def record(request):
        found = cc_public.web.projection.record(graph, request.query_params.get('id', ''))
        if found is None:
            return _not_found(request.query_params.get('id', ''))
        return _html(cc_public.web.page.fragment_record(found))

    async def record_json(request):
        found = cc_public.web.projection.record(graph, request.query_params.get('id', ''))
        if found is None:
            return _not_found(request.query_params.get('id', ''))
        return starlette.responses.JSONResponse(_plain(found))

    return starlette.applications.Starlette(routes = [
        starlette.routing.Route(cc_public.web.page.PATH_SURFACE, surface),
        starlette.routing.Route(cc_public.web.page.PATH_ROWS,    rows),
        starlette.routing.Route(cc_public.web.page.PATH_GROUPS,  opened),
        starlette.routing.Route(PATH_JSON,                       record_json),
        starlette.routing.Route(cc_public.web.page.PATH_RECORD,  record),
        starlette.routing.Mount(cc_public.web.page.PATH_STATIC.rstrip('/'),
                                starlette.staticfiles.StaticFiles(directory = DIR_STATIC),
                                name = 'static')])


# -----------------------------------------------------------------------------
def _html(element):
    return starlette.responses.HTMLResponse(str(element))


# -----------------------------------------------------------------------------
def _not_found(name):
    return starlette.responses.PlainTextResponse(
                'Nothing in this tree is named {name}.'.format(name = name),
                status_code = 404)


# -----------------------------------------------------------------------------
def _plain(value):
    """
    Return a projection as what JSON can hold: named tuples as objects,
    tuples as lists.

    """

    if hasattr(value, '_asdict'):
        return {key: _plain(one) for (key, one) in value._asdict().items()}

    if isinstance(value, (tuple, list)):
        return [_plain(one) for one in value]

    if isinstance(value, dict):
        return {str(key): _plain(one) for (key, one) in value.items()}

    return value
