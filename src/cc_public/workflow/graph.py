"""
---

id_self:                pym_cc_public.workflow.graph
guid_self:              pym_ef2c77423b1b4f63b8ee09b7292be458
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Workflow graph
brief:                  |
                        A dataflow workflow read for running: nodes,
                        their components, their ports, and the edges
                        between them.
description:            |
                        Resolves each node to the component it
                        instantiates and each edge to the ports it
                        joins, orders the nodes by their forward
                        edges, and says which inputs the graph leaves
                        unbound.
relation:               []

...
"""


import collections

import cc_public.check.workflow
import cc_public.path


KEY_NODE      = 'node'
KEY_EDGE      = 'edge'
KEY_EDGE_BACK = 'edge_back'
KEY_FROM      = 'from'
KEY_TO        = 'to'
KEY_GUARD     = 'guard'
KEY_CARRIES   = 'carries'
CARRIES_ITEM  = 'item'
KEY_INPUT     = 'input'
KEY_OUTPUT    = 'output'
KEY_OPTIONAL  = 'optional'

DELIM         = '.'


# -----------------------------------------------------------------------------
class ErrorGraph(Exception):
    """
    Raised for a workflow that cannot be run as written.

    """



# -----------------------------------------------------------------------------
class Graph:
    """
    One workflow, resolved.

    """

    def __init__(self, tree, id_workflow):

        item          = tree.resolve(id_workflow)
        self.id_self  = item.id_self
        self.document = tree.context.map_document[item.filepath]
        map_by_guid   = {d['guid_self']: d
                         for d in tree.context.map_document.values()
                         if isinstance(d, dict) and 'guid_self' in d}

        self.node      = {}
        self.component = {}

        for (local, node) in (self.document.get(KEY_NODE) or {}).items():
            component = cc_public.check.workflow._component_of(node, map_by_guid)
            if component is None:
                raise ErrorGraph('Node {local} names no component this tree '
                                 'holds.'.format(local = local))
            self.node[local]      = node
            self.component[local] = component

        self.edge      = self.document.get(KEY_EDGE) or {}
        self.edge_back = self.document.get(KEY_EDGE_BACK) or {}

    # -------------------------------------------------------------------------
    def order(self):
        """
        Return the nodes in an order that respects the forward edges.

        """

        map_in = collections.defaultdict(set)

        for edge in self.edge.values():
            map_in[edge[KEY_TO].split(DELIM, 1)[0]].add(
                                        edge[KEY_FROM].split(DELIM, 1)[0])

        placed = []
        ready  = sorted(n for n in self.node if not map_in[n])

        while ready:
            node = ready.pop(0)
            placed.append(node)
            for other in sorted(self.node):
                if other not in placed and other not in ready \
                        and map_in[other] <= set(placed):
                    ready.append(other)

        if len(placed) != len(self.node):
            raise ErrorGraph('The graph has a cycle no back edge declares.')

        return placed

    # -------------------------------------------------------------------------
    def inputs(self, local):
        return self.component[local].get(KEY_INPUT) or {}

    def outputs(self, local):
        return self.component[local].get(KEY_OUTPUT) or {}

    # -------------------------------------------------------------------------
    def outgoing(self, local, port):
        """
        Return [(node, port, guard, carries)] for the forward edges leaving
        a port.

        """

        out = []

        for edge in self.edge.values():
            if edge[KEY_FROM] == f'{local}.output.{port}':
                (node_dst, _, port_dst) = edge[KEY_TO].split(DELIM)
                out.append((node_dst, port_dst, edge.get(KEY_GUARD),
                            edge.get(KEY_CARRIES, CARRIES_ITEM)))

        return out

    # -------------------------------------------------------------------------
    def outgoing_back(self, local, port):
        """
        Return [(node, port, guard, carries)] for the back edges leaving a
        port.

        """

        out = []

        for edge in self.edge_back.values():
            if edge[KEY_FROM] == f'{local}.output.{port}':
                (node_dst, _, port_dst) = edge[KEY_TO].split(DELIM)
                out.append((node_dst, port_dst, edge.get(KEY_GUARD),
                            edge.get(KEY_CARRIES, CARRIES_ITEM)))

        return out

    # -------------------------------------------------------------------------
    def incoming(self, local, port):
        """
        Return [(node, port, guard)] for the forward edges entering a port.

        """

        out = []

        for edge in self.edge.values():
            if edge[KEY_TO] == f'{local}.input.{port}':
                (node_src, _, port_src) = edge[KEY_FROM].split(DELIM)
                out.append((node_src, port_src, edge.get(KEY_GUARD)))

        return out

    # -------------------------------------------------------------------------
    def unbound(self):
        """
        Return [(node, port, is_optional)] for inputs no forward edge feeds.
        These are the graph's own inputs.

        """

        out = []

        for local in self.node:
            for (port, spec) in self.inputs(local).items():
                if not self.incoming(local, port):
                    out.append((local, port, bool(spec.get(KEY_OPTIONAL))))

        return out
