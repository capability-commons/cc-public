"""
---

id_self:                pym_cc_public.edit.tree
guid_self:              pym_64cb989cdc624aa0a1bab0daeb0e792e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Item tree
brief:                  |
                        Find an item by name, and write a changed one
                        back through the printer.
description:            |
                        Loads the tree once and indexes every identity
                        it declares, top level and embedded. Resolves
                        a readable id or a guid to the file holding it
                        and the path within that file. Writes a
                        changed document back in the layout the
                        printer gives it, splicing into a docstring
                        where the file is python.

...
"""


import io
import pathlib

import ruamel.yaml

import cc_public.check
import cc_public.check.identifier
import cc_public.check.register
import cc_public.layout
import cc_public.load
import cc_public.load.python
import cc_public.path


KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RELATION  = 'relation'
KEY_TABLE     = 'table'
KEY_ID_TARGET = 'id_target'
KEY_ID_REL    = 'id_relation'

ID_TYPE_RELATION = 't_relation'
REL_HELD_IN      = 'r_is_held_in_registry'

SUFFIX_PYTHON = cc_public.layout.SUFFIX_PYTHON


# -----------------------------------------------------------------------------
class ErrorItem(Exception):
    """
    Raised where a name does not pick out exactly one item.

    """

    pass


# -----------------------------------------------------------------------------
class Item:
    """
    One resolved item: the file that holds it and the path to it there.

    path is empty for a top level item. document is the whole file's
    document, of which the item is the part at path.

    """

    def __init__(self, filepath, path, id_self, guid_self):
        self.filepath  = filepath
        self.path      = path
        self.id_self   = id_self
        self.guid_self = guid_self


# -----------------------------------------------------------------------------
class Tree:
    """
    Every item under a root, indexed by both its names.

    """

    def __init__(self, list_root):

        self.root = pathlib.Path(list_root[0]).resolve()

        (self.context, list_error) = cc_public.check._context(
                                            [pathlib.Path(p) for p in list_root])

        self.map_id   = {}
        self.map_guid = {}
        self.dup      = set()

        for (filepath, document) in self.context.map_document.items():
            for (path, id_self, guid_self) in \
                    cc_public.check.identifier.iter_identity(document):
                item = Item(filepath, path, id_self, guid_self)
                for (key, index) in ((id_self, self.map_id),
                                     (guid_self, self.map_guid)):
                    if key is None:
                        continue
                    if key in index:
                        self.dup.add(key)
                    index[key] = item

    # -------------------------------------------------------------------------
    def resolve(self, name):
        """
        Return the Item a readable id or guid names.

        """

        if name in self.dup:
            raise ErrorItem('{name} names more than one item in this '
                            'tree.'.format(name = name))

        item = self.map_id.get(name) or self.map_guid.get(name)

        if item is None:
            raise ErrorItem('Nothing in this tree is named {name}.'.format(
                                                                name = name))
        return item

    # -------------------------------------------------------------------------
    def refresh(self, filepath):
        """
        Reload one file's document after a write, so that later work in
        the same session sees what was written.

        """

        self.context.map_document[filepath] = cc_public.load.from_file(filepath)

    # -------------------------------------------------------------------------
    def document(self, item):
        """
        Return the file's document as a round trip mapping, for editing.

        """

        text = _text_of(item.filepath)

        return ruamel.yaml.YAML(typ = 'rt').load(text)

    # -------------------------------------------------------------------------
    def type_register(self):
        """
        Return the type register's document.

        """

        return cc_public.check.register.find_type(self.context.map_document)[1]

    # -------------------------------------------------------------------------
    def relation_register(self):
        """
        Return the relation register's document, found through the type
        register rather than by name.

        """

        entry = self.type_register()[KEY_TABLE].get(ID_TYPE_RELATION) or {}

        for edge in entry.get(KEY_RELATION) or []:
            if edge.get(KEY_ID_REL) == REL_HELD_IN:
                return self.context.map_document[
                                    self.resolve(edge[KEY_ID_TARGET]).filepath]

        raise ErrorItem('The type register does not say where relations '
                        'are held.')


# -----------------------------------------------------------------------------
def save(filepath, document):
    """
    Write document to filepath through the printer.

    A python file has the document spliced into its module docstring,
    one blank line inside the markers, at the docstring's indent.

    """

    stream = io.StringIO()
    yaml   = ruamel.yaml.YAML(typ = 'rt')
    yaml.dump(document, stream)

    text = cc_public.layout.format(stream.getvalue())

    if filepath.suffix != SUFFIX_PYTHON:
        filepath.write_text(text, encoding = 'utf-8')
        return

    source    = filepath.read_text(encoding = 'utf-8')
    list_line = source.splitlines()
    found     = next(m for m in cc_public.load.python.iter_metadata(source)
                       if m.kind == cc_public.load.python.KIND_MODULE)
    pad       = ' ' * found.indent
    body      = [pad + line if line else '' for line in text.splitlines()]

    list_line[found.first : found.last] = [''] + body + ['']

    filepath.write_text('\n'.join(list_line)
                        + ('\n' if source.endswith('\n') else ''),
                        encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _text_of(filepath):
    """
    Return the YAML text a file holds: the file, or its module document.

    """

    source = filepath.read_text(encoding = 'utf-8')

    if filepath.suffix != SUFFIX_PYTHON:
        return source

    return next(m for m in cc_public.load.python.iter_metadata(source)
                  if m.kind == cc_public.load.python.KIND_MODULE).text


# -----------------------------------------------------------------------------
def defaults():
    """
    Return the rights a new item is given, from pyproject.toml.

    """

    import tomllib

    for parent in (pathlib.Path('.').resolve(),
                   *pathlib.Path('.').resolve().parents):
        candidate = parent / 'pyproject.toml'
        if candidate.exists():
            with open(candidate, 'rb') as file:
                section = tomllib.load(file).get('tool', {}) \
                                            .get('cctool', {}).get('new')
            if section:
                return section
            break

    raise ErrorItem('No [tool.cctool.new] in pyproject.toml, so no '
                    'copyright, license or id_mark to give a new item.')
