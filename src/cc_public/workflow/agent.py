"""
---

id_self:                pym_cc_public.workflow.agent
guid_self:              pym_c6a34e7a24ca4245b7ca765b3bb5f5c5
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Agent nodes
brief:                  |
                        The brief a parked run leaves for its
                        performer, and how the outputs of an agent
                        node are read from the tree.
description:            |
                        A node performed by an agent parks the run.
                        The brief says what is bound on the node's
                        inputs, what each output asks for and how its
                        item will be found, and how to resume. On
                        resume the outputs are read from the graph,
                        never from the performer: an output revises an
                        input, or is found from an input by an edge of
                        a relation in a direction, keeping items of
                        the port's type and binding the first by
                        identifier. A port that finds nothing stops
                        the run, since the performer has not finished.
relation:               []

...
"""


import cc_public.facts
import cc_public.workflow


KEY_FOUND     = 'found'
KEY_PORT      = 'port'
KEY_RELATION  = 'relation'
KEY_DIRECTION = 'direction'
KEY_REVISES   = 'revises'
KEY_PROMPT    = 'prompt'
KEY_ID_TYPE   = 'id_type'
KEY_PREFIX    = 'prefix'
KEY_TITLE     = 'title'
KEY_TABLE     = 'table'
DIRECTION_OUT = 'out'
DIRECTION_IN  = 'in'
ID_REG_TYPE   = 'reg_type'


# -----------------------------------------------------------------------------
def brief(state, local, id_exe, map_id):
    """
    Return the brief for whoever performs the node: what is bound on
    its inputs, what each output asks for and how its item will be
    found, and how to resume the run.

    """

    tree  = state.tree
    lines = ['Execution {exe} of {wf} is waiting at node {node}.'.format(
                        exe = id_exe, wf = state.graph.id_self, node = local),
             '', 'Bound on its inputs:']

    for (port, id_item) in map_id.items():
        lines.append('  {port}: {id}  {title}'.format(
                        port = port, id = id_item, title = _title(tree, id_item)))

    lines.append('')
    lines.append('For each output, the task, and how its item is found once you are done:')

    for (port, spec) in state.graph.outputs(local).items():
        lines.append('  {port}: {task}'.format(port = port, task = _line(spec.get(KEY_PROMPT))))
        lines.append('    ' + _how(spec))

    lines.append('')
    lines.append('Work through cctool, commit, then run: cctool resume {exe}'.format(exe = id_exe))

    return '\n'.join(lines)


# -----------------------------------------------------------------------------
def outputs(state, local, map_id):
    """
    Return {port: id} for the node's outputs, read from the tree: the
    input an output revises, or what an edge from the input finds.
    Raise Stop where a port finds nothing, since the performer has not
    finished.

    """

    tree   = state.tree
    facts  = cc_public.facts.facts(tree.context.map_document)
    prefix = _prefix_of(tree)
    out    = {}

    for (port, spec) in state.graph.outputs(local).items():

        if spec.get(KEY_REVISES):
            out[port] = map_id[spec[KEY_REVISES]]
            continue

        found     = spec[KEY_FOUND]
        anchor    = tree.resolve(map_id[found[KEY_PORT]])
        list_guid = _guids_from(facts, anchor.guid_self, found[KEY_RELATION],
                                found[KEY_DIRECTION])
        list_id   = sorted(tree.resolve(guid).id_self for guid in list_guid
                           if guid in tree.map_id or guid in _guids(tree))
        list_id   = [i for i in list_id
                       if i.split('_', 1)[0] == prefix.get(spec.get(KEY_ID_TYPE))]

        if not list_id:
            raise cc_public.workflow.Stop(
                    '{node}.output.{port} finds nothing: no {type} {how} {anchor}. '
                    'The performer has not finished.'.format(
                            node = local, port = port, type = spec.get(KEY_ID_TYPE),
                            how = _how(spec), anchor = anchor.id_self))

        out[port] = list_id[0]

    return out


# -----------------------------------------------------------------------------
def _guids_from(facts, guid_anchor, id_relation, direction):
    """
    Return the guids at the far end of the anchor's edges of the
    relation, in the direction given.

    """

    if direction == DIRECTION_OUT:
        return [e.guid_target for e in facts.edge
                if e.guid_source == guid_anchor and e.id_relation == id_relation]

    return [e.guid_source for e in facts.edge
            if e.guid_target == guid_anchor and e.id_relation == id_relation]


# -----------------------------------------------------------------------------
def _guids(tree):
    """
    Return the guids the tree resolves.

    """

    return {item.guid_self for item in tree.map_id.values()}


# -----------------------------------------------------------------------------
def _prefix_of(tree):
    """
    Return {id_type: prefix} from the type register.

    """

    document = tree.context.map_document[tree.resolve(ID_REG_TYPE).location]

    return {id_type: entry.get(KEY_PREFIX)
            for (id_type, entry) in (document.get(KEY_TABLE) or {}).items()}


# -----------------------------------------------------------------------------
def _how(spec):
    """
    Return, as a phrase, how an output's item is found.

    """

    if spec.get(KEY_REVISES):
        return 'revises the item on {port}'.format(port = spec[KEY_REVISES])

    found = spec[KEY_FOUND]

    return ('found by {rel} {dir} the item on {port}'.format(
                rel  = found[KEY_RELATION],
                dir  = 'from' if found[KEY_DIRECTION] == DIRECTION_OUT else 'to',
                port = found[KEY_PORT]))


# -----------------------------------------------------------------------------
def _title(tree, id_item):
    """
    Return the item's title, or nothing.

    """

    item = tree.resolve(id_item)
    node = tree.context.map_document[item.location]

    for step in (item.path.split('.') if item.path else []):
        node = node[step]

    return str(node.get(KEY_TITLE) or '').strip()


# -----------------------------------------------------------------------------
def _line(text):
    """
    Return prose as one line.

    """

    return ' '.join(str(text or '').split())
