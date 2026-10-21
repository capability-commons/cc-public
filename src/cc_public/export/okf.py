"""
---

id_self:                pym_cc_public.export.okf
guid_self:              pym_af33627b48e7478b87b49b1395890398
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Open Knowledge Format export
brief:                  |
                        Make a bundle of the graph of data items in
                        the Open Knowledge Format, version 0.2.
description:            |
                        Each item is a concept named by its id, in a
                        folder for its type, with the name of its type
                        as its type and its brief as its description.
                        Each item it names is a link to that concept
                        from the root of the bundle. An index in the
                        root names the format version and lists the
                        folders, and one in each folder lists its
                        concepts. The format is specified at
                        https://github.com/GoogleCloudPlatform/open-knowledge-format
                        (SPEC.md, fetched 2026-10-19).
edge:                   []

...
"""


import cc_public.export.page
import cc_public.graph.item


VERSION_OKF       = '0.2'
NAME_INDEX        = 'index.md'
MARK_SECTION      = '#'
HEADING_ROOT      = 'Types'
DELIM_PATH        = '/'


# -----------------------------------------------------------------------------
def pages(map_item: dict[str, cc_public.graph.item.Item]) -> dict[str, str]:
    """
    Return the text of an Open Knowledge Format bundle for the items of
    map_item, keyed by the path of each file: a concept for each item,
    named by its id, in a folder for its type, and an index in the root
    and in each folder.

    The type of a concept is the name of the type of its item, and its
    description is the item's brief. The id, guid, file and line of the
    item, and each of its fields that is not prose, are extra keys of
    the frontmatter. The prose and the relations are the body, with
    each item they name as a link to its concept.

    """

    def _link(id_item):
        return link(map_item, id_item)

    map_text   = {}
    map_folder = {}

    for item in map_item.values():
        map_head  = {'type':        cc_public.graph.item.type_name(map_item, item.type),
                     'title':       cc_public.graph.item.title(map_item, item.id),
                     'description': cc_public.export.page.summary(item)}
        list_part = [cc_public.export.page.frontmatter(
                        map_head | cc_public.export.page.properties(item))]
        list_part.extend(cc_public.export.page.sections(item, map_item, _link, MARK_SECTION))

        map_text[path(item)] = '\n'.join(list_part)
        map_folder.setdefault(item.type, []).append(item)

    map_text[NAME_INDEX] = _index_root(map_item, map_folder)

    for (id_type, list_item) in map_folder.items():
        name           = cc_public.graph.item.folder(id_type) + DELIM_PATH + NAME_INDEX
        map_text[name] = _index_folder(map_item, id_type, list_item)

    return map_text


# -----------------------------------------------------------------------------
def path(item: cc_public.graph.item.Item) -> str:
    """
    Return the path of the concept of item within the bundle.

    """

    return '{folder}/{id}{suffix}'.format(folder = cc_public.graph.item.folder(item.type),
                                          id     = item.id,
                                          suffix = cc_public.export.page.SUFFIX_PAGE)


# -----------------------------------------------------------------------------
def link(map_item: dict[str, cc_public.graph.item.Item], id_item: str) -> str:
    """
    Return a link to the concept of id_item from the root of the
    bundle, shown by its title, or the id as code if the bundle has no
    such concept.

    """

    if id_item not in map_item:
        return '`{id}`'.format(id = id_item)

    return '[{text}]({path})'.format(
              text = _text(cc_public.graph.item.title(map_item, id_item)),
              path = DELIM_PATH + path(map_item[id_item]))


# -----------------------------------------------------------------------------
def _index_root(map_item:   dict[str, cc_public.graph.item.Item],
                map_folder: dict[str, list[cc_public.graph.item.Item]]) -> str:
    """
    Return the index of the root of the bundle: the version of the
    format it follows, and an entry for the folder of each type.

    """

    list_line = ['---',
                 'okf_version: "{version}"'.format(version = VERSION_OKF),
                 '---',
                 '',
                 '{mark} {heading}'.format(mark = MARK_SECTION, heading = HEADING_ROOT),
                 '']

    for id_type in sorted(map_folder, key = cc_public.graph.item.folder):
        item_type = map_item.get(id_type)
        list_line.append(_entry(cc_public.graph.item.type_name(map_item, id_type),
                                cc_public.graph.item.folder(id_type) + DELIM_PATH,
                                cc_public.export.page.summary(item_type) if item_type else ''))

    return '\n'.join(list_line) + '\n'


# -----------------------------------------------------------------------------
def _index_folder(map_item:  dict[str, cc_public.graph.item.Item],
                  id_type:   str,
                  list_item: list[cc_public.graph.item.Item]) -> str:
    """
    Return the index of the folder of the type id_type: an entry for
    the concept of each item in list_item, sorted by id.

    """

    list_line = ['{mark} {heading}'.format(
                    mark    = MARK_SECTION,
                    heading = cc_public.graph.item.type_name(map_item, id_type)),
                 '']

    for item in sorted(list_item, key = lambda item: item.id):
        list_line.append(_entry(cc_public.graph.item.title(map_item, item.id),
                                item.id + cc_public.export.page.SUFFIX_PAGE,
                                cc_public.export.page.summary(item)))

    return '\n'.join(list_line) + '\n'


# -----------------------------------------------------------------------------
def _entry(text: str, target: str, description: str) -> str:
    """
    Return an entry of an index: a link to target, shown by text, and
    the description, if there is one.

    """

    line = '* [{text}]({target})'.format(text = _text(text), target = target)
    if description:
        line += ' - ' + description

    return line


# -----------------------------------------------------------------------------
def _text(text: str) -> str:
    """
    Return text with the brackets that would end the text of a link
    escaped.

    """

    return text.replace('[', '\\[').replace(']', '\\]')
