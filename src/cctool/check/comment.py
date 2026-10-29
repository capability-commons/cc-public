"""
---

id_self:                pym_cctool.check.comment
guid_self:              pym_186b9fd0c21d4af28a6eee087d145b1b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Mentions in python comments
brief:                  |
                        Check that each id a comment of a python
                        module of the tree mentions names an item, as
                        dangling_mention checks the prose of data
                        items.
description:            |
                        The extractor reads only the docstrings of a
                        python module, so a comment that names an item
                        was not checked, and could name an item that
                        is gone, or that a release leaves behind. A
                        word in a comment that is shaped like an id
                        and has the prefix of a known type must name
                        an item, a guid or an old id of one, as in
                        prose. A row has the columns of
                        dangling_mention, and the holder is the item
                        of the module, or its file if it has none.
edge:                   []

...
"""


import io
import pathlib
import tokenize

import cctool.graph.extract


SUFFIX_PYTHON     = '.py'

Rows              = list[tuple[str, ...]]

# The mentions in each text of a module read, kept in one OS process, so
# that an edit, which checks the tree before and after, and the trees
# that tests copy, read each text once. It is emptied when it holds this
# many.
#
CACHE_MENTION     = {}
COUNT_MENTION     = 1024


# -----------------------------------------------------------------------------
def violations(root:         pathlib.Path,
               map_document: cctool.graph.extract.Documents,
               facts:        cctool.graph.extract.Facts,
               map_text:     dict[str, str | bytes | None] | None = None) -> Rows:
    """
    ---

    id_self:                pyf_cctool.check.comment.violations
    guid_self:              pyf_af03086b88394d659eed78ff1a5ee202
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Dangling mentions in python comments
    brief:                  |
                            Return a row for each id that a comment of a
                            python module of the tree at root mentions and
                            no item of facts holds: the holder, the id,
                            the file and the line.
    description:            |
                            A module that map_text holds is read from
                            there, as an edit leaves it, and not from the
                            disk.
    edge:                   []

    ...
    """

    set_held   = ({row[0] for row in facts['item']} | {row[1] for row in facts['item']}
                  | {row[1] for row in facts['alias']})
    set_prefix = {row[1] for row in facts['type_prefix']}
    map_holder = {file: id_self for (id_self, _, holder, file, _) in facts['item']
                  if not holder and file.endswith(SUFFIX_PYTHON)}
    list_row   = []

    for key in sorted(map_document):
        if not key.endswith(SUFFIX_PYTHON) or key != cctool.graph.extract.file_of(key):
            continue
        if isinstance(map_document[key][0], cctool.graph.extract.Unreadable):
            continue
        holder = map_holder.get(key, key)
        if map_text and key in map_text:
            text = map_text[key]
            text = text.decode('utf-8') if isinstance(text, bytes) else text
        else:
            text = (root / key).read_text(encoding = 'utf-8')
        if text not in CACHE_MENTION:
            if len(CACHE_MENTION) >= COUNT_MENTION:
                CACHE_MENTION.clear()
            CACHE_MENTION[text] = mentions(text)
        for (line, word) in CACHE_MENTION[text]:
            if word.partition('_')[0] in set_prefix and word not in set_held:
                list_row.append((holder, word, key, str(line)))

    return sorted(set(list_row))


# -----------------------------------------------------------------------------
def mentions(text: str) -> list[tuple[int, str]]:
    """
    ---

    id_self:                pyf_cctool.check.comment.mentions
    guid_self:              pyf_0793250a18624654a6084f01c9a3696a
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Ids in python comments
    brief:                  |
                            Return the line and the word of each word
                            shaped like an id in a comment of the python
                            module text.
    edge:                   []

    ...
    """

    list_mention = []

    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type != tokenize.COMMENT:
                continue
            for match in cctool.graph.extract.REGEX_MENTION.finditer(token.string):
                list_mention.append((token.start[0],
                                     cctool.graph.extract.REGEX_SUFFIX.sub('', match.group(0))))
    except (tokenize.TokenError, SyntaxError):
        return list_mention

    return list_mention
