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
relation:               []

...
"""


import ast
import io
import pathlib
import re
import uuid

import ruamel.yaml
import ruamel.yaml.comments

import cc_public.edit.tree
import cc_public.layout
import cc_public.load


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
# function lives inside a module, and new gives it a document in its
# docstring, keeping any prose the docstring held as the brief.
#
PREFIX_PACKAGE    = 'pyp'
PREFIX_MODULE     = 'pym'
PREFIX_DEFINITION = {'pyc': 'class', 'pyf': 'function'}
PREFIX_FILE       = (PREFIX_PACKAGE, PREFIX_MODULE)
NAME_PACKAGE      = '__init__.py'
SUFFIX_PYTHON     = '.py'
MARKER_OPEN       = '---'
MARKER_CLOSE      = '...'
QUOTE             = '"""'

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

    entry     = _entry(tree, id_type, id_self)
    prefix    = entry[KEY_PREFIX]
    is_source = prefix in PREFIX_FILE

    if prefix in PREFIX_DEFINITION:
        return _new_definition(tree, entry, id_self, defaults,
                               guid or (prefix + '_' + uuid.uuid4().hex))

    if is_source:
        filepath = _source_path(tree, prefix, id_self, dirpath_out)
    else:
        dirpath  = (pathlib.Path(dirpath_out) if dirpath_out
                    else _home(tree, prefix))
        filepath = dirpath / (id_self + SUFFIX)

    if filepath.exists():
        raise cc_public.edit.tree.ErrorItem(
                '{path} already exists.'.format(path = filepath))

    document = _skeleton(tree, entry, id_self,
                         guid or (prefix + '_' + uuid.uuid4().hex), defaults)

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
def _entry(tree, id_type, id_self):
    """
    Return the type register entry for id_type, having refused a type
    that is not one, one that lives inside a module, an id that is not
    of the type's form, and an id already taken.

    """

    table = tree.type_register()[KEY_TABLE]

    if id_type not in table:
        raise cc_public.edit.tree.ErrorItem(
                '{id_type} is not in the type register.'.format(
                                                        id_type = id_type))

    entry = table[id_type]

    if not re.match(entry[KEY_REGEX_ID], id_self):
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} does not match {regex}, the form of a {id_type} '
                'identifier.'.format(id_self = id_self,
                                     regex   = entry[KEY_REGEX_ID],
                                     id_type = id_type))

    if id_self in tree.map_id:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} already exists.'.format(id_self = id_self))

    return entry


# -----------------------------------------------------------------------------
def _skeleton(tree, entry, id_self, guid, defaults):
    """
    Return the new document: its identity and rights, then every field
    its schema requires, empty, envelope fields first and relations
    last.

    """

    mark = tree.resolve(defaults['id_mark'])

    document = ruamel.yaml.comments.CommentedMap()
    document['id_self']   = id_self
    document['guid_self'] = guid
    document['copyright'] = defaults['copyright']
    document['license']   = defaults['license']

    marks = ruamel.yaml.comments.CommentedSeq()
    one   = ruamel.yaml.comments.CommentedMap()
    one['id_mark']   = mark.id_self
    one['guid_mark'] = mark.guid_self
    marks.append(one)
    document['protective_mark'] = marks

    (required, properties) = shape(tree, entry)

    for key in ORDER_ENVELOPE:
        if key in required and key not in document:
            document[key] = empty(properties.get(key))

    for key in required:
        if key not in document and key != KEY_RELATION:
            document[key] = empty(properties.get(key))

    if KEY_RELATION in properties or KEY_RELATION in required:
        document[KEY_RELATION] = ruamel.yaml.comments.CommentedSeq()

    return document


# -----------------------------------------------------------------------------
def _new_definition(tree, entry, id_self, defaults, guid):
    """
    Give a class or function a document in its docstring, and return
    the file. The prose the docstring held becomes the item's brief.

    The identifier says where the definition is: the longest leading
    part that names a module or package, then the run of names down to
    the definition, in lower case. The definition must exist, once, and
    be of the kind the prefix says.

    """

    (item_module, anchor) = _definition_home(tree, id_self)
    filepath   = item_module.filepath
    source     = filepath.read_text(encoding = 'utf-8')
    found      = _definition(source, anchor, PREFIX_DEFINITION[entry[KEY_PREFIX]],
                             id_self)
    document   = _skeleton(tree, entry, id_self, guid, defaults)
    prose      = ast.get_docstring(found.node, clean = True)

    if prose and 'brief' in document:
        document['brief'] = ruamel.yaml.scalarstring.LiteralScalarString(
                                _paragraphs(prose) + '\n')

    cc_public.edit.tree.write_text(filepath, cc_public.layout.format_metadata(
                                        _spliced(source, found.node, document)))

    tree.refresh(filepath)
    location = cc_public.load.Location(filepath, found.path, found.kind)
    made     = cc_public.edit.tree.Item(filepath, '', id_self, guid, location)
    tree.map_id[id_self] = made
    tree.map_guid[guid]  = made

    return filepath


# -----------------------------------------------------------------------------
def _definition_home(tree, id_self):
    """
    Return (the module or package item, the run of lower case names
    beneath it) that a class or function identifier names.

    """

    list_part = id_self.split('_', 1)[1].split('.')

    for n in range(len(list_part) - 1, 0, -1):
        for prefix in PREFIX_FILE:
            id_home = prefix + '_' + '.'.join(list_part[:n])
            if id_home in tree.map_id:
                return (tree.map_id[id_home], list_part[n:])

    raise cc_public.edit.tree.ErrorItem(
            '{id_self} names no module or package this tree holds as its '
            'home.'.format(id_self = id_self))


# -----------------------------------------------------------------------------
def _definition(source, anchor, kind, id_self):
    """
    Return the one Definition in source at anchor, of the kind wanted.

    """

    import cc_public.load.python

    list_named = [d for d in cc_public.load.python.iter_definition(source)
                    if [name.lower() for name in d.path] == list(anchor)]
    list_found = [d for d in list_named if d.kind == kind]

    if not list_named:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} names no definition in its module: nothing is '
                'called {anchor} there.'.format(id_self = id_self,
                                                anchor  = '.'.join(anchor)))

    # The prefix says what kind of thing is meant, which is what tells
    # a class from a function of the same name in another case.
    #
    if not list_found:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} says {kind}, and {anchor} is a {actual}.'.format(
                        id_self = id_self, kind = kind,
                        anchor  = '.'.join(list_named[0].path),
                        actual  = list_named[0].kind))

    if len(list_found) > 1:
        raise cc_public.edit.tree.ErrorItem(
                '{id_self} names more than one {kind}, which differ only in '
                'case. An identifier is lower case, so they cannot be told '
                'apart.'.format(id_self = id_self, kind = kind))

    return list_found[0]


# -----------------------------------------------------------------------------
def _paragraphs(prose):
    """
    Return prose with each paragraph on one line, paragraphs apart by a
    blank line, as the printer will refill it.

    """

    return '\n\n'.join(' '.join(paragraph.split())
                        for paragraph in re.split(r'\n\s*\n', prose.strip())
                        if paragraph.strip())


# -----------------------------------------------------------------------------
def _spliced(source, node, document):
    """
    Return source with document written as node's docstring, in place
    of the docstring it had or before its first statement.

    """

    stream = io.StringIO()
    ruamel.yaml.YAML(typ = 'rt').dump(document, stream)

    first     = node.body[0]
    indent    = ' ' * first.col_offset
    body      = [indent + line if line else ''
                 for line in cc_public.layout.format(stream.getvalue()).splitlines()]
    docstring = ([indent + QUOTE, indent + MARKER_OPEN, '']
                 + body
                 + ['', indent + MARKER_CLOSE, indent + QUOTE])
    list_line = source.splitlines()

    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
            and isinstance(first.value.value, str):
        list_line[first.lineno - 1 : first.end_lineno] = docstring
    else:
        list_line[first.lineno - 1 : first.lineno - 1] = [*docstring, '']

    return '\n'.join(list_line) + ('\n' if source.endswith('\n') else '')


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

    cc_public.edit.tree.write_text(filepath,
                                   cc_public.layout.format_metadata(text))


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
def shape(tree, entry):
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
