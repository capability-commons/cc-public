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
import cc_public.item
import cc_public.load.python
import cc_public.path


ID_CHECK      = 'interface'
TITLE         = 'Interface members agree with their keys, their names and their source'
NOUN          = 'member'

KEY_ID_SELF   = 'id_self'
KEY_NAME      = 'name'
KEY_RELATION  = 'relation'
KEY_ID_REL    = 'id_relation'
KEY_ID_TARGET = 'id_target'
KEY_GUID_TGT  = 'guid_target'
KEY_LANGUAGE  = 'language'
KEY_DECLARE   = 'declaration'
KEY_TYPE      = 'type'
KEY_MODE      = 'mode'

PREFIX_ICD    = 'icd'
PREFIX_MEMBER = 'icm'
REL_IMPLEMENT = 'r_is_implemented_by'
KEY_GUID_SELF = 'guid_self'
KEY_PARAMETER = 'parameter'
SUFFIX_PYTHON = '.py'
DELIM_STEP    = '.'
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
    map_location = {d.get(KEY_GUID_SELF): location
                    for (location, d) in context.map_document.items()
                    if isinstance(d, dict)}

    for (filepath, document) in sorted(context.map_document.items(), key = str):

        if not isinstance(document, dict):
            continue

        id_document = document.get(KEY_ID_SELF)

        if not isinstance(id_document, str) \
                or cc_public.item.prefix_of(id_document) != PREFIX_ICD:
            continue

        stem     = PREFIX_MEMBER + SEPARATOR + id_document.split(SEPARATOR, 1)[1]
        declared = set(document.get(KEY_DECLARE) or ())

        for (path, key, member, language, holder) in _iter_member(document):
            count += 1
            list_bad.extend(_member(filepath, path, key, member, stem, language,
                                    declared, holder, map_location))

        list_bad.extend(_duplicate(filepath, document))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _member(filepath, path, key, member, stem, language, declared, holder = (),
            map_location = None):
    """
    Return a fault for each way one member disagrees with what holds it.

    The local part of an identity is every member this one sits within
    and then its own name, so a member naming the wrong holder is
    reported. Holding the first and last steps alone left the run
    between them uncompared, and that run is how an embedded item says
    where it sits.

    """

    out      = []
    id_self  = member.get(KEY_ID_SELF) or ''
    name     = member.get(KEY_NAME) or ''
    held     = key if key is not None else name
    expected = DELIM.join([stem, *holder, held])

    if not id_self.startswith(stem + DELIM):
        out.append(_fault(filepath, path,
                'A member of this document is identified by {stem} and a local name, and '
                'this one is {id_self}.'.format(stem = stem, id_self = id_self)))

    elif id_self != expected:
        out.append(_fault(filepath, path,
                'The identity is {id_self} and what holds it says {expected}. An identity '
                'is the document, then every member it sits within, then the key that '
                'holds it, or its name where a list does.'.format(id_self = id_self,
                                                                  expected = expected)))

    if language == 'python':
        out.extend(_signature(filepath, path, member, map_location))

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
def _signature(filepath, path, member, map_location):
    """
    Return a fault where the parameters a member states are not the
    parameters of the definition it says presents it.

    A member restates a signature the code already holds, so the two
    can drift while the edge still resolves. Comparing them is what
    keeps the document a contract rather than a copy
    (ddr_interface_control_document).

    """

    held = _parameter_of(member, map_location or {})

    if held is None:
        return []

    said = tuple(one.get(KEY_NAME) for one in member.get(KEY_PARAMETER) or ()
                 if isinstance(one, dict))

    if said == held:
        return []

    return [_fault(filepath, cc_public.path.join(path, KEY_PARAMETER),
            'The member states {said} and the definition presenting it takes '
            '{held}.'.format(said = ', '.join(said) or 'no parameter',
                             held = ', '.join(held) or 'no parameter'))]


# -----------------------------------------------------------------------------
def _parameter_of(member, map_location):
    """
    Return the parameter names of the definition a member says
    presents it, or None where there is no python to read.

    """

    for edge in member.get(KEY_RELATION) or []:

        if not isinstance(edge, dict) or edge.get(KEY_ID_REL) != REL_IMPLEMENT:
            continue

        location = map_location.get(edge.get(KEY_GUID_TGT))

        if location is None or location.filepath.suffix != SUFFIX_PYTHON:
            continue

        return cc_public.load.python.parameter_of(
                        location.filepath.read_text(encoding = 'utf-8'), location.anchor)

    return None


# -----------------------------------------------------------------------------
def _source(filepath, path, member, name):
    """
    Return a fault where a member names the source presenting it and
    that identifier does not end with the member's name at a step
    boundary.

    A readable id spells a definition in lower case and a member is
    named as the language spells it, so the two are compared with the
    case taken off (ddr_source_identifier).

    """

    out = []

    for edge in member.get(KEY_RELATION) or []:

        if not isinstance(edge, dict) or edge.get(KEY_ID_REL) != REL_IMPLEMENT:
            continue

        target = str(edge.get(KEY_ID_TARGET) or '')

        if SEPARATOR in target \
                and not _ends_with_step(target.split(SEPARATOR, 1)[1], name.lower()):
            out.append(_fault(filepath, cc_public.path.join(path, KEY_RELATION),
                    'The member is named {name} and says {target} presents it, which '
                    'does not end with that name at a step '
                    'boundary.'.format(name = name, target = target)))

    return out


# -----------------------------------------------------------------------------
def _ends_with_step(identifier, name):
    """
    Return whether identifier ends with name at a step boundary.

    A module member is named by its whole dotted path and a class or a
    function member by its last step, so both are admitted; a bare
    suffix of a step is not.

    """

    return identifier == name or identifier.endswith(DELIM_STEP + name)


# -----------------------------------------------------------------------------
def _duplicate(filepath, document):
    """
    Return a fault for each name two members of one table share.

    A name is what the surface language spells a declaration by, so two
    of them in one scope name one thing twice.

    """

    out      = []
    map_name = collections.defaultdict(list)

    for (path, key, member, _, _holder) in _iter_member(document):
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
def _iter_member(document, path = '', key = None, language = None, holder = ()):
    """
    Yield (path, key, member, language, holder) for every interface
    member in the document. key is None where a list holds the member,
    and holder is the local names of the members this one sits within.

    """

    if isinstance(document, dict):

        language = (document.get(KEY_LANGUAGE)
                    if isinstance(document.get(KEY_LANGUAGE), str) else language)

        if cc_public.item.prefix_of(document.get(KEY_ID_SELF)) == PREFIX_MEMBER:
            yield (path, key, document, language, holder)
            holder = (*holder, key if key is not None else document.get(KEY_NAME) or '')

        for (name, value) in document.items():
            yield from _iter_member(value, cc_public.path.join(path, name), name,
                                    language, holder)

    elif isinstance(document, list):

        for (index, value) in enumerate(document):
            yield from _iter_member(value, cc_public.path.join(path, index), None,
                                    language, holder)


# -----------------------------------------------------------------------------
def _fault(filepath, path, message):
    """
    Return one critical nonconformity.

    """

    return cc_public.check.result.fault(filepath, path, message)
