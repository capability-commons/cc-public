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
                        number and an empty list is a list. A string
                        is stored as prose or as a datum by the
                        schema: unbounded means prose, held as a block
                        scalar, which is what marks it as prose to the
                        printer; a length, pattern, enumeration,
                        constant or format means a datum. Deeper than
                        one step below an item a line break decides,
                        and a field already held as prose stays prose.
                        Prose given as such is stored as a block
                        scalar whatever the schema says.
relation:               []

...
"""


import ruamel.yaml
import ruamel.yaml.comments
import ruamel.yaml.scalarstring

import cc_public.edit.tree
import cc_public.path


KEY_RELATION = 'relation'

# What bounds a string to a line, and so marks a datum in a schema.
#
BOUND        = ('maxLength', 'pattern', 'enum', 'const', 'format', '$ref')


# -----------------------------------------------------------------------------
def set_field(tree, name, path, value = None, prose = None):
    """
    Set path within the item called name, and write the file back.

    Exactly one of value and prose is given. prose is text stored as a
    block scalar, given a final newline. value is stored as it is, a
    caller with YAML text reading it first, except that a string is
    stored as prose where the schema says the field is prose: a string
    the schema leaves unbounded, with no length, pattern, enumeration
    or format, is prose, and one it bounds is a datum. Where the schema
    says nothing of the field, a string holding a line break is prose,
    and a field already held as prose stays prose.

    """

    if (value is None) == (prose is None):
        raise ValueError('Give a value or prose, not both and not neither.')

    item = tree.resolve(name)

    if prose is not None:
        content = ruamel.yaml.scalarstring.LiteralScalarString(
                                                    prose.rstrip('\n') + '\n')
    elif isinstance(value, str) and is_prose(tree, item, path, value):
        content = ruamel.yaml.scalarstring.LiteralScalarString(
                                                    value.rstrip('\n') + '\n')
    else:
        content = _blocks(value)

    document = tree.document(item)

    path_full = cc_public.path.concat(item.path, path)
    cc_public.path.write(document, path_full, content)

    # A field already held as prose stays prose: the round trip keeps
    # the block style over a plain string put in its place. What it
    # does not keep is the final newline every block here ends with.
    #
    node = document
    for step in cc_public.path.split(path_full):
        node = node[int(step)] if isinstance(node, list) else node[step]
    if isinstance(node, ruamel.yaml.scalarstring.LiteralScalarString) \
            and not node.endswith('\n'):
        cc_public.path.write(document, path_full,
                             ruamel.yaml.scalarstring.LiteralScalarString(node + '\n'))

    _relation_last(document, item.path, path)
    cc_public.edit.tree.save(item.location, document)
    tree.refresh(item.filepath)

    return item



# -----------------------------------------------------------------------------
def is_prose(tree, item, path, value):
    """
    Return whether a string set at path on item is prose, by the
    schema where it speaks of the field and by the value where it does
    not.

    The schema speaks of a field one step below the item: a top level
    item's own field, or an embedded item's. A string it leaves
    unbounded is prose; one it bounds by length, pattern, enumeration,
    constant or format is a datum, since a datum fits a line and prose
    does not. Deeper paths, and fields no schema names, are prose
    where the value holds a line break.

    """

    list_step = cc_public.path.split(path)
    sub       = _subschema(tree, item, list_step[0]) if len(list_step) == 1 else None

    if not isinstance(sub, dict):
        return '\n' in value

    if sub.get('type') not in (None, 'string'):
        return False

    return not any(key in sub for key in BOUND)


# -----------------------------------------------------------------------------
def _subschema(tree, item, key):
    """
    Return the schema of the field key on item, or None where no schema
    names it.

    """

    import cc_public.check.register
    import cc_public.check.schema
    import cc_public.edit.insert
    import cc_public.edit.new

    try:
        if item.path:
            # The shape of a member of the collection holding the item,
            # which is the item's path with its own key taken off.
            #
            list_step  = cc_public.path.split(item.path)
            collection = ''
            for step in list_step[:-1]:
                collection = cc_public.path.join(collection, step)
            holder = cc_public.edit.tree.Item(item.filepath, '', None, None, item.location)
            (_, properties) = cc_public.edit.insert.shape_at(
                                    tree, holder, collection, list_step[-1].isdigit())
        else:
            map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
            map_prefix = cc_public.check.register.map_prefix(tree.type_register())
            (id_schema, _) = cc_public.check.schema.select_schema(
                                    tree.context.map_document[item.location], map_prefix)
            if id_schema is None or id_schema not in map_schema:
                return None
            (_, properties) = cc_public.edit.new.gather(map_schema[id_schema], map_schema)
    except (cc_public.edit.tree.ErrorItem, KeyError, TypeError):
        return None

    return properties.get(key)


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
