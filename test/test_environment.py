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
