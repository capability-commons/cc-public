"""
---

id_self:                pym_cc_public.export.obsidian
guid_self:              pym_5c1abb050eb3439fbbf06f5952a6f4ec
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Obsidian export
brief:                  |
                        Make an Obsidian vault of the graph of data
                        items.
description:            |
                        Each item is a note named by its id, in a
                        folder for its type, with its title as a
                        heading and an alias, and its type as a tag.
                        Each item it names is a wikilink to that note,
                        shown by its title.
relation:               []

...
"""


import cc_public.export.page
import cc_public.graph.item


MARK_TITLE        = '#'
MARK_SECTION      = '##'

# Obsidian reads a link to a name with a dot in it as a link to a file
# of that extension, so such a link names the page with its suffix.
#
DELIM_EXTENSION   = '.'

# Characters that would end the text of a wikilink early.
#
MAP_LINK_TEXT     = str.maketrans({'[': '(', ']': ')', '|': '/'})


# -----------------------------------------------------------------------------
def pages(map_item: dict[str, cc_public.graph.item.Item]) -> dict[str, str]:
    """
    Return the text of an Obsidian vault for the items of map_item,
    keyed by the path of each note: one note for each item, named by
    its id, in a folder for its type.

    """

    def _link(id_item):
        return link(map_item, id_item)

    map_text = {}

    for item in map_item.values():
        title    = cc_public.graph.item.title(map_item, item.id)
        map_head = {'type':    item.type,
                    'title':   title,
                    'aliases': [title],
                    'tags':    [cc_public.graph.item.folder(item.type)]}
        list_part = [cc_public.export.page.frontmatter(
                        map_head | cc_public.export.page.properties(item)),
                     '{mark} {title}\n'.format(mark = MARK_TITLE, title = title)]
        text_brief = cc_public.export.page.brief(item, map_item, _link)
        if text_brief:
            list_part.append(text_brief + '\n')
        list_part.extend(cc_public.export.page.sections(item, map_item, _link, MARK_SECTION))

        map_text[path(item)] = '\n'.join(list_part)

    return map_text


# -----------------------------------------------------------------------------
def path(item: cc_public.graph.item.Item) -> str:
    """
    Return the path of the note of item within the vault.

    """

    return '{folder}/{id}{suffix}'.format(folder = cc_public.graph.item.folder(item.type),
                                          id     = item.id,
                                          suffix = cc_public.export.page.SUFFIX_PAGE)


# -----------------------------------------------------------------------------
def link(map_item: dict[str, cc_public.graph.item.Item], id_item: str) -> str:
    """
    Return a wikilink to the note of id_item, shown by its title.

    """

    name = id_item
    if DELIM_EXTENSION in id_item:
        name += cc_public.export.page.SUFFIX_PAGE

    return '[[{name}|{text}]]'.format(
              name = name,
              text = cc_public.graph.item.title(map_item, id_item).translate(MAP_LINK_TEXT))
