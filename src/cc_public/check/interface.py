"""
---

id_self:                pym_cc_public.check.interface
guid_self:              pym_4b6efa92056e459db7df5b10939c0512
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Interface check
brief:                  |
                        Check the facts about an interface control
                        document that its schema cannot conveniently
                        state.
description:            |
                        A member's identity agrees with the local key
                        that holds it, or with its name where a list
                        holds it, and is qualified by the document.
                        Two members of one table do not share a name.
                        A type naming a shared declaration names one
                        the document holds. A member of a python
                        surface that names its source has the name
                        that source ends with. A parameter mode the
                        surface language does not have is refused.

                        Whether a baselined document has changed since
                        it was baselined is not checked here. It needs
                        the relation connecting one version to the
                        next, which ddr_interface_control_document
                        leaves open.
relation:               []

...
"""


import collections

import cc_public.check.result
import cc_public.path


ID_CHECK      = 'interface'
TITLE         = 'Interface members agree with their keys, their names and their source'
NOUN          = 'member'

KEY_ID_SELF   = 'id_self'
KEY_NAME      = 'name'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_ID_TARGET = 'id_target'
KEY_LANGUAGE  = 'language'
KEY_DECLARE   = 'declaration'
KEY_TYPE      = 'type'
KEY_MODE      = 'mode'

PREFIX_ICD    = 'icd'
PREFIX_MEMBER = 'icm'
REL_IMPLEMENT = 'r_is_implemented_by'
SEPARATOR     = '_'
DELIM         = '.'

# The parameter modes each language has. Python passes one way, so a
# parameter it declares as an output says something python cannot do.
#
MODE_BY_LANGUAGE = {'python': frozenset(('input',)),
                    'c':      frozenset(('input', 'output', 'input_output')),
                    'cpp':    frozenset(('input', 'output', 'input_output'))}


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every interface member whose identity, name,
    type reference or parameter mode disagrees with what holds it.

    The schema shapes a document and holds a surface to one form. What
    it cannot conveniently say is that an identity agrees with the key
    beside it, that a name is unique among its siblings, that a shared
    declaration a type names is one the document holds, and that a
    member of a python surface carries the name of the source it says
    presents it.

    """

    count    = 0
    list_bad = []

    for (filepath, document) in sorted(context.map_document.items(), key = str):

        if not isinstance(document, dict):
            continue

        id_document = document.get(KEY_ID_SELF)

        if not isinstance(id_document, str) \
                or id_document.split(SEPARATOR, 1)[0] != PREFIX_ICD:
            continue

        stem     = PREFIX_MEMBER + SEPARATOR + id_document.split(SEPARATOR, 1)[1]
        declared = set(document.get(KEY_DECLARE) or ())

        for (path, key, member, language) in _iter_member(document):
            count += 1
            list_bad.extend(_member(filepath, path, key, member, stem, language, declared))

        list_bad.extend(_duplicate(filepath, document))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _member(filepath, path, key, member, stem, language, declared):
    """
    Return a fault for each way one member disagrees with what holds it.

    """

    out     = []
    id_self = member.get(KEY_ID_SELF) or ''
    name    = member.get(KEY_NAME) or ''
    held    = key if key is not None else name

    if not id_self.startswith(stem + DELIM):
        out.append(_fault(filepath, path,
                'A member of this document is identified by {stem} and a local name, and '
                'this one is {id_self}.'.format(stem = stem, id_self = id_self)))

    elif id_self.rsplit(DELIM, 1)[-1] != held:
        out.append(_fault(filepath, path,
                'The identity ends {last}, and what holds it is {held}. An identity ends '
                'with the key that holds it, or with the name where a list does.'.format(
                                        last = id_self.rsplit(DELIM, 1)[-1], held = held)))

    reference = (member.get(KEY_TYPE) or {}).get(KEY_DECLARE)

    if reference is not None and reference not in declared:
        out.append(_fault(filepath, cc_public.path.join(path, 'type.declaration'),
                'Names the declaration {name}, which this document does not hold.'.format(
                                                                    name = reference)))

    mode  = member.get(KEY_MODE)
    legal = MODE_BY_LANGUAGE.get(language)

    if mode is not None and legal is not None and mode not in legal:
        out.append(_fault(filepath, cc_public.path.join(path, KEY_MODE),
                'A parameter of a {language} surface is {legal}, and this one is '
                '{mode}.'.format(language = language, mode = mode,
                                 legal = ' or '.join(sorted(legal)))))

    if language == 'python':
        out.extend(_source(filepath, path, member, name))

    return out


# -----------------------------------------------------------------------------
def _source(filepath, path, member, name):
    """
    Return a fault where a member names the source presenting it and
    that source does not end with the member's name.

    """

    out = []

    for edge in member.get(KEY_RELATION) or []:

        if not isinstance(edge, dict) or edge.get(KEY_ID_REL) != REL_IMPLEMENT:
            continue

        target = str(edge.get(KEY_ID_TARGET) or '')

        if SEPARATOR in target and not target.split(SEPARATOR, 1)[1].endswith(name):
            out.append(_fault(filepath, cc_public.path.join(path, KEY_RELATION),
                    'The member is named {name} and says {target} presents it, which does '
                    'not end with that name.'.format(name = name, target = target)))

    return out


# -----------------------------------------------------------------------------
def _duplicate(filepath, document):
    """
    Return a fault for each name two members of one table share.

    A name is what the surface language spells a declaration by, so two
    of them in one scope name one thing twice.

    """

    out      = []
    map_name = collections.defaultdict(list)

    for (path, key, member, _) in _iter_member(document):
        if key is not None:
            scope = path.rsplit(cc_public.path.DELIM_PATH, 1)[0]
            map_name[(scope, member.get(KEY_NAME))].append(path)

    for ((scope, name), list_path) in sorted(map_name.items()):
        if len(list_path) > 1:
            out.append(_fault(filepath, list_path[1],
                    'Two members of {scope} are named {name}. A name is what the language '
                    'spells one declaration by.'.format(scope = scope, name = name)))

    return out


# -----------------------------------------------------------------------------
def _iter_member(document, path = '', key = None, language = None):
    """
    Yield (path, key, member, language) for every interface member in
    the document. key is None where a list holds the member.

    """

    if isinstance(document, dict):

        language = (document.get(KEY_LANGUAGE)
                    if isinstance(document.get(KEY_LANGUAGE), str) else language)

        if str(document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] == PREFIX_MEMBER:
            yield (path, key, document, language)

        for (name, value) in document.items():
            yield from _iter_member(value, cc_public.path.join(path, name), name, language)

    elif isinstance(document, list):

        for (index, value) in enumerate(document):
            yield from _iter_member(value, cc_public.path.join(path, index), None, language)


# -----------------------------------------------------------------------------
def _fault(filepath, path, message):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = path,
                severity = cc_public.check.result.SEVERITY_CRITICAL,
                message  = message)
