"""
---

id_self:                pym_cc_public.edit.field
guid_self:              pym_8f69052f5308480aba6652d5fd486140
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Set a field
brief:                  |
                        Set one field of one item, named by dot path.
description:            |
                        The value is read as YAML, so a number is a
                        number and an empty list is a list. Prose is
                        read from a stream and stored as a block
                        scalar, which is what marks it as prose to the
                        printer.
relation:               []

...
"""


import ruamel.yaml
import ruamel.yaml.comments
import ruamel.yaml.scalarstring

import cc_public.edit.tree
import cc_public.path


KEY_RELATION = 'relation'


# -----------------------------------------------------------------------------
def set_field(tree, name, path, value = None, prose = None):
    """
    Set path within the item called name, and write the file back.

    Exactly one of value and prose is given. value is stored as it is,
    a string as a string; a caller with YAML text reads it first. prose
    is text stored as a block scalar, given a final newline.

    """

    if (value is None) == (prose is None):
        raise ValueError('Give a value or prose, not both and not neither.')

    if prose is not None:
        content = ruamel.yaml.scalarstring.LiteralScalarString(
                                                    prose.rstrip('\n') + '\n')
    else:
        content = _blocks(value)

    item     = tree.resolve(name)
    document = tree.document(item)

    cc_public.path.write(document, cc_public.path.concat(item.path, path),
                         content)

    _relation_last(document, item.path, path)
    cc_public.edit.tree.save(item.location, document)
    tree.refresh(item.filepath)

    return item



# -----------------------------------------------------------------------------
def _relation_last(document, path_item, path_field):
    """
    Keep an item's relation list as its last key.

    A field set for the first time is appended after everything,
    including the edges. Every item here writes its edges last, so the
    list is moved back to the end where a new key has landed after it.

    """

    node = document

    for step in cc_public.path.split(path_item):
        node = node[int(step)] if isinstance(node, list) else node[step]

    list_step = cc_public.path.split(path_field)

    for step in list_step[:-1]:
        node = node[int(step)] if isinstance(node, list) else node[step]

    if isinstance(node, dict) and KEY_RELATION in node \
                              and list(node)[-1] != KEY_RELATION:
        node[KEY_RELATION] = node.pop(KEY_RELATION)


# -----------------------------------------------------------------------------
def _blocks(value):
    """
    Return value with every string holding a line break made a block
    scalar, however deep it sits, since a line break is what marks
    prose to the printer and a quoted scalar spanning lines is not
    something the printer lays out.

    """

    if isinstance(value, str):
        if '\n' in value:
            return ruamel.yaml.scalarstring.LiteralScalarString(
                                                    value.rstrip('\n') + '\n')
        return value

    if isinstance(value, dict):
        return {k: _blocks(v) for (k, v) in value.items()}

    if isinstance(value, list):
        return [_blocks(v) for v in value]

    return value


# -----------------------------------------------------------------------------
def unset_field(tree, name, path):
    """
    Remove path from the item called name, and write the file back.

    The last step is removed from its parent, a key from a mapping or
    an index from a sequence. A path that is not there is reported.

    """

    item      = tree.resolve(name)
    document  = tree.document(item)
    list_step = cc_public.path.split(cc_public.path.concat(item.path, path))

    if not list_step:
        raise KeyError('An empty path names the whole item.')

    parent = document
    above  = None                     # the parent's own parent and step

    for step in list_step[:-1]:
        above  = (parent, step)
        parent = parent[int(step)] if isinstance(parent, list) else parent[step]

    last = list_step[-1]

    try:
        if isinstance(parent, list):
            del parent[int(last)]
        else:
            del parent[last]
    except (KeyError, IndexError, ValueError):
        raise KeyError('No {step} at {path}.'.format(step = last,
                                                    path = path)) from None

    # A mapping or a sequence emptied of its last member keeps the
    # comment tokens of what it held, and the dumper then writes it
    # badly. A fresh empty one in its place carries nothing.
    #
    if above is not None and isinstance(parent, (dict, list)) and not parent:
        (grand, step) = above
        fresh         = ruamel.yaml.comments.CommentedMap() if isinstance(parent, dict) \
                        else ruamel.yaml.comments.CommentedSeq()
        if isinstance(grand, list):
            grand[int(step)] = fresh
        else:
            grand[step] = fresh

    cc_public.edit.tree.save(item.location, document)
    tree.refresh(item.filepath)

    return item
