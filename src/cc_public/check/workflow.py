"""
---

id_self:                pym_cc_public.check.workflow
guid_self:              pym_a1cd2896606a40538114a119b7a38bef
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Workflow check
brief:                  |
                        Check that a dataflow workflow is a graph that
                        can run.
description:            |
                        Holds each dataflow workflow against what its
                        schema cannot say: that every port an edge
                        names exists on the component its node
                        instantiates and lies on the right side of it;
                        that the graph without its back edges can be
                        ordered; that a guard has an eval to consult;
                        that a back edge does not feed a required
                        input; and that a node instantiating a
                        component with no evals is reported.
usage:                  |
                        Run as part of cctool check. A node with no
                        evals is reported as a note rather than a
                        fault.

...
"""


import collections

import cc_public.check.result


ID_CHECK        = 'workflow'
TITLE           = 'Workflows are graphs that can run'
NOUN            = 'workflow'

PREFIX_WORKFLOW = 'wf'
SEPARATOR       = '_'
DELIM           = '.'

KEY_ID_SELF     = 'id_self'
KEY_GUID_SELF   = 'guid_self'
KEY_NODE        = 'node'
KEY_EDGE        = 'edge'
KEY_EDGE_BACK   = 'edge_back'
KEY_TO          = 'to'
KEY_GUARD       = 'guard'
KEY_INPUT       = 'input'
KEY_OUTPUT      = 'output'
KEY_OPTIONAL    = 'optional'
KEY_RELATION    = 'relation'
KEY_ID_REL      = 'id_relation'
KEY_GUID_TARGET = 'guid_target'
KEY_ID_TYPE     = 'id_type'
KEY_SUBJECT     = 'subject'
KEY_INCL_TYPE   = 'include_type'

REL_INSTANTIATES = 'r_instantiates'
REL_JUDGED_BY    = 'r_is_judged_by'

SIDE_OUTPUT     = 'output'
SIDE_INPUT      = 'input'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every workflow that could not run as written.

    """

    map_by_guid = {d.get(KEY_GUID_SELF): d
                   for d in context.map_document.values()
                   if isinstance(d, dict) and KEY_GUID_SELF in d}

    count              = 0
    list_nonconformity = []
    list_note          = []

    for (filepath, document) in sorted(context.map_document.items()):

        if not _is_workflow(document):
            continue

        count += 1
        (list_bad, list_seen) = _inspect(filepath, document, map_by_guid)
        list_nonconformity.extend(list_bad)
        list_note.extend(list_seen)

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_nonconformity,
                                         list_note          = list_note)


# -----------------------------------------------------------------------------
def _is_workflow(document):
    """
    Return whether document is a dataflow workflow.

    """

    id_self = document.get(KEY_ID_SELF) if isinstance(document, dict) else None

    return isinstance(id_self, str) \
                and id_self.split(SEPARATOR, 1)[0] == PREFIX_WORKFLOW


# -----------------------------------------------------------------------------
def _inspect(filepath, document, map_by_guid):
    """
    Return (nonconformities, notes) for one workflow.

    """

    list_bad      = []
    list_note     = []
    map_component = {}                 # local node name -> component document

    for (name, node) in (document.get(KEY_NODE) or {}).items():

        component = _component_of(node, map_by_guid)

        if component is None:
            list_bad.append(_fault(filepath, f'node.{name}',
                    'Names no component, or names one this tree does not hold.'))
            continue

        map_component[name] = component
        list_bad.extend(_type_agreement(filepath, name, component, map_by_guid))

        if not _has_eval(component):
            list_note.append(cc_public.check.result.Note(
                    filepath = str(filepath),
                    message  = 'Node {name} instantiates {component}, which '
                               'carries no eval on any port and none on '
                               'itself. Nothing checks what it '
                               'produces.'.format(name = name,
                                                  component = component[KEY_ID_SELF])))

    for (key, is_back) in ((KEY_EDGE, False), (KEY_EDGE_BACK, True)):
        for (src, list_dst) in (document.get(key) or {}).items():
            list_bad.extend(_edges(filepath, key, src, list_dst, is_back,
                                   map_component))

    list_bad.extend(_orderable(filepath, document, map_component))

    return (list_bad, list_note)


# -----------------------------------------------------------------------------
def _edges(filepath, key, src, list_dst, is_back, map_component):
    """
    Return the faults in one source port's destinations.

    """

    list_bad = []
    port_src = _port(src, SIDE_OUTPUT, map_component)

    if port_src is None:
        list_bad.append(_fault(filepath, f'{key}.{src}',
                'Names an output port that does not exist on the component '
                'its node instantiates.'))
        return list_bad

    for (idx, dst) in enumerate(list_dst or []):

        where    = f'{key}.{src}.{idx}'
        port_dst = _port(dst.get(KEY_TO, ''), SIDE_INPUT, map_component)

        if port_dst is None:
            list_bad.append(_fault(filepath, where,
                    'Names an input port that does not exist on the component '
                    'its node instantiates.'))
            continue

        if KEY_GUARD in dst and not _judged(port_src):
            list_bad.append(_fault(filepath, where,
                    'Carries a guard, and its source port has no eval '
                    'anchored to it, so there is no verdict to consult.'))

        if is_back and not port_dst.get(KEY_OPTIONAL, False):
            list_bad.append(_fault(filepath, where,
                    'Feeds a required input from a back edge. The first '
                    'pass then has nothing there and cannot run.'))

    return list_bad


# -----------------------------------------------------------------------------
def _orderable(filepath, document, map_component):
    """
    Return a fault where the graph minus its back edges has a cycle.

    Kahn's ordering: a node is ready when every forward edge into it
    comes from a node already placed. Anything never placed lies on a
    cycle that no back edge declares.

    """

    map_in = collections.defaultdict(set)

    for (src, list_dst) in (document.get(KEY_EDGE) or {}).items():
        node_src = src.split(DELIM, 1)[0]
        for dst in list_dst or []:
            node_dst = dst.get(KEY_TO, '').split(DELIM, 1)[0]
            if node_src in map_component and node_dst in map_component:
                map_in[node_dst].add(node_src)

    placed = set()
    ready  = [n for n in map_component if not map_in[n]]

    while ready:
        node = ready.pop()
        placed.add(node)
        for (other, deps) in map_in.items():
            if other not in placed and deps <= placed and other not in ready:
                ready.append(other)

    left = sorted(set(map_component) - placed)

    if not left:
        return []

    return [_fault(filepath, KEY_EDGE,
                   'Cannot be ordered: {nodes} lie on a cycle that no back '
                   'edge declares.'.format(nodes = ', '.join(left)))]


# -----------------------------------------------------------------------------
def _type_agreement(filepath, name, component, map_by_guid):
    """
    Return a fault for each port whose eval cannot judge what it carries.

    A port names the type of item on it. An eval may name the types it
    applies to. Where both speak and disagree, the eval would be handed
    an item it has said it cannot answer for.

    """

    list_bad = []

    for side in (KEY_INPUT, KEY_OUTPUT):
        for (local, port) in (component.get(side) or {}).items():

            id_type = port.get(KEY_ID_TYPE) if isinstance(port, dict) else None

            for edge in (port.get(KEY_RELATION) or []) if isinstance(port, dict) else []:

                if edge.get(KEY_ID_REL) != REL_JUDGED_BY:
                    continue

                document_eval = map_by_guid.get(edge.get(KEY_GUID_TARGET)) or {}
                include       = (document_eval.get(KEY_SUBJECT) or {}) \
                                              .get(KEY_INCL_TYPE) or []

                if include and id_type not in include:
                    list_bad.append(_fault(filepath,
                            'node.{name}.{side}.{local}'.format(
                                    name = name, side = side, local = local),
                            'Carries {id_type}, and the eval anchored to it '
                            'names only {include}.'.format(
                                    id_type = id_type,
                                    include = ', '.join(include))))

    return list_bad


# -----------------------------------------------------------------------------
def _component_of(node, map_by_guid):
    """
    Return the component a node instantiates, or None.

    """

    for edge in node.get(KEY_RELATION) or []:
        if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_INSTANTIATES:
            return map_by_guid.get(edge.get(KEY_GUID_TARGET))

    return None


# -----------------------------------------------------------------------------
def _port(path, side, map_component):
    """
    Return the port a path names on the given side, or None.

    A path is node.side.name. The side in the path must be the side
    asked for: an edge leaves an output and arrives at an input.

    """

    part = path.split(DELIM)

    if len(part) != 3 or part[1] != side or part[0] not in map_component:
        return None

    return (map_component[part[0]].get(side) or {}).get(part[2])


# -----------------------------------------------------------------------------
def _judged(port):
    """
    Return whether an eval is anchored to this port.

    """

    return any(isinstance(e, dict) and e.get(KEY_ID_REL) == REL_JUDGED_BY
               for e in port.get(KEY_RELATION) or [])


# -----------------------------------------------------------------------------
def _has_eval(component):
    """
    Return whether any eval is anchored to the component or to any of its ports.

    """

    if _judged(component):
        return True

    for side in (KEY_INPUT, KEY_OUTPUT):
        for port in (component.get(side) or {}).values():
            if isinstance(port, dict) and _judged(port):
                return True

    return False


# -----------------------------------------------------------------------------
def _fault(filepath, path, message):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                message  = message,
                severity = cc_public.check.result.SEVERITY_CRITICAL)
