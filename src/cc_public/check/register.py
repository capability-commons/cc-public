"""
---

id_self:                pym_cc_public.check.register
guid_self:              pym_b2e7cf718cea4a3caa05b09313530dde
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Register lookup
brief:                  |
                        Find the type register and index it by prefix.
description:            |
                        The type register, and the map from a type
                        prefix to the entry describing that type. Used
                        by the checks that resolve a type.

...
"""


ID_REG_TYPE = 'reg_type'

KEY_ID_SELF = 'id_self'
KEY_TABLE   = 'table'
KEY_PREFIX  = 'prefix'


# -----------------------------------------------------------------------------
class ErrorRegisterNotFound(Exception):
    """
    Raised when the type register cannot be found in the paths given.

    """



# -----------------------------------------------------------------------------
def find_type(map_document):
    """
    Return (filepath, document) for the type register.

    The one identifier that is known rather than discovered. Every
    other association in the system is read out of the register this
    names.

    """

    for (filepath, document) in map_document.items():
        if isinstance(document, dict) \
                        and document.get(KEY_ID_SELF) == ID_REG_TYPE:
            return (filepath, document)

    raise ErrorRegisterNotFound(
        'No data item with id_self {id_self} was found among the paths '
        'given, so no type can be resolved. Add the type register to '
        '--path.'.format(id_self = ID_REG_TYPE))


# -----------------------------------------------------------------------------
def map_prefix(document_register_type):
    """
    Return a type prefix to type entry map, taken from the type register.

    """

    return {entry[KEY_PREFIX]: entry
                for entry in document_register_type[KEY_TABLE].values()
                if  isinstance(entry, dict)
                and entry.get(KEY_PREFIX) is not None}
