"""
---

id_self:                pym_cc_public.web.contract
guid_self:              pym_1eff877204e74184ada095c6e7289952
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Contract of an interface
brief:                  |
                        Read an interface control document as a
                        contract: its members by group, the code that
                        realizes each, and whether that code agrees
                        with what each states.
description:            |
                        contract reads the members of an interface
                        control document in the order they are
                        written, grouped by the key that holds them
                        (declaration, module, function and so on),
                        leaving the parameters of a function inside
                        it. For a function realized by a python
                        function it sets the parameters the member
                        states beside those the code takes, part by
                        part, and the type stated to be returned
                        beside the type the code returns. A part the
                        member does not state is not compared, as the
                        checks parameter_mismatch and
                        signature_mismatch do not compare it; those
                        checks are the authority, and this module only
                        reads the same facts for the review pages.

                        A surface that is not native, a dataflow step
                        or artifacts, is read apart: its members by
                        group, and each part of its semantics that the
                        schema sch_interface_control_document names,
                        with the question the schema asks of it and
                        what the surface states, if anything.
relation:               []

...
"""


import collections
import dataclasses
import pathlib

import cc_public.graph.extract
import cc_public.web.argument


PREFIX_INTERFACE  = 'icd_'
PREFIX_MEMBER     = 'icm_'
R_REALIZES        = 'r_realizes'
KEY_ID_SELF       = cc_public.web.argument.KEY_ID_SELF
KEY_RELATION      = cc_public.web.argument.KEY_RELATION
KEY_PARAMETER     = 'parameter'
KEY_RETURNS       = 'returns'
KEY_SURFACE       = 'surface'
KEY_DECLARATION   = 'declaration'
KEY_PROPERTIES    = 'properties'
KEY_REF           = '$ref'
KEY_DEFS          = '$defs'
KEY_DESCRIPTION   = 'description'
ID_SCHEMA         = 'sch_interface_control_document'
REF_SEMANTICS     = '#/$defs/semantics'

FORM_NATIVE       = 'native'
FORM_DATAFLOW     = 'dataflow_step'
FORM_ARTIFACT     = 'artifact'

# The name of each form of surface, and the definition in the schema
# that lists the parts of its semantics. A native surface is named by
# its language instead.
#
MAP_FORM          = {FORM_DATAFLOW: ('Dataflow step', 'surface_dataflow_step'),
                     FORM_ARTIFACT: ('Artifact',      'surface_artifact')}

AGREES            = 'agrees'
DIFFERS           = 'differs'
UNSTATED          = 'unstated'
UNREALIZED        = 'unrealized'

COLUMN_REALIZED   = 'realized'
COLUMN_NAMES      = 'names'
COLUMN_TYPES      = 'types'
COLUMN_DEFAULTS   = 'defaults'
COLUMN_RETURNS    = 'returns'

# The columns of the contract, each with its label and the parts of a
# parameter it compares. The parameters column compares their names in
# order, and the returns column the type returned.
#
LIST_COLUMN       = ((COLUMN_REALIZED, 'Realized',   ()),
                     (COLUMN_NAMES,    'Parameters', ()),
                     (COLUMN_TYPES,    'Types',      ('type',)),
                     (COLUMN_DEFAULTS, 'Defaults',   ('default', 'optional', 'variadic')),
                     (COLUMN_RETURNS,  'Returns',    ()))

# How each kind of member is named as a group, by the key that holds
# members of that kind.
#
MAP_GROUP         = {'declaration': 'Declarations',
                     'package':     'Packages',
                     'module':      'Modules',
                     'namespace':   'Namespaces',
                     'constant':    'Constants',
                     'type':        'Types',
                     'class':       'Classes',
                     'function':    'Functions',
                     'input':       'Inputs',
                     'output':      'Outputs',
                     'state':       'State',
                     'config':      'Configuration',
                     'artifact':    'Artifacts'}

Graph             = cc_public.web.argument.Graph
Item              = cc_public.web.argument.Item
Facts             = cc_public.graph.extract.Facts


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Parameter:
    """
    A parameter that a member states: its id and name, the parts of its
    signature it states, and what the code says of each part, or None
    if no code says.

    """

    id:       str
    name:     str
    node:     dict
    map_part: dict[str, str]
    map_code: dict[str, str] | None

    # -------------------------------------------------------------------------
    def differs(self, part: str) -> bool:
        """
        Return True if the code says other than the parameter states of
        part.

        """

        return (self.map_code is not None and part in self.map_part
                and self.map_part[part] != self.map_code.get(part, ''))


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Member:
    """
    A member of an interface control document, with the code that
    realizes it and how that code agrees with what it states.

    """

    id:             str
    name:           str
    group:          str
    node:           dict
    list_parameter: list[Parameter]
    list_realizer:  list[str]
    location:       str
    returns:        str | None
    returns_code:   str | None
    list_extra:     list[str]
    map_verdict:    dict[str, str | None]

    # -------------------------------------------------------------------------
    def is_function(self) -> bool:
        """
        Return True if the member is a function, which has a signature
        to compare.

        """

        return self.group == 'function'


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Surface:
    """
    A surface of an interface control document that is not native: a
    dataflow step or artifacts. Its members by group (the ports of a
    step, by direction, or the artifacts), and each part of its
    semantics that the schema names, with what the surface states of
    it, or empty if it states nothing.

    """

    key:            str
    form:           str
    label:          str
    node:           dict
    list_group:     list[tuple[str, list[Member]]]
    list_semantics: list[tuple[str, str, str]]

    # -------------------------------------------------------------------------
    def stated(self) -> int:
        """
        Return how many parts of the semantics the surface states.

        """

        return sum(1 for (_, _, text) in self.list_semantics if text)


# -----------------------------------------------------------------------------
@dataclasses.dataclass
class Contract:
    """
    An interface control document read as a contract: the members of
    its declarations and native surfaces by group, in the order they
    are written, and its other surfaces.

    """

    item:         Item
    list_group:   list[tuple[str, list[Member]]]
    list_surface: list[Surface] = dataclasses.field(default_factory = list)

    # -------------------------------------------------------------------------
    def every_member(self) -> list[Member]:
        """
        Return every member, of every surface.

        """

        return self.members() + [member for surface in self.list_surface
                                 for (_, list_member) in surface.list_group
                                 for member in list_member]

    # -------------------------------------------------------------------------
    def members(self) -> list[Member]:
        """
        Return every member, in the order they are written.

        """

        return [member for (_, list_member) in self.list_group for member in list_member]

    # -------------------------------------------------------------------------
    def count(self, column: str, verdict: str) -> int:
        """
        Return how many members have verdict in column.

        """

        return sum(1 for member in self.members() if member.map_verdict.get(column) == verdict)


# -----------------------------------------------------------------------------
def interfaces(graph: Graph) -> list[Item]:
    """
    Return every interface control document, by title.

    """

    return sorted((item for item in graph.map_item.values()
                   if item.id.startswith(PREFIX_INTERFACE)),
                  key = lambda item: item.title or item.id)


# -----------------------------------------------------------------------------
def facts(root: pathlib.Path) -> Facts:
    """
    Return the facts of the tree under root, which say what the code
    holds of each function.

    """

    return cc_public.graph.extract.facts_of(cc_public.graph.extract.documents(root))


# -----------------------------------------------------------------------------
def contract(graph: Graph, facts: Facts, id_interface: str) -> Contract | None:
    """
    Return the contract of the interface control document id_interface,
    or None if the tree holds no such document.

    The comparison is the one the checks parameter_mismatch and
    signature_mismatch make, read here for display: a part a member
    does not state is not compared.

    """

    item = graph.map_item.get(id_interface)
    if item is None or not id_interface.startswith(PREFIX_INTERFACE):
        return None

    code         = _Code(facts)
    map_surface  = item.node.get(KEY_SURFACE) or {}
    list_native  = []
    list_surface = []
    for (key, value) in map_surface.items():
        form = next(iter(value), '') if isinstance(value, dict) else ''
        if form == FORM_NATIVE:
            list_native.append(value)
        elif form in MAP_FORM:
            list_surface.append(_surface(graph, code, key, form, value[form]))

    map_group = _groups(graph, code, {KEY_DECLARATION: item.node.get(KEY_DECLARATION),
                                      KEY_SURFACE:     list_native})

    return Contract(item = item, list_group = map_group, list_surface = list_surface)


# -----------------------------------------------------------------------------
def _groups(graph: Graph, code: '_Code', node: object) -> list[tuple[str, list[Member]]]:
    """
    Return the members held in node, by group, in the order they are
    written.

    """

    map_group = collections.defaultdict(list)
    for (group, name, node_member) in _walk(node, ()):
        map_group[group].append(_member(graph, code, group, name, node_member))
    return list(map_group.items())


# -----------------------------------------------------------------------------
def _surface(graph: Graph, code: '_Code', key: str, form: str, node: dict) -> Surface:
    """
    Return the surface filed under key, of form, whose body is node:
    its members, and each part of its semantics the schema names, with
    its gloss from the schema and what node states of it.

    """

    (label, name_def) = MAP_FORM[form]
    schema            = graph.node(ID_SCHEMA) or {}
    map_property      = (schema.get(KEY_DEFS, {}).get(name_def, {}).get(KEY_PROPERTIES) or {})
    list_semantics    = [(field,
                          ' '.join(str(value.get(KEY_DESCRIPTION, '')).split())
                             .removeprefix('Optional. '),
                          str(node.get(field) or ''))
                         for (field, value) in map_property.items()
                         if isinstance(value, dict) and value.get(KEY_REF) == REF_SEMANTICS]

    return Surface(key            = key,
                   form           = form,
                   label          = label,
                   node           = node,
                   list_group     = _groups(graph, code, node),
                   list_semantics = list_semantics)


# -----------------------------------------------------------------------------
def members(node: dict) -> list[str]:
    """
    Return the ids of the members held in the document node, in the
    order they are written, leaving out the members held in a member
    (the parameters of a function, say).

    """

    return [member.get(KEY_ID_SELF) for (_, _, member) in _walk(node, ())]


# -----------------------------------------------------------------------------
def group_name(group: str) -> str:
    """
    Return the name of the group of members held under the key group.

    """

    return MAP_GROUP.get(group, group.replace('_', ' ').capitalize())


# -----------------------------------------------------------------------------
class _Code:
    """
    What the code says of each python function, and where each item is
    written, read from the facts of a tree.

    """

    # -------------------------------------------------------------------------
    def __init__(self, facts: Facts) -> None:
        """
        Index facts by item.

        """

        self.map_name     = collections.defaultdict(dict)
        self.map_part     = collections.defaultdict(lambda: collections.defaultdict(dict))
        self.map_returns  = {}
        self.map_stated   = collections.defaultdict(dict)
        self.map_location = {}

        for (id_item, position, name) in facts.get('python_parameter', ()):
            self.map_name[id_item][int(position)] = name
        for (id_item, position, part, value) in facts.get('python_signature', ()):
            self.map_part[id_item][int(position)][part] = value
        for (id_item, spelling) in facts.get('python_returns', ()):
            self.map_returns[id_item] = spelling
        for (id_item, part, value) in facts.get('stated', ()):
            self.map_stated[id_item][part] = value
        for (id_item, _, _, file, line) in facts.get('item', ()):
            self.map_location[id_item] = '{file}, line {line}'.format(
                                             file = cc_public.graph.extract.file_of(file),
                                             line = line)

    # -------------------------------------------------------------------------
    def names(self, id_function: str) -> list[str]:
        """
        Return the names of the parameters of id_function, in order.

        """

        map_name = self.map_name.get(id_function, {})
        return [map_name[position] for position in sorted(map_name)]


# -----------------------------------------------------------------------------
def _walk(node: object, tuple_key: tuple) -> list[tuple[str, str, dict]]:
    """
    Return the group, the name and the document of each member held in
    node under the keys tuple_key, not looking inside a member.

    """

    if isinstance(node, list):
        return [found for value in node for found in _walk(value, tuple_key)]
    if not isinstance(node, dict):
        return []

    id_self = node.get(KEY_ID_SELF)
    if isinstance(id_self, str) and id_self.startswith(PREFIX_MEMBER):
        group = tuple_key[-2] if len(tuple_key) >= 2 else ''
        return [(group, str(node.get('name', tuple_key[-1] if tuple_key else id_self)), node)]

    return [found for (key, value) in node.items() if key != KEY_RELATION
            for found in _walk(value, (*tuple_key, key))]


# -----------------------------------------------------------------------------
def _member(graph: Graph, code: _Code, group: str, name: str, node: dict) -> Member:
    """
    Return the member node, named name in group, with what the code
    that realizes it says.

    """

    id_self       = node[KEY_ID_SELF]
    list_realizer = graph.sources(R_REALIZES, id_self)
    id_function   = next((id_item for id_item in list_realizer if id_item in code.map_name
                          or id_item in code.map_returns), None)
    stated        = code.map_stated.get(id_self, {})

    list_parameter = []
    for (position, value) in enumerate(node.get(KEY_PARAMETER) or []):
        if not isinstance(value, dict):
            continue
        id_parameter = str(value.get(KEY_ID_SELF, ''))
        map_code     = None
        if id_function is not None:
            map_code = dict(code.map_part[id_function].get(position, {}))
            map_code['name'] = code.map_name[id_function].get(position, '')
        list_parameter.append(Parameter(id       = id_parameter,
                                        name     = str(value.get('name', '')),
                                        node     = value,
                                        map_part = code.map_stated.get(id_parameter, {}),
                                        map_code = map_code))

    list_extra = []
    if id_function is not None:
        list_extra = code.names(id_function)[len(list_parameter):]

    member = Member(id             = id_self,
                    name           = name,
                    group          = group,
                    node           = node,
                    list_parameter = list_parameter,
                    list_realizer  = list_realizer,
                    location       = code.map_location.get(list_realizer[0], '')
                                     if list_realizer else '',
                    returns        = stated.get(KEY_RETURNS),
                    returns_code   = code.map_returns.get(id_function) if id_function else None,
                    list_extra     = list_extra,
                    map_verdict    = {})
    member.map_verdict = _verdicts(member, id_function is not None)
    return member


# -----------------------------------------------------------------------------
def _verdicts(member: Member, has_code: bool) -> dict[str, str | None]:
    """
    Return the verdict of each column on member: whether the code
    agrees with what it states, or None where the column does not
    apply to it.

    """

    map_verdict = {COLUMN_REALIZED: AGREES if member.list_realizer else UNREALIZED}
    if not member.is_function():
        return map_verdict | {column: None for (column, _, _) in LIST_COLUMN[1:]}
    if not has_code:
        return map_verdict | {column: UNREALIZED for (column, _, _) in LIST_COLUMN[1:]}

    is_named_alike = (not member.list_extra
                      and all(parameter.name == parameter.map_code['name']
                              for parameter in member.list_parameter))
    map_verdict[COLUMN_NAMES] = AGREES if is_named_alike else DIFFERS

    for (column, _, tuple_part) in LIST_COLUMN:
        if not tuple_part:
            continue
        list_stated = [(parameter, part) for parameter in member.list_parameter
                       for part in tuple_part if part in parameter.map_part]
        if not list_stated:
            map_verdict[column] = UNSTATED
        elif any(parameter.differs(part) for (parameter, part) in list_stated):
            map_verdict[column] = DIFFERS
        else:
            map_verdict[column] = AGREES

    if member.returns is None:
        map_verdict[COLUMN_RETURNS] = UNSTATED
    elif member.returns != (member.returns_code or ''):
        map_verdict[COLUMN_RETURNS] = DIFFERS
    else:
        map_verdict[COLUMN_RETURNS] = AGREES

    return map_verdict
