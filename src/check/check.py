"""Check the graph of data items held in the tree.

Extract facts from every YAML file under a _data directory, write
them as Souffle input, evaluate check.dl over them, and report every
row of every output relation. Each output relation is one check, and
each row is one failure. The exit status is 1 when any check fails.

Usage: python3 src/check/check.py [root]

The souffle executable is taken from the SOUFFLE environment
variable, or from the PATH.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

import yaml


RULES = pathlib.Path(__file__).with_name('check.dl')


def extract(root):
    """Return the facts of the tree under root, keyed by relation."""
    facts = {name: set() for name in (
        'item', 'reference', 'edge', 'type_prefix',
        'relation_domain', 'relation_range', 'relation_inverse',
        'entry_key')}
    for path in sorted(root.rglob('*.yaml')):
        rel = path.relative_to(root)
        if '_data' not in rel.parts or '.git' in rel.parts:
            continue
        with open(path, encoding='utf-8') as stream:
            _walk(yaml.safe_load(stream), '', str(rel), facts)
    return facts


def _walk(node, holder, file, facts):
    """Add the facts held by node, whose nearest item is holder."""
    if isinstance(node, list):
        for value in node:
            _walk(value, holder, file, facts)
        return
    if not isinstance(node, dict):
        return

    ident = node.get('id_self')
    if isinstance(ident, str):
        facts['item'].add(
            (ident, str(node.get('guid_self', '')), holder, file))
        _signature(ident, node, facts)
        holder = ident

    for key, value in node.items():
        if (key.startswith('id_') and key != 'id_self'
                and isinstance(value, str)):
            role = key[3:]
            guid = str(node.get('guid_' + role, ''))
            facts['reference'].add((holder, role, value, guid, file))

    if isinstance(node.get('id_relation'), str):
        facts['edge'].add(
            (holder, node['id_relation'], str(node.get('id_target'))))

    table = node.get('table')
    if isinstance(ident, str) and isinstance(table, dict):
        for key, entry in table.items():
            if isinstance(entry, dict):
                facts['entry_key'].add(
                    (ident, str(key), str(entry.get('id_self'))))

    for value in node.values():
        _walk(value, holder, file, facts)


def _signature(ident, node, facts):
    """Add the type and relation facts that an entry declares."""
    prefix, regex = node.get('prefix'), node.get('regex_id')
    if isinstance(prefix, str) and isinstance(regex, str):
        facts['type_prefix'].add((ident, prefix, regex))
    for name in ('domain', 'range'):
        for kind in _strings(node.get(name)):
            facts['relation_' + name].add((ident, kind))
    inverse = node.get('inverse')
    if isinstance(inverse, dict) and isinstance(
            inverse.get('id_self'), str):
        facts['relation_inverse'].add((inverse['id_self'], ident))


def _strings(value):
    """Return value if it is a list of strings, else nothing."""
    if isinstance(value, list) and all(
            isinstance(each, str) for each in value):
        return value
    return []


def write(facts, directory):
    """Write each relation as a tab-separated Souffle .facts file."""
    for name, rows in facts.items():
        with open(directory / (name + '.facts'), 'w',
                  encoding='utf-8') as stream:
            for row in sorted(rows):
                for field in row:
                    if '\t' in field or '\n' in field:
                        raise ValueError(f'{name}: {row!r}')
                stream.write('\t'.join(row) + '\n')


def main(argv):
    root = pathlib.Path(argv[1] if len(argv) > 1 else '.').resolve()
    souffle = os.environ.get('SOUFFLE', 'souffle')
    with tempfile.TemporaryDirectory() as temp:
        fact_dir = pathlib.Path(temp, 'fact')
        out_dir = pathlib.Path(temp, 'out')
        fact_dir.mkdir()
        out_dir.mkdir()
        write(extract(root), fact_dir)
        subprocess.run(
            [souffle, '-F', str(fact_dir), '-D', str(out_dir),
             str(RULES)], check=True)
        failures = 0
        for path in sorted(out_dir.glob('*.csv')):
            rows = path.read_text(encoding='utf-8').splitlines()
            for row in rows:
                print(path.stem + ': ' + row.replace('\t', '  '))
            failures += len(rows)
    print(f'{failures} failures')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
