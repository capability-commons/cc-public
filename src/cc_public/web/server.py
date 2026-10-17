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
                        respond maps the path of a request to a page,
                        or to a file of the _static directory, and
                        reads the tree afresh for each page. serve
                        answers GET requests with respond, until
                        interrupted. It uses the HTTP server of the
                        standard library.
relation:               []

...
"""


import http
import http.server
import mimetypes
import pathlib
import urllib.parse

import cc_public.web.argument
import cc_public.web.page
import cc_public.web.sankey


HOST_DEFAULT      = '127.0.0.1'
PORT_DEFAULT      = 8100
DIR_STATIC        = pathlib.Path(__file__).resolve().parent / '_static'
TYPE_HTML         = 'text/html; charset=utf-8'
TYPE_DEFAULT      = 'application/octet-stream'


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

    graph = cc_public.web.argument.Graph(root)

    if path == '/':
        return (http.HTTPStatus.OK, TYPE_HTML, cc_public.web.page.index(graph).encode())

    if path.startswith(cc_public.web.page.PATH_ISSUE):
        id_issue = urllib.parse.unquote(path.removeprefix(cc_public.web.page.PATH_ISSUE))
        issue    = graph.issue(id_issue)
        if issue is not None:
            return (http.HTTPStatus.OK, TYPE_HTML,
                    cc_public.web.page.issue(
                        graph, issue, cc_public.web.sankey.parse_open(query)).encode())
        return (http.HTTPStatus.NOT_FOUND, TYPE_HTML,
                cc_public.web.page.missing(id_issue).encode())

    return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cc_public.web.page.missing(path).encode())


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
