"""
---

id_self:                pym_test.test_environment
guid_self:              pym_72650454b1154704b639a9ad40b95341
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Environment shape tests
brief:                  |
                        Holds the property that keeps one environment
                        cheap to split: nothing imports the model
                        stack as it loads.
description:            |
                        ddr_environment_shape decides that the split
                        stays available only while every import of the
                        model stack sits inside the function that
                        needs it. The record says so and nothing held
                        it, so a module level import anywhere the gate
                        reaches would have closed the option in an
                        afternoon, by somebody tidying what looks like
                        an untidy lazy import.
relation:               []

...
"""


import ast

import pytest

import conftest


ROOT    = conftest.ROOT / 'src' / 'cc_public'
MODULE  = ('dspy', 'litellm', 'openai')
PREFIX_PRIVATE = '_'


def _imported_as_the_module_loads(filepath):
    """
    Return every module name imported at the top level of a file.

    """

    tree = ast.parse(filepath.read_text(encoding = 'utf-8'))
    out  = set()

    for node in tree.body:
        if isinstance(node, ast.Import):
            out.update(alias.name.split('.', 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split('.', 1)[0])

    return out


@pytest.mark.parametrize('filepath', sorted(ROOT.rglob('*.py')),
                         ids = lambda p: p.stem)
def test_the_model_stack_is_imported_inside_the_function_that_needs_it(filepath):
    """
    ---

    id_self:                pyf_test.test_environment.test_the_model_stack_is_imported_inside_the_function_that_needs_it
    guid_self:              pyf_0dfe56553efc4e618a75e83fc9648ab4
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  The model stack is imported where it is needed
    brief:                  |
                            No module of the tool imports the model stack
                            as it loads.
    description:            |
                            The property ddr_environment_shape decides to
                            keep, held over every module of the tool. An
                            import of the model stack at module scope
                            would put it in what the gate installs and
                            close the split the record keeps open.
    relation:               []

    ...
    """

    found = _imported_as_the_module_loads(filepath) & set(MODULE)

    assert not found, '{name} imports {found} as it loads'.format(
                            name = filepath.relative_to(ROOT), found = ', '.join(found))


def _defined_at_module_scope(filepath):
    """
    Return the private functions a module defines at its top level, by
    name, with the line each sits on.

    """

    tree = ast.parse(filepath.read_text(encoding = 'utf-8'))

    return {node.name: node.lineno for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith(PREFIX_PRIVATE)}


def _named_elsewhere(filepath, name):
    """
    Return how many times a name is mentioned outside its own
    definition.

    Outside, because a function that calls itself and nothing else is
    exactly the shape the rule is for: the one a review found had two
    recursive calls and no caller.

    """

    tree = ast.parse(filepath.read_text(encoding = 'utf-8'))
    own  = next((node for node in tree.body
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and node.name == name), None)
    mine = {id(node) for node in ast.walk(own)} if own is not None else set()

    return sum(1 for node in ast.walk(tree)
               if isinstance(node, ast.Name) and node.id == name and id(node) not in mine)


@pytest.mark.parametrize('filepath', sorted(ROOT.rglob('*.py')),
                         ids = lambda p: p.stem)
def test_a_private_function_at_module_scope_has_a_caller(filepath):
    """
    ---

    id_self:                pyf_test.test_environment.test_a_private_function_at_module_scope_has_a_caller
    guid_self:              pyf_4b291c65ddd246c59e04d7b315b3f0b8
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  A private function has a caller
    brief:                  |
                            No module of the tool defines a private
                            function at its top level that nothing but its
                            own recursion names.
    description:            |
                            A name beginning with an underscore belongs to
                            its module, so every caller is in the same
                            file and a walk of that file answers it. A
                            review found one left behind when what called
                            it was rewritten, and the ruff rules in use do
                            not reach it (ddr_code_quality).
    relation:               []

    ...
    """

    dead = [name for (name, line) in _defined_at_module_scope(filepath).items()
            if _named_elsewhere(filepath, name) == 0]

    assert not dead, '{name} defines {dead}, which nothing calls'.format(
                            name = filepath.relative_to(ROOT), dead = ', '.join(dead))
