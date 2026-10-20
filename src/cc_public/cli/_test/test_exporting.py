"""
---

id_self:                pym_cc_public.cli._test.test_exporting
guid_self:              pym_7d07934eb6824a9ab52fa2856277c71c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Exporting command tests
brief:                  |
                        Tests of the export commands, as the command
                        line presents them.
description:            |
                        Each test exports a copy of the repository's
                        data items to a folder, and checks the pages
                        written, or the refusal and its exit status.
relation:               []

...
"""


import click.testing

import cc_public.cli.command
import cc_public.export.obsidian


# -----------------------------------------------------------------------------
def _run(tree, *list_arg):
    """
    Return the result of cctool export with list_arg, over tree.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main,
                         ['export', *list_arg, '--root', str(tree)])


# -----------------------------------------------------------------------------
def _frontmatter(text):
    """
    Return the lines of the frontmatter of the page text, or None if it
    has none.

    """

    list_line = text.split('\n')
    if list_line[0] != '---':
        return None

    return list_line[1:list_line.index('---', 1)]


def test_obsidian_writes_a_note_for_each_item_with_wikilinks(tree, tmp_path):
    dir_out = tmp_path / 'vault'
    result  = _run(tree, 'obsidian', str(dir_out))
    assert result.exit_code == 0
    text = (dir_out / 'issue' / 'iss_tooling_language.md').read_text()
    assert _frontmatter(text)[:5] == ['type: "t_issue"',
                                      'title: "Language of the tooling"',
                                      'aliases: ["Language of the tooling"]',
                                      'tags: ["issue"]',
                                      'id: "iss_tooling_language"']
    assert '# Language of the tooling\n' in text
    assert '- This issue makes its assertion about [[lc_tooling|Tooling]].\n' in text


def test_obsidian_links_a_dotted_id_by_its_file():
    assert cc_public.export.obsidian.link({}, 'pym_a.b') == '[[pym_a.b.md|pym_a.b]]'
    assert cc_public.export.obsidian.link({}, 'lc_a') == '[[lc_a|lc_a]]'


def test_a_folder_that_is_not_empty_is_refused(tree, tmp_path):
    dir_out = tmp_path / 'vault'
    dir_out.mkdir()
    (dir_out / 'note.md').write_text('mine\n')
    result = _run(tree, 'obsidian', str(dir_out))
    assert result.exit_code == 2
    assert 'is not empty' in result.stderr
    assert (dir_out / 'note.md').read_text() == 'mine\n'


def test_replace_removes_old_pages_and_keeps_other_files(tree, tmp_path):
    dir_out = tmp_path / 'vault'
    (dir_out / '.obsidian').mkdir(parents = True)
    (dir_out / '.obsidian' / 'app.json').write_text('{}\n')
    (dir_out / 'gone' / 'old.md').parent.mkdir()
    (dir_out / 'gone' / 'old.md').write_text('old\n')
    result = _run(tree, 'obsidian', str(dir_out), '--replace')
    assert result.exit_code == 0
    assert (dir_out / '.obsidian' / 'app.json').read_text() == '{}\n'
    assert not (dir_out / 'gone').exists()
    assert (dir_out / 'issue' / 'iss_tooling_language.md').exists()
