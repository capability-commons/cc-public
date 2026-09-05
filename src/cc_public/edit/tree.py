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
                        it declares, top level and embedded, and
                        refuses a tree it could not read entirely.
                        Resolves a readable id or a guid to the file
                        holding it and the path within that file.
                        Writes a changed document back in the layout
                        the printer gives it, splicing into a
                        docstring where the file is python. Says what
                        a new item in the tree is given, from the
                        configuration at or above its root.
relation:               []

...
"""


import io
import os
import pathlib
import shutil

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
SUFFIX_TMP    = '.tmp'


# -----------------------------------------------------------------------------
class ErrorItem(Exception):
    """
    Raised where a name does not pick out exactly one item.

    """



# -----------------------------------------------------------------------------
class Item:
    """
    One resolved item: the file that holds it, the location of the
    document it is in, and the path to it within that document.

    path is empty for an item that is a document of its own. location
    is the file for most, and the file and the definition beneath it
    for a class or function item, whose document is its docstring.

    """

    def __init__(self, filepath, path, id_self, guid_self, location = None):
        self.filepath  = pathlib.Path(filepath)
        self.path      = path
        self.id_self   = id_self
        self.guid_self = guid_self
        self.location  = location if location is not None \
                         else cc_public.load.Location(filepath)


# -----------------------------------------------------------------------------
class Tree:
    """
    Every item under a root, indexed by both its names.

    """

    def __init__(self, list_root):

        if not list_root:
            raise ErrorItem('A tree needs at least one root.')

        self.root = pathlib.Path(list_root[0]).resolve()

        (self.context, list_error) = cc_public.check.context(
                                            [pathlib.Path(p) for p in list_root])

        # An edit over part of a tree could miss the item it collides
        # with or the reference it breaks, so a tree that could not be
        # read entirely is not one that can be written to. The checks
        # report the same files; this is what stops anything acting
        # before they are fixed.
        #
        list_problem = [e['message'] for e in list_error] + [
                            '{path}: {err}'.format(path = path, err = err)
                            for (path, err) in self.context.list_failure_load]

        if list_problem:
            raise ErrorItem('The tree could not be read entirely, so nothing '
                            'in it can be edited until it can: '
                            '{problems}'.format(problems = '; '.join(list_problem)))

        self.map_id   = {}
        self.map_guid = {}
        self.dup      = set()

        for (location, document) in self.context.map_document.items():
            for (path, id_self, guid_self) in \
                    cc_public.check.identifier.iter_identity(document):
                item = Item(location.filepath, path, id_self, guid_self, location)
                for (key, index) in ((id_self, self.map_id),
                                     (guid_self, self.map_guid)):
                    if key is None:
                        continue
                    if key in index:
                        self.dup.add(key)
                    index[key] = item

    # -------------------------------------------------------------------------
    def defaults(self):
        """
        Return the rights a new item in this tree is given.

        """

        return defaults(self.root)

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
        Reload every document of one file after a write, so that later
        work in the same session sees what was written.

        """

        filepath = pathlib.Path(filepath)

        for location in [loc for loc in self.context.map_document
                             if loc.filepath == filepath]:
            del self.context.map_document[location]

        for (location, document) in cc_public.load.iter_document(filepath):
            self.context.map_document[location] = document

    # -------------------------------------------------------------------------
    def document(self, item):
        """
        Return the document holding item as a round trip mapping, for
        editing.

        """

        return self.document_at(item.location)

    # -------------------------------------------------------------------------
    def document_at(self, location):
        """
        Return the document at location as a round trip mapping.

        """

        return ruamel.yaml.YAML(typ = 'rt').load(_text_of(location))

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
                                    self.resolve(edge[KEY_ID_TARGET]).location]

        raise ErrorItem('The type register does not say where relations '
                        'are held.')


# -----------------------------------------------------------------------------
def save(location, document):
    """
    Write document to its location through the printer.

    location is a Location, or a file, which is the file's own
    document. A python file has the document spliced into the docstring
    it belongs to, the module's or a definition's, one blank line
    inside the markers, at the docstring's indent.

    """

    if not isinstance(location, cc_public.load.Location):
        location = cc_public.load.Location(location)

    filepath = location.filepath
    stream   = io.StringIO()
    yaml     = ruamel.yaml.YAML(typ = 'rt')
    yaml.dump(document, stream)

    text = cc_public.layout.format(stream.getvalue())

    if filepath.suffix != SUFFIX_PYTHON:
        write_text(filepath, text)
        return

    source    = filepath.read_text(encoding = 'utf-8')
    list_line = source.splitlines()
    found     = metadata_at(source, location.anchor)
    pad       = ' ' * found.indent
    body      = [pad + line if line else '' for line in text.splitlines()]

    list_line[found.first : found.last] = [''] + body + ['']

    write_text(filepath, '\n'.join(list_line)
                         + ('\n' if source.endswith('\n') else ''))


# -----------------------------------------------------------------------------
def write_text(filepath, text):
    """
    Write text to filepath so that the file is either what it was or
    what it is asked to be, and never part of either.

    The text goes to a hidden file beside the target, which the checks
    never walk, and is moved over the target in one step. A file that
    exists keeps its mode.

    """

    filepath = pathlib.Path(filepath)
    tmp      = filepath.with_name('.' + filepath.name + SUFFIX_TMP)

    try:
        tmp.write_text(text, encoding = 'utf-8')
        if filepath.exists():
            shutil.copymode(filepath, tmp)
        os.replace(tmp, filepath)
    finally:
        tmp.unlink(missing_ok = True)


# -----------------------------------------------------------------------------
def _text_of(location):
    """
    Return the YAML text at a location: the file, or the document in
    the docstring the location names.

    """

    source = location.filepath.read_text(encoding = 'utf-8')

    if location.filepath.suffix != SUFFIX_PYTHON:
        return source

    return metadata_at(source, location.anchor).text


# -----------------------------------------------------------------------------
def metadata_at(source, anchor):
    """
    Return the Metadata of the docstring document at anchor in source,
    or raise where there is none.

    """

    found = next((m for m in cc_public.load.python.iter_metadata(source)
                    if m.path == tuple(anchor)), None)

    if found is None:
        raise ErrorItem('No document sits at {anchor} in this file.'.format(
                            anchor = cc_public.load.SEPARATOR_ANCHOR.join(anchor)
                                     or 'the module'))

    return found


# -----------------------------------------------------------------------------
def defaults(root):
    """
    Return the rights a new item is given, from the pyproject.toml at
    or above root.

    The tree being written to is what says what a new item in it gets.
    Where the command is run from says nothing: a tree edited from
    another directory takes its own defaults, not that directory's.

    """

    import tomllib

    root = pathlib.Path(root).resolve()

    for parent in (root, *root.parents):
        candidate = parent / 'pyproject.toml'
        if candidate.exists():
            with open(candidate, 'rb') as file:
                section = tomllib.load(file).get('tool', {}) \
                                            .get('cctool', {}).get('new')
            if section:
                return section
            break

    raise ErrorItem('No [tool.cctool.new] in a pyproject.toml at or above '
                    '{root}, so no copyright, license or id_mark to give a '
                    'new item there.'.format(root = root))
