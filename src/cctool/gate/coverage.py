"""
---

id_self:                pym_cctool.gate.coverage
guid_self:              pym_5dd48e5117b44306bde3d8d830721fcc
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Coverage against maturity
brief:                  |
                        Compare the coverage that a run of the tests
                        measured of each source file with the floor
                        that its maturity level sets.
description:            |
                        The data file that coverage run writes is read
                        through the JSON report of coverage, so only
                        its public interface is used. The lines and
                        branches covered of each file become facts of
                        measured_coverage, in a thousand, beside the
                        facts of the tree, for the rule of
                        lpf_cctool.gate.coverage alone, and nothing
                        measured is kept. A file with no branches is
                        covered in full for branches. The run is too
                        slow for a gate, so it is made overnight, as
                        the ruling on how coverage is checked asks.
usage:                  |
                        pixi run coverage, or cctool coverage once the
                        tests have run under coverage run --branch.
edge:                   []

...
"""


import json
import pathlib
import tempfile

import cctool.graph.extract
import cctool.graph.logic


RULES          = pathlib.Path(__file__).with_name('coverage.lp')
NAME_MEASURED  = 'measured_coverage'
FILE_DATA      = '.coverage'

# The columns of the measured coverage, which is not a base predicate.
#
MAP_MEASURED   = {NAME_MEASURED: (('file',     'symbol'),
                                  ('kind',     'symbol'),
                                  ('measured', 'number'))}

KIND_LINE      = 'line'
KIND_BRANCH    = 'branch'
PER            = 1000


# -----------------------------------------------------------------------------
class ErrorCoverage(Exception):
    """
    The coverage cannot be read or compared.

    """


# -----------------------------------------------------------------------------
def check(root: pathlib.Path, path_data: pathlib.Path) -> list[str]:
    """
    Return a line for each source file under root whose coverage, as
    the data file at path_data records it, is below the floor its
    maturity sets, and then what to do about it, or no lines if none
    is.

    """

    facts                = cctool.graph.extract.extract(root)
    facts[NAME_MEASURED] = measured(root, path_data)
    text                 = RULES.read_text(encoding = 'utf-8')
    rows                 = cctool.graph.logic.run(facts, text, MAP_MEASURED)
    map_column           = {name: tuple(column for (column, _) in tuple_column)
                            for (name, tuple_column)
                            in cctool.graph.logic.declared(text).items()}

    return cctool.graph.logic.described(rows, map_column, cctool.graph.logic.worded(text))


# -----------------------------------------------------------------------------
def measured(root: pathlib.Path, path_data: pathlib.Path) -> set[tuple[str, str, str]]:
    """
    Return the coverage of lines and of branches, in a thousand, of each
    file under root that the data file at path_data measured, keyed by
    the path of the file in the tree, or none if the run measured no
    file.

    """

    try:
        import coverage  # a dependency of development only, so imported where used
    except ImportError as error:
        raise ErrorCoverage('coverage is not installed; run pixi install.') from error
    if not path_data.is_file():
        raise ErrorCoverage('{path} holds no coverage data; run the tests under coverage '
                            'run --branch first.'.format(path = path_data))

    with tempfile.TemporaryDirectory() as name:
        path_report = pathlib.Path(name) / 'coverage.json'
        try:
            measure = coverage.Coverage(data_file = str(path_data))
            measure.load()
            measure.json_report(outfile = str(path_report), ignore_errors = True)
        except coverage.exceptions.NoDataError:
            return set()
        except coverage.exceptions.CoverageException as error:
            raise ErrorCoverage('The coverage data cannot be read: {error}'.format(
                                                                    error = error)) from error
        map_file = json.loads(path_report.read_text(encoding = 'utf-8')).get('files', {})

    set_row = set()
    for (name, entry) in map_file.items():
        relative = _relative(root, pathlib.Path(name))
        if relative is None:
            continue
        summary = entry.get('summary', {})
        set_row.add((relative, KIND_LINE, _per(summary.get('covered_lines', 0),
                                               summary.get('num_statements', 0))))
        set_row.add((relative, KIND_BRANCH, _per(summary.get('covered_branches', 0),
                                                 summary.get('num_branches', 0))))
    return set_row


# -----------------------------------------------------------------------------
def _relative(root: pathlib.Path, path: pathlib.Path) -> str | None:
    """
    Return the path of the file at path in the tree under root, or None
    if it is outside the tree. A relative path is read from the working
    directory, as coverage writes it.

    """

    path = (path if path.is_absolute() else pathlib.Path.cwd() / path).resolve()
    try:
        return path.relative_to(root.resolve()).as_posix()
    except ValueError:
        return None


# -----------------------------------------------------------------------------
def _per(covered: int, total: int) -> str:
    """
    Return how many in a thousand of total are covered, rounded down,
    or a thousand if there are none to cover.

    """

    return str(PER if not total else covered * PER // total)
