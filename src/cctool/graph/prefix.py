"""
---

id_self:                pym_cctool.graph.prefix
guid_self:              pym_1ac0b017d3da4bff8853fb9ac8728804
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Type prefixes
brief:                  |
                        The prefix of each type of data item, as the
                        data item type register records it, for code
                        that names or recognizes ids.
description:            |
                        The data item type register is where a prefix
                        is decided: each type entry has a prefix
                        field. Code that has to know a prefix before
                        it reads a tree, such as the extractor when it
                        names a python module, takes it from here, and
                        nowhere else. A test compares this map with
                        the register, so a prefix changed in the
                        register and not here fails the tests.
edge:                   []

...
"""


MAP_PREFIX        = {'type_annotation':                 'ann',
                     'type_commit':                     'cmt',
                     'type_concept':                    'concept',
                     'type_criticality':                'crit',
                     'type_concern':                    'concern',
                     'type_dataflow_graph':             'dfg',
                     'type_dataflow_node':              'dfn',
                     'type_decision':                   'dec',
                     'type_design_rule':                'rule',
                     'type_external_class':             'extcla',
                     'type_external_document':          'extdoc',
                     'type_external_relation':          'extrel',
                     'type_file':                       'file',
                     'type_interface_control_document': 'icd',
                     'type_interface_member':           'icm',
                     'type_logic_program_file':         'lpf',
                     'type_logic_program_predicate':    'lpp',
                     'type_logical_component':          'lco',
                     'type_maturity_level':             'maturity',
                     'type_option':                     'opt',
                     'type_protective_mark':            'mark',
                     'type_python_class':               'pycls',
                     'type_python_function':            'pyf',
                     'type_python_module':              'pym',
                     'type_python_package':             'pyp',
                     'type_register':                   'reg',
                     'type_relation':                   'relation',
                     'type_relation_constraint':        'relcon',
                     'type_release':                    'release',
                     'type_requirement':                'rqt',
                     'type_review':                     'review',
                     'type_role':                       'rol',
                     'type_ruling':                     'ruling',
                     'type_schema':                     'sch',
                     'type_federated_segment':          'segment',
                     'type_shell_script':               'shell',
                     'type_team_member':                'member',
                     'type_test_case':                  'case',
                     'type_type':                       'type',
                     'type_writing_style_rule':         'style'}


# -----------------------------------------------------------------------------
def stem(id_type: str) -> str:
    """
    Return the start of every id of the type id_type: its prefix and
    an underscore.

    """

    return MAP_PREFIX[id_type] + '_'
