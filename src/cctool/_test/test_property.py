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
                        prints passes message check, a citation of a
                        part that a file holds is never reported, and
                        the fast check of a schema finds a document of
                        the tree, however changed, to conform only if
                        jsonschema does, and a layout of a text read
                        by the fast reader is that of a ruamel.yaml
                        read.

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
import copy
import functools
import os
import pathlib
import re
import string

import click.testing
import pytest
import ruamel.yaml

import cctool.check.check
import cctool.check.citation
import cctool.check.schema
import cctool.cli.command
import cctool.commit.message
import cctool.conftest
import cctool.edit.edit
import cctool.edit.layout
import cctool.gate.gate
import cctool.graph.extract
import cctool.graph.logic
import cctool.graph.parse


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
# checks the tree twice, about 50 s an example, so it makes fewer still
# and is marked slow, and the gate of a push leaves it out.
#
COUNT_HEAVY       = {NAME_RUN: 3, NAME_OVERNIGHT: 200}
COUNT_RENAME      = {NAME_RUN: 3, NAME_OVERNIGHT: 20}

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
RENAME            = hypothesis.settings(max_examples = COUNT_RENAME[NAME_PROFILE])


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
VALUE             = strategies.recursive(
                        strategies.one_of(SCALAR, strategies.none(),
                                          strategies.floats(allow_nan = False),
                                          strategies.sampled_from(('', 'a\n', '\ufeff', '\u0661',
                                                                   'mark_public', 'Add x.'))),
                        lambda each: strategies.one_of(strategies.lists(each, max_size = 3),
                                                       strategies.dictionaries(KEY, each,
                                                                               max_size = 3)),
                        max_leaves = 6)
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
@hypothesis.example(document = {'brief': '#', 'title': ''})
@hypothesis.example(document = {'title': '', 'brief': ' 0'})
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
@RENAME
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
def test_a_message_that_message_new_prints_passes_message_check(title, brief):
    runner = click.testing.CliRunner()
    result = runner.invoke(cctool.cli.command.main,
                           ['message', 'new', title, '--brief', brief,
                            '--root', str(DIR_REPO)])
    hypothesis.assume(result.exit_code == 0)
    assert cctool.commit.message.violations(DIR_REPO, result.stdout) == []


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


# -----------------------------------------------------------------------------
@hypothesis.given(document = DOCUMENT)
def test_the_fast_reading_of_a_document_is_that_of_ruamel(document):
    text = '\n'.join(cctool.edit.layout.dump(document, 0)) + '\n'
    assert _lines(cctool.graph.parse.load(text)) == _lines(ruamel.yaml.YAML(typ = 'rt').load(text))


# -----------------------------------------------------------------------------
@hypothesis.example(text = '0\t')
@hypothesis.example(text = '!')
@hypothesis.example(text = '=')
@hypothesis.given(text = strategies.text(max_size = 200))
def test_the_fast_reading_of_any_text_that_ruamel_reads_is_the_same(text):
    try:
        expected = _lines(ruamel.yaml.YAML(typ = 'rt').load(text))
    except ruamel.yaml.YAMLError:
        hypothesis.reject()
    assert _lines(cctool.graph.parse.load(text)) == expected


# -----------------------------------------------------------------------------
@hypothesis.given(data = strategies.data())
def test_the_fast_check_of_a_changed_document_agrees_with_jsonschema(data):
    (map_document, map_file, map_schema, list_pair) = _schema_pairs()
    (id_document, id_schema) = data.draw(strategies.sampled_from(list_pair))
    document = copy.deepcopy(map_document[map_file[id_document]][0])
    list_path = list(_paths(document))
    for _ in range(data.draw(strategies.integers(min_value = 1, max_value = 3))):
        _change(document, data.draw(strategies.sampled_from(list_path)), data)
    set_invalid = {id_each for (id_each, schema) in map_schema.items()
                   if not cctool.check.schema.is_valid(schema)}
    registry    = cctool.check.schema.registry_of([schema for (id_each, schema) in map_schema.items()
                                                   if id_each not in set_invalid])
    validator   = cctool.check.schema.Validator(map_schema[id_schema], registry = registry)
    fast        = cctool.check.schema._Fast(map_schema, set_invalid)
    is_valid    = not cctool.check.schema.errors(validator, document)
    assert fast.is_valid(id_schema, document) == is_valid


# -----------------------------------------------------------------------------
@functools.cache
def _schema_pairs():
    """
    Return the documents of the tree, the file of each, the schemas,
    and each pair of a document and a schema it must conform to.

    """

    map_document = cctool.graph.extract.documents(DIR_REPO)
    facts        = cctool.graph.extract.facts_of(map_document)
    program      = '{rules}\n{show}'.format(
                       rules = cctool.check.check.RULES.read_text(),
                       show  = cctool.graph.logic.show('document_schema',
                                                       cctool.graph.logic.derived()))
    map_file     = {row[0]: row[3] for row in facts['item'] if not row[2]}
    map_schema   = {id_document: map_document[file][0] for (id_document, file) in map_file.items()
                    if isinstance(map_document[file][0], dict)
                    and cctool.check.schema.KEY_ID_SCHEMA in map_document[file][0]}
    list_pair    = sorted(pair for pair in cctool.graph.logic.run(facts, program)['document_schema']
                          if pair[0] in map_file and pair[1] in map_schema)
    return (map_document, map_file, map_schema, list_pair)


# -----------------------------------------------------------------------------
def _paths(node, path = ()):
    """
    Yield the path of each part of node below it.

    """

    if isinstance(node, dict):
        list_each = list(node.items())
    elif isinstance(node, list):
        list_each = list(enumerate(node))
    else:
        return
    for (key, value) in list_each:
        yield (*path, key)
        yield from _paths(value, (*path, key))


# -----------------------------------------------------------------------------
def _change(document, path, data):
    """
    Change the part of document at path, if it is still there: remove
    it, add a field beside it, or put a value drawn from data in its
    place.

    """

    parent = document
    try:
        for part in path[:-1]:
            parent = parent[part]
        parent[path[-1]]
    except (KeyError, IndexError, TypeError):
        return
    choice = data.draw(strategies.sampled_from(('remove', 'add', 'value')))
    if choice == 'remove':
        del parent[path[-1]]
    elif choice == 'add' and isinstance(parent, dict):
        parent[data.draw(WORD)] = data.draw(VALUE)
    else:
        parent[path[-1]] = data.draw(VALUE)


# -----------------------------------------------------------------------------
@hypothesis.example(text = "'a': \"b\"\nc: ['d']\n")
@hypothesis.example(text = '0\t')
@hypothesis.given(text = strategies.one_of(
                             strategies.text(max_size = 200),
                             DOCUMENT.map(lambda document: '\n'.join(
                                              cctool.edit.layout.dump(document, 0)) + '\n')))
def test_the_layout_check_of_a_text_read_fast_is_that_of_a_ruamel_read(text):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(cctool.edit.layout, '_load', cctool.edit.layout.YAML.load)
        expected = cctool.edit.layout._violation('_data/x.yaml', text)
    assert cctool.edit.layout._violation('_data/x.yaml', text) == expected


# -----------------------------------------------------------------------------
def _lines(value):
    """
    Return value with the type, line and column of each part, so that
    two loads compare by all that the extractor reads. A value of
    another type, such as a tagged scalar, compares by its repr.

    """

    if isinstance(value, dict):
        return ('map', [(key, value.lc.key(key), value.lc.value(key), _lines(each))
                        for (key, each) in value.items()])
    if isinstance(value, list):
        return ('seq', [(value.lc.item(index), _lines(each)) for (index, each) in enumerate(value)])
    if isinstance(value, (str, int, float)) or value is None:
        return (type(value).__name__, value)
    return (type(value).__name__, repr(value))
