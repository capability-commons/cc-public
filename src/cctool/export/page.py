"""
---

id_self:                pym_cctool.export.page
guid_self:              pym_62c56b04ae4a468fa2c0380323465295
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Pages of an export
brief:                  |
                        Write the frontmatter, the prose and the
                        relations of the page of an item, and write
                        the pages to a folder.
description:            |
                        A field of an item that is not prose goes in
                        the frontmatter, written as JSON, which YAML
                        reads. Its prose fields are the sections of
                        the body, with each paragraph on one line and
                        each id they mention given as a link. Its
                        relations are a last section of sentences. The
                        pages are written only to an empty folder,
                        unless the pages already in it are to be
                        replaced.
edge:                   []

...
"""


import json
import pathlib
import re
import typing

import cctool.graph.item


KEY_TITLE         = 'title'
KEY_BRIEF         = 'brief'
KEY_DESCRIPTION   = 'description'
SUFFIX_PAGE       = '.md'
LINE_FRONTMATTER  = '---'
HEADING_RELATION  = 'Relations'

# A field is a section of the body when it is prose: text of more than
# one line or more than this many characters, or a list that holds such
# text. Any other field goes in the frontmatter.
#
WIDTH_PROPERTY    = 80

# The keys each export sets in the frontmatter itself. A field of an
# item with one of these names goes in under PREFIX_FIELD.
#
SET_KEY_PAGE      = {'id', 'guid', 'type', 'title', 'description', 'tags',
                     'aliases', 'file', 'line'}
PREFIX_FIELD      = 'item_'
REGEX_KEY_PLAIN   = re.compile(r'^[A-Za-z_$][A-Za-z0-9_$-]*$')

Link              = typing.Callable[[str], str]


# -----------------------------------------------------------------------------
class ErrorExport(Exception):
    """
    An export that cannot be written where it was asked to be.

    """


# -----------------------------------------------------------------------------
def frontmatter(map_property: dict[str, typing.Any]) -> str:
    """
    Return the YAML frontmatter block that holds map_property, in
    order. Each value is written as JSON, which YAML reads, so that no
    text needs quoting rules of its own.

    """

    list_line = [LINE_FRONTMATTER]

    for (key, value) in map_property.items():
        name = key if REGEX_KEY_PLAIN.match(key) else json.dumps(key)
        list_line.append('{name}: {value}'.format(name = name, value = json.dumps(value)))

    list_line.append(LINE_FRONTMATTER)

    return '\n'.join(list_line) + '\n'


# -----------------------------------------------------------------------------
def properties(item: cctool.graph.item.Item) -> dict[str, typing.Any]:
    """
    Return the fields of item that go in the frontmatter, after its id,
    guid, file and line: each that is not prose, by its own name unless
    an export sets that key itself.

    """

    map_property = {'id': item.id, 'guid': item.guid, 'file': item.file, 'line': item.line}

    for (key, value) in item.map_field.items():
        if key in (KEY_TITLE, KEY_BRIEF, KEY_DESCRIPTION) or is_prose(value):
            continue
        name               = PREFIX_FIELD + key if key in SET_KEY_PAGE else key
        map_property[name] = value

    return map_property


# -----------------------------------------------------------------------------
def is_prose(value: typing.Any) -> bool:
    """
    Return True if value is prose, which goes in the body of a page.

    """

    if isinstance(value, list):
        return any(map(is_prose, value))

    return isinstance(value, str) and ('\n' in value or len(value) > WIDTH_PROPERTY)


# -----------------------------------------------------------------------------
def sections(item:     cctool.graph.item.Item,
             map_item: dict[str, cctool.graph.item.Item],
             link:     Link,
             mark:     str) -> list[str]:
    """
    Return the sections of the body of the page of item, each headed
    with mark: one for each field of prose other than its title and
    brief, then one that states its relations. Each id the prose
    mentions, and each item a relation names, is given as link of it.

    """

    list_section = []

    for (key, value) in item.map_field.items():
        if key in (KEY_TITLE, KEY_BRIEF) or not (is_prose(value) or key == KEY_DESCRIPTION):
            continue
        list_section.append(_section(mark, key.replace('_', ' ').capitalize(),
                                     _prose(value, map_item, link)))

    list_line = relations(item, map_item, link)
    if list_line:
        list_section.append(_section(mark, HEADING_RELATION, '\n'.join(list_line)))

    return list_section


# -----------------------------------------------------------------------------
def brief(item:     cctool.graph.item.Item,
          map_item: dict[str, cctool.graph.item.Item],
          link:     Link) -> str:
    """
    Return the brief of item as markdown, with each id it mentions
    given as link of it.

    """

    return _prose(item.map_field.get(KEY_BRIEF, ''), map_item, link)


# -----------------------------------------------------------------------------
def summary(item: cctool.graph.item.Item) -> str:
    """
    Return the brief of item on one line, as it is written.

    """

    return ' '.join(cctool.graph.item.paragraphs(str(item.map_field.get(KEY_BRIEF, ''))))


# -----------------------------------------------------------------------------
def relations(item:     cctool.graph.item.Item,
              map_item: dict[str, cctool.graph.item.Item],
              link:     Link) -> list[str]:
    """
    Return a list item for each relation of item: the item that holds
    it, each item it names in a field, and each primary edge from it,
    each stated as a sentence.

    """

    subject   = 'This ' + cctool.graph.item.type_name(map_item, item.type).lower()
    list_line = []

    if item.holder:
        list_line.append('{subject} is held in {holder}.'.format(subject = subject,
                                                                 holder  = link(item.holder)))

    for (field, id_item) in item.list_reference:
        list_line.append('{subject} names {target} in its {field} field.'.format(
                            subject = subject,
                            target  = link(id_item),
                            field   = field))

    for (relation, target) in item.list_edge:
        list_line.append(cctool.graph.item.sentence(map_item, relation, subject, link(target)))

    return ['- ' + line for line in list_line]


# -----------------------------------------------------------------------------
def write(dir_out: pathlib.Path, map_text: dict[str, str], is_replace: bool) -> None:
    """
    Write each text of map_text to the file under dir_out that its key
    names. dir_out must be empty or absent, unless is_replace is True:
    then every page under it is removed first, with each folder left
    empty, and any other file, such as the settings of a viewer, is
    kept.

    """

    if dir_out.exists() and not dir_out.is_dir():
        raise ErrorExport('{dir} is a file, not a folder.'.format(dir = dir_out))

    if dir_out.is_dir() and any(dir_out.iterdir()):
        if not is_replace:
            raise ErrorExport('{dir} is not empty. Give an empty or new folder, or pass '
                              '--replace to remove the pages in it first.'.format(dir = dir_out))
        _clear(dir_out)

    for (name, text) in map_text.items():
        path = dir_out / name
        path.parent.mkdir(parents = True, exist_ok = True)
        path.write_text(text, encoding = 'utf-8')


# -----------------------------------------------------------------------------
def _clear(dir_out: pathlib.Path) -> None:
    """
    Remove every page under dir_out, and each folder that is left
    empty, other than dir_out.

    """

    for path in dir_out.rglob('*' + SUFFIX_PAGE):
        if path.is_file():
            path.unlink()

    for path in sorted(dir_out.rglob('*'), key = lambda path: len(path.parts), reverse = True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


# -----------------------------------------------------------------------------
def _section(mark: str, heading: str, text: str) -> str:
    """
    Return a section of a page: its heading after mark, and text.

    """

    return '{mark} {heading}\n\n{text}\n'.format(mark = mark, heading = heading, text = text)


# -----------------------------------------------------------------------------
def _prose(value:    typing.Any,
           map_item: dict[str, cctool.graph.item.Item],
           link:     Link) -> str:
    """
    Return value as markdown: each paragraph of text on a line of its
    own, or a list as a list. Each id it mentions is given as link of
    it, and each term it links as the term.

    """

    if isinstance(value, list):
        return '\n'.join('- ' + _prose(each, map_item, link) for each in value)

    return '\n\n'.join(cctool.graph.item.mentions(cctool.graph.item.terms(paragraph),
                                                    map_item, link)
                       for paragraph in cctool.graph.item.paragraphs(str(value)))
