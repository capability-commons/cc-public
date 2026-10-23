"""
---

id_self:                pym_cc_public.web.constraint
guid_self:              pym_86521e9d578546868f7c3fd34e85893c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Relation constraints on review pages
brief:                  |
                        The sentences that say what may stand at each
                        end of a relation, and where a role is needed.
description:            |
                        A relation page reads each end of the
                        relation: the briefs of the relation
                        constraints it names, or that the end is open.
                        A role page names the types whose items play
                        the role, and each end of a relation whose
                        constraints admit or exclude it. Each sentence
                        is a list of parts, text or a link to an item,
                        which pym_cc_public.web.page lays out.
edge:                   []

...
"""


import cc_public.web.argument
import cc_public.graph.prefix


RELATION_HAS_ITEMS_THAT_PLAY = 'relation_has_items_that_play'
RELATION_ADMITS              = 'relation_admits'
RELATION_EXCLUDES            = 'relation_excludes'
RELATION_CONSTRAINS_SOURCE   = 'relation_constrains_source'
RELATION_CONSTRAINS_TARGET   = 'relation_constrains_target'
PREFIX_RELATION              = cc_public.graph.prefix.stem('type_relation')
PREFIX_ROLE                  = cc_public.graph.prefix.stem('type_role')
LIST_END                     = (('source', RELATION_CONSTRAINS_SOURCE),
                                ('target', RELATION_CONSTRAINS_TARGET))
LIST_LITERAL                 = (('Admitted', RELATION_ADMITS),
                                ('Excluded', RELATION_EXCLUDES))

Graph = cc_public.web.argument.Graph

# A sentence is a list of parts. A part is text, or a pair of an id and
# the text that links to its page.
#
Part     = str | tuple[str, str]
Sentence = list[Part]


# -----------------------------------------------------------------------------
def sentences(graph: Graph, id_item: str) -> list[Sentence]:
    """
    Return the sentences that say how id_item takes part in relation
    constraints: for a relation, what may stand at each end; for a
    role, which types play it and at which ends of which relations it
    is admitted or excluded. Any other item has none.

    """

    if id_item.startswith(PREFIX_RELATION):
        return _ends(graph, id_item)
    if id_item.startswith(PREFIX_ROLE):
        return _role(graph, id_item)
    return []


# -----------------------------------------------------------------------------
def _ends(graph: Graph, id_relation: str) -> list[Sentence]:
    """
    Return a sentence for each end of the relation id_relation: the
    constraints it names for that end, each read by its brief, or
    that the end is open.

    """

    item          = graph.map_item[id_relation]
    list_sentence = []

    for (end, id_constrains) in LIST_END:
        list_constraint = item.targets(id_constrains)
        if not list_constraint:
            list_sentence.append(['The {end} is open to any item.'.format(end = end)])
            continue
        sentence = ['The {end} '.format(end = end)]
        sentence += _joined([(id_constraint, _brief(graph, id_constraint))
                             for id_constraint in list_constraint], ', and ')
        list_sentence.append(sentence + ['.'])

    return list_sentence


# -----------------------------------------------------------------------------
def _role(graph: Graph, id_role: str) -> list[Sentence]:
    """
    Return the sentences for the role id_role: the types whose items
    play it, and each end of a relation that admits or excludes it.

    """

    list_type = graph.sources(RELATION_HAS_ITEMS_THAT_PLAY, id_role)

    if list_type:
        list_sentence = [['Played by the items of ']
                         + _joined([(id_type, graph.title(id_type)) for id_type in list_type],
                                   ' and ')
                         + ['.']]
    else:
        list_sentence = [['Played by the items of no type.']]

    for (verb, id_literal) in LIST_LITERAL:
        for (end, id_constrains) in LIST_END:
            list_relation = sorted({id_relation
                                    for id_constraint in graph.sources(id_literal, id_role)
                                    for id_relation in graph.sources(id_constrains,
                                                                     id_constraint)})
            if list_relation:
                list_sentence.append(
                    ['{verb} at the {end} of '.format(verb = verb, end = end)]
                    + _joined([(id_relation, graph.title(id_relation))
                               for id_relation in list_relation], ' and ')
                    + ['.'])

    return list_sentence


# -----------------------------------------------------------------------------
def _brief(graph: Graph, id_item: str) -> str:
    """
    Return the brief of id_item on one line, or its id if it has none
    or is not in the tree.

    """

    item = graph.map_item.get(id_item)
    if item is None or not item.brief:
        return id_item
    return ' '.join(item.brief.split())


# -----------------------------------------------------------------------------
def _joined(list_part: list[Part], last: str) -> Sentence:
    """
    Return list_part as one run of a sentence: separated by commas, and
    the last two by last.

    """

    sentence = []

    for (index, part) in enumerate(list_part):
        if index:
            sentence.append(last if index == len(list_part) - 1 else ', ')
        sentence.append(part)

    return sentence
