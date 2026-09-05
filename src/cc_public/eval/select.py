"""
---

id_self:                pym_cc_public.eval.select
guid_self:              pym_43906de35249460fba113911504bc06d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Eval selection
brief:                  |
                        Work out what each eval applies to.
description:            |
                        Resolves the three anchors, being items of a
                        type, items a schema specifies transitively
                        through composition, and pairs of items joined
                        by a relation. Narrows the result by selector.
                        Run alone, it reports what would be judged and
                        at what cost.

...
"""


import io
import re
import typing

import ruamel.yaml

import cc_public.check.register
import cc_public.need
import cc_public.check.schema
import cc_public.path


ID_REL_TYPE   = 'r_evaluates_items_of_type'
ID_REL_SCHEMA = 'r_evaluates_items_specified_by_schema'
ID_REL_JOIN   = 'r_evaluates_items_joined_by_relation'

PREFIX_EVAL   = 'evl'
SEPARATOR     = '_'

KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_ID_TARGET = 'id_target'
KEY_ID_SCHEMA = '$id'
KEY_REF       = '$ref'
KEY_PREFIX    = 'prefix'
KEY_SCOPE     = 'scope'
KEY_SUBJECT   = 'subject'
KEY_INCL_TYPE = 'include_type'
KEY_INCLUDE   = 'include'
KEY_EXCLUDE   = 'exclude'


# -----------------------------------------------------------------------------
class Selector(typing.NamedTuple):
    """
    What to select, as patterns over identifiers.

    The id fields are anchored regular expressions and the guid fields
    are exact. That is not arbitrary: a guid is an opaque handle and
    matching part of one means nothing, whereas an id is a name with
    structure worth matching against.

    Within one field the patterns are a union; across fields they
    intersect. The eval side and the subject side narrow different
    halves of the result, so giving id_item alone selects every eval
    that applies to that item.

    An empty field constrains nothing.

    """

    id_eval:     tuple = ()
    guid_eval:   tuple = ()
    id_schema:   tuple = ()
    guid_schema: tuple = ()
    id_type:     tuple = ()
    guid_type:   tuple = ()
    id_item:     tuple = ()
    guid_item:   tuple = ()


# -----------------------------------------------------------------------------
class Task(typing.NamedTuple):
    """
    One eval, and one thing to apply it to.

    subject holds one item for a type or schema anchor, and two for a
    relation anchor.

    """

    id_eval:       str
    document_eval: dict
    id_subject:    tuple
    filepath:      str
    text_input:    str


# -----------------------------------------------------------------------------
def select(context, selector = None):
    """
    Return the list of tasks the selector picks out.

    """

    selector   = selector or Selector()
    map_schema = cc_public.check.schema.map_schema(context.map_document)
    map_prefix = cc_public.check.register.map_prefix(
                    cc_public.check.register.find_type(context.map_document)[1])
    map_compose = _map_compose(map_schema)

    list_task = []

    for (filepath, document) in sorted(context.map_document.items()):

        if not _is_eval(document):
            continue

        if not _wanted_eval(document, selector):
            continue

        for (id_subject, text_input) in _iter_subject(document,
                                                      context,
                                                      map_prefix,
                                                      map_compose,
                                                      selector):
            if not text_input.strip():
                continue
            list_task.append(Task(id_eval       = document[KEY_ID_SELF],
                                  document_eval = document,
                                  id_subject    = id_subject,
                                  filepath      = str(filepath),
                                  text_input    = text_input))

    return list_task


# -----------------------------------------------------------------------------
def _is_eval(document):
    """
    Return whether document is an eval.

    """

    if not isinstance(document, dict):
        return False

    id_self = document.get(KEY_ID_SELF)

    return isinstance(id_self, str) \
                    and id_self.split(SEPARATOR, 1)[0] == PREFIX_EVAL


# -----------------------------------------------------------------------------
def _wanted_eval(document, selector):
    """
    Return whether the eval side of the selector admits this eval.

    """

    if not _match(selector.id_eval,   document.get(KEY_ID_SELF),   True):
        return False

    if not _match(selector.guid_eval, document.get(KEY_GUID_SELF), False):
        return False

    # The schema and type fields constrain the anchor rather than the
    # eval, so an eval anchored elsewhere is simply not wanted.
    #
    for (patterns, id_rel, is_regex) in (
            (selector.id_schema,   ID_REL_SCHEMA, True),
            (selector.guid_schema, ID_REL_SCHEMA, False),
            (selector.id_type,     ID_REL_TYPE,   True),
            (selector.guid_type,   ID_REL_TYPE,   False)):

        if not patterns:
            continue

        key = KEY_ID_TARGET if is_regex else 'guid_target'

        if not any(_match(patterns, edge.get(key), is_regex)
                        for edge in _iter_anchor(document, id_rel)):
            return False

    return True


# -----------------------------------------------------------------------------
def _iter_anchor(document, id_rel):
    """
    Yield each anchor edge of document carrying the given relation.

    """

    for edge in document.get(KEY_RELATION) or []:
        if isinstance(edge, dict) and edge.get(KEY_ID_REL) == id_rel:
            yield edge


# -----------------------------------------------------------------------------
def _iter_subject(document_eval, context, map_prefix, map_compose, selector):
    """
    Yield (id_subject, text_input) for everything this eval applies to.

    """

    for edge in _iter_anchor(document_eval, ID_REL_TYPE):
        yield from _subject_of_type(edge, context, map_prefix, selector,
                                    document_eval)

    for edge in _iter_anchor(document_eval, ID_REL_SCHEMA):
        yield from _subject_of_schema(edge, context, map_prefix, map_compose,
                                      selector, document_eval)

    for edge in _iter_anchor(document_eval, ID_REL_JOIN):
        yield from _subject_of_join(edge, context, map_prefix, selector,
                                    document_eval)


# -----------------------------------------------------------------------------
def _wanted_type(id_self, document_eval, map_prefix):
    """
    Return whether the eval's subject constraint admits this item.

    Applied to every item shown to a judge, both ends of a join
    included. An eval naming no constraint admits everything its anchor
    reaches.

    """

    subject = document_eval.get(KEY_SUBJECT) or {}
    include = tuple(subject.get(KEY_INCL_TYPE) or ())

    if not include:
        return True

    entry = map_prefix.get(id_self.split(SEPARATOR, 1)[0])

    if entry is None:
        return False

    return entry.get(KEY_ID_SELF) in include

# -----------------------------------------------------------------------------
def _subject_of_type(edge, context, map_prefix, selector, document_eval):
    """
    Yield every item whose type is the one the edge names.

    """

    id_type = edge.get(KEY_ID_TARGET)
    prefix  = next((p for (p, entry) in map_prefix.items()
                        if entry.get(KEY_ID_SELF) == id_type), None)

    if prefix is None:
        return

    for (id_self, document) in _iter_item(context):
        if id_self.split(SEPARATOR, 1)[0] == prefix \
                        and _wanted_item(document, selector) \
                        and _wanted_type(id_self, document_eval, map_prefix):
            yield ((id_self,), _render(((id_self, document),), document_eval))


# -----------------------------------------------------------------------------
def _subject_of_schema(edge, context, map_prefix, map_compose, selector,
                       document_eval):
    """
    Yield every item the named schema specifies, composition included.

    """

    id_schema = edge.get(KEY_ID_TARGET)

    for (id_self, document) in _iter_item(context):

        (id_selected, _) = cc_public.check.schema.select_schema(document,
                                                                map_prefix)

        if id_selected is None:
            continue

        if id_schema not in map_compose.get(id_selected, set()):
            continue

        if _wanted_item(document, selector) \
                        and _wanted_type(id_self, document_eval, map_prefix):
            yield ((id_self,), _render(((id_self, document),), document_eval))


# -----------------------------------------------------------------------------
def _subject_of_join(edge, context, map_prefix, selector,
                     document_eval):
    """
    Yield every pair of items joined by an edge of the named relation.

    """

    id_rel     = edge.get(KEY_ID_TARGET)
    map_by_id  = dict(_iter_item(context))
    map_by_guid = {d.get(KEY_GUID_SELF): (i, d)
                        for (i, d) in map_by_id.items()}

    for (id_self, document) in sorted(map_by_id.items()):
        for edge_item in document.get(KEY_RELATION) or []:

            if not isinstance(edge_item, dict):
                continue

            if edge_item.get(KEY_ID_REL) != id_rel:
                continue

            found = map_by_guid.get(edge_item.get('guid_target'))

            if found is None:
                continue                  # dangling; the reference check says so

            (id_far, document_far) = found

            if not (_wanted_type(id_self, document_eval, map_prefix)
                    and _wanted_type(id_far, document_eval, map_prefix)):
                continue

            if _wanted_item(document, selector) \
                            or _wanted_item(document_far, selector):
                yield ((id_self, id_far),
                       _render(((id_self, document), (id_far, document_far)),
                               document_eval))


# -----------------------------------------------------------------------------
def _iter_item(context):
    """
    Yield (id_self, document) for every item that is not itself an eval.

    """

    for (_filepath, document) in sorted(context.map_document.items()):

        if not isinstance(document, dict) or _is_eval(document):
            continue

        id_self = document.get(KEY_ID_SELF)

        if isinstance(id_self, str):
            yield (id_self, document)


# -----------------------------------------------------------------------------
def _wanted_item(document, selector):
    """
    Return whether the subject side of the selector admits this item.

    """

    return _match(selector.id_item,   document.get(KEY_ID_SELF),   True) \
       and _match(selector.guid_item, document.get(KEY_GUID_SELF), False)


# -----------------------------------------------------------------------------
def _match(tuple_pattern, value, is_regex):
    """
    Return whether value satisfies any of the patterns, or there are none.

    """

    if not tuple_pattern:
        return True

    if not isinstance(value, str):
        return False

    if not is_regex:
        return value in tuple_pattern

    return any(re.fullmatch(pattern, value) for pattern in tuple_pattern)


# -----------------------------------------------------------------------------
def _map_compose(map_schema):
    """
    Return an id to set of composed schema ids map, transitively closed.

    A schema composes another by referencing it whole. A reference
    carrying a fragment names a value type rather than a shape, and is
    not composition.

    """

    map_url = {document.get(KEY_ID_SCHEMA): id_self
                    for (id_self, document) in map_schema.items()}

    map_direct = {id_self: {map_url[url]
                                for url in _iter_ref(document)
                                if  url in map_url}
                        for (id_self, document) in map_schema.items()}

    map_closed = {}

    for (id_self, list_direct) in map_direct.items():

        seen    = {id_self}
        pending = list(list_direct)

        while pending:
            id_next = pending.pop()
            if id_next not in seen:
                seen.add(id_next)
                pending.extend(map_direct.get(id_next, ()))

        map_closed[id_self] = seen

    return map_closed


# -----------------------------------------------------------------------------
def _iter_ref(node):
    """
    Yield each whole schema reference in node.

    """

    if isinstance(node, dict):
        for (key, value) in node.items():
            if key == KEY_REF and isinstance(value, str) and '#' not in value:
                yield value
            else:
                yield from _iter_ref(value)

    elif isinstance(node, list):
        for value in node:
            yield from _iter_ref(value)


# -----------------------------------------------------------------------------
def _render(tuple_item, document_eval):
    """
    Return the text a judge would be given for these items.

    Narrowed to what the eval's scope selects. An eval given a whole
    item where its criterion concerns a few fields answers unreliably,
    the verdict resting on weighing everything present rather than on
    the passage in question. The renderer does not decide what to give;
    the eval says.

    """

    scope   = document_eval.get(KEY_SCOPE) or {}
    include = tuple(scope.get(KEY_INCLUDE) or ())
    exclude = tuple(scope.get(KEY_EXCLUDE) or ())

    list_part = []
    is_empty  = True

    for (id_self, item) in tuple_item:
        document = cc_public.need.compose(item)          # a need shows its statement
        selected = cc_public.path.select(document, include, exclude)
        if selected is cc_public.path.DROP:
            selected = {}
        body = _body(selected)
        if body.strip():
            is_empty = False
        list_part.append('--- {id_self}\n{body}'.format(id_self = id_self,
                                                        body    = body))

    # An item carrying none of the fields the scope names is not an item
    # this eval has anything to say about. Returning the empty string
    # says so, and select drops the task. Judging it anyway would put a
    # bare header in front of the judge, which is not a subject: with
    # nothing to weigh, a verdict is a guess.
    #
    if is_empty:
        return ''

    return '\n'.join(list_part)


# -----------------------------------------------------------------------------
def _body(selected):
    """
    Return one item's selected fields as text a judge can read.

    Prose is emitted as itself. A YAML dump of it is not prose: ruamel
    renders a multi line string double quoted, with escape sequences for
    the line breaks and folds inserted to fit the width, and a judge
    reading that answers less reliably than one reading the paragraph.
    Anything that is not a string keeps its structure and is dumped.

    """

    if not isinstance(selected, dict):
        return _dump(selected)

    list_part = []

    for (name, value) in selected.items():
        if isinstance(value, str):
            list_part.append('{name}:\n{text}\n'.format(name = name,
                                                         text = value.strip()))
        else:
            list_part.append('{name}:\n{body}'.format(name = name,
                                                      body = _dump(value)))

    return '\n'.join(list_part)


# -----------------------------------------------------------------------------
def _dump(value):
    """
    Return a YAML rendering of one value.

    """

    yaml                    = ruamel.yaml.YAML(typ = 'safe')
    yaml.default_flow_style = False

    # Prose nested inside a structure is prose too. Without this a
    # multi line string is double quoted with its line breaks escaped,
    # which is not what anyone wrote and not what reads back well.
    #
    yaml.representer.add_representer(
        str,
        lambda dumper, data: dumper.represent_scalar(
                    'tag:yaml.org,2002:str', data,
                    style = '|' if '\n' in data else None))

    stream = io.StringIO()
    yaml.dump(value, stream)

    return stream.getvalue()
