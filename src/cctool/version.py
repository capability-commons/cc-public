"""
---

id_self:                pym_cctool.version
guid_self:              pym_6ebe53fe0a45405b9c138c86ed687b8f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Version
brief:                  |
                        The version of cc-public, which the package
                        build reads and the command line reports.
description:            |
                        The release step writes VERSION from the
                        computed bump, and hatchling reads it from
                        this file when the package is built, so
                        pyproject.toml declares the version dynamic
                        and a release needs no relock. The command
                        line reads it by importing this module, not
                        from the installed metadata, which an editable
                        install leaves at the version it was built
                        with.
edge:                   []

...
"""


VERSION                 = '0.1.0'
