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
                        Validate each YAML document in the tree
                        against the schemas it must conform to.
description:            |
                        A YAML document is an item held by no other.
                        Which schemas it must conform to is derived in
                        a logic program, as document_schema, and this
                        module validates it against each of them with
                        JSON Schema. The items inside a document
                        conform as part of it. Each violation is
                        reported with the line of the file it is found
                        at.

                        A schema is itself a YAML document, and
                        sch_schema holds it to the metaschema of JSON
                        Schema. No document is validated against a
                        schema that fails the metaschema, which could
                        not be used and is reported already. A $ref
                        that names no schema is reported once, against
                        the schema that holds it.
edge:                   []

...
"""


import functools
import json
import re
import typing
import urllib.parse

import jsonschema
import jsonschema.exceptions
import jsonschema.validators
import referencing
import referencing.exceptions

import cc_public.check.store
import cc_public.graph.extract


KEY_ID_SCHEMA     = '$id'
KEY_REF           = '$ref'
MARK_FRAGMENT     = '#'
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

# What is known of each schema read so far: whether it conforms to the
# metaschema, the $refs it holds, and its digest. It is keyed by the id
# of the schema, which is kept with it so that the id cannot be reused
# while it is held. A document is never changed once read, so what is
# known of it holds for as long as it is the same object. It is emptied
# when it holds COUNT_SCHEMA.
#
MAP_SCHEMA        = {}
COUNT_SCHEMA      = 4096

# The kind of verdict that the store of the checker keeps for schema
# validation.
#
KIND_STORE        = 'schema'
ESCAPE            = '\\'
CLASS_OPEN        = '['
CLASS_CLOSE       = ']'
END_ECMA          = '$'
END_PYTHON        = '\\Z'
TUPLE_ERROR_USE   = (jsonschema.exceptions.SchemaError,
                     jsonschema.exceptions.UnknownType,
                     referencing.exceptions.Unresolvable)


# -----------------------------------------------------------------------------
def ecma(pattern: str) -> str:
    """
    Return pattern, a regular expression of ECMA 262 as JSON Schema
    defines it, rewritten for python's re, so that each $ outside a
    character class matches only at the end of the text. In python, $
    also matches before a newline that ends the text, so ^[^\\n]+$
    would admit a title that ends in a newline.

    """

    list_part = []
    is_class  = False
    index     = 0

    while index < len(pattern):
        char = pattern[index]
        if char == ESCAPE:
            list_part.append(pattern[index:index + 2])
            index += 2
            continue
        if is_class:
            is_class = char != CLASS_CLOSE
        elif char == CLASS_OPEN:
            is_class = True
        elif char == END_ECMA:
            char = END_PYTHON
        list_part.append(char)
        index += 1

    return ''.join(list_part)


# -----------------------------------------------------------------------------
@functools.lru_cache(maxsize = 1024)
def _compiled(pattern: str) -> re.Pattern:
    """
    Return pattern, rewritten by ecma and compiled.

    """

    return re.compile(ecma(pattern))


# -----------------------------------------------------------------------------
def _pattern(validator, pattern, instance, _):
    """
    Yield an error if the string instance does not match pattern, read
    as ECMA 262 reads it.

    """

    if validator.is_type(instance, 'string') and not _compiled(pattern).search(instance):
        yield jsonschema.exceptions.ValidationError(
                  '{instance!r} does not match {pattern!r}'.format(instance = instance,
                                                                   pattern  = pattern))


# The validator of JSON Schema 2020-12, but with pattern read as JSON
# Schema reads it. A $ref is followed with the validator registered
# for the $schema of the schema it names, so this one is registered
# for 2020-12 in place of jsonschema's own.
#
Validator         = jsonschema.validators.validates(
                        jsonschema.Draft202012Validator.META_SCHEMA['$id'])(
                            jsonschema.validators.extend(jsonschema.Draft202012Validator,
                                                         {'pattern': _pattern}))


# -----------------------------------------------------------------------------
def violations(map_document: cc_public.graph.extract.Documents,
               facts:        cc_public.graph.extract.Facts,
               set_pair:     set[tuple[str, ...]],
               cache:        dict | None = None) -> list[tuple[str, ...]]:
    """
    Return a row for each violation of a schema by one of the YAML
    documents. set_pair holds the document_schema rows: each names a
    document and a schema it must conform to.

    cache, if given, keeps what each validation found, so that a later
    call with the same schemas reuses it for a YAML document that is the
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
                     if not is_valid(schema)}
    set_url_bad   = {str(map_schema[id_schema][KEY_ID_SCHEMA]) for id_schema in set_invalid}
    registry      = registry_of([schema for (id_schema, schema) in map_schema.items()
                                 if id_schema not in set_invalid])
    map_validator = {}
    set_row       = set()
    kept          = _Kept(cache, map_schema)

    for (id_document, id_schema) in sorted(set_pair):
        if id_document not in map_file or id_schema not in map_schema:
            continue
        if id_schema in set_invalid:
            continue
        file             = map_file[id_document]
        (document, base) = map_document[file]
        list_row         = kept.get(id_document, id_schema, file, document)
        if list_row is not None:
            set_row.update(list_row)
            continue
        if id_schema not in map_validator:
            map_validator[id_schema] = Validator(map_schema[id_schema], registry = registry)
        try:
            list_error = errors(map_validator[id_schema], document)
        except referencing.exceptions.Unresolvable as error:
            # A $ref to a schema that fails the metaschema is reported
            # already. One to a schema that does not exist is reported
            # here, once, against the schema that holds it.
            #
            if str(error.ref) not in set_url_bad:
                set_row.add(_unresolved(id_schema, map_file[id_schema], map_document, error))
            continue
        except TUPLE_ERROR_USE:
            continue
        list_row = [_row(id_document, id_schema, file, document, base, error)
                    for error in list_error]
        kept.put(id_document, id_schema, file, document, list_row)
        set_row.update(list_row)

    kept.save()

    return _once(set_row, kept)


# -----------------------------------------------------------------------------
def _once(set_row: set[tuple[str, ...]], kept: '_Kept') -> list[tuple[str, ...]]:
    """
    Return the rows with each violation reported once. A document that
    must conform to two schemas, one of which refers to the other, such
    as a register under sch_register and its own sch_reg_* schema, breaks
    both at the same place with the same message. The row of the schema
    that reaches more schemas, the more specific, is kept.

    """

    map_row = {}

    for row in sorted(set_row):
        key      = (row[0], *row[2:])
        kept_row = map_row.get(key)
        if kept_row is None or len(kept.reach(row[1])) > len(kept.reach(kept_row[1])):
            map_row[key] = row

    return sorted(map_row.values())


# -----------------------------------------------------------------------------
class _Kept:
    """
    What validations found before: those that cache keeps, made in this
    OS process, and those that the store of the checker keeps, made in an
    earlier run. What a document was found to violate under a schema is
    reused only while that schema, and each schema it refers to, is as
    it was, so a change to one schema validates again only the
    documents that depend on it.

    """

    # -------------------------------------------------------------------------
    def __init__(self, cache: dict | None, map_schema: dict[str, dict]):
        """
        Gather what validations with the schemas of map_schema found.

        """

        self.map_schema = map_schema
        self.map_url    = {str(schema[KEY_ID_SCHEMA]): id_schema
                           for (id_schema, schema) in map_schema.items()}
        self.map_found  = {} if cache is None else cache.setdefault('found', {})
        self.is_stored  = cc_public.check.store.directory() is not None
        self.map_stored = cc_public.check.store.load(KIND_STORE) if self.is_stored else {}
        self.map_used   = {}
        self.map_reach  = {}

    # -------------------------------------------------------------------------
    def get(self, id_document, id_schema, file, document) -> list | None:
        """
        Return the rows found for document, held in file, under the
        schema id_schema, or None if they were not kept.

        """

        found = self.map_found.get((id_document, id_schema))
        reach = self.reach(id_schema)
        key   = self._key(id_document, id_schema, file, document)

        if found is not None and found[0] is document and _same(found[1], reach):
            list_row = found[2]
        elif key in self.map_stored:
            list_row = [tuple(row) for row in self.map_stored[key]]
            self.map_found[(id_document, id_schema)] = (document, reach, list_row)
        else:
            return None

        if key:
            self.map_used[key] = [list(row) for row in list_row]
        return list_row

    # -------------------------------------------------------------------------
    def put(self, id_document, id_schema, file, document, list_row) -> None:
        """
        Keep list_row, the rows found for document, held in file, under
        the schema id_schema.

        """

        self.map_found[(id_document, id_schema)] = (document, self.reach(id_schema), list_row)
        key = self._key(id_document, id_schema, file, document)
        if key:
            self.map_used[key] = [list(row) for row in list_row]

    # -------------------------------------------------------------------------
    def save(self) -> None:
        """
        Write what was used to the store, in place of what it held, if
        there is a store and that has changed.

        """

        if self.is_stored and self.map_used != self.map_stored:
            cc_public.check.store.save(KIND_STORE, self.map_used)

    # -------------------------------------------------------------------------
    def reach(self, id_schema: str) -> tuple:
        """
        Return the schema id_schema and each schema it refers to, at
        any depth, as pairs of a name and the schema, in order of name.
        A $ref that names no schema of the tree is a pair of its url and
        None.

        """

        if id_schema not in self.map_reach:
            map_seen  = {}
            list_todo = [id_schema]
            while list_todo:
                name = list_todo.pop()
                if name in map_seen:
                    continue
                map_seen[name] = self.map_schema.get(name)
                schema = map_seen[name]
                if schema is not None:
                    base = str(schema[KEY_ID_SCHEMA])
                    for ref in _known(schema)[1]:
                        url = urllib.parse.urljoin(base, ref).partition(MARK_FRAGMENT)[0]
                        list_todo.append(self.map_url.get(url, url))
            self.map_reach[id_schema] = tuple(sorted(map_seen.items(),
                                                     key = lambda pair: pair[0]))

        return self.map_reach[id_schema]

    # -------------------------------------------------------------------------
    def _key(self, id_document, id_schema, file, document) -> str | None:
        """
        Return the key of the store for document, held in file, under
        the schema id_schema, or None if there is no store or the
        digest of the file is not known.

        """

        digest = cc_public.graph.extract.digest_of(document) if self.is_stored else None
        if digest is None:
            return None
        list_digest = ['{name}={digest}'.format(name   = name,
                                                digest = _known(schema)[2] if schema else '')
                       for (name, schema) in self.reach(id_schema)]
        return cc_public.check.store.key(id_document, id_schema, file, digest,
                                         cc_public.check.store.digest(' '.join(list_digest)))


# -----------------------------------------------------------------------------
def _same(reach: tuple, other: tuple) -> bool:
    """
    Return whether reach and other name the same schemas, each the same
    object.

    """

    return len(reach) == len(other) and all(
        name == name_other and schema is schema_other
        for ((name, schema), (name_other, schema_other)) in zip(reach, other, strict = True))


# -----------------------------------------------------------------------------
def is_valid(schema: dict) -> bool:
    """
    Return whether schema conforms to the metaschema of JSON Schema.

    """

    return _known(schema)[0]


# -----------------------------------------------------------------------------
def _known(schema: dict) -> tuple[bool, tuple[str, ...], str]:
    """
    Return what is known of schema: whether it conforms to the
    metaschema, the url of each $ref it holds, and its digest.

    """

    key = id(schema)
    if key not in MAP_SCHEMA or MAP_SCHEMA[key][0] is not schema:
        if len(MAP_SCHEMA) >= COUNT_SCHEMA:
            MAP_SCHEMA.clear()
        text            = json.dumps(schema, sort_keys = True, default = str)
        MAP_SCHEMA[key] = (schema,
                           (META.is_valid(schema),
                            tuple(sorted(set(_refs(schema)))),
                            cc_public.check.store.digest(text)))

    return MAP_SCHEMA[key][1]


# -----------------------------------------------------------------------------
def _refs(node: typing.Any) -> typing.Iterator[str]:
    """
    Yield the url of each $ref in node, at any depth.

    """

    if isinstance(node, dict):
        for (key, value) in node.items():
            if key == KEY_REF and isinstance(value, str):
                yield value
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _refs(value)


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
def _unresolved(id_schema, file, map_document, error):
    """
    Return the row that reports a $ref in the schema id_schema, held
    in file, that names no schema.

    """

    return (id_schema,
            id_schema,
            file,
            str(map_document[file][1]),
            KEY_REF,
            'The $ref {ref} names no schema, so nothing is validated against '
            '{id}.'.format(ref = error.ref, id = id_schema)[:LENGTH_MESSAGE])


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
            DELIM_PATH.join(str(part) for part in error.absolute_path) or DELIM_PATH,
            ' '.join(error.message.split())[:LENGTH_MESSAGE])


# -----------------------------------------------------------------------------
def errors(validator, document):
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
