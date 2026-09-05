"""
---

id_self:                pym_cc_public.load.yaml
guid_self:              pym_8291ddb364c14a15942c07c03b38ac97
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  YAML loader
brief:                  |
                        Load YAML documents.
description:            |
                        The safe loader, so that tags naming arbitrary
                        python types are refused and duplicate mapping
                        keys are an error. A YAML stream announces its
                        encoding with a byte order mark and is UTF-8
                        where it carries none.
relation:               []

...
"""


import codecs
import typing

import ruamel.yaml


# What this loader raises for a defective document.
#
ERROR_LOAD = (ruamel.yaml.YAMLError,)


BOM_ENCODING     = ((codecs.BOM_UTF32_LE, 'utf-32'),
                    (codecs.BOM_UTF32_BE, 'utf-32'),
                    (codecs.BOM_UTF16_LE, 'utf-16'),
                    (codecs.BOM_UTF16_BE, 'utf-16'),
                    (codecs.BOM_UTF8,     'utf-8-sig'))
ENCODING_DEFAULT = 'utf-8'


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the YAML document in data as a python data structure.

    A YAML stream announces its encoding with a byte order mark, and
    is UTF-8 where it carries none, so a null encoding is resolved
    from the leading bytes rather than assumed.

    The safe loader is used, so tags naming arbitrary python types are
    refused rather than constructed. Duplicate mapping keys are an
    error -- a register keyed by identifier would otherwise lose an
    entry silently.

    """

    if encoding is None:
        encoding = _encoding_from_bom(data)

    return ruamel.yaml.YAML(typ = 'safe').load(data.decode(encoding))


# -----------------------------------------------------------------------------
def _encoding_from_bom(data: bytes) -> str:
    """
    Return the encoding named by the leading byte order mark.

    Falls back to UTF-8, which is what YAML specifies for a stream
    carrying no mark.

    """

    # YAML 1.2 section 5.2 -- a stream may announce its
    # encoding with a byte order mark, and is UTF-8 in
    # the absence of one. UTF-32 must be tested before
    # UTF-16, since the little endian UTF-32 mark begins
    # with the little endian UTF-16 mark.
    #
    # The utf-16 and utf-32 codecs read endianness from
    # the mark and strip it; utf-8-sig strips it. So the
    # encoding named here always consumes the mark rather
    # than leaving it in the decoded text.
    #
    for (bom, encoding) in BOM_ENCODING:
        if data.startswith(bom):
            return encoding

    return ENCODING_DEFAULT
