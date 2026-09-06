"""
---

id_self:                pym_cc_public.workflow.component
guid_self:              pym_4fcb8b39bcdc4048a9a6402410525085
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  The tool's own components
brief:                  |
                        Functions that implement components of the
                        tool's own workflows.
description:            |
                        Each function here is named by a component
                        through r_is_implemented_by and follows the
                        contract of a component in code: it takes the
                        tree, the ledger and the inputs by port,
                        returns the id of an item for each output
                        port, and notes on the ledger what it changes
                        before changing it. The first accepts a
                        requirement.
relation:               []

...
"""


import cc_public.edit.accept


PORT_REQUIREMENT = 'requirement'
PORT_ACCEPTED    = 'accepted'


# -----------------------------------------------------------------------------
def accept(tree, ledger, map_input):
    """
    ---

    id_self:                pyf_cc_public.workflow.component.accept
    guid_self:              pyf_074e3769a2d640ed9f73ec7e241169de
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Accept a requirement
    brief:                  |
                            Accept the requirement bound to the
                            requirement input, where its assurance is
                            complete, and return it on the requirement
                            output.

                            The contract of a component in code: the tree,
                            the ledger and the inputs by port come in; the
                            id of an item for each output port goes out;
                            what is changed is noted on the ledger first,
                            so that a stop puts it back; and a refusal is
                            raised, which stops the run.
    description:            |
                            The first component in code. Notes the
                            requirement's file on the ledger, accepts it
                            through the edit tier's accept, which refuses
                            where the assurance is incomplete, and returns
                            the same id on the accepted output.
    relation:               []

    ...
    """

    id_requirement = map_input[PORT_REQUIREMENT]

    ledger.note_modify(tree.resolve(id_requirement).filepath)
    cc_public.edit.accept.accept(tree, id_requirement)

    return {PORT_ACCEPTED: id_requirement}
