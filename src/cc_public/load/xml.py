"""
---

id_self:                pym_cc_public.load.xml
guid_self:              pym_121cd4e627c145d285792c8d5a2bf4cb
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  XML loader
brief:                  |
                        Load XML documents.
description:            |
                        Parsed twice: once as a security gate refusing
                        document type definitions and entity
                        declarations, and once to convert. An XML
                        document declares its own encoding, so an
                        encoding supplied by a caller is refused
                        rather than ignored. Mixed content has no
                        faithful representation as a mapping and is
                        refused.
relation:               []

...
"""


import typing
import xml.etree.ElementTree

import defusedxml
import defusedxml.ElementTree
import xmltodict


# xmltodict conventions -- attributes are prefixed, character data keyed.
#
PREFIX_ATTR = '@'
KEY_TEXT    = '#text'


# -----------------------------------------------------------------------------
class ErrorNotTreeShaped(Exception):
    """
    Raised for an XML document that is not shaped like a tree of maps.

    Only a subset of valid XML has a faithful dictionary
    representation. The case excluded here is mixed content -- an
    element holding both character data and child elements -- because
    the position of the text relative to the children cannot be
    recorded in a mapping, and is silently discarded by any XML to
    dictionary conversion.

    """



# -----------------------------------------------------------------------------
class ErrorEncodingNotSupported(Exception):
    """
    Raised when a non-null encoding arg is passed to load.xml.from_bytes

    Unlike JSON, JSONC and YAML, XML file encodings are
    required to be specified in the file, so any non null
    encoding parameter cannot be acted upon.

    """




# What this loader raises for a defective document. Deliberately
# excludes ErrorEncodingNotSupported, which reports a caller passing
# an argument that cannot be honoured rather than a bad document.
#
ERROR_LOAD = (xml.etree.ElementTree.ParseError,
              defusedxml.DefusedXmlException,
              ErrorNotTreeShaped)


# -----------------------------------------------------------------------------
def from_bytes(data: bytes, encoding: str | None = None) -> typing.Any:
    """
    Return the XML document in data as a python data structure.

    An XML document declares its own encoding, so encoding is accepted
    only to keep the loader interface uniform and is deliberately not
    used -- passing it to the parser would override the declaration
    rather than defer to it, which is the opposite of what a caller
    supplying a default would mean by it.

    The document is parsed twice. The first pass is a security gate --
    defusedxml is asked to refuse document type definitions and entity
    declarations outright. Note that forbid_dtd defaults to False; it
    is set here deliberately, on the grounds that a data item has no
    business carrying a DTD. The second pass performs the conversion.
    The cost of the extra pass is negligible beside the cost of
    getting this wrong.

    """

    if encoding is not None:
        raise ErrorEncodingNotSupported(
            'An encoding of {encoding!r} was supplied, but an XML document '
            'declares its own encoding and that declaration is the only '
            'authority on it. Pass encoding = None so that the declaration '
            'is honoured.'.format(encoding = encoding))

    defusedxml.ElementTree.fromstring(data,
                                      forbid_dtd      = True,
                                      forbid_entities = True,
                                      forbid_external = True)

    struct = xmltodict.parse(data)

    path_mixed = _find_mixed_content(struct)

    if path_mixed is not None:
        raise ErrorNotTreeShaped(
            'Mixed content at {path} -- this element holds both character '
            'data and child elements, so it has no faithful dictionary '
            'representation.'.format(path = path_mixed))

    return struct


# -----------------------------------------------------------------------------
def _find_mixed_content(data: typing.Any,
                        path: str = '') -> str | None:
    """
    Return the path of the first mixed content element, or None.

    An element is mixed content when it carries character data
    alongside one or more child elements. Attribute keys do not count,
    since an element may legitimately have both attributes and text.

    """

    if isinstance(data, dict):

        list_key_child = [key for key in data
                              if      key != KEY_TEXT
                              and not key.startswith(PREFIX_ATTR)]

        if KEY_TEXT in data and list_key_child:
            return path or '/'

        for (key, value) in data.items():
            path_mixed = _find_mixed_content(value, '{path}/{key}'.format(
                                                    path = path, key = key))
            if path_mixed is not None:
                return path_mixed

    elif isinstance(data, list):

        for (idx, value) in enumerate(data):
            path_mixed = _find_mixed_content(value, '{path}[{idx}]'.format(
                                                    path = path, idx = idx))
            if path_mixed is not None:
                return path_mixed

    return None
