"""
---

id_self:                pym_cc_public.check.source
guid_self:              pym_90a2bc08403b4f308d116976d5ec5244
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Source check
brief:                  |
                        Check that every class and function item is
                        named by where it sits.
description:            |
                        A class or function item lives in the
                        docstring of its definition, and its
                        identifier is its module's, then the run of
                        definition names down to it in lower case,
                        under the prefix of its kind. A document
                        declaring another identifier has been moved
                        without its definition or left behind by a
                        rename, and an edge pointing at it no longer
                        points at the code. Critical, at the document.
relation:               []

...
"""


import cc_public.check.result
import cc_public.load
import cc_public.load.python


ID_CHECK       = 'source'
TITLE          = 'Source items sit where their identifiers say'
NOUN           = 'source item'

KEY_ID_SELF    = 'id_self'
SEPARATOR      = '_'
DELIM          = '.'

# The prefix a document in a definition's docstring carries, by what
# the definition is.
#
PREFIX_BY_KIND = {cc_public.load.python.KIND_CLASS:    'pyc',
                  cc_public.load.python.KIND_FUNCTION: 'pyf'}


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every class or function item whose identifier
    is not the one its place in the file gives it.

    A source item is named by where it sits: its module's identifier,
    then the run of definition names down to it, in lower case, under
    the prefix of its kind. A document that says otherwise has been
    moved without its definition, or its definition renamed without it,
    and either way an edge pointing at the identifier no longer points
    at the code.

    """

    map_document = context.map_document
    list_bad     = []
    count        = 0

    for (location, document) in sorted(map_document.items()):

        if location.is_own or not isinstance(document, dict):
            continue

        count += 1

        own       = map_document.get(cc_public.load.Location(location.filepath))
        id_module = own.get(KEY_ID_SELF) if isinstance(own, dict) else None

        # The module's own identifier is the identifier check's to
        # report; without a sound one there is nothing to compare to.
        #
        if not isinstance(id_module, str) or SEPARATOR not in id_module:
            continue

        expected = '{prefix}{sep}{body}{delim}{anchor}'.format(
                        prefix = PREFIX_BY_KIND.get(location.kind, '?'),
                        sep    = SEPARATOR,
                        body   = id_module.split(SEPARATOR, 1)[1],
                        delim  = DELIM,
                        anchor = DELIM.join(location.anchor).lower())

        if document.get(KEY_ID_SELF) != expected:
            list_bad.append(cc_public.check.result.Nonconformity(
                    filepath = str(location),
                    path     = KEY_ID_SELF,
                    message  = 'Declares {declared}, and sits in {kind} {name} of '
                               '{module}, which names it {expected}. A source item '
                               'is named by where it sits: move the document with '
                               'the definition, or make it say where it '
                               'is.'.format(declared = document.get(KEY_ID_SELF),
                                            kind     = location.kind,
                                            name     = DELIM.join(location.anchor),
                                            module   = id_module,
                                            expected = expected)))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])
