"""
---

id_self:                pym_cc_public.edit.insert
guid_self:              pym_8d6eb3e21b1c4dc186b0e89c42c65450
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Insert an item
brief:                  |
                        Put a new item into a collection held by
                        another item.
description:            |
                        An embedded item has no schema of its own. Its
                        shape is read from the container's schema at
                        the collection it goes into, and every
                        required field is written empty, as new does.
                        Where the shape carries an identity, one is
                        minted, with the key and readable id derived
                        by the convention the container uses: in a
                        register the key is the id; elsewhere the key
                        is a local name and the id is qualified by the
                        container. A collection that is a list is
                        appended to.

...
"""


import re
import uuid

import ruamel.yaml.comments

import cc_public.check.register
import cc_public.check.schema
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.path


KEY_TABLE        = 'table'
KEY_PREFIX       = 'prefix'
KEY_REGEX_ID     = 'regex_id'
KEY_ID_SELF      = 'id_self'
KEY_GUID_SELF    = 'guid_self'
KEY_RELATION     = 'relation'
KEY_PROPERTIES   = 'properties'
KEY_ADDITIONAL   = 'additionalProperties'
KEY_ITEMS        = 'items'
KEY_ALLOF        = 'allOf'
KEY_REF          = '$ref'
KEY_DEFS         = '$defs'

PREFIX_REGISTER  = 'reg'
SEPARATOR        = '_'
SUFFIX           = '.yaml'


# -----------------------------------------------------------------------------
def insert(tree, id_type, name, name_container, path_collection = None,
           id_self = None):
    """
    Put a new item of id_type, called name, into a collection of the
    container, and write the file back. Return (key, id_self).

    """

    table = tree.type_register()[KEY_TABLE]

    if id_type not in table:
        raise cc_public.edit.tree.ErrorItem(
                '{id_type} is not in the type register.'.format(
                                                        id_type = id_type))

    entry_type = table[id_type]
    container  = tree.resolve(name_container)
    document   = tree.document(container)
    is_reg     = container.id_self.split(SEPARATOR, 1)[0] == PREFIX_REGISTER

    if path_collection is None:
        if not is_reg:
            raise cc_public.edit.tree.ErrorItem(
                    '{name} is not a register, so say which collection '
                    'with --at.'.format(name = container.id_self))
        path_collection = KEY_TABLE

    path_full  = cc_public.path.concat(container.path, path_collection)
    collection = _walk(document, path_full, is_create = True)

    if not isinstance(collection, (dict, list)):
        raise cc_public.edit.tree.ErrorItem(
                '{path} in {name} is not a collection.'.format(
                                    path = path_collection,
                                    name = container.id_self))

    (required, properties) = _shape_at(tree, container, path_full,
                                       isinstance(collection, list))
    (key, id_self) = _identity(tree, entry_type, name, container, is_reg,
                               id_self, required, properties)

    if isinstance(collection, dict) and key in collection:
        raise cc_public.edit.tree.ErrorItem(
                '{path} in {name} already holds {key}.'.format(
                                    path = path_collection,
                                    name = container.id_self,
                                    key  = key))

    item = _skeleton(id_self, entry_type[KEY_PREFIX], required, properties)

    if isinstance(collection, dict):
        collection[key] = item
    else:
        collection.append(item)

    cc_public.edit.tree.save(container.filepath, document)
    tree.refresh(container.filepath)

    if id_self is not None:
        made = cc_public.edit.tree.Item(
                    container.filepath,
                    cc_public.path.join(path_full,
                                        key if isinstance(collection, dict)
                                            else len(collection) - 1),
                    id_self, item[KEY_GUID_SELF])
        tree.map_id[id_self]              = made
        tree.map_guid[item[KEY_GUID_SELF]] = made

    return (key, id_self)


# -----------------------------------------------------------------------------
def _shape_at(tree, container, path_full, is_list):
    """
    Return (required keys, properties) for an entry at path_full in the
    container, gathered from every subschema that mentions the place.

    """

    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    map_prefix = cc_public.check.register.map_prefix(tree.type_register())
    (id_schema, reason) = cc_public.check.schema.select_schema(
                            tree.context.map_document[container.filepath],
                            map_prefix)

    if id_schema is None:
        raise cc_public.edit.tree.ErrorItem(reason)

    required   = []
    properties = {}

    for (shape, _) in _entry_shape(map_schema[id_schema], path_full,
                                   map_schema, is_list):
        (req, props) = cc_public.edit.new.gather(shape, map_schema)
        required.extend(r for r in req if r not in required)
        for (key_prop, value) in props.items():
            properties.setdefault(key_prop, value)

    return (required, properties)


# -----------------------------------------------------------------------------
def _identity(tree, entry_type, name, container, is_reg, id_self, required,
              properties):
    """
    Return (key, id_self) by the container's convention: in a register
    the key is the id; elsewhere the key is the local name and the id
    is qualified by the container. An entry with no identity of its own
    has a key and no id.

    """

    if KEY_ID_SELF not in properties and KEY_ID_SELF not in required:
        return (name, None)

    prefix = entry_type[KEY_PREFIX]

    if is_reg:
        key     = prefix + SEPARATOR + name
        id_self = id_self or key
    else:
        key     = name
        id_self = id_self or (prefix + SEPARATOR
                              + container.id_self.split(SEPARATOR, 1)[1]
                              + '.' + name)

    if not re.match(entry_type[KEY_REGEX_ID], id_self):
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} does not match {regex}, the form of a '
                '{id_type} identifier.'.format(
                        id_self = id_self,
                        regex   = entry_type[KEY_REGEX_ID],
                        id_type = entry_type[KEY_ID_SELF]))

    if id_self in tree.map_id:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} already exists.'.format(id_self = id_self))

    return (key, id_self)


# -----------------------------------------------------------------------------
def _skeleton(id_self, prefix, required, properties):
    """
    Return the new entry: its identity where it has one, then every
    required field empty, envelope fields first and relations last.

    """

    item = ruamel.yaml.comments.CommentedMap()

    if id_self is not None:
        item[KEY_ID_SELF]   = id_self
        item[KEY_GUID_SELF] = prefix + SEPARATOR + uuid.uuid4().hex

    for field in cc_public.edit.new.ORDER_ENVELOPE:
        if field in required and field not in item:
            item[field] = cc_public.edit.new.empty(properties.get(field))

    for field in required:
        if field not in item and field != KEY_RELATION:
            item[field] = cc_public.edit.new.empty(properties.get(field))

    if KEY_RELATION in properties or KEY_RELATION in required:
        item[KEY_RELATION] = ruamel.yaml.comments.CommentedSeq()

    return item


# -----------------------------------------------------------------------------
def _walk(node, path, is_create = False):
    """
    Return the node at path, or raise naming what was missing.

    With is_create, a last step absent from a mapping is made as an
    empty mapping: a collection the schema knows about need not exist
    before the first thing is put into it. Anything absent earlier in
    the path is still a mistake to report.

    """

    list_step = cc_public.path.split(path)

    for (index, step) in enumerate(list_step):
        try:
            node = node[int(step)] if isinstance(node, list) else node[step]
        except (KeyError, IndexError, ValueError, TypeError):
            if is_create and index == len(list_step) - 1 \
                          and isinstance(node, dict):
                node[step] = ruamel.yaml.comments.CommentedMap()
                return node[step]
            raise cc_public.edit.tree.ErrorItem(
                    'No {step} at {path}.'.format(step = step,
                                                 path = path)) from None
    return node


# -----------------------------------------------------------------------------
def _entry_shape(schema, path, map_schema, is_list):
    """
    Return every (subschema, owning schema) a member of the collection
    at path must meet.

    An entry is constrained wherever the collection is mentioned, and
    a register's is mentioned twice: by the general register schema and
    by the register's own. All of them are followed, through every
    composed schema, and their members gathered together.

    """

    list_node = [(schema, schema)]

    for step in cc_public.path.split(path):

        found = []

        for (node, root) in list_node:
            found.extend(_properties(node, root, step, map_schema))

        if not found:
            raise cc_public.edit.tree.ErrorItem(
                    'The schema says nothing about {step} in {path}, so '
                    'the shape of an entry there is unknown.'.format(
                                                    step = step, path = path))
        list_node = found

    list_member = []

    for (node, root) in list_node:
        member = node.get(KEY_ITEMS if is_list else KEY_ADDITIONAL)
        if isinstance(member, dict):
            list_member.append(_deref(member, root, map_schema))

    if not list_member:
        raise cc_public.edit.tree.ErrorItem(
                'The schema does not say what a member of {path} looks '
                'like.'.format(path = path))

    return list_member


# -----------------------------------------------------------------------------
def _properties(node, root, step, map_schema):
    """
    Return every (subschema, owning schema) that property step has at
    node, looking through allOf.

    """

    (node, root) = _deref(node, root, map_schema)

    found = []
    own   = (node.get(KEY_PROPERTIES) or {}).get(step)

    if own is not None:
        found.append(_deref(own, root, map_schema))

    for part in node.get(KEY_ALLOF) or []:
        (node_part, root_part) = _deref(part, root, map_schema)
        found.extend(_properties(node_part, root_part, step, map_schema))

    return found


# -----------------------------------------------------------------------------
def _deref(node, root, map_schema):
    """
    Return (node, owning schema) with a $ref followed.

    A reference to another file makes that file the owner; a fragment
    is then looked up in the owner, which is what keeps a local $defs
    reference pointing into the file it was written in.

    """

    ref = node.get(KEY_REF) if isinstance(node, dict) else None

    if ref is None:
        return (node, root)

    (uri, _, fragment) = ref.partition('#')

    if uri:
        target = map_schema.get(uri.rsplit('/', 1)[-1].removesuffix(SUFFIX))
        if target is None:
            return (node, root)
        root = target
    else:
        target = root

    if fragment:
        for step in fragment.strip('/').split('/'):
            target = target.get(step, {})

    return _deref(target, root, map_schema)
