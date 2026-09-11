"""
---

id_self:                pyp_cc_public.adapter
guid_self:              pyp_7c214a7f7c7f4f25bc5d2ea2f6e69059
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Adapters
brief:                  |
                        The installed adapters that carry out an
                        automated test method.
description:            |
                        A test method names an adapter by identity and
                        never a command, so what a run executes is
                        code installed with the tool. Each module here
                        is one adapter. The package itself holds the
                        runner that selects one from the allowlist,
                        runs it, and normalises what it observed into
                        a test execution.
relation:               []

...
"""


import datetime
import platform
import sys
import uuid

import cc_public.check.register
import cc_public.check.schema
import cc_public.edit.new
import cc_public.decision
import cc_public.load.git
import cc_public.testing

from cc_public.adapter import pytest_function


# The adapters a method may name. A method names one by identity, and
# nothing outside this map is reachable from a data item, so no item is
# a way to run code the tool does not already hold.
#
ADAPTER       = {'pym_cc_public.adapter.pytest_function': pytest_function}

ID_SCHEMA     = 'sch_test_execution'
ID_TYPE       = 't_test_execution'

KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RESULT    = 'result'

PREFIX_EXE    = 'tex'
PREFIX_RESULT = 'tres'
KEY_MAIN      = 'main'
KEY_RANGE     = 'range'
KEY_ID_SELF   = 'id_self'
REL_TESTS     = 'r_tests'
SEPARATOR     = '_'


# -----------------------------------------------------------------------------
def execute(tree, id_case, id_under_test):
    """
    Return (document of a test execution, [problem]) for one binding.

    The document is not written. A caller that wants it kept writes it;
    one that wants the outcome reads it. It is validated against
    sch_test_execution before it is returned, so nothing invalid
    reaches an evidence projection.

    """

    map_document = tree.context.map_document

    (specification, list_problem) = cc_public.testing.resolve(map_document, id_case)

    if specification is None:
        return (None, list_problem)

    map_item = cc_public.testing.index(map_document)
    subject  = map_item.get(id_under_test)

    if subject is None:
        return (None, ['No item in this tree is named {name}, so there is nothing to '
                       'observe.'.format(name = id_under_test)])

    kind = _kind_of(map_document, id_under_test)

    if kind not in _admitted(map_document):
        return (None, ['{name} is a {kind}, and r_tests admits {which}. What was bound '
                       'is what the execution records observed, so anything may be '
                       'named and nothing would say '
                       'otherwise.'.format(name = id_under_test, kind = kind or 'no type',
                                           which = ', '.join(sorted(_admitted(map_document)))
                                                   or 'nothing')])

    if specification.id_adapter is None:
        return (None, ['{case} names {method}, which a person carries out, so nothing '
                       'here runs it. Its evidence is an attestation, which cctool '
                       'attest records.'.format(case    = id_case,
                                                method  = specification.id_method)])

    adapter = ADAPTER.get(specification.id_adapter)

    if adapter is None:
        return (None, ['{name} is not an installed adapter. A method names one of {known}.'
                       .format(name = specification.id_adapter,
                               known = ', '.join(sorted(ADAPTER)))])

    started  = _now()
    observed = adapter.run(map_document, specification.configuration, tree.root)

    document = _document(tree, specification, id_under_test, subject, observed, started)

    map_schema = cc_public.check.schema.map_schema(map_document)
    list_error = cc_public.check.schema.validate(
                        document, ID_SCHEMA, map_schema,
                        cc_public.check.schema.registry(map_schema))

    return (document, ['The execution does not conform at {path}. {message}'.format(
                                                    path = path or '(root)',
                                                    message = message)
                       for (path, message) in list_error])


# -----------------------------------------------------------------------------
def _document(tree, specification, id_under_test, subject, observed, started):
    """
    Return the execution document for one run.

    """

    stamp   = started.strftime('%Y%m%d%H%M%S')
    short   = uuid.uuid4().hex[:6]
    id_self = '{p}_{stamp}_{short}'.format(p = PREFIX_EXE, stamp = stamp, short = short)
    result  = {KEY_ID_SELF:          '{p}_{stamp}_{short}.{key}'.format(
                                            p = PREFIX_RESULT, stamp = stamp,
                                            short = short, key = KEY_MAIN),
               KEY_GUID_SELF:        PREFIX_RESULT + '_' + uuid.uuid4().hex,
               'conformance_result': observed.conformance_result,
               'observation':        observed.observation.rstrip('\n') + '\n'}

    if observed.conformance_result is None:
        del result['conformance_result']

    defaults = tree.defaults()
    document = {'copyright':       defaults.get('copyright'),
                'license':         defaults.get('license'),
                'protective_mark': [{'id_mark':   defaults.get('id_mark'),
                                     'guid_mark': tree.resolve(
                                            defaults['id_mark']).guid_self}]}
    document.update({
        KEY_ID_SELF:         id_self,
        KEY_GUID_SELF:       PREFIX_EXE + '_' + uuid.uuid4().hex,
        'title':             'Run of {case}'.format(case = specification.id_case),
        'brief':             '{case} run against {subject} by {method}.\n'.format(
                                    case    = specification.id_case,
                                    subject = id_under_test,
                                    method  = specification.id_method),
        'description':       'What {adapter} observed, normalised.\n'.format(
                                    adapter = specification.id_adapter),
        'id_method':         specification.id_method,
        'guid_method':       tree.resolve(specification.id_method).guid_self,
        'digest_method':     specification.digest_method,
        'id_case':           specification.id_case,
        'guid_case':         tree.resolve(specification.id_case).guid_self,
        'digest_case':       specification.digest_case,
        'id_under_test':     id_under_test,
        'guid_under_test':   tree.resolve(id_under_test).guid_self,
        'digest_under_test': cc_public.decision.digest_of(subject),
        'id_adapter':        specification.id_adapter,
        'guid_adapter':      tree.resolve(specification.id_adapter).guid_self,
        'adapter_version':   'pytest ' + observed.version,
        'environment':       _environment(tree, observed),
        'time_start':        _text(started),
        'time_finish':       _text(_now()),
        'execution_outcome': observed.execution_outcome,
        KEY_RESULT:          {KEY_MAIN: result},
        'relation':          [_edge(tree, 'r_uses_test_method', specification.id_method),
                              _edge(tree, 'r_tests', id_under_test)]})

    return document


# -----------------------------------------------------------------------------
def _admitted(map_document):
    """
    Return the types r_tests admits at its far end, read from the
    relation register.

    Read rather than listed, so that widening what may be bound is
    editing the entry (ddr_test_execution).

    """

    index = cc_public.item.index(map_document).by_id.get(REL_TESTS)

    return set((index.document.get(KEY_RANGE) or ()) if index else ())


# -----------------------------------------------------------------------------
def _kind_of(map_document, id_self):
    """
    Return the type of the item called id_self, by its prefix.

    """

    (_, document) = cc_public.check.register.find_type(map_document)
    entry = cc_public.check.register.map_prefix(document).get(
                                        id_self.split(SEPARATOR, 1)[0])

    return entry.get(KEY_ID_SELF) if entry else None


# -----------------------------------------------------------------------------
def _environment(tree, observed):
    """
    Return what a later reader needs in order to run this again: the
    interpreter, the platform, the node run, and whether the tree was
    clean when it ran.

    """

    try:
        revision = cc_public.load.git.revision(tree.root)
    except Exception:
        revision = None

    return ('python {version} on {platform}. The node was {node}. The tree was at '
            '{revision}.\n'.format(version  = platform.python_version(),
                                   platform = sys.platform,
                                   node     = observed.node or 'not resolved',
                                   revision = revision or 'no revision'))


# -----------------------------------------------------------------------------
def _edge(tree, id_relation, id_target):
    """
    Return one relation edge to the named item.

    """

    return {'id_relation':   id_relation,
            'guid_relation': tree.resolve(id_relation).guid_self,
            'id_target':     id_target,
            'guid_target':   tree.resolve(id_target).guid_self}


def _now():
    """
    Return the time now, in UTC.

    """

    return datetime.datetime.now(datetime.UTC)


def _text(when):
    """
    Return a time as the schema spells one.

    """

    return when.strftime('%Y-%m-%dT%H:%M:%SZ')


# -----------------------------------------------------------------------------
def record(tree, document):
    """
    Write an execution to the tree, and return its readable id.

    A run keeps nothing unless it is asked to. This is what asking
    does.

    """

    return cc_public.edit.new.from_document(tree, ID_TYPE, document)
