"""
---

id_self:                pym_test.test_gate_tool
guid_self:              pym_3d0d3c58d6514d829598e79a51cc1c77
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Gate tool controls
brief:                  |
                        Runs each gate tool against a defect it is
                        meant to catch and asserts that the tool
                        fails.
description:            |
                        A tool that ran and exited zero has shown that
                        it ran. Whether it would have said anything
                        had there been something to say is a separate
                        question, and this is where it is answered.
                        One control per tool, each pointing the tool
                        at a known defect outside the tree so that the
                        repository never holds a broken file.
relation:               []

...
"""


import collections
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

import conftest


TYPE_ERROR = '''import typing


def statement(document: dict[str, typing.Any]) -> int:
    return ' '.join(str(document).split())
'''


def _mypy(text):
    """
    Run the configured type checker over one file holding text, outside
    the tree, and return what it did.

    """

    with tempfile.TemporaryDirectory() as name:
        filepath = pathlib.Path(name) / 'probe.py'
        filepath.write_text(text, encoding = 'utf-8')
        return subprocess.run(
                    [sys.executable, '-m', 'mypy', '--no-incremental',
                     '--python-version', '3.14', '--strict', str(filepath)],
                    cwd            = str(conftest.ROOT),
                    capture_output = True,
                    text           = True,
                    check          = False)


def test_the_type_checker_fails_on_a_wrong_return_type():
    # The defect mypy is in the gate to catch. Without this, a green
    # `pixi run type` says only that mypy ran.
    done = _mypy(TYPE_ERROR)
    assert done.returncode != 0
    assert 'return-value' in done.stdout


def test_the_type_checker_passes_what_is_right():
    # And it is not simply failing everything: the same shape, correct.
    done = _mypy(TYPE_ERROR.replace('-> int:', '-> str:'))
    assert done.returncode == 0, done.stdout


# Every statement of this runs when flag is true. The branch where the
# condition is false never does, which is exactly the difference between
# the two measurements and the reason for the migration.
#
COVERED = '''def taken(flag):
    answer = 'no'
    if flag:
        answer = 'yes'
    return answer
'''

EXERCISES_ONE_BRANCH = '''import probe


def test_one_way():
    assert probe.taken(True) == 'yes'
'''


def _coverage(floor, is_branch):
    """
    Run the suite of a tiny package outside the tree under a coverage
    floor, and return what it did.

    One function with one branch, and a test that takes it one way. The
    branch the test does not take is the defect the floor is here to
    notice.

    """

    with tempfile.TemporaryDirectory() as name:
        dirpath = pathlib.Path(name)
        (dirpath / 'probe.py').write_text(COVERED, encoding = 'utf-8')
        (dirpath / 'test_probe.py').write_text(EXERCISES_ONE_BRANCH,
                                               encoding = 'utf-8')

        # An empty config, so the probe does not inherit this
        # repository's pytest settings and measure this repository.
        (dirpath / 'probe.ini').write_text('[pytest]\n', encoding = 'utf-8')
        return subprocess.run(
                    [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                     '-c', str(dirpath / 'probe.ini'), str(dirpath),
                     '--cov=probe', '--cov-report=',
                     *(['--cov-branch'] if is_branch else []),
                     '--cov-fail-under=' + str(floor)],
                    cwd            = str(dirpath),
                    capture_output = True,
                    text           = True,
                    check          = False)


def test_the_coverage_floor_fails_when_coverage_is_under_it():
    # Without this, a green run says the floor was configured, not that
    # it would have stopped anything.
    done = _coverage(100, is_branch = True)
    assert done.returncode != 0
    assert 'Coverage failure' in done.stdout or 'Required test coverage' in done.stdout


def test_the_coverage_floor_passes_when_coverage_is_over_it():
    done = _coverage(50, is_branch = True)
    assert done.returncode == 0, done.stdout


def test_branch_measurement_sees_what_statement_measurement_does_not():
    # Every statement of taken() runs; the branch where the condition is
    # false never does. A floor of 100 passes without --cov-branch and
    # fails with it, which is the whole reason for the migration.
    assert _coverage(100, is_branch = False).returncode == 0
    assert _coverage(100, is_branch = True).returncode != 0


def test_the_packaging_smoke_tells_the_wheel_from_the_checkout():
    # The one thing the smoke exists to decide. cc_public is installed
    # editable, so the checkout is importable, and a smoke test that
    # merely imports it may be reading the tree the wheel was built
    # from. This is that judgement, exercised both ways.
    import package_smoke

    with tempfile.TemporaryDirectory() as name:
        elsewhere = pathlib.Path(name)
        assert package_smoke.is_inside(elsewhere / 'lib' / 'cc_public' / '__init__.py',
                                       elsewhere)
        assert not package_smoke.is_inside(conftest.ROOT / 'src' / 'cc_public' /
                                           '__init__.py', elsewhere)

    # And the negative it is guarding against: this interpreter has the
    # editable install, so what it imports is inside the repository.
    # A smoke run against an environment like this one must not pass.
    import cc_public

    assert package_smoke.is_inside(cc_public.__file__, conftest.ROOT)


# -----------------------------------------------------------------------------
# The three tools that were here before any of this and had nothing
# showing they could fail. Each is given the defect it is in the gate to
# catch, and then the same shape without it.

UNUSED_IMPORT = '''import json


def nothing():
    return 1
'''

# The house ignores UP032: format() is the house form. A run that
# reports it is a run that did not read the house configuration, which
# is the way a linter passes while looking at the wrong rules.
#
HOUSE_IGNORED = '''def greet(name):
    return 'hello {name}'.format(name = name)
'''


def _ruff(text):
    with tempfile.TemporaryDirectory() as name:
        filepath = pathlib.Path(name) / 'probe.py'
        filepath.write_text(text, encoding = 'utf-8')
        return subprocess.run(
                    [sys.executable, '-m', 'ruff', 'check',
                     '--config', str(conftest.ROOT / 'pyproject.toml'),
                     '--no-cache', str(filepath)],
                    capture_output = True, text = True, check = False)


def test_the_linter_fails_on_a_rule_it_selects():
    done = _ruff(UNUSED_IMPORT)
    assert done.returncode != 0
    assert 'F401' in done.stdout


def test_the_linter_passes_what_is_right():
    done = _ruff('def nothing():\n    return 1\n')
    assert done.returncode == 0, done.stdout


def test_the_linter_reads_the_house_configuration():
    # Not that it runs, but that it runs as configured here. A default
    # rule set would report UP032 on this and the house set does not.
    done = _ruff(HOUSE_IGNORED)
    assert done.returncode == 0, done.stdout
    assert 'UP032' not in done.stdout


CONTRACT = '''[tool.importlinter]
root_package = "probe_pkg"

[[tool.importlinter.contracts]]
name = "two tiers, importing downward only"
type = "layers"
layers = ["probe_pkg.high", "probe_pkg.low"]
'''


def _layers(is_broken):
    """
    Run the import linter over a package of two tiers.

    The lower tier imports the upper one where is_broken, which is the
    one thing a layers contract exists to refuse.

    """

    with tempfile.TemporaryDirectory() as name:
        dirpath = pathlib.Path(name)
        package = dirpath / 'probe_pkg'
        package.mkdir()
        (package / '__init__.py').write_text('', encoding = 'utf-8')
        (package / 'high.py').write_text('VALUE = 1\n', encoding = 'utf-8')
        (package / 'low.py').write_text(
            'import probe_pkg.high\n' if is_broken else 'VALUE = 2\n',
            encoding = 'utf-8')
        (dirpath / 'pyproject.toml').write_text(CONTRACT, encoding = 'utf-8')

        environment = dict(os.environ, PYTHONPATH = str(dirpath))
        return subprocess.run(
                    ['lint-imports', '--config', str(dirpath / 'pyproject.toml')],
                    cwd            = str(dirpath),
                    env            = environment,
                    capture_output = True, text = True, check = False)


def test_the_layering_contract_fails_on_an_upward_import():
    done = _layers(is_broken = True)
    assert done.returncode != 0
    assert 'BROKEN' in done.stdout.upper()


def test_the_layering_contract_passes_a_package_that_imports_downward():
    done = _layers(is_broken = False)
    assert done.returncode == 0, done.stdout + done.stderr


def _check(break_it = None):
    """
    Run the repository check over a copy of the tree, as the gate runs
    it, having first done break_it to that copy.

    The command and not the projection: a check can compute a finding
    correctly and still exit zero, and the gate believes the exit
    status.

    """

    with tempfile.TemporaryDirectory() as name:
        dirpath = pathlib.Path(name) / 'tree'
        dirpath.mkdir()
        conftest.copy_tree(dirpath)

        # The tests too. copy_tree leaves test/ out, and a case names a
        # test function in it, so a copy without them is not whole and
        # would fail the closed world for a reason of its own.
        shutil.copytree(conftest.ROOT / 'test', dirpath / 'test')
        if break_it is not None:
            break_it(dirpath)
        return subprocess.run(
                    ['cctool', 'check', '--closed-world',
                     '--fail-on-nonconformity', '--path', str(dirpath)],
                    capture_output = True, text = True, check = False)


ABSENT = 'term_' + '0' * 32


def _dangle(dirpath):
    """
    Point an edge at a guid nothing in the tree carries.

    The guid and not the readable id, because a reference resolves by
    guid: changing the id alone leaves the edge pointing where it
    always did.

    """

    filepath = dirpath / 'ddr' / 'ddr_gate_tool.yaml'
    text     = filepath.read_text(encoding = 'utf-8')
    line     = text.splitlines(keepends = True)
    found    = [i for (i, one) in enumerate(line) if 'guid_target:' in one]

    if not found:
        raise AssertionError('nothing to break in ' + str(filepath))

    (head, _) = line[found[0]].split('guid_target:', 1)
    line[found[0]] = '{head}guid_target:        {guid}\n'.format(head = head,
                                                                guid = ABSENT)
    filepath.write_text(''.join(line), encoding = 'utf-8')


def test_the_repository_check_passes_a_tree_that_is_whole():
    done = _check()
    assert done.returncode == 0, done.stdout[-2000:]


def test_the_repository_check_fails_a_reference_to_nothing():
    # The defect it is in the gate to catch. Eighteen checks run here
    # and this shows one of them reaching the exit status; the other
    # seventeen are not controlled by this.
    done = _check(_dangle)
    assert done.returncode != 0
    assert 'reference' in done.stdout.lower()


# -----------------------------------------------------------------------------
# One control per check. The command reaching a non zero exit is shown
# once, above; what these show is that each of the eighteen checks
# reports the defect it exists to find, and at what severity. A check
# that quietly stopped looking would pass every other test in this
# repository.

def _text(name, old, new):
    """
    Return a break that replaces old with new, once, in the file.

    """

    def break_it(dirpath):
        filepath = dirpath / name
        text     = filepath.read_text(encoding = 'utf-8')
        if text.count(old) != 1:
            raise AssertionError('{name} holds {n} of {old!r}'.format(
                            name = name, n = text.count(old), old = old))
        filepath.write_text(text.replace(old, new, 1), encoding = 'utf-8')

    return break_it


def _field(id_item, path, **kwargs):
    """
    Return a break that writes one field through the edit api.

    """

    def break_it(dirpath):
        import cc_public.edit.field
        import cc_public.edit.tree
        cc_public.edit.field.set_field(
            cc_public.edit.tree.Tree([dirpath]), id_item, path, **kwargs)

    return break_it


def _criticality(id_item, id_level):
    """
    Return a break that declares a criticality on a requirement.

    Declared here, in a copy, and never on a requirement of the tool
    itself: what a level should demand of the tool's own requirements
    is not settled, and declaring one to exercise a check would settle
    it by accident.

    """

    def break_it(dirpath):
        import cc_public.edit.field
        import cc_public.edit.tree
        tree = cc_public.edit.tree.Tree([dirpath])
        cc_public.edit.field.set_field(
            tree, id_item, 'criticality',
            value = {'safety': {'id_criticality':   id_level,
                                'guid_criticality': tree.resolve(id_level).guid_self}})

    return break_it


def _edge(id_source, id_relation, id_target, is_added = True):
    """
    Return a break that adds or removes one edge.

    """

    def break_it(dirpath):
        import cc_public.edit.link
        import cc_public.edit.tree
        tree = cc_public.edit.tree.Tree([dirpath])
        act  = cc_public.edit.link.link if is_added else cc_public.edit.link.unlink
        act(tree, id_source, id_relation, id_target)

    return break_it


def _unparseable(dirpath):
    (dirpath / 'ddr' / 'ddr_unparseable.yaml').write_text('id_self: [unclosed\n',
                                                          encoding = 'utf-8')


def _duplicate_guid(dirpath):
    borrowed = [one for one
                in (dirpath / 'ddr' / 'ddr_criticality.yaml').read_text().splitlines()
                if one.startswith('guid_self:')][0].split()[1]
    filepath = dirpath / 'ddr' / 'ddr_gate_tool.yaml'
    line     = filepath.read_text(encoding = 'utf-8').splitlines(keepends = True)
    for (index, one) in enumerate(line):
        if one.startswith('guid_self:'):
            line[index] = 'guid_self:              {guid}\n'.format(guid = borrowed)
            break
    filepath.write_text(''.join(line), encoding = 'utf-8')


def _no_evidence(dirpath):
    (dirpath / 'evidence' / 'evd_pytest.yaml').unlink()


def _decided_then_changed(dirpath):
    import cc_public.edit.decide
    import cc_public.edit.field
    import cc_public.edit.tree

    tree = cc_public.edit.tree.Tree([dirpath])
    cc_public.edit.decide.decide(
            tree, 'accept', ['req_printer_idempotent'],
            {'actor': 'A person', 'role': 'Engineer', 'authority': 'This control'},
            'Decided, so that the subject may then be changed under it.')
    cc_public.edit.field.set_field(
            cc_public.edit.tree.Tree([dirpath]), 'req_printer_idempotent', 'rationale',
            prose = 'Reworded after the decision, so the digest no longer matches.')


def _second_segment(dirpath):
    """
    Make a second segment beside the core and have the core name
    something inside it.

    A reference may run into a segment its own consumes, never the
    other way, and the core consumes nothing.

    """

    import re
    import uuid

    import cc_public.edit.link
    import cc_public.edit.tree

    def reseat(source, target, prefix, id_new):
        text = source.read_text(encoding = 'utf-8')
        text = re.sub(r'^id_self: +\S+', 'id_self:                ' + id_new,
                      text, count = 1, flags = re.MULTILINE)
        text = re.sub(r'^guid_self: +\S+',
                      'guid_self:              {p}_{h}'.format(p = prefix,
                                                               h = uuid.uuid4().hex),
                      text, count = 1, flags = re.MULTILINE)
        for block in ('relation:', 'question:'):
            text = re.sub(r'^' + block + r'.*?(?=^\w|\Z)',
                          'relation:               []\n\n' if block == 'relation:' else '',
                          text, count = 1, flags = re.MULTILINE | re.DOTALL)
        target.parent.mkdir(parents = True, exist_ok = True)
        target.write_text(text, encoding = 'utf-8')

    reseat(dirpath / 'segment' / 'seg_cc_public.yaml',
           dirpath / 'probe' / 'segment' / 'seg_probe.yaml', 'seg', 'seg_probe')
    reseat(dirpath / 'ddr' / 'ddr_gate_tool.yaml',
           dirpath / 'probe' / 'ddr' / 'ddr_probe.yaml', 'ddr', 'ddr_probe')

    cc_public.edit.link.link(cc_public.edit.tree.Tree([dirpath]),
                             'ddr_criticality', 'r_decides', 'ddr_probe')


# The defect each check is here to find, and what it says about it.
# Severity is part of the control: layout, decision and confidence
# report and do not stop the gate, and that is a fact about them worth
# holding to.
#
BROKEN = [
 ('parse',       'critical', _unparseable,                    'while parsing'),
 ('guid',        'critical', _duplicate_guid,                 'is already declared'),
 ('identifier',  'critical', _text('ddr/ddr_gate_tool.yaml',
                                   'id_self:                ddr_gate_tool',
                                   'id_self:                ddr_Gate_Tool'),
                                                              'does not match'),
 ('source',      'critical', _text('src/cc_public/query.py',
                                   'pyf_cc_public.query.database.path\n',
                                   'pyf_cc_public.query.database.wrongname\n'),
                                                              'named by where it sits'),
 ('reference',   'critical', _dangle,                         'Reference to'),
 ('segment',     'critical', _second_segment,                 'does not consume it'),
 ('relation',    'critical', _edge('need_layout_stable', 'r_is_implemented_by',
                                   'pym_cc_public.layout'),   'edge runs from'),
 ('schema',      'critical', _text('ddr/ddr_criticality.yaml',
                                   'title:', 'undeclared_field:      x\ntitle:'),
                                                              'Unevaluated properties'),
 ('requirement', 'critical', _field('req_printer_idempotent', 'process',
                                    value = 'frobnicate'),    'process word'),
 ('statement',   'critical', _field('req_printer_idempotent', 'qualifier',
                                    value = 'in no more than 5'),
                                                              'followed by no unit'),
 ('decision',    'advisory', _decided_then_changed,           'has changed since'),
 ('layout',      'advisory', _text('ddr/ddr_gate_tool.yaml',
                                   'title:                  ', 'title: '),
                                                              'Not laid out'),
 ('workflow',    'critical', _text('workflow/wf_accept_requirement.yaml',
                                   'guid_target:    cmp_469a5534091a49f2b3a0d7532e17907b',
                                   'guid_target:    cmp_' + '0' * 32),
                                                              'Names no component'),
 ('interface',   'critical', _text('interface/icd_cc_public_query.yaml',
                                   'id_self:      icm_cc_public_query.database\n',
                                   'id_self:      icm_cc_public_query.absent\n'),
                                                              'what holds it says'),
 ('testing',     'critical', _field('tc_path_reported', 'configuration',
                                    value = {'not_a_declared_key': 'nonsense'}),
                                                              'required property'),
 ('trace',       'critical', _edge('req_printer_idempotent', 'r_is_implemented_by',
                                   'pym_cc_public.layout', is_added = False),
                                                              'nothing implements it'),
 ('trace',       'critical', _criticality('req_printer_idempotent',
                                            'crit_safety_40'),
                                                              'analysed and recorded'),
 ('evidence',    'critical', _no_evidence,                    'no evidence by'),
 ('confidence',  'advisory', _field('evl_test_exercises_criteria', 'criterion',
                                    prose = 'Something else entirely is asked here.'),
                                                              'since changed'),
]


def _identifier(table):
    """
    Return a readable pytest id per row, numbering only where a check
    is here for more than one defect.

    """

    seen = collections.Counter(row[0] for row in table)
    made = collections.Counter()
    out  = []

    for row in table:
        made[row[0]] += 1
        out.append(row[0] if seen[row[0]] == 1 else
                   '{name}{n}'.format(name = row[0], n = made[row[0]]))

    return out


@pytest.mark.parametrize(('id_check', 'severity', 'break_it', 'says'), BROKEN,
                         ids = _identifier(BROKEN))
def test_each_check_reports_the_defect_it_is_here_to_find(id_check, severity,
                                                          break_it, says, tmp_path):
    import cc_public.check

    dirpath = tmp_path / 'tree'
    dirpath.mkdir()
    conftest.copy_tree(dirpath)
    shutil.copytree(conftest.ROOT / 'test', dirpath / 'test')
    break_it(dirpath)

    report = cc_public.check.check(list_path = [dirpath],
                                   is_closed_world = True)['report']
    found  = [(one['severity'], ' '.join(one['message'].split()))
              for check in report['check'] if check['id_check'] == id_check
              for one in check['nonconformity']]

    assert found, '{check} reported nothing'.format(check = id_check)
    assert any(severity == s and says in m for (s, m) in found), found[:3]
