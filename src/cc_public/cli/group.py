"""
---

id_self:                pym_cc_public.cli.group
guid_self:              pym_eb0491e5da6848ada5440cb417a91428
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Command group
brief:                  |
                        The group that every command is registered on,
                        and what the commands share.
description:            |
                        This module holds the group and the exit
                        statuses. A command module imports it and
                        registers its commands on main.
edge:                   []

...
"""


import click


EXIT_OK            = 0
EXIT_NONCONFORMITY = 1
EXIT_ERROR         = 2


# -----------------------------------------------------------------------------
@click.group()
def main():
    """
    Capability commons tooling.

    """
