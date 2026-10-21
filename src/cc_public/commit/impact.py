"""
---

id_self:                pym_cc_public.commit.impact
guid_self:              pym_91b4c79e8df24a029693f3513a5da011
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit impact
brief:                  |
                        Find what a commit touches, and the untouched
                        items linked to it: the blast radius of the
                        commit.
description:            |
                        The graph before the commit is read from its
                        first parent, and the graph after it from the
                        commit, or from the staged content. Each item
                        is matched by its guid, so a rename is found
                        as one. impact.lp finds the items touched and
                        walks the links out from them.
usage:                  |
                        Run by cctool impact.
edge:                   []

...
"""


import ast
import hashlib
import json
import pathlib
import tempfile
import typing

import cc_public.commit.change
import cc_public.gate.gate
import cc_public.graph.logic
import cc_public.graph.extract


RULES           = pathlib.Path(__file__).with_name('impact.lp')
TUPLE_DIRECTION = ('in', 'out', 'both')
TUPLE_DELTA     = ('added', 'removed', 'renamed', 'changed')
DEPTH_DEFAULT   = 1

Impact          = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def impact(root:      pathlib.Path,
           rev:       str | None,
           depth:     int = DEPTH_DEFAULT,
           direction: str = 'both') -> Impact:
    """
    Return what the commit rev of the repository at root touches, and
    the untouched items around it, as impact_trees does. The commit is
    compared with its first parent. If rev is None, the staged content
    is compared with HEAD, as the next commit would be.

    """

    with tempfile.TemporaryDirectory() as name:
        dir_before = pathlib.Path(name, 'before')
        dir_after  = pathlib.Path(name, 'after')
        dir_before.mkdir()
        dir_after.mkdir()
        parent = 'HEAD' if rev is None else rev + '^'
        if cc_public.commit.change.is_commit(root, parent):
            cc_public.gate.gate.copy_commit(root, parent, dir_before)
        if rev is None:
            cc_public.gate.gate.copy_staged(root, dir_after)
        else:
            cc_public.gate.gate.copy_commit(root, rev, dir_after)
        return impact_trees(dir_before, dir_after, depth, direction)


# -----------------------------------------------------------------------------
def impact_trees(dir_before: pathlib.Path,
                 dir_after:  pathlib.Path,
                 depth:      int = DEPTH_DEFAULT,
                 direction:  str = 'both') -> Impact:
    """
    Return what the change from the tree in dir_before to the tree in
    dir_after touches, and the untouched items around it.

    touched holds a row for each item the change adds, removes, renames
    or changes: its id, its delta, the id it was if renamed, and the
    file and line that hold it. neighbor holds a row for each link that
    reaches an untouched item, within depth links of a touched one, in
    direction: the item, its depth, the item it is reached from, the
    relation, the direction of the link, and the file and line of the
    item.

    """

    if direction not in TUPLE_DIRECTION:
        raise ValueError('The direction {direction} is not one of {list}.'.format(
                             direction = direction, list = ', '.join(TUPLE_DIRECTION)))

    map_after  = cc_public.graph.extract.documents(dir_after)
    map_before = cc_public.graph.extract.documents(dir_before)
    facts      = cc_public.graph.extract.facts_of(map_after)
    before     = cc_public.graph.extract.facts_of(map_before)

    facts['before_item']             = before['item']
    facts['before_edge']             = before['edge']
    facts['before_reference']        = before['reference']
    facts['before_inverse_relation'] = before['inverse_relation']
    facts['digest']                  = set(digests(dir_after, map_after).items())
    facts['before_digest']           = set(digests(dir_before, map_before).items())
    facts['max_depth']               = {(str(depth),)}
    facts['direction']               = {(direction,)}

    rows       = cc_public.graph.logic.run(facts, RULES.read_text(encoding = 'utf-8'))
    map_place  = {row[0]: (row[3], row[4]) for row in before['item']}
    map_place |= {row[0]: (row[3], row[4]) for row in facts['item']}

    def order(row):
        return (TUPLE_DELTA.index(row[1]), row[0])

    return {'touched':   [(*row, *map_place.get(row[0], ('', '')))
                          for row in sorted(rows['touched'], key = order)],
            'neighbor': [(*row, *map_place.get(row[0], ('', '')))
                          for row in sorted(rows['neighbor'],
                                            key = lambda row: (int(row[1]), row[0], row[2]))]}


# -----------------------------------------------------------------------------
def digests(root: pathlib.Path, map_document: cc_public.graph.extract.Documents) -> dict:
    """
    Return a digest of what each item of the YAML documents of the tree
    at root holds, keyed by its id: its own fields, with each item inside
    it reduced to its id, and, for the item of a file other than a YAML
    document or of a class or function, the source text that holds it.

    """

    map_digest = {}
    map_module = {}

    for (key, (document, _)) in map_document.items():
        if not cc_public.graph.extract.is_document(document):
            continue
        source = _source(root, key, map_module)
        for (id_self, own) in _items(document):
            text = json.dumps(own, sort_keys = True, default = str)
            if id_self == _id_of(document):
                text += source
            map_digest[id_self] = hashlib.blake2b(text.encode('utf-8'),
                                                  digest_size = 16).hexdigest()

    return map_digest


# -----------------------------------------------------------------------------
def _items(node: typing.Any) -> list[tuple[str, typing.Any]]:
    """
    Return each item inside node, node included, with what it holds
    itself: its fields, with each item inside it reduced to its id.

    """

    list_item = []

    def own(value, is_top):
        if isinstance(value, dict):
            id_self = _id_of(value)
            if id_self is not None and not is_top:
                list_item.append((id_self, own(value, True)))
                return id_self
            return {str(key): own(child, False) for (key, child) in value.items()}
        if isinstance(value, list):
            return [own(child, False) for child in value]
        return value

    top = own(node, _id_of(node) is not None)
    if _id_of(node) is not None:
        list_item.append((_id_of(node), top))

    return list_item


# -----------------------------------------------------------------------------
def _id_of(node: typing.Any) -> str | None:
    """
    Return the id of the item node is, or None if it is not one.

    """

    if isinstance(node, dict) and isinstance(node.get(cc_public.graph.extract.KEY_ID_SELF), str):
        return node[cc_public.graph.extract.KEY_ID_SELF]
    return None


# -----------------------------------------------------------------------------
def _source(root: pathlib.Path, key: str, map_module: dict) -> str:
    """
    Return the source text of what holds the YAML document keyed by key:
    the text of the class or function for a key that names one, the text
    of the file for any file but a YAML document, and nothing otherwise.

    """

    file = cc_public.graph.extract.file_of(key)
    path = root / file

    if path.suffix == cc_public.graph.extract.SUFFIX_YAML:
        return ''

    text = path.read_bytes().decode('utf-8', errors = 'replace')

    if key == file:
        return text

    if file not in map_module:
        map_module[file] = ast.parse(text)
    node = map_module[file]
    for name in key.split(cc_public.graph.extract.DELIM_DEFINITION)[1:]:
        node = next(child for child in node.body
                    if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                    and child.name == name)

    return ast.get_source_segment(text, node) or ''
