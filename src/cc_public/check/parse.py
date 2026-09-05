"""
---

id_self:                pym_cc_public.check.parse
guid_self:              pym_31509ffe5b17441a895f33a43a19f929
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Parse check
brief:                  |
                        Check that structured data files load.
description:            |
                        Reports the files the driver could not load.
                        The loading itself is done once by the driver,
                        so this check reports what was found rather
                        than reading anything again.
relation:               []

...
"""


import cc_public.check.result


ID_CHECK = 'parse'
TITLE    = 'Files load'
NOUN     = 'file'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every file that did not load.

    """

    list_nonconformity = [
        cc_public.check.result.Nonconformity(filepath = str(filepath),
                                             path     = '',
                                             message  = message)
            for (filepath, message) in context.list_failure_load]

    return cc_public.check.result.Result(
                            count_item         = len(context.list_filepath),
                            list_nonconformity = list_nonconformity,
                            list_note          = [])
