"""
---

id_self:                pym_cctool.check.release_record
guid_self:              pym_6ff6b471ba934615b8eb0cf80bf31479
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Release record
brief:                  |
                        Read the version module and the release items
                        of a tree, and find where they disagree.
description:            |
                        The version module holds the version that the
                        package build and the command line read, and
                        each release item records one release. The
                        release step writes both, so the newest
                        release item and the module hold one version;
                        the check version_disagreement in
                        pym_cctool.check.check reports a tree where
                        they do not. This module imports only the
                        graph extractor, so that the check can use it.
edge:                   []

...
"""


import pathlib
import re

import cctool.graph.extract
import cctool.graph.prefix


# The version module, which the package build and the command line read,
# and the line in it that holds the version.
#
PATH_MODULE       = pathlib.PurePosixPath('src/cctool/version.py')
REGEX_VERSION     = re.compile(r"^(VERSION *= *')([^']*)(')", re.MULTILINE)

# A release version is the three numbers of SemVer 2.0.0, with no
# pre-release or build label, and its item is named for it.
#
REGEX_SEMVER      = re.compile(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)')
PREFIX            = cctool.graph.prefix.stem('type_release')
KEY_VERSION       = 'version'
COLUMNS           = ('file', 'line', 'id', 'version', 'module')


# -----------------------------------------------------------------------------
def module_version(text: str) -> str | None:
    """
    Return the version that text, the source of the version module,
    holds, or None if it holds none.

    """

    match = REGEX_VERSION.search(text)
    return None if match is None else match.group(2)


# -----------------------------------------------------------------------------
def numbers(version: str) -> tuple[int, int, int] | None:
    """
    Return the major, minor and patch numbers of version, or None if
    it is not a release version.

    """

    match = REGEX_SEMVER.fullmatch(version)
    return None if match is None else tuple(int(part) for part in match.groups())


# -----------------------------------------------------------------------------
def newest(map_document: cctool.graph.extract.Documents) -> tuple[str, str, str, int] | None:
    """
    Return the release item of the documents with the highest version:
    its file, its line, its id and its version. Return None if there is
    no release item.

    """

    list_found = []

    for (key, (document, line)) in map_document.items():
        if not isinstance(document, dict):
            continue
        id_self = document.get(cctool.graph.extract.KEY_ID_SELF)
        version = document.get(KEY_VERSION)
        if (isinstance(id_self, str) and id_self.startswith(PREFIX)
                and isinstance(version, str) and numbers(version) is not None):
            list_found.append((numbers(version), cctool.graph.extract.file_of(key), line,
                               id_self, version))

    if not list_found:
        return None

    (_, file, line, id_self, version) = max(list_found)
    return (file, line, id_self, version)


# -----------------------------------------------------------------------------
def disagreements(root:         pathlib.Path,
                  map_document: cctool.graph.extract.Documents,
                  map_text:     dict[str, str | bytes | None] | None = None
                  ) -> list[tuple[str, ...]]:
    """
    Return a row for the newest release item of the tree at root if
    the version module holds another version: the file and line of the
    item, its id, its version, and the version the module holds. A tree
    with no version module, or no release item, has nothing to compare.
    The version module is read from map_text if that holds it, as an
    edit leaves it, and from the disk otherwise.

    """

    path  = root / PATH_MODULE
    found = newest(map_document)

    if map_text and str(PATH_MODULE) in map_text:
        text = map_text[str(PATH_MODULE)]
        text = text.decode('utf-8') if isinstance(text, bytes) else text
    elif path.is_file():
        text = path.read_text(encoding = 'utf-8')
    else:
        text = None

    if found is None or text is None:
        return []

    (file, line, id_self, version) = found
    module = module_version(text)

    if module == version:
        return []

    return [(file, str(line), id_self, version, str(module))]
