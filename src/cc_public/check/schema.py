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
                        This check selects a schema for each item,
                        either the schema the item names or the schema
                        its type names, and validates the item against
                        it. A pattern constrains a datum, and a datum
                        holds no line break. The draft reads a regular
                        expression by ECMA-262, where a dollar sign
                        anchors the end of the string, while Python
                        also matches before a final newline. The check
                        therefore refuses the line break itself. An
                        item held within another item is validated
                        against the schema its type names, for that
                        one rule, which the pass over the container
                        does not state. Facts that span documents,
                        which a schema cannot express, are left to
                        their own checks.
relation:               []

...
"""


import re

import jsonschema
import jsonschema.validators
import referencing
import referencing.jsonschema

import cc_public.check.register
import cc_public.item
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

KEYWORD_UNEVALUATED = 'unevaluatedProperties'
KEYWORD_PATTERN     = 'pattern'
MESSAGE_DATUM       = 'is constrained by a pattern, so it holds a datum'

# The properties an unevaluated properties error names, which the
# message holds and the error object does not.
#
PATTERN_QUOTED      = r"'([^']+)'"
KEYWORD_PROPERTIES  = 'properties'
KEYWORD_ALL_OF      = 'allOf'
KEYWORD_REF         = '$ref'
KEYWORD_REQUIRED    = 'required'
KEYWORD_DESCRIPTION = 'description'
KEYWORD_DEFS        = '$defs'
PREFIX_SCHEMA       = 'sch'
WORD_OPTIONAL       = 'optional'
FRAGMENT            = '#'
SUFFIX_SCHEMA       = '.yaml'


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
    reg          = registry(map_by_id)

    count_valid        = 0
    list_note          = []
    list_nonconformity = []

    for (filepath, document) in sorted(map_document.items()):

        list_nonconformity.extend(_restated(filepath, document))

        # An item naming two schemas would be validated against one of
        # them, chosen by the order of its edges; naming two is a fault.
        #
        list_named = _list_id_schema(document)

        if len(list_named) > 1:
            list_nonconformity.append(cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = KEY_RELATION,
                        message  = 'Names {n} schemas, {names}. An item names one '
                                   'schema, or none and takes its type\'s.'.format(
                                        n = len(list_named), names = ', '.join(list_named))))
            continue

        (id_schema, reason) = select_schema(document, map_prefix)

        if id_schema is None:
            list_note.append(cc_public.check.result.Note(
                                            filepath = str(filepath),
                                            message  = reason))
            continue

        # An item naming its own schema narrows the contract its type
        # makes; it cannot swap it for another. The one named must be
        # the type's, or compose it.
        #
        id_typed = _id_schema_of_type(document, map_prefix)

        if id_typed is not None and id_schema != id_typed \
                and not _composes(id_schema, id_typed, map_by_id):
            list_nonconformity.append(cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = KEY_RELATION,
                        message  = 'Names {own} as its schema, which does not '
                                   'compose {typed}, the schema its type names. '
                                   'An item may narrow its type\'s contract and '
                                   'not replace it.'.format(own   = id_schema,
                                                            typed = id_typed)))
            continue

        if id_schema not in map_by_id:
            list_nonconformity.append(cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = '',
                        message  = 'Schema {id_schema} is named by the type '
                                   'register but no such schema was '
                                   'found.'.format(id_schema = id_schema)))
            continue

        list_error = validate(document, id_schema, map_by_id, reg)

        if not list_error:
            count_valid += 1

        list_nonconformity.extend(
            cc_public.check.result.Nonconformity(filepath = str(filepath),
                                                 path     = path,
                                                 message  = message)
                for (path, message) in list_error)

        list_nonconformity.extend(_datum(filepath, document, map_prefix, map_by_id, reg))

    return cc_public.check.result.Result(
                            count_item         = count_valid,
                            list_nonconformity = list_nonconformity,
                            list_note          = list_note)


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
def registry(map_schema):
    """
    Return a referencing registry holding every schema, keyed by $id.

    Cross schema $ref is resolved from this registry, so no reference
    is ever retrieved over the network. A caller validating many
    documents builds one and hands it to validate; a caller validating
    one lets validate build it.

    """

    registry = referencing.Registry()

    for document in map_schema.values():
        resource = referencing.Resource.from_contents(
                        document,
                        default_specification = referencing.jsonschema.DRAFT202012)
        registry = registry.with_resource(uri      = document[KEY_ID_SCHEMA],
                                          resource = resource)

    return registry.crawl()


# -----------------------------------------------------------------------------
def select_schema(document, map_prefix, is_embedded = False):
    """
    Return (id_schema, reason) for document. One or the other is None.

    A document may name its own schema, and that wins over the schema
    named by its type. Without this, every item of a type would be
    validated identically, and two registers sharing the reg prefix
    could not be told apart -- yet the type register and the relation
    register hold different kinds of entry and want different schemas.

    is_embedded says the item is held within another. Its own edge is
    then passed over, because on an entry of the type register that
    edge names the schema of the items the entry describes and not the
    schema of the entry. An embedded item takes the schema its type
    names, always.

    """

    id_schema = None if is_embedded else _id_schema(document)

    if id_schema is not None:
        return (id_schema, None)

    id_item = _id_item(document)

    if id_item is None:
        return (None, 'No id_self, so no type prefix to resolve.')

    if SEPARATOR not in id_item:
        return (None, 'id_self {id_item} carries no type '
                      'prefix.'.format(id_item = id_item))

    prefix = cc_public.item.prefix_of(id_item)

    if prefix not in map_prefix:
        return (None, 'Prefix {prefix} is not in the type '
                      'register.'.format(prefix = prefix))

    id_schema = _id_schema(map_prefix[prefix])

    if id_schema is not None:
        return (id_schema, None)

    return (None, 'Type for prefix {prefix} names no schema.'.format(
                                                        prefix = prefix))


# -----------------------------------------------------------------------------
def _id_schema_of_type(document, map_prefix):
    """
    Return the id of the schema the document's type names, or None.

    """

    id_item = _id_item(document)

    if id_item is None or SEPARATOR not in id_item:
        return None

    entry = map_prefix.get(cc_public.item.prefix_of(id_item))

    return _id_schema(entry) if entry is not None else None


# -----------------------------------------------------------------------------
def _composes(id_schema, id_wanted, map_by_id, seen = None):
    """
    Return whether the schema id_schema names, or any it composes by
    allOf, transitively, is id_wanted.

    """

    seen = seen if seen is not None else set()

    if id_schema == id_wanted:
        return True

    if id_schema in seen or id_schema not in map_by_id:
        return False

    seen.add(id_schema)

    for branch in map_by_id[id_schema].get('allOf') or []:
        ref = branch.get('$ref') if isinstance(branch, dict) else None
        if isinstance(ref, str):
            name = ref.rsplit('/', 1)[-1].split('.yaml', 1)[0]
            if _composes(name, id_wanted, map_by_id, seen):
                return True

    return False


# -----------------------------------------------------------------------------
def _id_schema(mapping):
    """
    Return the id of the schema mapping names for itself, or None.

    Works the same whether mapping is a whole document or one entry in
    a register, since an edge is an edge wherever it is written.

    """

    list_named = _list_id_schema(mapping)

    return list_named[0] if list_named else None


# -----------------------------------------------------------------------------
def _list_id_schema(mapping):
    """
    Return the ids of every schema mapping names for itself.

    """

    if not isinstance(mapping, dict):
        return []

    return [edge.get(KEY_ID_TARGET) for edge in mapping.get(KEY_RELATION) or []
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == ID_REL_SCHEMA]


# -----------------------------------------------------------------------------
def _datum(filepath, document, map_prefix, map_schema, reg):
    """
    Return a Nonconformity for every item held within document whose
    datum is written as a block scalar.

    The rule reaches an item at a location through its own schema, and
    an item held within one only here: the extension that carries the
    rule is lost where the container follows a reference into the entry
    schema, so the container pass never states it of an entry. Only
    that one message is kept, so nothing the container already reports
    is reported twice.

    """

    out = []

    for held in cc_public.item.iter_item(document):
        (path, item) = (held.path, held.document)
        if not path:
            continue

        (id_schema, _) = select_schema(item, map_prefix, is_embedded = True)

        if id_schema is None or id_schema not in map_schema:
            continue

        out.extend(cc_public.check.result.Nonconformity(
                            filepath = str(filepath),
                            path     = cc_public.path.join(path, path_error),
                            message  = message)
                   for (path_error, message) in validate(item, id_schema, map_schema, reg)
                   if MESSAGE_DATUM in message)

    return out


# -----------------------------------------------------------------------------
def _pattern(validator, value, instance, schema):
    """
    Apply pattern as the draft defines it, and refuse a line break.

    A pattern constrains a datum, and a datum holds no line break
    (ddr_layout_convention). The check is needed because the draft
    reads a regular expression by ECMA-262, where $ matches at the end
    of the string, while Python matches it before a final newline as
    well. A value written as a block scalar carries that newline, so a
    pattern anchored with $ accepts it and says nothing.

    """

    yield from KEYWORD_PATTERN_DRAFT(validator, value, instance, schema)

    if isinstance(instance, str) and '\n' in instance:
        yield jsonschema.ValidationError(
                '{value!r} {message}, and a datum holds no line break. It is written as '
                'a block scalar, and the line break is part of the value.'.format(
                                        value = instance, message = MESSAGE_DATUM))


KEYWORD_PATTERN_DRAFT = jsonschema.Draft202012Validator.VALIDATORS[KEYWORD_PATTERN]

Validator             = jsonschema.validators.extend(
                                jsonschema.Draft202012Validator,
                                {KEYWORD_PATTERN: _pattern})


# -----------------------------------------------------------------------------
def validate(document, id_schema, map_schema, reg = None):
    """
    Return [(path, message)] for every way document fails the schema
    id_schema names, empty when it conforms.

    map_schema holds every schema by id, as map_schema returns it. The
    registry is built here where the caller has none.

    """

    validator = Validator(map_schema[id_schema],
                                                registry = reg if reg is not None
                                                           else registry(map_schema))
    list_error = sorted(validator.iter_errors(document),
                        key = lambda error: list(error.path))

    # A subschema that failed yields no annotations, so unevaluated
    # properties at that path names the fields that branch would have
    # evaluated. That error is the child's, reported once, where it is,
    # and is dropped here only where every field it names is declared
    # somewhere in the composition (ddr_schema_closure).
    #
    list_path = [list(error.path) for error in list_error]
    declared  = _declared(map_schema[id_schema], map_schema)

    held = [(_path(error), error.message)
                for (error, path) in zip(list_error, list_path, strict = True)
                if not (error.validator == KEYWORD_UNEVALUATED
                        and _names_only_declared(error, declared)
                        and any(len(other) > len(path) and other[:len(path)] == path
                                for other in list_path))]

    # One fault, said once. An entry is validated against the envelope
    # by three schemas that compose it (ddr_schema_closure).
    #
    return list(dict.fromkeys(held))


# -----------------------------------------------------------------------------
def _restated(filepath, document):
    """
    Return a finding for each way a schema says twice what it says
    once, and the two disagree.

    A description opening Optional on a property the schema requires,
    and a definition that is a bare reference to another item schema,
    which gives one shape two names (ddr_restated_fact).

    """

    if not isinstance(document, dict) \
            or cc_public.item.prefix_of(document.get(KEY_ID_SELF)) != PREFIX_SCHEMA:
        return []

    return list(_says_optional(filepath, document)) \
         + list(_is_an_alias(filepath, document))


# -----------------------------------------------------------------------------
def _says_optional(filepath, node, path = ''):
    """
    Yield a finding for each required property whose description opens
    by calling it optional.

    """

    if isinstance(node, list):
        for (index, one) in enumerate(node):
            yield from _says_optional(filepath, one, cc_public.path.join(path, index))
        return

    if not isinstance(node, dict):
        return

    required = set(node.get(KEYWORD_REQUIRED) or ())

    for (name, one) in (node.get(KEYWORD_PROPERTIES) or {}).items():
        said = str((one or {}).get(KEYWORD_DESCRIPTION) or '').strip().lower() \
               if isinstance(one, dict) else ''
        if name in required and said.startswith(WORD_OPTIONAL):
            yield cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = cc_public.path.join(
                                        cc_public.path.join(path, KEYWORD_PROPERTIES),
                                        name),
                        message  = 'Required, and its description calls it optional. A '
                                   'schema is what travels to a partner, so it says '
                                   'one thing about a field or the reader believes '
                                   'the wrong one.')

    for (key, one) in node.items():
        yield from _says_optional(filepath, one, cc_public.path.join(path, key))


# -----------------------------------------------------------------------------
def _is_an_alias(filepath, document):
    """
    Yield a finding for each definition that is a bare reference to
    another item schema.

    A bare reference to a primitive is not one: it names a role for a
    type. One to a whole schema gives that schema a second name, and
    the next schema copied from a neighbour carries whichever it
    copied.

    """

    for (name, node) in (document.get(KEYWORD_DEFS) or {}).items():

        uri = node.get(KEYWORD_REF) if isinstance(node, dict) else None

        if not isinstance(uri, str) or len(node) != 1 or FRAGMENT in uri:
            continue

        yield cc_public.check.result.Nonconformity(
                    filepath = str(filepath),
                    path     = cc_public.path.join(KEYWORD_DEFS, name),
                    message  = 'A bare reference to {named}, which gives one shape two '
                               'names. Compose the schema where it is '
                               'wanted.'.format(named = uri.rsplit('/', 1)[-1]))


# -----------------------------------------------------------------------------
def _names_only_declared(error, declared):
    """
    Return whether every property an unevaluated properties error
    names is declared by some schema of the composition.

    Which properties went unevaluated is in the message and nowhere
    else in the error, so it is read from there.

    """

    return not (set(re.findall(PATTERN_QUOTED, error.message)) - declared)


# -----------------------------------------------------------------------------
def _declared(node, map_schema, seen = None):
    """
    Return every property name the schema declares, anywhere in it and
    in the schemas it refers to.

    Anywhere rather than at the path the error sits on, which would
    mean resolving the subschema there. A name declared somewhere in
    the composition counts as declared, so a misspelling that happens
    to be another item's field escapes; a name nothing declares does
    not (ddr_schema_closure).

    """

    seen = set() if seen is None else seen

    if isinstance(node, list):
        return set().union(*[_declared(one, map_schema, seen) for one in node]) \
               if node else set()

    if not isinstance(node, dict):
        return set()

    out = set(node.get(KEYWORD_PROPERTIES) or ())

    for (key, value) in node.items():

        if key == KEYWORD_REF and isinstance(value, str) and value not in seen:
            seen.add(value)
            out |= _declared(map_schema.get(value.rsplit('/', 1)[-1]
                                                 .removesuffix(SUFFIX_SCHEMA)),
                             map_schema, seen)
        elif key != KEYWORD_PROPERTIES:
            out |= _declared(value, map_schema, seen)
        else:
            out |= _declared(list(value.values()), map_schema, seen)

    return out


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
