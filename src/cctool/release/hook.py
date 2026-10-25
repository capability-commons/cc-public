"""
---

id_self:                pym_cctool.release.hook
guid_self:              pym_d059742bb49f46a49af0cd5504d041f4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Build hook of the package
brief:                  |
                        Add the file of shadows to the wheel that
                        hatchling builds from the tree.
description:            |
                        pyproject.toml at
                        tool.hatch.build.targets.wheel.hooks.custom
                        names this module, so that hatchling runs it
                        when it builds a wheel. It writes the file of
                        shadows that pym_cctool.release.shadow makes
                        into a temporary folder, and has hatchling put
                        it into the _data of the package. An editable
                        install reads the tree itself, which holds
                        every item, so it gets no shadows. The module
                        imports hatchling, which only a build has, so
                        the wheel leaves it out.
edge:                   []

...
"""


import pathlib
import shutil
import sys
import tempfile

import hatchling.builders.hooks.plugin.interface


VERSION_EDITABLE  = 'editable'
KEY_FORCE_INCLUDE = 'force_include'
DIR_SOURCE        = 'src'


# -----------------------------------------------------------------------------
class ShadowHook(hatchling.builders.hooks.plugin.interface.BuildHookInterface):
    """
    A build hook of hatchling that adds the file of shadows to a wheel.

    """

    PLUGIN_NAME = 'custom'

    # -------------------------------------------------------------------------
    def initialize(self, version: str, build_data: dict) -> None:
        """
        Write the file of shadows of the tree, and have hatchling
        include it in the wheel, unless the build is editable.

        """

        if version == VERSION_EDITABLE:
            return

        root = pathlib.Path(self.root)
        sys.path.insert(0, str(root / DIR_SOURCE))
        import cctool.release.shadow

        self.dir_shadow = pathlib.Path(tempfile.mkdtemp())
        written         = cctool.release.shadow.write(root, self.dir_shadow)
        if written is not None:
            build_data[KEY_FORCE_INCLUDE][str(written[0])] = written[1]

    # -------------------------------------------------------------------------
    def finalize(self, _version: str, _build_data: dict, _artifact_path: str) -> None:
        """
        Remove the temporary folder of the file of shadows.

        """

        if getattr(self, 'dir_shadow', None) is not None:
            shutil.rmtree(self.dir_shadow, ignore_errors = True)
