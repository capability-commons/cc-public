"""
---

id_self:                pym_cc_public.web.server
guid_self:              pym_341d2bfc86774482a691f937d9524be7
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Review page server
brief:                  |
                        Serve the review pages over HTTP on this
                        computer.
description:            |
                        respond maps the path of a request to a page
                        (the issue list, an issue, the requirement
                        list, a requirement, the list of interface
                        control documents, or any item), or to a file
                        of the _static directory, and reads the tree
                        afresh for each page. serve answers GET
                        requests with respond, until interrupted. It
                        uses the HTTP server of the standard library.
relation:               []

...
"""


import http
import http.server
import mimetypes
import pathlib
import threading
import urllib.parse

import cc_public.web.argument
import cc_public.web.page
import cc_public.web.sankey


HOST_DEFAULT      = '127.0.0.1'
PORT_DEFAULT      = 8100
DIR_STATIC        = pathlib.Path(__file__).resolve().parent / '_static'
TYPE_HTML         = 'text/html; charset=utf-8'
TYPE_DEFAULT      = 'application/octet-stream'
LOCK_READ         = threading.Lock()
MAP_INDEX         = {'/':                                 cc_public.web.page.index,
                     cc_public.web.page.PATH_REQUIREMENTS: cc_public.web.page.requirements,
                     cc_public.web.page.PATH_INTERFACES:   cc_public.web.page.interfaces}


# -----------------------------------------------------------------------------
def respond(root: pathlib.Path, path: str) -> tuple[int, str, bytes]:
    """
    Return the status, the content type and the body of the response
    to a request for path, over the tree under root.

    The tree is read afresh for each page, so a page shows the tree as
    it is when the page is asked for.

    """

    (path, query) = (urllib.parse.urlsplit(path).path, urllib.parse.urlsplit(path).query)

    if path.startswith(cc_public.web.page.PATH_STATIC):
        return _static(path.removeprefix(cc_public.web.page.PATH_STATIC))

    if path in MAP_INDEX:
        return (http.HTTPStatus.OK, TYPE_HTML, MAP_INDEX[path](_graph(root)).encode())

    for prefix in (cc_public.web.page.PATH_ISSUE,
                   cc_public.web.page.PATH_REQUIREMENT,
                   cc_public.web.page.PATH_ITEM):
        if path.startswith(prefix):
            id_item = urllib.parse.unquote(path.removeprefix(prefix))
            body    = _item_page(_graph(root), prefix, id_item, query)
            if body is None:
                return (http.HTTPStatus.NOT_FOUND, TYPE_HTML,
                        cc_public.web.page.missing(id_item).encode())
            return (http.HTTPStatus.OK, TYPE_HTML, body.encode())

    return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cc_public.web.page.missing(path).encode())


# -----------------------------------------------------------------------------
def _graph(root: pathlib.Path) -> cc_public.web.argument.Graph:
    """
    Return the graph of the tree under root, read by one request at a
    time: the reader of cc_public.graph.extract and its cache are shared,
    and the server answers requests in threads.

    """

    with LOCK_READ:
        return cc_public.web.argument.Graph(root)


# -----------------------------------------------------------------------------
def _item_page(graph:   cc_public.web.argument.Graph,
               prefix:  str,
               id_item: str,
               query:   str) -> str | None:
    """
    Return the page of id_item at the path prefix, with the query of
    its address, or None if the tree holds no such issue or item.

    """

    if prefix == cc_public.web.page.PATH_ISSUE:
        issue = graph.issue(id_item)
        if issue is None:
            return None
        return cc_public.web.page.issue(graph, issue,
                                        cc_public.web.sankey.parse_toggle(query),
                                        cc_public.web.sankey.parse_show(query))

    if prefix == cc_public.web.page.PATH_REQUIREMENT:
        return cc_public.web.page.requirement(graph, id_item)

    if id_item not in graph.map_item:
        return None
    return cc_public.web.page.item(graph, id_item)


# -----------------------------------------------------------------------------
def _static(name: str) -> tuple[int, str, bytes]:
    """
    Return the response for the static file name. A name that leads out
    of the static directory is not found.

    """

    path = (DIR_STATIC / name).resolve()

    if DIR_STATIC not in path.parents or not path.is_file():
        return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cc_public.web.page.missing(name).encode())

    (type_content, _) = mimetypes.guess_type(path.name)
    return (http.HTTPStatus.OK, type_content or TYPE_DEFAULT, path.read_bytes())


# -----------------------------------------------------------------------------
def serve(root: pathlib.Path, host: str, port: int) -> None:
    """
    Serve the pages of the tree under root at host and port, until
    interrupted.

    """

    # -------------------------------------------------------------------------
    class Handler(http.server.BaseHTTPRequestHandler):
        """
        Answer each GET request with respond.

        """

        # ---------------------------------------------------------------------
        def do_GET(self) -> None:
            """
            Send the response to the request.

            """

            (status, type_content, body) = respond(root, self.path)
            self.send_response(status)
            self.send_header('Content-Type', type_content)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    with http.server.ThreadingHTTPServer((host, port), Handler) as server:
        server.serve_forever()
