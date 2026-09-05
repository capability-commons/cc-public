"""
---

id_self:                pym_cc_public.edit.new
guid_self:              pym_c2487d64bf424a308262068b32de1ae4
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  New item
brief:                  |
                        Make a data item of a type, with its identity
                        minted and every required field present and
                        empty.
description:            |
                        The skeleton comes from the type's schema:
                        each required field, through every schema it
                        composes, is present with an empty value of
                        the right kind, and the item fails its checks
                        until every such field is written. Rights come
                        from the tool's defaults. A package or a
                        module is written as a file holding only its
                        docstring.

...
"""


import io
import pathlib
import re
import uuid

import ruamel.yaml
import ruamel.yaml.comments

import cc_public.edit.tree
import cc_public.layout


KEY_TABLE      = 'table'
KEY_PREFIX     = 'prefix'
KEY_REGEX_ID   = 'regex_id'
KEY_RELATION   = 'relation'
KEY_ID_REL     = 'id_relation'
KEY_ID_TARGET  = 'id_target'
KEY_REQUIRED   = 'required'
KEY_PROPERTIES = 'properties'
KEY_ALLOF      = 'allOf'
KEY_REF        = '$ref'
KEY_TYPE       = 'type'

REL_SPECIFIED  = 'r_is_specified_by_schema'
SUFFIX         = '.yaml'

# Source items. A package or a module is a file, and a file holding
# only a docstring is a valid one, so new can make it. A class or a
# function lives inside a module and is written there.
#
PREFIX_PACKAGE  = 'pyp'
PREFIX_MODULE   = 'pym'
PREFIX_EMBEDDED = ('pyc', 'pyf')
NAME_PACKAGE    = '__init__.py'
SUFFIX_PYTHON   = '.py'

# The envelope, in the order every item here writes it.
#
ORDER_ENVELOPE = ('id_self', 'guid_self', 'copyright', 'license',
                  'protective_mark', 'status', 'title', 'brief',
                  'description', 'usage', 'note')

EMPTY = {'string':  '',
         'object':  ruamel.yaml.comments.CommentedMap,
         'array':   ruamel.yaml.comments.CommentedSeq,
         'integer': 0,
         'number':  0,
         'boolean': False}


# -----------------------------------------------------------------------------
def new(tree, id_type, id_self, defaults, dirpath_out = None, guid = None):
    """
    Make the item and write it. Return its filepath.

    defaults holds copyright, license and id_mark. The directory is
    given, or is where items of this type already live. guid is minted
    here unless the caller minted one to build the id from.

    """

    table = tree.type_register()[KEY_TABLE]

    if id_type not in table:
        raise cc_public.edit.tree.ErrorItem(
                '{id_type} is not in the type register.'.format(
                                                        id_type = id_type))

    entry  = table[id_type]
    prefix = entry[KEY_PREFIX]

    if prefix in PREFIX_EMBEDDED:
        raise cc_public.edit.tree.ErrorItem(
                'A {id_type} lives in the docstring of a class or function '
                'inside a module. Write it there.'.format(id_type = id_type))

    if not re.match(entry[KEY_REGEX_ID], id_self):
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} does not match {regex}, the form of a {id_type} '
                'identifier.'.format(id_self = id_self,
                                     regex   = entry[KEY_REGEX_ID],
                                     id_type = id_type))

    if id_self in tree.map_id:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} already exists.'.format(id_self = id_self))

    is_source = prefix in (PREFIX_PACKAGE, PREFIX_MODULE)

    if is_source:
        filepath = _source_path(tree, prefix, id_self, dirpath_out)
    else:
        dirpath  = (pathlib.Path(dirpath_out) if dirpath_out
                    else _home(tree, prefix))
        filepath = dirpath / (id_self + SUFFIX)

    mark = tree.resolve(defaults['id_mark'])

    document = ruamel.yaml.comments.CommentedMap()
    document['id_self']   = id_self
    document['guid_self'] = guid or (prefix + '_' + uuid.uuid4().hex)
    document['copyright'] = defaults['copyright']
    document['license']   = defaults['license']

    marks = ruamel.yaml.comments.CommentedSeq()
    one   = ruamel.yaml.comments.CommentedMap()
    one['id_mark']   = mark.id_self
    one['guid_mark'] = mark.guid_self
    marks.append(one)
    document['protective_mark'] = marks

    (required, properties) = _shape(tree, entry)

    for key in ORDER_ENVELOPE:
        if key in required and key not in document:
            document[key] = empty(properties.get(key))

    for key in required:
        if key not in document and key != KEY_RELATION:
            document[key] = empty(properties.get(key))

    if KEY_RELATION in properties or KEY_RELATION in required:
        document[KEY_RELATION] = ruamel.yaml.comments.CommentedSeq()

    if filepath.exists():
        raise cc_public.edit.tree.ErrorItem(
                '{path} already exists.'.format(path = filepath))

    filepath.parent.mkdir(parents = True, exist_ok = True)

    if is_source:
        _write_source(filepath, document)
    else:
        cc_public.edit.tree.save(filepath, document)

    # The tree now holds the item and its document, so a module made
    # next can find the package made first, and an entry can be put in
    # a set made a moment ago.
    #
    tree.refresh(filepath)
    made = cc_public.edit.tree.Item(filepath, '', id_self,
                                    document['guid_self'])
    tree.map_id[id_self]                 = made
    tree.map_guid[document['guid_self']] = made

    return filepath


# -----------------------------------------------------------------------------
def _source_path(tree, prefix, id_self, dirpath_out):
    """
    Return where a new package or module belongs.

    The dotted body of the identifier is its place: the last segment is
    the file or directory name, and what precedes it names the package
    that holds it, which must already exist. A package with no parent
    needs --out.

    """

    list_part = id_self.split('_', 1)[1].split('.')
    name      = list_part[-1]

    if dirpath_out is not None:
        base = pathlib.Path(dirpath_out)
    else:
        id_parent = PREFIX_PACKAGE + '_' + '.'.join(list_part[:-1])
        if len(list_part) < 2 or id_parent not in tree.map_id:
            raise cc_public.edit.tree.ErrorItem(
                    '{id_self} names no existing package as its parent '
                    '({parent}). Make the package first, or give '
                    '--out.'.format(id_self = id_self, parent = id_parent))
        base = tree.map_id[id_parent].filepath.parent

    if prefix == PREFIX_PACKAGE:
        return base / name / NAME_PACKAGE

    return base / (name + SUFFIX_PYTHON)


# -----------------------------------------------------------------------------
def _write_source(filepath, document):
    """
    Write a python file holding nothing but the document in its docstring.

    """

    stream = io.StringIO()
    ruamel.yaml.YAML(typ = 'rt').dump(document, stream)

    body = cc_public.layout.format(stream.getvalue()).rstrip('\n')
    text = '"""\n---\n\n' + body + '\n\n...\n"""\n'

    filepath.write_text(cc_public.layout.format_metadata(text),
                        encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _home(tree, prefix):
    """
    Return the directory items of this prefix live in, by majority.

    """

    count = {}

    for (id_self, item) in tree.map_id.items():
        if id_self.split('_', 1)[0] == prefix and not item.path:
            count[item.filepath.parent] = count.get(item.filepath.parent, 0) + 1

    if not count:
        raise cc_public.edit.tree.ErrorItem(
                'No item with prefix {prefix} exists yet, so there is no '
                'directory to put one in. Give --out.'.format(prefix = prefix))

    return max(count, key = count.get)


# -----------------------------------------------------------------------------
def _shape(tree, entry):
    """
    Return (required keys in order, properties) for a type's schema,
    gathered through everything it composes.

    """

    id_schema = next((e[KEY_ID_TARGET] for e in entry.get(KEY_RELATION) or []
                        if e.get(KEY_ID_REL) == REL_SPECIFIED), None)

    if id_schema is None:
        raise cc_public.edit.tree.ErrorItem(
                '{id_type} names no schema, so its shape is unknown.'.format(
                                                id_type = entry['id_self']))

    map_schema = {d['id_self']: d for d in tree.context.map_document.values()
                  if isinstance(d, dict) and '$id' in d and 'id_self' in d}

    return gather(map_schema[id_schema], map_schema)


# -----------------------------------------------------------------------------
def gather(schema, map_schema):
    """
    Return (required keys in order, properties) for a schema, through
    every schema it composes by allOf.

    """

    required   = []
    properties = {}

    def walk(node):
        for key in node.get(KEY_REQUIRED) or []:
            if key not in required:
                required.append(key)
        for (key, value) in (node.get(KEY_PROPERTIES) or {}).items():
            properties.setdefault(key, value)
        for part in node.get(KEY_ALLOF) or []:
            ref = part.get(KEY_REF)
            if ref is None:
                walk(part)
            elif '#' not in ref:
                target = ref.rsplit('/', 1)[-1].removesuffix(SUFFIX)
                if target in map_schema:
                    walk(map_schema[target])

    walk(schema)

    return (required, properties)


# -----------------------------------------------------------------------------
def empty(subschema):
    """
    Return the empty value of the kind a subschema describes.

    """

    kind  = (subschema or {}).get(KEY_TYPE, 'string')
    empty = EMPTY.get(kind, '')

    return empty() if callable(empty) else empty
