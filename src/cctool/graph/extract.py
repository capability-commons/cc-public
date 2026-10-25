"""
---

id_self:                pym_cctool.graph.extract
guid_self:              pym_067145ba52314db69f64c5605d575451
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Fact extraction
brief:                  |
                        Extract the facts of the graph of data items
                        held in a tree.
description:            |
                        This module reads every item in the tree: the
                        YAML files under a _data directory, the
                        docstrings of python modules and of the
                        classes and functions in them, and the comment
                        headers of other files. It returns the facts
                        they hold, one set of rows for each base
                        predicate. PREDICATE names each base
                        predicate, its columns and what a row of it
                        means, and is the one place they are declared,
                        for logic programs and for SQL alike. A file
                        that ought to hold a YAML document but cannot
                        be read is not an error here: it gives a row
                        of unreadable, so that the checker reports it
                        with every other failure.
edge:                   []

...
"""


import ast
import hashlib
import os
import pathlib
import re
import typing
import weakref

import ruamel.yaml
import ruamel.yaml.scalarstring

import cctool.graph.prefix
import cctool.graph.tool


# Round trip loading keeps the line and column of every key and value,
# so that a fact can later be traced to where it is written.
#
YAML              = ruamel.yaml.YAML(typ = 'rt')

KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_ID_RELATION   = 'id_relation'
KEY_ID_TARGET     = 'id_target'
KEY_ENTRIES       = 'entries'
KEY_PREFIX        = 'prefix'
KEY_REGEX_ID      = 'regex_id'
KEY_INVERSE       = 'inverse'
KEY_ALIAS         = 'alias'
KEY_ACYCLIC       = 'acyclic'
KEY_READS_THROUGH = 'reads_through'
KEY_FAMILY        = 'prefix_family'
KEY_REPLACEMENT   = 'replacement'
KEY_BREAKS        = 'breaks'
KEY_EXCEPTION     = 'prefix_exception'
KEY_LABEL         = 'label'
KEY_ENFORCEMENT   = 'enforcement'

# The fields of a concept that hold its terms, by the rating of each.
#
RATING_DEPRECATED = 'deprecated'
MAP_TERM_RATING   = {'term_preferred':  'preferred',
                     'term_admitted':   'admitted',
                     'term_deprecated': RATING_DEPRECATED}
KEY_REF           = '$ref'
KEY_SCHEMA_URI    = '$id'

# The parts of a signature that an item may state, as an interface
# member does.
#
KEY_TYPE          = 'type'
KEY_DEFAULT       = 'default'
KEY_OPTIONAL      = 'optional'
KEY_VARIADIC      = 'variadic'
KEY_RETURNS       = 'returns'
KEY_SPELLING      = 'spelling'

# Fields whose text names no item: identity, aliases, which name what
# no longer exists, patterns, and what code spells a name, a type, a
# default or a value as. A field named id_<field> or guid_<field> is a
# reference, and is read as one. The old id, new id and guid of a
# rename that a release records say what was so at the release, not
# what is now, so they are not read as references or mentions either.
#
SET_KEY_UNNAMED   = {'id_self', 'guid_self', 'alias', 'prefix', 'regex_id', 'pattern',
                     '$id', '$schema', '$ref', 'name', 'spelling', 'default', 'value',
                     'old', 'new', 'guid'}

# A word shaped like an id, not part of a path or of a longer word. A
# file name is read as the id it is named for, and a word that a * ends
# is a pattern, not a mention.
#
REGEX_MENTION     = re.compile(r'(?<![A-Za-z0-9_$./-])[a-z]{1,8}_[a-z0-9][a-z0-9_]*'
                               r'(?:\.[a-z0-9_][a-z0-9_]*)*')
REGEX_SUFFIX      = re.compile(r'\.(?:yaml|py|lp|toml|json|md)$')
MARK_GLOB         = '*'

# A citation of a part of a file, such as gate.py within is_code_staged,
# names the part as the file spells it, not an item, so a word in that
# place is not a mention. The check of citations checks it against the
# file instead.
#
REGEX_CITED       = re.compile(r'[\w./-]\.(?:py|lp|yaml|yml|toml|json)\s+(?:within|at|just\s+after)'
                               r'\s+(?:[\w$.-]+(?:,\s+|\s+and\s+))*$')
SIZE_CITED        = 400

# A word, and a span in double quotes, which quotes another's words as
# they were written and so is not held to the rules of the text around it.
#
REGEX_WORD        = re.compile(r'[A-Za-z]+')
REGEX_QUOTED      = re.compile(r'"[^"\n]*"')
REGEX_REF         = re.compile(r'/(sch_[a-z0-9_]+)\.yaml')

# A wiki link to a concept: [[term]], or [[concept|label]]
# where the concept is named by its id and the label is shown in its place.
#
REGEX_TERM_LINK   = re.compile(r'\[\[([^\[\]|\n]+?)(?:\|([^\[\]|\n]+?))?\]\]')

# A definition that opens with an article and then a link names its
# genus there, the broader concept it narrows: "A [[file]] that ...".
#
KEY_DEFINITION    = 'brief'
REGEX_GENUS       = re.compile(r'\s*(?:A|An|One|The)\s+$')
MAP_PLURAL        = {'ies': 'y', 'es': '', 's': ''}

PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
DELIM_PREFIX      = '_'
DIR_DATA          = '_data'

# The documents of a consumed tree are keyed by their path in that tree,
# under this folder and the id of its segment item, which no real path
# in a tree has. So _consumed/SEGMENT/_data/... is a document of the
# segment whose item is SEGMENT, at _data/... in its own tree.
#
DIR_CONSUMED      = '_consumed'

# A release writes, into the _data of its package, a file of shadows under
# this folder: one for each item that the package leaves behind but a
# shipped item names. No tree holds the folder.
#
DIR_SHADOW        = 'shadow'
PREFIX_SEGMENT    = cctool.graph.prefix.stem('type_federated_segment')
SUFFIX_YAML       = '.yaml'
SUFFIX_PYTHON     = '.py'
SUFFIX_PROGRAM    = '.lp'
SUFFIX_SCRIPT     = '.js'
SUFFIX_STYLE      = '.css'

# A YAML document opens with this line and closes with the next. In a
# comment header each line also begins with the comment marker: # in
# most files, % in a logic program, // in a script, and * in a style
# sheet, whose comments are blocks.
#
LINE_OPEN         = '---'
LINE_CLOSE        = '...'
MARK_COMMENT      = '#'
MAP_MARK_COMMENT  = {SUFFIX_PROGRAM: '%',
                     SUFFIX_SCRIPT:  '//',
                     SUFFIX_STYLE:   ' *'}

# A script may open with a line that names its interpreter, and a style
# sheet with the line that opens its comment block, which the line after
# the header closes. The comment header then opens on the line after.
#
MARK_SHEBANG      = '#!'
LINE_BLOCK_OPEN   = '/*'
LINE_BLOCK_CLOSE  = ' */'

# Directories that hold no items: version control, environments,
# caches, local tools and the frozen fixture that tests copy in.
#
SET_DIR_SKIP      = {'.git', '.pixi', '.venv', '__pycache__', '_tools', '_fixture'}

# The YAML documents read so far, keyed by the path and the digest of
# the file that holds each. It is emptied when it holds this many.
#
MAP_READ          = {}
COUNT_READ        = 4096

# The digest of the file that each YAML document read from a YAML file
# or python module was read from, keyed by the id of the document, which
# is kept with it so that the id is not reused. It is emptied with
# MAP_READ.
#
MAP_DIGEST        = {}

# The facts of each YAML document extracted so far, keyed by its file,
# the line its first line is on, and the words that prose avoids and the
# terms that text is searched for, with the document, so that a document
# read again as the same object is not walked again. It is emptied when
# it holds COUNT_FACTS.
#
MAP_FACTS         = {}
COUNT_FACTS       = 8192

# How much of the head of a file that is not YAML or python is read to
# tell whether it has changed. A comment header is far shorter.
#
SIZE_HEAD         = 65536

# Each base predicate: its columns, and what one row of it states. A
# column is a symbol unless its name is followed by :number. A line
# is the line of the file, counted from 1, that the key of the field
# is on: id_self for an item, and id_<field> for a reference.
#
TYPE_SYMBOL       = 'symbol'
DELIM_TYPE        = ':'

PREDICATE         = {
    'item':               (('id', 'guid', 'holder', 'file', 'line:number'),
                           'The item id, with guid, is written in file at line. holder '
                           'is the id of the item that contains it, or empty if none '
                           'does.'),
    'reference':          (('holder', 'field', 'id', 'guid', 'file', 'line:number'),
                           'The item holder names the item id, with guid, in a pair '
                           'of fields id_<field> and guid_<field>, written in file at '
                           'line.'),
    'edge':               (('source', 'relation', 'target'),
                           'The item source records an edge of relation to target, '
                           'as written. primary_edge reads edges through inverses.'),
    'type_prefix':        (('type', 'prefix', 'regex'),
                           'The type has the id prefix, and its ids match regex.'),
    'prefix_family':      (('type', 'family'),
                           'The prefix of the type belongs to family, whose prefixes '
                           'may differ from one another by one letter.'),
    'prefix_exception':   (('type', 'reason'),
                           'The prefix of the type breaks the prefix rule, for reason.'),
    'enforcement':        (('rule', 'mechanism'),
                           'The writing style rule says that mechanism holds it today.'),
    'word_replacement':   (('rule', 'avoided', 'preferred'),
                           'The writing style rule asks for preferred in place of the '
                           'word avoided.'),
    'avoided_word':       (('holder', 'word', 'file', 'line:number'),
                           'The text of a field of the item holder uses word, which a '
                           'writing style rule asks to replace, in file at line.'),
    'term_word':          (('holder', 'field', 'term', 'file', 'line:number'),
                           'The text of the field of the item holder uses the words of '
                           'term, a preferred or admitted term of a concept, outside '
                           'any link or double quotes, in file at line. The words may '
                           'differ from term in case or by a plural ending. Where '
                           'terms overlap, the longest is taken.'),
    'designation':        (('concept', 'term', 'rating'),
                           'The concept has the term, rated preferred, admitted or '
                           'deprecated.'),
    'label':              (('id', 'label'),
                           'The item id, an external class, has label in the release '
                           'it was brought in from.'),
    'term_link':          (('holder', 'term', 'concept', 'file', 'line:number'),
                           'The text of a field of the item holder links term to a '
                           'concept, in file at line. A wiki link written [[term]] leaves '
                           'concept empty, to be found by the term; one written '
                           '[[concept|term]] names it.'),
    'genus_link':         (('holder', 'term', 'concept'),
                           'The brief of the item holder opens with an article and a '
                           'link of term to a concept, which names its genus. As for '
                           'term_link, concept is empty when the link finds it by the '
                           'term.'),
    'term_form':          (('text', 'form'),
                           'The text, a term of a concept, the label of an external '
                           'class or the term of a link, has form when lower-cased, '
                           'and also made singular if it is the term of a link. Texts '
                           'with a form in common name the same term.'),
    'inverse_relation':   (('inverse', 'relation'),
                           'An edge of inverse is an edge of relation, reversed.'),
    'register_entry_key': (('register', 'key', 'id'),
                           'The register holds, under key, a register entry with id.'),
    'module_name':        (('id', 'expected'),
                           'A python module, package, class or function, or a logic '
                           'program file, holds the item id, and its place in the tree '
                           'calls for the id expected.'),
    'python_parameter':   (('id', 'position:number', 'name'),
                           'The python function that holds the item id takes the '
                           'parameter name at position, counted from 0, in the order a '
                           'caller gives them. The receiver of a method is not one.'),
    'python_signature':   (('id', 'position:number', 'part', 'value'),
                           'The parameter at position of the python function that '
                           'holds the item id has value for part: its type and '
                           'default as the code writes them, or empty if it has '
                           'none, and whether it is optional and variadic, as true '
                           'or false.'),
    'python_returns':     (('id', 'type'),
                           'The python function that holds the item id returns type, '
                           'as the code writes it, or empty if it does not say.'),
    'stated':             (('id', 'part', 'value'),
                           'The item id states value for part of a signature: the '
                           'spelling of its type, its default, whether it is optional '
                           'or variadic, as true or false, or the spelling of the type '
                           'it returns. A parameter of a command also states its kind, '
                           'whether it is a flag, and, for an argument, its position '
                           'among the arguments, counted from 0.'),
    'position':           (('id', 'position:number'),
                           'The item id is written as the element at position, counted '
                           'from 0, of a list.'),
    'tree_file':          (('file',),
                           'The tree holds file, whether or not the file holds an '
                           'item.'),
    'mention':            (('holder', 'id', 'file', 'line:number'),
                           'The text of a field of the item holder names id, in file '
                           'at line. Any word shaped like an id is a mention, but only '
                           'one with the prefix of a known type need name an item.'),
    'alias':              (('id', 'alias'),
                           'The item id was once named alias.'),
    'acyclic_relation':   (('relation',),
                           'No chain of edges of relation may lead from an item back '
                           'to itself.'),
    'reads_through':      (('relation', 'end'),
                           'An edge of relation is about the thing that the proxy at '
                           'its end, source or target, points at.'),
    'schema_uri':         (('schema', 'uri', 'file', 'line:number'),
                           'The schema gives uri as its $id, in file at line.'),
    'schema_ref':         (('holder', 'schema', 'file', 'line:number'),
                           'The schema holder refers to the schema with a $ref, in '
                           'file at line.'),
    'unreadable':         (('file', 'line:number', 'message'),
                           'The file ought to hold a YAML document, but cannot be read: '
                           'message says why, and line is where.'),
    'interface_port':     (('interface', 'kind', 'name', 'member'),
                           'A dataflow step surface of the interface control document '
                           'interface has the member, called name, as a port or setting '
                           'of kind: input, output, state or settings.'),
    'dataflow_node':      (('graph', 'key', 'node', 'os_process'),
                           'The dataflow graph graph holds the dataflow node '
                           'node under key, placed on the OS process with that key, or '
                           'on none if os_process is empty.'),
    'dataflow_edge':      (('graph', 'source', 'source_port', 'target', 'target_port',
                            'direction', 'file', 'line:number'),
                           'A dataflow edge of the dataflow graph graph carries '
                           'data from the port source_port of the dataflow node source '
                           'to the port target_port of the dataflow node target, '
                           'feedforward or feedback, written in file at line. An end it '
                           'does not name is empty.'),
    'dataflow_setting':   (('node', 'name'),
                           'The settings of the dataflow node node give a value for '
                           'the setting name.'),
    'os_process':         (('graph', 'key', 'host'),
                           'The dataflow graph graph has an OS process under '
                           'key, which runs on the host with that key, or on none if '
                           'host is empty.'),
    'host':               (('graph', 'key'),
                           'The dataflow graph graph has a host under key.'),
    'command_member':     (('member', 'program', 'command', 'name'),
                           'A command line surface of program states the member as '
                           'command, its words after the program name joined by '
                           'spaces, if name is empty, or else as the parameter name '
                           'of command: the first spelling of an option, or the name '
                           'of an argument. The parameters of the program itself '
                           'have an empty command.'),
    'click_command':      (('program', 'command'),
                           'click describes command, its words after the program name '
                           'joined by spaces, or empty for the program itself, as a '
                           'command of program, the running cctool. It is a fact of the '
                           'tool, and not of any document.'),
    'click_parameter':    (('program', 'command', 'name', 'part', 'value'),
                           'click describes the parameter name of command of program, '
                           'the first spelling of an option or the name of an '
                           'argument, as having value for part: its kind, argument or '
                           'option; its type, as click names it; its default, or empty '
                           'if it has none; whether it is optional, variadic or a flag, '
                           'as true or false; and, for an argument, its position among '
                           'the arguments, counted from 0. The option for help is '
                           'click\'s own, and is left out.'),
    'check_member':       (('member', 'interface', 'check', 'severity'),
                           'The interface control document interface states the member '
                           'as its check named check, whose rows are severity: failure '
                           'or advice.'),
    'segment_of':         (('file', 'segment'),
                           'The file is held by the segment: the segment item of the '
                           'tree it was read from, or empty if that tree holds no '
                           'segment item or more than one. A consumed tree is read '
                           'beside the tree being checked, under DIR_CONSUMED.'),
    'consumed_file':      (('file',),
                           'The file was read from a tree that the tree being checked '
                           'consumes.'),
    'shadow':             (('id', 'file'),
                           'The item id is a shadow, written in file: it stands for an '
                           'item that a release left behind, with its id and guid and '
                           'nothing else.'),
    'check_severity':     (('check', 'severity'),
                           'The running cctool reports the rows of check as severity, '
                           'failure or advice. It is a fact of the tool, and not of any '
                           'document.'),
}

# Python modules are imported with src as the root of the path. The
# item of a package is held in the docstring of its __init__ module.
# A logic program file is named in the same way as a python module.
#
DIR_IMPORT_ROOT   = 'src'
MAP_PREFIX_MODULE = {SUFFIX_PYTHON:  cctool.graph.prefix.stem('type_python_module'),
                     SUFFIX_PROGRAM: cctool.graph.prefix.stem('type_logic_program_file')}
PREFIX_PACKAGE    = cctool.graph.prefix.stem('type_python_package')
NAME_PACKAGE      = '__init__'
DELIM_MODULE      = '.'

# A class or function holds an item in its docstring, as a module does.
# Its YAML document is keyed by the path of its file and the names of
# the definitions down to it, in the form pytest uses:
# src/cctool/graph/jq.py::query. Its id is the name of its module and
# those names, in lower case, under the prefix of its kind.
#
DELIM_DEFINITION  = '::'
# A predicate of a logic program holds an item in a comment, as a
# function does in its docstring: a YAML document whose lines each begin
# with %, written before the declaration of the predicate. Its YAML
# document is keyed by the path of its file and the name of the
# predicate, src/cctool/check/check.lp::bad_id, and its id is the name
# of its logic program file and the name of the predicate, under this
# prefix.
#
PREFIX_PREDICATE  = cctool.graph.prefix.stem('type_logic_program_predicate')
REGEX_DECL_NAME   = re.compile(r'^%[ \t]*decl[ \t]+(\w+)[ \t]*\(')

MAP_PREFIX_KIND   = {ast.ClassDef:         cctool.graph.prefix.stem('type_python_class'),
                     ast.FunctionDef:      cctool.graph.prefix.stem('type_python_function'),
                     ast.AsyncFunctionDef: cctool.graph.prefix.stem('type_python_function')}

# Where a dataflow step surface lists its ports and settings, and the
# fields of a dataflow graph and of the ends of its dataflow
# edges. A dataflow edge is feedforward unless it says otherwise.
#
KEY_SURFACE       = 'surface'
KEY_DATAFLOW      = 'dataflow_step'
TUPLE_PORT_KIND   = ('input', 'output', 'state', 'settings')
KEY_NAME          = 'name'
KEY_NODE          = 'dataflow_node'
KEY_EDGE          = 'dataflow_edge'
KEY_OS_PROCESS    = 'os_process'
KEY_HOST          = 'host'
KEY_SETTINGS      = 'settings'
KEY_SOURCE        = 'source'
KEY_TARGET        = 'target'
KEY_DIRECTION     = 'direction'
KEY_ID_NODE       = 'id_dataflow_node'
KEY_ID_PORT       = 'id_port'
FEEDFORWARD       = 'feedforward'

# Where a command line surface names its program and lists its
# commands, and the fields that only a parameter of a command states.
#
KEY_COMMAND_LINE  = 'command_line'
KEY_PROGRAM       = 'program'
KEY_COMMAND       = 'command'
KEY_PARAMETER     = 'parameter'
KEY_KIND          = 'kind'
KEY_FLAG          = 'flag'

# Where an interface control document lists the checks it reports, and
# the severity of each.
#
KEY_CHECK         = 'check'
KEY_SEVERITY      = 'severity'

# What the code says of each class or function that holds a YAML document,
# keyed by the id of the document, with a weak reference to it: the id its place
# calls for, the parameters of a function, each as its name and a mapping
# of the parts of python_signature, and the type it returns. None of it is
# in the document, so it is noted when the file is read. It is keyed by
# the document and not by the file, since another copy of a file may say
# other things with the same key. An entry goes when its document does.
# The receiver of a method is not a parameter.
#
MAP_DEFINITION    = {}
SET_RECEIVER      = {'self', 'cls'}

Facts             = dict[str, set[tuple[str, ...]]]
Documents         = dict[str, tuple[typing.Any, int]]

# The terms to search text for, keyed by their words in lower case, and
# the first word of each term of more than one word.
#
Terms             = tuple[dict[str, str], set[str]]


# -----------------------------------------------------------------------------
class ErrorRead(Exception):
    """
    A file that ought to hold a YAML document cannot be read. line is
    the line of the file where the fault is.

    """

    # -------------------------------------------------------------------------
    def __init__(self, message: str, line: int) -> None:
        """
        Keep message, on one line, and line.

        """

        super().__init__(' '.join(message.split()))
        self.line = line


# -----------------------------------------------------------------------------
class Unreadable:
    """
    The YAML document of a file that cannot be read, held in its place
    in the documents of a tree, with the error that says why.

    """

    # -------------------------------------------------------------------------
    def __init__(self, error: ErrorRead) -> None:
        """
        Keep error.

        """

        self.error = error


# -----------------------------------------------------------------------------
def is_document(document: typing.Any) -> bool:
    """
    Return True if document is one that a file holds and that could be
    read, not None or an Unreadable.

    """

    return document is not None and not isinstance(document, Unreadable)


# -----------------------------------------------------------------------------
def extract(root: pathlib.Path) -> Facts:
    """
    Return the facts of the tree under root, keyed by predicate.

    """

    return facts_of(documents(root))


# -----------------------------------------------------------------------------
def documents(root:    pathlib.Path,
              package: pathlib.PurePosixPath | None = None) -> Documents:
    """
    Return each YAML document in the tree under root, with the line of
    its file that its first line is on, keyed by the file's path
    relative to root.

    If package is given, root is the folder of an installed python
    package, which holds the data items of its tree in a _data folder.
    Each of its other files is keyed as if it were under package, where
    it was in the tree the package was built from, so that its ids are
    those that tree gives it.

    Documents are read from YAML files under a _data directory, from
    the docstrings of a python module and of its classes and functions,
    and from the comment header of any other file. A file that holds no
    document is kept, with None in its place, so that the tree's files
    are known. A file that cannot be read has an Unreadable in place of
    its document. A class or function is keyed as file_of says.

    """

    map_document = {}

    for path in _files(root):
        relative = path.relative_to(root)
        if package is not None and relative.parts[0] != DIR_DATA:
            relative = pathlib.Path(package, relative)
        try:
            map_document.update(read(path, relative))
        except ErrorRead as error:
            map_document[str(relative)] = (Unreadable(error), error.line)

    return map_document


# -----------------------------------------------------------------------------
def _files(root: pathlib.Path) -> list[pathlib.Path]:
    """
    Return the path of each file under root, in order, leaving out every
    folder SET_DIR_SKIP names without walking into it. An environment
    under .pixi holds ten times the files of the tree, so walking it
    only to skip them was most of the time a read of the tree took.

    """

    list_path = []

    for (dir_walk, list_dir, list_name) in os.walk(root):
        list_dir[:] = [name for name in list_dir if name not in SET_DIR_SKIP]
        list_path.extend(pathlib.Path(dir_walk, name) for name in list_name
                         if name not in SET_DIR_SKIP)

    return sorted(path for path in list_path if path.is_file())


# -----------------------------------------------------------------------------
def file_of(key: str) -> str:
    """
    Return the path of the file that holds the YAML document keyed by
    key: the key itself for the document of a file, and the part before
    the first :: for that of a class or function.

    """

    return key.partition(DELIM_DEFINITION)[0]


# -----------------------------------------------------------------------------
def files(map_document: Documents) -> list[str]:
    """
    Return the path of each file that holds a YAML document that could
    be read, in order, once each.

    """

    return sorted({file_of(key) for (key, (document, _)) in map_document.items()
                   if is_document(document)})


# -----------------------------------------------------------------------------
def facts_of(map_document: Documents, with_tool: bool = True) -> Facts:
    """
    Return the facts that the YAML documents hold, keyed by predicate,
    with the facts of cctool itself unless with_tool is False. Those
    import its whole command line, and so every dependency it has.

    """

    facts                     = {name: set() for name in PREDICATE}
    facts['word_replacement'] = _replacements(map_document)
    terms                     = _terms(map_document)
    context                   = (frozenset(row[1] for row in facts['word_replacement']),
                                 frozenset(terms[0].items()),
                                 frozenset(terms[1]))

    if len(MAP_FACTS) >= COUNT_FACTS:
        MAP_FACTS.clear()

    for (file, (document, base)) in map_document.items():
        if file == file_of(file):
            facts['tree_file'].add((file,))
        if isinstance(document, Unreadable):
            facts['unreadable'].add((file, base, str(document.error)))
            continue
        if document is None:
            continue
        key = (file, base, context)
        if key not in MAP_FACTS or MAP_FACTS[key][0] is not document:
            MAP_FACTS[key] = (document, _facts_of_document(file, document, base,
                                                           facts['word_replacement'], terms))
        for (name, set_row) in MAP_FACTS[key][1].items():
            facts[name].update(set_row)

    facts['term_form']     = _forms(facts)
    facts['segment_of']    = _segments(facts)
    facts['consumed_file'] = {(file,) for (file,) in facts['tree_file']
                              if consumer(file) is not None}
    facts['shadow']        = {(row[0], row[3]) for row in facts['item'] if is_shadow(row[3])}

    for (name, set_row) in (cctool.graph.tool.facts() if with_tool else {}).items():
        facts[name].update(set_row)

    return facts


# -----------------------------------------------------------------------------
def _segments(facts: Facts) -> set[tuple[str, str]]:
    """
    Return the segment that holds each file of the facts: the segment
    that its key names for the file of a consumed tree, and for the
    file of the tree being checked, its one segment item, or empty if
    it holds none or more than one.

    """

    set_own = {row[0] for row in facts['item']
               if row[0].startswith(PREFIX_SEGMENT) and consumer(row[3]) is None}
    own     = next(iter(set_own)) if len(set_own) == 1 else ''

    return {(file, consumer(file) or own) for (file,) in facts['tree_file']}


# -----------------------------------------------------------------------------
def consumer(key: str) -> str | None:
    """
    Return the segment of the consumed tree that the document keyed by
    key was read from, or None if key is that of the tree being
    checked.

    """

    list_part = pathlib.PurePosixPath(key).parts
    if len(list_part) > 2 and list_part[0] == DIR_CONSUMED:
        return list_part[1]
    return None


# -----------------------------------------------------------------------------
def is_shadow(key: str) -> bool:
    """
    Return True if the document keyed by key is a file of shadows: one
    under the folder DIR_SHADOW of _data, which a release writes and
    no tree holds.

    """

    return pathlib.PurePosixPath(in_tree(key)).parts[:2] == (DIR_DATA, DIR_SHADOW)


# -----------------------------------------------------------------------------
def in_tree(key: str) -> str:
    """
    Return key as the path that it has in the tree it was read from:
    key itself for the tree being checked, and key without its
    DIR_CONSUMED folder and segment for a consumed tree.

    """

    if consumer(key) is None:
        return key
    return str(pathlib.PurePosixPath(*pathlib.PurePosixPath(key).parts[2:]))


# -----------------------------------------------------------------------------
def _facts_of_document(file:             str,
                       document:         typing.Any,
                       base:             int,
                       word_replacement: set[tuple[str, str, str]],
                       terms:            Terms) -> Facts:
    """
    Return the facts that document, read from file with its first line
    at line base, holds, keyed by predicate, with the predicates it
    holds no facts of left out. word_replacement holds the words that
    prose avoids, and terms the terms that text is searched for.

    """

    facts                     = {name: set() for name in PREDICATE}
    facts['word_replacement'] = word_replacement

    _walk(document, '', (file, base), facts, terms)
    if isinstance(document, dict):
        _ports(document, facts)
        _commands(document, facts)
        _checks(document, facts)
        _dataflow_graph(document, (file, base), facts)
        (held, definition) = MAP_DEFINITION.get(id(document), (None, None))
        if held is not None and held() is document:
            id_self                              = str(document.get(KEY_ID_SELF))
            (expected, tuple_parameter, returns) = definition
            facts['module_name'].add((id_self, expected))
            for (position, (name, map_part)) in enumerate(tuple_parameter):
                facts['python_parameter'].add((id_self, str(position), name))
                for (part, value) in map_part.items():
                    facts['python_signature'].add((id_self, str(position), part, value))
            if returns is not None:
                facts['python_returns'].add((id_self, returns))
        elif pathlib.Path(file).suffix in MAP_PREFIX_MODULE:
            facts['module_name'].add((str(document.get(KEY_ID_SELF)),
                                      module_name(pathlib.Path(file))))

    del facts['word_replacement']

    return {name: set_row for (name, set_row) in facts.items() if set_row}


# -----------------------------------------------------------------------------
def _forms(facts: Facts) -> set[tuple[str, str]]:
    """
    Return the forms of each term of a concept, of each label of an
    external class, and of each term that a link finds its concept by,
    so that a link may give a term in the plural or with a capital
    letter.

    """

    set_form = {(term, term.lower()) for (_, term, _) in facts['designation']}
    set_form.update((label, label.lower()) for (_, label) in facts['label'])

    for (_, term, concept, _, _) in facts['term_link']:
        if not concept:
            set_form.update((term, form) for form in forms(term))

    return set_form


# -----------------------------------------------------------------------------
def _terms(map_document: Documents) -> Terms:
    """
    Return each preferred or admitted term that a register entry gives,
    keyed by its words in lower case, and the first word of each term of
    more than one word. They are read before any text, so that every
    text can be searched for all of them.

    """

    map_term  = {}
    set_first = set()

    for (document, _) in map_document.values():
        map_entry = document.get(KEY_ENTRIES) if isinstance(document, dict) else None
        for entry in _map(map_entry).values():
            if not isinstance(entry, dict):
                continue
            for key in (key for (key, rating) in MAP_TERM_RATING.items()
                        if rating != RATING_DEPRECATED):
                value = entry.get(key)
                for term in [value] if isinstance(value, str) else _list_str(value):
                    list_word                     = REGEX_WORD.findall(term.lower())
                    map_term[' '.join(list_word)] = term
                    if len(list_word) > 1:
                        set_first.add(list_word[0])

    return (map_term, set_first)


# -----------------------------------------------------------------------------
def _term_words(text: str, terms: Terms) -> list[tuple[str, int]]:
    """
    Return each term of terms whose words text uses, with the offset in
    text where they begin. The longest term is taken where terms
    overlap, and the last word may have a plural ending.

    """

    (map_term, set_first) = terms
    size_max              = max((key.count(' ') + 1 for key in map_term), default = 0)

    list_match = list(REGEX_WORD.finditer(text))
    list_word  = [match.group(0).lower() for match in list_match]
    list_found = []
    index      = 0

    while index < len(list_word):
        size_top = min(size_max, len(list_word) - index) if list_word[index] in set_first else 1
        for size in range(size_top, 0, -1):
            words = ' '.join(list_word[index:index + size])
            term  = next((map_term[form] for form in forms(words) if form in map_term),
                         None)
            if term is not None:
                list_found.append((term, list_match[index].start()))
                index += size
                break
        else:
            index += 1

    return list_found


# -----------------------------------------------------------------------------
def forms(term: str) -> set[str]:
    """
    Return the forms that the term of a link may match a term of a
    concept by: lower-cased, and also with a plural ending made
    singular: ies to y, and es or s dropped.

    """

    form     = term.lower()
    set_form = {form}

    for (suffix, singular) in MAP_PLURAL.items():
        if form.endswith(suffix):
            set_form.add(form.removesuffix(suffix) + singular)

    return set_form


# -----------------------------------------------------------------------------
def _replacements(map_document: Documents) -> set[tuple[str, str, str]]:
    """
    Return the rule, the avoided word and the preferred word of each
    replacement that a register entry lists. They are read before any
    text, so that every text can be judged against all of them.

    """

    set_row = set()

    for (document, _) in map_document.values():
        map_entry = document.get(KEY_ENTRIES) if isinstance(document, dict) else None
        for entry in _map(map_entry).values():
            if isinstance(entry, dict):
                for (avoided, preferred) in _map(entry.get(KEY_REPLACEMENT)).items():
                    set_row.add((str(entry.get(KEY_ID_SELF)), str(avoided), str(preferred)))

    return set_row


# -----------------------------------------------------------------------------
def column(spec: str) -> tuple[str, str]:
    """
    Return the name and the type of the column that spec declares.

    """

    (name, _, type_column) = spec.partition(DELIM_TYPE)
    return (name.strip(), type_column.strip() or TYPE_SYMBOL)


# -----------------------------------------------------------------------------
def module_name(relative: pathlib.Path) -> str:
    """
    Return the id that names the python module or logic program file
    at relative: the prefix and the dotted name it would be imported
    under, in lower case. An __init__ module is named for its package.

    """

    list_part = list(pathlib.PurePosixPath(in_tree(str(relative))).with_suffix('').parts)
    prefix    = MAP_PREFIX_MODULE[relative.suffix]

    if list_part and list_part[0] == DIR_IMPORT_ROOT:
        list_part = list_part[1:]

    if list_part and list_part[-1] == NAME_PACKAGE:
        list_part = list_part[:-1]
        prefix    = PREFIX_PACKAGE

    return prefix + DELIM_MODULE.join(list_part).lower()


# -----------------------------------------------------------------------------
def read(path: pathlib.Path, relative: pathlib.Path) -> Documents:
    """
    Return the YAML documents that the file at path holds, as parse_all
    does. relative is the path of the file relative to the root of the
    tree.

    A YAML file or python module that holds what it held when it was
    last read gives the same documents as then, the same objects, so
    that what was found by checking them can be reused. So does any
    other file whose size and head are as they were. A
    document is never changed once read.

    """

    if path.suffix in (SUFFIX_YAML, SUFFIX_PYTHON, SUFFIX_PROGRAM):
        data = path.read_bytes()
        key  = (str(relative), hashlib.blake2b(data, digest_size = 16).digest())
        if key not in MAP_READ:
            if len(MAP_READ) >= COUNT_READ:
                MAP_READ.clear()
                MAP_DIGEST.clear()
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError as error:
                raise ErrorRead('The file is not UTF-8: {error}'.format(error = error),
                                data.count(b'\n', 0, error.start) + 1) from error
            MAP_READ[key] = parse_all(text, relative)
            for (document, _) in MAP_READ[key].values():
                if isinstance(document, dict):
                    MAP_DIGEST[id(document)] = (document, key[1].hex())
        return MAP_READ[key]

    # Any other file may be large, or not text, so only its head is
    # read, and only as far as a comment header could go. It is known
    # to be unchanged by its size and the digest of its head.
    #
    with open(path, 'rb') as file:
        head = file.read(SIZE_HEAD)
    key  = (str(relative), path.stat().st_size, hashlib.blake2b(head, digest_size = 16).digest())
    if key not in MAP_READ:
        if len(MAP_READ) >= COUNT_READ:
            MAP_READ.clear()
        MAP_READ[key] = {str(relative): _header(_line_of_file(path), mark_comment(relative))}
    return MAP_READ[key]


# -----------------------------------------------------------------------------
def digest_of(document: typing.Any) -> str | None:
    """
    Return the digest of the file that read gave document from, or None
    if read did not give it from a YAML file or python module.

    """

    (held, digest) = MAP_DIGEST.get(id(document), (None, None))
    return digest if held is document else None


# -----------------------------------------------------------------------------
def parse_all(text: str, relative: pathlib.Path) -> Documents:
    """
    Return every YAML document that text holds, as the content of the
    file at relative: the document of the file, keyed by relative, as
    parse returns it, and that of each class or function of a python
    module that holds one, keyed as file_of says. Raise ErrorRead if one
    cannot be read.

    """

    map_document = {str(relative): parse(text, relative)}

    if relative.suffix == SUFFIX_PYTHON:
        for (key, expected, tuple_parameter, returns, document) in definitions(text,
                                                                                relative):
            _define(document[0], (expected, tuple_parameter, returns))
            map_document[key]   = document

    if relative.suffix == SUFFIX_PROGRAM:
        for (key, expected, document) in predicates(text, relative):
            _define(document[0], (expected, (), None))
            map_document[key]   = document

    return map_document


# -----------------------------------------------------------------------------
def _define(document: typing.Any, definition: tuple) -> None:
    """
    Note in MAP_DEFINITION what the code says of the class, function or
    predicate that holds document, until document is gone. Only a
    mapping has facts of its own, so nothing is noted for any other.

    """

    if not isinstance(document, dict):
        return
    MAP_DEFINITION[id(document)] = (weakref.ref(document), definition)
    weakref.finalize(document, MAP_DEFINITION.pop, id(document), None)


# -----------------------------------------------------------------------------
def definitions(text: str, relative: pathlib.Path) -> list[tuple]:
    """
    Return, for each class or function of the python module text, at
    relative, whose docstring holds a YAML document: its key, the id its
    place calls for, its parameters as _parameters gives them, the type
    it returns as _returns gives it, and the document with the line of
    the file that its first line is on. A class or function is one at the top of the
    module or in a class, not one inside a function. Raise ErrorRead if
    a document cannot be read.

    """

    list_found = []

    def visit(list_node, list_name):
        for node in list_node:
            if type(node) not in MAP_PREFIX_KIND:
                continue
            list_path = [*list_name, node.name]
            found     = _document_of(node)
            if found is not None:
                list_found.append((DELIM_DEFINITION.join([str(relative), *list_path]),
                                   definition_id(relative, list_path, node),
                                   _parameters(node, is_method = bool(list_name)),
                                   _returns(node),
                                   found))
            if isinstance(node, ast.ClassDef):
                visit(node.body, list_path)

    visit(_module(text).body, [])

    return list_found


# -----------------------------------------------------------------------------
def predicates(text: str, relative: pathlib.Path) -> list[tuple]:
    """
    Return, for each predicate of the logic program text, at relative,
    that holds an item: its key, the id its place calls for, and the
    document with the line of the file that its first line is on. Raise
    ErrorRead if a document cannot be read, or names no predicate.

    """

    list_found = []

    for (first, name, document) in blocks(text, mark_comment(relative)):
        if first == 0 or (first == 1 and is_lead(text.split('\n', 1)[0])):
            continue
        if name is None:
            raise ErrorRead('The YAML document in this comment is not followed by the '
                            'declaration of a predicate.', first + 1)
        list_found.append((DELIM_DEFINITION.join([str(relative), name]),
                           predicate_id(relative, name),
                           document))

    return list_found


# -----------------------------------------------------------------------------
def blocks(text: str, mark: str) -> list[tuple[int, str | None, tuple[typing.Any, int]]]:
    """
    Return, for each YAML document in a comment of text, whose comment
    lines begin with mark: the index of its first line, the name of the
    predicate whose declaration follows it in the same comment, or None
    if none does, and the document with the line of the file that its
    first line is on. Raise ErrorRead if a document cannot be read.

    """

    list_line  = text.split('\n')
    list_found = []

    for (first, last) in spans_marked(list_line, mark):
        name = None
        for line in list_line[last + 1:]:
            if not line.startswith(mark):
                break
            match = REGEX_DECL_NAME.match(line)
            if match:
                name = match.group(1)
                break
        list_doc = [_unmarked(line, mark) for line in list_line[first:last + 1]]
        list_found.append((first, name, (_load('\n'.join(list_doc), first + 1), first + 1)))

    return list_found


# -----------------------------------------------------------------------------
def spans_marked(list_line: list[str], mark: str) -> list[tuple[int, int]]:
    """
    Return the indices of the lines that open and close each YAML
    document written in a comment of list_line, each line of it
    beginning with mark.

    """

    list_span = []
    first     = None

    for (index, line) in enumerate(list_line):
        if not line.startswith(mark):
            first = None
            continue
        text = _unmarked(line, mark)
        if first is None and text == LINE_OPEN:
            first = index
        elif first is not None and text == LINE_CLOSE:
            list_span.append((first, index))
            first = None

    return list_span


# -----------------------------------------------------------------------------
def _unmarked(line: str, mark: str) -> str:
    """
    Return line without the comment marker that begins it, and the
    space after the marker.

    """

    return line[len(mark):].removeprefix(' ') if line.startswith(mark) else line


# -----------------------------------------------------------------------------
def predicate_id(relative: pathlib.Path, name: str) -> str:
    """
    Return the id of the item of the predicate name of the logic program
    at relative: the prefix of a predicate, the name of its file and
    name, in lower case and separated by full stops.

    """

    (_, _, module) = module_name(relative).partition(DELIM_PREFIX)

    return PREFIX_PREDICATE + DELIM_MODULE.join([module, name]).lower()


# -----------------------------------------------------------------------------
def _parameters(node: ast.AST, is_method: bool) -> tuple[tuple[str, dict[str, str]], ...]:
    """
    Return the parameters of the function node, in the order a caller
    gives them, or none if node is a class. Each is its name and a
    mapping of the parts of python_signature. The receiver of a method
    is left out.

    """

    if isinstance(node, ast.ClassDef):
        return ()

    args          = node.args
    list_position = [*args.posonlyargs, *args.args]
    list_default  = [None] * (len(list_position) - len(args.defaults)) + list(args.defaults)
    list_found    = [(arg, default, False)
                     for (arg, default) in zip(list_position, list_default, strict = True)]

    if is_method and list_found and list_found[0][0].arg in SET_RECEIVER:
        list_found = list_found[1:]

    list_found += [(args.vararg, None, True)] if args.vararg else []
    list_found += list(zip(args.kwonlyargs, args.kw_defaults,
                           [False] * len(args.kwonlyargs), strict = True))
    list_found += [(args.kwarg, None, True)] if args.kwarg else []

    return tuple((arg.arg, {'type':     _spelling(arg.annotation),
                            'default':  _spelling(default),
                            'optional': _truth(default is not None or is_variadic),
                            'variadic': _truth(is_variadic)})
                 for (arg, default, is_variadic) in list_found)


# -----------------------------------------------------------------------------
def _returns(node: ast.AST) -> str | None:
    """
    Return the type that the function node returns, as the code writes
    it, or empty if it does not say. Return None if node is a class.

    """

    if isinstance(node, ast.ClassDef):
        return None
    return _spelling(node.returns)


# -----------------------------------------------------------------------------
def _spelling(node: ast.AST | None) -> str:
    """
    Return node as the code writes it, or empty if there is none.

    """

    return '' if node is None else ast.unparse(node)


# -----------------------------------------------------------------------------
def _truth(value: bool) -> str:
    """
    Return value as true or false.

    """

    return 'true' if value else 'false'


# -----------------------------------------------------------------------------
def definition_id(relative: pathlib.Path, list_name: list[str], node: ast.AST) -> str:
    """
    Return the id of the item of the class or function node, named by
    list_name down from the top of the python module at relative: the
    prefix of its kind, the name of its module, and list_name, in lower
    case and separated by full stops.

    """

    (_, _, name) = module_name(relative).partition(DELIM_PREFIX)

    return MAP_PREFIX_KIND[type(node)] + DELIM_MODULE.join([name, *list_name]).lower()


# -----------------------------------------------------------------------------
def parse(text: str, relative: pathlib.Path) -> tuple[typing.Any, int]:
    """
    Return the YAML document that text holds, as the content of the file
    at relative, or None if it holds none, and the line of the file that
    its first line is on. Raise ErrorRead if it cannot be read.

    """

    if relative.suffix == SUFFIX_YAML:
        if DIR_DATA not in relative.parts:
            return (None, 1)
        return (_load(text, 1), 1)

    if relative.suffix == SUFFIX_PYTHON:
        return _docstring(text)

    return _header(iter(text.splitlines()), mark_comment(relative))


# -----------------------------------------------------------------------------
def _docstring(text: str) -> tuple[typing.Any, int]:
    """
    Return the YAML document in the module docstring of the python
    module text, or None if it holds none, and the line of the file that
    its first line is on.

    """

    return _document_of(_module(text)) or (None, 1)


# -----------------------------------------------------------------------------
def _module(text: str) -> ast.Module:
    """
    Return the syntax tree of the python module text. Raise ErrorRead
    if it is not python.

    """

    try:
        return ast.parse(text)
    except (SyntaxError, ValueError) as error:
        raise ErrorRead('The module is not python: {error}'.format(error = error),
                        getattr(error, 'lineno', None) or 1) from error


# -----------------------------------------------------------------------------
def _document_of(node: ast.AST) -> tuple[typing.Any, int] | None:
    """
    Return the YAML document in the docstring of node, a module, class
    or function, with the line of the file that its first line is on, or
    None if its docstring holds none.

    """

    docstring = ast.get_docstring(node)

    if not (docstring and docstring.startswith(LINE_OPEN)):
        return None

    # The docstring is cleaned of the blank lines that open it, and of
    # the indentation of a definition, so its first line is that many
    # lines below the opening quotes.
    #
    raw     = node.body[0].value.value
    leading = raw[:len(raw) - len(raw.lstrip())].count('\n')
    base    = node.body[0].lineno + leading

    return (_load(docstring, base), base)


# -----------------------------------------------------------------------------
def _load(text: str, base: int) -> typing.Any:
    """
    Return the YAML document text, whose first line is line base of
    its file. Raise ErrorRead if it is not YAML, or repeats a key.

    """

    try:
        return YAML.load(text)
    except ruamel.yaml.YAMLError as error:
        mark = getattr(error, 'problem_mark', None)
        raise ErrorRead('The document is not YAML: {error}'.format(error = error),
                        base + (mark.line if mark is not None else 0)) from error


# -----------------------------------------------------------------------------
def _line_of_file(path: pathlib.Path) -> typing.Iterator[str]:
    """
    Yield the lines of the file at path, and stop at the first that is
    not text.

    """

    try:
        with open(path, encoding = 'utf-8') as file:
            yield from file
    except UnicodeDecodeError:
        return


# -----------------------------------------------------------------------------
def mark_comment(relative: pathlib.Path) -> str:
    """
    Return the marker that begins a comment line in the file at
    relative.

    """

    return MAP_MARK_COMMENT.get(relative.suffix, MARK_COMMENT)


# -----------------------------------------------------------------------------
def is_lead(line: str) -> bool:
    """
    Return True if line may come before a comment header: a line that
    names an interpreter, or one that opens a comment block.

    """

    return line.startswith(MARK_SHEBANG) or line.rstrip() == LINE_BLOCK_OPEN


# -----------------------------------------------------------------------------
def _header(iter_line: typing.Iterator[str], mark: str) -> tuple[typing.Any, int]:
    """
    Return the YAML document in the comment header that the lines open
    with, each line beginning with mark, or None if they do not open
    with one, and the line of the file that its first line is on. A
    line that is_lead may come before the header.

    """

    list_line = []
    base      = 1

    for line in iter_line:
        text = line.rstrip('\n')
        if base == 1 and (not list_line) and is_lead(text):
            base = 2
            continue
        if not text.startswith(mark):
            return (None, 1)
        text = text[len(mark):].removeprefix(' ')
        if (not list_line) and text != LINE_OPEN:
            return (None, 1)
        list_line.append(text)
        if text == LINE_CLOSE:
            return (_load('\n'.join(list_line), base), base)

    return (None, 1)


# -----------------------------------------------------------------------------
def _walk(node:     typing.Any,
          holder:   str,
          location: tuple[str, int],
          facts:    Facts,
          terms:    Terms) -> None:
    """
    Add the facts held by node, whose nearest enclosing item is holder.
    location is the file that holds node, and the line of the file that
    the first line of its YAML document is on. terms are the terms that
    its text is searched for.

    """

    if isinstance(node, list):

        for (position, value) in enumerate(node):
            if isinstance(value, dict) and isinstance(value.get(KEY_ID_SELF), str):
                facts['position'].add((value[KEY_ID_SELF], str(position)))
            _walk(value, holder, location, facts, terms)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)

    if isinstance(id_self, str):

        facts['item'].add((id_self,
                           str(node.get(KEY_GUID_SELF, '')),
                           holder,
                           location[0],
                           _line(node, KEY_ID_SELF, location)))
        _signature(id_self, node, facts)
        _stated(id_self, node, facts)
        for alias in _list_str(node.get(KEY_ALIAS)):
            facts['alias'].add((id_self, alias))
        holder = id_self

    _reference(node, holder, location, facts)
    _text(node, holder, location, facts, terms)

    map_entry = node.get(KEY_ENTRIES)

    if isinstance(id_self, str) and isinstance(map_entry, dict):
        for (key, entry) in map_entry.items():
            if isinstance(entry, dict):
                facts['register_entry_key'].add((id_self,
                                                 str(key),
                                                 str(entry.get(KEY_ID_SELF))))

    for value in node.values():
        _walk(value, holder, location, facts, terms)


# -----------------------------------------------------------------------------
def _reference(node:     dict[str, typing.Any],
               holder:   str,
               location: tuple[str, int],
               facts:    Facts) -> None:
    """
    Add a fact for each reference that node makes, and for the edge
    that node is, if it is one.

    """

    for (key, value) in node.items():
        if key.startswith(PREFIX_ID) and key != KEY_ID_SELF and isinstance(value, str):
            field = key[len(PREFIX_ID):]
            guid  = str(node.get(PREFIX_GUID + field, ''))
            facts['reference'].add((holder, field, value, guid, location[0],
                                    _line(node, key, location)))

    if isinstance(node.get(KEY_ID_RELATION), str):
        facts['edge'].add((holder,
                           node[KEY_ID_RELATION],
                           str(node.get(KEY_ID_TARGET))))


# -----------------------------------------------------------------------------
def _text(node:     dict[str, typing.Any],
          holder:   str,
          location: tuple[str, int],
          facts:    Facts,
          terms:    Terms) -> None:
    """
    Add a fact for each id and each of terms that the text of a field
    of node mentions, for each schema that node refers to with a $ref,
    and for the $id that node gives. The fields that give terms are not
    searched for terms.

    """

    for (key, value) in node.items():
        if key == KEY_SCHEMA_URI and isinstance(value, str):
            facts['schema_uri'].add((holder, value, location[0], _line(node, key, location)))
        if key == KEY_REF and isinstance(value, str):
            for match in REGEX_REF.finditer(value):
                facts['schema_ref'].add((holder, match.group(1), location[0],
                                         _line(node, key, location)))
        if key in SET_KEY_UNNAMED or key.startswith((PREFIX_ID, PREFIX_GUID)):
            continue
        is_judged = key != KEY_BREAKS
        field     = (str(key), ({}, set()) if key in MAP_TERM_RATING else terms)
        if isinstance(value, str):
            _mention(value, holder, location[0], int(_line(node, key, location)), facts,
                     is_judged, field)
        elif isinstance(value, list):
            for (index, each) in enumerate(value):
                if isinstance(each, str):
                    _mention(each, holder, location[0],
                             int(_line_item(value, index, location)), facts, is_judged,
                             field)


# -----------------------------------------------------------------------------
def _mention(text:      str,
             holder:    str,
             file:      str,
             line:      int,
             facts:     Facts,
             is_judged: bool                        = True,
             field:     tuple[str, Terms]          = ('', ({}, set()))) -> None:
    """
    Add a fact for each id that text mentions, and, if is_judged, for
    each link to a concept, each word that a writing style rule asks to
    replace, and each term that field, the name of the field and the
    terms to search it for, uses outside a link, all outside double
    quotes. line is the line of the file that the field holding text is
    on. The text of a block scalar begins on the line below its key.

    """

    offset = 1 if isinstance(text, ruamel.yaml.scalarstring.LiteralScalarString) else 0

    for match in REGEX_MENTION.finditer(text):
        if (text.startswith(MARK_GLOB, match.end())
                or REGEX_CITED.search(text, max(0, match.start() - SIZE_CITED), match.start())):
            continue
        word = REGEX_SUFFIX.sub('', match.group(0))
        facts['mention'].add((holder, word, file,
                              str(line + offset + text.count('\n', 0, match.start()))))

    if is_judged:
        unquoted = REGEX_QUOTED.sub(lambda match: ' ' * len(match.group(0)), text)
        for match in REGEX_TERM_LINK.finditer(unquoted):
            (target, label) = (match.group(1).strip(), match.group(2))
            (term, concept) = (target, '') if label is None else (label.strip(), target)
            facts['term_link'].add((holder, term, concept, file,
                                    str(line + offset + text.count('\n', 0, match.start()))))
            if field[0] == KEY_DEFINITION and REGEX_GENUS.fullmatch(unquoted[:match.start()]):
                facts['genus_link'].add((holder, term, concept))

    if not is_judged:
        return

    unquoted = REGEX_QUOTED.sub(lambda match: ' ' * len(match.group(0)), text)
    plain    = unquoted
    for regex in (REGEX_TERM_LINK, REGEX_MENTION):
        plain = regex.sub(lambda match: ' ' * len(match.group(0)), plain)

    for (term, start) in _term_words(plain, field[1]):
        facts['term_word'].add((holder, field[0], term, file,
                                str(line + offset + text.count('\n', 0, start))))

    set_avoided = {row[1] for row in facts['word_replacement']}

    for match in REGEX_WORD.finditer(unquoted):
        word = match.group(0).lower()
        if word in set_avoided:
            facts['avoided_word'].add((holder, word, file,
                                       str(line + offset + text.count('\n', 0, match.start()))))


# -----------------------------------------------------------------------------
def _line_item(node: list[typing.Any], index: int, location: tuple[str, int]) -> str:
    """
    Return the line of the file that item index of node is on, or 0 if
    the loader did not record it.

    """

    lc = getattr(node, 'lc', None)

    if lc is None:
        return '0'

    return str(location[1] + lc.item(index)[0])


# -----------------------------------------------------------------------------
def _line(node: dict[str, typing.Any], key: str, location: tuple[str, int]) -> str:
    """
    Return the line of the file that key is on in node, or 0 if the
    loader did not record it.

    """

    lc = getattr(node, 'lc', None)

    if lc is None:
        return '0'

    return str(location[1] + lc.key(key)[0])


# -----------------------------------------------------------------------------
def _signature(id_self: str, node: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add the type and relation facts that an entry declares.

    """

    prefix   = node.get(KEY_PREFIX)
    regex_id = node.get(KEY_REGEX_ID)

    if isinstance(prefix, str) and isinstance(regex_id, str):
        facts['type_prefix'].add((id_self, prefix, regex_id))

    if node.get(KEY_ACYCLIC) is True:
        facts['acyclic_relation'].add((id_self,))

    for end in _list_str(node.get(KEY_READS_THROUGH)):
        facts['reads_through'].add((id_self, end))

    for key in (KEY_FAMILY, KEY_EXCEPTION, KEY_LABEL, KEY_ENFORCEMENT):
        if isinstance(node.get(key), str):
            facts[key].add((id_self, node[key].strip()))

    for (key, rating) in MAP_TERM_RATING.items():
        value     = node.get(key)
        list_term = [value] if isinstance(value, str) else _list_str(value)
        for term in list_term:
            facts['designation'].add((id_self, term, rating))

    inverse = node.get(KEY_INVERSE)

    if isinstance(inverse, dict) and isinstance(inverse.get(KEY_ID_SELF), str):
        facts['inverse_relation'].add((inverse[KEY_ID_SELF], id_self))


# -----------------------------------------------------------------------------
def _stated(id_self: str, node: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add a stated fact for each part of a signature that the item node
    states.

    """

    for (part, value) in (('type',     _type_spelling(node.get(KEY_TYPE))),
                          ('default',  node.get(KEY_DEFAULT)),
                          ('optional', node.get(KEY_OPTIONAL)),
                          ('variadic', node.get(KEY_VARIADIC))):
        if isinstance(value, bool):
            facts['stated'].add((id_self, part, _truth(value)))
        elif isinstance(value, str):
            facts['stated'].add((id_self, part, value))

    returns = node.get(KEY_RETURNS)

    if isinstance(returns, dict):
        spelling = _type_spelling(returns.get(KEY_TYPE))
        if spelling is not None:
            facts['stated'].add((id_self, 'returns', spelling))


# -----------------------------------------------------------------------------
def _ports(document: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add a fact for each port and setting of each dataflow step surface
    of document.

    """

    surface = document.get(KEY_SURFACE)

    if not isinstance(surface, dict):
        return

    interface = str(document.get(KEY_ID_SELF))

    for form in surface.values():
        step = form.get(KEY_DATAFLOW) if isinstance(form, dict) else None
        if not isinstance(step, dict):
            continue
        for kind in TUPLE_PORT_KIND:
            for (key, member) in _map(step.get(kind)).items():
                if isinstance(member, dict) and isinstance(member.get(KEY_ID_SELF), str):
                    facts['interface_port'].add((interface,
                                                 kind,
                                                 str(member.get(KEY_NAME, key)),
                                                 member[KEY_ID_SELF]))


# -----------------------------------------------------------------------------
def _commands(document: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add a fact for each command and each parameter that a command line
    surface of document states.

    """

    surface = document.get(KEY_SURFACE)

    if not isinstance(surface, dict):
        return

    for form in surface.values():
        line = form.get(KEY_COMMAND_LINE) if isinstance(form, dict) else None
        if isinstance(line, dict):
            _command_members(line, str(line.get(KEY_PROGRAM)), (), facts)


# -----------------------------------------------------------------------------
def _command_members(node:       dict[str, typing.Any],
                     program:    str,
                     tuple_name: tuple[str, ...],
                     facts:      Facts) -> None:
    """
    Add the facts of the parameters of node, a command line surface of
    program or a command whose words after the program name are
    tuple_name, and of each command it holds. A parameter of a command
    also states its kind, whether it is a flag, and, for an argument,
    its position among the arguments.

    """

    command        = cctool.graph.tool.DELIM_COMMAND.join(tuple_name)
    list_parameter = node.get(KEY_PARAMETER)
    position       = 0

    for parameter in list_parameter if isinstance(list_parameter, list) else []:
        if not isinstance(parameter, dict) or not isinstance(parameter.get(KEY_ID_SELF), str):
            continue
        id_self = parameter[KEY_ID_SELF]
        kind    = parameter.get(KEY_KIND)
        facts['command_member'].add((id_self, program, command,
                                     str(parameter.get(KEY_NAME, ''))))
        if isinstance(kind, str):
            facts['stated'].add((id_self, 'kind', kind))
        if isinstance(parameter.get(KEY_FLAG), bool):
            facts['stated'].add((id_self, 'flag', _truth(parameter[KEY_FLAG])))
        if kind == cctool.graph.tool.KIND_ARGUMENT:
            facts['stated'].add((id_self, 'position', str(position)))
            position += 1

    for (key, each) in _map(node.get(KEY_COMMAND)).items():
        if not isinstance(each, dict) or not isinstance(each.get(KEY_ID_SELF), str):
            continue
        tuple_each = (*tuple_name, str(each.get(KEY_NAME, key)))
        facts['command_member'].add((each[KEY_ID_SELF], program,
                                     cctool.graph.tool.DELIM_COMMAND.join(tuple_each), ''))
        _command_members(each, program, tuple_each, facts)


# -----------------------------------------------------------------------------
def _checks(document: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add a fact for each check that document, if it is an interface
    control document, states.

    """

    if not isinstance(document.get(KEY_SURFACE), dict):
        return

    interface = str(document.get(KEY_ID_SELF))

    for (key, member) in _map(document.get(KEY_CHECK)).items():
        if isinstance(member, dict) and isinstance(member.get(KEY_ID_SELF), str):
            facts['check_member'].add((member[KEY_ID_SELF],
                                       interface,
                                       str(member.get(KEY_NAME, key)),
                                       str(member.get(KEY_SEVERITY, ''))))


# -----------------------------------------------------------------------------
def _dataflow_graph(document: dict[str, typing.Any],
                    location: tuple[str, int],
                    facts:    Facts) -> None:
    """
    Add the facts of the dataflow nodes, dataflow edges, OS processes
    and hosts of document, if it is a dataflow graph: a YAML document
    whose dataflow_node field maps each key to an item.

    """

    map_node = _map(document.get(KEY_NODE))

    if not map_node or not all(isinstance(node, dict) and KEY_ID_SELF in node
                               for node in map_node.values()):
        return

    graph  = str(document.get(KEY_ID_SELF))

    for (key, node) in map_node.items():
        id_node = str(node[KEY_ID_SELF])
        os_process = str(node.get(KEY_OS_PROCESS, ''))
        facts['dataflow_node'].add((graph, str(key), id_node, os_process))
        for name in _map(node.get(KEY_SETTINGS)):
            facts['dataflow_setting'].add((id_node, str(name)))

    for (key, os_process) in _map(document.get(KEY_OS_PROCESS)).items():
        host = os_process.get(KEY_HOST, '') if isinstance(os_process, dict) else ''
        facts['os_process'].add((graph, str(key), str(host)))

    for key in _map(document.get(KEY_HOST)):
        facts['host'].add((graph, str(key)))

    list_edge = document.get(KEY_EDGE)

    if not isinstance(list_edge, list):
        return

    for (index, edge) in enumerate(list_edge):
        if not isinstance(edge, dict):
            continue
        source = _map(edge.get(KEY_SOURCE))
        target = _map(edge.get(KEY_TARGET))
        facts['dataflow_edge'].add((graph,
                                  str(source.get(KEY_ID_NODE, '')),
                                  str(source.get(KEY_ID_PORT, '')),
                                  str(target.get(KEY_ID_NODE, '')),
                                  str(target.get(KEY_ID_PORT, '')),
                                  str(edge.get(KEY_DIRECTION, FEEDFORWARD)),
                                  location[0],
                                  _line_item(list_edge, index, location)))


# -----------------------------------------------------------------------------
def _map(value: typing.Any) -> dict[typing.Any, typing.Any]:
    """
    Return value if it is a mapping, and an empty mapping if not.

    """

    if isinstance(value, dict):
        return value
    return {}


# -----------------------------------------------------------------------------
def _type_spelling(value: typing.Any) -> str | None:
    """
    Return the spelling of the type reference value, or None if it
    gives none.

    """

    if isinstance(value, dict) and isinstance(value.get(KEY_SPELLING), str):
        return value[KEY_SPELLING]
    return None


# -----------------------------------------------------------------------------
def _list_str(value: typing.Any) -> list[str]:
    """
    Return value if it is a list of strings, and an empty list if not.

    """

    if isinstance(value, list) and all(isinstance(each, str) for each in value):
        return value
    return []
