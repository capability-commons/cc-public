"""
---

id_self:                pym_test.test_criticality
guid_self:              pym_2f3984cff14741de841e60d3e0534b43
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Criticality derivation tests
brief:                  |
                        Tests that criticality is declared on a
                        requirement, derived onto what is responsible
                        for meeting it, and taken as the greatest on
                        each dimension separately.
description:            |
                        The levels and the relations followed are read
                        from the registers, so each test changes a
                        register or a requirement and asks what the
                        derivation says.
relation:               []

...
"""


import cc_public.edit.field
import cc_public.edit.link
import cc_public.trace


ID_REQ    = 'req_path_reported'
ID_OTHER  = 'req_named_query_run'
ID_UNDER  = 'pyf_cc_public.query.database.path'
SAFETY_60 = 'crit_safety_60'
SAFETY_90 = 'crit_safety_90'
SEC_40    = 'crit_security_40'


def _declare(tree, id_requirement, dimension, id_level, guid_level = None):
    """
    Give a requirement a criticality on one dimension, keeping any
    other dimension it already declares.

    """

    document = tree.context.map_document[tree.resolve(id_requirement).location]
    carried  = dict(document.get('criticality') or {})
    carried[dimension] = {
        'id_criticality':   id_level,
        'guid_criticality': guid_level or tree.resolve(id_level).guid_self}
    cc_public.edit.field.set_field(tree, id_requirement, 'criticality',
                                   value = carried)


def _derived(tree):
    return cc_public.trace.criticality(tree.context.map_document)


def test_the_base_is_read_from_the_register_and_not_from_the_code(tree):
    # Ten entries, five on each dimension, the lowest of each the base.
    base = _derived(tree).base
    assert base == {'safety': 10, 'security': 10}


def test_the_relations_followed_are_declared_and_not_listed(tree):
    followed = cc_public.trace.responsibility(tree.context.map_document)
    assert 'r_is_implemented_by' in followed
    assert 'r_verifies' not in followed          # verifying is not being responsible


def test_a_relation_that_declares_responsibility_is_followed(tree):
    before = cc_public.trace.responsibility(tree.context.map_document)
    cc_public.edit.field.set_field(tree, 'r_verifies', 'responsibility',
                                   value = True)
    assert cc_public.trace.responsibility(tree.context.map_document) \
           == before | {'r_verifies'}


def test_nothing_declares_a_criticality_so_nothing_derives_one(tree):
    assert _derived(tree).derived == {}


def test_what_implements_a_requirement_takes_its_criticality(tree):
    _declare(tree, ID_REQ, 'safety', SAFETY_60)
    derived = _derived(tree).derived
    assert derived[ID_UNDER] == {'safety': 60}

    # And only what that requirement reaches: the requirement itself
    # declares rather than derives, and its siblings are untouched.
    assert ID_REQ not in derived
    assert all(one == ID_UNDER or 'safety' not in level
               for (one, level) in derived.items())


def test_a_dimension_left_out_stays_at_its_base(tree):
    _declare(tree, ID_REQ, 'safety', SAFETY_60)
    assert 'security' not in _derived(tree).derived[ID_UNDER]


def test_each_dimension_is_carried_separately(tree):
    _declare(tree, ID_REQ, 'safety',   SAFETY_60)
    _declare(tree, ID_REQ, 'security', SEC_40)
    assert _derived(tree).derived[ID_UNDER] == {'safety': 60, 'security': 40}


def test_the_greatest_reaching_an_item_is_the_one_it_takes(tree):
    # Two requirements on one item: the graver consequence decides, so
    # that a trivial requirement cannot dilute a critical one.
    cc_public.edit.link.link(tree, ID_OTHER, 'r_is_implemented_by', ID_UNDER)
    _declare(tree, ID_REQ,   'safety', SAFETY_60)
    _declare(tree, ID_OTHER, 'safety', SAFETY_90)
    assert _derived(tree).derived[ID_UNDER]['safety'] == 90


def test_criticality_runs_as_far_as_the_edges_run(tree):
    # A chain: the module is responsible for the function, so it takes
    # what reached the function.
    cc_public.edit.link.link(tree, ID_UNDER, 'r_is_implemented_by',
                             'pym_cc_public.query')
    _declare(tree, ID_REQ, 'safety', SAFETY_90)
    derived = _derived(tree).derived
    assert derived[ID_UNDER]['safety']        == 90
    assert derived['pym_cc_public.query']['safety'] == 90


def test_a_level_the_register_does_not_hold_carries_nothing(tree):
    _declare(tree, ID_REQ, 'safety', 'crit_safety_50', guid_level = 'crit_x')
    assert _derived(tree).derived == {}


def test_the_command_reads_the_same_projection(tree, tmp_path):
    import click.testing

    import cc_public.cli.assurance
    import cc_public.cli.group

    def run(*option):
        return click.testing.CliRunner().invoke(
                    cc_public.cli.group.main,
                    ['trace', '--criticality', '--root', str(tmp_path), *option])

    done = run()
    assert done.exit_code == 0
    assert 'safety 10' in done.output and 'security 10' in done.output
    assert 'Nothing declares a criticality' in done.output

    _declare(tree, ID_REQ, 'safety', SAFETY_90)
    done = run()
    assert done.exit_code == 0
    assert ID_UNDER in done.output and 'safety 90' in done.output

    # A dimension nothing raised is shown at its base, not left blank.
    assert 'security 10' in done.output


def test_a_key_naming_a_level_of_another_dimension_is_reported(tree, tmp_path):
    # The schema keys a criticality by dimension and says the entry
    # names the same one. Two places for one fact, and the second was
    # never read: safety could name a security level and the
    # derivation would give the item a security level under a safety
    # key.
    from conftest import clean

    _declare(tree, ID_REQ, 'safety', 'crit_security_60')
    found = [message for (id_check, message) in clean(tmp_path)
                     if id_check == 'requirement']
    assert any('is a security level' in m for m in found), found


def test_a_key_naming_a_level_of_its_own_dimension_is_not_reported(tree, tmp_path):
    from conftest import clean

    _declare(tree, ID_REQ, 'safety', SAFETY_60)
    assert [m for (id_check, m) in clean(tmp_path) if id_check == 'requirement'] == []
