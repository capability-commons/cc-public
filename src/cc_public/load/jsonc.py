"""
---

id_self:                pym_cc_public.load.jsonc
guid_self:              pym_d22f4d547ce7426aa6ae4eeccb1c9250
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  JSONC loader
brief:                  |
                        Load JSONC documents.
description:            |
                        JSON with comments, as understood by VS Code.
                        Both line and block comments are permitted, as
                        are trailing commas.

...
"""


import json
import typing

import jstyleson


# What this loader raises for a defective document. jstyleson strips
# comments and then defers to the standard library.
#
ERROR_LOAD = (json.JSONDecodeError,)


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the JSONC document in data as a python data structure.

    JSONC is JSON with comments, as understood by VS Code. Both line
    and block comments are permitted, as are trailing commas. For
    strict JSON, which permits neither, see cc_public.load.json.

    """

    if encoding is None:

        # RFC 8259 requires utf-8 and makes no allowance for
        # a byte order mark. Editors emit one anyway, so decode
        # with utf-8-sig, which consumes a mark where there
        # is one and is plain utf-8 where there is not.
        #
        encoding = 'utf-8-sig'

    return jstyleson.loads(data.decode(encoding))
