"""
---

id_self:                pym_cc_public.edit.rename
guid_self:              pym_5fc4c54cf6934f2e822a1b3f3a2b664b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Rename an item
brief:                  |
                        Give an item a new readable id, and carry the
                        change to everything that names it.
description:            |
                        The guid is the truth and never changes. The
                        readable id changes in its declaration, in the
                        file name where the item is a file, in every
                        embedded item whose id is qualified by it, and
                        in every reference that pairs the id with the
                        guid. A mention of the old id in prose is
                        reported and left, since prose is written, not
                        derived.

...
"""


import collections
import re

import cc_public.check.reference
import cc_public.check.register
import cc_public.edit.tree
import cc_public.path


KEY_ID_SELF    = 'id_self'
KEY_TABLE      = 'table'
KEY_REGEX_ID   = 'regex_id'
PREFIX_GUID    = 'guid_'
PREFIX_ID      = 'id_'
SEPARATOR      = '_'
DELIM          = '.'
SUFFIX_PYTHON  = cc_public.edit.tree.SUFFIX_PYTHON

Report = collections.namedtuple('Report', ['map_rename', 'list_filepath',
                                           'list_mention'])


# -----------------------------------------------------------------------------
def rename(tree, name, id_new):
    """
    Rename the item called name to id_new, and write every file touched.

    Return a Report: the ids renamed, old to new, including the embedded
    items qualified by the one named; the files written; and the
    places where prose mentions the old id, as (filepath, path).

    An item under a local key is qualified by its holder, so only the
    last step of its id may change, and its key changes with it.
    Whatever names the key elsewhere, a port address in an edge for
    one, is a value the caller sets.

    """

    item = tree.resolve(name)

    if item.path and not _is_register_entry(item) \
            and id_new.rsplit(DELIM, 1)[0] != item.id_self.rsplit(DELIM, 1)[0]:
        raise cc_public.edit.tree.ErrorItem(
                '{name} is qualified by the item holding it, so only its '
                'last step can change. Rename the holder for the '
                'rest.'.format(name = name))

    if item.filepath.suffix == SUFFIX_PYTHON:
        raise cc_public.edit.tree.ErrorItem(
                '{name} is a python file, whose name is its place on the '
                'import path. Move it with the file.'.format(name = name))

    if id_new in tree.map_id:
        raise cc_public.edit.tree.ErrorItem(
                '{id_new} already exists.'.format(id_new = id_new))

    _validate(tree, id_new)

    map_rename   = _cascade(tree, item.id_self, id_new)
    map_guid     = {tree.resolve(old).guid_self: new
                            for (old, new) in map_rename.items()}
    map_document = {}

    for (old, new) in map_rename.items():
        it  = tree.resolve(old)
        doc = _document(tree, it.filepath, map_document)
        cc_public.path.write(doc, cc_public.path.join(it.path, KEY_ID_SELF), new)
        if it.path:
            parent  = _parent(doc, it.path)
            key_old = cc_public.path.split(it.path)[-1]
            key_new = new if key_old == old else new.rsplit(DELIM, 1)[-1]
            if key_old != key_new:
                _rekey(parent, key_old, key_new)

    for filepath in list(tree.context.map_document):
        doc = map_document.get(filepath) or tree.document(
                        cc_public.edit.tree.Item(filepath, '', None, None))
        if _repoint(doc, map_guid):
            map_document[filepath] = doc

    list_mention = _mentions(tree, set(map_rename))

    for (filepath, doc) in sorted(map_document.items()):
        cc_public.edit.tree.save(filepath, doc)
        tree.refresh(filepath)

    list_filepath = sorted(map_document)
    filepath_old  = item.filepath

    if not item.path:
        target = item.filepath.with_name(id_new + item.filepath.suffix)
        item.filepath.rename(target)
        tree.context.map_document[target] = \
                            tree.context.map_document.pop(item.filepath)
        list_filepath = [target if f == item.filepath else f
                                                for f in list_filepath]
        for it in tree.map_guid.values():
            if it.filepath == filepath_old:
                it.filepath = target

    for (old, new) in map_rename.items():
        it            = tree.map_id.pop(old)
        it.id_self    = new
        it.path       = _path_new(it.path, old, new)
        tree.map_id[new] = it

    return Report(map_rename, list_filepath, list_mention)


# -----------------------------------------------------------------------------
def _path_new(path, old, new):
    """
    Return path with its last step renamed as the item was.

    """

    if not path:
        return path

    steps = cc_public.path.split(path)
    last  = steps[-1]
    steps[-1] = new if last == old else \
                new.rsplit(DELIM, 1)[-1] if last == old.rsplit(DELIM, 1)[-1] \
                else last
    out = ''
    for step in steps:
        out = cc_public.path.join(out, step)
    return out


# -----------------------------------------------------------------------------
def _document(tree, filepath, map_document):
    """
    Return the round trip document for filepath, one per file, so that
    two renames landing in one file land in one document.

    """

    if filepath not in map_document:
        map_document[filepath] = tree.document(
                        cc_public.edit.tree.Item(filepath, '', None, None))

    return map_document[filepath]


# -----------------------------------------------------------------------------
def _cascade(tree, id_old, id_new):
    """
    Return {old: new} for the item and every item its id qualifies.

    An embedded item's id is its prefix, the body of its container's
    id, a full stop and its key: prt_draft.record under cmp_draft. So
    the container's new body is carried into each.

    """

    body_old = id_old.split(SEPARATOR, 1)[1]
    body_new = id_new.split(SEPARATOR, 1)[1]
    out      = {id_old: id_new}

    for id_item in tree.map_id:
        (prefix, _, body) = id_item.partition(SEPARATOR)
        if body.startswith(body_old + DELIM):
            out[id_item] = prefix + SEPARATOR + body_new + body[len(body_old):]

    return out


# -----------------------------------------------------------------------------
def _validate(tree, id_new):
    prefix     = id_new.split(SEPARATOR, 1)[0]
    map_prefix = cc_public.check.register.map_prefix(tree.type_register())
    entry      = map_prefix.get(prefix)

    if entry is None:
        raise cc_public.edit.tree.ErrorItem(
                'No type has the prefix {prefix}.'.format(prefix = prefix))

    if not re.match(entry[KEY_REGEX_ID], id_new):
        raise cc_public.edit.tree.ErrorItem(
                '{id_new} does not match {regex}, the form of a {type} '
                'id.'.format(id_new = id_new, regex = entry[KEY_REGEX_ID],
                             type = entry[KEY_ID_SELF]))


# -----------------------------------------------------------------------------
def _is_register_entry(item):
    steps = cc_public.path.split(item.path)
    return len(steps) == 2 and steps[0] == KEY_TABLE and steps[1] == item.id_self


# -----------------------------------------------------------------------------
def _parent(document, path):
    node = document
    for step in cc_public.path.split(path)[:-1]:
        node = node[int(step)] if isinstance(node, list) else node[step]
    return node


# -----------------------------------------------------------------------------
def _rekey(mapping, old, new):
    """
    Replace key old with new in place, keeping its position.

    """

    position = list(mapping).index(old)
    value    = mapping.pop(old)
    mapping.insert(position, new, value)


# -----------------------------------------------------------------------------
def _repoint(document, map_guid):
    """
    Set the readable id beside each reference to a renamed guid. Return
    whether anything changed.

    """

    changed = False

    for (path, key, guid, _id_advisory) in \
            cc_public.check.reference.iter_reference(document):
        if guid not in map_guid or not key.startswith(PREFIX_GUID):
            continue
        key_id = PREFIX_ID + key[len(PREFIX_GUID):]
        holder = _parent(document, path)
        if holder.get(key_id) != map_guid[guid]:
            holder[key_id] = map_guid[guid]
            changed        = True

    return changed


# -----------------------------------------------------------------------------
def _mentions(tree, set_id):
    """
    Return [(filepath, path)] where a string value other than a
    declaration or reference contains one of the ids as a whole word.

    """

    regex = re.compile(r'(?<![a-z0-9_.])(' + '|'.join(
                        re.escape(i) for i in sorted(set_id, key = len,
                                                     reverse = True))
                       + r')(?![a-z0-9_])')
    out   = []

    for (filepath, document) in tree.context.map_document.items():
        for (path, value) in _iter_string(document):
            key = cc_public.path.split(path)[-1]
            if key.startswith((PREFIX_ID, PREFIX_GUID)):
                continue
            if regex.search(value):
                out.append((filepath, path))

    return out


# -----------------------------------------------------------------------------
def _iter_string(node, path = ''):
    if isinstance(node, dict):
        for (key, value) in node.items():
            yield from _iter_string(value, cc_public.path.join(path, key))
    elif isinstance(node, list):
        for (idx, value) in enumerate(node):
            yield from _iter_string(value, cc_public.path.join(path, idx))
    elif isinstance(node, str):
        yield (path, node)
