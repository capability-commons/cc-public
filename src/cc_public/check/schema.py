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

                        A schema is itself a document, and sch_schema
                        holds it to the metaschema of JSON Schema. No
                        document is validated against a schema that
                        fails the metaschema, which could not be used
                        and is reported already.
relation:               []

...
"""


import jsonschema
import jsonschema.exceptions
import referencing
import referencing.exceptions

import cc_public.graph.extract


KEY_ID_SCHEMA     = '$id'
COLUMNS           = ('id', 'schema', 'file', 'line', 'path', 'message')
LENGTH_MESSAGE    = 200
DELIM_PATH        = '/'
KEY_UNEVALUATED   = 'unevaluatedProperties'

# A schema that fails the metaschema of JSON Schema cannot be used to
# validate, and using one, or one that refers to it, raises one of
# these errors.
#
META              = jsonschema.Draft202012Validator(
                        jsonschema.Draft202012Validator.META_SCHEMA)
TUPLE_ERROR_USE   = (jsonschema.exceptions.SchemaError,
                     jsonschema.exceptions.UnknownType,
                     referencing.exceptions.Unresolvable)


# -----------------------------------------------------------------------------
def violations(map_document: cc_public.graph.extract.Documents,
               facts:        cc_public.graph.extract.Facts,
               set_pair:     set[tuple[str, ...]],
               cache:        dict | None = None) -> list[tuple[str, ...]]:
    """
    Return a row for each violation of a schema by one of the
    documents. set_pair holds the document_schema rows: each names a
    document and a schema it must conform to.

    cache, if given, keeps what each validation found, so that a later
    call with the same schemas reuses it for a document that is the
    same object as before. An edit checks the tree before and after it
    with one cache, and so validates only the documents it changes.

    """

    map_file   = {row[0]: row[3] for row in facts['item'] if not row[2]}
    map_schema = {}

    for (id_document, file) in map_file.items():
        document = map_document[file][0]
        if isinstance(document, dict) and KEY_ID_SCHEMA in document:
            map_schema[id_document] = document

    set_invalid   = {id_schema for (id_schema, schema) in map_schema.items()
                     if not META.is_valid(schema)}
    registry      = registry_of([schema for (id_schema, schema) in map_schema.items()
                                 if id_schema not in set_invalid])
    map_validator = {}
    set_row       = set()
    map_found     = _cached(cache, map_schema)

    for (id_document, id_schema) in sorted(set_pair):
        if id_document not in map_file or id_schema not in map_schema:
            continue
        if id_schema in set_invalid:
            continue
        document = map_document[map_file[id_document]][0]
        found    = map_found.get((id_document, id_schema))
        if found is not None and found[0] is document:
            set_row.update(found[1])
            continue
        if id_schema not in map_validator:
            map_validator[id_schema] = jsonschema.Draft202012Validator(map_schema[id_schema],
                                                                       registry = registry)
        file             = map_file[id_document]
        (document, base) = map_document[file]
        try:
            list_error = _error(map_validator[id_schema], document)
        except TUPLE_ERROR_USE:
            continue
        list_row = [_row(id_document, id_schema, file, document, base, error)
                    for error in list_error]
        map_found[(id_document, id_schema)] = (document, list_row)
        set_row.update(list_row)

    return sorted(set_row)


# -----------------------------------------------------------------------------
def _cached(cache: dict | None, map_schema: dict[str, dict]) -> dict:
    """
    Return what the validations kept in cache found, keyed by document
    and schema, emptied first unless every schema is the same object as
    when they were made. With no cache, return a mapping to throw away.

    """

    if cache is None:
        return {}

    signature = sorted((id_schema, id(schema)) for (id_schema, schema) in map_schema.items())
    if cache.get('signature') != signature:
        cache['signature'] = signature
        cache['schema']    = list(map_schema.values())
        cache['found']     = {}

    return cache['found']


# -----------------------------------------------------------------------------
def registry_of(list_schema: list[dict]) -> referencing.Registry:
    """
    Return the registry that resolves a reference to each schema of
    list_schema by its $id.

    """

    return referencing.Registry().with_resources(
                (str(schema[KEY_ID_SCHEMA]), referencing.Resource.from_contents(schema))
                for schema in list_schema)


# -----------------------------------------------------------------------------
def _row(id_document, id_schema, file, document, base, error):
    """
    Return the row that reports error, found in document under the
    schema id_schema.

    """

    return (id_document,
            id_schema,
            file,
            str(_line(document, list(error.absolute_path), base)),
            DELIM_PATH.join(str(part) for part in error.absolute_path),
            ' '.join(error.message.split())[:LENGTH_MESSAGE])


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
