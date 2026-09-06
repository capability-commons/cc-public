"""
---

id_self:                pym_cc_public.workflow.produce
guid_self:              pym_317420d8fc6544b582b0713ee5c027c5
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Materialise a port
brief:                  |
                        Make or revise the item on an output port from
                        what the generator answers.
description:            |
                        Works out which fields the generator is asked
                        for and what it is told about them, mints an
                        identity from the slug it offers or from the
                        node and a tag, makes the item through the
                        edit package or revises the one bound to the
                        port it revises, links what the port decides
                        and derives from, fills each field as a value,
                        as prose or as a table of entries from a JSON
                        list, and marks what it made proposed. Knows
                        nothing of scheduling, judgement or edges.
relation:               []

...
"""


import json
import re
import uuid

import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.eval.select
import cc_public.path
import cc_public.workflow


KEY_TABLE       = 'table'
KEY_PREFIX      = 'prefix'
KEY_REGEX_ID    = 'regex_id'
KEY_ID_TYPE     = 'id_type'
KEY_PROMPT      = 'prompt'
KEY_REVISES     = 'revises'
KEY_LINK        = 'link'
KEY_FIELD       = 'field'
KEY_OPTIONAL    = 'optional'
KEY_STATUS      = 'status'
KEY_SLUG        = 'slug'
KEY_KEY         = 'key'

STATUS_PROPOSED = 'proposed'

LENGTH_TAG      = 6
WIDTH_VALUE     = 50
WIDTH_LINE      = 80

# A cut line does not end on one of these.
#
WORDS_DANGLING  = {'and', 'or', 'with', 'of', 'for', 'to', 'the', 'a', 'an',
                   'by', 'in', 'on', 'at', 'from', 'as', 'but', 'nor'}

# Envelope fields the tool fills; never asked of the generator.
#
FIELD_OWN       = ('id_self', 'guid_self', 'copyright', 'license',
                   'protective_mark', 'relation', 'status')

# Fields of a table row that name the row rather than fill it.
#
FIELD_ROW_OWN   = (KEY_KEY, 'id_self', 'guid_self')

Stop = cc_public.workflow.Stop


# -----------------------------------------------------------------------------
def produce(state, local, port, spec, map_input, entry):
    """
    Make or revise the item on one output port. Return its id.

    state carries the tree, the ledger, the bindings and the generators
    of the run; entry is the node's report entry, which takes notes.

    """

    entry_type = _entry_type(state.tree, local, port, spec)
    (required, properties) = cc_public.edit.new.shape(state.tree, entry_type)
    (list_field, list_table, prompt) = _ask(spec, required, properties)
    generator  = state.generator_for(local)
    id_item    = _prior(state, local, port, spec)

    if id_item is not None:
        answer = generator.produce(prompt, map_input, list_field, False)
        state.ledger.note_modify(state.tree.resolve(id_item).filepath)
    else:
        answer  = generator.produce(prompt, map_input, list_field, True)
        id_item = _make(state, local, port, spec, entry_type, answer, entry)
        settle(state, local, port, spec, id_item)

    _fill(state.tree, id_item, answer, list_field, list_table, properties, entry)

    return id_item


# -----------------------------------------------------------------------------
def settle(state, local, port, spec, id_item):
    """
    Do to a new item what the port says: link it by each relation in
    its link map, and mark it proposed where its schema allows, since
    what a workflow makes is proposed until accepted. The same whether
    a prompt or a function made it.

    """

    _link(state, local, port, spec, id_item)

    entry_type      = _entry_type(state.tree, local, port, spec)
    (_, properties) = cc_public.edit.new.shape(state.tree, entry_type)
    item            = state.tree.resolve(id_item)
    document        = state.tree.context.map_document[item.location]

    if STATUS_PROPOSED in ((properties.get(KEY_STATUS) or {}).get('enum') or []) \
            and not document.get(KEY_STATUS):
        cc_public.edit.field.set_field(state.tree, id_item, KEY_STATUS,
                                       value = STATUS_PROPOSED)


# -----------------------------------------------------------------------------
def render(tree, id_item):
    """
    Return an item as prose, for a generator to read.

    """

    item = tree.resolve(id_item)
    node = tree.context.map_document[item.location]

    for step in cc_public.path.split(item.path):       # an embedded item
        node = node[int(step)] if isinstance(node, list) else node[step]

    return cc_public.eval.select.render(((id_item, node, item.location),), {})


# -----------------------------------------------------------------------------
def _entry_type(tree, local, port, spec):
    """
    Return the type register entry for what the port carries.

    """

    table   = tree.type_register()[KEY_TABLE]
    id_type = spec.get(KEY_ID_TYPE)

    if id_type not in table:
        raise Stop('{node}.output.{port} carries {t}, which is not a '
                   'type.'.format(node = local, port = port, t = id_type))

    return table[id_type]


# -----------------------------------------------------------------------------
def _ask(spec, required, properties):
    """
    Return (fields asked for, the table fields among them, the prompt).

    The fields the model fills are those the port names, else every
    required prose field. A table field, an object of entries, is
    filled from a list the model returns, and the prompt says so. What
    the schema bounds to a line, the model is told, so that a title
    comes back within its line rather than being cut to it afterwards.

    """

    if spec.get(KEY_FIELD):
        list_field = [f for f in spec[KEY_FIELD] if f in properties]
    else:
        list_field = [f for f in required if f not in FIELD_OWN
                      and (properties.get(f) or {}).get('type', 'string') == 'string']

    list_table = [f for f in list_field if _is_table(properties.get(f))]
    prompt     = spec.get(KEY_PROMPT) or ''

    if list_table:
        prompt = prompt.rstrip() + '\n\n' + ' '.join(
            '{f} is a JSON list of objects, each with a key of lowercase letters and '
            'underscores and the fields the prompt names for it; answer it with the JSON '
            'and nothing else.'.format(f = f) for f in list_table)

    hints = ['{f} is one line of at most {n} characters'.format(
                                            f = f, n = properties[f]['maxLength'])
             for f in list_field if _is_line(properties.get(f))]

    if hints:
        prompt = prompt.rstrip() + '\n\n' + '. '.join(hints) + '.'

    return (list_field, list_table, prompt)


# -----------------------------------------------------------------------------
def _prior(state, local, port, spec):
    """
    Return the id of the item the port revises, or None where it makes
    one instead.

    A port revising an input returns that input's item, changed in
    place. Where the input is optional and nothing is bound there, as
    on the first pass through a loop, a new item is made instead.

    """

    if not spec.get(KEY_REVISES):
        return None

    id_item = state.bound.get((local, spec[KEY_REVISES]))

    if id_item is None \
            and not state.graph.inputs(local)[spec[KEY_REVISES]].get(KEY_OPTIONAL):
        raise Stop('{node}.output.{port} revises {src}, which is not '
                   'bound.'.format(node = local, port = port,
                                   src = spec[KEY_REVISES]))

    return id_item


# -----------------------------------------------------------------------------
def _make(state, local, port, spec, entry_type, answer, entry):
    """
    Make the item from the identity the answer offers and return its id.

    """

    (id_item, guid) = _mint(state.tree, entry_type, local, port, answer, entry)
    path = cc_public.edit.new.new(state.tree, spec[KEY_ID_TYPE], id_item,
                                  state.tree.defaults(), guid = guid)
    state.ledger.note_create(path)

    return id_item


# -----------------------------------------------------------------------------
def _mint(tree, entry_type, local, port, answer, entry):
    """
    Return (id, guid) for a new item: the slug the model offered, else
    the node and a tag; a taken slug keeps its name and adds the tag.

    """

    prefix  = entry_type[KEY_PREFIX]
    guid    = prefix + '_' + uuid.uuid4().hex
    tag     = guid.split('_', 1)[1][:LENGTH_TAG]
    slug    = _slug(answer.get(KEY_SLUG, ''), prefix)
    id_item = prefix + '_' + slug

    if not slug or not re.fullmatch(entry_type[KEY_REGEX_ID], id_item):
        id_item = '{p}_{node}_{tag}'.format(p = prefix, node = local, tag = tag)
        entry['note'].append('{node}.output.{port}: the slug offered, {s!r}, '
                             'was not usable; {id} minted.'.format(
                                node = local, port = port,
                                s = answer.get(KEY_SLUG, ''), id = id_item))
    elif id_item in tree.map_id:
        entry['note'].append('{node}.output.{port}: {s} is taken; {id} '
                             'minted.'.format(node = local, port = port,
                                              s = id_item, id = id_item + '_' + tag))
        id_item = id_item + '_' + tag

    return (id_item, guid)


# -----------------------------------------------------------------------------
def _link(state, local, port, spec, id_item):
    """
    Link the item as the port says: for each relation in its link map,
    an edge from the item to what is bound on each input port named.

    """

    for (relation, list_port) in (spec.get(KEY_LINK) or {}).items():
        for port_src in list_port:
            id_target = state.bound.get((local, port_src))
            if id_target is None:
                raise Stop('{node}.output.{port} links {rel} to {src}, which is not '
                           'bound.'.format(node = local, port = port, rel = relation,
                                           src = port_src))
            cc_public.edit.link.link(state.tree, id_item, relation, id_target)


# -----------------------------------------------------------------------------
def _fill(tree, id_item, answer, list_field, list_table, properties, entry):
    """
    Write each answered field: a table from its list, a bounded line
    cut to its bound, a short value as a value, and the rest as prose.

    A field the schema bounds to a line is one line whatever the model
    returned, so its whitespace is collapsed. Otherwise one short line
    is a value and anything longer is prose, the same line the printer
    draws. A field left empty is left empty; the checks will say so.

    """

    for field in list_field:
        text = str(answer.get(field, '') or '')
        if not text.strip():
            continue
        if field in list_table:
            _fill_table(tree, id_item, field, text, entry)
            continue
        sub     = properties.get(field) or {}
        is_line = _is_line(sub)
        if is_line:
            text = _line(' '.join(text.split()), sub['maxLength'])
        if is_line or 'enum' in sub or 'pattern' in sub or (
                '\n' not in text.strip() and len(text.strip()) <= WIDTH_VALUE):
            cc_public.edit.field.set_field(tree, id_item, field, value = text.strip())
        else:
            cc_public.edit.field.set_field(tree, id_item, field, prose = text)


# -----------------------------------------------------------------------------
def _is_table(subschema):
    """
    Return whether a field's schema is a table of entries.

    """

    return isinstance(subschema, dict) and subschema.get('type') == 'object' \
           and isinstance(subschema.get('additionalProperties'), dict)


# -----------------------------------------------------------------------------
def _is_line(subschema):
    """
    Return whether a field's schema bounds it to one line.

    """

    return isinstance(subschema, dict) and 'maxLength' in subschema \
           and subschema['maxLength'] <= WIDTH_LINE


# -----------------------------------------------------------------------------
def _rows(text):
    """
    Return the JSON list of objects in text, or None where there is none.

    """

    start = text.find('[')
    end   = text.rfind(']')

    try:
        list_row = json.loads(text[start:end + 1]) if start >= 0 <= end else None
    except ValueError:
        return None

    return list_row if isinstance(list_row, list) else None


# -----------------------------------------------------------------------------
def _fill_table(tree, id_item, field, text, entry):
    """
    Insert one entry under field for each object in the JSON list the
    model returned. The entry's type is the table's name: assumption
    holds t_assumption, question holds t_question. A list that does
    not parse is noted and the table left empty.

    The list replaces the table: an entry whose key is kept keeps its
    identity and takes the new fields, a new key is inserted, and a key
    the model no longer returns is removed.

    """

    list_row = _rows(text)

    if list_row is None:
        entry['note'].append('{item}.{field}: the model did not return a JSON '
                             'list; left empty.'.format(item = id_item, field = field))
        return

    item_doc = tree.context.map_document[tree.resolve(id_item).location]
    existing = dict(item_doc.get(field) or {})
    kept     = set()

    for (n, row) in enumerate(list_row):
        if not isinstance(row, dict):
            continue
        name = _slug(row.get(KEY_KEY, ''), '') or 'a{n}'.format(n = n + 1)
        kept.add(name)
        id_entry = _row_entry(tree, id_item, field, name, existing, entry)
        if id_entry is None:
            continue
        for (key, value) in row.items():
            if key not in FIELD_ROW_OWN and isinstance(value, str) and value.strip():
                # The entry's schema says whether the field is a datum,
                # an enumeration or a pattern, or prose.
                cc_public.edit.field.set_field(tree, id_entry, key, value = value.strip())

    for name in existing:
        if name not in kept:
            cc_public.edit.field.unset_field(tree, id_item,
                                             cc_public.path.join(field, name))


# -----------------------------------------------------------------------------
def _row_entry(tree, id_item, field, name, existing, entry):
    """
    Return the id of the table entry called name, inserting it where it
    is new, or None where it could not be inserted.

    """

    if name in existing:
        return existing[name]['id_self']

    try:
        return cc_public.edit.insert.insert(tree, 't_' + field, name, id_item, field)[1]
    except cc_public.edit.tree.ErrorItem as err:
        entry['note'].append('{item}.{field}: {err}'.format(item = id_item,
                                                            field = field, err = err))
        return None


# -----------------------------------------------------------------------------
def _line(text, width):
    """
    Return text cut to width at a word boundary, where it is longer.

    A model told the bound and overrunning it anyway would otherwise
    stop the whole run on a title, and the ledger would throw the pass
    away. A cut title is visible and cheap to mend; a lost pass is not.

    """

    if len(text) <= width:
        return text

    words = text[:width].rsplit(' ', 1)[0].split(' ')

    while words and words[-1].rstrip(',;:').lower() in WORDS_DANGLING:
        words.pop()

    cut = ' '.join(words).rstrip(' ,;:')

    return cut or text[:width]


# -----------------------------------------------------------------------------
def _slug(offered, prefix):
    """
    Return the slug a model offered as the body of a readable id: lower
    case, runs of anything else made one underscore, a repeated type
    prefix dropped, and nothing at either end.

    """

    slug = re.sub(r'[^a-z0-9]+', '_', str(offered or '').lower()).strip('_')

    if slug.startswith(prefix + '_'):
        slug = slug[len(prefix) + 1:]

    return slug
