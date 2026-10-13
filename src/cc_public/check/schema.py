"""
---

id_self:                pym_cc_public.check.schema
guid_self:              pym_76db8b74c2754ed5a0393bcbd7d295dd
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Schema validation
brief:                  |
                        Validate each document in the tree against the
                        schemas it must conform to.
description:            |
                        A document is an item held by no other. Which
                        schemas it must conform to is derived in
                        Datalog, as document_schema, and this module
                        validates it against each of them with JSON
                        Schema. The items inside a document conform as
                        part of it. Each violation is reported with
                        the line of the file it is found at.
relation:               []

...
"""


import jsonschema
import referencing

import cc_public.graph.extract


KEY_ID_SCHEMA     = '$id'
LENGTH_MESSAGE    = 200
DELIM_PATH        = '/'
KEY_UNEVALUATED   = 'unevaluatedProperties'


# -----------------------------------------------------------------------------
def violations(map_document: cc_public.graph.extract.Documents,
               facts:        cc_public.graph.extract.Facts,
               set_pair:     set[tuple[str, ...]]) -> list[tuple[str, ...]]:
    """
    Return a row for each violation of a schema by one of the
    documents. set_pair holds the document_schema rows: each names a
    document and a schema it must conform to.

    """

    map_file   = {row[0]: row[3] for row in facts['item'] if not row[2]}
    map_schema = {}

    for (id_document, file) in map_file.items():
        document = map_document[file][0]
        if isinstance(document, dict) and KEY_ID_SCHEMA in document:
            map_schema[id_document] = document

    registry = referencing.Registry().with_resources(
                    (str(schema[KEY_ID_SCHEMA]), referencing.Resource.from_contents(schema))
                    for schema in map_schema.values())
    map_validator = {}
    set_row       = set()

    for (id_document, id_schema) in sorted(set_pair):
        if id_document not in map_file or id_schema not in map_schema:
            continue
        if id_schema not in map_validator:
            map_validator[id_schema] = jsonschema.Draft202012Validator(map_schema[id_schema],
                                                                       registry = registry)
        file             = map_file[id_document]
        (document, base) = map_document[file]
        for error in _error(map_validator[id_schema], document):
            set_row.add((id_document,
                         id_schema,
                         file,
                         str(_line(document, list(error.absolute_path), base)),
                         DELIM_PATH.join(str(part) for part in error.absolute_path),
                         ' '.join(error.message.split())[:LENGTH_MESSAGE]))

    return sorted(set_row)


# -----------------------------------------------------------------------------
def _error(validator, document):
    """
    Return the errors of document under validator.

    A field that fails a subschema counts as unevaluated, so any other
    error also raises an unevaluatedProperties error for the fields
    around it. Such errors are left out while any other remains: once
    the others are fixed, a field that no schema allows is reported.

    """

    list_error = list(validator.iter_errors(document))
    list_other = [error for error in list_error if error.validator != KEY_UNEVALUATED]

    return list_other or list_error


# -----------------------------------------------------------------------------
def _line(document, list_part, base):
    """
    Return the line of the file that the field at list_part is on, or
    the line of the nearest field above it that the loader recorded.

    """

    line = base
    node = document

    for part in list_part:
        lc = getattr(node, 'lc', None)
        try:
            if lc is not None:
                line = base + (lc.key(part) if isinstance(node, dict) else lc.item(part))[0]
            node = node[part]
        except (KeyError, IndexError, TypeError):
            break

    return line
