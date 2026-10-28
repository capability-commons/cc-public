"""
---

id_self:                pym_cctool.release.shadow
guid_self:              pym_35338f9fc0464b59ac50438ac8d964a6
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Shadows of what a release leaves behind
brief:                  |
                        Find each item that the package of a release
                        leaves behind but a shipped item names, and
                        write the file of shadows that the package
                        ships in their place.
description:            |
                        WTP ruled on 2026-10-25 that a release ships
                        the whole of _data, with a shadow of each item
                        it leaves behind
                        (ruling_what_data_a_release_ships). The
                        package holds _data and the code of cctool
                        without its tests, as pyproject.toml at
                        tool.hatch.build.targets.wheel says, so an
                        item held in any other file, such as the
                        comment header of pyproject.toml, stays
                        behind. A shadow keeps the id and guid of the
                        item, and its type follows from the prefix of
                        its id, as concept_shadow says. The build of
                        the package calls this module from
                        pym_cctool.release.hook.
edge:                   []

...
"""


import fnmatch
import pathlib
import tomllib

import cctool.check.comment
import cctool.check.layout
import cctool.graph.extract


# What the package holds is read from pyproject.toml at
# tool.hatch.build.targets.wheel: the folders of its packages and of its
# forced includes, less what it excludes. A pattern of the exclusions
# reads as gitignore reads it, so **/ stands for any number of folders.
# The file of shadows goes into the _data of the package.
#
FILE_PROJECT      = 'pyproject.toml'
KEY_TOOL          = 'tool'
KEY_HATCH         = 'hatch'
KEY_BUILD         = 'build'
KEY_TARGETS       = 'targets'
KEY_WHEEL         = 'wheel'
KEY_PACKAGES      = 'packages'
KEY_EXCLUDE       = 'exclude'
KEY_FORCE_INCLUDE = 'force-include'
MARK_ANY_FOLDER   = '**/'
SUFFIX_PYTHON     = '.py'
PATH_PACKAGE      = 'cctool/{dir_data}/{dir_shadow}/{segment}.yaml'

KEY_ID_SEGMENT    = 'id_segment'
KEY_GUID_SEGMENT  = 'guid_segment'
KEY_SHADOW        = 'shadow'
WIDTH_KEY         = 24


# -----------------------------------------------------------------------------
def is_shipped(file: str, table: dict) -> bool:
    """
    ---

    id_self:                pyf_cctool.release.shadow.is_shipped
    guid_self:              pyf_c45ff5f1ca6042b187ecded0edc7a28e
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Whether the package ships a file
    brief:                  |
                            Return True if the package of a release holds
                            the file of the tree, by table, the build
                            table of the wheel in pyproject.toml.
    edge:                   []

    ...
    """

    path     = pathlib.PurePosixPath(file)
    list_dir = [pathlib.PurePosixPath(each) for each in
                [*table.get(KEY_PACKAGES, []), *table.get(KEY_FORCE_INCLUDE, {})]]

    if not any(path == each or each in path.parents for each in list_dir):
        return False

    list_name = [str(path), *(str(each) for each in path.parents)]
    for pattern in table.get(KEY_EXCLUDE, []):
        for form in {pattern, pattern.replace(MARK_ANY_FOLDER, '')}:
            if any(fnmatch.fnmatchcase(name, form) for name in list_name):
                return False
    return True


# -----------------------------------------------------------------------------
def wheel(root: pathlib.Path) -> dict:
    """
    ---

    id_self:                pyf_cctool.release.shadow.wheel
    guid_self:              pyf_2080889ddf49470aa280fba7d2a6d9ba
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Build table of the wheel
    brief:                  |
                            Return the table that says what the wheel
                            holds, from the pyproject.toml of the tree at
                            root, or an empty table if it has none.
    edge:                   []

    ...
    """

    path = root / FILE_PROJECT
    if not path.is_file():
        return {}
    table = tomllib.loads(path.read_text(encoding = 'utf-8'))
    for key in (KEY_TOOL, KEY_HATCH, KEY_BUILD, KEY_TARGETS, KEY_WHEEL):
        table = table.get(key, {})
    return table


# -----------------------------------------------------------------------------
def shadows(root: pathlib.Path) -> tuple[str | None, list[tuple[str, str]]]:
    """
    ---

    id_self:                pyf_cctool.release.shadow.shadows
    guid_self:              pyf_99b9742a43954cd4a73976bbc7471d77
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Items a release leaves behind but names
    brief:                  |
                            Return the segment item of the tree at root,
                            or None if it holds none or more than one, and
                            the id and guid of each item of the tree that
                            the package leaves behind but a shipped item
                            names, by a reference or a mention in prose or
                            in a python comment, sorted by id.
    edge:                   []

    ...
    """

    table        = wheel(root)
    map_document = cctool.graph.extract.documents(root)
    facts        = cctool.graph.extract.facts_of(map_document, with_tool = False)
    map_item     = {}
    set_held     = set()

    for (id_self, guid, _, file, _) in facts['item']:
        map_item.setdefault(id_self, guid)
        map_item.setdefault(guid, id_self)
        if is_shipped(file, table):
            set_held.update((id_self, guid))

    set_named = {row[2] for row in facts['reference'] if is_shipped(row[4], table)}
    set_named.update(row[1] for row in facts['mention'] if is_shipped(row[2], table))
    for file in map_document:
        if (file.endswith(SUFFIX_PYTHON) and is_shipped(file, table)
                and file == cctool.graph.extract.file_of(file)):
            text = (root / file).read_text(encoding = 'utf-8')
            set_named.update(word for (_, word) in cctool.check.comment.mentions(text))

    set_item = {row[0] for row in facts['item']}
    set_id   = {name if name in set_item else map_item[name]
                for name in set_named - set_held if name in map_item}

    return (_segment(facts), sorted((id_self, map_item[id_self]) for id_self in set_id))


# -----------------------------------------------------------------------------
def _segment(facts: cctool.graph.extract.Facts) -> tuple[str, str] | None:
    """
    Return the id and guid of the one segment item of facts, or None if
    they hold none or more than one.

    """

    set_found = {(row[0], row[1]) for row in facts['item']
                 if row[0].startswith(cctool.graph.extract.PREFIX_SEGMENT)}
    return next(iter(set_found)) if len(set_found) == 1 else None


# -----------------------------------------------------------------------------
def text(segment: tuple[str, str], list_shadow: list[tuple[str, str]]) -> str:
    """
    ---

    id_self:                pyf_cctool.release.shadow.text
    guid_self:              pyf_ad088ae5835048cb95a91441765726bb
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  File of shadows
    brief:                  |
                            Return the text of the file of shadows of the
                            segment, the id and guid of its segment item:
                            the segment, then a shadow of each item of
                            list_shadow, laid out as cctool format lays
                            out a data item.
    edge:                   []

    ...
    """

    list_line = [_line(KEY_ID_SEGMENT, segment[0]),
                 _line(KEY_GUID_SEGMENT, segment[1]),
                 _line(KEY_SHADOW, '[]') if not list_shadow else KEY_SHADOW + ':']

    for (id_self, guid) in list_shadow:
        list_line += ['',
                      _line('  - ' + cctool.graph.extract.KEY_ID_SELF, id_self),
                      _line('    guid_self', guid)]

    return cctool.check.layout.format('\n'.join(list_line) + '\n')


# -----------------------------------------------------------------------------
def _line(key: str, value: str) -> str:
    """
    Return the line that gives key the value, with the value at the
    column that cctool format puts it at.

    """

    return (key + ':').ljust(WIDTH_KEY) + value


# -----------------------------------------------------------------------------
def write(root: pathlib.Path, dir_out: pathlib.Path) -> tuple[pathlib.Path, str] | None:
    """
    ---

    id_self:                pyf_cctool.release.shadow.write
    guid_self:              pyf_66bab7f0091348a8be6cf970d1ddaa59
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Write the file of shadows
    brief:                  |
                            Write the file of shadows of the tree at root
                            into the folder dir_out, and return its path
                            and the path it has in the package, or None if
                            the tree holds no one segment item.
    edge:                   []

    ...
    """

    (segment, list_shadow) = shadows(root)

    if segment is None:
        return None

    path = dir_out / (segment[0] + '.yaml')
    path.write_text(text(segment, list_shadow), encoding = 'utf-8')
    return (path, PATH_PACKAGE.format(dir_data   = cctool.graph.extract.DIR_DATA,
                                      dir_shadow = cctool.graph.extract.DIR_SHADOW,
                                      segment    = segment[0]))
