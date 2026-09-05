"""
---

id_self:                pym_cc_public.check.identity
guid_self:              pym_0c19a62a6e204b63959346552671cd27
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Identity check
brief:                  |
                        Check that identity declarations are unique.
description:            |
                        Collects every guid_self, at any depth, and
                        reports any guid declared more than once.
                        Walks the loaded structure, so a guid quoted
                        in prose is not a declaration.
relation:               []

...
"""


import collections

import cc_public.check.result
import cc_public.path


ID_CHECK  = 'guid'
TITLE     = 'Declarations are unique'
NOUN      = 'declaration'

KEY_GUID  = 'guid_self'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every guid_item declared more than once.

    A collision is reported against the second and subsequent
    declaration, so that the first one stays the one that owns it.
    Which declaration comes first follows the order in which files are
    walked, and carries no authority beyond that.

    """

    map_site          = collections.defaultdict(list)
    count_declaration = 0

    for (filepath, document) in context.map_document.items():
        for (path, guid) in iter_declaration(document):
            map_site[guid].append((filepath, path))
            count_declaration += 1

    list_nonconformity = []

    for (guid, list_site) in sorted(map_site.items()):

        if len(list_site) < 2:
            continue

        (filepath_first, path_first) = list_site[0]

        for (filepath, path) in list_site[1:]:
            list_nonconformity.append(
                cc_public.check.result.Nonconformity(
                    filepath = str(filepath),
                    path     = path,
                    message  = '{guid} is already declared at '
                               '{other}:{path_first}'.format(
                                        guid       = guid,
                                        other      = filepath_first,
                                        path_first = path_first)))

    return cc_public.check.result.Result(
                            count_item         = count_declaration,
                            list_nonconformity = list_nonconformity,
                            list_note          = [])


# -----------------------------------------------------------------------------
def iter_declaration(document, path = ''):
    """
    Yield (path, guid) for each identity declaration in document.

    A declaration is any guid_self field, at any depth. Nothing about
    the containing structure is consulted.

    """

    if isinstance(document, dict):

        for (key, value) in document.items():

            path_child = cc_public.path.join(path, key)

            if key == KEY_GUID and isinstance(value, str):
                yield (path_child, value)
            else:
                yield from iter_declaration(value, path_child)

    elif isinstance(document, list):

        for (idx, value) in enumerate(document):
            yield from iter_declaration(
                        value, cc_public.path.join(path, idx))
