"""
---

id_self:                pym_cctool.graph.sparql
guid_self:              pym_5a666a6e76044ba4abd648973cbe797e
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  SPARQL evaluation
brief:                  |
                        Evaluate a SPARQL query over the graph of data
                        items, with Oxigraph.
description:            |
                        This module loads the items into an in-memory
                        Oxigraph store as RDF triples. An item is
                        named cc:ID. Its type is its rdf:type, its
                        fields are f:NAME, and each primary edge is a
                        triple of its relation, with each inverse
                        relation recorded the other way round. A query
                        changes nothing outside the store it runs in.
edge:                   []

...
"""


import pyoxigraph

import cctool.graph.extract
import cctool.graph.item


# The namespaces of the graph. An item, a type and a relation are each
# named by its id under NS_ITEM, so that cc:ID is the item with the id ID,
# cc:type_annotation a type, and cc:relation_is_about a relation. A field
# of an item is named under NS_FIELD, as f:title.
#
NS_ITEM           = 'urn:cc:'
NS_FIELD          = 'urn:cc:field:'
NS_RDF            = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
NS_RDFS           = 'http://www.w3.org/2000/01/rdf-schema#'
NS_XSD            = 'http://www.w3.org/2001/XMLSchema#'
MAP_PREFIX        = {'cc':   NS_ITEM,
                     'f':    NS_FIELD,
                     'rdf':  NS_RDF,
                     'rdfs': NS_RDFS,
                     'xsd':  NS_XSD}

TYPE_RDF          = pyoxigraph.NamedNode(NS_RDF + 'type')
FIELD_GUID        = 'guid'
FIELD_FILE        = 'file'
FIELD_LINE        = 'line'
FIELD_HOLDER      = 'holder'
COLUMN_TRIPLE     = ('subject', 'predicate', 'object')

# How a literal of each datatype is printed, if not as text.
#
MAP_DATATYPE      = {NS_XSD + 'integer': int,
                     NS_XSD + 'double':  float,
                     NS_XSD + 'decimal': float,
                     NS_XSD + 'boolean': lambda text: text == 'true'}

Value             = str | int | float | bool | None


# -----------------------------------------------------------------------------
class ErrorSparql(Exception):
    """
    A SPARQL query that cannot be evaluated.

    """


# -----------------------------------------------------------------------------
def store(map_item: dict[str, cctool.graph.item.Item],
          facts:    cctool.graph.extract.Facts) -> pyoxigraph.Store:
    """
    Return an in-memory store that holds the graph of the items of
    map_item as RDF triples.

    Each item has its type as its rdf:type, and its guid, file, line
    and holder, and each field that is a scalar or a list of scalars,
    as a field. Each item it names in a pair of id_ and guid_ fields is
    a field too, named for the pair, whose value is that item. Each
    primary edge is a triple of its relation. An inverse relation is
    recorded the other way round, so that a query may use either.

    """

    map_inverse = {}
    for (inverse, relation) in facts['inverse_relation']:
        map_inverse.setdefault(relation, []).append(inverse)

    list_quad = []

    def _add(subject, predicate, value):
        list_quad.append(pyoxigraph.Quad(subject, predicate, value))

    for item in map_item.values():
        node = _item(item.id)
        if item.type:
            _add(node, TYPE_RDF, _item(item.type))
        _add(node, _field(FIELD_GUID), pyoxigraph.Literal(item.guid))
        _add(node, _field(FIELD_FILE), pyoxigraph.Literal(item.file))
        _add(node, _field(FIELD_LINE), _literal(item.line))
        if item.holder:
            _add(node, _field(FIELD_HOLDER), _item(item.holder))
        for (key, value) in item.map_field.items():
            for each in value if isinstance(value, list) else [value]:
                _add(node, _field(key), _literal(each))
        for (field, id_item) in item.list_reference:
            _add(node, _field(field), _item(id_item))
        for (relation, target) in item.list_edge:
            _add(node, _item(relation), _item(target))
            for inverse in map_inverse.get(relation, []):
                _add(_item(target), _item(inverse), node)

    result = pyoxigraph.Store()
    result.bulk_extend(list_quad)

    return result


# -----------------------------------------------------------------------------
def query(map_item: dict[str, cctool.graph.item.Item],
          facts:    cctool.graph.extract.Facts,
          text:     str) -> tuple[tuple[str, ...], list[tuple]] | bool:
    """
    Return the result of the SPARQL query text, evaluated over the
    graph of map_item: for SELECT, its variables and its rows; for
    CONSTRUCT and DESCRIBE, the triples, as rows of subject, predicate
    and object; and for ASK, True or False. The prefixes cc, f, rdf,
    rdfs and xsd are declared. Raise ErrorSparql if the query cannot be
    evaluated.

    """

    try:
        result = store(map_item, facts).query(text, prefixes = MAP_PREFIX)
    except (SyntaxError, OSError) as error:
        raise ErrorSparql(str(error)) from error

    if isinstance(result, pyoxigraph.QueryBoolean):
        return bool(result)

    if isinstance(result, pyoxigraph.QuerySolutions):
        tuple_column = tuple(variable.value for variable in result.variables)
        return (tuple_column, [tuple(value(solution[column]) for column in tuple_column)
                               for solution in result])

    return (COLUMN_TRIPLE, [(value(triple.subject), value(triple.predicate), value(triple.object))
                            for triple in result])


# -----------------------------------------------------------------------------
def value(term: pyoxigraph.NamedNode | pyoxigraph.Literal | None) -> Value:
    """
    Return term as it is printed: an item by its id, a field by f: and
    its name, any other named node in angle brackets, a number or a
    truth value as one, and other literals as text.

    """

    if isinstance(term, pyoxigraph.NamedNode):
        iri = term.value
        if iri.startswith(NS_FIELD):
            return 'f:' + iri[len(NS_FIELD):]
        if iri.startswith(NS_ITEM):
            return iri[len(NS_ITEM):]
        return '<{iri}>'.format(iri = iri)

    if isinstance(term, pyoxigraph.Literal):
        convert = MAP_DATATYPE.get(term.datatype.value, str)
        return convert(term.value)

    return None if term is None else str(term)


# -----------------------------------------------------------------------------
def _item(id_item: str) -> pyoxigraph.NamedNode:
    """
    Return the node of the item id_item.

    """

    return pyoxigraph.NamedNode(NS_ITEM + id_item)


# -----------------------------------------------------------------------------
def _field(name: str) -> pyoxigraph.NamedNode:
    """
    Return the predicate of the field name.

    """

    return pyoxigraph.NamedNode(NS_FIELD + name)


# -----------------------------------------------------------------------------
def _literal(scalar: cctool.graph.item.Scalar) -> pyoxigraph.Literal:
    """
    Return scalar as a literal: a truth value as xsd:boolean, a whole
    number as xsd:integer, a fraction as xsd:double, and text as text.

    """

    if isinstance(scalar, bool):
        return pyoxigraph.Literal('true' if scalar else 'false',
                                  datatype = pyoxigraph.NamedNode(NS_XSD + 'boolean'))
    if isinstance(scalar, (int, float)):
        return pyoxigraph.Literal(scalar)

    return pyoxigraph.Literal(str(scalar))
