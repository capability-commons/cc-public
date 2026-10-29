"""
---

id_self:                pym_cctool.web.server
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
                        items of a type, the logical components, a
                        logical component, a search, the decision
                        list, a decision, the requirement list, a
                        requirement, the list of interface control
                        documents, one of them, or any item), or to a
                        file of the _static directory, and reads the
                        tree afresh for each page. serve answers GET
                        requests with respond, until interrupted. It
                        uses the HTTP server of the standard library.

                        A page is served only to a request that names
                        the server by a name of this computer or by an
                        IP address. A site that points a name of its
                        own at this computer, and so has a browser
                        that views it ask for a page under that name,
                        is refused, so that it cannot read the tree.

                        submit answers the forms of the pages that
                        change the data. It turns a form into a batch
                        with pym_cctool.web.request and makes it with
                        pym_cctool.edit.edit, as cctool batch does:
                        the tree is checked with the edit in place,
                        and written only if the edit adds no failure.
                        A form sent from a page of any other site, or
                        to a server by any other name than this
                        computer's, is refused, so that another page
                        open in the browser cannot change the tree.
edge:                   []

...
"""


import http
import http.server
import ipaddress
import mimetypes
import pathlib
import threading
import urllib.parse

import cctool.check.check
import cctool.edit.edit
import cctool.graph.extract
import cctool.web.argument
import cctool.web.contract
import cctool.web.page
import cctool.web.request
import cctool.web.sankey


HOST_DEFAULT      = '127.0.0.1'
PORT_DEFAULT      = 8100
DIR_STATIC        = pathlib.Path(__file__).resolve().parent / '_static'
TYPE_HTML         = 'text/html; charset=utf-8'
TYPE_DEFAULT      = 'application/octet-stream'
SET_HOST_LOCAL    = {'127.0.0.1', 'localhost', '[::1]'}
LOCK_READ         = threading.Lock()
MAP_INDEX         = {cctool.web.page.PATH_HOME:         cctool.web.page.home,
                     cctool.web.page.PATH_DECISIONS:       cctool.web.page.decisions,
                     cctool.web.page.PATH_COMPONENTS:     cctool.web.page.components,
                     cctool.web.page.PATH_REQUIREMENTS: cctool.web.page.requirements,
                     cctool.web.page.PATH_INTERFACES:   cctool.web.page.interfaces}


# -----------------------------------------------------------------------------
def respond(root: pathlib.Path, path: str) -> tuple[int, str, bytes]:
    """
    Return the status, the content type and the body of the response
    to a request for path, over the tree under root.

    The tree is read afresh for each page, so a page shows the tree as
    it is when the page is asked for.

    """

    (path, query) = (urllib.parse.urlsplit(path).path, urllib.parse.urlsplit(path).query)

    if path.startswith(cctool.web.page.PATH_STATIC):
        return _static(path.removeprefix(cctool.web.page.PATH_STATIC))

    if path == cctool.web.page.PATH_EDIT:
        return _form(root, query)

    if path in MAP_INDEX or path == cctool.web.page.PATH_SEARCH:
        graph = _graph(root)
        if path == cctool.web.page.PATH_DECISIONS:
            body = cctool.web.page.decisions(graph, query)
        elif path in MAP_INDEX:
            body = MAP_INDEX[path](graph)
        else:
            body = cctool.web.page.search(graph, _text(query))
        return (http.HTTPStatus.OK, TYPE_HTML, body.encode())

    for prefix in (cctool.web.page.PATH_TYPE,
                   cctool.web.page.PATH_COMPONENT,
                   cctool.web.page.PATH_DECISION,
                   cctool.web.page.PATH_REQUIREMENT,
                   cctool.web.page.PATH_INTERFACE,
                   cctool.web.page.PATH_ITEM):
        if path.startswith(prefix):
            id_item = urllib.parse.unquote(path.removeprefix(prefix))
            body    = _item_page(root, prefix, id_item, query)
            if body is None:
                return (http.HTTPStatus.NOT_FOUND, TYPE_HTML,
                        cctool.web.page.missing(id_item).encode())
            return (http.HTTPStatus.OK, TYPE_HTML, body.encode())

    return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cctool.web.page.missing(path).encode())


# -----------------------------------------------------------------------------
def _form(root: pathlib.Path, query: str) -> tuple[int, str, bytes]:
    """
    Return the response to a request for the form that query asks for.

    """

    try:
        graph   = _graph(root)
        request = cctool.web.request.parse(query)
        body    = cctool.web.page.edit(graph, request)
    except cctool.web.request.ErrorRequest as error:
        return (http.HTTPStatus.BAD_REQUEST, TYPE_HTML,
                cctool.web.page.refused(str(error)).encode())
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
    no failure it is written, and the response leads to the decision page
    at what it made; if it adds any, nothing is written and the form is
    shown again with the failures it would add.

    """

    if not _is_local(host, origin):
        return (http.HTTPStatus.FORBIDDEN, TYPE_HTML,
                cctool.web.page.refused('Forms are taken only from the pages of this '
                                        'server, on this computer.').encode(), None)

    try:
        request = cctool.web.request.parse(body.decode('utf-8'))
        with LOCK_READ:
            graph          = cctool.web.argument.Graph(root)
            id_item        = cctool.web.request.id_new(graph, request)
            list_operation = cctool.web.request.operations(graph, request)
            tree           = cctool.edit.edit.Tree(root)
            cctool.edit.edit.batch(tree, list_operation)
            added          = cctool.edit.edit.apply(tree)
    except (cctool.web.request.ErrorRequest, cctool.edit.edit.ErrorEdit,
            UnicodeDecodeError) as error:
        return (http.HTTPStatus.BAD_REQUEST, TYPE_HTML,
                cctool.web.page.refused(str(error)).encode(), None)

    if added:
        list_added = ['{name}: {row}'.format(name = name, row = '  '.join(map(str, row)))
                      for (name, list_row) in added.items() for row in list_row]
        page       = cctool.web.page.edit(graph, request, list_added)
        return (http.HTTPStatus.UNPROCESSABLE_ENTITY, TYPE_HTML, page.encode(), None)

    return (http.HTTPStatus.SEE_OTHER, TYPE_HTML, b'',
            cctool.web.request.address(graph, request, id_item))


# -----------------------------------------------------------------------------
def is_readable(host: str) -> bool:
    """
    Return True if a page may be served to a request to the server named
    host: by a name of this computer, or by an IP address, which no
    other site can stand for. Any other name may be that of a site that
    points it at this computer.

    """

    name = _name(host)
    if name in SET_HOST_LOCAL or '[{name}]'.format(name = name) in SET_HOST_LOCAL:
        return True
    try:
        ipaddress.ip_address(name)
    except ValueError:
        return False
    return True


# -----------------------------------------------------------------------------
def _name(host: str) -> str:
    """
    Return the name of the server in host, the Host header of a
    request, without its port, or '' if host is not a host.

    """

    try:
        return urllib.parse.urlsplit('//' + host).hostname or ''
    except ValueError:
        return ''


# -----------------------------------------------------------------------------
def _is_local(host: str, origin: str | None) -> bool:
    """
    Return True if host names this computer, and origin, if a browser
    sent one, is a page of the server named host.

    """

    name = _name(host)
    if name not in SET_HOST_LOCAL and '[{name}]'.format(name = name) not in SET_HOST_LOCAL:
        return False
    return origin is None or origin == 'http://' + host


# -----------------------------------------------------------------------------
def _graph(root: pathlib.Path) -> cctool.web.argument.Graph:
    """
    Return the graph of the tree under root, read by one request at a
    time: the reader of cctool.graph.extract and its cache are shared,
    and the server answers requests in threads.

    """

    with LOCK_READ:
        return cctool.web.argument.Graph(root)


# -----------------------------------------------------------------------------
def _item_page(root:    pathlib.Path,
               prefix:  str,
               id_item: str,
               query:   str) -> str | None:
    """
    Return the page of id_item at the path prefix in the tree under
    root, with the query of its address, or None if the tree holds no
    such decision or item.

    """

    if prefix == cctool.web.page.PATH_INTERFACE:
        with LOCK_READ:
            (graph, facts) = (cctool.web.argument.Graph(root),
                              cctool.web.contract.facts(root))
        return cctool.web.page.interface(graph, facts, id_item)

    graph = _graph(root)

    if prefix in (cctool.web.page.PATH_TYPE, cctool.web.page.PATH_COMPONENT):
        return _catalog_page(graph, prefix, id_item, query)

    if prefix == cctool.web.page.PATH_DECISION:
        decision = graph.decision(id_item)
        if decision is None:
            return None
        return cctool.web.page.decision(graph, decision,
                                        cctool.web.sankey.parse_toggle(query),
                                        cctool.web.sankey.parse_show(query))

    if prefix == cctool.web.page.PATH_REQUIREMENT:
        return cctool.web.page.requirement(graph, id_item)

    return cctool.web.page.item(graph, id_item) if id_item in graph.map_item else None


# -----------------------------------------------------------------------------
def _catalog_page(graph:   cctool.web.argument.Graph,
                    prefix:  str,
                    id_item: str,
                    query:   str) -> str | None:
    """
    Return the list of the items of the type id_item, or the page of
    the subject id_item, as prefix says, or None if graph has no such
    type or subject.

    """

    if prefix == cctool.web.page.PATH_TYPE:
        return cctool.web.page.type_list(graph, id_item, _text(query))
    return cctool.web.page.component(graph, id_item)


# -----------------------------------------------------------------------------
def _text(query: str) -> str:
    """
    Return the words typed into the search box, from query.

    """

    map_value = urllib.parse.parse_qs(query)
    return map_value.get(cctool.web.page.KEY_QUERY, [''])[0].strip()


# -----------------------------------------------------------------------------
def _static(name: str) -> tuple[int, str, bytes]:
    """
    Return the response for the static file name. A name that leads out
    of the static directory is not found.

    """

    path = (DIR_STATIC / name).resolve()

    if DIR_STATIC not in path.parents or not path.is_file():
        return (http.HTTPStatus.NOT_FOUND, TYPE_HTML, cctool.web.page.missing(name).encode())

    (type_content, _) = mimetypes.guess_type(path.name)
    return (http.HTTPStatus.OK, type_content or TYPE_DEFAULT, path.read_bytes())


# -----------------------------------------------------------------------------
def serve(root: pathlib.Path, host: str, port: int) -> None:
    """
    Serve the pages of the tree under root at host and port, until
    interrupted.

    """

    threading.Thread(target = _warm, args = (root,), daemon = True).start()

    with server(root, host, port) as each:
        each.serve_forever()


# -----------------------------------------------------------------------------
def server(root: pathlib.Path, host: str, port: int) -> http.server.ThreadingHTTPServer:
    """
    Return a server of the pages of the tree under root, bound to host
    and port, that is not yet serving.

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
            Send the response to the request, unless it names the
            server by a name that is_readable refuses.

            """

            if not is_readable(self.headers.get('Host') or ''):
                self.send_error(http.HTTPStatus.FORBIDDEN,
                                'Pages are served only under a name of this computer, or '
                                'an IP address.')
                return

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

            if urllib.parse.urlsplit(self.path).path != cctool.web.page.PATH_EDIT:
                self.send_error(http.HTTPStatus.NOT_FOUND)
                return

            text = self.headers.get('Content-Length') or '0'
            if not (text.isascii() and text.isdigit()):
                self.send_error(http.HTTPStatus.BAD_REQUEST,
                                'The Content-Length is not a number of bytes.')
                return

            (status, type_content, body, location) = submit(root,
                                                            self.headers.get('Host') or '',
                                                            self.headers.get('Origin'),
                                                            self.rfile.read(int(text)))
            self.send_response(status)
            if location:
                self.send_header('Location', location)
            self.send_header('Content-Type', type_content)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return http.server.ThreadingHTTPServer((host, port), Handler)


# -----------------------------------------------------------------------------
def _warm(root: pathlib.Path) -> None:
    """
    Read and check the tree under root once, so that the first page and
    the first form do not wait for every YAML document to be parsed and
    validated. A request that comes meanwhile waits for it.

    """

    with LOCK_READ:
        cctool.web.argument.Graph(root)
        cctool.check.check.check_documents(cctool.graph.extract.documents(root),
                                           cctool.check.check.CACHE_SCHEMA)
