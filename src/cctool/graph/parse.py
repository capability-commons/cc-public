"""
---

id_self:                pym_cctool.graph.parse
guid_self:              pym_313a1df63a184016a3359b888bbef453
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Fast YAML reading
brief:                  |
                        Read a YAML document with the C parser of
                        libyaml into the same values, key lines and
                        block styles that a round trip load of
                        ruamel.yaml gives, many times faster.
description:            |
                        Reading needs the data, the line of each key
                        and item, and whether text was written as a
                        block, but not the comments and quoting that a
                        round trip load keeps for writing back. The C
                        parser of PyYAML composes the nodes; each node
                        is then built into the mappings, lists and
                        scalars of ruamel.yaml, with the YAML 1.2
                        rules for plain scalars that ruamel.yaml
                        follows. A document that uses what this does
                        not build, such as a tag, an alias or a merge
                        key, a repeated key, a document libyaml cannot
                        parse, or a Python whose PyYAML has no C
                        parser, is loaded by ruamel.yaml instead, so
                        the result, or the error, is always that of a
                        round trip load. libyaml reads a few texts
                        that ruamel.yaml refuses, such as a tab after
                        a scalar; the layout check reads every file
                        with ruamel.yaml, and reports such a file.
                        Editing and layout still use ruamel.yaml,
                        since they write the document back.
edge:                   []

...
"""


import bisect
import re
import threading
import typing

import ruamel.yaml
import ruamel.yaml.comments
import ruamel.yaml.constructor
import ruamel.yaml.nodes
import ruamel.yaml.resolver
import ruamel.yaml.scalarstring
import yaml
import yaml.nodes
import yaml.resolver


# The error that reading a document that is not YAML raises. Only
# ruamel.yaml decides that a document is not YAML, so that the verdict
# and its words are always the same.
#
ERROR             = ruamel.yaml.YAMLError

# Whether PyYAML was built with libyaml. A wheel built from source
# where libyaml was missing, as on a Mac for a Python with no wheel,
# has no yaml._yaml, so yaml.cyaml cannot be imported; yaml imports it
# itself when it can.
#
IS_FAST           = getattr(yaml, '__with_libyaml__', False)
TAG_STR           = 'tag:yaml.org,2002:str'

# The tags of plain scalars that are built here. Any other tag, such as
# a merge key or an explicit tag, sends the document to ruamel.yaml.
#
SET_TAG_CORE      = {'tag:yaml.org,2002:bool',
                     'tag:yaml.org,2002:float',
                     'tag:yaml.org,2002:int',
                     'tag:yaml.org,2002:null',
                     'tag:yaml.org,2002:timestamp'}

MAP_STYLE_BLOCK   = {'|': ruamel.yaml.scalarstring.LiteralScalarString,
                     '>': ruamel.yaml.scalarstring.FoldedScalarString}

# The same, and the quoted styles, as a round trip load that preserves
# quotes keeps them.
#
MAP_STYLE_QUOTED  = {**MAP_STYLE_BLOCK,
                     "'": ruamel.yaml.scalarstring.SingleQuotedScalarString,
                     '"': ruamel.yaml.scalarstring.DoubleQuotedScalarString}
SET_STYLE_BLOCK   = set(MAP_STYLE_BLOCK)

# The mark that opens a comment, outside a scalar.
#
MARK_COMMENT      = '#'


# -----------------------------------------------------------------------------
class Unbuilt(Exception):
    """
    A document uses what this module does not build, or repeats a key,
    so ruamel.yaml loads it instead.

    """


# -----------------------------------------------------------------------------
class Yaml:
    """
    A YAML loader and dumper that threads may use at the same time. A
    ruamel YAML object keeps the state of the stream it is reading, so
    two threads that share one, such as the review tool warming its
    cache beside a request, corrupt each other's reads. Each thread
    gets one of its own, made with the same settings.

    """

    # -------------------------------------------------------------------------
    def __init__(self, typ: str, **map_setting: typing.Any) -> None:
        """
        Keep the type of loader and the settings to make each with.

        """

        self.typ         = typ
        self.map_setting = map_setting
        self.local       = threading.local()

    # -------------------------------------------------------------------------
    def instance(self) -> ruamel.yaml.YAML:
        """
        Return the YAML object of the calling thread.

        """

        yaml = getattr(self.local, 'yaml', None)
        if yaml is None:
            yaml = ruamel.yaml.YAML(typ = self.typ)
            for (name, value) in self.map_setting.items():
                setattr(yaml, name, value)
            self.local.yaml = yaml
        return yaml

    # -------------------------------------------------------------------------
    def load(self, stream: typing.Any) -> typing.Any:
        """
        Return the document that stream holds.

        """

        return self.instance().load(stream)

    # -------------------------------------------------------------------------
    def dump(self, data: typing.Any, stream: typing.Any) -> None:
        """
        Write data to stream.

        """

        self.instance().dump(data, stream)


# The round trip loader that reads what libyaml cannot, or what this
# module does not build.
#
ROUND_TRIP        = Yaml('rt')
ROUND_TRIP_QUOTED = Yaml('rt', preserve_quotes = True)


# -----------------------------------------------------------------------------
class _Resolver(yaml.resolver.BaseResolver):
    """
    The rules of YAML 1.2 for the type of a plain scalar, taken from
    ruamel.yaml so that both agree, rather than the YAML 1.1 rules of
    PyYAML, which read yes, no, on and off as booleans.

    """


for (_tuple_version, _tag, _regex, _list_first) in ruamel.yaml.resolver.implicit_resolvers:
    if (1, 2) in _tuple_version:
        _Resolver.add_implicit_resolver(_tag, _regex, _list_first)


if IS_FAST:

    # -------------------------------------------------------------------------
    class _Composer(yaml.cyaml.CParser, _Resolver):
        """
        The C parser of libyaml, with the rules of YAML 1.2.

        """

        # ---------------------------------------------------------------------
        def __init__(self, stream: str) -> None:
            """
            Parse stream.

            """

            yaml.cyaml.CParser.__init__(self, stream)
            _Resolver.__init__(self)

        # ---------------------------------------------------------------------
        def resolve(self, kind: type, value: typing.Any, implicit: typing.Any) -> str:
            """
            Return the tag of a node that the text gives no tag. A node
            tagged with a bare !, which the parser also asks about, is
            left to ruamel.yaml, which keeps that tag.

            """

            if implicit is False or implicit == (False, False):
                raise Unbuilt('tag')
            return _Resolver.resolve(self, kind, value, implicit)


# -----------------------------------------------------------------------------
def load(text: str, is_quoted: bool = False, is_commented: bool = False) -> typing.Any:
    """
    Return the YAML document text as a round trip load of ruamel.yaml
    would, one that preserves quotes if is_quoted, and records its
    comments if is_commented. Raise ERROR if it is not YAML, or repeats
    a key.

    The fast reader records no comments, so if is_commented, a text
    with a comment is left to ruamel.yaml.

    """

    map_style = MAP_STYLE_QUOTED if is_quoted else MAP_STYLE_BLOCK
    if IS_FAST:
        try:
            node = yaml.compose(text, Loader = _Composer)
            if is_commented and MARK_COMMENT in text and _has_comment(node, text):
                raise Unbuilt('comment')
            return _build(node, set(), map_style, text)
        except (Unbuilt, yaml.YAMLError):
            pass
    return (ROUND_TRIP_QUOTED if is_quoted else ROUND_TRIP).load(text)


# -----------------------------------------------------------------------------
def _has_comment(node: yaml.nodes.Node | None, text: str) -> bool:
    """
    Return True if text, which composes to node, holds a comment: a #
    that no scalar holds. The header of a block scalar, the line of its
    | or >, may hold a comment too, so it is not counted as held.

    """

    list_span = []
    list_node = [] if node is None else [node]
    set_seen  = set()

    while list_node:
        each = list_node.pop()
        if id(each) in set_seen:
            continue
        set_seen.add(id(each))
        if isinstance(each, yaml.nodes.ScalarNode):
            start = each.start_mark.index
            if each.style in SET_STYLE_BLOCK:
                start = text.find('\n', start) + 1 or each.end_mark.index
            list_span.append((start, each.end_mark.index))
        elif isinstance(each, yaml.nodes.SequenceNode):
            list_node.extend(each.value)
        elif isinstance(each, yaml.nodes.MappingNode):
            list_node.extend(part for pair in each.value for part in pair)

    list_span.sort()
    list_start = [start for (start, _) in list_span]

    for index in (match.start() for match in re.finditer(MARK_COMMENT, text)):
        position = bisect.bisect_right(list_start, index) - 1
        if position < 0 or index >= list_span[position][1]:
            return True

    return False


# -----------------------------------------------------------------------------
def _build(node:      yaml.nodes.Node | None,
           set_seen:  set[int],
           map_style: dict[str, type],
           text:      str) -> typing.Any:
    """
    Return the value of node, in the types of ruamel.yaml, with the
    line and column of each key and item. set_seen holds the nodes
    built so far, so that an alias, which is a node seen twice, is
    left to ruamel.yaml. map_style gives the type of a string scalar of
    each style that is kept. text is the text that node is read from,
    so that a node with an anchor, which ruamel.yaml keeps on the value,
    is left to ruamel.yaml.

    """

    if node is None:
        return None
    if id(node) in set_seen:
        raise Unbuilt('alias')
    set_seen.add(id(node))
    if text[node.start_mark.index:node.start_mark.index + 1] == '&':
        raise Unbuilt('anchor')

    if isinstance(node, yaml.nodes.ScalarNode):
        return _scalar(node, map_style)
    if isinstance(node, yaml.nodes.SequenceNode):
        return _sequence(node, set_seen, map_style, text)
    return _mapping(node, set_seen, map_style, text)


# -----------------------------------------------------------------------------
def _scalar(node: yaml.nodes.ScalarNode, map_style: dict[str, type]) -> typing.Any:
    """
    Return the value of the scalar node.

    """

    # libyaml marks an empty value at the end of the indicator before
    # it, and ruamel.yaml at the next token, so it is left to ruamel.
    #
    if node.start_mark.index == node.end_mark.index:
        raise Unbuilt('empty scalar')
    if node.tag == TAG_STR:
        if node.style in map_style:
            return map_style[node.style](node.value)
        return node.value
    if node.tag not in SET_TAG_CORE:
        raise Unbuilt(node.tag)

    # The constructor of the round trip loader of the thread builds the
    # scalar, so that a number or a date is just what ruamel.yaml makes
    # of it. It keeps what it builds by node, so each is let go.
    #
    constructor = ROUND_TRIP.instance().constructor
    scalar      = ruamel.yaml.nodes.ScalarNode(node.tag, node.value, style = node.style)
    try:
        return constructor.construct_object(scalar)
    finally:
        constructor.constructed_objects.pop(scalar, None)


# -----------------------------------------------------------------------------
def _sequence(node:      yaml.nodes.SequenceNode,
              set_seen:  set[int],
              map_style: dict[str, type],
              text:      str) -> ruamel.yaml.comments.CommentedSeq:
    """
    Return the list of the sequence node, with the line and column of
    each item.

    """

    if node.tag != 'tag:yaml.org,2002:seq':
        raise Unbuilt(node.tag)

    sequence = ruamel.yaml.comments.CommentedSeq()
    sequence.lc.line = node.start_mark.line
    sequence.lc.col  = node.start_mark.column
    for (index, item) in enumerate(node.value):
        sequence.append(_build(item, set_seen, map_style, text))
        sequence.lc.add_kv_line_col(index, [item.start_mark.line, item.start_mark.column])
    return sequence


# -----------------------------------------------------------------------------
def _mapping(node:      yaml.nodes.MappingNode,
             set_seen:  set[int],
             map_style: dict[str, type],
             text:      str) -> ruamel.yaml.comments.CommentedMap:
    """
    Return the mapping of the mapping node, with the line and column of
    each key and its value.

    """

    if node.tag != 'tag:yaml.org,2002:map':
        raise Unbuilt(node.tag)

    mapping = ruamel.yaml.comments.CommentedMap()
    mapping.lc.line = node.start_mark.line
    mapping.lc.col  = node.start_mark.column
    for (node_key, node_value) in node.value:
        key = _build(node_key, set_seen, map_style, text)
        if not isinstance(key, (str, int, float, bool)) or key is None:
            raise Unbuilt('key')
        if key in mapping:
            raise Unbuilt('repeated key')
        mapping[key] = _build(node_value, set_seen, map_style, text)
        mapping.lc.add_kv_line_col(key, [node_key.start_mark.line,   node_key.start_mark.column,
                                         node_value.start_mark.line, node_value.start_mark.column])
    return mapping
