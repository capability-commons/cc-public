"""
---

id_self:                pym_cc_public.cli._test.test_guidance
guid_self:              pym_6b95ee67b87741e2a55ed74686c46244
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Agent guidance tests
brief:                  |
                        Tests that the agent guides name only
                        commands, tasks, items, checks, fields and
                        paths that the code has.
description:            |
                        AGENTS.md and the skills are read by agents
                        that act on them without checking. A command,
                        id or path they name that no longer exists
                        sends an agent the wrong way, so each test
                        reads the code spans of the guides and fails
                        on any name the code does not have.
edge:                   []

...
"""


import importlib.util
import pathlib
import re
import tomllib

import click
import pytest

import cc_public.check.check
import cc_public.cli.command
import cc_public.commit.change
import cc_public.conftest
import cc_public.graph.logic
import cc_public.graph.extract


DIR_REPO          = cc_public.conftest.DIR_REPO
TUPLE_GUIDE       = ('AGENTS.md', '.agents/skills/*/SKILL.md')

# Code is what a guide writes between backticks, inline or fenced. Only
# code is checked, so prose may say "cctool prints" freely.
#
REGEX_FENCE       = re.compile(r'```[^\n]*\n(.*?)```', re.DOTALL)
REGEX_SPAN        = re.compile(r'`([^`\n]+)`')

# A word with two capitals in a row stands for what the reader
# supplies, such as ID, PATH or TOPIC, and is not checked.
#
REGEX_PLACEHOLDER = re.compile(r'[A-Z]{2}')

REGEX_NAME        = re.compile(r'[a-z][a-z0-9]*(?:_[a-z0-9]+)+')
REGEX_DOTTED      = re.compile(r'[a-z_]+(?:\.[a-z0-9_]+)+')
REGEX_PATH        = re.compile(r'[\w.*-]*/[\w./*-]*|[\w-]+\.(?:yaml|md|py|lp|toml)')
STRIP             = '\'"`()[]'
STRIP_END         = '.,;:'
TUPLE_SEPARATOR   = ('|', ';', '&&', '||')
MESSAGE_FIX       = ('Correct the guide, or write the part the reader supplies in capitals, '
                     'such as ID or PATH.')


# -----------------------------------------------------------------------------
def _guides() -> list[pathlib.Path]:
    """
    Return the path of each guide for agents.

    """

    return sorted(path for pattern in TUPLE_GUIDE for path in DIR_REPO.glob(pattern))


# -----------------------------------------------------------------------------
def _code() -> list[tuple[str, str]]:
    """
    Return each piece of code in the guides, with the guide it is in.

    """

    list_code = []

    for path in _guides():
        text      = path.read_text(encoding = 'utf-8')
        relative  = path.relative_to(DIR_REPO).as_posix()
        list_code += [(relative, code) for code in REGEX_FENCE.findall(text)]
        list_code += [(relative, code) for code in REGEX_SPAN.findall(REGEX_FENCE.sub('', text))]

    return list_code


# -----------------------------------------------------------------------------
def _words() -> list[tuple[str, str]]:
    """
    Return each word of code in the guides, without the quotes and
    punctuation around it, with the guide it is in. Placeholders are
    left out.

    """

    return [(guide, word.strip(STRIP).rstrip(STRIP_END))
            for (guide, code) in _code()
            for word in code.split()
            if word.strip(STRIP).rstrip(STRIP_END) and not REGEX_PLACEHOLDER.search(word)]


# -----------------------------------------------------------------------------
def _commands(prefix: str) -> list[tuple[str, list[str]]]:
    """
    Return the words that follow each use of prefix in the code of the
    guides, up to the end of its line or command, with the guide it is
    in.

    """

    list_command = []

    for (guide, code) in _code():
        for line in code.splitlines():
            for part in line.split(prefix + ' ')[1:] + ([''] if line.strip() == prefix else []):
                list_word = []
                for word in part.split():
                    if word in TUPLE_SEPARATOR:
                        break
                    list_word.append(word.strip(STRIP).rstrip(STRIP_END))
                list_command.append((guide, list_word))

    return list_command


# -----------------------------------------------------------------------------
@pytest.fixture(scope = 'module')
def facts():
    """
    The facts of the repository's own data items.

    """

    return cc_public.graph.extract.extract(DIR_REPO)


# -----------------------------------------------------------------------------
def test_every_cctool_command_in_the_guides_exists():
    list_wrong = []

    for (guide, list_word) in _commands('cctool'):
        command = cc_public.cli.command.main
        index   = 0
        while (isinstance(command, click.Group) and index < len(list_word)
               and list_word[index] in command.commands):
            command = command.commands[list_word[index]]
            index  += 1
        if index == 0 and list_word and not list_word[0].startswith('-'):
            list_wrong.append('{guide}: cctool has no command {word}.'.format(
                                  guide = guide, word = list_word[0]))
            continue
        set_option = {option for param in command.params for option in param.opts} | {'--help'}
        list_wrong += ['{guide}: cctool {name} has no option {option}.'.format(
                           guide = guide, name = command.name, option = word)
                       for word in list_word[index:]
                       if word.startswith('--') and word not in set_option]

    assert not list_wrong, '\n'.join([*list_wrong, MESSAGE_FIX])

# -----------------------------------------------------------------------------
def test_every_pixi_task_in_the_guides_exists():
    text     = (DIR_REPO / 'pyproject.toml').read_text(encoding = 'utf-8')
    set_task = set(tomllib.loads(text)['tool']['pixi']['tasks'])

    list_wrong = ['{guide}: pixi has no task {task}.'.format(guide = guide, task = list_word[1])
                  for (guide, list_word) in _commands('pixi')
                  if list_word[:1] == ['run'] and len(list_word) > 1
                  and list_word[1] not in set_task]

    assert not list_wrong, '\n'.join([*list_wrong, MESSAGE_FIX])

# -----------------------------------------------------------------------------
def test_every_id_in_the_guides_names_an_item(facts):
    set_prefix = {prefix for (_, prefix, _) in facts['type_prefix']}
    set_id     = ({row[0] for row in facts['item']}
                  | {alias for (_, alias) in facts['alias']}
                  | _known())

    list_wrong = ['{guide}: no item has the id {word}.'.format(guide = guide, word = word)
                  for (guide, word) in _words()
                  if REGEX_NAME.fullmatch(word)
                  and word.split('_')[0] in set_prefix
                  and word not in set_id]

    assert not list_wrong, '\n'.join([*list_wrong, MESSAGE_FIX])

# -----------------------------------------------------------------------------
def test_every_other_name_in_the_guides_is_a_check_relation_or_field(facts):
    set_prefix = {prefix for (_, prefix, _) in facts['type_prefix']}
    set_known  = _known() | _fields(cc_public.graph.extract.documents(DIR_REPO))

    list_wrong = []

    for (guide, word) in _words():
        if REGEX_PATH.fullmatch(word) or word.startswith('-'):
            continue
        if REGEX_DOTTED.fullmatch(word) and word.startswith('cc_public.'):
            if importlib.util.find_spec(word) is None:
                list_wrong.append('{guide}: there is no module {word}.'.format(
                                      guide = guide, word = word))
            continue
        for part in word.split('.'):
            if (REGEX_NAME.fullmatch(part) and part.split('_')[0] not in set_prefix
                    and part not in set_known):
                list_wrong.append('{guide}: {part} is no check, predicate or field.'.format(
                                      guide = guide, part = part))

    assert not list_wrong, '\n'.join([*list_wrong, MESSAGE_FIX])

# -----------------------------------------------------------------------------
def test_every_path_in_the_guides_exists():
    list_wrong = []

    for (guide, word) in _words():
        if not REGEX_PATH.fullmatch(word) or word.startswith(('..', '.git/', '-', '/')):
            continue
        path = word.split('::')[0].rstrip('/')
        pattern  = path if '/' in path else '**/' + path
        is_found = any(DIR_REPO.glob(pattern))
        if not is_found:
            list_wrong.append('{guide}: there is no file {path}.'.format(guide = guide,
                                                                          path = path))

    assert not list_wrong, '\n'.join([*list_wrong, MESSAGE_FIX])


# -----------------------------------------------------------------------------
def _known() -> set[str]:
    """
    Return the name of every check and every predicate that rules may
    use. Some begin with the prefix of a type, as concern_count would.

    """

    return (set(cc_public.check.check.wording())
            | set(cc_public.graph.logic.worded(
                  cc_public.commit.change.RULES.read_text(encoding = 'utf-8')))
            | set(cc_public.graph.extract.PREDICATE)
            | set(cc_public.graph.logic.derived()))


# -----------------------------------------------------------------------------
def _fields(map_document: cc_public.graph.extract.Documents) -> set[str]:
    """
    Return the name of every field that some YAML document uses.

    """

    set_field = set()
    list_node = list(map_document.values())

    while list_node:
        node = list_node.pop()
        if isinstance(node, dict):
            set_field.update(str(key) for key in node)
            list_node.extend(node.values())
        elif isinstance(node, (list, tuple)):
            list_node.extend(node)

    return set_field
