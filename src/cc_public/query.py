"""
---

id_self:                pym_cc_public.query
guid_self:              pym_c51a761be6c14f958655cf7edebcabbf
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Query
brief:                  |
                        The facts loaded into an in-memory SQLite
                        database, walked, pathed, and asked questions.
description:            |
                        Loads the facts into a database that lives for
                        one command, and answers over it: the
                        neighbourhood of an item to a depth along
                        chosen relations in either direction, a
                        shortest path between two items, what nothing
                        points at and what no edge uses, and any SQL a
                        caller or a named query item gives. Draws a
                        walk as Graphviz dot or as mermaid. See
                        ddr_graph_query.
relation:               []

...
"""


import sqlite3
import typing

import cc_public.facts


KEY_ID_SELF   = 'id_self'
KEY_SQL       = 'sql'

DIRECTION_ALL = ('out', 'in')

# The tables, as SQL knows them. A query names them and nothing else.
#
SCHEMA = """
CREATE TABLE item        (guid TEXT PRIMARY KEY, id_self TEXT, prefix TEXT,
                          status TEXT, location TEXT);
CREATE TABLE edge        (guid_source TEXT, id_relation TEXT, guid_target TEXT,
                          id_target TEXT);
CREATE TABLE containment (guid_holder TEXT, guid_held TEXT);
CREATE INDEX edge_source ON edge (guid_source);
CREATE INDEX edge_target ON edge (guid_target);
"""


# -----------------------------------------------------------------------------
class Step(typing.NamedTuple):
    """
    One item reached in a walk: at what depth, from which item, by
    which relation, and in which direction, out along an edge the
    source holds or in along an edge that names it.

    """

    depth:       int
    id_self:     str
    guid:        str
    id_from:     str | None
    id_relation: str | None
    direction:   str | None


# -----------------------------------------------------------------------------
class Database:
    """
    The facts of a tree, loaded into an in-memory SQLite database that
    lives as long as this object.

    """

    def __init__(self, map_document):
        self.facts = cc_public.facts.facts(map_document)
        self.db    = sqlite3.connect(':memory:')
        self.db.executescript(SCHEMA)
        self.db.executemany('INSERT INTO item VALUES (?, ?, ?, ?, ?)', self.facts.item)
        self.db.executemany('INSERT INTO edge VALUES (?, ?, ?, ?)', self.facts.edge)
        self.db.executemany('INSERT INTO containment VALUES (?, ?)', self.facts.containment)
        self.db.commit()

    # -------------------------------------------------------------------------
    def close(self):
        """
        Let the database go. Safe to call twice.

        """

        if self.db is not None:
            self.db.close()
            self.db = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):
        self.close()

    # -------------------------------------------------------------------------
    def guid_of(self, name):
        """
        Return the guid of the item called name, an id or a guid, or None.

        """

        row = self.db.execute('SELECT guid FROM item WHERE guid = ? OR id_self = ?',
                              (name, name)).fetchone()

        return row[0] if row else None

    # -------------------------------------------------------------------------
    def id_of(self, guid):
        """
        Return the readable id of guid, or the guid where nothing carries it.

        """

        row = self.db.execute('SELECT id_self FROM item WHERE guid = ?', (guid,)).fetchone()

        return row[0] if row and row[0] else guid

    # -------------------------------------------------------------------------
    def run(self, sql, parameters = ()):
        """
        ---

        id_self:                pyf_cc_public.query.database.run
        guid_self:              pyf_02ebd9a3cfb34863bd2716945a09e578
        copyright:              Copyright 2026 William Payne
        license:                Apache-2.0

        protective_mark:

          - id_mark:            mark_public
            guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

        title:                  Run
        brief:                  |
                                Return (column names, rows) for a query over
                                the facts.
        description:            |
                                Runs SQL over the fact tables and returns the
                                column names with the rows.
        relation:               []

        ...
        """

        cursor = self.db.execute(sql, parameters)
        names  = [d[0] for d in cursor.description or ()]

        return (names, [tuple(row) for row in cursor.fetchall()])

    # -------------------------------------------------------------------------
    def walk(self, name, depth = 1, list_relation = (), list_direction = DIRECTION_ALL):
        """
        ---

        id_self:                pyf_cc_public.query.database.walk
        guid_self:              pyf_100de10c70814fca80c132c66d1e6890
        copyright:              Copyright 2026 William Payne
        license:                Apache-2.0

        protective_mark:

          - id_mark:            mark_public
            guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

        title:                  Walk
        brief:                  |
                                Return the Steps within depth of the item
                                called name, breadth first, each item once at
                                the depth it is first reached, along the
                                relations named or every relation, in the
                                directions asked.
        description:            |
                                Breadth first from the start item, each item
                                once at the depth it is first reached, along
                                the relations named or every relation, in the
                                directions asked, with the edge that reached
                                it.
        relation:               []

        ...
        """

        guid_start = self.guid_of(name)

        if guid_start is None:
            return None

        seen  = {guid_start}
        list_step = [Step(0, self.id_of(guid_start), guid_start, None, None, None)]
        frontier  = [guid_start]

        for n in range(1, depth + 1):
            reached = []
            for guid in frontier:
                for (guid_next, relation, direction) in self._adjacent(guid, list_relation,
                                                                       list_direction):
                    if guid_next in seen:
                        continue
                    seen.add(guid_next)
                    reached.append(guid_next)
                    list_step.append(Step(n, self.id_of(guid_next), guid_next,
                                          self.id_of(guid), relation, direction))
            frontier = reached
            if not frontier:
                break

        return list_step

    # -------------------------------------------------------------------------
    def path(self, name_from, name_to):
        """
        ---

        id_self:                pyf_cc_public.query.database.path
        guid_self:              pyf_2d6ec8ed72c84bb785b8536d7712b4f4
        copyright:              Copyright 2026 William Payne
        license:                Apache-2.0

        protective_mark:

          - id_mark:            mark_public
            guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

        title:                  Path
        brief:                  |
                                Return a shortest path from one item to
                                another as a list of Steps, the first at depth
                                zero; an empty list where no path joins them;
                                None where either name is unknown.
        description:            |
                                Breadth first from one item until the other is
                                reached, then the way back retraced; an empty
                                list where no path joins them, None where
                                either name is unknown.
        relation:               []

        ...
        """

        guid_from = self.guid_of(name_from)
        guid_to   = self.guid_of(name_to)

        if guid_from is None or guid_to is None:
            return None

        came_from = {guid_from: None}
        frontier  = [guid_from]

        while frontier and guid_to not in came_from:
            reached = []
            for guid in frontier:
                for (guid_next, relation, direction) in self._adjacent(guid, (), DIRECTION_ALL):
                    if guid_next not in came_from:
                        came_from[guid_next] = (guid, relation, direction)
                        reached.append(guid_next)
            frontier = reached

        if guid_to not in came_from:
            return []

        list_step = []
        guid      = guid_to
        while guid is not None:
            before = came_from[guid]
            list_step.append(Step(0, self.id_of(guid), guid,
                                  self.id_of(before[0]) if before else None,
                                  before[1] if before else None,
                                  before[2] if before else None))
            guid = before[0] if before else None
        list_step.reverse()

        return [s._replace(depth = n) for (n, s) in enumerate(list_step)]

    # -------------------------------------------------------------------------
    def orphans(self):
        """
        ---

        id_self:                pyf_cc_public.query.database.orphans
        guid_self:              pyf_af990ce834a44a819b497769528679c9
        copyright:              Copyright 2026 William Payne
        license:                Apache-2.0

        protective_mark:

          - id_mark:            mark_public
            guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

        title:                  Orphans
        brief:                  |
                                Return (items no edge points at, relations no
                                edge uses), as ids.
        description:            |
                                Two queries over the facts: items that no edge
                                points at and no item holds, and relation
                                entries that no edge is labelled with.
        relation:               []

        ...
        """

        (_, rows) = self.run("""
            SELECT id_self FROM item
            WHERE guid NOT IN (SELECT guid_target FROM edge)
              AND guid NOT IN (SELECT guid_held FROM containment)
            ORDER BY id_self""")
        list_item = [r[0] for r in rows]
        (_, rows) = self.run("""
            SELECT id_self FROM item
            WHERE prefix = 'r'
              AND id_self NOT IN (SELECT DISTINCT id_relation FROM edge)
            ORDER BY id_self""")
        list_relation = [r[0] for r in rows]

        return (list_item, list_relation)

    # -------------------------------------------------------------------------
    def _adjacent(self, guid, list_relation, list_direction):
        """
        Yield (guid, relation, direction) for every edge at guid in the
        directions asked, along the relations named or all.

        """

        clause = ''
        params = [guid]
        if list_relation:
            clause  = ' AND id_relation IN ({q})'.format(q = ','.join('?' * len(list_relation)))
            params += list(list_relation)
        if 'out' in list_direction:
            for (target, relation) in self.db.execute(
                    'SELECT guid_target, id_relation FROM edge WHERE guid_source = ?' + clause,  # noqa: S608 -- placeholders only
                    params):
                yield (target, relation, 'out')
        if 'in' in list_direction:
            for (source, relation) in self.db.execute(
                    'SELECT guid_source, id_relation FROM edge WHERE guid_target = ?' + clause,  # noqa: S608 -- placeholders only
                    params):
                yield (source, relation, 'in')


# -----------------------------------------------------------------------------
def named(map_document, name):
    """
    ---

    id_self:                pyf_cc_public.query.named
    guid_self:              pyf_3065b021018c4b30a3f48f57a0b5ead6
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Named query
    brief:                  |
                            Return the SQL of the query item called name,
                            or None.
    description:            |
                            Finds the query item called by name and
                            returns the SQL it holds.
    relation:               []

    ...
    """

    for document in map_document.values():
        if isinstance(document, dict) and document.get(KEY_ID_SELF) == name:
            return document.get(KEY_SQL)

    return None


# -----------------------------------------------------------------------------
def drawing(list_step, id_format):
    """
    ---

    id_self:                pyf_cc_public.query.drawing
    guid_self:              pyf_e9351a12dedb4d3a8c4715ea7168b9ac
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Drawing
    brief:                  |
                            Return the steps of a walk as a drawing: dot
                            for Graphviz, or mermaid.
    description:            |
                            The steps of a walk as a drawing: one node per
                            item and one edge labelled with its relation
                            per step that reached an item, in Graphviz dot
                            or in mermaid.
    relation:               []

    ...
    """

    edges = [(s.id_from, s.id_self) if s.direction == 'out' else (s.id_self, s.id_from)
             for s in list_step if s.id_from is not None]
    labels = [s.id_relation for s in list_step if s.id_from is not None]

    if id_format == 'mermaid':
        lines = ['graph LR']
        for (n, s) in enumerate(list_step):
            lines.append('    n{n}["{id}"]'.format(n = n, id = s.id_self))
        index = {s.id_self: n for (n, s) in enumerate(list_step)}
        for ((a, b), label) in zip(edges, labels, strict = True):
            lines.append('    n{a} -->|{label}| n{b}'.format(a = index[a], b = index[b],
                                                             label = label))
        return '\n'.join(lines) + '\n'

    lines = ['digraph {', '    rankdir=LR;']
    for s in list_step:
        lines.append('    "{id}";'.format(id = s.id_self))
    for ((a, b), label) in zip(edges, labels, strict = True):
        lines.append('    "{a}" -> "{b}" [label="{label}"];'.format(a = a, b = b, label = label))
    lines.append('}')

    return '\n'.join(lines) + '\n'
