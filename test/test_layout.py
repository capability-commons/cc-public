"""
---

id_self:                pym_test.test_layout
guid_self:              pym_f0599442807d4a7c81dd1a9a6be7e00f
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Layout tests
brief:                  |
                        The printer preserves content and is a
                        fixpoint.
description:            |
                        Runs the printer over every file in the tree
                        and over adversarial documents, asserting
                        content is preserved, comments are kept, and
                        the result is a fixpoint.

...
"""

import ast
import pathlib

import pytest
import ruamel.yaml
import ruamel.yaml.scalarstring

import cc_public.check
import cc_public.layout
import cc_public.load.python


ROOT = pathlib.Path(__file__).resolve().parent.parent
RT   = ruamel.yaml.YAML(typ = 'rt')


def shape(node):
    """Exact for every scalar; words only for literal block scalars."""
    if isinstance(node, dict):
        return {k: shape(v) for (k, v) in node.items()}
    if isinstance(node, list):
        return [shape(v) for v in node]
    if isinstance(node, ruamel.yaml.scalarstring.LiteralScalarString):
        return ('|', ' '.join(node.split()))
    if isinstance(node, str):
        return ('=', str(node))
    return node


def code_of(text):
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) \
                and node.body and isinstance(node.body[0], ast.Expr) \
                and isinstance(node.body[0].value, ast.Constant):
            node.body[0].value.value = ''
    return ast.dump(tree, include_attributes = False)


def documents_of(text):
    return [shape(RT.load(m.text))
            for m in cc_public.load.python.iter_metadata(text)]


FILES = sorted(p for p in set(cc_public.check.iter_filepath_all([ROOT]))
                 if p.suffix in ('.yaml', '.py'))


@pytest.mark.parametrize('filepath', FILES, ids = lambda p: p.name)
def test_printer_preserves_and_is_fixpoint(filepath):
    source = filepath.read_text(encoding = 'utf-8')
    out    = cc_public.layout.format_source(source, filepath.suffix)

    assert cc_public.layout.format_source(out, filepath.suffix) == out

    if filepath.suffix == '.yaml':
        assert shape(RT.load(out)) == shape(RT.load(source))
    else:
        assert code_of(out) == code_of(source)
        assert documents_of(out) == documents_of(source)

    def count_comment(text):
        return sum(line.lstrip().startswith('#') for line in text.splitlines())
    assert count_comment(out) == count_comment(source)


def test_long_plain_scalar_is_left_alone():
    text = 'pattern:                ^(a b|c d)[0-9]{4} ' + 'x' * 70 + '$\n'
    assert cc_public.layout.format(text) == text


def test_only_block_scalars_are_refilled():
    text = ('note:                   |\n'
            '                        one two\n'
            '                        three\n')
    assert 'one two three' in cc_public.layout.format(text)


def test_flow_lists_become_block():
    out = cc_public.layout.format('alias:                  [a, b]\n')
    assert out == 'alias:\n  - a\n  - b\n'


def test_unsupported_is_refused():
    with pytest.raises(cc_public.layout.Unsupported):
        cc_public.layout.format('- a\n- b\n')


def test_nested_docstrings_are_located_and_laid_out():
    src = ('"""\n---\nid_self: pym_x\n...\n"""\n\nclass A:\n    """\n    ---\n'
           '    id_self:  pyc_x.a\n    ...\n    """\n\n    def f(self):\n'
           '        """\n        ---\n        id_self: pyf_x.a.f\n        ...\n'
           '        """\n')
    found = list(cc_public.load.python.iter_metadata(src))
    assert [(m.kind, m.path, m.indent) for m in found] == \
           [('module', (), 0), ('class', ('A',), 4), ('function', ('A', 'f'), 8)]
    out = cc_public.layout.format_metadata(src)
    assert '        id_self:                pyf_x.a.f' in out
    assert cc_public.layout.format_metadata(out) == out


def test_marker_inside_a_string_is_not_a_document():
    src = '"""\n---\nid_self: pym_x\n...\n"""\nS = """\n---\n"""\n'
    assert len(list(cc_public.load.python.iter_metadata(src))) == 1


def test_a_long_quoted_scalar_is_never_folded_or_truncated(tmp_path):
    import cc_public.edit.tree
    long = "Unmet on 5 of 5 judgements: backticks around `id_type`, and a colon: here, " * 4
    doc  = {'a': [{'reason': long.strip(), 'n': 1}]}
    path = tmp_path / 'x.yaml'
    cc_public.edit.tree.save(path, doc)
    back = cc_public.load.from_file(path)
    assert back['a'][0]['reason'] == long.strip()
    assert cc_public.layout.format(path.read_text()) == path.read_text()
