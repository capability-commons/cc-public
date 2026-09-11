"""
---

id_self:                pym_test.test_glossary
guid_self:              pym_7a791015544446a3ac757e9e9e65b6fd
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Glossary projection tests
brief:                  |
                        Tests of the glossary projection: lookup over
                        a word two concepts claim, the sense report,
                        and the gap report.
description:            |
                        Reads the tree the fixture copies. A word two
                        entries claim returns both. A rejected word
                        returns the entry that rejects it. A word a
                        glossary holds is not a gap, in the singular
                        or the plural, and a word prose uses that no
                        glossary holds is.
relation:               []

...
"""


import cc_public.edit.field
import cc_public.edit.insert
import cc_public.glossary


def _map(tree):
    return tree.context.map_document


def test_a_word_two_concepts_claim_returns_both(tree):
    (accepted, avoided) = cc_public.glossary.lookup(_map(tree), 'concept')
    assert [t.id_self for t in accepted] == ['term_ontology_concept', 'term_solution_concept']
    assert avoided == ()


def test_a_rejected_word_returns_the_entry_that_rejects_it(tree):
    (accepted, avoided) = cc_public.glossary.lookup(_map(tree), 'idea')
    assert accepted == ()
    assert 'term_solution_concept' in [t.id_self for t in avoided]


def test_an_accepted_other_form_finds_the_entry(tree):
    (accepted, _) = cc_public.glossary.lookup(_map(tree), 'solution concept')
    assert [t.id_self for t in accepted] == ['term_solution_concept']


def test_the_sense_report_names_the_word_and_its_entries(tree):
    (shared, numbered) = cc_public.glossary.senses(_map(tree))
    assert ('concept', ('term_ontology_concept', 'term_solution_concept')) in shared
    assert numbered == ()


def test_a_readable_id_that_numbers_a_sense_is_reported(tree):
    cc_public.edit.insert.insert(tree, 't_term', 'scope_2', 'reg_term', 'table')
    cc_public.edit.field.set_field(tree, 'term_scope_2', 'term', value = 'scope')
    (_, numbered) = cc_public.glossary.senses(_map(tree))
    assert numbered == ('term_scope_2',)


def test_a_word_a_glossary_holds_is_no_gap_in_either_number(tree):
    (word, pair, _) = cc_public.glossary.gaps(_map(tree), minimum = 1)
    phrases = {p for (p, _) in word} | {p for (p, _) in pair}
    assert 'register' not in phrases                     # term_register holds it
    assert 'registers' not in phrases                    # a plural is the same word
    assert 'control cases' not in phrases                # a pair, in the plural


def test_a_word_prose_uses_that_no_glossary_holds_is_a_gap(tree):
    (word, _, _) = cc_public.glossary.gaps(_map(tree), minimum = 1)
    assert 'prose' in {p for (p, _) in word}


def test_a_term_no_record_decides_is_reported(tree):
    (_, _, undecided) = cc_public.glossary.gaps(_map(tree), minimum = 1)
    assert 'term_solution_concept' not in undecided      # ddr_concept decides it
    assert 'term_anchor' in undecided


def test_a_datum_written_as_a_block_scalar_is_not_counted_as_prose(tree, tmp_path):
    # A control case subject, a query's sql and a rule's example hold
    # line breaks and are not prose. Counted as prose, the candidate
    # list opened with the headers of every stored subject.
    import cc_public.check
    import cc_public.glossary

    context = cc_public.check.context([tmp_path])[0]
    read    = '\n'.join(text for (_, text)
                         in cc_public.glossary._iter_prose(
                                dict(context.map_document)))

    # Nothing a control case, a query or a rule example holds reaches
    # the count. The candidate list opened with the header of every
    # stored subject before this.
    assert 'as rendered:' not in read
    assert 'SELECT ' not in read

    (word, pair, _) = cc_public.glossary.gaps(context.map_document, 3)
    said = {row[0] for row in word} | {row[0] for row in pair}
    assert 'statement' not in said and 'def' not in said


def test_a_run_of_words_inside_a_term_is_not_a_gap(tree, tmp_path):
    # The register holds writing style rule and writing style guide,
    # and interface control document. The pair list presented the
    # glossary's own terms back as candidates.
    import cc_public.check
    import cc_public.glossary

    context = cc_public.check.context([tmp_path])[0]
    (_, pair, _) = cc_public.glossary.gaps(context.map_document, 1)
    said = {row[0] for row in pair}

    assert 'writing style' not in said
    assert 'interface control' not in said
    assert 'control document' not in said
