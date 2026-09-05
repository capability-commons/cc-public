"""
---

id_self:                pym_cc_public.load.json
guid_self:              pym_d43f7598db784c5ba9e564cf1ed5ecce
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  JSON loader
brief:                  |
                        Load JSON documents.
description:            |
                        Strict JSON, in which neither comments nor
                        trailing commas are legal. UTF-8 as RFC 8259
                        requires, tolerating a byte order mark that
                        the specification does not allow for but
                        editors emit anyway.

...
"""


import json
import typing


# What this loader raises for a defective document.
#
ERROR_LOAD = (json.JSONDecodeError,)


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the JSON document in data as a python data structure.

    Strict JSON. Neither comments nor trailing commas are legal here --
    for the dialect that permits both, see cc_public.load.jsonc.

    """

    if encoding is None:

        # RFC 8259 requires utf-8 and makes no allowance for
        # a byte order mark. Editors emit one anyway, so decode
        # with utf-8-sig, which consumes a mark where there
        # is one and is plain utf-8 where there is not.
        #
        encoding = 'utf-8-sig'

    return json.loads(data.decode(encoding))
