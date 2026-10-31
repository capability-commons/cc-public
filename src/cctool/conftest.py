"""
---

id_self:                pym_cctool.conftest
guid_self:              pym_8c07ee653351466fa401605f3b360b5f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Test fixtures
brief:                  |
                        The fixtures the tests share: a copy of the
                        repository to break.
description:            |
                        This module holds the fixtures. Every test
                        runs wherever the environment is installed,
                        since clingo is part of it. A copy keeps only
                        a fixed slice of the deliberations: frozen
                        copies of the decisions the tests name, held
                        in _test/_fixture, in place of every decision
                        of the repository. So the tests neither slow
                        down nor change meaning as the deliberations
                        in the repository grow, are ruled on or are
                        corrected.
edge:                   []

...
"""


import fnmatch
import functools
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest

import cctool.commit.message
import cctool.graph.extract


DIR_REPO  = pathlib.Path(__file__).resolve().parents[2]

# What a copy leaves out: version control, environments, caches, local
# tools and the fixture, which goes in its own place. The tests run in
# parallel, and a copy is made while other workers run, so a cache that
# a test writes in the repository must be left out: hypothesis writes
# and removes files under .hypothesis, and a copy that listed one of
# them before it was removed failed with no such file.
#
TUPLE_SKIP = ('.git', '.pixi', '.venv', '_tools', '__pycache__', '.ruff_cache',
              '.pytest_cache', '.hypothesis', '*.egg-info', '_fixture')


# The decisions of a copy are those of the fixture, frozen copies of the
# decisions the tests name, not those of the repository. The fixture
# leaves out the ruling of dec_tooling_language, so that the tests have
# an open decision to work on. Change the fixture only for a test, and
# never because the repository has changed.
#
DIR_DECISION         = DIR_REPO / '_data' / 'decision'
DIR_FIXTURE_DECISION = pathlib.Path(__file__).resolve().parent / '_test' / '_fixture' / 'decision'

# An annotation outside the decisions may name an item of a decision, and
# a copy that holds only the decisions of the fixture would hold it
# dangling, so a copy leaves out each annotation that names an item of a
# decision the fixture does not hold.
#
DIR_ANNOTATION       = DIR_REPO / '_data' / 'annotation'
REGEX_NAME           = re.compile(r'[a-z][a-z0-9_]*')


# The source a copy keeps: only the modules and logic programs that the
# rest of the copy names, and those that they name in turn, so that each
# check of a copy reads and checks less.
#
# The source files that the tests name are kept as well.
#
DIR_SOURCE          = DIR_REPO / 'src'
TUPLE_SOURCE_KEPT   = ('src/cctool/cli/__init__.py',
                       'src/cctool/edit/_test/test_edit.py',
                       'src/cctool/edit/edit.py',
                       'src/cctool/check/layout.py',
                       'src/cctool/graph/jq.py')
FILE_PACKAGE        = '__init__.py'


# The team member register, and the line of it that gives the key the
# maintainer signs with, which a signed copy gives the key of a keyring
# made for the tests in its place.
#
FILE_MEMBERS   = '_data/register/reg_team_member.yaml'
KEY_MAINTAINER = '9C4FB30F113CAB6A'
LINE_KEY       = 'git_signing_key:    {key}\n'.format(key = KEY_MAINTAINER)

# The line that gives the key the landing queue signs with, which a
# signed copy leaves out, so that the key of the keyring is the only key
# its register gives.
#
REGEX_QUEUE_KEY = re.compile(r'^ *git_queue_signing_key: .*\n', re.MULTILINE)

# The global configuration of git in each test, in place of the user's.
#
DIR_HOME        = 'home'
FILE_GIT_CONFIG = '.gitconfig'
ENV_BROWSERS    = 'PLAYWRIGHT_BROWSERS_PATH'
DIR_BROWSERS    = '.cache/ms-playwright'
TEXT_GIT_CONFIG = ('[user]\n\tname = William Payne\n\temail = wtpayne@gmail.com\n'
                   '[commit]\n\tgpgsign = false\n[tag]\n\tgpgsign = false\n')

# The configuration a signed copy commits under: as the maintainer, whom
# the register gives as git_author, signing each commit.
#
TUPLE_CONFIG   = (('user.name',      'William Payne'),
                  ('user.email',     'wtpayne@gmail.com'),
                  ('commit.gpgsign', 'true'),
                  ('gpg.format',     'openpgp'))


# -----------------------------------------------------------------------------
def _ignore(dir_from: str, list_name: list[str]) -> set[str]:
    """
    Return the names in dir_from that a copy leaves out: those that
    match TUPLE_SKIP; in _data/decision, every decision; in
    _data/annotation, each annotation that names an item of a decision
    the fixture does not hold; and in src, what _source_kept does not
    keep.

    """

    set_skip = shutil.ignore_patterns(*TUPLE_SKIP)(dir_from, list_name)
    dir_here = pathlib.Path(dir_from)
    if dir_here == DIR_DECISION:
        set_skip |= set(list_name)
    if dir_here == DIR_ANNOTATION:
        set_skip |= {name for name in list_name
                     if names_absent_decision_item((dir_here / name).read_text(
                                                       encoding = 'utf-8', errors = 'replace'))}
    if dir_here == DIR_SOURCE or DIR_SOURCE in dir_here.parents:
        set_kept  = _source_kept()
        set_skip |= {name for name in list_name if dir_here / name not in set_kept}
    return set_skip


# -----------------------------------------------------------------------------
def names_absent_decision_item(text: str) -> bool:
    """
    Return whether text names the id of an item that a decision of the
    repository holds and no decision of the fixture does.

    """

    return not _absent_decision_items().isdisjoint(REGEX_NAME.findall(text))


# -----------------------------------------------------------------------------
@functools.cache
def _absent_decision_items() -> frozenset[str]:
    """
    Return the id of each item that a decision of the repository holds in
    a file of its own and no decision of the fixture holds.

    """

    set_held = {path.stem for path in DIR_FIXTURE_DECISION.rglob('*.yaml')}
    return frozenset(path.stem for path in DIR_DECISION.rglob('*.yaml')
                     if path.stem not in set_held)


# -----------------------------------------------------------------------------
@functools.cache
def _source_kept() -> frozenset[pathlib.Path]:
    """
    Return the paths under src that a copy keeps: those of
    TUPLE_SOURCE_KEPT, each module or logic program that one of them or
    a file the copy keeps outside src mentions by its id, or by the id
    of a class or function in it, and those that they mention in turn,
    with the folders that hold them and the package module of each, so
    that a module kept is in the logical component its package
    realizes.

    """

    map_module = {}
    for path in DIR_SOURCE.rglob('*'):
        if path.suffix in cctool.graph.extract.MAP_PREFIX_MODULE and not _is_skipped(path):
            map_module[cctool.graph.extract.module_name(path.relative_to(DIR_REPO))] = path

    set_kept  = {DIR_REPO / relative for relative in TUPLE_SOURCE_KEPT}
    list_todo = [*(path for path in _outside_source() if path.is_file()), *set_kept]
    while list_todo:
        text = list_todo.pop().read_text(encoding = 'utf-8', errors = 'replace')
        for match in cctool.graph.extract.REGEX_MENTION.finditer(text):
            path = _module_of(match.group(0), map_module)
            if path is not None and path not in set_kept:
                set_kept.add(path)
                list_todo.append(path)

    set_dir = {dir_parent for path in set_kept for dir_parent in path.parents
               if DIR_SOURCE in dir_parent.parents}
    return frozenset(set_kept | set_dir | {path for each in set_dir
                                           if (path := each / FILE_PACKAGE).is_file()})


# -----------------------------------------------------------------------------
def _outside_source() -> list[pathlib.Path]:
    """
    Return each path that a copy keeps outside src.

    """

    list_path = []
    for (name, list_dir, list_file) in os.walk(DIR_REPO):
        dir_here = pathlib.Path(name)
        list_dir[:] = [each for each in list_dir
                       if not _is_skipped(dir_here / each) and dir_here / each != DIR_SOURCE
                       and dir_here != DIR_DECISION]
        list_path.extend(dir_here / each for each in list_file if not _is_skipped(dir_here / each))
    list_path.extend(sorted(DIR_FIXTURE_DECISION.rglob('*')))
    return list_path


# -----------------------------------------------------------------------------
def _is_skipped(path: pathlib.Path) -> bool:
    """
    Return whether path, or a folder it is in, matches TUPLE_SKIP.

    """

    return any(fnmatch.fnmatch(part, pattern)
               for part in path.relative_to(DIR_REPO).parts for pattern in TUPLE_SKIP)


# -----------------------------------------------------------------------------
def _module_of(word: str, map_module: dict[str, pathlib.Path]) -> pathlib.Path | None:
    """
    Return the module or logic program that the id word names, or holds
    the class, function or predicate it names, or None if it names none.

    """

    (prefix, _, name) = word.partition(cctool.graph.extract.DELIM_PREFIX)
    prefix           += cctool.graph.extract.DELIM_PREFIX
    tuple_prefix      = (*cctool.graph.extract.MAP_PREFIX_MODULE.values(),
                         cctool.graph.extract.PREFIX_PACKAGE)
    tuple_prefix      = (prefix,) if prefix in tuple_prefix else tuple_prefix
    if prefix == cctool.graph.extract.PREFIX_PREDICATE:
        tuple_prefix  = (cctool.graph.extract.MAP_PREFIX_MODULE[
                             cctool.graph.extract.SUFFIX_PROGRAM],)
    list_part         = name.split(cctool.graph.extract.DELIM_MODULE)
    while list_part:
        dotted = cctool.graph.extract.DELIM_MODULE.join(list_part)
        for each in tuple_prefix:
            if each + dotted in map_module:
                return map_module[each + dotted]
        list_part.pop()
    return None


# -----------------------------------------------------------------------------
def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Mark reads_data each test that copies the repository, so that the
    gate of a commit that stages data but no code runs it.

    """

    for item in items:
        if 'tree' in getattr(item, 'fixturenames', ()):
            item.add_marker(pytest.mark.reads_data)


# -----------------------------------------------------------------------------
@pytest.fixture(autouse = True)
def git_config(tmp_path_factory, monkeypatch):
    """
    Give git, in each test, a global configuration of its own in place
    of the user's: the maintainer as the identity, and no signing. A
    test that commits in a repository of its own would otherwise sign
    with the user's key, and fail wherever that key cannot sign without
    a person to unlock it, as when the landing queue runs the tests
    unattended. A fixture that signs sets its key itself.

    git reads its global configuration from the home directory, so each
    test has a home of its own. Many fixtures remove every variable of
    git from the environment, so a variable could not carry this. The
    browsers that playwright installed are found where they are.

    """

    dir_home = tmp_path_factory.getbasetemp() / DIR_HOME
    if not dir_home.exists():
        dir_home.mkdir()
        (dir_home / FILE_GIT_CONFIG).write_text(TEXT_GIT_CONFIG, encoding = 'utf-8')
    if ENV_BROWSERS not in os.environ:
        monkeypatch.setenv(ENV_BROWSERS, str(pathlib.Path.home() / DIR_BROWSERS))
    monkeypatch.setenv('HOME', str(dir_home))
    monkeypatch.setenv('GIT_CONFIG_NOSYSTEM', '1')


# -----------------------------------------------------------------------------
@pytest.fixture
def tree(tmp_path):
    """
    Yield the root of a copy of the repository: its data items, its
    source and the files at its root, without version control,
    environments or caches, and with the decisions of the fixture in
    place of those of the repository.

    The copy is removed when the test ends. A run makes one for each of
    some hundreds of tests, and pytest keeps the temporary folders of
    its last three runs, so copies left behind would fill a disk with
    few inodes.

    """

    shutil.copytree(DIR_REPO, tmp_path,
                    ignore        = _ignore,
                    dirs_exist_ok = True)
    shutil.copytree(DIR_FIXTURE_DECISION, tmp_path / DIR_DECISION.relative_to(DIR_REPO),
                    ignore        = shutil.ignore_patterns(*TUPLE_SKIP),
                    dirs_exist_ok = True)
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors = True)


# -----------------------------------------------------------------------------
@pytest.fixture(scope = 'session')
def keyring():
    """
    Yield a keyring made for the tests, with one signing key and no
    passphrase, as the folder that holds it and the long id of the key.
    gpg runs an agent for a keyring, and the path of the agent's socket
    must be short, so the folder is made directly in the temporary
    folder of the system.

    """

    if shutil.which('gpg') is None:
        pytest.skip('gpg is not installed, so no commit can be signed.')
    home = tempfile.mkdtemp(prefix = 'gpg')
    env  = {**os.environ, 'GNUPGHOME': home}
    subprocess.run(['gpg', '--batch', '--pinentry-mode', 'loopback', '--passphrase', '',
                    '--quick-generate-key', 'Test key <test@example.invalid>', 'ed25519',
                    'sign', 'never'],
                   env = env, check = True, capture_output = True)
    listing = subprocess.run(['gpg', '--list-keys', '--with-colons'],
                             env = env, check = True, capture_output = True, text = True).stdout
    key = next(line.split(':')[4] for line in listing.splitlines() if line.startswith('pub:'))
    yield (home, key.upper())
    subprocess.run(['gpgconf', '--kill', 'gpg-agent'], env = env, check = False,
                   capture_output = True)
    shutil.rmtree(home, ignore_errors = True)


# -----------------------------------------------------------------------------
@pytest.fixture
def signed_repo(tree, keyring, monkeypatch):
    """
    Return the root of a copy of the repository, committed on main as
    the maintainer under a message that conforms. git signs each commit
    made in it with the key of keyring, which the copy's register gives
    as the maintainer's, and as the only key it gives.

    """

    (home, key) = keyring
    for key_env in [key_env for key_env in os.environ if key_env.startswith('GIT_')]:
        monkeypatch.delenv(key_env)
    monkeypatch.setenv('GNUPGHOME', home)
    for (index, (name, value)) in enumerate([*TUPLE_CONFIG, ('user.signingkey', key)]):
        monkeypatch.setenv('GIT_CONFIG_KEY_{index}'.format(index = index), name)
        monkeypatch.setenv('GIT_CONFIG_VALUE_{index}'.format(index = index), value)
    monkeypatch.setenv('GIT_CONFIG_COUNT', str(len(TUPLE_CONFIG) + 1))

    path = tree / FILE_MEMBERS
    path.write_text(REGEX_QUEUE_KEY.sub('', path.read_text().replace(
                        LINE_KEY, LINE_KEY.replace(KEY_MAINTAINER, key))))
    message = cctool.commit.message.compose('Add the first version of cc-public',
                                            'The first version.')
    for list_arg in (['init', '--quiet', '--initial-branch', 'main'],
                     ['add', '--all'],
                     ['commit', '--quiet', '--no-verify', '--message', message]):
        subprocess.run(['git', *list_arg], cwd = tree, check = True, capture_output = True)
    return tree


# -----------------------------------------------------------------------------
@pytest.fixture
def dev_repo(tmp_path, monkeypatch):
    """
    Return the root of a small repository, checked out on dev, whose one
    commit holds README.md. git commits in it as the maintainer and,
    unless told otherwise, signs nothing.

    """

    for key_env in [key_env for key_env in os.environ if key_env.startswith('GIT_')]:
        monkeypatch.delenv(key_env)
    tuple_config = (*TUPLE_CONFIG[:2], ('commit.gpgsign', 'false'))
    for (index, (name, value)) in enumerate(tuple_config):
        monkeypatch.setenv('GIT_CONFIG_KEY_{index}'.format(index = index), name)
        monkeypatch.setenv('GIT_CONFIG_VALUE_{index}'.format(index = index), value)
    monkeypatch.setenv('GIT_CONFIG_COUNT', str(len(tuple_config)))

    root = tmp_path / 'cc-public'
    root.mkdir()
    (root / 'README.md').write_text('Start.\n')
    for list_arg in (['init', '--quiet', '--initial-branch', 'dev'],
                     ['add', '--all'],
                     ['commit', '--quiet', '--no-verify', '--message', 'Start']):
        subprocess.run(['git', *list_arg], cwd = root, check = True, capture_output = True)
    return root
