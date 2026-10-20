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
                        (the index of every type, the list of the
                        items of a type, the subjects, a subject, a
                        search, the issue list, an issue, the
                        requirement list, a requirement, the list of
                        interface control documents, one of them, or
                        any item), or to a file of the _static
                        directory, and reads the tree afresh for each
                        page. serve answers GET requests with respond,
                        until interrupted. It uses the HTTP server of
                        the standard library.

                        submit answers the forms of the pages that
                        change the data. It turns a form into a batch
                        with pym_cc_public.web.request and makes it
                        with pym_cc_public.edit.edit, as cctool batch
                        does: the tree is checked with the edit in
                        place, and written only if the edit adds no
                        failure. A form sent from a page of any other
                        site, or to a server by any other name than
                        this computer's, is refused, so that another
                        page open in the browser cannot change the
                        tree.
relation:               []

...
"""


import http
import http.server
import mimetypes
import pathlib
import threading
import urllib.parse

import cc_public.check.check
import cc_public.edit.edit
import cc_public.graph.extract
import cc_public.web.argument
import cc_public.web.contract
import cc_public.web.page
import cc_public.web.request
import cc_public.web.sankey


HOST_DEFAULT      = '127.0.0.1'
PORT_DEFAULT      = 8100
DIR_STATIC        = pathlib.Path(__file__).resolve().parent / '_static'
TYPE_HTML         = 'text/html; charset=utf-8'
TYPE_DEFAULT      = 'application/octet-stream'
SET_HOST_LOCAL    = {'127.0.0.1', 'localhost', '[::1]'}
LOCK_READ         = threading.Lock()
MAP_INDEX         = {cc_public.web.page.PATH_HOME:         cc_public.web.page.home,
                     cc_public.web.page.PATH_ISSUES:       cc_public.web.page.issues,
                     cc_public.web.page.PATH_SUBJECTS:     cc_public.web.page.subjects,
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

    if path == cc_public.web.page.PATH_EDIT:
        return _form(root, query)

    if path in MAP_INDEX or path == cc_public.web.page.PATH_SEARCH:
        graph = _graph(root)
        body  = (MAP_INDEX[path](graph) if path in MAP_INDEX
                 else cc_public.web.page.search(graph, _text(query)))
        return (http.HTTPStatus.OK, TYPE_HTML, body.encode())

    for prefix in (cc_public.web.page.PATH_TYPE,
                   cc_public.web.page.PATH_SUBJECT,
                   cc_public.web.page.PATH_ISSUE,
                   cc_public.web.page.PATH_REQUIREMENT,
                   cc_public.web.page.PATH_INTERFACE,
                   cc_public.web.page.PATH_ITEM):
        if path.startswith(prefix):
            id_item = urllib.parse.unquote(path.removeprefix(prefix))
            body    = _item_page(root, prefix, id_item, query)
            if body is None:
                return (http.HTTPStatus.NOT_FOUND, TYPE_HTML,
                        cc_public.web.page.missing(id_item).encode())
            return (http.HTTPStatus.OK, TYPE_HTML, body.encode())

    return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cc_public.web.page.missing(path).encode())


# -----------------------------------------------------------------------------
def _form(root: pathlib.Path, query: str) -> tuple[int, str, bytes]:
    """
    Return the response to a request for the form that query asks for.

    """

    try:
        graph   = _graph(root)
        request = cc_public.web.request.parse(query)
        body    = cc_public.web.page.edit(graph, request)
    except cc_public.web.request.ErrorRequest as error:
        return (http.HTTPStatus.BAD_REQUEST, TYPE_HTML,
                cc_public.web.page.refused(str(error)).encode())
    return (http.HTTPStatus.OK, TYPE_HTML, body.encode())


# -----------------------------------------------------------------------------
def submit(root:   pathlib.Path,
           host:   str,
           origin: str | None,
           body:   bytes) -> tuple[int, str, bytes, str | None]:
    """
    Return the status, content type, body and the address to go to of
    the response to a form sent with body, to the server named host
    from a page at origin.

    The form is made as one batch over the tree under root. If it adds
    no failure it is written, and the response leads to the issue page
    at what it made; if it adds any, nothing is written and the form is
    shown again with the failures it would add.

    """

    if not _is_local(host, origin):
        return (http.HTTPStatus.FORBIDDEN, TYPE_HTML,
                cc_public.web.page.refused('Forms are taken only from the pages of this '
                                           'server, on this computer.').encode(), None)

    try:
        request = cc_public.web.request.parse(body.decode('utf-8'))
        with LOCK_READ:
            graph          = cc_public.web.argument.Graph(root)
            id_item        = cc_public.web.request.id_new(graph, request)
            list_operation = cc_public.web.request.operations(graph, request)
            tree           = cc_public.edit.edit.Tree(root)
            cc_public.edit.edit.batch(tree, list_operation)
            added          = cc_public.edit.edit.apply(tree)
    except (cc_public.web.request.ErrorRequest, cc_public.edit.edit.ErrorEdit,
            UnicodeDecodeError) as error:
        return (http.HTTPStatus.BAD_REQUEST, TYPE_HTML,
                cc_public.web.page.refused(str(error)).encode(), None)

    if added:
        list_added = ['{name}: {row}'.format(name = name, row = '  '.join(map(str, row)))
                      for (name, list_row) in added.items() for row in list_row]
        page       = cc_public.web.page.edit(graph, request, list_added)
        return (http.HTTPStatus.UNPROCESSABLE_ENTITY, TYPE_HTML, page.encode(), None)

    return (http.HTTPStatus.SEE_OTHER, TYPE_HTML, b'',
            cc_public.web.request.address(graph, request, id_item))


# -----------------------------------------------------------------------------
def _is_local(host: str, origin: str | None) -> bool:
    """
    Return True if host names this computer, and origin, if a browser
    sent one, is a page of the server named host.

    """

    name = urllib.parse.urlsplit('//' + host).hostname or ''
    if name not in SET_HOST_LOCAL and '[{name}]'.format(name = name) not in SET_HOST_LOCAL:
        return False
    return origin is None or origin == 'http://' + host


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
def _item_page(root:    pathlib.Path,
               prefix:  str,
               id_item: str,
               query:   str) -> str | None:
    """
    Return the page of id_item at the path prefix in the tree under
    root, with the query of its address, or None if the tree holds no
    such issue or item.

    """

    if prefix == cc_public.web.page.PATH_INTERFACE:
        with LOCK_READ:
            (graph, facts) = (cc_public.web.argument.Graph(root),
                              cc_public.web.contract.facts(root))
        return cc_public.web.page.interface(graph, facts, id_item)

    graph = _graph(root)

    if prefix in (cc_public.web.page.PATH_TYPE, cc_public.web.page.PATH_SUBJECT):
        return _catalogue_page(graph, prefix, id_item, query)

    if prefix == cc_public.web.page.PATH_ISSUE:
        issue = graph.issue(id_item)
        if issue is None:
            return None
        return cc_public.web.page.issue(graph, issue,
                                        cc_public.web.sankey.parse_toggle(query),
                                        cc_public.web.sankey.parse_show(query))

    if prefix == cc_public.web.page.PATH_REQUIREMENT:
        return cc_public.web.page.requirement(graph, id_item)

    return cc_public.web.page.item(graph, id_item) if id_item in graph.map_item else None


# -----------------------------------------------------------------------------
def _catalogue_page(graph:   cc_public.web.argument.Graph,
                    prefix:  str,
                    id_item: str,
                    query:   str) -> str | None:
    """
    Return the list of the items of the type id_item, or the page of
    the subject id_item, as prefix says, or None if graph has no such
    type or subject.

    """

    if prefix == cc_public.web.page.PATH_TYPE:
        return cc_public.web.page.type_list(graph, id_item, _text(query))
    return cc_public.web.page.subject(graph, id_item)


# -----------------------------------------------------------------------------
def _text(query: str) -> str:
    """
    Return the words typed into the search box, from query.

    """

    map_value = urllib.parse.parse_qs(query)
    return map_value.get(cc_public.web.page.KEY_QUERY, [''])[0].strip()


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
        Answer each GET request with respond, and each POST request
        with submit.

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

        # ---------------------------------------------------------------------
        def do_POST(self) -> None:
            """
            Send the response to the form sent.

            """

            if urllib.parse.urlsplit(self.path).path != cc_public.web.page.PATH_EDIT:
                self.send_error(http.HTTPStatus.NOT_FOUND)
                return

            length = int(self.headers.get('Content-Length') or 0)
            (status, type_content, body, location) = submit(root,
                                                            self.headers.get('Host') or '',
                                                            self.headers.get('Origin'),
                                                            self.rfile.read(length))
            self.send_response(status)
            if location:
                self.send_header('Location', location)
            self.send_header('Content-Type', type_content)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    threading.Thread(target = _warm, args = (root,), daemon = True).start()

    with http.server.ThreadingHTTPServer((host, port), Handler) as server:
        server.serve_forever()


# -----------------------------------------------------------------------------
def _warm(root: pathlib.Path) -> None:
    """
    Read and check the tree under root once, so that the first page and
    the first form do not wait for every document to be parsed and
    validated. A request that comes meanwhile waits for it.

    """

    with LOCK_READ:
        cc_public.web.argument.Graph(root)
        cc_public.check.check.check_documents(cc_public.graph.extract.documents(root),
                                              cc_public.check.check.CACHE_SCHEMA)
