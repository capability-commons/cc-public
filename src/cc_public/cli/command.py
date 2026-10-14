"""
---

id_self:                pym_cc_public.cli.command
guid_self:              pym_1d79542b3a134e14a0bfa420fc543df6
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
                        else. The commands live with their kind, and
                        what the commands share lives in the group
                        module.
relation:               []

...
"""


import cc_public.cli.checking  # each registers its commands on the group
import cc_public.cli.editing
import cc_public.cli.gating
import cc_public.cli.group
import cc_public.cli.messaging
import cc_public.cli.querying


main = cc_public.cli.group.main


# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
