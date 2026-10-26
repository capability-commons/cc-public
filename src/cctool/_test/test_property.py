"""
---

id_self:                pym_cctool._test.test_property
guid_self:              pym_ceeae2e1bd8c4d67b9b907c48263e42b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Property tests
brief:                  |
                        Tests that hold a property of the tooling over
                        inputs that Hypothesis makes up, rather than
                        over a few chosen by hand.
description:            |
                        Each test states something that must hold for
                        any input: a layout of a layout is the same
                        layout, a rename undone gives back the tree, a
                        file of any text is read or reported
                        unreadable, a commit message that message new
                        prints passes message check, and a citation of
                        a part that a file holds is never reported.

                        The tests are marked fuzz, so the gate of a
                        commit leaves them out. A run makes few
                        examples of each, with no database. With
                        CCTOOL_FUZZ set to overnight, a run makes many
                        and keeps the examples that failed in a
                        database in the git directory, which every
                        worktree shares, so that the next run tries
                        them first. An example that fails overnight is
                        added to its test with example once fixed, so
                        that every run tries it.
edge:                   []

...
"""


import contextlib
import functools
import os
import pathlib
import re
import string

import click.testing
import pytest
import ruamel.yaml

import cctool.check.citation
import cctool.cli.command
import cctool.conftest
import cctool.edit.edit
import cctool.edit.layout
import cctool.gate.gate
import cctool.graph.extract


hypothesis = pytest.importorskip('hypothesis')
strategies = hypothesis.strategies


pytestmark = [pytest.mark.fuzz, pytest.mark.reads_data]


DIR_REPO          = cctool.conftest.DIR_REPO
ENV_FUZZ          = 'CCTOOL_FUZZ'
NAME_OVERNIGHT    = 'overnight'
NAME_RUN          = 'run'
DIR_DATABASE      = 'cctool_hypothesis'
COUNT_RUN         = 20
COUNT_OVERNIGHT   = 2000

# A test that reads the whole tree for each example makes fewer: a
# rename, or a check of a commit message against the schemas. A rename
# checks the tree twice, so it is marked slow, and the gate of a push
# leaves it out.
#
COUNT_HEAVY       = {NAME_RUN: 3, NAME_OVERNIGHT: 200}

# A few examples on each run, with no database; many overnight, with the
# examples that failed kept in the git directory.
#
NAME_PROFILE      = NAME_OVERNIGHT if os.environ.get(ENV_FUZZ) == NAME_OVERNIGHT else NAME_RUN
MAP_COUNT         = {NAME_RUN: COUNT_RUN, NAME_OVERNIGHT: COUNT_OVERNIGHT}
LIST_HEALTH        = [hypothesis.HealthCheck.function_scoped_fixture,
                     hypothesis.HealthCheck.too_slow]

hypothesis.settings.register_profile(
                NAME_PROFILE,
                max_examples          = MAP_COUNT[NAME_PROFILE],
                deadline              = None,
                database              = (hypothesis.database.DirectoryBasedExampleDatabase(
                                             cctool.gate.gate.git_dir(DIR_REPO) / DIR_DATABASE)
                                         if NAME_PROFILE == NAME_OVERNIGHT else None),
                suppress_health_check = LIST_HEALTH)
hypothesis.settings.load_profile(NAME_PROFILE)

HEAVY             = hypothesis.settings(max_examples = COUNT_HEAVY[NAME_PROFILE])


# Text as people and agents write it in a data item: printable, with
# some punctuation that YAML gives a meaning to, and some letters beyond
# ASCII.
#
ALPHABET          = string.printable.replace('\r', '').replace('\x0b', '').replace('\x0c', '')
TEXT              = strategies.text(alphabet = strategies.sampled_from(ALPHABET + '\u00e9\u00df\u20ac\u2014'),
                                    max_size = 200)
WORD              = strategies.from_regex(r'[a-z]{1,8}(_[a-z]{1,8}){0,3}', fullmatch = True)
KEY               = strategies.sampled_from(('title', 'brief', 'description', 'note',
                                             'condition', 'object', 'rationale'))
SCALAR            = strategies.one_of(TEXT, strategies.integers(), strategies.booleans())
DOCUMENT          = strategies.dictionaries(KEY, strategies.one_of(SCALAR,
                                                                   strategies.lists(TEXT,
                                                                                    max_size = 4)),
                                            min_size = 1, max_size = 5)

# The types of item that a rename may move without keeping an alias,
# since only a register entry keeps one.
#
TUPLE_STANDALONE  = ('requirement', 'logical_component', 'interface_control_document')

# The suffixes of the files that the extractor reads as a whole, and
# some it reads only for a comment header.
#
TUPLE_SUFFIX      = ('.yaml', '.py', '.lp', '.sh', '.js', '.css', '')


# -----------------------------------------------------------------------------
def _words(text: str) -> dict:
    """
    Return the YAML document that text holds, with each prose field as
    its words, since a layout refills prose and keeps only its words.

    """

    document = ruamel.yaml.YAML(typ = 'safe').load(text)
    return {key: (' '.join(value.split()) if key in cctool.edit.layout.SET_KEY_PROSE
                  and isinstance(value, str) else value)
            for (key, value) in document.items()}


# -----------------------------------------------------------------------------
@functools.cache
def _standalone() -> list[str]:
    """
    Return the ids of the items of the repository in the folders of
    TUPLE_STANDALONE, which a copy made for a test holds too.

    """

    return sorted(
        item for (item, _, _, file, _) in cctool.graph.extract.extract(DIR_REPO)['item']
        if any(file.startswith('_data/{folder}/'.format(folder = folder))
               for folder in TUPLE_STANDALONE))


# -----------------------------------------------------------------------------
@hypothesis.example(document = {'brief': ''})
@hypothesis.given(document = DOCUMENT)
def test_a_layout_of_a_layout_is_the_same_and_keeps_the_data(document):
    text = '\n'.join(cctool.edit.layout.dump(document, 0)) + '\n'
    try:
        laid_out = cctool.edit.layout.format(text)
    except cctool.edit.layout.Unsupported:
        hypothesis.reject()
    assert cctool.edit.layout.format(laid_out) == laid_out
    assert _words(laid_out) == _words(text)


# -----------------------------------------------------------------------------
@pytest.mark.slow
@HEAVY
@hypothesis.given(data = strategies.data())
def test_a_rename_undone_gives_back_the_tree(tree, data):
    list_id = _standalone()
    id_old  = data.draw(strategies.sampled_from(list_id))
    prefix  = id_old.partition('_')[0]
    id_new  = data.draw(WORD.map(lambda word: '{prefix}_{word}'.format(prefix = prefix,
                                                                     word   = word)))
    hypothesis.assume(id_new not in list_id)

    edited = cctool.edit.edit.Tree(tree)
    cctool.edit.edit.batch(edited, [{'rename': [id_old, id_new]},
                                    {'rename': [id_new, id_old]}])
    for (relative, text) in edited.edit.items():
        path = tree / relative
        if text is None:
            assert not path.exists()
        else:
            assert path.exists() and path.read_text() == text, relative


# -----------------------------------------------------------------------------
@hypothesis.given(text = strategies.text(max_size = 400),
                  suffix = strategies.sampled_from(TUPLE_SUFFIX))
def test_a_file_of_any_text_is_read_or_reported_unreadable(tmp_path, text, suffix):
    relative = pathlib.Path('_data', 'item' + suffix)
    path     = tmp_path / relative
    path.parent.mkdir(exist_ok = True)
    path.write_text(text, encoding = 'utf-8')
    with contextlib.suppress(cctool.graph.extract.ErrorRead):
        cctool.graph.extract.read(path, relative)


# -----------------------------------------------------------------------------
@HEAVY
@hypothesis.example(title = 'Add 0\r', brief = '0')
@hypothesis.given(title = strategies.from_regex(
                      r'(Add|Remove|Fix [a-z ]{1,20} so that) [^ \n][^\n]{0,40}[^.\n]',
                      fullmatch = True),
                  brief = TEXT.filter(str.strip))
def test_a_message_that_message_new_prints_passes_message_check(tmp_path, title, brief):
    runner = click.testing.CliRunner()
    result = runner.invoke(cctool.cli.command.main,
                           ['message', 'new', title, '--brief', brief,
                            '--root', str(DIR_REPO)])
    hypothesis.assume(result.exit_code == 0)
    path   = tmp_path / 'COMMIT_EDITMSG'
    path.write_text(result.stdout, encoding = 'utf-8')
    result = runner.invoke(cctool.cli.command.main,
                           ['message', 'check', str(path), '--root', str(DIR_REPO)])
    assert result.exit_code == 0, result.output


# -----------------------------------------------------------------------------
@hypothesis.given(data = strategies.data())
def test_a_citation_of_a_part_a_file_holds_is_not_reported(data):
    map_file  = cctool.check.citation.files(DIR_REPO)
    list_file = sorted(file for (written, file) in map_file.items()
                       if written == file and file.startswith(('src/', '_data/register/'))
                       and cctool.check.citation.parts(DIR_REPO, file))
    file      = data.draw(strategies.sampled_from(list_file))
    part      = data.draw(strategies.sampled_from(
                              sorted(cctool.check.citation.parts(DIR_REPO, file))))
    hypothesis.assume(re.fullmatch(r'[\w$][\w$.-]*[\w$]|[\w$]', part))
    connect   = 'within' if file.endswith(('.py', '.lp', '.sh')) else 'at'
    before    = data.draw(TEXT.filter(lambda text: not text.rstrip().endswith(('/', '.', ':'))))
    text      = '{before} ({file} {connect} {part}).'.format(before  = before,
                                                            file    = file,
                                                            connect = connect,
                                                            part    = part)
    document  = {'id_self': 'item_x', 'brief': text, 'edge': []}
    (_, list_name) = cctool.check.citation.violations(DIR_REPO,
                                                      {'_data/item.yaml': (document, 1)})
    assert [row for row in list_name if row[3] == file] == []


# -----------------------------------------------------------------------------
@hypothesis.given(revision = strategies.from_regex(r'[0-9a-f]{7,12}', fullmatch = True),
                  number   = strategies.integers(min_value = 1, max_value = 9999))
def test_a_citation_of_a_file_in_a_commit_is_not_read(revision, number):
    text     = 'It was so ({revision}:src/cctool/check/check.py line {number}).'.format(
                   revision = revision, number = number)
    document = {'id_self': 'item_x', 'brief': text, 'edge': []}
    assert cctool.check.citation.violations(DIR_REPO, {'_data/item.yaml': (document, 1)}) \
        == ([], [])
