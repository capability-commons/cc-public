"""
---

id_self:                pym_cc_public.workflow.code
guid_self:              pym_f255418605674866868cca41062bdf16
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Components in code
brief:                  |
                        How the executor runs a component implemented
                        by a function rather than by prompts.
description:            |
                        Finds the function a component names by its
                        r_is_implemented_by edge, imports it by the
                        identifier of the module's own document, calls
                        it once for the node with the tree, the ledger
                        and the ids bound to its inputs, and takes an
                        id for each output port from what it returns.
                        A new item is noted on the ledger and settled
                        as one a prompt made. Anything the function
                        raises stops the run.
relation:               []

...
"""


import importlib

import cc_public.load
import cc_public.workflow
import cc_public.workflow.produce


KEY_RELATION    = 'relation'
KEY_ID_REL      = 'id_relation'
KEY_GUID_TGT    = 'guid_target'
KEY_ID_SELF     = 'id_self'
REL_IMPLEMENTED = 'r_is_implemented_by'
PREFIX_FUNCTION = 'pyf'
SEPARATOR       = '_'


# -----------------------------------------------------------------------------
def implementation(tree, component):
    """
    Return the source item a component names as its implementation, or
    None where it runs on prompts.

    """

    for edge in component.get(KEY_RELATION) or []:
        if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_IMPLEMENTED:
            return tree.resolve(edge[KEY_GUID_TGT])

    return None


# -----------------------------------------------------------------------------
def function_of(tree, item):
    """
    Return the function the source item names, imported.

    A component in code names a function at module level, whose module
    is named by the identifier of the file's own document, so that the
    function is found by import and never by a path.

    """

    if item.id_self.split(SEPARATOR, 1)[0] != PREFIX_FUNCTION \
            or len(item.location.anchor) != 1:
        raise cc_public.workflow.Stop(
                '{item} is not a function at module level, and a component in '
                'code names one.'.format(item = item.id_self))

    own         = tree.context.map_document[cc_public.load.Location(item.filepath)]
    name_module = own[KEY_ID_SELF].split(SEPARATOR, 1)[1]

    try:
        module = importlib.import_module(name_module)
    except ImportError as err:
        raise cc_public.workflow.Stop(
                '{item} lives in {module}, which cannot be imported: '
                '{err}'.format(item = item.id_self, module = name_module,
                               err = err)) from err

    return getattr(module, item.location.anchor[0])


# -----------------------------------------------------------------------------
def call(state, local, found, map_input):
    """
    Run the function implementing the node's component on the ids bound
    to its inputs, and return (what it produced by port, the ids of the
    items that exist now and did not before).

    The function takes the tree, the ledger and the inputs by port, and
    returns the id of an item for each output port. What it makes it
    makes through the edit tier; what it changes it notes on the ledger
    first. Anything it raises stops the run, which restores.

    """

    function = function_of(state.tree, found)
    before   = set(state.tree.map_id)

    try:
        result = function(state.tree, state.ledger, dict(map_input))
    except Exception as err:
        raise cc_public.workflow.Stop(
                '{node}: {fn} raised {kind}: {err}'.format(
                        node = local, fn = found.id_self,
                        kind = type(err).__name__, err = err)) from err

    if not isinstance(result, dict):
        raise cc_public.workflow.Stop(
                '{node}: {fn} returned {kind}, and a component in code returns '
                'the id of an item for each output port.'.format(
                        node = local, fn = found.id_self, kind = type(result).__name__))

    set_new = set(state.tree.map_id) - before

    for id_new in sorted(set_new):
        state.ledger.note_create(state.tree.resolve(id_new).filepath)

    return (result, set_new)


# -----------------------------------------------------------------------------
def output(state, local, port, spec, map_output, set_new):
    """
    Return the id the function produced for one output port, settled
    as a made item is where it is new: linked as the port says and
    marked proposed where its schema allows.

    """

    id_item = map_output.get(port)

    if not isinstance(id_item, str):
        raise cc_public.workflow.Stop(
                '{node}.output.{port}: the function produced nothing for '
                'it.'.format(node = local, port = port))

    if id_item not in state.tree.map_id:
        raise cc_public.workflow.Stop(
                '{node}.output.{port}: the function names {id}, which the tree '
                'does not hold.'.format(node = local, port = port, id = id_item))

    if id_item in set_new:
        cc_public.workflow.produce.settle(state, local, port, spec, id_item)

    return id_item
