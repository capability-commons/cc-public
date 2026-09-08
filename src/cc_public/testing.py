"""
---

id_self:                pym_cc_public.testing
guid_self:              pym_839c532f346f4e67bd8abf085445003a
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test model
brief:                  |
                        Resolve a test case into the specification of
                        a run: the method, the adapter, the
                        configuration and the digests the result will
                        be bound to.
description:            |
                        A test case names one test method, the method
                        names the adapter that carries it out, and the
                        case carries the configuration that method
                        asks for. Resolving them yields everything a
                        run needs except the item under test, which is
                        bound when the run happens.

                        Every problem found on the way is returned
                        rather than raised, so a caller reports all of
                        them at once.

                        Plain data over the documents of a tree.
                        Validation against a schema is done by the
                        check that reads this.
relation:               []

...
"""


import typing

import cc_public.decision
import cc_public.item


KEY_ID_SELF     = 'id_self'
KEY_RELATION    = 'relation'
KEY_ID_REL      = 'id_relation'
KEY_ID_TARGET   = 'id_target'
KEY_TABLE       = 'table'
KEY_FORM        = 'execution_form'
KEY_AUTOMATED   = 'automated'
KEY_ID_ADAPTER  = 'id_adapter'
KEY_ID_SCHEMA   = 'id_schema_case'
KEY_CONFIG      = 'configuration'
KEY_VERSION     = 'version'
KEY_EXPECTATION = 'expectation'
KEY_CRITERIA    = 'success_criteria'

REL_USES        = 'r_uses_test_method'
REL_VERIFIES    = 'r_verifies'

PREFIX_CASE     = 'tc'
PREFIX_RELATION = 'r'
KEY_DEPENDENCY  = 'dependency'
SEPARATOR       = '_'


# -----------------------------------------------------------------------------
class Specification(typing.NamedTuple):
    """
    Everything a run of one test case needs, save the item under test.

    id_schema_case is the schema the method says governs configuration.
    The digests are what a result is bound to: a later reader compares
    them to the items as they are and sees at once whether the result
    still describes what exists.

    """

    id_case:        str
    id_method:      str
    id_adapter:     str
    id_schema_case: str
    configuration:  dict
    digest_case:    str
    digest_method:  str
    list_verified:  tuple


# -----------------------------------------------------------------------------
def resolve(map_document, id_case):
    """
    Return (Specification, [problem]) for the case called id_case.

    The Specification is None where a problem stopped the resolution.
    Every problem found is returned, so that a caller reports them all
    at once rather than one per run.

    """

    map_item = index(map_document)
    case     = map_item.get(id_case)

    if case is None:
        return (None, ['No item in this tree is named {name}.'.format(name = id_case)])

    list_problem = []
    list_method  = _target(case, REL_USES)

    if len(list_method) != 1:
        return (None, ['{case} names {n} test method(s) by {rel}, and a case names '
                       'one.'.format(case = id_case, n = len(list_method),
                                     rel = REL_USES)])

    id_method = list_method[0]
    method    = map_item.get(id_method)

    if method is None:
        return (None, ['{case} names the test method {name}, which this tree does not '
                       'hold.'.format(case = id_case, name = id_method)])

    automated = (method.get(KEY_FORM) or {}).get(KEY_AUTOMATED)

    if automated is None:
        list_problem.append(
                '{method} takes no automated execution form, so nothing here runs '
                'it.'.format(method = id_method))

    id_adapter = (automated or {}).get(KEY_ID_ADAPTER)

    if id_adapter is not None and id_adapter not in map_item:
        list_problem.append(
                '{method} names the adapter {name}, which this tree does not '
                'hold.'.format(method = id_method, name = id_adapter))

    id_schema = method.get(KEY_ID_SCHEMA)

    if id_schema is not None and id_schema not in map_item:
        list_problem.append(
                '{method} names {name} as the schema of its case configuration, and this '
                'tree does not hold it.'.format(method = id_method, name = id_schema))

    if list_problem:
        return (None, list_problem)

    return (Specification(id_case        = id_case,
                          id_method      = id_method,
                          id_adapter     = id_adapter,
                          id_schema_case = id_schema,
                          configuration  = case.get(KEY_CONFIG) or {},
                          digest_case    = cc_public.decision.digest_of(case),
                          digest_method  = cc_public.decision.digest_of(method),
                          list_verified  = tuple(_target(case, REL_VERIFIES))),
            [])


# -----------------------------------------------------------------------------
def iter_case(map_document):
    """
    Yield (location, id_self) for every test case in the tree.

    """

    for (location, document) in sorted(map_document.items(), key = str):
        if isinstance(document, dict) \
                and str(document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] \
                                                            == PREFIX_CASE:
            yield (location, document[KEY_ID_SELF])


# -----------------------------------------------------------------------------
def locate(map_document, id_self):
    """
    Return the location of the item called id_self, or None.

    A location carries the file and, for an item held in a docstring,
    the run of definition names down to it as the source spells them.
    The readable id spells them in lower case, so the location is what
    a caller needing the real names asks.

    """

    held = cc_public.item.index(map_document).by_id.get(id_self)

    return held.location if held is not None else None


# -----------------------------------------------------------------------------
def index(map_document):
    """
    Return every item in the tree by readable id, the items held within
    another included, since a test method is an entry of a register.

    """

    return {name: held.document
            for (name, held) in cc_public.item.index(map_document).by_id.items()}


# -----------------------------------------------------------------------------
def _target(item, id_relation):
    """
    Return the readable id of every item the given relation reaches
    from this one.

    """

    return [edge[KEY_ID_TARGET]
            for edge in item.get(KEY_RELATION) or []
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == id_relation
            and edge.get(KEY_ID_TARGET) is not None]


# -----------------------------------------------------------------------------
def dependency(map_document):
    """
    Return the readable ids of every relation declaring that following
    it reaches something the source rests on.

    Read from the relation register, so a relation a partner brings is
    followed by the same closure without this module knowing its name.

    """

    out = set()

    for document in map_document.values():

        if not isinstance(document, dict) or not isinstance(document.get(KEY_TABLE), dict):
            continue

        for entry in document[KEY_TABLE].values():
            if isinstance(entry, dict) and entry.get(KEY_DEPENDENCY) \
                    and str(entry.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] \
                                                                == PREFIX_RELATION:
                out.add(entry[KEY_ID_SELF])

    return frozenset(out)


# -----------------------------------------------------------------------------
def closure(map_document, list_id):
    """
    Return the readable ids of the items given and of every item
    reachable from them by a dependency edge, in order.

    A chain is followed as far as it runs and each item is reached
    once, so a cycle terminates.

    """

    map_item  = index(map_document)
    follow    = dependency(map_document)
    seen      = []
    set_seen  = set()
    pending   = [name for name in list_id if name]

    while pending:

        name = pending.pop(0)

        if name in set_seen:
            continue

        set_seen.add(name)
        seen.append(name)

        item = map_item.get(name)

        if item is None:
            continue

        pending.extend(edge[KEY_ID_TARGET]
                       for edge in item.get(KEY_RELATION) or []
                       if isinstance(edge, dict)
                       and edge.get(KEY_ID_REL) in follow
                       and edge.get(KEY_ID_TARGET) is not None)

    return tuple(seen)


# -----------------------------------------------------------------------------
def expectation(map_document, id_case):
    """
    Return what a case expects, or None where nothing says.

    A case states its own expectation where what it expects is not what
    the requirement already says: over one test function that observes
    several requirements, a case for each, expecting something
    different of the same run.

    Where the case states none, what it verifies is the statement. The
    success criteria of a requirement are the expected result, so a
    case repeating them would be a second copy to keep current and a
    second thing to disagree with the first.

    """

    map_item = index(map_document)
    case     = map_item.get(id_case)

    if not isinstance(case, dict):
        return None

    stated = str(case.get(KEY_EXPECTATION) or '').strip()

    if stated:
        return stated

    list_criteria = []

    for name in _target(case, REL_VERIFIES):
        verified = map_item.get(name)
        if not isinstance(verified, dict):
            continue
        criteria = str(verified.get(KEY_CRITERIA) or '').strip()
        if criteria:
            list_criteria.append(criteria)

    return '\n\n'.join(list_criteria) or None
