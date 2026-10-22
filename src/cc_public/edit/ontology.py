"""
---

id_self:                pym_cc_public.edit.ontology
guid_self:              pym_2e05ab81c5b04535a1e41c5c1c0935ab
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Ontology import
brief:                  |
                        Make or refresh the external classes for named
                        classes of an ontology release, and for every
                        class above them.
description:            |
                        An ontology release is read from a Turtle
                        file: the label of each named class, and its
                        named superclasses. operations returns the
                        batch operations that make an external class
                        for each class asked for and each class above
                        it, citing the external document of its
                        release and linked to its superclasses by
                        relation_is_subclass_of. Where the external
                        class exists already, only what differs from
                        the release is changed, so that moving to a
                        new release is a reviewable diff. The
                        definitions of the classes are not copied.
usage:                  |
                        Called by the import command of
                        pym_cc_public.cli.editing.
edge:                   []

...
"""


import collections
import hashlib
import pathlib
import re

import pyoxigraph

import cc_public.edit.edit


NS_RDFS           = 'http://www.w3.org/2000/01/rdf-schema#'
NS_OWL            = 'http://www.w3.org/2002/07/owl#'
NODE_LABEL        = pyoxigraph.NamedNode(NS_RDFS + 'label')
NODE_SUBCLASS_OF  = pyoxigraph.NamedNode(NS_RDFS + 'subClassOf')
NODE_THING        = pyoxigraph.NamedNode(NS_OWL + 'Thing')
LANGUAGE          = 'en'

PREFIX_ITEM       = 'extcla'
KEY_FIXITY        = 'fixity'
KEY_DIGEST        = 'digest'
SIZE_BLOCK        = 1 << 20
ID_CITES          = 'relation_cites'
ID_SUBCLASS_OF    = 'relation_is_subclass_of'
SCHEME_URI        = 'uri'
TEMPLATE_TITLE    = '{short} {label}'
TEMPLATE_BRIEF    = 'The class with the label "{label}" in {release}.'

# A run of anything but lower-case letters and digits becomes one
# underscore in an id.
#
PATTERN_SLUG      = r'[^a-z0-9]+'

Namespace         = collections.namedtuple('Namespace', ['iri', 'short', 'release'])


# -----------------------------------------------------------------------------
class Ontology:
    """
    The labels and direct superclasses of the named classes in an
    ontology release, read from a Turtle file.

    """

    # -------------------------------------------------------------------------
    def __init__(self, path: pathlib.Path) -> None:
        """
        Read the Turtle file at path.

        """

        self.map_label  = {}
        self.map_parent = collections.defaultdict(set)

        try:
            iter_quad = pyoxigraph.parse(path   = str(path),
                                         format = pyoxigraph.RdfFormat.TURTLE)
            for quad in iter_quad:
                self._add(quad)
        except (OSError, SyntaxError) as error:
            raise cc_public.edit.edit.ErrorEdit('{file} is not readable Turtle: {error}'.format(
                                                    file = path, error = error)) from error

    # -------------------------------------------------------------------------
    def _add(self, quad: pyoxigraph.Quad) -> None:
        """
        Keep quad if it gives a class a label or a named superclass. A
        label in English, or in no language, is kept over any other.

        """

        if not isinstance(quad.subject, pyoxigraph.NamedNode):
            return
        iri = quad.subject.value

        if quad.predicate == NODE_LABEL and isinstance(quad.object, pyoxigraph.Literal):
            language = quad.object.language
            if language in (None, LANGUAGE) or iri not in self.map_label:
                self.map_label[iri] = quad.object.value

        if (quad.predicate == NODE_SUBCLASS_OF
                and isinstance(quad.object, pyoxigraph.NamedNode)
                and quad.object != NODE_THING):
            self.map_parent[iri].add(quad.object.value)

    # -------------------------------------------------------------------------
    def closure(self, list_iri: list[str]) -> list[str]:
        """
        Return the classes of list_iri and every class above them, each
        after the classes above it, and otherwise in sorted order.

        """

        list_class = []
        set_seen   = set()
        for iri in sorted(list_iri):
            self._visit(iri, list_class, set_seen)
        return list_class

    # -------------------------------------------------------------------------
    def _visit(self, iri: str, list_class: list[str], set_seen: set[str]) -> None:
        """
        Add iri to list_class after every class above it, unless it is
        there already.

        """

        if iri in set_seen:
            return
        if iri not in self.map_label:
            raise cc_public.edit.edit.ErrorEdit(
                'The release has no labelled class {iri}. Give the IRI of a class '
                'it defines.'.format(iri = iri))
        set_seen.add(iri)
        for parent in sorted(self.map_parent[iri]):
            self._visit(parent, list_class, set_seen)
        list_class.append(iri)


# -----------------------------------------------------------------------------
def operations(tree:           cc_public.edit.edit.Tree,
               ontology:       Ontology,
               list_namespace: list[Namespace],
               list_iri:       list[str]) -> list[dict]:
    """
    Return the batch operations that make an external class for each
    class of list_iri and each class above it, or bring an existing one
    up to date with the release: its label, its title, its brief, the
    release it cites and the classes it is a subclass of. A new
    external class takes its id from its label; an existing one keeps
    its id.

    """

    list_class = ontology.closure(list_iri)
    map_known  = _known(tree)
    map_id     = {iri: map_known.get(iri) or _id(iri, ontology.map_label[iri], list_namespace)
                  for iri in list_class}
    _refuse_shared(map_id)

    list_operation = []
    for iri in list_class:
        namespace = _namespace(iri, list_namespace)
        label     = ontology.map_label[iri]
        map_field = {'title':      TEMPLATE_TITLE.format(short = namespace.short.upper(),
                                                         label = label),
                     'brief':      TEMPLATE_BRIEF.format(label   = label,
                                                         release = namespace.release),
                     'identifier': [{'scheme': SCHEME_URI, 'value': iri}],
                     'label':      label}
        set_link  = {(ID_CITES, namespace.release)}
        set_link |= {(ID_SUBCLASS_OF, map_id[parent]) for parent in ontology.map_parent[iri]}
        list_operation.extend(_item_operations(tree, map_id[iri], map_field, set_link))

    return list_operation


# -----------------------------------------------------------------------------
def known(tree: cc_public.edit.edit.Tree, list_namespace: list[Namespace]) -> list[str]:
    """
    Return, in sorted order, the IRI of every external class in tree
    that one of list_namespace covers.

    """

    return sorted(iri for iri in _known(tree)
                  if any(iri.startswith(namespace.iri) for namespace in list_namespace))


# -----------------------------------------------------------------------------
def differences(list_operation: list[dict]) -> list[str]:
    """
    Return a sentence for each operation of list_operation, saying how
    an external class differs from the release.

    """

    list_sentence = []
    for operation in list_operation:
        if 'new' in operation:
            list_sentence.append('{id} is missing.'.format(id = operation['new']))
        elif 'set' in operation:
            (id_item, key, _) = operation['set']
            list_sentence.append('{id}: its {key} differs from the release.'.format(
                                                                    id = id_item, key = key))
        elif 'link' in operation:
            (id_item, id_relation, id_target) = operation['link']
            list_sentence.append('{id}: it lacks the edge {relation} {target}.'.format(
                                    id = id_item, relation = id_relation, target = id_target))
        else:
            (id_item, id_relation, id_target) = operation['unlink']
            list_sentence.append('{id}: it has the edge {relation} {target}, which the release '
                                 'lacks.'.format(id       = id_item,
                                                 relation = id_relation,
                                                 target   = id_target))
    return list_sentence


# -----------------------------------------------------------------------------
def refuse_other_release(tree:           cc_public.edit.edit.Tree,
                         path:           pathlib.Path,
                         list_namespace: list[Namespace]) -> None:
    """
    Refuse a Turtle file at path whose digest differs from the fixity
    that the external document of a release in list_namespace records.

    """

    digest = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(SIZE_BLOCK), b''):
            digest.update(block)

    for id_release in sorted({namespace.release for namespace in list_namespace}):
        fixity = _document(tree, id_release).get(KEY_FIXITY) or {}
        if fixity and str(fixity.get(KEY_DIGEST)) != digest.hexdigest():
            raise cc_public.edit.edit.ErrorEdit(
                '{file} has the sha256 digest {found}, but {release} records {digest}. Import '
                'from the file of that release, or give the new release an external document '
                'of its own.'.format(file    = path,
                                     found   = digest.hexdigest(),
                                     release = id_release,
                                     digest  = fixity.get(KEY_DIGEST)))


# -----------------------------------------------------------------------------
def _item_operations(tree:      cc_public.edit.edit.Tree,
                     id_item:   str,
                     map_field: dict,
                     set_link:  set[tuple[str, str]]) -> list[dict]:
    """
    Return the operations that make the item id_item with map_field and
    the edges of set_link, or, if it exists, that change only what
    differs from them.

    """

    if id_item not in tree.map_item:
        return [{'new':   id_item,
                 'field': map_field,
                 'link':  [list(link) for link in sorted(set_link)]}]

    document  = _document(tree, id_item)
    list_operation = [{'set': [id_item, key, value]}
                      for (key, value) in map_field.items()
                      if _comparable(document.get(key)) != _comparable(value)]

    set_old = {(row[1], row[2]) for row in tree.facts['edge']
               if row[0] == id_item and row[1] in (ID_CITES, ID_SUBCLASS_OF)}
    list_operation.extend({'link': [id_item, *link]} for link in sorted(set_link - set_old))
    list_operation.extend({'unlink': [id_item, *link]} for link in sorted(set_old - set_link))
    return list_operation


# -----------------------------------------------------------------------------
def _known(tree: cc_public.edit.edit.Tree) -> dict[str, str]:
    """
    Return the id of each external class in tree, by the IRI of its
    class. A class keeps the id it was first given, even when its label
    changes.

    """

    map_known = {}
    for (document, _) in tree.map_document.values():
        if not isinstance(document, dict):
            continue
        id_item = str(document.get('id_self', ''))
        if not id_item.startswith(PREFIX_ITEM + '_'):
            continue
        for identifier in document.get('identifier') or []:
            if identifier.get('scheme') == SCHEME_URI:
                map_known[str(identifier.get('value'))] = id_item
    return map_known


# -----------------------------------------------------------------------------
def _document(tree: cc_public.edit.edit.Tree, id_item: str) -> dict:
    """
    Return the YAML document of the standalone item id_item.

    """

    for (document, _) in tree.map_document.values():
        if isinstance(document, dict) and document.get('id_self') == id_item:
            return document
    raise cc_public.edit.edit.ErrorEdit(
        'The item {id} is not a YAML document of its own.'.format(id = id_item))


# -----------------------------------------------------------------------------
def _comparable(value):
    """
    Return value as plain lists, dicts and strings, so that it compares
    equal to the same value built in python. Text compares by its words,
    since the layout wraps prose.

    """

    if isinstance(value, dict):
        return {str(key): _comparable(item) for (key, item) in value.items()}
    if isinstance(value, list):
        return [_comparable(item) for item in value]
    if isinstance(value, str):
        return ' '.join(str(value).split())
    return value


# -----------------------------------------------------------------------------
def _namespace(iri: str, list_namespace: list[Namespace]) -> Namespace:
    """
    Return the namespace that iri begins with, the longest if several
    do.

    """

    list_match = [namespace for namespace in list_namespace if iri.startswith(namespace.iri)]
    if not list_match:
        raise cc_public.edit.edit.ErrorEdit(
            'No --namespace covers the class {iri}. Give one for the IRI it begins '
            'with.'.format(iri = iri))
    return max(list_match, key = lambda namespace: len(namespace.iri))


# -----------------------------------------------------------------------------
def _id(iri: str, label: str, list_namespace: list[Namespace]) -> str:
    """
    Return the id of the external class for iri: the prefix of the
    type, the short name of its namespace, and its label in lower case.

    """

    slug = re.sub(PATTERN_SLUG, '_', label.lower()).strip('_')
    return '{prefix}_{short}_{slug}'.format(prefix = PREFIX_ITEM,
                                            short  = _namespace(iri, list_namespace).short,
                                            slug   = slug)


# -----------------------------------------------------------------------------
def _refuse_shared(map_id: dict[str, str]) -> None:
    """
    Refuse an import in which two classes would get the same id.

    """

    map_iri = collections.defaultdict(list)
    for (iri, id_item) in map_id.items():
        map_iri[id_item].append(iri)
    for (id_item, list_iri) in sorted(map_iri.items()):
        if len(list_iri) > 1:
            raise cc_public.edit.edit.ErrorEdit(
                'The classes {list} would all get the id {id}. Import them from '
                'namespaces with different short names.'.format(list = ', '.join(sorted(list_iri)),
                                                                id   = id_item))
