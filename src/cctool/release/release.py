"""
---

id_self:                pym_cctool.release.release
guid_self:              pym_d05b24372e1c4c858224a2ec33db33af
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Release step
brief:                  |
                        Compute the bump since the last release, write
                        the release item and the version module, and
                        check a commit before it is tagged.
description:            |
                        The bump is computed from the change between
                        the trees of the last release tag and HEAD,
                        which impact finds by guid, so that a rename
                        is found as one. A schema, register or
                        register entry that is removed or renamed
                        calls for a major bump, one added for a minor
                        bump, and anything else for a patch; before
                        1.0.0 each level bumps the part below it. Code
                        is public only where an interface control
                        document says so, which the graph cannot yet
                        tell, so it does not count. The commit items
                        since the tag give the notes, and name the
                        commit of each break. The release item records
                        the runtime packages of pixi.lock, from its
                        tool environment, or, until there is one, from
                        what cc-public needs in the default
                        environment. Nothing is committed or tagged
                        here: the maintainer decides each release, per
                        ruling_maintainer_decides_each_release.
usage:                  |
                        Run by cctool release prepare and cctool
                        release check.
edge:                   []

...
"""


import pathlib
import re
import subprocess
import tempfile

import ruamel.yaml

import cctool.check.check
import cctool.check.release_record
import cctool.check.segment
import cctool.commit.change
import cctool.commit.history
import cctool.commit.impact
import cctool.commit.message
import cctool.edit.edit
import cctool.gate.gate
import cctool.graph.extract
import cctool.graph.logic
import cctool.graph.parse


# A release tag is v and the version, and git describe finds the last
# one by this pattern.
#
PREFIX_TAG        = 'v'
PATTERN_TAG       = 'v[0-9]*.[0-9]*.[0-9]*'

# The levels of a bump, from least to most. Before 1.0.0 anything may
# change (SemVer 2.0.0, item 4), and each level bumps the part below
# it, so that the minor part still tells a partner when to expect a
# break.
#
LEVEL_PATCH       = 'patch'
LEVEL_MINOR       = 'minor'
LEVEL_MAJOR       = 'major'
TUPLE_LEVEL       = (LEVEL_PATCH, LEVEL_MINOR, LEVEL_MAJOR)

# What is supported, as ruled in ruling_public_api_split_by_kind: the
# data format, its schemas and registers, with the types and relations
# they hold. Code is supported only where an interface control document
# says so, which the graph cannot yet tell, so it is judged unsupported
# here.
#
TUPLE_DIR_SUPPORT = ('_data/schema/', '_data/register/')
DELTA_ADDED       = 'added'
DELTA_REMOVED     = 'removed'
DELTA_RENAMED     = 'renamed'
SET_DELTA_BREAKS  = {DELTA_REMOVED, DELTA_RENAMED}

# The runtime lock: the environment of pixi.lock that holds what cctool
# needs to run and nothing used only to develop it. Until pixi.lock has
# one, the packages that the project needs are found from the default
# environment, by following what each package depends on.
#
PATH_LOCK         = 'pixi.lock'
ENV_RUNTIME       = 'tool'
ENV_DEFAULT       = 'default'
URL_PROJECT       = './'
TUPLE_KIND        = ('conda', 'pypi')
TUPLE_SUFFIX      = ('.conda', '.tar.bz2')
REGEX_PURL        = re.compile(r'pkg:pypi/([^?@]+)')
REGEX_NAME_END    = re.compile(r'[ ;<>=!~\[(]')
REGEX_SEPARATOR   = re.compile(r'[-_.]+')
MARK_EXTRA        = 'extra =='
YAML_LOCK         = ruamel.yaml.YAML(typ = 'safe')

DIR_RELEASE       = '_data/release'
KEY_DEPENDENCY    = 'dependency'
TUPLE_KEY_PACKAGE = ('platform', 'name', 'version', 'sha256')
KEY_RENAME        = 'rename'
TUPLE_KEY_RENAME  = ('old', 'new', 'guid')


# -----------------------------------------------------------------------------
class ErrorRelease(Exception):
    """
    The release step cannot do what was asked. The message says why.

    """


# -----------------------------------------------------------------------------
def last_tag(root: pathlib.Path, rev: str) -> str | None:
    """
    Return the last release tag that rev reaches in the repository at
    root, or None if it reaches none.

    """

    done = subprocess.run(['git', 'describe', '--tags', '--abbrev=0',
                           '--match', PATTERN_TAG, rev],
                          cwd            = root,
                          capture_output = True,
                          text           = True,
                          check          = False)

    return done.stdout.strip() if done.returncode == 0 else None


# -----------------------------------------------------------------------------
def touched(root: pathlib.Path,
            base: str,
            rev:  str) -> tuple[list[tuple[str, ...]], list[dict[str, str]]]:
    """
    Return each item that the commits from base to rev add, remove,
    rename or change, as impact finds them between the two trees: its
    id, its delta, the id it was if renamed, and its file and line. An
    item added and removed again between them is not touched. Return
    too the rename map: the old id, new id and guid of each item
    renamed, ordered by old id.

    """

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        cctool.gate.gate.copy_commit(root, base, dir_before)
        cctool.gate.gate.copy_commit(root, rev, dir_after)
        list_touched = cctool.commit.impact.impact_trees(dir_before, dir_after)['touched']
        list_renamed = [row for row in list_touched if row[1] == DELTA_RENAMED]
        map_guid     = {}
        if list_renamed:
            facts    = cctool.graph.extract.extract(dir_after)
            map_guid = {row[0]: row[1] for row in facts['item']}

    list_rename = [dict(zip(TUPLE_KEY_RENAME, (row[2], row[0], map_guid[row[0]]), strict = True))
                   for row in sorted(list_renamed, key = lambda row: row[2])]

    return (list_touched, list_rename)


# -----------------------------------------------------------------------------
def level(list_touched: list[tuple[str, ...]]) -> tuple[str, list[tuple[str, ...]]]:
    """
    Return the level of the bump that list_touched calls for, and the
    rows that call for it: major if a supported item is removed or
    renamed, minor if one is added, and patch otherwise.

    """

    list_support = [row for row in list_touched if row[3].startswith(TUPLE_DIR_SUPPORT)]
    list_break   = [row for row in list_support if row[1] in SET_DELTA_BREAKS]
    list_add     = [row for row in list_support if row[1] == DELTA_ADDED]

    if list_break:
        return (LEVEL_MAJOR, list_break)
    if list_add:
        return (LEVEL_MINOR, list_add)
    return (LEVEL_PATCH, [])


# -----------------------------------------------------------------------------
def bumped(version: str, name_level: str) -> str:
    """
    Return the version after version for a bump of name_level. Before
    1.0.0 each level bumps the part below it.

    """

    tuple_number = cctool.check.release_record.numbers(version)
    if tuple_number is None:
        raise ErrorRelease('{version} is not a release version, such as 1.2.3.'.format(
                               version = version))

    (major, minor, patch) = tuple_number
    if major == 0 and name_level != LEVEL_PATCH:
        name_level = TUPLE_LEVEL[TUPLE_LEVEL.index(name_level) - 1]

    if name_level == LEVEL_MAJOR:
        return '{major}.0.0'.format(major = major + 1)
    if name_level == LEVEL_MINOR:
        return '{major}.{minor}.0'.format(major = major, minor = minor + 1)
    return '{major}.{minor}.{patch}'.format(major = major, minor = minor, patch = patch + 1)


# -----------------------------------------------------------------------------
def commit_items(root: pathlib.Path, base: str, rev: str) -> list[tuple[str, str, dict]]:
    """
    Return each commit from base to rev, oldest first, as its short
    hash, the title of its commit item, and the item. A commit whose
    message holds no item, as one made without the hooks may, gives its
    subject line as the title.

    """

    text       = _git(root, 'log', '--reverse', '--format=' + cctool.commit.history.FORMAT_LOG,
                      '{base}..{rev}'.format(base = base, rev = rev))
    list_item  = []

    for record in text.split(cctool.commit.history.MARK_RECORD):
        (commit, _, message) = record.strip('\n').partition(cctool.commit.history.MARK_FIELD)
        if not commit:
            continue
        try:
            (_, item) = cctool.commit.message.parse(message)
        except cctool.commit.message.ErrorMessage:
            item = {cctool.commit.message.KEY_TITLE: message.partition('\n')[0]}
        list_item.append((commit[:cctool.commit.history.LENGTH_SHORT],
                          str(item.get(cctool.commit.message.KEY_TITLE, '')),
                          item))

    return list_item


# -----------------------------------------------------------------------------
def mentioned_by(list_item: list[tuple[str, str, dict]]) -> dict[str, list[str]]:
    """
    Return the short hashes of the commits of list_item whose items
    name each id, keyed by id. A commit item names each item it removes
    or renames, so each break traces to the commit that made it.

    """

    map_short = {}

    for (short, _, item) in list_item:
        text = ' '.join(str(item.get(key, '')) for key in cctool.commit.change.TUPLE_KEY_TEXT)
        for id_item in set(cctool.graph.extract.REGEX_MENTION.findall(text)):
            map_short.setdefault(id_item, []).append(short)

    return map_short


# -----------------------------------------------------------------------------
def prepare(root: pathlib.Path, brief: str) -> dict:
    """
    Write the release item and the version module for a release of HEAD
    of the repository at root, in one edit, and return what was done.
    The version is the last release tag's, bumped by the level that the
    change since it calls for; with no release tag, it is the version the
    module holds, as the first release. Nothing is committed or tagged:
    the maintainer decides each release.

    The result holds the tag the release follows, the version before and
    after, the level and the touched rows that call for it, the short
    hashes of the commits whose items name each id, the renames and
    removals since the tag, the commits since it, and the files written.

    """

    if _git(root, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ErrorRelease('The working tree has changes that are not committed. Commit or '
                           'stash them first, so that the release records HEAD.')

    path_module = root / cctool.check.release_record.PATH_MODULE
    if not path_module.is_file():
        raise ErrorRelease('There is no version module at {path}.'.format(
                               path = cctool.check.release_record.PATH_MODULE))

    text_module  = path_module.read_text(encoding = 'utf-8')
    base         = last_tag(root, 'HEAD')
    list_touched = []
    list_rename  = []
    list_item    = []
    name_level   = None
    list_reason  = []
    before       = None
    version      = cctool.check.release_record.module_version(text_module)

    if base is not None:
        if _git(root, 'rev-parse', base + '^{commit}') == _git(root, 'rev-parse', 'HEAD'):
            raise ErrorRelease('HEAD is the release {tag}, so there is nothing to '
                               'release.'.format(tag = base))
        (list_touched, list_rename) = touched(root, base, 'HEAD')
        list_item                   = commit_items(root, base, 'HEAD')
        (name_level, list_reason)   = level(list_touched)
        before                      = base.removeprefix(PREFIX_TAG)
        version                     = bumped(before, name_level)

    if version is None or cctool.check.release_record.numbers(version) is None:
        raise ErrorRelease('The version module holds {version}, which is not a release '
                           'version, such as 1.2.3.'.format(version = version))

    tree       = cctool.edit.edit.Tree(root)
    segment    = cctool.check.segment.segment_of(cctool.graph.extract.documents(root))
    if segment is None:
        raise ErrorRelease('The tree holds no segment item, or more than one, so the release '
                           'cannot be named for its federated segment.')

    id_release = '{prefix}{segment}_{version}'.format(
                     prefix  = cctool.check.release_record.PREFIX,
                     segment = segment.removeprefix(cctool.graph.extract.PREFIX_SEGMENT),
                     version = version.replace('.', '_'))
    path_lock  = root / PATH_LOCK
    text_lock  = path_lock.read_text(encoding = 'utf-8') if path_lock.is_file() else ''
    list_field = [('title',        'Release {v}'.format(v = version)),
                  ('brief',        brief),
                  ('version',      version),
                  (KEY_DEPENDENCY, dependencies(text_lock))]

    if list_rename:
        list_field.append((KEY_RENAME, list_rename))

    tree.update(cctool.edit.edit.new(tree, id_release, list_field, []))
    tree.update({str(cctool.check.release_record.PATH_MODULE):
                 cctool.check.release_record.REGEX_VERSION.sub(
                     lambda match: match.group(1) + version + match.group(3), text_module)})

    added = cctool.edit.edit.apply(tree)
    if added:
        raise ErrorRelease('\n'.join([*cctool.graph.logic.described(
                                           added,
                                           cctool.check.check.columns(),
                                           cctool.check.check.wording()),
                                       'Refused: the release item adds failures. Nothing '
                                       'was written.']))

    return {'base':    base,
            'before':  before,
            'version': version,
            'level':   name_level,
            'reason':  list_reason,
            'commit':  mentioned_by(list_item),
            'renamed': [(rename['old'], rename['new']) for rename in list_rename],
            'removed': [row[0] for row in list_touched if row[1] == DELTA_REMOVED],
            'notes':   [(short, title) for (short, title, _) in list_item],
            'written': sorted(tree.edit)}


# -----------------------------------------------------------------------------
def verify(root: pathlib.Path, tag: str, rev: str) -> list[str]:
    """
    Return a sentence for each reason the commit rev of the repository
    at root may not be tagged tag: its tree must hold exactly one
    release item whose version is that of the tag, the version module
    must hold that version too, and the item must record the
    dependencies of the runtime lock at rev and the renames since the
    last release tag before rev. The item may have been added by an
    earlier commit.

    """

    version = tag.removeprefix(PREFIX_TAG)
    if not tag.startswith(PREFIX_TAG) or cctool.check.release_record.numbers(version) is None:
        return ['The tag {tag} is not v and a release version, such as v1.2.3.'.format(
                    tag = tag)]

    short      = _git(root, 'rev-parse',
                      '--short={n}'.format(n = cctool.commit.history.LENGTH_SHORT), rev).strip()
    list_file  = [file for file in _git(root, 'ls-tree', '-r', '--name-only', rev, '--',
                                        DIR_RELEASE).split()
                  if file.endswith('.yaml')]
    list_match = [file for file in list_file
                  if _version_of(_shown(root, rev, file)) == version]

    if len(list_match) != 1:
        return ['The tree at {short} holds {count} release items for {version}, not one. Run '
                'cctool release prepare, and commit what it writes.'.format(
                    short = short, count = len(list_match), version = version)]

    file       = list_match[0]
    item       = cctool.graph.parse.load(_shown(root, rev, file))
    module     = cctool.check.release_record.module_version(
                     _shown(root, rev, str(cctool.check.release_record.PATH_MODULE)))
    list_found = []

    if module != version:
        list_found.append('The version module at {short} holds {found}, not {version}.'.format(
                              short = short, found = module, version = version))

    list_recorded = [{str(key): str(value) for (key, value) in package.items()}
                     for package in item.get(KEY_DEPENDENCY) or []]
    if list_recorded != dependencies(_shown(root, rev, PATH_LOCK)):
        list_found.append('{file} does not record the dependencies of {lock} at {short}. Run '
                          'the release gate on that lock, remove the release item, and run '
                          'cctool release prepare again.'.format(
                              file = file, lock = PATH_LOCK, short = short))

    base          = last_tag(root, rev + '^') if cctool.commit.change.is_commit(
                                                    root, rev + '^') else None
    list_expected = [] if base is None else touched(root, base, rev)[1]
    list_recorded = [{str(key): str(value) for (key, value) in rename.items()}
                     for rename in item.get(KEY_RENAME) or []]
    if list_recorded != list_expected:
        list_found.append('{file} does not record the renames since {base}. Remove the release '
                          'item, and run cctool release prepare again.'.format(
                              file = file, base = base))

    return list_found


# -----------------------------------------------------------------------------
def _version_of(text: str) -> str | None:
    """
    Return the version that the release item in text records, or None
    if text holds no release item.

    """

    item = cctool.graph.parse.load(text) if text else None

    if not isinstance(item, dict) or cctool.check.release_record.KEY_VERSION not in item:
        return None
    return str(item[cctool.check.release_record.KEY_VERSION])


# -----------------------------------------------------------------------------
def _shown(root: pathlib.Path, rev: str, file: str) -> str:
    """
    Return the content of file at the commit rev, or an empty string if
    the commit has no such file.

    """

    done = subprocess.run(['git', 'show', '{rev}:{file}'.format(rev = rev, file = file)],
                          cwd            = root,
                          capture_output = True,
                          text           = True,
                          check          = False)

    return done.stdout if done.returncode == 0 else ''


# -----------------------------------------------------------------------------
def dependencies(text: str) -> list[dict[str, str]]:
    """
    Return each package of the runtime lock in text, the content of
    pixi.lock, for each platform it names: the platform, the name, the
    version and the sha256 hash, ordered by platform and name. The
    project itself is left out.

    """

    lock      = YAML_LOCK.load(text) if text else None
    map_entry = {}

    if not isinstance(lock, dict) or not isinstance(lock.get('environments'), dict):
        raise ErrorRelease('{lock} holds no lock to read the runtime packages from. Run pixi '
                           'lock.'.format(lock = PATH_LOCK))

    for entry in lock['packages']:
        for kind in TUPLE_KIND:
            if kind in entry:
                map_entry[(kind, entry[kind])] = entry

    map_env  = lock['environments']
    env      = map_env[ENV_RUNTIME if ENV_RUNTIME in map_env else ENV_DEFAULT]
    list_row = []

    for (platform, list_ref) in env['packages'].items():
        map_name = _named(list_ref, map_entry)
        set_kept = ({package for (package, _) in map_name.values()} if ENV_RUNTIME in map_env
                    else _needed(map_entry[('pypi', URL_PROJECT)], map_name))
        list_row += [dict(zip(TUPLE_KEY_PACKAGE, (str(platform), *package), strict = True))
                     for package in sorted(set_kept)]

    return list_row


# -----------------------------------------------------------------------------
def _named(list_ref: list[dict], map_entry: dict) -> dict[tuple[str, str], tuple]:
    """
    Return each package that list_ref, the packages of one platform of
    an environment, names, but the project, keyed by its kind and name:
    its name, version and hash, and the keys of what it depends on. A
    conda package is keyed by the name of each python package it
    provides as well.

    """

    map_name = {}

    for ref in list_ref:
        ((kind, url),) = ref.items()
        if url == URL_PROJECT:
            continue
        entry = map_entry[(kind, url)]
        if kind == 'pypi':
            name     = str(entry['name'])
            package  = (name, str(entry['version']), str(entry['sha256']))
            list_key = _required(entry)
            map_name[('pypi', _normal(name))] = (package, list_key)
            continue
        file = url.rpartition('/')[2]
        for suffix in TUPLE_SUFFIX:
            file = file.removesuffix(suffix)
        (name, version, _) = file.rsplit('-', 2)
        package            = (name, version, str(entry['sha256']))
        list_key           = [('conda', text.split()[0]) for text in entry.get('depends') or []]
        map_name[('conda', name)] = (package, list_key)
        for purl in entry.get('purls') or []:
            match = REGEX_PURL.match(purl)
            if match is not None:
                map_name[('pypi', _normal(match.group(1)))] = (package, list_key)

    return map_name


# -----------------------------------------------------------------------------
def _required(entry: dict) -> list[tuple[str, str]]:
    """
    Return the keys of the python packages that the lock entry of a
    python package requires. A requirement only an extra asks for is
    left out.

    """

    return [('pypi', _normal(REGEX_NAME_END.split(text, maxsplit = 1)[0]))
            for text in entry.get('requires_dist') or [] if MARK_EXTRA not in text]


# -----------------------------------------------------------------------------
def _needed(project: dict, map_name: dict) -> set[tuple[str, str, str]]:
    """
    Return each package of map_name that the project, the lock entry of
    cc-public, needs to run: those it requires, and those they depend on
    in turn. A virtual package, such as __glibc, which no entry holds,
    is passed over.

    """

    list_todo = _required(project)
    set_kept  = set()
    set_seen  = set()

    while list_todo:
        key = list_todo.pop()
        if key in set_seen or key not in map_name:
            continue
        set_seen.add(key)
        (package, list_key) = map_name[key]
        set_kept.add(package)
        list_todo += list_key

    return set_kept


# -----------------------------------------------------------------------------
def _normal(name: str) -> str:
    """
    Return the normal form of the python package name.

    """

    return REGEX_SEPARATOR.sub('-', name).lower()


# -----------------------------------------------------------------------------
def _git(root: pathlib.Path, *list_arg: str) -> str:
    """
    Return what git prints when run with list_arg in the repository at
    root.

    """

    try:
        return subprocess.run(['git', *list_arg],
                              cwd            = root,
                              capture_output = True,
                              text           = True,
                              check          = True).stdout
    except subprocess.CalledProcessError as error:
        raise ErrorRelease('git {arg} failed: {text}'.format(
                               arg = ' '.join(list_arg), text = error.stderr.strip())) from error
