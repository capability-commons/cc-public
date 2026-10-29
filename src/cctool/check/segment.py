"""
---

id_self:                pym_cctool.check.segment
guid_self:              pym_bb8b62b7ee73487b9e470f3c36cd4904
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Segment
brief:                  |
                        Read the trees that the segment being checked
                        consumes, and tell its failures from those of
                        the trees it consumes.
description:            |
                        A segment item names, with an edge of
                        relation_consumes, the release item of each
                        segment it consumes. The check reads each
                        consumed tree beside the tree being checked,
                        with its documents keyed under the folder that
                        DIR_CONSUMED in pym_cctool.graph.extract
                        names, and checks the two together.

                        A consumed tree is the cctool package that is
                        running: its installed _data and code when it
                        was installed from a release, or the checkout
                        it runs from. A row of a check that names only
                        items and files of consumed trees is a notice,
                        and not a failure, since the segment being
                        checked cannot change them. Advice about them
                        is left out.
edge:                   []

...
"""


import pathlib

import cctool
import cctool.check.release_record
import cctool.graph.extract


# Where a consumed tree is read from: an installed release of a package,
# or a checkout of the tree that it is built from.
#
PLACE_RELEASE     = 'release'
PLACE_CHECKOUT    = 'checkout'

# An installed cctool package holds the code that is under src/cctool in
# its tree, and its _data folder as it is in the tree.
#
DIR_PACKAGE       = pathlib.PurePosixPath('src/cctool')
DIR_IMPORT_ROOT   = 'src'

RELATION          = 'relation_consumes'
KEY_EDGE          = 'edge'
COLUMNS           = ('file', 'line', 'id', 'release', 'newest', 'place')

Rows              = list[tuple[str, ...]]


# -----------------------------------------------------------------------------
def trees() -> list[tuple[str, pathlib.Path]]:
    """
    ---

    id_self:                pyf_cctool.check.segment.trees
    guid_self:              pyf_fe364d5e9cb14841974ad62ff6cc3c78
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Trees that may be consumed
    brief:                  |
                            Return where each tree that a segment may
                            consume is read from, and its folder: the
                            folder of the running cctool package if it was
                            installed from a release, or the root of the
                            checkout it runs from.
    edge:                   []

    ...
    """

    dir_package = pathlib.Path(cctool.__file__).resolve().parent
    dir_root    = dir_package.parent.parent

    if (dir_package / cctool.graph.extract.DIR_DATA).is_dir():
        return [(PLACE_RELEASE, dir_package)]
    if (dir_package.parent.name == DIR_IMPORT_ROOT
            and (dir_root / cctool.graph.extract.DIR_DATA).is_dir()):
        return [(PLACE_CHECKOUT, dir_root)]
    return []


# -----------------------------------------------------------------------------
def union(root: pathlib.Path) -> cctool.graph.extract.Documents:
    """
    ---

    id_self:                pyf_cctool.check.segment.union
    guid_self:              pyf_d141e25605d14218b091f4cf671363bd
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Documents of a segment and what it consumes
    brief:                  |
                            Return the documents of the tree under root,
                            with those of each tree that its segment item
                            consumes, keyed as consumed returns them.
    edge:                   []

    ...
    """

    map_own              = cctool.graph.extract.documents(root)
    (map_consumed, _, _) = consumed(root, map_own)
    return {**map_own, **map_consumed}


# -----------------------------------------------------------------------------
def consumed(root:         pathlib.Path,
             map_document: cctool.graph.extract.Documents) -> tuple[
                 cctool.graph.extract.Documents, Rows, Rows]:
    """
    ---

    id_self:                pyf_cctool.check.segment.consumed
    guid_self:              pyf_791513001bda4f70aca0728cc6dda137
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Documents of the consumed trees
    brief:                  |
                            Return the documents of each tree that the
                            segment items of map_document consume, keyed
                            under the folder of consumed trees and the
                            segment of each, and the rows that disagree
                            with the newest release item of a consumed
                            tree, as failures and as notices.
    description:            |
                            A segment item that names a release item which
                            a consumed tree holds, but which is not its
                            newest, disagrees with that tree. That fails
                            while the tree is an installed release, which
                            is pinned, and is a notice while it is a
                            checkout, which moves ahead of the release
                            item named. A tree that holds no segment item,
                            or the tree at root itself, is not read.
    edge:                   []

    ...
    """

    list_consumes = consumes(map_document)
    map_consumed  = {}
    list_failure  = []
    list_notice   = []

    if not list_consumes:
        return (map_consumed, list_failure, list_notice)

    for (place, path) in trees():
        if path.resolve() == root.resolve():
            continue
        package  = DIR_PACKAGE if place == PLACE_RELEASE else None
        map_tree = cctool.graph.extract.documents(path, package)
        segment  = segment_of(map_tree)
        if segment is None:
            continue
        map_consumed.update({str(pathlib.PurePosixPath(cctool.graph.extract.DIR_CONSUMED,
                                                       segment, key)): value
                             for (key, value) in map_tree.items()})
        list_row = _disagreements(list_consumes, map_tree, place)
        (list_failure if place == PLACE_RELEASE else list_notice).extend(list_row)

    return (map_consumed, list_failure, list_notice)


# -----------------------------------------------------------------------------
def consumes(map_document: cctool.graph.extract.Documents) -> list[tuple[str, int, str, str]]:
    """
    Return the file and line of each segment item of the documents,
    its id, and the release item that each of its edges of RELATION
    names.

    """

    list_consumes = []

    for (key, (document, line)) in map_document.items():
        id_self = segment_id(document)
        if id_self is None:
            continue
        for edge in document.get(KEY_EDGE) or []:
            if (isinstance(edge, dict)
                    and edge.get(cctool.graph.extract.KEY_ID_RELATION) == RELATION):
                list_consumes.append((cctool.graph.extract.file_of(key), line, id_self,
                                      str(edge.get(cctool.graph.extract.KEY_ID_TARGET))))

    return list_consumes


# -----------------------------------------------------------------------------
def segment_of(map_document: cctool.graph.extract.Documents) -> str | None:
    """
    ---

    id_self:                pyf_cctool.check.segment.segment_of
    guid_self:              pyf_71c9105d812749949ddb9037b6b12ac2
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Segment item of a tree
    brief:                  |
                            Return the id of the one segment item of the
                            documents, or None if they hold none or more
                            than one.
    edge:                   []

    ...
    """

    set_id = {segment_id(document) for (document, _) in map_document.values()} - {None}
    return next(iter(set_id)) if len(set_id) == 1 else None


# -----------------------------------------------------------------------------
def segment_id(document: object) -> str | None:
    """
    Return the id of document if it is a segment item, or else None.

    """

    if not isinstance(document, dict):
        return None
    id_self = document.get(cctool.graph.extract.KEY_ID_SELF)
    if isinstance(id_self, str) and id_self.startswith(cctool.graph.extract.PREFIX_SEGMENT):
        return id_self
    return None


# -----------------------------------------------------------------------------
def _disagreements(list_consumes: list[tuple[str, int, str, str]],
                   map_tree:      cctool.graph.extract.Documents,
                   place:         str) -> Rows:
    """
    Return a row for each release item that list_consumes names, and
    that the consumed tree map_tree holds, but not as its newest, read
    from place.

    """

    found = cctool.check.release_record.newest(map_tree)
    if found is None:
        return []

    newest  = found[2]
    set_id  = {document.get(cctool.graph.extract.KEY_ID_SELF)
               for (document, _) in map_tree.values() if isinstance(document, dict)}

    return [(file, str(line), id_self, release, newest, place)
            for (file, line, id_self, release) in list_consumes
            if release in set_id and release != newest]


# -----------------------------------------------------------------------------
def attribute(map_row: dict[str, Rows],
              facts:   cctool.graph.extract.Facts) -> tuple[dict[str, Rows], dict[str, Rows]]:
    """
    ---

    id_self:                pyf_cctool.check.segment.attribute
    guid_self:              pyf_c971d1b3dab24615917f7320242b7fde
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Attribute rows to segments
    brief:                  |
                            Split the rows of each check in two: those
                            that name an item or file of the tree being
                            checked, or none at all, and those that name
                            only items and files of consumed trees. Each
                            is keyed by check, with the checks that have
                            no rows left out.
    edge:                   []

    ...
    """

    map_file = {}
    for (id_self, _, _, file, _) in facts['item']:
        map_file.setdefault(id_self, set()).add(file)
    for (file,) in facts['tree_file']:
        map_file.setdefault(file, set()).add(file)

    map_own      = {}
    map_consumed = {}

    for (name, list_row) in map_row.items():
        for row in list_row:
            set_file = set().union(*(map_file.get(str(value), set()) for value in row))
            is_own   = not set_file or any(cctool.graph.extract.consumer(file) is None
                                           for file in set_file)
            (map_own if is_own else map_consumed).setdefault(name, []).append(row)

    return (map_own, map_consumed)
