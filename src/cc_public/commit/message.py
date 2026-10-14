"""
---

id_self:                pym_cc_public.commit.message
guid_self:              pym_59df4c74e5eb465893caf918d87e7912
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit message
brief:                  |
                        Compose a commit message around a new commit
                        item, and check a message against sch_commit.
description:            |
                        A commit message is the subject line, a blank
                        line, the commit item as a YAML document from
                        --- to ..., and then any trailers. The subject
                        line is the title of the item.

                        A message is checked against sch_commit, which
                        holds the templates a title is built from, as
                        read from the tree. The id must end with the
                        first six hex digits of the guid, which a
                        schema cannot say.
usage:                  |
                        cctool message new TITLE --brief TEXT cctool
                        message check FILE

                        The commit-msg hook in .githooks runs the
                        check on every commit.
relation:               []

...
"""


import datetime
import pathlib
import uuid

import jsonschema
import ruamel.yaml

import cc_public.check.schema
import cc_public.edit.layout
import cc_public.graph.extract


ID_SCHEMA       = 'sch_commit'
PREFIX          = 'cmt'
FORMAT_TIME     = '%Y%m%d%H%M%S'
LENGTH_SUFFIX   = 6
MARK_COMMENT    = '#'
LINE_OPEN       = cc_public.graph.extract.LINE_OPEN
LINE_CLOSE      = cc_public.graph.extract.LINE_CLOSE
KEY_ID_SELF     = cc_public.graph.extract.KEY_ID_SELF
KEY_GUID_SELF   = cc_public.graph.extract.KEY_GUID_SELF
KEY_TITLE       = 'title'
KEY_BRIEF       = 'brief'
KEY_DESCRIPTION = 'description'
KEY_RELATION    = 'relation'


# -----------------------------------------------------------------------------
class ErrorMessage(Exception):
    """
    The message cannot be read as a subject line and a commit item.

    """


# -----------------------------------------------------------------------------
def compose(title:       str,
            brief:       str,
            description: str | None = None,
            now:         datetime.datetime | None = None) -> str:
    """
    Return a commit message whose item has title, brief and
    description, with an id and a guid minted for it.

    """

    hex_guid = uuid.uuid4().hex
    time     = (now or datetime.datetime.now(datetime.UTC)).strftime(FORMAT_TIME)
    item     = {KEY_ID_SELF:   '{prefix}_{time}_{suffix}'.format(prefix = PREFIX,
                                                                 time   = time,
                                                                 suffix = hex_guid[:LENGTH_SUFFIX]),
                KEY_GUID_SELF: '{prefix}_{hex}'.format(prefix = PREFIX, hex = hex_guid),
                KEY_TITLE:     title,
                KEY_BRIEF:     brief}

    if description:
        item[KEY_DESCRIPTION] = description
    item[KEY_RELATION] = []

    body = cc_public.edit.layout.format(
                '\n'.join(cc_public.edit.layout.dump(item, 0)) + '\n')

    return '{title}\n\n{open}\n\n{body}\n{close}\n'.format(title = title,
                                                           open  = LINE_OPEN,
                                                           body  = body,
                                                           close = LINE_CLOSE)


# -----------------------------------------------------------------------------
def parse(text: str) -> tuple[str, dict]:
    """
    Return the subject line of the commit message text, and the commit
    item it holds. Lines that git treats as comments are left out.

    """

    list_line = [line for line in text.split('\n') if not line.startswith(MARK_COMMENT)]

    if len(list_line) < 3 or list_line[1] != '' or list_line[2] != LINE_OPEN:
        raise ErrorMessage('A commit message is a subject line, a blank line, and then the '
                           'commit item, opened by {open}.'.format(open = LINE_OPEN))
    if LINE_CLOSE not in list_line:
        raise ErrorMessage('The commit item is not closed by {close}.'.format(close = LINE_CLOSE))

    end = list_line.index(LINE_CLOSE)

    try:
        item = cc_public.graph.extract.YAML.load('\n'.join(list_line[2:end + 1]))
    except ruamel.yaml.YAMLError as error:
        raise ErrorMessage('The commit item is not YAML: {error}'.format(
                                            error = ' '.join(str(error).split()))) from error

    if not isinstance(item, dict):
        raise ErrorMessage('The commit item is not a mapping.')

    return (list_line[0], item)


# -----------------------------------------------------------------------------
def violations(root: pathlib.Path, text: str) -> list[str]:
    """
    Return a sentence for each way the commit message text fails
    sch_commit, as the tree at root holds it, or fails to match its own
    subject line and guid.

    """

    try:
        (subject, item) = parse(text)
    except ErrorMessage as error:
        return [str(error)]

    map_document = cc_public.graph.extract.documents(root)
    list_schema  = [document for (document, _) in map_document.values()
                    if isinstance(document, dict)
                    and cc_public.check.schema.KEY_ID_SCHEMA in document
                    and cc_public.check.schema.META.is_valid(document)]
    map_schema   = {str(schema.get(KEY_ID_SELF)): schema for schema in list_schema}

    if ID_SCHEMA not in map_schema:
        return ['{id} cannot be found in the tree.'.format(id = ID_SCHEMA)]

    validator = jsonschema.Draft202012Validator(
                    map_schema[ID_SCHEMA],
                    registry = cc_public.check.schema.registry_of(list_schema))

    list_found = [_sentence(error) for error in validator.iter_errors(item)]

    if item.get(KEY_TITLE) != subject:
        list_found.append('The subject line is not the title of the commit item.')

    id_self   = str(item.get(KEY_ID_SELF, ''))
    guid_self = str(item.get(KEY_GUID_SELF, ''))
    suffix    = guid_self.partition('_')[2][:LENGTH_SUFFIX]
    if not (suffix and id_self.endswith('_' + suffix)):
        list_found.append('The id does not end with the first {count} hex digits of the '
                          'guid.'.format(count = LENGTH_SUFFIX))

    return sorted(set(list_found), key = list_found.index)


# -----------------------------------------------------------------------------
def _sentence(error: jsonschema.ValidationError) -> str:
    """
    Return a sentence that reports error, found in a commit item.

    """

    list_part = list(error.absolute_path)

    if list_part == [KEY_TITLE] and error.validator == 'pattern':
        return 'The title is not built from a template in {id}: {title}'.format(
                                                        id = ID_SCHEMA, title = error.instance)

    return '{path}: {message}'.format(path    = '/'.join(map(str, list_part)) or 'item',
                                      message = ' '.join(error.message.split()))

