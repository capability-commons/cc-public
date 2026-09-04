"""
---

id_self:                pym_cc_public.check.schema
guid_self:              pym_dc70a7fa709c4eaaab6b18f0eadd5fb0
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Schema check
brief:                  |
                        Check that items conform to their schema.
description:            |
                        Resolves a schema for each item, from the item
                        own edge where it has one and otherwise from
                        its type, and validates against it. Cross
                        schema references resolve from a registry
                        built locally, so no reference is ever
                        retrieved over the network.

...
"""


import jsonschema
import referencing
import referencing.jsonschema

import cc_public.check.register
import cc_public.check.result
import cc_public.path


ID_CHECK      = 'schema'
TITLE         = 'Items conform to schema'
NOUN          = 'document'

# The relation whose object is the schema specifying the subject.
#
ID_REL_SCHEMA = 'r_is_specified_by_schema'

KEY_ID_SELF   = 'id_self'
KEY_ID_SCHEMA = '$id'
KEY_TABLE     = 'table'
KEY_PREFIX    = 'prefix'
KEY_RELATION  = 'relation'        # the array of edges
KEY_ID_REL    = 'id_relation'     # the edge's label
KEY_ID_TARGET = 'id_target'       # the edge's far end

SEPARATOR     = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every document that fails its schema.

    Documents that no schema could be selected for are reported as
    notes rather than passed over, so that coverage is visible rather
    than implied -- a check that examined nothing must not be mistaken
    for a check that passed.

    """

    map_document = context.map_document
    map_by_id    = map_schema(map_document)
    (_, document_type) = cc_public.check.register.find_type(map_document)
    map_prefix   = cc_public.check.register.map_prefix(document_type)
    registry     = _registry(map_by_id)

    count_valid        = 0
    list_note          = []
    list_nonconformity = []

    for (filepath, document) in sorted(map_document.items()):

        (id_schema, reason) = select_schema(document, map_prefix)

        if id_schema is None:
            list_note.append(cc_public.check.result.Note(
                                            filepath = str(filepath),
                                            message  = reason))
            continue

        if id_schema not in map_by_id:
            list_nonconformity.append(cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = '',
                        message  = 'Schema {id_schema} is named by the type '
                                   'register but no such schema was '
                                   'found.'.format(id_schema = id_schema)))
            continue

        list_error = _validate(document, map_by_id[id_schema], registry)

        if not list_error:
            count_valid += 1

        list_nonconformity.extend(
            cc_public.check.result.Nonconformity(filepath = str(filepath),
                                                 path     = path,
                                                 message  = message)
                for (path, message) in list_error)

    return cc_public.check.result.Result(
                            count_item         = count_valid,
                            list_nonconformity = list_nonconformity,
                            list_note          = list_note)


# -----------------------------------------------------------------------------
def _find_register_type(map_document):
    """
    Return the type register document.

    """

    for document in map_document.values():
        if _id_item(document) == ID_REG_TYPE:
            return document

    raise ErrorRegisterNotFound(
        'No data item with id_item {id_item} was found among the paths '
        'given, so no schema can be selected. Add the type register to '
        '--path, along with any schema it names.'.format(
                                                id_item = ID_REG_TYPE))


# -----------------------------------------------------------------------------
def map_schema(map_document):
    """
    Return an id_item to document map of every schema in the tree.

    A schema is identified by its $id -- the declaration that makes a
    document addressable as a schema -- rather than by its location or
    by its name.

    """

    return {_id_item(document): document
                for document in map_document.values()
                if  isinstance(document, dict)
                and KEY_ID_SCHEMA in document
                and _id_item(document) is not None}


# -----------------------------------------------------------------------------
def _registry(map_schema):
    """
    Return a referencing registry holding every schema, keyed by $id.

    Cross schema $ref is resolved from this registry, so no reference
    is ever retrieved over the network.

    """

    registry = referencing.Registry()

    for document in map_schema.values():
        resource = referencing.Resource.from_contents(
                        document,
                        default_specification = referencing.jsonschema.DRAFT202012)
        registry = registry.with_resource(uri      = document[KEY_ID_SCHEMA],
                                          resource = resource)

    return registry


# -----------------------------------------------------------------------------
def select_schema(document, map_prefix):
    """
    Return (id_schema, reason) for document. One or the other is None.

    An item may name its own schema, and that wins over the schema
    named by its type. Without this, every item of a type would be
    validated identically, and two registers sharing the reg prefix
    could not be told apart -- yet the type register and the relation
    register hold different kinds of entry and want different schemas.

    """

    id_schema = _id_schema(document)

    if id_schema is not None:
        return (id_schema, None)

    id_item = _id_item(document)

    if id_item is None:
        return (None, 'No id_self, so no type prefix to resolve.')

    if SEPARATOR not in id_item:
        return (None, 'id_self {id_item} carries no type '
                      'prefix.'.format(id_item = id_item))

    prefix = id_item.split(SEPARATOR, 1)[0]

    if prefix not in map_prefix:
        return (None, 'Prefix {prefix} is not in the type '
                      'register.'.format(prefix = prefix))

    id_schema = _id_schema(map_prefix[prefix])

    if id_schema is not None:
        return (id_schema, None)

    return (None, 'Type for prefix {prefix} names no schema.'.format(
                                                        prefix = prefix))


# -----------------------------------------------------------------------------
def _id_schema(mapping):
    """
    Return the id of the schema mapping names for itself, or None.

    Works the same whether mapping is a whole document or one entry in
    a register, since an edge is an edge wherever it is written.

    """

    if not isinstance(mapping, dict):
        return None

    for edge in mapping.get(KEY_RELATION) or []:

        if not isinstance(edge, dict):
            continue

        if edge.get(KEY_ID_REL) == ID_REL_SCHEMA:
            return edge.get(KEY_ID_TARGET)

    return None


# -----------------------------------------------------------------------------
def _validate(document, document_schema, registry):
    """
    Return a list of validation error messages, empty when valid.

    """

    validator = jsonschema.Draft202012Validator(document_schema,
                                                registry = registry)

    return [(_path(error), error.message)
                for error in sorted(validator.iter_errors(document),
                                    key = lambda error: list(error.path))]


# -----------------------------------------------------------------------------
def _path(error):
    """
    Return the location of a validation error as a slash separated path.

    """

    return cc_public.path.DELIM_PATH.join(
                            str(part) for part in error.path)


# -----------------------------------------------------------------------------
def _id_item(document):
    """
    Return the id_item of document, or None.

    """

    if isinstance(document, dict):
        return document.get(KEY_ID_SELF)

    return None
