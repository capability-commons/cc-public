"""
---

id_self:                pym_cctool.graph.tool
guid_self:              pym_39248cc11995417689ace6fa4a332506
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Facts of the tool
brief:                  |
                        Give the facts of cctool itself that no
                        document of a tree holds: its command line, as
                        click describes it, and the severity of each
                        of its checks.
description:            |
                        A command line surface states the commands of
                        a program, and icd_cctool_check the severity
                        of each check. These facts are what the tool
                        does as it runs, so that a check can hold the
                        one to the other. The command line is read
                        from click's own description of each command,
                        Command.to_info_dict, and not by parsing the
                        source, and the severities from
                        cctool.check.check. Each module is imported
                        when the facts are first asked for, since each
                        imports this module in turn. The facts of the
                        command line are kept for the life of the OS
                        process, and the severities are read each
                        time.
edge:                   []

...
"""


import functools
import importlib

import click


# The program, the module whose main is its click group, and the module
# that runs its checks. Each module is imported when the facts are first
# asked for, and not before, since each imports the module that asks.
#
NAME_PROGRAM      = 'cctool'
NAME_COMMAND      = 'cctool.cli.command'
NAME_CHECK        = 'cctool.check.check'

# What joins the names of a command and of the groups it is under, and
# the kind of a parameter given by its place.
#
DELIM_COMMAND     = ' '
KIND_ARGUMENT     = 'argument'


# -----------------------------------------------------------------------------
def facts() -> dict[str, frozenset[tuple[str, ...]]]:
    """
    Return the facts of cctool itself, keyed by predicate: the commands
    and parameters of its command line, read from click's own
    description of them, and the severity of each of its checks. The
    severities are read afresh each time, since the logic programs
    that set them are files that may change while the OS process runs.

    """

    return {**_command_line(),
            'check_severity': frozenset(importlib.import_module(NAME_CHECK)
                                                  .severities().items())}


# -----------------------------------------------------------------------------
@functools.cache
def _command_line() -> dict[str, frozenset[tuple[str, ...]]]:
    """
    Return the facts of the command line of cctool, keyed by predicate,
    read once in each OS process.

    """

    group   = importlib.import_module(NAME_COMMAND).main
    context = click.Context(group, info_name = NAME_PROGRAM)
    found   = {'click_command':   set(),
               'click_parameter': set()}

    _command(group.to_info_dict(context), (), set(context.help_option_names), found)

    return {name: frozenset(set_row) for (name, set_row) in found.items()}


# -----------------------------------------------------------------------------
def _command(info:       dict,
             tuple_name: tuple[str, ...],
             set_help:   set[str],
             found:      dict[str, set[tuple[str, ...]]]) -> None:
    """
    Add the facts of the command that info describes, whose names under
    the program are tuple_name, and of each command under it. An option
    spelled only by a name of set_help is click's own, and is left out.

    """

    command  = DELIM_COMMAND.join(tuple_name)
    position = 0

    found['click_command'].add((NAME_PROGRAM, command))

    for param in info['params']:
        if set(param['opts']) <= set_help:
            continue
        is_argument = param['param_type_name'] == KIND_ARGUMENT
        name        = param['name'] if is_argument else param['opts'][0]
        map_part    = {'kind':     param['param_type_name'],
                       'type':     param['type']['name'],
                       'default':  _text(param['default']),
                       'optional': _truth(not param['required']),
                       'variadic': _truth(param['multiple'] or param['nargs'] == -1),
                       'flag':     _truth(bool(param.get('is_flag')))}
        if is_argument:
            map_part['position'] = str(position)
            position            += 1
        for (part, value) in map_part.items():
            found['click_parameter'].add((NAME_PROGRAM, command, name, part, value))

    for (name, each) in info.get('commands', {}).items():
        _command(each, (*tuple_name, name), set_help, found)


# -----------------------------------------------------------------------------
def _text(value: object) -> str:
    """
    Return value as a command line default is written: empty if there is
    none, and true or false for a truth value.

    """

    if value is None:
        return ''
    if isinstance(value, bool):
        return _truth(value)
    return str(value)


# -----------------------------------------------------------------------------
def _truth(value: bool) -> str:
    """
    Return value as true or false.

    """

    return 'true' if value else 'false'
