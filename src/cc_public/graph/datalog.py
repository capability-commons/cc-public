"""
---

id_self:                pym_cc_public.graph.datalog
guid_self:              pym_c1c7e94e143148229f358c139ee034de
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Datalog evaluation
brief:                  |
                        Evaluate Datalog rules over the facts of the
                        graph of data items, with souffle.
description:            |
                        This module writes the facts as souffle input,
                        and evaluates a program made of three parts:
                        the declarations of the base relations, the
                        derived relations of derive.dl, and the rules
                        given. It returns the rows of every output
                        relation of the rules given, in the order they
                        are named.
usage:                  |
                        The souffle executable is taken from the
                        SOUFFLE environment variable, or from the
                        PATH.
relation:               []

...
"""


import os
import pathlib
import re
import subprocess
import tempfile

import cc_public.graph.extract


PATH_DERIVE       = pathlib.Path(__file__).with_name('derive.dl')
DELIM_FIELD       = '\t'

# A declaration names a relation and its columns, as name:type pairs.
# An output directive names one or more relations to be written out.
#
REGEX_DECL        = re.compile(r'\.decl\s+(\w+)\s*\(([^)]*)\)')
REGEX_OUTPUT      = re.compile(r'\.output\s+(\w+(?:\s*,\s*\w+)*)')

# A comment takes a whole line, so that text in a comment, such as the
# header of a module, is never read as a directive.
#
REGEX_COMMENT     = re.compile(r'^\s*//.*$', re.MULTILINE)

Rows              = dict[str, list[tuple[str, ...]]]


# -----------------------------------------------------------------------------
class ErrorDatalog(Exception):
    """
    The rules given could not be evaluated. The message is souffle's.

    """


# -----------------------------------------------------------------------------
def declaration() -> str:
    """
    Return the declarations of the base relations, each as input.

    """

    list_line = []

    for (name, (tuple_column, _)) in cc_public.graph.extract.RELATION.items():
        list_line.append('.decl {name}({column})'.format(
                            name   = name,
                            column = ', '.join('{c}:{t}'.format(c = column, t = type_column)
                                              for (column, type_column)
                                              in map(cc_public.graph.extract.column,
                                                     tuple_column))))
        list_line.append('.input {name}'.format(name = name))

    return '\n'.join(list_line) + '\n'


# -----------------------------------------------------------------------------
def declared(text: str) -> dict[str, tuple[tuple[str, str], ...]]:
    """
    Return the name and the type of each column of each relation that
    text declares, keyed by relation.

    """

    map_column = {}

    for match in REGEX_DECL.finditer(REGEX_COMMENT.sub('', text)):
        map_column[match.group(1)] = tuple(cc_public.graph.extract.column(spec)
                                           for spec in match.group(2).split(',')
                                           if spec.strip())

    return map_column


# -----------------------------------------------------------------------------
def output(text: str) -> list[str]:
    """
    Return the relations that text names in output directives, in the
    order it first names them.

    """

    list_name = []

    for match in REGEX_OUTPUT.finditer(REGEX_COMMENT.sub('', text)):
        list_name.extend(name.strip() for name in match.group(1).split(','))

    return list(dict.fromkeys(list_name))


# -----------------------------------------------------------------------------
def derived() -> dict[str, tuple[tuple[str, str], ...]]:
    """
    Return the name and the type of each column of each derived
    relation, keyed by relation.

    """

    return declared(PATH_DERIVE.read_text(encoding = 'utf-8'))


# -----------------------------------------------------------------------------
def write(facts: cc_public.graph.extract.Facts, dir_fact: pathlib.Path) -> None:
    """
    Write each base relation as a tab separated souffle .facts file.

    """

    for (name, set_row) in facts.items():
        path = dir_fact / '{name}.facts'.format(name = name)
        with open(path, 'w', encoding = 'utf-8') as file:
            for row in sorted(set_row):
                if any((DELIM_FIELD in field) or ('\n' in field) for field in row):
                    raise ValueError('{name}: {row!r}'.format(name = name, row = row))
                file.write(DELIM_FIELD.join(row) + '\n')


# -----------------------------------------------------------------------------
def run(facts: cc_public.graph.extract.Facts, rules: str) -> Rows:
    """
    Return the rows of each output relation of rules, evaluated over
    facts, keyed by relation in the order rules names them.

    """

    souffle = os.environ.get('SOUFFLE', 'souffle')
    rows    = {}

    with tempfile.TemporaryDirectory() as dir_temp:

        dir_fact     = pathlib.Path(dir_temp, 'fact')
        dir_out      = pathlib.Path(dir_temp, 'out')
        path_program = pathlib.Path(dir_temp, 'program.dl')
        dir_fact.mkdir()
        dir_out.mkdir()

        write(facts, dir_fact)
        prelude = declaration() + '\n' + PATH_DERIVE.read_text(encoding = 'utf-8') + '\n'
        path_program.write_text(prelude + rules, encoding = 'utf-8')

        try:
            result = subprocess.run([souffle, '-F', str(dir_fact), '-D', str(dir_out),
                                     str(path_program)],
                                    capture_output = True,
                                    text           = True,
                                    check          = False)
        except FileNotFoundError as error:
            raise ErrorDatalog('souffle cannot be found at {souffle!r}. Put it on the '
                               'PATH, or name it in the SOUFFLE environment '
                               'variable.'.format(souffle = souffle)) from error
        if result.returncode != 0:
            raise ErrorDatalog('{error}\nThe rules given begin at line {line} of {path}.'.format(
                                    error = (result.stderr or result.stdout).strip(),
                                    line  = prelude.count('\n') + 1,
                                    path  = path_program.name))

        for name in output(rules):
            path = dir_out / '{name}.csv'.format(name = name)
            text = path.read_text(encoding = 'utf-8') if path.exists() else ''
            rows[name] = sorted(tuple(line.split(DELIM_FIELD))
                                for line in text.splitlines())

    return rows
