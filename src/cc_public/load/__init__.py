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
SUFFIX_PYTHON = '.py'

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


# Between a file and the run of definition names beneath it, in the
# form pytest uses to name a test in a file.
#
SEPARATOR_ANCHOR = '::'


# -----------------------------------------------------------------------------
class Location:
    """
    Where a document sits: a file, and, for a document held in a
    docstring beneath the file's own, the run of definition names down
    to it.

    Two locations are the same where their file and anchor are. kind
    says what the docstring belongs to, module, class or function, and
    is carried rather than compared, since the file and anchor fix it.

    """

    __slots__ = ('filepath', 'anchor', 'kind')

    def __init__(self, filepath, anchor = (), kind = None):
        self.filepath = pathlib.Path(filepath)
        self.anchor   = tuple(anchor)
        self.kind     = kind

    def __eq__(self, other):
        return isinstance(other, Location) \
               and (self.filepath, self.anchor) == (other.filepath, other.anchor)

    def __hash__(self):
        return hash((self.filepath, self.anchor))

    def __lt__(self, other):
        return (self.filepath, self.anchor) < (other.filepath, other.anchor)

    def __str__(self):
        return str(self.filepath) + ''.join(SEPARATOR_ANCHOR + name
                                            for name in self.anchor)

    def __repr__(self):
        return 'Location({loc!r})'.format(loc = str(self))

    @property
    def is_own(self):
        """
        Whether this is the file's own document rather than one beneath it.

        """

        return not self.anchor


# -----------------------------------------------------------------------------
def iter_document(filepath: pathlib.Path,
                  encoding: str | None = ENCODING):
    """
    Yield (Location, document) for every document filepath holds.

    A file of data holds one, at the file itself. A python file holds
    one in its module docstring and one in the docstring of each class
    and function that carries a document; each is an item in its own
    right, at its own location.

    """

    suffix = filepath.suffix.lower()

    if suffix not in LOADER:
        raise ValueError('Unsupported suffix: {suffix}'.format(suffix = suffix))

    data = filepath.read_bytes()

    if suffix == SUFFIX_PYTHON:
        for (kind, anchor, document) in loader_python.iter_document(data, encoding):
            yield (Location(filepath, anchor, kind), document)
    else:
        yield (Location(filepath), LOADER[suffix](data, encoding = encoding))


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
