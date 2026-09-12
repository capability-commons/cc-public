"""
---

id_self:                pym_cc_public.check.testing
guid_self:              pym_5cd4ce2fbead4451b4b89e7aaa321161
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test binding check
brief:                  |
                        Check that every test case resolves into a
                        runnable specification and that its
                        configuration is what its method asks for.
description:            |
                        A test case names one method. The method names
                        an adapter the tree holds, and a schema for
                        the configuration a case supplies. The case
                        supplies configuration that the schema
                        accepts. A binding that does not resolve is
                        reported where the case is written. The
                        resolution itself is done by the testing
                        module, which validates nothing. The schema of
                        the configuration is read here, in the check,
                        because this is where the schemas are.
relation:               []

...
"""


import cc_public.check.result
import cc_public.check.schema
import cc_public.path
import cc_public.testing


ID_CHECK    = 'testing'
TITLE       = 'Test cases resolve into a runnable specification'
NOUN        = 'test case'

KEY_CONFIG  = 'configuration'


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every test case that does not resolve, and
    every configuration its method's schema refuses.

    A case that does not resolve cannot be run, and the reason is
    reported where the case is written rather than where the run would
    have failed.

    """

    map_schema = cc_public.check.schema.map_schema(context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    count    = 0
    list_bad = []

    for (location, id_case) in cc_public.testing.iter_case(context.map_document):

        count += 1

        (specification, list_problem) = cc_public.testing.resolve(context.map_document,
                                                                  id_case)

        list_bad.extend(_fault(location, '', problem)
                        for problem in list_problem)

        if specification is None:
            continue

        list_bad.extend(_configuration(location, specification, map_schema, registry))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _configuration(location, specification, map_schema, registry):
    """
    Return a fault for each way the configuration a case supplies fails
    the schema its method names.

    """

    if specification.id_schema_case not in map_schema:
        return []

    return [_fault(location, cc_public.path.join(KEY_CONFIG, path),
                   '{message} The schema is {schema}, which {method} names for the '
                   'configuration of its cases.'.format(
                            message = message,
                            schema  = specification.id_schema_case,
                            method  = specification.id_method))
            for (path, message) in cc_public.check.schema.validate(
                                        specification.configuration,
                                        specification.id_schema_case,
                                        map_schema, registry)]


# -----------------------------------------------------------------------------
def _fault(location, path, message):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.fault(location, path, message)
