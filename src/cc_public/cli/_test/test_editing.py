"""
---

id_self:                pym_cc_public.cli._test.test_editing
guid_self:              pym_d203fbe35763494eb549a6ef16939ab3
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Editing command tests
brief:                  |
                        Tests of the editing commands, as the command
                        line presents them.
description:            |
                        Each test runs a command over a copy of the
                        repository, and checks what it writes, what it
                        prints and its exit status.
edge:                   []

...
"""


import click.testing

import cc_public.cli.command


LIST_ANN = ['new', 'ann_x', '--field', 'title', 'Edits work', '--field', 'brief', 'They do.']


# -----------------------------------------------------------------------------
def _run(tree, *list_arg, stdin = None):
    """
    Return the result of cctool with list_arg, over tree.

    """

    runner = click.testing.CliRunner()
    return runner.invoke(cc_public.cli.command.main, [*list_arg, '--root', str(tree)],
                         input = stdin)


def test_new_writes_the_item_and_says_where(tree):
    result = _run(tree, *LIST_ANN, '--link', 'relation_is_about', 'concept_concept')
    assert result.exit_code == 0
    assert result.stdout == 'Wrote _data/annotation/ann_x.yaml\n'
    assert (tree / '_data/annotation/ann_x.yaml').exists()


def test_a_field_named_twice_is_a_list(tree):
    result = _run(tree, 'new', 'concern_x',
                  '--field', 'title', 'X',
                  '--field', 'brief', 'X.',
                  '--field', 'description', 'X.',
                  '--field', 'question', 'Is it X?',
                  '--field', 'question', 'Is it Y?',
                  '--field', 'measure', 'X, in percent.',
                  '--field', 'measure', 'X, per release.')
    assert result.exit_code == 0
    assert ('    measure:\n'
            '      - X, in percent.\n'
            '      - X, per release.\n') in (tree / '_data/register/reg_concern.yaml').read_text()


def test_dry_run_prints_a_diff_and_writes_nothing(tree):
    result = _run(tree, *LIST_ANN, '--link', 'relation_is_about', 'concept_concept', '--dry-run')
    assert result.exit_code == 0
    assert result.stdout.startswith('--- a/_data/annotation/ann_x.yaml\n'
                                    '+++ b/_data/annotation/ann_x.yaml\n'
                                    '@@ -0,0 +1,20 @@\n'
                                    '+id_self:                ann_x\n')
    assert not (tree / '_data/annotation/ann_x.yaml').exists()


def test_an_edit_that_adds_a_failure_is_refused(tree):
    result = _run(tree, *LIST_ANN)
    assert result.exit_code == 1
    assert result.stdout == ''
    assert result.stderr == ('missing_about: ann_x is about nothing: it has no edge of relation_is_about.\n'
                             '  fix: Link it to its subject with cctool link ID relation_is_about TARGET.\n'
                             'Refused: the edit adds 1 failure. Nothing was written.\n')


def test_an_edit_that_cannot_be_made_exits_with_2(tree):
    result = _run(tree, 'link', 'ann_none', 'relation_is_about', 'concept_concept')
    assert result.exit_code == 2
    assert result.stderr == 'No item has the id ann_none.\n'


def test_batch_makes_items_that_need_each_other_together(tree):
    stdin  = ('- new:   concept_x\n'
              '  field: {title: X, brief: X., description: X., term_preferred: x}\n'
              '- new:   ann_x\n'
              '  field: {title: X, brief: X.}\n'
              '  link:  [[relation_is_about, concept_x]]\n'
              '- set:   [concept_x, note, A note.]\n')
    result = _run(tree, 'batch', '-', stdin = stdin)
    assert result.exit_code == 0
    assert result.stdout == ('Wrote _data/register/reg_concept.yaml\n'
                             'Wrote _data/annotation/ann_x.yaml\n')


def test_set_with_yaml_writes_a_list_and_unset_takes_it_out(tree):
    path = tree / '_data/register/reg_concept.yaml'
    text = path.read_text()
    result = _run(tree, 'set', 'concept_concept', 'term_admitted', '[idea, notion]', '--yaml')
    assert result.exit_code == 0
    assert '    term_admitted:\n      - idea\n      - notion\n' in path.read_text()
    assert _run(tree, 'unset', 'concept_concept', 'term_admitted').exit_code == 0
    assert path.read_text() == text


def test_set_refuses_a_value_that_is_not_yaml(tree):
    result = _run(tree, 'set', 'concept_concept', 'term_admitted', '[idea', '--yaml')
    assert result.exit_code == 2
    assert result.stderr.startswith('VALUE is not YAML: ')


def test_header_gives_a_file_its_item_and_says_where(tree):
    (tree / 'src/cc_public/cli/extra.py').write_text('X = 1\n')
    result = _run(tree, 'header', 'src/cc_public/cli/extra.py',
                  '--field', 'title', 'Extra', '--field', 'brief', 'Extra.',
                  '--field', 'description', 'Extra.')
    assert result.exit_code == 0
    assert result.stdout == 'Wrote src/cc_public/cli/extra.py\n'
    assert (tree / 'src/cc_public/cli/extra.py').read_text().startswith(
        '"""\n---\n\nid_self:                pym_cc_public.cli.extra\n')


def test_remove_says_which_file_it_removed(tree):
    assert _run(tree, *LIST_ANN, '--link', 'relation_is_about', 'concept_concept').exit_code == 0
    result = _run(tree, 'remove', 'ann_x')
    assert result.exit_code == 0
    assert result.stdout == 'Removed _data/annotation/ann_x.yaml\n'


def test_rename_lists_the_files_that_still_name_the_old_id(tree):
    result = _run(tree, 'rename', 'concept_annotation', 'concept_remark')
    assert result.exit_code == 0
    assert 'Wrote _data/register/reg_concept.yaml\n' in result.stdout
    assert ('Still names concept_annotation: src/cc_public/edit/_test/test_edit.py\n'
            in result.stderr)


def test_format_names_the_files_it_would_change_and_then_changes_them(tree):
    path = tree / '_data/register/reg_concern.yaml'
    path.write_text(path.read_text().replace('title:                  Concern register',
                                             'title: Concern register'))
    result = _run(tree, 'format', '--check')
    assert result.exit_code == 1
    assert result.stdout == 'Would change _data/register/reg_concern.yaml\n'
    result = _run(tree, 'format')
    assert result.exit_code == 0
    assert result.stdout == 'Changed _data/register/reg_concern.yaml\n'
    assert _run(tree, 'format', '--check').stdout == ''


TEXT_ONTOLOGY = '''\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix x:    <https://example.org/x/> .
x:entity    a owl:Class ; rdfs:label "entity"@en .
x:continuant a owl:Class ; rdfs:label "continuant"@en ; rdfs:subClassOf x:entity .
x:record    a owl:Class ; rdfs:label "Record Entity"@en ; rdfs:subClassOf x:continuant .
x:unused    a owl:Class ; rdfs:label "unused"@en ; rdfs:subClassOf x:entity .
'''
LIST_IMPORT   = ['--namespace', 'https://example.org/x/', 'x', 'extdoc_iso_1087_2019',
                 'https://example.org/x/record']


# -----------------------------------------------------------------------------
def _import(tree, text = TEXT_ONTOLOGY, list_arg = LIST_IMPORT):
    """
    Return the result of cctool import of text, as a Turtle file in tree.

    """

    path = tree / 'ontology.ttl'
    path.write_text(text)
    return _run(tree, 'import', str(path), *list_arg)


def test_import_makes_the_class_and_every_class_above_it(tree):
    result = _import(tree)
    assert result.exit_code == 0, result.output
    assert sorted(path.name for path in (tree / '_data/external_class').glob('extcla_x_*')) == [
        'extcla_x_continuant.yaml', 'extcla_x_entity.yaml', 'extcla_x_record_entity.yaml']
    text = (tree / '_data/external_class/extcla_x_record_entity.yaml').read_text()
    assert 'title:                  X Record Entity\n' in text
    assert 'label:                  Record Entity\n' in text
    assert '    value:              https://example.org/x/record\n' in text
    assert 'id_target:          extcla_x_continuant\n' in text
    assert 'id_target:          extdoc_iso_1087_2019\n' in text


def test_import_again_changes_nothing(tree):
    assert _import(tree).exit_code == 0
    result = _import(tree)
    assert result.exit_code == 0
    assert result.stdout == 'The external classes agree with the release already.\n'


def test_import_of_a_new_release_changes_only_what_differs(tree):
    assert _import(tree).exit_code == 0
    result = _import(tree, TEXT_ONTOLOGY.replace('"continuant"', '"enduring entity"'))
    assert result.exit_code == 0, result.output
    assert result.stdout == 'Wrote _data/external_class/extcla_x_continuant.yaml\n'
    text = (tree / '_data/external_class/extcla_x_continuant.yaml').read_text()
    assert 'label:                  enduring entity\n' in text


def test_import_refuses_a_class_the_release_lacks(tree):
    result = _import(tree, list_arg = [*LIST_IMPORT[:4], 'https://example.org/x/missing'])
    assert result.exit_code == 2
    assert 'The release has no labelled class https://example.org/x/missing.' in result.stderr


def test_import_refuses_a_class_no_namespace_covers(tree):
    result = _import(tree, list_arg = ['--namespace', 'https://example.org/y/', 'y',
                                       'extdoc_iso_1087_2019', 'https://example.org/x/record'])
    assert result.exit_code == 2
    assert 'No --namespace covers the class https://example.org/x/' in result.stderr


def test_import_check_names_what_differs_and_writes_nothing(tree):
    assert _import(tree).exit_code == 0
    text   = TEXT_ONTOLOGY.replace('"continuant"', '"enduring entity"')
    result = _import(tree, text, [*LIST_IMPORT[:4], '--check'])
    assert result.exit_code == 1
    assert result.stdout.startswith('extcla_x_continuant: its title differs from the release.\n')
    assert 'extcla_x_continuant: its label differs from the release.\n' in result.stdout
    assert 'label:                  continuant\n' in (
                        tree / '_data/external_class/extcla_x_continuant.yaml').read_text()


def test_import_check_passes_when_the_classes_agree(tree):
    assert _import(tree).exit_code == 0
    result = _import(tree, list_arg = [*LIST_IMPORT[:4], '--check'])
    assert result.exit_code == 0
    assert result.stdout == 'The external classes agree with the release already.\n'


def test_import_refuses_a_file_that_is_not_the_recorded_release(tree):
    result = _import(tree, list_arg = ['--namespace', 'https://example.org/x/', 'x',
                                       'extdoc_cco_2_2', 'https://example.org/x/record'])
    assert result.exit_code == 2
    assert 'but extdoc_cco_2_2 records a9453382' in result.stderr
