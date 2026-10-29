"""
---

id_self:                pym_cctool.edit.peer
guid_self:              pym_04d67a470f64404093c79c9d1e040406
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Peer
brief:                  |
                        Set up a peer, and report which release each
                        segment item of a tree pins.
description:            |
                        init writes the segment item of a new peer,
                        which consumes the newest release of the tree
                        that the running cctool reads as the one a
                        segment may consume, with the rights it is
                        given. It covers only what follows the install
                        of cctool, which no command of cctool can
                        make. Writing the dependency of the peer on a
                        release waits on the publishing route.

                        status reports, for each edge of
                        relation_consumes of the segment item of a
                        tree, the release it names, the segment that
                        holds that release, the newest release of that
                        segment, and where that segment is read from.
usage:                  |
                        Called by the commands of
                        pym_cctool.cli.peering.
edge:                   []

...
"""


import pathlib
import re
import uuid

import cctool.check.layout
import cctool.check.release_record
import cctool.check.segment
import cctool.graph.extract


PREFIX_SEGMENT    = 'segment'
DIR_SEGMENT       = '_data/federated_segment'
SUFFIX_YAML       = '.yaml'
ID_MARK           = 'mark_public'
PATTERN_NAME      = '[a-z][a-z0-9]*(_[a-z0-9]+)*'


# -----------------------------------------------------------------------------
class ErrorPeer(Exception):
    """
    The peer cannot be set up or read. The message says why.

    """


# -----------------------------------------------------------------------------
def init(root:      pathlib.Path,
         name:      str,
         title:     str,
         brief:     str,
         rights:    tuple[str, str]) -> str:
    """
    Write the segment item of a new peer at root, named segment_ and
    name, with title, brief and rights, its copyright and its license,
    which consumes the newest release of the tree a segment may
    consume. Return the path of the file written, relative to root.

    """

    if re.fullmatch(PATTERN_NAME, name) is None:
        raise ErrorPeer('{name} is not a name for a segment: use lower case words joined '
                        'by underscores, such as cc_patrol.'.format(name = name))

    map_own = cctool.graph.extract.documents(root)
    if any(cctool.check.segment.segment_id(document) is not None
           for (document, _) in map_own.values()):
        raise ErrorPeer('{root} holds a segment item already, so it is a segment, and is '
                        'not set up again.'.format(root = root))

    (release, map_guid) = _consumable()
    id_self             = '{prefix}_{name}'.format(prefix = PREFIX_SEGMENT, name = name)
    relative            = '{dir}/{id}{suffix}'.format(dir    = DIR_SEGMENT,
                                                      id     = id_self,
                                                      suffix = SUFFIX_YAML)
    map_field           = {
        'id_self':         id_self,
        'guid_self':       '{prefix}_{hex}'.format(prefix = PREFIX_SEGMENT,
                                                   hex    = uuid.uuid4().hex),
        'copyright':       rights[0],
        'license':         rights[1],
        'protective_mark': [{'id_mark':   ID_MARK,
                             'guid_mark': map_guid[ID_MARK]}],
        'title':           title,
        'brief':           brief,
        'edge':            [{'id_relation':   cctool.check.segment.RELATION,
                             'guid_relation': map_guid[cctool.check.segment.RELATION],
                             'id_target':     release,
                             'guid_target':   map_guid[release]}]}

    path = root / relative
    if path.exists():
        raise ErrorPeer('The file {file} exists.'.format(file = relative))

    text = '\n'.join(cctool.check.layout.dump(map_field, 0)) + '\n'
    try:
        text = cctool.check.layout.lay_out(text, pathlib.Path(relative))
    except cctool.check.layout.Unsupported as error:
        raise ErrorPeer('The segment item cannot be laid out: {error}. Give a brief '
                        'whose first line does not start with a space.'.format(
                            error = error)) from error
    path.parent.mkdir(parents = True, exist_ok = True)
    path.write_text(text, encoding = 'utf-8')
    return relative


# -----------------------------------------------------------------------------
def _consumable() -> tuple[str, dict[str, str]]:
    """
    Return the id of the newest release of the tree a segment may
    consume, and the guid of each item of that tree by id.

    """

    for (place, path) in cctool.check.segment.trees():
        package  = (cctool.check.segment.DIR_PACKAGE
                    if place == cctool.check.segment.PLACE_RELEASE else None)
        map_tree = cctool.graph.extract.documents(path, package)
        found    = cctool.check.release_record.newest(map_tree)
        if found is None:
            continue
        facts = cctool.graph.extract.facts_of(map_tree, with_tool = False)
        return (found[2], {row[0]: row[1] for row in facts['item']})

    raise ErrorPeer('cctool reads no tree that holds a release, so a peer has nothing to '
                    'consume. Install cctool from a release, or run it from a checkout.')


# -----------------------------------------------------------------------------
def status(root: pathlib.Path) -> list[tuple[str, str, str, str, str]]:
    """
    Return a row for each edge of relation_consumes of the segment items
    of the tree at root: the segment, the release it names, the segment
    that holds that release, its newest release, and where that segment
    is read from. The last three are empty when no tree read holds the
    release.

    """

    map_own  = cctool.graph.extract.documents(root)
    list_row = []
    map_held = {}

    for (place, path) in cctool.check.segment.trees():
        if path.resolve() == root.resolve():
            continue
        package  = (cctool.check.segment.DIR_PACKAGE
                    if place == cctool.check.segment.PLACE_RELEASE else None)
        map_tree = cctool.graph.extract.documents(path, package)
        segment  = cctool.check.segment.segment_of(map_tree)
        found    = cctool.check.release_record.newest(map_tree)
        if segment is None or found is None:
            continue
        for (document, _) in map_tree.values():
            if isinstance(document, dict):
                map_held[document.get(cctool.graph.extract.KEY_ID_SELF)] = (segment, found[2],
                                                                           place)

    for (_, _, id_self, release) in cctool.check.segment.consumes(map_own):
        (segment, newest, place) = map_held.get(release, ('', '', ''))
        list_row.append((id_self, release, segment, newest, place))

    return sorted(list_row)
