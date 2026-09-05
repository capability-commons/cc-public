"""
---

id_self:                pyp_cc_public.load
guid_self:              pyp_e9da464cc94247b491df4d838daecb98
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Load
brief:                  |
                        Load structured data.
description:            |
                        One submodule per format, each exposing the
                        same entry point, so that a loader is selected
                        by lookup. Adds the one source of bytes wanted
                        often enough to be worth naming: a file on
                        disk.
relation:               []

...
"""


import pathlib
import typing

from cc_public.load import json   as loader_json
from cc_public.load import jsonc  as loader_jsonc
from cc_public.load import python as loader_python
from cc_public.load import xml    as loader_xml
from cc_public.load import yaml   as loader_yaml


LOADER     = {'.yaml':  loader_yaml.from_bytes,
              '.yml':   loader_yaml.from_bytes,
              '.json':  loader_json.from_bytes,
              '.jsonc': loader_jsonc.from_bytes,
              '.xml':   loader_xml.from_bytes,
              '.py':    loader_python.from_bytes}

SUFFIX_ALL = tuple(LOADER)

# A null encoding lets each loader apply its own format convention --
# XML reads its declaration, JSON is UTF-8 by RFC 8259, YAML reads its
# byte order mark. Pass one only to override that.
#
ENCODING   = None

# Everything a loader may raise for a defective document, so that a
# caller can tell a bad file from a bug. Contributed by the loaders
# themselves, then deduplicated, since json and jsonc share a type.
#
ERROR_LOAD = tuple(dict.fromkeys(loader_yaml.ERROR_LOAD
                               + loader_json.ERROR_LOAD
                               + loader_jsonc.ERROR_LOAD
                               + loader_xml.ERROR_LOAD
                               + loader_python.ERROR_LOAD
                               + (loader_python.ErrorMetadataMissing,
                                  loader_python.ErrorEllipsisInProse)
                               + (UnicodeDecodeError, OSError)))


# -----------------------------------------------------------------------------
def from_file(filepath: pathlib.Path,
              encoding: str | None = ENCODING) -> typing.Any:
    """
    Return the content of filepath as a python data structure.

    The format is selected by suffix. The bytes are read here and
    handed to a format specific loader, so that the same loaders can be
    driven from any other source of bytes -- a network response, an
    archive member, a database column.

    Encoding is left null by default, so that each format applies its
    own convention for determining it.

    """

    suffix = filepath.suffix.lower()

    if suffix not in LOADER:
        raise ValueError('Unsupported suffix: {suffix}'.format(suffix = suffix))

    return LOADER[suffix](filepath.read_bytes(), encoding = encoding)
