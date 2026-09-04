"""
---

id_self:                pym_cc_public.check.reference
guid_self:              pym_f0ea5d1c3db94638af39fb9fce1c7a6f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Reference check
brief:                  |
                        Check that references resolve and agree with
                        themselves.
description:            |
                        Finds references by position, a reference
                        being a string that is exactly a guid sitting
                        anywhere that is not a declaration. Reports
                        those that do not resolve, and those whose
                        advisory readable id has gone stale.

...
"""


import re

import cc_public.check.identity
import cc_public.check.result
import cc_public.path


ID_CHECK    = 'reference'
TITLE       = 'References resolve and agree'
NOUN        = 'reference'

REGEX_GUID  = re.compile(r'^[a-z]{1,8}_[0-9a-f]{32}$')

PREFIX_GUID = 'guid'
PREFIX_ID   = 'id'

SEPARATOR   = '_'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every reference that does not resolve or agree.

    """

    map_declaration = _map_declaration(context)

    # Where the caller asserts the paths hold everything, a reference
    # that does not resolve is a fault rather than a boundary, and the
    # consequence of it changes accordingly.
    #
    severity_unresolved = (cc_public.check.result.SEVERITY_CRITICAL
                                if context.is_closed_world else
                           cc_public.check.result.SEVERITY_ADVISORY)

    list_nonconformity = []
    count_reference    = 0

    for (filepath, document) in sorted(context.map_document.items()):

        for (path, key, guid, id_advisory) in iter_reference(document):

            count_reference += 1

            list_nonconformity.extend(
                _inspect(filepath, path, guid, id_advisory, map_declaration,
                         severity_unresolved))

    return cc_public.check.result.Result(
                            count_item         = count_reference,
                            list_nonconformity = list_nonconformity,
                            list_note          = [])


# -----------------------------------------------------------------------------
def _inspect(filepath, path, guid, id_advisory, map_declaration,
             severity_unresolved):
    """
    Yield the nonconformities of one reference.

    """

    # A reference whose two halves name different types contradicts
    # itself. That is reported by the identifier check, which applies
    # the same rule to every id/guid pair rather than to references
    # alone, so nothing is said about it here.
    #
    # It is still worth stopping. Such a guid will almost certainly not
    # resolve, and reporting it as possibly lying behind a sharing
    # boundary would be misleading advice about what is a typo.
    #
    if id_advisory is not None and _prefix(guid) != _prefix(id_advisory):
        return

    if guid not in map_declaration:

        if severity_unresolved == cc_public.check.result.SEVERITY_CRITICAL:
            reason = ('The paths given were asserted to be complete, so '
                      'there is nowhere else it could be declared.')
        else:
            reason = ('It may lie behind a sharing boundary, or it may be a '
                      'defect -- only the caller knows.')

        yield cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = severity_unresolved,
                message  = 'Reference to {guid}{named} is not declared in the '
                           'paths given. {reason}'.format(
                                    guid   = guid,
                                    reason = reason,
                                    named  = '' if id_advisory is None else
                                             ' ({id})'.format(id = id_advisory)),
                )
        return

    # Resolvable, so the readable id can be compared against the truth.
    # sch_relation is explicit that a stale copy is harmless, guid_item
    # being the only thing ever resolved, so this is advisory.
    #
    (filepath_target, id_target) = map_declaration[guid]

    if id_advisory is not None and id_target is not None \
                               and id_advisory != id_target:
        yield cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_ADVISORY,
                message  = 'Reference carries the readable id {id_advisory}, '
                           'but {guid} is declared as {id_target} in '
                           '{filepath_target}. The guid is the truth; the '
                           'readable id has gone stale.'.format(
                                        id_advisory     = id_advisory,
                                        guid            = guid,
                                        id_target       = id_target,
                                        filepath_target = filepath_target))


# -----------------------------------------------------------------------------
def iter_reference(document, path = ''):
    """
    Yield (path, key, guid, id_advisory) for each reference in document.

    A reference is a whole string value matching the guid form, at any
    position that is not a declaration site. Where the mapping holding
    it also carries the matching readable id -- guid_obj alongside
    id_obj, guid_item alongside id_item -- that id is yielded with it.

    """

    set_declaration = set(_path_declaration(document))

    yield from _iter_reference(document, path, set_declaration)


# -----------------------------------------------------------------------------
def _iter_reference(node, path, set_declaration):
    """
    Walk node, yielding references.

    """

    if isinstance(node, dict):

        for (key, value) in node.items():

            path_child = cc_public.path.join(path, key)

            if isinstance(value, str) and REGEX_GUID.match(value):
                if path_child not in set_declaration:
                    yield (path_child, key, value, _id_advisory(node, key))
            else:
                yield from _iter_reference(value, path_child, set_declaration)

    elif isinstance(node, list):

        for (idx, value) in enumerate(node):
            yield from _iter_reference(
                            value,
                            cc_public.path.join(path, idx),
                            set_declaration)


# -----------------------------------------------------------------------------
def _id_advisory(mapping, key_guid):
    """
    Return the readable id sitting alongside key_guid, or None.

    The two field names differ only in their leading word, so the
    readable one is named by substitution rather than by a table.

    """

    if not key_guid.startswith(PREFIX_GUID):
        return None

    key_id = PREFIX_ID + key_guid[len(PREFIX_GUID):]
    value  = mapping.get(key_id)

    return value if isinstance(value, str) else None


# -----------------------------------------------------------------------------
def _path_declaration(document):
    """
    Yield the path of each declaration, which is therefore not a reference.

    """

    for (path, _) in cc_public.check.identity.iter_declaration(document):
        yield path


# -----------------------------------------------------------------------------
def _map_declaration(context):
    """
    Return a guid to (filepath, id_item) map of everything declared in scope.

    """

    map_declaration = {}

    for (filepath, document) in context.map_document.items():
        for (path, guid) in cc_public.check.identity.iter_declaration(document):
            map_declaration[guid] = (filepath, _id_at(document, path))

    return map_declaration


# -----------------------------------------------------------------------------
def _id_at(document, path):
    """
    Return the readable id declared alongside the guid at path.

    """

    node = document

    for part in cc_public.path.split(path)[:-1]:
        if not isinstance(node, dict):
            return None
        node = node.get(part, {})

    return node.get('id_self') if isinstance(node, dict) else None


# -----------------------------------------------------------------------------
def _prefix(identifier):
    """
    Return the type prefix of identifier.

    """

    return identifier.split(SEPARATOR, 1)[0]
