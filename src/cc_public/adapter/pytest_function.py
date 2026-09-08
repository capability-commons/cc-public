"""
---

id_self:                pym_cc_public.adapter.pytest_function
guid_self:              pym_c62e5f399bae4c6fb04593696c3d2c04
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pytest function adapter
brief:                  |
                        The adapter that carries out a test method by
                        running one pytest test function.
description:            |
                        A case names the source item of the test
                        function it runs, and the adapter derives the
                        pytest node id from that item: the file the
                        item sits in, then the definitions beneath it.
                        Neither the method nor the case carries a
                        command or a path, so a case names something
                        this tree resolves and asks for nothing but a
                        test to be run.
relation:               []

...
"""


import cc_public.testing


KEY_ID_TEST   = 'id_test'
KEY_ID_SELF   = 'id_self'

PREFIX_MODULE = 'pym'
PREFIX_TEST   = 'pyf'
SEPARATOR     = '_'
DELIM         = '.'
DELIM_NODE    = '::'


# -----------------------------------------------------------------------------
def specify(map_document, configuration):
    """
    Return (node_id, [problem]) for the configuration of one case.

    The node id is derived from the identity the case names and from
    nothing else: the file the test function's module sits in, then the
    definitions beneath it. A case that named a path or a command could
    ask for anything to be run; one that names an identity can ask only
    for a test this tree holds.

    """

    id_test = configuration.get(KEY_ID_TEST)

    if not isinstance(id_test, str):
        return (None, ['The configuration names no test function under {key}.'.format(
                                                                key = KEY_ID_TEST)])

    if id_test.split(SEPARATOR, 1)[0] != PREFIX_TEST:
        return (None, ['{name} is not a python function, so it is not a test to '
                       'run.'.format(name = id_test)])

    map_item = cc_public.testing.index(map_document)

    if id_test not in map_item:
        return (None, ['The configuration names {name}, which this tree does not '
                       'hold.'.format(name = id_test)])

    (id_module, list_definition) = _split(id_test, map_item)

    if id_module is None:
        return (None, ['No python module item holds {name}, so the file to run it in is '
                       'not known.'.format(name = id_test)])

    filepath = id_module.split(SEPARATOR, 1)[1].replace(DELIM, '/') + '.py'

    return (DELIM_NODE.join([filepath, *list_definition]), [])


# -----------------------------------------------------------------------------
def _split(id_test, map_item):
    """
    Return (id of the module holding the test, the definition names
    beneath it), by taking the longest module id the test id begins
    with.

    A function id is its module's id and then the definitions, so the
    module is found by looking rather than by guessing how many parts
    it has.

    """

    stem   = id_test.split(SEPARATOR, 1)[1]
    prefix = PREFIX_MODULE + SEPARATOR
    best   = None

    for name in map_item:
        if not name.startswith(prefix):
            continue
        candidate = name.split(SEPARATOR, 1)[1]
        if (stem + DELIM).startswith(candidate + DELIM) \
                and (best is None or len(candidate) > len(best)):
            best = candidate

    if best is None:
        return (None, [])

    return (prefix + best, stem[len(best) + 1:].split(DELIM))
