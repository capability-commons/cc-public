"""
---

id_self:                pym_cctool.check._test.test_citation
guid_self:              pym_94ae04228e554673b98afd8dff2cb359
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Citation tests
brief:                  |
                        Tests of the checks that prose cites a file of
                        the tree by the part it means, and that the
                        cited file holds that part.
description:            |
                        Each test writes a small tree of a python
                        module, a logic program, a pyproject.toml, a
                        README.md and a data item, and checks the
                        citations in the brief of the item.
edge:                   []

...
"""


import cctool.check.citation


# -----------------------------------------------------------------------------
def test_a_citation_by_line_is_reported_and_one_of_a_commit_is_not(tmp_path):
    _files(tmp_path)
    (list_line, list_name) = _violations(tmp_path, 'It is so (src/tool.py lines 3-4, and'
                                                   ' 0b69eb4:src/tool.py line 2).')
    assert list_line == [('_data/item.yaml', '1', 'item_x', 'src/tool.py lines 3-4')]
    assert list_name == []


# -----------------------------------------------------------------------------
def test_a_part_of_each_kind_of_file_is_found_by_name(tmp_path):
    _files(tmp_path)
    text = ('See tool.py within check, tool.py within Store.load and LIMIT, '
            'pyproject.toml at project.dependencies, pyproject.toml just after '
            'tool.pixi.tasks.gate, _data/item.yaml at edge, README.md#getting-started, '
            'rules.lp within dangling_mention.')
    assert _violations(tmp_path, text) == ([], [])


# -----------------------------------------------------------------------------
def test_a_part_the_file_does_not_hold_is_reported(tmp_path):
    _files(tmp_path)
    text = ('See tool.py within Store.save, pyproject.toml at project.name_of and '
            'README.md#gone.')
    assert _violations(tmp_path, text)[1] == [
        ('_data/item.yaml', '1', 'item_x', 'README.md', 'gone'),
        ('_data/item.yaml', '1', 'item_x', 'pyproject.toml', 'project.name_of'),
        ('_data/item.yaml', '1', 'item_x', 'src/tool.py', 'Store.save')]


# -----------------------------------------------------------------------------
def test_a_plain_word_or_a_commit_after_a_path_is_prose(tmp_path):
    _files(tmp_path)
    text = 'The tool.py at hand, and pyproject.toml at 89c74d8, are as they were.'
    assert _violations(tmp_path, text) == ([], [])


# -----------------------------------------------------------------------------
def _files(root):
    """
    Write a small tree: a python module, a logic program, a pyproject.toml,
    a README.md and a data item.

    """

    (root / 'src').mkdir()
    (root / '_data').mkdir()
    (root / 'src/tool.py').write_text('LIMIT = 3\n\n\ndef check():\n    pass\n\n\n'
                                      'class Store:\n    def load(self):\n        pass\n')
    (root / 'src/rules.lp').write_text('% decl dangling_mention(holder, id).\n'
                                       'dangling_mention(H, I) :- mention(H, I).\n')
    (root / 'pyproject.toml').write_text('[project]\nname = "x"\ndependencies = ["click"]\n\n'
                                         '[tool.pixi.tasks]\ngate = "cctool gate"\n')
    (root / 'README.md').write_text('# Tool\n\n## Getting started\n\nRun it.\n')
    (root / '_data/item.yaml').write_text('id_self: item_x\nedge: []\n')


# -----------------------------------------------------------------------------
def _violations(root, text):
    """
    Return the rows of the two checks of citations for a tree whose one
    data item holds text in its brief.

    """

    document = {'id_self': 'item_x', 'brief': text, 'edge': []}
    return cctool.check.citation.violations(root, {'_data/item.yaml': (document, 1)})
