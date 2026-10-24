"""
---

id_self:                pym_cctool.cli.command
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
edge:                   []

...
"""


import cctool.cli.auditing  # each registers its commands on the group
import cctool.cli.checking
import cctool.cli.editing
import cctool.cli.exporting
import cctool.cli.gating
import cctool.cli.group
import cctool.cli.messaging
import cctool.cli.querying
import cctool.cli.releasing
import cctool.cli.serving


main = cctool.cli.group.main


# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
