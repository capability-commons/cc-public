"""
---

id_self:                pym_cc_public.cli.command
guid_self:              pym_87dddb59e2b44e55960145b2a832cb3d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Command definitions
brief:                  |
                        The commands the tool offers.
description:            |
                        This module is the entry point. It imports
                        each module of the package so that the
                        module's commands register on the group, and
                        it exposes the group as main. It holds nothing
                        else. The commands live with their kind, which
                        is checking, editing, judging, assurance,
                        committing or running, and what the commands
                        share lives in the group module.
relation:               []

...
"""


import cc_public.cli.assurance  # each registers its commands on the group
import cc_public.cli.checking
import cc_public.cli.committing
import cc_public.cli.editing
import cc_public.cli.group
import cc_public.cli.judging
import cc_public.cli.querying
import cc_public.cli.rendering
import cc_public.cli.running


main = cc_public.cli.group.main


# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
