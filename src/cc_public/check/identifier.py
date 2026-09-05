"""
---

id_self:                pym_cc_public.check.identifier
guid_self:              pym_84e70c4ba91c4417a0c48448db0911c4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Identifier check
brief:                  |
                        Check that identifiers are well formed and
                        distinct.
description:            |
                        Holds each identifier against the form its
                        type declares, checks that a register entry
                        key agrees with the id it repeats, that the
                        two halves of a reference name the same type,
                        that no two types claim one prefix, and that
                        no two items claim one readable id.
relation:               []

...
"""


import collections
import re

import cc_public.check.register
import cc_public.check.result
import cc_public.path


ID_CHECK      = 'identifier'
TITLE         = 'Identifiers are well formed and distinct'
NOUN          = 'identity'

KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_REGEX_ID  = 'regex_id'
KEY_REGEX_GUID = 'regex_guid'
KEY_PREFIX    = 'prefix'
KEY_TABLE     = 'table'
KEY_ID_URI    = '$id'

SUFFIX_URI    = '.yaml'

PREFIX_GUID   = 'guid'
PREFIX_ID     = 'id'

SEPARATOR     = '_'

# The form of a guid, for a type that declares no regex_guid of its
# own. A guid is minted rather than chosen, so this holds for every
# type unless one deliberately says otherwise.
#
REGEX_GUID_DERIVED = '^{prefix}_[0-9a-f]{{32}}$'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every identifier that does not match its type.

    """

    (filepath_type,
     document_type) = cc_public.check.register.find_type(context.map_document)

    map_prefix = cc_public.check.register.map_prefix(document_type)

    count_identity     = 0
    list_note          = []
    list_nonconformity = (_prefix_collision(filepath_type, document_type)
                        + _id_collision(context))

    for (filepath, document) in sorted(context.map_document.items()):

        for (path, id_self, guid_self) in iter_identity(document):

            count_identity += 1

            (list_bad, note) = _inspect(filepath, path, id_self, guid_self,
                                        map_prefix)
            list_nonconformity.extend(list_bad)

            if note is not None:
                list_note.append(note)

        list_nonconformity.extend(_pair_disagreement(filepath, document))
        list_nonconformity.extend(_uri_disagreement(filepath, document))

    return cc_public.check.result.Result(
                            count_item         = count_identity,
                            list_nonconformity = list_nonconformity,
                            list_note          = list_note)


# -----------------------------------------------------------------------------
def _prefix_collision(filepath, document_type):
    """
    Return a nonconformity for each type prefix claimed more than once.

    A prefix names exactly one type. It is also the key by which a
    schema is selected, and the index built for that selection is a
    map -- so a second claimant does not conflict, it silently
    displaces the first. Nothing downstream can notice, which is why
    this is checked here.

    """

    map_claim    = collections.defaultdict(list)
    list_bad     = []

    for (key, entry) in (document_type.get(KEY_TABLE) or {}).items():
        if isinstance(entry, dict) and isinstance(entry.get(KEY_PREFIX), str):
            map_claim[entry[KEY_PREFIX]].append(key)

    for (prefix, list_key) in sorted(map_claim.items()):

        if len(list_key) < 2:
            continue

        for key in list_key[1:]:
            list_bad.append(cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = '/{table}/{key}'.format(table = KEY_TABLE,
                                                   key   = key),
                severity = cc_public.check.result.SEVERITY_CRITICAL,
                message  = 'Prefix {prefix} is already claimed by {other}. A '
                           'prefix names exactly one type.'.format(
                                        prefix = prefix,
                                        other  = ', '.join(list_key[:-1]))))

    return list_bad


# -----------------------------------------------------------------------------
def _id_collision(context):
    """
    Return a nonconformity for each readable id declared more than once.

    A readable id is not globally unique and is not promised to be --
    two repositories in a federation may each hold a t_wtp, and neither
    is wrong. Within ONE scope they cannot both be present, because
    nothing can then resolve the name to either of them, and tooling
    that indexes by readable id silently keeps whichever it saw last.

    This is therefore not a claim that the promise was broken. It is
    the point at which a collision has actually been brought about, by
    drawing both items into one scope, and has to be resolved by
    renaming one of them.

    A repeated id carrying a repeated guid is one item declared twice
    rather than two items colliding, and is left to the guid check
    rather than reported here as well.

    """

    map_site = collections.defaultdict(list)

    for (filepath, document) in sorted(context.map_document.items()):
        for (path, id_self, guid_self) in iter_identity(document):
            if isinstance(id_self, str):
                map_site[id_self].append((filepath, path, guid_self))

    list_bad = []

    for (id_self, list_site) in sorted(map_site.items()):

        if len(list_site) < 2:
            continue

        (filepath_first, path_first, guid_first) = list_site[0]

        for (filepath, path, guid_self) in list_site[1:]:

            if guid_self is not None and guid_self == guid_first:
                continue

            list_bad.append(cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_CRITICAL,
                message  = 'Readable id {id_self} is also declared at '
                           '{other}:{path_first}, for a different item. '
                           'Rename one of them, in this scope nothing can '
                           'resolve the name to either.'.format(
                                        id_self    = id_self,
                                        other      = filepath_first,
                                        path_first = path_first)))

    return list_bad


# -----------------------------------------------------------------------------
def _uri_disagreement(filepath, document):
    """
    Return a nonconformity where a document's $id and id_self disagree.

    A schema names itself twice: once as a data item, by id_self, and
    once as a JSON Schema, by the $id that a $ref resolves against. The
    two name one schema, and the last segment of the URI is the
    identifier. Where they differ, a reference resolving by URI reaches
    a schema whose identifier says it is something else.

    JSON Schema cannot compare the two, and the pattern on $id asserts
    the shape of the URI rather than what it ends with, so this is the
    only place the agreement is checked.

    """

    if not isinstance(document, dict):
        return []

    id_uri  = document.get(KEY_ID_URI)
    id_self = document.get(KEY_ID_SELF)

    if not isinstance(id_uri, str) or not isinstance(id_self, str):
        return []

    stem = id_uri.rsplit('/', 1)[-1]

    stem = stem.removesuffix(SUFFIX_URI)

    if stem == id_self:
        return []

    return [cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = KEY_ID_URI,
                severity = cc_public.check.result.SEVERITY_CRITICAL,
                message  = '{key} ends in {stem} but the item declares '
                           'id_self {id_self}. The two name one schema and '
                           'must agree.'.format(key     = KEY_ID_URI,
                                                stem    = stem,
                                                id_self = id_self))]


# -----------------------------------------------------------------------------
def _pair_disagreement(filepath, node, path = ''):
    """
    Return a nonconformity for each id_<role>/guid_<role> pair that disagrees.

    Wherever a mapping names something twice -- once readably and once
    opaquely -- the two name the same item, so they carry the same type
    prefix by construction. Where they do not, the mapping contradicts
    itself, and it does so without reference to anything outside it.

    Applies to every role, not just self: an edge naming a sch by guid
    and a reg by readable id is wrong in the same way and for the same
    reason.

    """

    list_bad = []

    if isinstance(node, dict):

        for (key, value) in node.items():

            if key.startswith(PREFIX_GUID) and isinstance(value, str):

                id_paired = node.get(PREFIX_ID + key[len(PREFIX_GUID):])

                if isinstance(id_paired, str) \
                        and _prefix_of(value) != _prefix_of(id_paired):
                    list_bad.append(cc_public.check.result.Nonconformity(
                        filepath = str(filepath),
                        path     = cc_public.path.join(
                                                        path, key),
                        severity = cc_public.check.result.SEVERITY_CRITICAL,
                        message  = 'Names a {prefix_guid} by guid and a '
                                   '{prefix_id} by readable id ({id_paired}), '
                                   'so the two cannot be the same '
                                   'item.'.format(
                                        prefix_guid = _prefix_of(value),
                                        prefix_id   = _prefix_of(id_paired),
                                        id_paired   = id_paired)))

            list_bad.extend(_pair_disagreement(
                        filepath, value, '{path}/{key}'.format(path = path,
                                                               key  = key)))

    elif isinstance(node, list):

        for (idx, value) in enumerate(node):
            list_bad.extend(_pair_disagreement(
                        filepath, value, '{path}[{idx}]'.format(path = path,
                                                                idx  = idx)))

    return list_bad


# -----------------------------------------------------------------------------
def _prefix_of(identifier):
    """
    Return the type prefix of identifier.

    """

    return identifier.split(SEPARATOR, 1)[0]


# -----------------------------------------------------------------------------
def _inspect(filepath, path, id_self, guid_self, map_prefix):
    """
    Return (list of nonconformity, note) for one declared identity.

    """

    def bad(message):
        return cc_public.check.result.Nonconformity(
                    filepath = str(filepath),
                    path     = path,
                    severity = cc_public.check.result.SEVERITY_CRITICAL,
                    message  = message)

    def unchecked(reason):
        return cc_public.check.result.Note(filepath = str(filepath),
                                           message  = '{path}: {reason}'.format(
                                                        path   = path,
                                                        reason = reason))

    if not isinstance(id_self, str):
        return ([], unchecked('No id_self, so no type to check against.'))

    list_bad = []

    # A register entry is keyed by its readable id and repeats it as a
    # field. Checked before anything to do with types, since the two
    # must agree whether or not the type is known.
    #
    part = cc_public.path.split(path)

    if len(part) >= 2 and part[-2] == KEY_TABLE and part[-1] != id_self:
        list_bad.append(bad(
            'Entry is keyed {key} but declares id_self {id_self}. The key '
            'and the field name the same entry, so they must agree.'.format(
                                        key = part[-1], id_self = id_self)))

    if SEPARATOR not in id_self:
        list_bad.append(bad(
            'Identifier {id_self} carries no type prefix.'.format(
                                                    id_self = id_self)))
        return (list_bad, None)

    prefix = id_self.split(SEPARATOR, 1)[0]

    if prefix not in map_prefix:
        return (list_bad, unchecked('Prefix {prefix} is not in the type '
                                    'register.'.format(prefix = prefix)))

    entry = map_prefix[prefix]

    regex_id = entry.get(KEY_REGEX_ID)

    if isinstance(regex_id, str) and not _matches(regex_id, id_self):
        list_bad.append(bad(
            'Readable id {id_self} does not match {regex_id}, the form '
            'required by its type.'.format(id_self  = id_self,
                                           regex_id = regex_id)))

    if isinstance(guid_self, str):

        regex_guid = entry.get(KEY_REGEX_GUID)
        is_derived = not isinstance(regex_guid, str)

        if is_derived:
            regex_guid = REGEX_GUID_DERIVED.format(
                                        prefix = re.escape(entry[KEY_PREFIX]))

        if not _matches(regex_guid, guid_self):
            list_bad.append(bad(
                'Guid {guid_self} does not match {regex_guid}, the form '
                '{source} for the type of {id_self}.'.format(
                        guid_self  = guid_self,
                        regex_guid = regex_guid,
                        source     = 'derived from the prefix' if is_derived
                                                        else 'it declares',
                        id_self    = id_self)))

    return (list_bad, None)


# -----------------------------------------------------------------------------
def _matches(pattern, value):
    """
    Return whether value matches pattern, an unmatchable pattern aside.

    A pattern that will not compile is a fault in the register rather
    than in the identifier, so it is not reported against the item that
    happened to be checked against it.

    """

    try:
        return re.match(pattern, value) is not None
    except re.error:
        return True


# -----------------------------------------------------------------------------
def iter_identity(document, path = ''):
    """
    Yield (path, id_self, guid_self) for each mapping declaring an identity.

    A mapping declares an identity where it holds id_self or guid_self
    as a STRING. The string test is what keeps a schema's properties
    block out of the reckoning: it holds keys of both those names, but
    their values are subschemas rather than identifiers.

    """

    if isinstance(document, dict):

        id_self   = document.get(KEY_ID_SELF)
        guid_self = document.get(KEY_GUID_SELF)

        if isinstance(id_self, str) or isinstance(guid_self, str):
            yield (path, id_self, guid_self)

        for (key, value) in document.items():
            yield from iter_identity(
                        value, cc_public.path.join(path, key))

    elif isinstance(document, list):

        for (idx, value) in enumerate(document):
            yield from iter_identity(
                        value, cc_public.path.join(path, idx))
