"""
---

id_self:                pym_test.test_coverage_analysis
guid_self:              pym_386ec523169f4444bc1b472931260825
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Coverage analysis tests
brief:                  |
                        Tests that a criticality requiring the
                        coverage objective asks for an analysis, and
                        that an analysis stands only while what it
                        read is unchanged.
description:            |
                        Every criticality here is declared on a
                        requirement in a copy of the tree and never on
                        a real one. What a level demands of the tool's
                        own requirements is not settled, and declaring
                        one to exercise a check would settle it by
                        accident.
relation:               []

...
"""


import cc_public.check
import cc_public.check.trace
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load
import cc_public.testing
import cc_public.trace
from conftest import DEFAULTS, clean


ID_REQ   = 'req_path_reported'
JUDGE    = 'openai/gpt-5.1'
LEVEL_40 = 'crit_safety_40'
LEVEL_10 = 'crit_safety_10'
ID_EVAL  = 'evl_test_exercises_criteria'


def _declare(tree, id_level):
    cc_public.edit.field.set_field(
        tree, ID_REQ, 'criticality',
        value = {'safety': {'id_criticality':   id_level,
                            'guid_criticality': tree.resolve(id_level).guid_self}})


BODY = ("\n\ndef test_probe():\n"
        '    """\n    Proves it.\n\n    """\n'
        "    if 1 + 1 != 2:\n        raise AssertionError('no')\n")


def _verifier(tree):
    """
    Put a test function into the tree and make it verify the
    requirement, returning its id.

    The copy holds no test directory, so the functions that verify the
    tool's requirements are not in it. One written here is code this
    tree holds, which is what an analysis must be able to read.

    """

    id_verifier = 'pyf_cc_public.probe.test_probe'

    if tree.context.map_document.get(tree.resolve(ID_REQ).location) is None:
        raise AssertionError('the requirement is not in this tree')

    cc_public.edit.new.new(tree, 't_python_module', 'pym_cc_public.probe', DEFAULTS)
    for (field, text) in (('title', 'Probe'), ('brief', 'A stand-in.'),
                          ('description', 'Holds a stand-in for a test.')):
        cc_public.edit.field.set_field(tree, 'pym_cc_public.probe', field, value = text)

    path = tree.root / 'src' / 'cc_public' / 'probe.py'
    path.write_text(path.read_text(encoding = 'utf-8') + BODY, encoding = 'utf-8')

    tree = cc_public.edit.tree.Tree([tree.root])
    cc_public.edit.new.new(tree, 't_python_function', id_verifier, DEFAULTS)
    cc_public.edit.field.set_field(tree, id_verifier, 'title', value = 'Probe')
    cc_public.edit.field.set_field(tree, id_verifier, 'description',
                                   prose = 'A stand-in for a test.')
    cc_public.edit.link.link(tree, id_verifier, 'r_verifies', ID_REQ)

    return id_verifier


def _analysis(tree, verdict = 'met', digest = None, feedback = 'Both halves are caught.'):
    """
    Write a coverage analysis naming the requirement and its verifier.

    """

    id_verifier = _verifier(tree)
    tree        = cc_public.edit.tree.Tree([tree.root])
    document    = tree.context.map_document[tree.resolve(ID_REQ).location]
    text        = cc_public.check.trace._source_of(tree.context.map_document, id_verifier)

    cc_public.edit.new.new(tree, 't_coverage_analysis', 'cva_probe', DEFAULTS)
    for (field, value) in (('title',      'Probe analysis'),
                           ('id_eval',    ID_EVAL),
                           ('guid_eval',  tree.resolve(ID_EVAL).guid_self),
                           ('judge',      JUDGE),
                           ('time',       '2026-09-11T09:00:00Z')):
        cc_public.edit.field.set_field(tree, 'cva_probe', field, value = value)
    for (field, value) in (('brief',       'What a judge read.'),
                           ('description', 'A stand-in analysis, written by a test.')):
        cc_public.edit.field.set_field(tree, 'cva_probe', field, prose = value)

    cc_public.edit.field.set_field(
            tree, 'cva_probe', 'confidence',
            value = {'false_positive': 0.0, 'false_negative': 0.167, 'unanimous': 1.0})
    cc_public.edit.field.set_field(
            tree, 'cva_probe', 'analysis',
            value = {'c0': {'id_requirement':   ID_REQ,
                            'guid_requirement': tree.resolve(ID_REQ).guid_self,
                            'id_verifier':      id_verifier,
                            'guid_verifier':    tree.resolve(id_verifier).guid_self,
                            'verdict':          verdict,
                            'feedback':         feedback,
                            'digest':           digest or cc_public.check.trace.digest_of(
                                                                    document, text),
                            'time':             '2026-09-11T09:00:00Z'}})

    return (id_verifier, cc_public.edit.tree.Tree([tree.root]))


def _said(tmp_path):
    """
    Return the trace check's advisory messages. clean reports only
    what is critical, and an unmet reading is advisory by design.

    """

    report = cc_public.check.check(list_path = [tmp_path])['report']

    return [n['message'] for c in report['check'] if c['id_check'] == 'trace'
            for n in c['nonconformity'] if n['severity'] == 'advisory']


def _gap(tmp_path, path_wanted = 'verification'):
    context = cc_public.check.context([tmp_path])[0]
    record  = [r for r in cc_public.trace.projection(
                                context.map_document, False,
                                cc_public.check.trace.analysed(context.map_document))
                 if r.id_self == ID_REQ][0]

    return [g for g in record.gap
              if g.path == path_wanted and 'analysed and recorded' in g.message]


def test_a_level_that_requires_the_objective_asks_for_an_analysis(tree, tmp_path):
    assert _gap(tmp_path) == []

    _declare(tree, LEVEL_40)
    (gap,) = _gap(tmp_path)
    assert gap.severity == 'critical'
    assert 'no current analysis names it' in gap.message


def test_a_level_that_does_not_require_it_asks_for_nothing(tree, tmp_path):
    # The register decides, not the check: the base level requires
    # three objectives and this is not one of them.
    _declare(tree, LEVEL_10)
    assert _gap(tmp_path) == []


def test_an_analysis_of_what_the_level_asks_about_closes_the_gap(tree, tmp_path):
    _declare(tree, LEVEL_40)
    _analysis(tree)
    assert _gap(tmp_path) == []
    assert clean(tmp_path) == []


def test_an_analysis_stops_standing_when_the_criteria_change(tree, tmp_path):
    _declare(tree, LEVEL_40)
    _analysis(tree)
    assert _gap(tmp_path) == []

    cc_public.edit.field.set_field(tree, ID_REQ, 'success_criteria',
                                   prose = 'Something else entirely is shown.')
    assert len(_gap(tmp_path)) == 1


def test_an_analysis_stops_standing_when_the_test_changes(tree, tmp_path):
    # What was read is the criteria and the source of the test. A
    # changed test is a test nobody has read against these criteria.
    _declare(tree, LEVEL_40)
    (id_verifier, _) = _analysis(tree)
    assert _gap(tmp_path) == []

    location = cc_public.testing.locate(
                        cc_public.check.context([tmp_path])[0].map_document, id_verifier)
    location.filepath.write_text(
            location.filepath.read_text(encoding = 'utf-8').replace(
                    '1 + 1 != 2', '1 + 1 != 3', 1), encoding = 'utf-8')
    assert len(_gap(tmp_path)) == 1


def test_an_analysis_naming_a_verifier_this_tree_lacks_stands_for_nothing(tree, tmp_path):
    _declare(tree, LEVEL_40)
    (_, tree) = _analysis(tree)
    cc_public.edit.field.set_field(tree, 'cva_probe', 'analysis.c0.id_verifier',
                                   value = 'pyf_test.test_nothing.test_absent')
    assert len(_gap(tmp_path)) == 1


def test_an_unmet_reading_is_reported_advisory_with_the_judge_and_its_rates(tree,
                                                                           tmp_path):
    # A judge is not a check, so what it answered is advisory whatever
    # the requirement's status, and what it rests on is written beside
    # it rather than left for a reader to go and find.
    _analysis(tree, verdict = 'unmet',
              feedback = 'Nothing would catch the absence of a path.')
    (said,) = [m for m in _said(tmp_path) if 'could pass while' in m]
    assert JUDGE in said
    assert 'false positive rate of 0.0' in said
    assert 'false negative rate of 0.167' in said
    assert 'Nothing would catch the absence of a path.' in said


def test_an_unmet_reading_of_something_changed_since_is_not_reported(tree, tmp_path):
    _analysis(tree, verdict = 'unmet', digest = 'deadbeef')
    assert not [m for m in _said(tmp_path) if 'could pass while' in m]
