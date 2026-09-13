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
                        application opens the tree under the roots
                        given once, at construction, and serves that
                        reading until the process ends; an edit to the
                        tree is seen by starting again. The index
                        route renders the listing as a document; the
                        search route renders it as a fragment; the
                        item route renders one item as a document, or
                        as JSON at the sibling path ending in .json,
                        and answers not found where nothing is named
                        so. Static serves the vendored HTMX and the
                        stylesheet.
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


DIR_STATIC  = pathlib.Path(__file__).parent / 'static'
SUFFIX_JSON = '.json'


# -----------------------------------------------------------------------------
def application(list_root):
    """
    Return the Starlette application serving the tree under the roots
    given, read once here.

    """

    tree = cc_public.edit.tree.Tree(list_root)
    name = tree.root.name

    async def index(request):
        listing = cc_public.web.projection.listing(
                                tree,
                                query  = request.query_params.get('q', ''),
                                prefix = request.query_params.get('kind') or None)
        return _html(cc_public.web.page.document(
                                'Items', cc_public.web.page.index(listing), name))

    async def search(request):
        listing = cc_public.web.projection.listing(
                                tree,
                                query  = request.query_params.get('q', ''),
                                prefix = request.query_params.get('kind') or None)
        return _html(cc_public.web.page.fragment_listing(listing))

    async def item(request):
        found = cc_public.web.projection.detail(tree, request.path_params['name'])
        if found is None:
            return _not_found(request.path_params['name'])
        return _html(cc_public.web.page.document(
                                found.title or found.id_self,
                                cc_public.web.page.detail(found), name))

    async def item_json(request):
        found = cc_public.web.projection.detail(tree, request.path_params['name'])
        if found is None:
            return _not_found(request.path_params['name'])
        return starlette.responses.JSONResponse(_plain(found))

    return starlette.applications.Starlette(routes = [
        starlette.routing.Route(cc_public.web.page.PATH_INDEX,  index),
        starlette.routing.Route(cc_public.web.page.PATH_SEARCH, search),
        starlette.routing.Route(cc_public.web.page.PATH_ITEM + '{name}' + SUFFIX_JSON,
                                item_json),
        starlette.routing.Route(cc_public.web.page.PATH_ITEM + '{name}', item),
        starlette.routing.Mount(cc_public.web.page.PATH_STATIC.rstrip('/'),
                                starlette.staticfiles.StaticFiles(directory = DIR_STATIC),
                                name = 'static')])


# -----------------------------------------------------------------------------
def _html(element):
    return starlette.responses.HTMLResponse(str(element))


def _not_found(name):
    return starlette.responses.PlainTextResponse(
                'Nothing in this tree is named {name}.'.format(name = name),
                status_code = 404)


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
