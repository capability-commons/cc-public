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
                        The entry point: imports each module of the
                        package so that its commands register on the
                        group, and exposes the group as main. Holds
                        nothing else; the commands live with their
                        kind, checking, editing, judging, assurance,
                        committing and running, and what they share
                        lives in group.
relation:               []

...
"""


import cc_public.cli.assurance     # noqa: F401 -- each registers its commands on the group
import cc_public.cli.checking      # noqa: F401
import cc_public.cli.committing    # noqa: F401
import cc_public.cli.editing       # noqa: F401
import cc_public.cli.group
import cc_public.cli.judging       # noqa: F401
import cc_public.cli.running       # noqa: F401


main = cc_public.cli.group.main


# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
