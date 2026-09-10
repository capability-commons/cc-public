"""
---

id_self:                pym_test.selection
guid_self:              pym_fac41954e3584c49b9a1d51d51e64910
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test selection by what changed
brief:                  |
                        Decides which tests a change can reach, from a
                        map measured over a whole run, and runs those.
description:            |
                        The loop and not the judgement. A selective
                        run is a way to see quickly whether a change
                        broke something it could have broken; the gate
                        remains what says a tree is sound, and nothing
                        in CI reads this.

                        Every rule here errs towards running
                        everything. A change this cannot attribute, a
                        map that is absent, a map measured in a way
                        that cannot attribute, or a selection so large
                        that selecting saved nothing, all mean the
                        whole suite. Under-running is the failure that
                        matters: a suite that ran the wrong tests and
                        passed looks exactly like one that ran the
                        right ones.

                        A run made from here writes no evidence.
                        Evidence is what a whole session observed, and
                        a partial session writing it would drop the
                        rows for every case it did not run.
relation:               []

...
"""


import argparse
import concurrent.futures
import json
import os
import pathlib
import shutil
import subprocess
import sys
import typing


ROOT       = pathlib.Path(__file__).resolve().parent.parent
PATH_MAP   = ROOT / '.test_map.json'

DIR_DATA   = '.test_map_data'
DIR_SOURCE = 'src/cc_public'
DIR_TEST   = 'test'
CONFTEST   = 'test/conftest.py'

KEY_CORE    = 'core'
KEY_SOURCE  = 'by_source'
KEY_TEST    = 'test'
KEY_COMMIT  = 'commit'
KEY_MISSING = 'missing'

# The coverage cores that report a line every time it runs. The default
# core on python 3.12 and after is sys.monitoring, which asks the
# interpreter to stop reporting a line once it has been seen. That is
# right for measuring coverage and wrong for attributing it: only the
# first test to reach a line is recorded against it, and every later
# test looks as though it never touched the code. A map measured that
# way is not merely coarse, it is confidently wrong, so it is refused
# rather than used.
#
CORE_ATTRIBUTING = ('ctrace', 'pytrace')

# Selecting most of the suite saves little and risks the whole of what
# selection can get wrong, so past this share of it the whole suite is
# run instead.
#
SHARE_NOT_WORTH_IT = 0.5

# The suite's own timeout is what a judgement wants and is wrong here.
# Eight modules run at once and each of the heavy ones runs the tool in
# subprocesses, so a test that takes three minutes alone can take twenty
# under measurement. A test stopped by a timeout leaves its module out of
# the map, which is a hole rather than a failure, so the timeout is far
# enough out that only a hang reaches it.
#
SECOND_TIMEOUT = 3600

VARIABLE_PARTIAL = 'CCTOOL_PARTIAL_RUN'
VARIABLE_CORE    = 'COVERAGE_CORE'


class Plan(typing.NamedTuple):
    """
    What to run, and why that is what to run.

    is_whole says the whole suite, whatever node holds. reason is one
    sentence a person reads before trusting a short run.

    """

    is_whole: bool
    node:     tuple
    reason:   str


def is_source(path):
    """
    Return whether path is a module of the tool.

    """

    return path.startswith(DIR_SOURCE + '/') and path.endswith('.py')


def is_test(path):
    """
    Return whether path is a test module.

    """

    return path.startswith(DIR_TEST + '/') and path.endswith('.py')


def _whole_because(set_changed, held):
    """
    Return why the whole suite must run, or None where no reason
    applies.

    Every reason here is a change whose reach a map of executed lines
    cannot say: an absent map, the shared fixtures, a data item, the
    project file, or a module the map never saw. Tests read those and
    execute no line naming them.

    """

    if not held.by_source:
        return 'There is no map, so what a change reaches is unknown.'

    for path in sorted(set_changed):

        if path == CONFTEST:
            return 'test/conftest.py changed, and every test is built from it.'

        if not is_source(path) and not is_test(path):
            return ('{path} changed. It is neither a module of the tool nor a test, so '
                    'what reads it is not something a map of executed lines can '
                    'say.'.format(path = path))

        if is_source(path) and path not in held.by_source:
            return ('{path} changed, and the map does not hold it. It may be new, or it '
                    'may have been reached by nothing when the map was '
                    'measured.'.format(path = path))

    return None


def _reached(set_changed, held):
    """
    Return the node ids a change can reach.

    A changed test module is named whole, since the map cannot hold a
    test that did not exist when it was measured. So is every module
    the measurement could not account for, since nothing is known
    about what its tests reach.

    """

    node = set(held.missing)

    for path in sorted(set_changed):
        node.update([path] if is_test(path) else held.by_source[path])

    return node


def plan(set_changed, held):
    """
    Return the Plan for a set of changed paths, given what the map
    holds.

    """

    if set_changed and (whole := _whole_because(set_changed, held)) is not None:
        return Plan(True, (), whole)

    node = _reached(set_changed, held) if set_changed else set()

    if not node:
        return Plan(False, (), 'Nothing has changed.' if not set_changed else
                               'Nothing the map holds reaches what changed.')

    if held.count and len(node) > SHARE_NOT_WORTH_IT * held.count:
        return Plan(True, (), '{n} of {m} tests reach what changed, which is enough of '
                              'the suite that running all of it is simpler and no '
                              'slower.'.format(n = len(node), m = held.count))

    return Plan(False, tuple(sorted(node)),
                '{n} of {m} tests reach what changed{also}.'.format(
                        n    = len(node), m = held.count,
                        also = '' if not held.missing else
                               ', counting {k} module(s) the map could not account '
                               'for'.format(k = len(held.missing))))


def measure(root = ROOT, path = PATH_MAP, width = 8):
    """
    Run the whole suite recording which tests reach which modules, and
    write the map. Return the number of modules that did not pass.

    The core is set here and not left to whoever runs this, because a
    map measured by the default core is confidently wrong rather than
    merely coarse, and nothing downstream could tell.

    One process per test module rather than one session over all of
    them. Recording a context per test under xdist leaves worker data
    files the combine step cannot read, and one session without xdist
    took ten hours where this takes half an hour.

    """

    import coverage

    dirpath = root / DIR_DATA
    shutil.rmtree(dirpath, ignore_errors = True)
    dirpath.mkdir(parents = True)

    list_module = sorted(p.name for p in (root / DIR_TEST).glob('test_*.py'))

    with concurrent.futures.ThreadPoolExecutor(max_workers = width) as pool:
        list_code = list(pool.map(lambda name: _measure_one(root, dirpath, name),
                                  list_module))

    set_missing = {name for (name, code) in zip(list_module, list_code, strict = True)
                        if code != 0}

    held        = coverage.CoverageData(str(dirpath / 'combined'))
    set_missing |= _combine_into(held, sorted(dirpath.glob('data.*')))

    for name in sorted(set_missing):
        print('{name} is not in the map, so it will run whatever '
              'changed.'.format(name = name))

    path.write_text(json.dumps(_map_of(held, root, CORE_ATTRIBUTING[0], set_missing),
                               indent = 2, sort_keys = True) + '\n',
                    encoding = 'utf-8')

    return len(set_missing)


def _measure_one(root, dirpath, name, core = CORE_ATTRIBUTING[0]):
    """
    Run one test module, recording which test reached which line, and
    return its return code.

    core is a parameter only so that a control can measure the same
    module with the default core and show what that loses. Nothing in
    the measurement passes anything but the attributing core.

    """

    done = subprocess.run(
                [sys.executable, '-m', 'pytest', '-q', '-n', '0',
                 DIR_TEST + '/' + name, '--cov=cc_public', '--cov-report=',
                 '--cov-fail-under=0', '--cov-context=test',
                 '--timeout', str(SECOND_TIMEOUT)],
                cwd            = str(root),
                env            = dict(os.environ,
                                      **{VARIABLE_PARTIAL: '1',
                                         VARIABLE_CORE:    core,
                                         'COVERAGE_FILE':  str(dirpath / ('data.' + name))}),
                capture_output = True,
                text           = True,
                check          = False)

    return done.returncode


def _combine_into(held, list_path):
    """
    Read each data file into held, and return the test modules whose
    data could not be read.

    One at a time, because a module whose tests run the tool in a
    subprocess collects that subprocess's coverage too, and where the
    subprocess measured branches the file cannot be combined with the
    rest. What that module reaches is then unknown, which is said
    rather than passed over: the caller makes it run always.

    """

    import coverage

    set_missing = set()

    for filepath in list_path:
        try:
            held.update(_read(filepath))
        except coverage.exceptions.DataError:
            set_missing.add(filepath.name.split('.', 1)[1])

    return set_missing


def _read(filepath):
    """
    Return the coverage data one file holds.

    """

    import coverage

    held = coverage.CoverageData(str(filepath))
    held.read()

    return held


def _map_of(held, root, core, set_missing):
    """
    Return the map, as it is written: which tests reached each module,
    every test the measurement saw, and every test module the
    measurement could not account for.

    """

    map_source = {}
    set_test   = set()

    for filepath in held.measured_files():

        name = _relative(filepath, root)

        if name is None:
            continue

        node = set()

        for one in held.contexts_by_lineno(filepath).values():
            node.update(context.split('|')[0] for context in one if context)

        if node:
            map_source[name] = sorted(node)
            set_test        |= node

    return {KEY_CORE:    core,
            KEY_COMMIT:  _commit(root),
            KEY_MISSING: sorted(DIR_TEST + '/' + name for name in set_missing),
            KEY_TEST:    sorted(set_test),
            KEY_SOURCE:  map_source}


def _relative(filepath, root):
    """
    Return the repository relative path of a measured file, or None
    where it lies outside the repository.

    """

    try:
        return pathlib.Path(filepath).resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _commit(root):
    """
    Return the commit the map was measured at, or absent.

    """

    done = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                          capture_output = True, text = True, check = False)

    return done.stdout.strip() or 'absent'


class Map(typing.NamedTuple):
    """
    What the map holds: which tests reached each module, how many tests
    the measurement saw, and the test modules it could not account for.

    A module in missing did not pass under measurement, or its data
    could not be read. Nothing is known about what its tests reach, so
    it runs whenever anything runs.

    """

    by_source: dict
    count:     int
    missing:   tuple


NO_MAP = Map({}, 0, ())


def load(path = PATH_MAP):
    """
    Return the Map, or NO_MAP where there is none this can be trusted.

    A map measured by a core that cannot attribute is refused here
    rather than believed, since believing it would run a handful of
    tests and report success.

    """

    if not path.exists():
        return NO_MAP

    held = json.loads(path.read_text(encoding = 'utf-8'))

    if held.get(KEY_CORE) not in CORE_ATTRIBUTING:
        return NO_MAP

    return Map(by_source = held.get(KEY_SOURCE) or {},
               count     = len(held.get(KEY_TEST) or ()),
               missing   = tuple(held.get(KEY_MISSING) or ()))


def changed(root = ROOT, ref = None):
    """
    Return the repository relative paths that differ from ref, or from
    the last commit and the working tree where ref is absent.

    """

    def git(*argument):
        done = subprocess.run(['git', '-C', str(root), *argument],
                              capture_output = True, text = True, check = True)
        return [line for line in done.stdout.splitlines() if line]

    if ref is not None:
        return set(git('diff', '--name-only', ref))

    return set(git('diff', '--name-only', 'HEAD')) \
         | set(git('ls-files', '--others', '--exclude-standard'))


def main(argument = None):
    """
    Run what a change can reach, and say what was run and why.

    """

    parser = argparse.ArgumentParser(description = 'Run the tests a change can reach.')
    parser.add_argument('--since', default = None,
                        help = 'Compare against this commit rather than the working '
                               'tree against the last one.')
    parser.add_argument('--dry-run', action = 'store_true',
                        help = 'Say what would run, and run nothing.')
    parser.add_argument('--measure', action = 'store_true',
                        help = 'Run the whole suite and write the map, then stop.')
    parsed = parser.parse_args(argument)

    if parsed.measure:
        count = measure()
        print('map written to {path}{gap}'.format(
                    path = PATH_MAP.name,
                    gap  = '' if not count else
                           ', with {n} module(s) it could not account for, which '
                           'will run whatever changes'.format(n = count)))

        # Not a failure. A module the map cannot account for is one the
        # selector runs always, so the map is incomplete and still
        # safe, and a task that failed every time would teach whoever
        # runs it to stop reading what it says.
        #
        return 0

    decided = plan(changed(ref = parsed.since), load())

    print(decided.reason)

    if parsed.dry_run:
        print('The whole suite would run.' if decided.is_whole else
              '{n} node(s) would run.'.format(n = len(decided.node)))
        return 0

    if not decided.is_whole and not decided.node:
        return 0

    target = [DIR_TEST] if decided.is_whole else list(decided.node)

    return subprocess.run([sys.executable, '-m', 'pytest', '-q', '-n', 'auto', *target],
                          cwd   = str(ROOT),
                          env   = dict(os.environ, **{VARIABLE_PARTIAL: '1'}),
                          check = False).returncode


if __name__ == '__main__':
    sys.exit(main())
