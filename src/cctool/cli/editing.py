"""
---

id_self:                pym_cctool.cli.editing
guid_self:              pym_e25b436077ee4217a567d4e052acb03b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Editing commands
brief:                  |
                        The commands that edit the data items in the
                        tree.
description:            |
                        This module holds the new, header, link,
                        unlink, set, unset, remove, rename, move,
                        batch, import and format commands. Each makes
                        its edit, checks the tree with the edit in
                        place, and writes it only if it adds no
                        failure. With --dry-run, each prints the edit
                        as a diff and writes nothing.
usage:                  |
                        cctool new ID [--field NAME VALUE]... [--link
                        RELATION TARGET]...

                        cctool header FILEPATH [ID] [--field NAME
                        VALUE]... [--link RELATION TARGET]...

                        cctool link SOURCE RELATION TARGET

                        cctool unlink SOURCE RELATION TARGET

                        cctool set ID FIELDPATH VALUE [--yaml]

                        cctool unset ID FIELDPATH

                        cctool remove ID

                        cctool rename OLD NEW

                        cctool move OLDPATH NEWPATH

                        cctool batch FILEPATH

                        cctool import FILEPATH [IRI]... --namespace
                        IRI SHORT RELEASE... [--check]

                        cctool format [--check]
edge:                   []

...
"""


import difflib
import pathlib
import re
import sys

import click
import ruamel.yaml

import cctool.check.check
import cctool.check.layout
import cctool.cli.group
import cctool.edit.edit
import cctool.edit.ontology
import cctool.graph.extract
import cctool.graph.logic


# -----------------------------------------------------------------------------
def _option(function):
    """
    Add the options that every editing command shares to function.

    """

    list_option = [
        click.option('--root',
                     metavar = 'DIRPATH',
                     default = '.',
                     type    = click.Path(exists    = True,
                                          file_okay = False,
                                          path_type = pathlib.Path),
                     help    = 'The tree to edit. Defaults to the working directory.'),
        click.option('--dry-run', 'is_dry_run',
                     is_flag = True,
                     help    = 'Print the edit as a diff, and write nothing.')]

    for option in reversed(list_option):
        function = option(function)

    return function


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_self', metavar = 'ID')
@click.option('--field',
              'list_field',
              nargs    = 2,
              multiple = True,
              metavar  = 'NAME VALUE',
              help     = 'A field of the new item. Repeat for each field. A NAME given '
                         'more than once makes a list.')
@click.option('--link',
              'list_link',
              nargs    = 2,
              multiple = True,
              metavar  = 'RELATION TARGET',
              help     = 'An edge from the new item. Repeat for each edge.')
@_option
def new(id_self, list_field, list_link, root, is_dry_run):
    """
    Make a new item with the id ID.

    The type is the one whose prefix ID has. An item of a type held in
    a register is added after the last entry of its register; any other
    gets a file of its own under _data. The guid is made for it, and a
    standalone item takes its rights from the segment item of the tree.

    """

    _run(root, is_dry_run, [{'new':   id_self,
                             'field': _fields(list_field),
                             'link':  [list(pair) for pair in list_link]}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('path', metavar = 'FILEPATH', type = click.Path(dir_okay = False))
@click.argument('id_self', metavar = '[ID]', required = False)
@click.option('--field',
              'list_field',
              nargs    = 2,
              multiple = True,
              metavar  = 'NAME VALUE',
              help     = 'A field of the new item. Repeat for each field. A NAME given '
                         'more than once makes a list.')
@click.option('--link',
              'list_link',
              nargs    = 2,
              multiple = True,
              metavar  = 'RELATION TARGET',
              help     = 'An edge from the new item. Repeat for each edge.')
@_option
def header(path, id_self, list_field, list_link, root, is_dry_run):
    """
    Give the file at FILEPATH a new item, made as new makes one, and write
    it at the head of the file: in the module docstring of a python
    module, and in a comment header in any other file. The file is
    made if there is none. A relative FILEPATH is taken from the root of
    the tree.

    FILEPATH may name a class or function of a python module in the form
    pytest uses, such as src/cctool/graph/jq.py::query. The item is
    then written in its docstring, and the text the docstring held
    becomes its brief unless --field brief is given.

    The id of a python module, class or function, or of a logic program
    file, follows from its path, so ID is left out for one. Any other
    file needs ID.

    """

    (path, delim, names) = path.partition(cctool.graph.extract.DELIM_DEFINITION)

    try:
        relative = (root / path).resolve().relative_to(root.resolve())
    except ValueError:
        click.echo('{path} is not in the tree.'.format(path = path), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    _run(root, is_dry_run, [{'header': str(relative) + delim + names,
                             'id':     id_self,
                             'field':  _fields(list_field),
                             'link':   [list(pair) for pair in list_link]}])


# -----------------------------------------------------------------------------
def _fields(list_field):
    """
    Return the fields of list_field as a mapping, in which a name given
    more than once has a list of its values.

    """

    map_field = {}
    for (key, value) in list_field:
        map_field.setdefault(key, []).append(value)

    return {key: list_value if len(list_value) > 1 else list_value[0]
            for (key, list_value) in map_field.items()}


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_source', metavar = 'SOURCE')
@click.argument('id_relation', metavar = 'RELATION')
@click.argument('id_target', metavar = 'TARGET')
@_option
def link(id_source, id_relation, id_target, root, is_dry_run):
    """
    Add an edge of RELATION from SOURCE to TARGET.

    """

    _run(root, is_dry_run, [{'link': [id_source, id_relation, id_target]}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_source', metavar = 'SOURCE')
@click.argument('id_relation', metavar = 'RELATION')
@click.argument('id_target', metavar = 'TARGET')
@_option
def unlink(id_source, id_relation, id_target, root, is_dry_run):
    """
    Take the edge of RELATION from SOURCE to TARGET away.

    """

    _run(root, is_dry_run, [{'unlink': [id_source, id_relation, id_target]}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command('set')
@click.argument('id_self', metavar = 'ID')
@click.argument('path', metavar = 'FIELDPATH')
@click.argument('value', metavar = 'VALUE')
@click.option('--yaml', 'is_yaml',
              is_flag = True,
              help    = 'Read VALUE as YAML, for a number, a list or a mapping.')
@_option
def set_field(id_self, path, value, is_yaml, root, is_dry_run):
    """
    Set the field at FIELDPATH in the item ID to VALUE.

    FIELDPATH is a field name, or a dotted path into its value, in which a
    number picks an element of a list, as in protective_mark.0.id_mark.
    A field id_FIELD that names an item gets guid_FIELD beside it.

    VALUE is text unless --yaml is given. A prose field is wrapped to
    the width of prose, and a blank line in VALUE starts a new
    paragraph. Pass - as VALUE to read it from stdin.

    """

    if value == '-':
        value = sys.stdin.read()

    if is_yaml:
        try:
            value = cctool.edit.edit.YAML.load(value)
        except ruamel.yaml.YAMLError as error:
            click.echo('VALUE is not YAML: {error}'.format(error = error), err = True)
            sys.exit(cctool.cli.group.EXIT_ERROR)

    _run(root, is_dry_run, [{'set': [id_self, path, value]}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_self', metavar = 'ID')
@click.argument('path', metavar = 'FIELDPATH')
@_option
def unset(id_self, path, root, is_dry_run):
    """
    Take the field at FIELDPATH out of the item ID, with guid_FIELD if it is
    id_FIELD. FIELDPATH is as for set.

    """

    _run(root, is_dry_run, [{'unset': [id_self, path]}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_self', metavar = 'ID')
@_option
def remove(id_self, root, is_dry_run):
    """
    Remove the item ID: the file of a standalone item, or the entry of
    an item held in a register. An item that anything still names is
    refused.

    """

    _run(root, is_dry_run, [{'remove': id_self}])


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('id_old', metavar = 'OLD')
@click.argument('id_new', metavar = 'NEW')
@_option
def rename(id_old, id_new, root, is_dry_run):
    """
    Give the item OLD the id NEW, in every YAML document that names it,
    in the strings of the logic programs that the rules match it by, and
    in the name of its file. A register entry keeps OLD as an alias.

    Other text outside YAML documents, such as python code, is not
    changed. Each file that still names OLD is listed afterwards.

    """

    _run(root, is_dry_run, [{'rename': [id_old, id_new]}])
    if is_dry_run:
        return

    regex = re.compile(cctool.edit.edit.PATTERN_WHOLE_ID.format(id = re.escape(id_old)))
    for relative in cctool.graph.extract.files(
                            cctool.graph.extract.documents(root.resolve())):
        try:
            text = (root / relative).read_text(encoding = 'utf-8')
        except UnicodeDecodeError:
            continue
        if any(regex.search(line) and line.strip() != '- ' + id_old
               for line in text.splitlines()):
            click.echo('Still names {id}: {file}'.format(id = id_old, file = relative),
                       err = True)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('path_old', metavar = 'OLDPATH')
@click.argument('path_new', metavar = 'NEWPATH')
@_option
def move(path_old, path_new, root, is_dry_run):
    """
    Move the file or folder OLDPATH to NEWPATH. An item that lives in
    the file it names, such as a python module or a logic program file,
    gets the id of its new place, and keeps its guid, in every YAML
    document that names it and in the strings of the logic programs. A
    python module or package under src gets the dotted name of its new
    place in the code of every python module, and in the spelling of
    each type that a YAML document spells as code does.

    Other text, such as a path written in prose or the name of a module
    in a manifest, is not changed. Each file that still names the old
    path or the old dotted name is listed afterwards.

    """

    _run(root, is_dry_run, [{'move': [path_old, path_new]}])
    if is_dry_run:
        return

    list_pattern = [re.escape(path_old.rstrip('/'))]
    dotted       = cctool.edit.edit.dotted(pathlib.PurePosixPath(path_old))
    if dotted:
        list_pattern.append(cctool.edit.edit.PATTERN_DOTTED.format(name = re.escape(dotted)))
    regex = re.compile('|'.join(list_pattern))
    for relative in sorted({cctool.graph.extract.file_of(key) for key
                            in cctool.graph.extract.documents(root.resolve())}):
        try:
            text = (root / relative).read_text(encoding = 'utf-8')
        except UnicodeDecodeError:
            continue
        if regex.search(text):
            click.echo('Still names {path}: {file}'.format(path = path_old, file = relative),
                       err = True)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command()
@click.argument('path_file', metavar = 'FILEPATH', type = click.File(encoding = 'utf-8'))
@_option
def batch(path_file, root, is_dry_run):
    """
    Make the operations listed in the YAML file FILEPATH, or - for stdin,
    as one edit. An operation is one of new, header, link, unlink,
    set, unset, remove and rename. Items that need each other, such as a concept
    and the item that names it, are made this way. For example:

    \b
    - new:   concept_x
      field: {title: X, brief: ..., description: ..., term_preferred: x}
    - new:   ann_x
      field: {title: ..., brief: ...}
      link:  [[relation_is_about, concept_x]]
    - link:  [concept_x, relation_is_narrower_than, concept_concept]
    - set:   [concept_x, usage, ...]

    """

    try:
        list_operation = cctool.edit.edit.YAML.load(path_file.read())
    except ruamel.yaml.YAMLError as error:
        click.echo('FILEPATH is not YAML: {error}'.format(error = error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    _run(root, is_dry_run, list_operation)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command('import')
@click.argument('path_ttl', metavar = 'FILEPATH',
                type = click.Path(exists = True, dir_okay = False, path_type = pathlib.Path))
@click.argument('list_iri', metavar = '[IRI]...', nargs = -1)
@click.option('--namespace', 'list_namespace',
              metavar  = 'IRI SHORT RELEASE',
              nargs    = 3,
              multiple = True,
              required = True,
              help     = 'Classes and relations whose IRI begins with IRI get ids '
                         'extcla_SHORT_LABEL and extrel_SHORT_LABEL and cite the external '
                         'document RELEASE. Name one for each namespace.')
@click.option('--check', 'is_check',
              is_flag = True,
              help    = 'Name each way the external classes and relations differ from the '
                        'release, and write nothing. Without IRI, every one the namespaces '
                        'cover is compared. The exit status is 1 when any differs.')
@_option
def import_(path_ttl, list_iri, list_namespace, is_check, root, is_dry_run):
    """
    Make an external class for each class IRI of the ontology release
    in the Turtle file FILEPATH, and an external relation for each
    relation IRI, with everything they depend on, or bring those made
    before up to date with the release. Only labels, named superclasses
    and superproperties, and the domains and ranges of relations are
    read; other axioms are not. A file whose digest differs from the
    fixity its release records is refused. For example:

    \b
    cctool import CommonCoreOntologiesMerged.ttl \\
        --namespace http://purl.obolibrary.org/obo/BFO_ bfo extdoc_bfo_2020 \\
        --namespace https://www.commoncoreontologies.org/ cco extdoc_cco_2_2 \\
        https://www.commoncoreontologies.org/ont00000958

    """

    list_namespace = [cctool.edit.ontology.Namespace(*each) for each in list_namespace]
    try:
        tree = cctool.edit.edit.Tree(root.resolve())
        cctool.edit.ontology.refuse_other_release(tree, path_ttl, list_namespace)
        list_iri = list(list_iri)
        if not list_iri and is_check:
            list_iri = cctool.edit.ontology.known(tree, list_namespace)
        if not list_iri:
            raise cctool.edit.edit.ErrorEdit(
                'Give the IRI of at least one class or relation to import, or use '
                '--check.')
        ontology       = cctool.edit.ontology.Ontology(path_ttl)
        list_operation = cctool.edit.ontology.operations(tree, ontology, list_namespace,
                                                         list_iri)
    except cctool.edit.edit.ErrorEdit as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    if not list_operation:
        click.echo('The external classes and relations agree with the release already.')
        return
    if is_check:
        for sentence in cctool.edit.ontology.differences(list_operation):
            click.echo(sentence)
        click.echo('Run the same command without --check to bring them up to date.')
        sys.exit(cctool.cli.group.EXIT_NONCONFORMITY)
    _run(root, is_dry_run, list_operation)


# -----------------------------------------------------------------------------
@cctool.cli.group.main.command('format')
@click.option('--root',
              metavar = 'DIRPATH',
              default = '.',
              type    = click.Path(exists    = True,
                                   file_okay = False,
                                   path_type = pathlib.Path),
              help    = 'The tree to lay out. Defaults to the working directory.')
@click.option('--check', 'is_check',
              is_flag = True,
              help    = 'Name the files that would change, and write nothing. The exit '
                        'status is 1 when any would.')
def format_(root, is_check):
    """
    Lay out every YAML document in the tree under --root, or the working
    directory: the YAML files under _data, the module docstrings of
    python modules, and the comment headers of other files.

    """

    root         = root.resolve()
    map_document = cctool.graph.extract.documents(root)
    list_changed = []

    for (relative, (document, _)) in sorted(map_document.items()):
        if isinstance(document, cctool.graph.extract.Unreadable):
            click.echo('{file}: {error}'.format(file = relative, error = document.error),
                       err = True)

    for relative in cctool.graph.extract.files(map_document):
        path = root / relative
        text = path.read_text(encoding = 'utf-8')
        try:
            laid_out = cctool.check.layout.format_kept(text, pathlib.Path(relative))
        except cctool.check.layout.Unsupported as error:
            click.echo('{file}: {error}'.format(file = relative, error = error), err = True)
            continue
        if laid_out != text:
            list_changed.append(relative)
            if not is_check:
                path.write_text(laid_out, encoding = 'utf-8')

    for relative in list_changed:
        click.echo('{verb} {file}'.format(verb = 'Would change' if is_check else 'Changed',
                                          file = relative))

    sys.exit(cctool.cli.group.EXIT_NONCONFORMITY if (is_check and list_changed)
             else cctool.cli.group.EXIT_OK)


# -----------------------------------------------------------------------------
def _run(root, is_dry_run, list_operation):
    """
    Make the operations of list_operation over the tree under root as
    one edit, check it, and write it, or print it with --dry-run. Exit
    with 1 if it adds a failure, and with 2 if it cannot be made.

    """

    try:
        tree  = cctool.edit.edit.Tree(root.resolve())
        cctool.edit.edit.batch(tree, list_operation)
        added = cctool.edit.edit.apply(tree, is_written = not is_dry_run)
    except cctool.edit.edit.ErrorEdit as error:
        click.echo(str(error), err = True)
        sys.exit(cctool.cli.group.EXIT_ERROR)

    if is_dry_run:
        for (relative, text) in tree.edit.items():
            path = tree.root / relative
            if isinstance(text, bytes) or (path.exists() and not _is_text(path)):
                click.echo('Binary {file} {verb}'.format(
                               file = relative, verb = 'removed' if text is None else 'written'))
                continue
            old  = path.read_text(encoding = 'utf-8') if path.exists() else ''
            click.echo(''.join(difflib.unified_diff(old.splitlines(True),
                                                    (text or '').splitlines(True),
                                                    'a/' + relative,
                                                    'b/' + relative)),
                       nl = False)

    if added:
        for line in cctool.graph.logic.described(added,
                                                      cctool.check.check.columns(),
                                                      cctool.check.check.wording()):
            click.echo(line, err = True)
        count = sum(len(list_row) for list_row in added.values())
        click.echo('Refused: the edit adds {count} {noun}. Nothing was written.'.format(
                       count = count,
                       noun  = 'failure' if count == 1 else 'failures'),
                   err = True)
        sys.exit(cctool.cli.group.EXIT_NONCONFORMITY)

    if not is_dry_run:
        for (relative, text) in tree.edit.items():
            click.echo('{verb} {file}'.format(verb = 'Removed' if text is None else 'Wrote',
                                              file = relative))


# -----------------------------------------------------------------------------
def _is_text(path: pathlib.Path) -> bool:
    """
    Return True if the file at path is text that can be read as utf-8.

    """

    try:
        path.read_text(encoding = 'utf-8')
    except UnicodeDecodeError:
        return False
    return True
