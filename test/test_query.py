"""
---

id_self:                pym_test.test_query
guid_self:              pym_d9abbeb361c24cae8b6a38fb1475bc67
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Query tests
brief:                  |
                        The facts hold everything the tree states, and
                        the graph is walked, pathed, drawn and queried
                        as the requirements say.
description:            |
                        One test per requirement of the graph query
                        tool: the fact counts against the checks'
                        counts, the neighbourhood by depth, relation
                        and direction, the shortest path and its
                        absence, orphans appearing and vanishing with
                        an edge, a named query and typed SQL, and a
                        drawing in both formats.
relation:               []

...
"""


import json
import sqlite3

import click.testing
import pytest

import cc_public.check
import cc_public.check.identifier
import cc_public.cli.command
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.facts
import cc_public.query
import cc_public.testing
from conftest import DEFAULTS


def run(*args):
    return click.testing.CliRunner().invoke(cc_public.cli.command.main, list(args))


def test_facts_hold_every_identity_edge_and_containment_of_the_tree(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_facts_hold_every_identity_edge_and_containment_of_the_tree
    guid_self:              pyf_a020228dedcc49f9a1d6d0a0f73b3d69
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  The facts hold every identity, edge and containment
    brief:                  |
                            The facts hold every identity, edge and
                            containment.
    description:            |
                            Counts item facts against the guid check, edge
                            facts against the relation edges of identified
                            items, and containment facts against the
                            identifier check's embedded identities.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_facts_derived_from_tree
        guid_target:        req_9de1607f8b5b4f898065765d36db499a

    ...
    """

    facts  = cc_public.facts.facts(tree.context.map_document)
    report = cc_public.check.check(list_path = [tmp_path])['report']
    count  = {c['id_check']: c['count_item'] for c in report['check']}
    assert len(facts.item) == count['guid']

    def edges(node):
        if isinstance(node, dict):
            own = [e for e in (node.get('relation') or []) if isinstance(e, dict)] \
                  if isinstance(node.get('guid_self'), str) else []
            return len(own) + sum(edges(v) for v in node.values())
        return sum(edges(v) for v in node) if isinstance(node, list) else 0

    assert len(facts.edge) == sum(edges(d) for d in tree.context.map_document.values())
    embedded = {guid for d in tree.context.map_document.values()
                     for (path, _, guid) in cc_public.check.identifier.iter_identity(d)
                     if path and guid}
    held = {c.guid_held for c in facts.containment}
    assert embedded == held and len(held) == len(facts.containment)
    one = next(i for i in facts.item if i.id_self == 'req_printer_idempotent')
    assert one.prefix == 'req' and one.status == 'accepted' and one.location.endswith('.yaml')


def test_walk_reports_the_neighbourhood_to_a_depth_along_named_relations(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_walk_reports_the_neighbourhood_to_a_depth_along_named_relations
    guid_self:              pyf_21b4438010a1409fb36ac1cf6b0a54e2
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Walk reports the neighbourhood to a depth along named relations
    brief:                  |
                            Walk reports the neighbourhood to a depth
                            along named relations.
    description:            |
                            Walks a requirement to depths one and two, in
                            one direction and both, with and without a
                            relation named, and asserts what is reached
                            and by what.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_walk_reports_neighbourhood
        guid_target:        req_f954bd2cda2344d98ed5b1faa3d9fe99

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_walk_follows_named_relations
        guid_target:        req_9d975348164e4650addf5f56118e4182

    ...
    """

    db = cc_public.query.Database(tree.context.map_document)
    one = db.walk('req_printer_idempotent', 1)
    ids = {s.id_self for s in one}
    assert {'req_printer_idempotent', 'need_layout_stable', 'pym_cc_public.layout'} <= ids
    assert all(s.depth == 1 for s in one if s.id_from is not None)
    assert next(s for s in one if s.id_self == 'need_layout_stable').id_relation == 'r_is_derived_from'
    two = db.walk('req_printer_idempotent', 2)
    assert {s.id_self for s in two} > ids
    assert {s.depth for s in two} == {0, 1, 2}
    only = db.walk('req_printer_idempotent', 2, ['r_is_derived_from'])
    assert all(s.id_relation == 'r_is_derived_from' for s in only if s.id_from is not None)
    assert 'pym_cc_public.layout' not in {s.id_self for s in only}
    assert db.walk('req_printer_idempotent', 1, (), ('out',)) and \
           all(s.direction == 'out' for s in db.walk('req_printer_idempotent', 3, (), ('out',))
               if s.id_from is not None)
    assert db.walk('nothing_here', 1) is None


def test_a_shortest_path_is_reported_or_its_absence(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_a_shortest_path_is_reported_or_its_absence
    guid_self:              pyf_5c4024f5802f43288d79090a75539c0f
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A shortest path is reported, or its absence
    brief:                  |
                            A shortest path is reported, or its absence.
    description:            |
                            Joins two items by routes of two and three
                            edges and asserts the shorter is reported,
                            then asks for a path to an item in its own
                            component and gets none.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_path_reported
        guid_target:        req_628a90f901f14926bf38dc2d29c523b8

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_no_path_reported
        guid_target:        req_d0b64a53c3474cc6911af0fe0472ab7a

    ...
    """

    db = cc_public.query.Database(tree.context.map_document)
    # a three-edge route exists too: requirement -> layout module <- ... ; the two-edge one wins
    cc_public.edit.link.link(tree, 'ddr_fail_closed', 'r_decides', 'pym_cc_public.layout')
    db = cc_public.query.Database(tree.context.map_document)
    step = db.path('need_layout_stable', 'ddr_fail_closed')
    assert [s.id_self for s in step][0] == 'need_layout_stable' and step[-1].id_self == 'ddr_fail_closed'
    assert len(step) == 4                         # need <- req -> layout <- decision
    cc_public.edit.new.new(tree, 't_ddr', 'ddr_alone', DEFAULTS)
    db = cc_public.query.Database(tree.context.map_document)
    assert db.path('ddr_alone', 'need_layout_stable') == []
    assert db.path('nothing', 'need_layout_stable') is None


def test_orphans_are_what_nothing_points_at(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_orphans_are_what_nothing_points_at
    guid_self:              pyf_99975b7fe6b148eba051aed4f49a66cc
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Orphans are what nothing points at
    brief:                  |
                            Items nothing points at are listed, and stop
                            being listed once something points at them.
    description:            |
                            Makes an item nothing points at, sees it
                            listed, points at it and sees it gone.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_unreferenced_items_listed
        guid_target:        req_c2a686dc37e340e08f4ceb8631af75d7

    ...
    """

    db = cc_public.query.Database(tree.context.map_document)
    (before_item, _) = db.orphans()
    cc_public.edit.new.new(tree, 't_ddr', 'ddr_alone', DEFAULTS)
    db = cc_public.query.Database(tree.context.map_document)
    (after_item, _) = db.orphans()
    assert 'ddr_alone' in after_item and 'ddr_alone' not in before_item
    cc_public.edit.link.link(tree, 'ddr_fail_closed', 'r_decides', 'ddr_alone')
    db = cc_public.query.Database(tree.context.map_document)
    assert 'ddr_alone' not in db.orphans()[0]


def test_unused_relations_are_what_no_edge_names(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_unused_relations_are_what_no_edge_names
    guid_self:              pyf_685a0ef345f7478889f184378f10284a
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Unused relations are what no edge names
    brief:                  |
                            Relations no edge uses are listed, and each
                            listed one is a relation.
    description:            |
                            Reads the second half of what orphans reports
                            and asserts every entry in it is a relation.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_unused_relations_listed
        guid_target:        req_334b1654059748bcb18938201b6a9a27

    ...
    """

    map_document = tree.context.map_document
    (_, unused)  = cc_public.query.Database(map_document).orphans()

    # What every relation the register declares, less every relation an
    # edge is labelled with. Computed here rather than read from the
    # same place the query reads it, so the two can disagree.
    declared = {name for document in map_document.values()
                     if isinstance(document, dict)
                     and str(document.get('id_self', '')) == 'reg_relation'
                     for name in document['table']}
    labelled = {edge['id_relation']
                for item in cc_public.testing.index(map_document).values()
                for edge in item.get('relation') or []
                if isinstance(edge, dict) and 'id_relation' in edge}

    assert declared
    assert set(unused) == declared - labelled
    assert all(r.startswith('r_') for r in unused)

    # And it leaves the list once an edge is labelled with it. The list
    # is a fact about the documents, so labelling one edge is the change
    # the criteria describe. Written into the loaded document rather
    # than through link, since what is tested is what the query reports
    # and not what the relation register admits.
    taken  = min(unused)
    holder = next(document for document in map_document.values()
                  if isinstance(document, dict)
                  and document.get('id_self') == 'req_unused_relations_listed')
    holder.setdefault('relation', []).append(
        {'id_relation':   taken,
         'guid_relation': 'r_' + '0' * 32,
         'id_target':     'req_unused_relations_listed',
         'guid_target':   holder['guid_self']})

    (_, after) = cc_public.query.Database(map_document).orphans()
    assert taken not in after
    assert set(after) == set(unused) - {taken}


def test_a_named_query_runs_over_the_facts(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_a_named_query_runs_over_the_facts
    guid_self:              pyf_20cb93a9f39946938572d2a437f82758
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A named query runs over the facts
    brief:                  |
                            A named query runs over the facts.
    description:            |
                            Runs the counting query and reads back the
                            count of item facts, runs a query by name and
                            SQL typed at the command line, and sees bad
                            SQL refused.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_named_query_run
        guid_target:        req_3c672d6e90e844239e61eebc5dab157c

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_typed_query_run
        guid_target:        req_5ffe40ced6b7489ca3b37c3b9ec20af2

    ...
    """

    db = cc_public.query.Database(tree.context.map_document)
    sql = cc_public.query.named(tree.context.map_document, 'qry_count_items')
    (names, rows) = db.run(sql)
    assert names == ['items'] and rows == [(len(db.facts.item),)]
    assert cc_public.query.named(tree.context.map_document, 'qry_nothing') is None
    out = run('query', '--root', str(tmp_path), 'qry_decides_most', '--format', 'json')
    assert out.exit_code == 0, out.output
    rows = json.loads(out.output)
    assert rows[0]['decided'] >= rows[-1]['decided'] and 'decision' in rows[0]
    out = run('query', '--root', str(tmp_path), '--sql', 'SELECT COUNT(*) AS n FROM edge')
    assert out.exit_code == 0 and 'n' in out.output
    assert run('query', '--root', str(tmp_path), '--sql', 'SELECT * FROM nowhere').exit_code == 2


def test_every_named_query_runs(tree):
    """
    Every query item in the tree runs over its facts without error, so
    a change to the fact tables that breaks one is found here and not
    by the reader who next runs it.

    """

    map_document = tree.context.map_document
    database     = cc_public.query.Database(map_document)
    list_query   = sorted(name for name in tree.map_id if name.startswith('qry_'))
    assert list_query
    for name in list_query:
        (columns, rows) = database.run(cc_public.query.named(map_document, name))
        assert columns, name
        assert isinstance(rows, list), name


def test_a_neighbourhood_is_drawn_in_dot_and_in_mermaid(tree, tmp_path):
    """
    ---

    id_self:                pyf_test.test_query.test_a_neighbourhood_is_drawn_in_dot_and_in_mermaid
    guid_self:              pyf_a76a6f6e437e4a18ab51a12c6d970f6e
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A neighbourhood is drawn in dot and in mermaid
    brief:                  |
                            A neighbourhood is drawn in dot and in
                            mermaid.
    description:            |
                            Draws a walk in both formats and asserts every
                            item is a node and every reaching edge a
                            labelled edge.

    relation:

      - id_relation:        r_verifies
        guid_relation:      r_490096e908d1444cb0defb530fcf7786
        id_target:          req_neighbourhood_drawn
        guid_target:        req_389dd46b64ba45598a0006556b88c2c3

    ...
    """

    db   = cc_public.query.Database(tree.context.map_document)
    step = db.walk('req_printer_idempotent', 1)
    dot  = cc_public.query.drawing(step, 'dot')
    assert dot.startswith('digraph {') and dot.rstrip().endswith('}')
    for s in step:
        assert '"{id}"'.format(id = s.id_self) in dot
    assert dot.count('->') == len(step) - 1 and '[label="r_is_derived_from"]' in dot
    mermaid = cc_public.query.drawing(step, 'mermaid')
    assert mermaid.startswith('graph LR') and mermaid.count('-->') == len(step) - 1
    assert '|r_is_derived_from|' in mermaid

    # Every edge of the neighbourhood is drawn, not only the edges the
    # walk reached each item by: the two judge requirements of one need
    # share their functions, which a walk reaches once, by one of them.
    step  = db.walk('need_trustworthy_judgement', 2)
    among = db.edges_among(step)
    ids   = {s.id_self for s in step}
    assert all(a in ids and b in ids for (a, b, _) in among)
    for req in ('req_judge_confirms_unmet', 'req_judge_reports_confirmed_verdict'):
        assert (req, 'pyf_cc_public.eval.check.check', 'r_is_implemented_by') in among
    assert cc_public.query.drawing(step, 'dot', among).count('->') == len(among) > len(step) - 1
    out = run('walk', '--root', str(tmp_path), 'need_layout_stable', '--format', 'mermaid')
    assert out.exit_code == 0 and out.output.startswith('graph LR')
    out = run('path', '--root', str(tmp_path), 'need_layout_stable', 'pym_cc_public.layout')
    assert out.exit_code == 0 and 'pym_cc_public.layout' in out.output
    out = run('orphans', '--root', str(tmp_path))
    assert out.exit_code == 0 and 'relation(s) nothing uses' in out.output


def test_the_facts_are_open_for_reading_alone(tree, tmp_path):
    # The run member's obligation says the query is read only, and an
    # obligation is what the provider must do. Over the tree, DELETE
    # FROM item returned an empty result and the item count fell to
    # zero.
    import cc_public.check
    import cc_public.query

    context = cc_public.check.context([tmp_path])[0]
    db      = cc_public.query.Database(context.map_document)
    before  = db.run('SELECT count(*) FROM item')[1]

    with pytest.raises(sqlite3.OperationalError):
        db.run('DELETE FROM item')

    assert db.run('SELECT count(*) FROM item')[1] == before
    db.close()


def test_a_walk_of_a_name_the_tree_does_not_hold_is_absent(tree, tmp_path):
    # The member says list[Step] | None, and said list[Step] while
    # returning None, so a caller iterating the result raised on a typo.
    import cc_public.check
    import cc_public.query

    context = cc_public.check.context([tmp_path])[0]
    db      = cc_public.query.Database(context.map_document)

    assert db.walk('req_no_such_requirement') is None
    assert db.walk('req_path_reported') is not None
    db.close()
