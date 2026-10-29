"""
---

id_self:                pym_cctool.cli.group
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

edge:

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          icm_cctool_command_line.ok
    guid_target:        icm_6afb43665f5f4005ba5d45e2168ef344

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          icm_cctool_command_line.nonconformity
    guid_target:        icm_c5cee6fae5ac41878976d6113072557c

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          icm_cctool_command_line.error
    guid_target:        icm_b548d2385f9b4a62a587d93acbe7478f

...
"""


import click

import cctool.version


EXIT_OK            = 0
EXIT_NONCONFORMITY = 1
EXIT_ERROR         = 2


# -----------------------------------------------------------------------------
@click.group()
@click.version_option(version   = cctool.version.VERSION,
                      prog_name = 'cctool')
def main():
    """
    Capability Commons tooling.

    """
