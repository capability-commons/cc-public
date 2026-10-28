"""
---

id_self:                pym_cctool.gate._test.test_coverage
guid_self:              pym_714a53ed5487473fbe48a5e6b6698eb9
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Coverage tests
brief:                  |
                        Tests of the check of coverage against the
                        maturity of each source file.
description:            |
                        Each test writes a module of its own into a
                        copy of the repository, at a maturity it
                        declares, runs part of it under coverage in a
                        process of its own, so that a run of these
                        tests under coverage is not disturbed, and
                        checks the coverage the run measured.
edge:                   []

...
"""


import os
import re
import subprocess
import sys

import pytest

import cctool.gate.coverage


pytest.importorskip('coverage')

pytestmark = pytest.mark.reads_data

MODULE = '''"""
---
id_self: pym_x.y
guid_self: pym_{hex}
copyright: Copyright 2026 William Payne
license: Apache-2.0
protective_mark:
- id_mark: mark_public
  guid_mark: mark_0c96ccb7b7534574acf6ed42f9deba0f
title: Test module
brief: A test module.
description: A test module.
edge: {edge}
...
"""


def used(flag):
    if flag:
        return 1
    return 2


def unused():
    total = 0
    for each in range(3):
        total += each
    return total


used(__name__ == '__main__')
'''

EDGE = '''
- id_relation: relation_has_maturity
  guid_relation: {relation}
  id_target: {level}
  guid_target: {guid}'''


# -----------------------------------------------------------------------------
def _guid_of(root, id_self):
    """
    Return the guid of the item with id_self in the registers of root.

    """

    regex = re.compile(r'id_self:\s+{id}\n\s*guid_self:\s+(\S+)'.format(id = re.escape(id_self)))
    for path in sorted((root / '_data' / 'register').glob('*.yaml')):
        match = regex.search(path.read_text())
        if match:
            return match.group(1)
    raise KeyError(id_self)


# -----------------------------------------------------------------------------
def _measured(root, level = None, is_run = True):
    """
    Write the module x.y at level, or with no maturity if level is None,
    run it under coverage if is_run, or only a module of the standard library if not,, and return the path
    of the coverage data.

    """

    edge = '[]' if level is None else EDGE.format(relation = _guid_of(root, 'relation_has_maturity'),
                                                    level    = level,
                                                    guid     = _guid_of(root, level))
    path = root / 'src' / 'x' / 'y.py'
    path.parent.mkdir(parents = True)
    (path.parent / '__init__.py').write_text('')
    path.write_text(MODULE.format(hex = '0' * 32, edge = edge))
    path_data = root / '.coverage'
    subprocess.run([sys.executable, '-m', 'coverage', 'run', '--branch',
                    '--data-file', str(path_data), '-m', 'x.y' if is_run else 'this'],
                   cwd = root, check = True, capture_output = True,
                   env = {**os.environ, 'PYTHONPATH': str(root / 'src')})
    return path_data


def test_the_coverage_a_run_measured_is_read_in_a_thousand(tree):
    set_row = cctool.gate.coverage.measured(tree, _measured(tree))
    assert {row[1:] for row in set_row if row[0] == 'src/x/y.py'} == {('line', '500'),
                                                                     ('branch', '250')}


def test_a_file_below_the_floor_of_its_maturity_is_reported(tree):
    [branch, line, fix] = cctool.gate.coverage.check(tree, _measured(tree, 'maturity_60'))
    assert branch == ('src/x/y.py: coverage_below_floor: src/x/y.py has branch coverage of 250 '
                      'in a thousand, below the floor of 700 in a thousand that its maturity '
                      'sets.')
    assert 'has line coverage of 500 in a thousand, below the floor of 800' in line
    assert fix.startswith('  fix: Write the tests')


def test_a_file_at_a_level_with_no_floor_passes(tree):
    assert cctool.gate.coverage.check(tree, _measured(tree, 'maturity_40')) == []


def test_a_file_that_declares_no_maturity_passes(tree):
    assert cctool.gate.coverage.check(tree, _measured(tree)) == []


def test_a_file_the_run_did_not_measure_is_covered_by_none(tree):
    list_line = cctool.gate.coverage.check(tree, _measured(tree, 'maturity_80', is_run = False))
    assert [line.split(' in a')[0].split(': ', 1)[1] for line in list_line[:2]] == [
        'coverage_below_floor: src/x/y.py has branch coverage of 0',
        'coverage_below_floor: src/x/y.py has line coverage of 0']


def test_no_data_says_how_to_make_it(tree):
    with pytest.raises(cctool.gate.coverage.ErrorCoverage, match = 'coverage run --branch'):
        cctool.gate.coverage.check(tree, tree / '.coverage')
