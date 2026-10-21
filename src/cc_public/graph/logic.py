"""
---

id_self:                pym_cc_public.graph.logic
guid_self:              pym_c1c7e94e143148229f358c139ee034de
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Logic program evaluation
brief:                  |
                        Evaluate logic program rules over the facts of
                        the graph of data items, with clingo.
description:            |
                        The rules are a clingo program. This module
                        adds the facts and a program made of two
                        parts, the derived relations of derive.lp and
                        the rules given, to one clingo control, in the
                        same process. It returns the rows of every
                        relation the rules given name in a #show
                        directive, in the order they are named.

                        Any message clingo gives is an error, a
                        warning included, and the program must have
                        exactly one answer set. So a misspelt relation
                        or a violated constraint is reported, and
                        never reads as an empty result.

                        clingo has no declarations of its own, so a
                        relation is declared in a comment, such as "%
                        decl item(id: symbol, line: number)". The
                        declaration gives the names of the columns,
                        and marks those that are numbers. A relation
                        shown without one has no column names, and one
                        shown with one has as many columns as it
                        declares. The base relations are declared by
                        RELATION in pym_cc_public.graph.extract.

                        clingo has no string functions of its own, so
                        five are given in python and called with @:
                        @match(regex, text) is 1 if regex matches the
                        whole of text and 0 if not; @cat(a, b, ...)
                        joins its arguments; @strlen(text) is the
                        length of text; @substr(text, start, length)
                        is the part of text that begins at start,
                        counted from 0; and @prefix(text) is what
                        comes before its first underscore. Each call
                        goes back to python, so a rule that calls one
                        for every pair of two relations is slow:
                        @prefix finds the prefix of an id once, where
                        @match would try it against every type.
edge:                   []

...
"""


import functools
import pathlib
import re

import clingo

import cc_public.graph.extract


PATH_DERIVE       = pathlib.Path(__file__).with_name('derive.lp')
TYPE_NUMBER       = 'number'

# A declaration is a comment that names a relation and its columns.
# It may go on over more comment lines, one column on each. A show
# directive names one relation and its arity.
#
REGEX_DECL        = re.compile(r'^[ \t]*%[ \t]*decl[ \t]+(\w+)[ \t]*\(((?:[^)\n]|\n[ \t]*%)*)\)',
                               re.MULTILINE)
REGEX_SHOW        = re.compile(r'#show[ \t]+(\w+)[ \t]*/[ \t]*(\d+)[ \t]*\.')

# The wording of a shown relation is two comments after its
# declaration: "% did", a sentence that says what a row of it records,
# with each column named in braces, and "% fix", what to do about it.
# Each may go on over more comment lines, indented.
#
REGEX_WORDING     = re.compile(r'^[ \t]*%[ \t]*(did|fix)[ \t]+(.*(?:\n[ \t]*%[ \t]{2,}\S.*)*)',
                               re.MULTILINE)

# Text in a comment is never read as a directive. A comment runs from
# % to the end of the line, or from %* to *%.
#
REGEX_COMMENT     = re.compile(r'%\*.*?\*%|%[^\n]*', re.DOTALL)

# Each string is written between double quotes, with a backslash
# before a backslash or a double quote, and a newline as \n.
#
MAP_ESCAPE        = str.maketrans({'\\': '\\\\', '"': '\\"', '\n': '\\n'})

Rows              = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
class ErrorLogic(Exception):
    """
    The rules given could not be evaluated. The message is clingo's,
    or says what is missing.

    """


# -----------------------------------------------------------------------------
class Context:
    """
    The functions that rules call with @.

    """

    # -------------------------------------------------------------------------
    def match(self, regex: clingo.Symbol, text: clingo.Symbol) -> clingo.Symbol:
        """
        Return 1 if regex matches the whole of text, and 0 if not.

        """

        try:
            is_match = _compiled(regex.string).fullmatch(text.string) is not None
        except re.error as error:
            raise ErrorLogic('Bad regex {regex!r}: {error}'.format(
                                  regex = regex.string, error = error)) from error
        return clingo.Number(int(is_match))

    # -------------------------------------------------------------------------
    def prefix(self, text: clingo.Symbol) -> clingo.Symbol:
        """
        Return what comes before the first underscore of text, or all of
        text if it has none.

        """

        return clingo.String(text.string.partition('_')[0])

    # -------------------------------------------------------------------------
    def cat(self, *args: clingo.Symbol) -> clingo.Symbol:
        """
        Return the strings joined.

        """

        return clingo.String(''.join(each.string for each in args))

    # -------------------------------------------------------------------------
    def strlen(self, text: clingo.Symbol) -> clingo.Symbol:
        """
        Return the length of text.

        """

        return clingo.Number(len(text.string))

    # -------------------------------------------------------------------------
    def substr(self,
               text:   clingo.Symbol,
               start:  clingo.Symbol,
               length: clingo.Symbol) -> clingo.Symbol:
        """
        Return the part of text that begins at start and has length
        characters.

        """

        return clingo.String(text.string[start.number:start.number + length.number])


# -----------------------------------------------------------------------------
@functools.lru_cache(maxsize = 1024)
def _compiled(regex: str) -> re.Pattern:
    """
    Return regex, compiled.

    """

    return re.compile(regex)


# -----------------------------------------------------------------------------
def declared(text: str) -> dict[str, tuple[tuple[str, str], ...]]:
    """
    Return the name and the type of each column of each relation that
    text declares, keyed by relation.

    """

    map_column = {}

    for match in REGEX_DECL.finditer(text):
        map_column[match.group(1)] = tuple(cc_public.graph.extract.column(spec)
                                           for spec in match.group(2).replace('%', '').split(',')
                                           if spec.strip())

    return map_column


# -----------------------------------------------------------------------------
def worded(text: str) -> dict[str, dict[str, str]]:
    """
    Return the did and the fix of each relation that text declares
    with them, keyed by relation. The wording of a declaration runs to
    the next declaration.

    """

    map_wording = {}
    list_match  = list(REGEX_DECL.finditer(text))

    for (index, match) in enumerate(list_match):
        end     = list_match[index + 1].start() if index + 1 < len(list_match) else len(text)
        map_key = {each.group(1): ' '.join(each.group(2).replace('%', ' ').split())
                   for each in REGEX_WORDING.finditer(text, match.end(), end)}
        if map_key:
            map_wording[match.group(1)] = map_key

    return map_wording


# -----------------------------------------------------------------------------
def described(rows:        Rows,
              map_column:  dict[str, tuple[str, ...]],
              map_wording: dict[str, dict[str, str]],
              prefix:      str = '') -> list[str]:
    """
    Return a line for each row of rows, and then the fix of its
    relation once. A row reads as the did of its relation with the
    columns filled in, after its file and line where it has them, and
    after the name of the relation, which callers and tests can match
    on. A relation with no wording gives its row as it is.

    """

    list_line = []

    for (name, list_row) in rows.items():
        wording = map_wording.get(name, {})
        for row in list_row:
            map_value = (dict(zip(map_column[name], row, strict = True))
                         if name in map_column else {})
            list_part = [map_value[key] for key in ('file', 'line') if map_value.get(key)]
            place     = ':'.join(list_part) + ': ' if list_part else ''
            text      = (wording['did'].format(**map_value)
                         if 'did' in wording else '  '.join(row))
            list_line.append('{prefix}{place}{name}: {text}'.format(prefix = prefix,
                                                                     place  = place,
                                                                     name   = name,
                                                                     text   = text))
        if list_row and 'fix' in wording:
            list_line.append('{prefix}  fix: {fix}'.format(prefix = prefix, fix = wording['fix']))

    return list_line


# -----------------------------------------------------------------------------
def output(text: str) -> list[str]:
    """
    Return the relations that text names in show directives, in the
    order it first names them.

    """

    return list(dict.fromkeys(match.group(1)
                              for match in REGEX_SHOW.finditer(REGEX_COMMENT.sub('', text))))


# -----------------------------------------------------------------------------
def show(name: str, map_column: dict[str, tuple[tuple[str, str], ...]]) -> str:
    """
    Return the directive that shows the relation name, whose columns
    map_column declares.

    """

    return '#show {name}/{arity}.\n'.format(name = name, arity = len(map_column[name]))


# -----------------------------------------------------------------------------
def derived() -> dict[str, tuple[tuple[str, str], ...]]:
    """
    Return the name and the type of each column of each derived
    relation, keyed by relation.

    """

    return declared(PATH_DERIVE.read_text(encoding = 'utf-8'))


# -----------------------------------------------------------------------------
def base() -> dict[str, tuple[tuple[str, str], ...]]:
    """
    Return the name and the type of each column of each base relation,
    keyed by relation.

    """

    return {name: tuple(map(cc_public.graph.extract.column, tuple_column))
            for (name, (tuple_column, _)) in cc_public.graph.extract.RELATION.items()}


# -----------------------------------------------------------------------------
def write(facts:      cc_public.graph.extract.Facts,
          map_column: dict[str, tuple[tuple[str, str], ...]]) -> str:
    """
    Return the facts as a clingo program. A column declared a number
    is written as one, and any other as a string.

    """

    list_line = []

    for (name, set_row) in facts.items():
        tuple_type = tuple(type_column for (_, type_column) in map_column.get(name, ()))
        for row in sorted(set_row):
            list_line.append('{name}({args}).'.format(
                                name = name,
                                args = ', '.join(_term(field, tuple_type, index)
                                                 for (index, field) in enumerate(row))))

    return '\n'.join(list_line) + '\n'


# -----------------------------------------------------------------------------
def _term(field: str, tuple_type: tuple[str, ...], index: int) -> str:
    """
    Return the field at index of a row as a clingo term.

    """

    if index < len(tuple_type) and tuple_type[index] == TYPE_NUMBER:
        return str(int(field))
    return '"{text}"'.format(text = str(field).translate(MAP_ESCAPE))


# -----------------------------------------------------------------------------
def _field(symbol: clingo.Symbol) -> str:
    """
    Return the argument of a shown atom as text.

    """

    if symbol.type == clingo.SymbolType.String:
        return symbol.string
    if symbol.type == clingo.SymbolType.Number:
        return str(symbol.number)
    return str(symbol)


# -----------------------------------------------------------------------------
def run(facts:      cc_public.graph.extract.Facts,
        rules:      str,
        map_extra:  dict[str, tuple[tuple[str, str], ...]] | None = None) -> Rows:
    """
    Return the rows of each output relation of rules, evaluated over
    facts, keyed by relation in the order rules names them. map_extra
    declares the columns of any relation of facts that is neither a
    base relation nor derived, such as text_hit.

    """

    prelude    = PATH_DERIVE.read_text(encoding = 'utf-8') + '\n'
    map_column = base() | derived() | (map_extra or {}) | declared(rules)
    list_name  = output(rules)
    rows       = {name: [] for name in list_name}

    for (name, arity) in ((match.group(1), int(match.group(2)))
                          for match in REGEX_SHOW.finditer(REGEX_COMMENT.sub('', rules))):
        if (name in map_column) and (arity != len(map_column[name])):
            raise ErrorLogic('{name} is shown with arity {arity}, but declared with '
                             '{count} columns.'.format(name  = name,
                                                       arity = arity,
                                                       count = len(map_column[name])))

    # Every message clingo gives is an error, a warning included: an
    # atom that occurs in no rule head is most often a misspelt
    # relation, and would otherwise make its rule silently never fire.
    # An input relation may be empty, so each is declared defined.
    #
    list_message = []
    control      = clingo.Control(['--models=2'],
                                  logger = lambda _, message: list_message.append(message))
    line         = prelude.count('\n') + 1

    try:
        control.add('base', [], defined(facts, map_column) + write(facts, map_column))
        control.add('base', [], prelude + rules)
        control.ground([('base', [])], context = Context())
    except RuntimeError as error:
        raise ErrorLogic(_message(''.join(list_message) or str(error), line)) from error

    if list_message:
        raise ErrorLogic(_message(''.join(list_message), line))

    # A stratified program has exactly one model, so clingo is asked
    # for two to show that there is no second. None means that a
    # constraint is violated, and more than one that the rules choose:
    # either way, no rows can be trusted, and an empty result must not
    # read as no failures.
    #
    count = 0

    with control.solve(yield_ = True) as handle:
        for model in handle:
            count += 1
            if count > 1:
                raise ErrorLogic('The rules have more than one answer set, so their '
                                 'rows are not determined. Remove any choice rule.')
            for symbol in model.symbols(shown = True):
                if symbol.name in rows:
                    rows[symbol.name].append(tuple(map(_field, symbol.arguments)))

    if count == 0:
        raise ErrorLogic('The rules have no answer set, so they give no rows. A '
                         'constraint (a rule with no head) holds, or the program '
                         'contradicts itself.')

    return {name: sorted(list_row) for (name, list_row) in rows.items()}


# -----------------------------------------------------------------------------
def defined(facts:      cc_public.graph.extract.Facts,
            map_column: dict[str, tuple[tuple[str, str], ...]]) -> str:
    """
    Return a directive that declares each input relation of facts
    defined, so that one with no rows is not taken for a misspelling.

    """

    return ''.join('#defined {name}/{arity}.\n'.format(name = name, arity = len(map_column[name]))
                   for name in sorted(set(facts) | set(base()))
                   if name in map_column)


# -----------------------------------------------------------------------------
def _message(text: str, line: int) -> str:
    """
    Return clingo's message text, with the line the rules begin on.

    """

    return '{text}\nThe rules given begin at line {line} of the program.'.format(
               text = text.strip(),
               line = line)
