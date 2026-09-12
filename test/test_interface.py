"""
---

id_self:                pym_test.test_interface
guid_self:              pym_3dcc7b6d5f5840b5a2d1275541bcc17d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Interface control document schema tests
brief:                  |
                        Tests that a document takes one form per
                        surface, that a native surface names one
                        language, and that a member carries an
                        identity.
description:            |
                        A surface is a keyed object that holds exactly
                        one of native and dataflow_step. A surface
                        with both forms, and a surface with a form the
                        document does not admit, are refused. A native
                        surface names exactly one language. Every
                        declaration a surface holds carries an
                        identity, because a requirement or a test case
                        names one declaration rather than the whole
                        document.
relation:               []

...
"""


import copy
import hashlib

import pytest

import cc_public.check.schema


ID_SCHEMA = 'sch_interface_control_document'


def member(key, name, brief, **rest):
    return dict({'id_self':   'icm_probe.' + key,
                 'guid_self': 'icm_' + hashlib.sha256(key.encode()).hexdigest()[:32],
                 'name':      name,
                 'brief':     brief + '\n'}, **rest)


ICD = {
    'id_self':         'icd_probe',
    'guid_self':       'icd_' + '0' * 32,
    'title':           'A probe interface',
    'brief':           'An interface written to try the schema.\n',
    'description':     'It is thrown away.\n',
    'copyright':       'Copyright 2026 William Payne',
    'license':         'Apache-2.0',
    'protective_mark': [{'id_mark':   'mark_public',
                         'guid_mark': 'mark_0c96ccb7b7534574acf6ed42f9deba0f'}],
    'version_interface': '1.0',
    'status':          'proposed',
    'surface': {
        'python': {'native': {
            'language': 'python',
            'dialect':  'python3.14',
            'class': {'database': member(
                'database', 'Database', 'The graph the queries run over.',
                method = {'path': member(
                    'path', 'path', 'The shortest path between two items.',
                    parameter = [member('source', 'source', 'Where the path starts.',
                                        type = {'spelling': 'str'}, mode = 'input'),
                                 member('target', 'target', 'Where it ends.',
                                        type = {'spelling': 'str'}, mode = 'input')],
                    returns = {'type': {'spelling': 'list[str]'},
                               'brief': 'The items along the path.\n'},
                    error = {'absent': member('absent', 'NoPath',
                                              'No path joins the two.',
                                              condition = 'The graph holds no path.\n')})})}}}},
    'relation': []}


@pytest.fixture(name = 'validate')
def _validate(tree, tmp_path):
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema.registry(map_schema)

    def run(document):
        return cc_public.check.schema.validate(copy.deepcopy(document), ID_SCHEMA,
                                               map_schema, registry)

    return run


def test_a_native_python_surface_conforms(validate):
    assert validate(ICD) == []


def test_a_dataflow_step_surface_conforms(validate):
    document = copy.deepcopy(ICD)
    document['surface'] = {'step': {'dataflow_step': {
        'invocation': 'Once per tick, with whatever the inputs carry.\n',
        'input':  {'frame': member('frame', 'frame', 'The frame to read.')},
        'output': {'track': member('track', 'track', 'What was found in it.')},
        'state':  {'history': member('history', 'history', 'What was found before.')},
        'determinism': 'One frame yields one track table, always.\n'}}}
    assert validate(document) == []


def test_a_surface_holding_two_forms_is_refused(validate):
    document = copy.deepcopy(ICD)
    document['surface']['python']['dataflow_step'] = {'invocation': 'Never.\n'}
    (path, message) = validate(document)[0]
    assert path == 'surface.python'
    assert 'too many properties' in message.lower() or 'maxProperties' in message


def test_a_surface_form_the_document_does_not_admit_is_refused(validate):
    document = copy.deepcopy(ICD)
    document['surface'] = {'wire': {'message_protocol': {'framing': 'length prefixed'}}}
    messages = [message for (_, message) in validate(document)]
    assert any('message_protocol' in message for message in messages)


def test_a_native_surface_naming_no_language_is_refused(validate):
    document = copy.deepcopy(ICD)
    del document['surface']['python']['native']['language']
    messages = [message for (_, message) in validate(document)]
    assert any('language' in message for message in messages)


def test_a_language_the_first_schema_does_not_cover_is_refused(validate):
    document = copy.deepcopy(ICD)
    document['surface']['python']['native']['language'] = 'rust'
    messages = [message for (_, message) in validate(document)]
    assert any('rust' in message for message in messages)


def test_a_member_without_an_identity_is_refused(validate):
    document = copy.deepcopy(ICD)
    del document['surface']['python']['native']['class']['database']['guid_self']
    messages = [message for (_, message) in validate(document)]
    assert any('guid_self' in message for message in messages)


def test_a_type_reference_is_not_an_item_reference(validate):
    document = copy.deepcopy(ICD)
    method = document['surface']['python']['native']['class']['database']['method']['path']
    method['parameter'][0]['type'] = {'id_type': 't_query', 'guid_type': 't_' + '1' * 32}
    messages = [message for (_, message) in validate(document)]
    assert any('id_type' in message for message in messages)


def test_a_baselined_document_states_its_version(validate):
    document = copy.deepcopy(ICD)
    document['status'] = 'baselined'
    del document['version_interface']
    messages = [message for (_, message) in validate(document)]
    assert any('version_interface' in message for message in messages)
