"""
---

id_self:                pym_cc_public.question
guid_self:              pym_ca80f34ea27c466bac9fbeb8f921fee0
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Questions
brief:                  |
                        What the decision records leave open, and what
                        has since been answered.
description:            |
                        Walks every record for its questions and every
                        item for r_answers edges, and pairs them. A
                        question with no incoming edge is open.

...
"""


KEY_QUESTION  = 'question'
KEY_ID_SELF   = 'id_self'
KEY_GUID_SELF = 'guid_self'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_GUID_TGT  = 'guid_target'

REL_ANSWERS   = 'r_answers'


# -----------------------------------------------------------------------------
def report(map_document):
    """
    Return one (id_record, id_question, text, list_answerer) per
    question, in record order. list_answerer is empty where open.

    """

    map_answer = {}

    for document in map_document.values():
        for (id_self, edges) in _iter_edges(document):
            for edge in edges:
                if edge.get(KEY_ID_REL) == REL_ANSWERS:
                    map_answer.setdefault(edge.get(KEY_GUID_TGT), []).append(id_self)

    list_row = []

    for (_, document) in sorted(map_document.items()):

        if not isinstance(document, dict):
            continue

        for (key, question) in (document.get(KEY_QUESTION) or {}).items():
            if not isinstance(question, dict):
                continue
            list_row.append((document.get(KEY_ID_SELF),
                             question.get(KEY_ID_SELF) or key,
                             ' '.join(str(question.get(KEY_QUESTION, '')).split()),
                             sorted(map_answer.get(question.get(KEY_GUID_SELF), []))))

    return list_row


# -----------------------------------------------------------------------------
def _iter_edges(node, id_self = None):
    """
    Yield (id of the nearest identified item, its edges) throughout node.

    """

    if isinstance(node, dict):
        if isinstance(node.get(KEY_ID_SELF), str):
            id_self = node[KEY_ID_SELF]
        edges = node.get(KEY_RELATION)
        if isinstance(edges, list) and id_self is not None:
            yield (id_self, [e for e in edges if isinstance(e, dict)])
        for value in node.values():
            yield from _iter_edges(value, id_self)
    elif isinstance(node, list):
        for value in node:
            yield from _iter_edges(value, id_self)
