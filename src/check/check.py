"""
---

id_self:                pym_check
guid_self:              pym_56d08447c0cf432dbe39760c22730116
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Check
brief:                  |
                        Check the graph of data items held in the
                        tree, by evaluating check.dl over facts
                        extracted from it.
description:            |
                        This module extracts facts from every YAML
                        file under a _data directory, writes them as
                        Souffle input, evaluates check.dl over them,
                        and reports every row of every output
                        relation. Each output relation is one check,
                        and each row is one failure. The exit status
                        is 1 when any check fails.
usage:                  |
                        python3 src/check/check.py [root]

                        The souffle executable is taken from the
                        SOUFFLE environment variable, or from the
                        PATH.
relation:               []

...
"""


import os
import pathlib
import subprocess
import sys
import tempfile
import typing

import yaml


RULES             = pathlib.Path(__file__).with_name('check.dl')

KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_ID_RELATION   = 'id_relation'
KEY_ID_TARGET     = 'id_target'
KEY_TABLE         = 'table'
KEY_PREFIX        = 'prefix'
KEY_REGEX_ID      = 'regex_id'
KEY_INVERSE       = 'inverse'

PREFIX_ID         = 'id_'
PREFIX_GUID       = 'guid_'
DIR_DATA          = '_data'
DIR_GIT           = '.git'
DELIM_FIELD       = '\t'

TUPLE_RELATION    = ('item',
                     'reference',
                     'edge',
                     'type_prefix',
                     'relation_domain',
                     'relation_range',
                     'relation_inverse',
                     'entry_key')

Facts             = dict[str, set[tuple[str, ...]]]


# -----------------------------------------------------------------------------
def extract(root: pathlib.Path) -> Facts:
    """
    Return the facts of the tree under root, keyed by relation.

    """

    facts = {name: set() for name in TUPLE_RELATION}

    for path in sorted(root.rglob('*.yaml')):
        relative = path.relative_to(root)
        if (DIR_DATA not in relative.parts) or (DIR_GIT in relative.parts):
            continue
        with open(path, encoding = 'utf-8') as file:
            _walk(yaml.safe_load(file), '', str(relative), facts)

    return facts


# -----------------------------------------------------------------------------
def _walk(node: typing.Any, holder: str, location: str, facts: Facts) -> None:
    """
    Add the facts held by node, whose nearest enclosing item is holder.

    """

    if isinstance(node, list):

        for value in node:
            _walk(value, holder, location, facts)
        return

    if not isinstance(node, dict):
        return

    id_self = node.get(KEY_ID_SELF)

    if isinstance(id_self, str):

        facts['item'].add((id_self,
                           str(node.get(KEY_GUID_SELF, '')),
                           holder,
                           location))
        _signature(id_self, node, facts)
        holder = id_self

    _reference(node, holder, location, facts)

    table = node.get(KEY_TABLE)

    if isinstance(id_self, str) and isinstance(table, dict):
        for (key, entry) in table.items():
            if isinstance(entry, dict):
                facts['entry_key'].add((id_self,
                                        str(key),
                                        str(entry.get(KEY_ID_SELF))))

    for value in node.values():
        _walk(value, holder, location, facts)


# -----------------------------------------------------------------------------
def _reference(node:     dict[str, typing.Any],
               holder:   str,
               location: str,
               facts:    Facts) -> None:
    """
    Add a fact for each reference that node makes, and for the edge
    that node is, if it is one.

    """

    for (key, value) in node.items():
        if key.startswith(PREFIX_ID) and key != KEY_ID_SELF and isinstance(value, str):
            role = key[len(PREFIX_ID):]
            guid = str(node.get(PREFIX_GUID + role, ''))
            facts['reference'].add((holder, role, value, guid, location))

    if isinstance(node.get(KEY_ID_RELATION), str):
        facts['edge'].add((holder,
                           node[KEY_ID_RELATION],
                           str(node.get(KEY_ID_TARGET))))


# -----------------------------------------------------------------------------
def _signature(id_self: str, node: dict[str, typing.Any], facts: Facts) -> None:
    """
    Add the type and relation facts that an entry declares.

    """

    prefix   = node.get(KEY_PREFIX)
    regex_id = node.get(KEY_REGEX_ID)

    if isinstance(prefix, str) and isinstance(regex_id, str):
        facts['type_prefix'].add((id_self, prefix, regex_id))

    for name in ('domain', 'range'):
        for id_type in _list_str(node.get(name)):
            facts['relation_' + name].add((id_self, id_type))

    inverse = node.get(KEY_INVERSE)

    if isinstance(inverse, dict) and isinstance(inverse.get(KEY_ID_SELF), str):
        facts['relation_inverse'].add((inverse[KEY_ID_SELF], id_self))


# -----------------------------------------------------------------------------
def _list_str(value: typing.Any) -> list[str]:
    """
    Return value if it is a list of strings, and an empty list if not.

    """

    if isinstance(value, list) and all(isinstance(each, str) for each in value):
        return value
    return []


# -----------------------------------------------------------------------------
def write(facts: Facts, dir_fact: pathlib.Path) -> None:
    """
    Write each relation as a tab separated Souffle .facts file.

    """

    for (name, set_row) in facts.items():
        path = dir_fact / '{name}.facts'.format(name = name)
        with open(path, 'w', encoding = 'utf-8') as file:
            for row in sorted(set_row):
                if any((DELIM_FIELD in field) or ('\n' in field) for field in row):
                    raise ValueError('{name}: {row!r}'.format(name = name, row = row))
                file.write(DELIM_FIELD.join(row) + '\n')


# -----------------------------------------------------------------------------
def main(list_arg: list[str]) -> int:
    """
    Check the tree named by the first argument, or the current
    directory, and return the exit status.

    """

    root    = pathlib.Path(list_arg[1] if len(list_arg) > 1 else '.').resolve()
    souffle = os.environ.get('SOUFFLE', 'souffle')
    count   = 0

    with tempfile.TemporaryDirectory() as dir_temp:

        dir_fact = pathlib.Path(dir_temp, 'fact')
        dir_out  = pathlib.Path(dir_temp, 'out')
        dir_fact.mkdir()
        dir_out.mkdir()

        write(extract(root), dir_fact)
        subprocess.run([souffle, '-F', str(dir_fact), '-D', str(dir_out), str(RULES)],
                       check = True)

        for path in sorted(dir_out.glob('*.csv')):
            for row in path.read_text(encoding = 'utf-8').splitlines():
                print('{check}: {row}'.format(check = path.stem,
                                              row   = row.replace(DELIM_FIELD, '  ')))
                count += 1

    print('{count} failures'.format(count = count))
    return 1 if count else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
