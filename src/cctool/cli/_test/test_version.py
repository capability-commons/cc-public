"""
---

id_self:                pym_cctool.cli._test.test_version
guid_self:              pym_6ec5cdeac69d483eaaac7be1b234c929
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Version option tests
brief:                  |
                        Tests of the version option, as the command
                        line presents it.
description:            |
                        The version option reports the version module,
                        the same file the package build reads.
edge:                   []

...
"""


import click.testing

import cctool.cli.command
import cctool.version


# -----------------------------------------------------------------------------
def test_version_reports_the_version_module():
    result = click.testing.CliRunner().invoke(cctool.cli.command.main, ['--version'])
    assert result.exit_code == 0
    assert result.stdout == 'cctool, version {version}\n'.format(version = cctool.version.VERSION)
