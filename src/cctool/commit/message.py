"""
---

id_self:                pym_cctool.commit.message
guid_self:              pym_59df4c74e5eb465893caf918d87e7912
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit message
brief:                  |
                        Compose a commit message around a new commit
                        item, and check a message against sch_commit.
description:            |
                        A commit message is the subject line, a blank
                        line, the commit item as a YAML document from
                        --- to ..., and then any trailers. The subject
                        line is the title of the item.

                        A message is checked against sch_commit, which
                        holds the templates a title is built from, as
                        read from the tree. The id must end with the
                        first six hex digits of the guid, which a
                        schema cannot say.

                        A Contributor trailer names the team member
                        who supplied the content of the commit, by the
                        guid of their entry in a team member register.
                        The check fails a guid that no team member
                        register of the tree holds. The team member
                        registers of a tree are reg_team_member, which
                        type_team_member names, and each register that
                        names type_team_member with the inverse of
                        relation_has_items_held_in_register, as one in
                        a peer does, in the tree or in a tree it
                        consumes.

                        The author of a commit is the person
                        responsible for its being correct, so it must
                        be a team member whose entry in a team member
                        register gives that author as its git_author,
                        name and email as git records them. An agent
                        that helped says so in a trailer, and is never
                        the author. A tree whose registers give no
                        git_author predates the rule, and its commits
                        are not checked for it.

                        git drafts the message of a merge or a revert
                        itself, with no item. draft turns such a draft
                        into a message that conforms: it keeps the
                        subject git wrote, adds the branch merged into
                        where git leaves it out, makes the body the
                        brief, and names in the description each item
                        that the commit removes or renames, as the
                        check of the commit requires. Any other
                        message is left as it is.
usage:                  |
                        cctool message new TITLE --brief TEXT

                        cctool message check FILE

                        cctool message draft FILE

                        The commit-msg hook in .githooks runs the
                        check on every commit, and the
                        prepare-commit-msg hook runs draft before it.
edge:                   []

...
"""


import datetime
import pathlib
import re
import subprocess
import uuid

import jsonschema

import cctool.check.layout
import cctool.check.schema
import cctool.check.segment
import cctool.commit.change
import cctool.graph.extract
import cctool.graph.parse
import cctool.graph.prefix


ID_SCHEMA       = 'sch_commit'
PREFIX          = cctool.graph.prefix.MAP_PREFIX['type_commit']
FORMAT_TIME     = '%Y%m%d%H%M%S'
LENGTH_SUFFIX   = 6
MARK_COMMENT    = '#'
LINE_OPEN       = cctool.graph.extract.LINE_OPEN
LINE_CLOSE      = cctool.graph.extract.LINE_CLOSE
KEY_ID_SELF     = cctool.graph.extract.KEY_ID_SELF
KEY_GUID_SELF   = cctool.graph.extract.KEY_GUID_SELF
KEY_TITLE       = 'title'
KEY_BRIEF       = 'brief'
KEY_DESCRIPTION = 'description'
KEY_EDGE        = 'edge'
KEY_ENTRIES     = 'entries'
ID_TYPE_MEMBER  = 'type_team_member'
RELATION_HELD   = 'relation_has_items_held_in_register'
KEY_INVERSE     = 'inverse'
KEY_ID_RELATION = 'id_relation'
KEY_ID_TARGET   = 'id_target'
KEY_GIT_AUTHOR  = 'git_author'
KEY_SIGNING_KEY = 'git_signing_key'

# A trailer that names the team member who supplied the content of the
# commit, by the guid of their register entry.
#
REGEX_CONTRIBUTOR = re.compile(r'^Contributor:\s*(.*?)\s*$')

# The name and email at the head of an identity as git var
# GIT_AUTHOR_IDENT gives it, before the time and the zone.
#
REGEX_IDENT     = re.compile(r'^(.*?<[^>]*>)')

# The letters git gives for the signature of a commit, as %G? prints
# them: G and U are good signatures, and the rest are said in words.
#
SET_STATUS_GOOD = {'G', 'U'}
MAP_STATUS      = {'N': 'is not signed',
                   'B': 'has a bad signature',
                   'X': 'is signed with a key that has expired',
                   'Y': 'is signed with a key that has since expired',
                   'R': 'is signed with a key that is revoked',
                   'E': 'has a signature that git cannot check, as its key is not in the keyring'}

# The subject lines that git drafts for a merge and for a revert. A
# merge into the main branch is drafted without the branch it is into.
#
REGEX_MERGE     = re.compile(r'^Merge (branch|branches|remote-tracking branch|tag|commit) [^ ]')
REGEX_INTO      = re.compile(r' into [^ ]+$')
REGEX_REVERT    = re.compile(r'^(Revert|Reapply) "(.+)"$')

# A title is at most this long. A revert of a long title quotes as much
# of it as fits, and the brief names the commit it reverts.
#
LENGTH_TITLE    = 80
MARK_CUT        = '...'


# -----------------------------------------------------------------------------
class ErrorMessage(Exception):
    """
    The message cannot be read as a subject line and a commit item.

    """


# -----------------------------------------------------------------------------
def compose(title:       str,
            brief:       str,
            description: str | None = None,
            now:         datetime.datetime | None = None) -> str:
    """
    Return a commit message whose item has title, brief and
    description, with an id and a guid minted for it.

    """

    hex_guid = uuid.uuid4().hex
    time     = (now or datetime.datetime.now(datetime.UTC)).strftime(FORMAT_TIME)
    item     = {KEY_ID_SELF:   '{prefix}_{time}_{suffix}'.format(prefix = PREFIX,
                                                                 time   = time,
                                                                 suffix = hex_guid[:LENGTH_SUFFIX]),
                KEY_GUID_SELF: '{prefix}_{hex}'.format(prefix = PREFIX, hex = hex_guid),
                KEY_TITLE:     title,
                KEY_BRIEF:     brief}

    if description:
        item[KEY_DESCRIPTION] = description
    item[KEY_EDGE] = []

    body = cctool.check.layout.format(
                '\n'.join(cctool.check.layout.dump(item, 0)) + '\n')

    return '{title}\n\n{open}\n\n{body}\n{close}\n'.format(title = title,
                                                           open  = LINE_OPEN,
                                                           body  = body,
                                                           close = LINE_CLOSE)


# -----------------------------------------------------------------------------
def draft(root: pathlib.Path, text: str) -> str:
    """
    Return the message text, as git drafted it for a commit of the
    staged content of the repository at root, made into one that
    conforms if git drafted it for a merge or a revert and it has no
    item. Any other message is returned as it is.

    """

    list_line    = text.split('\n')
    list_kept    = [line for line in list_line if not line.startswith(MARK_COMMENT)]
    list_comment = [line for line in list_line if line.startswith(MARK_COMMENT)]
    subject      = list_kept[0].strip() if list_kept else ''
    body         = '\n'.join(list_kept[1:]).strip()

    if LINE_OPEN in (line.strip() for line in list_kept[1:]):
        return text

    if REGEX_MERGE.match(subject):
        if not REGEX_INTO.search(subject):
            subject = '{subject} into {branch}'.format(subject = subject, branch = _branch(root))
    elif REGEX_REVERT.match(subject):
        subject = _fitted(subject)
    else:
        return text

    item        = {KEY_TITLE: subject, KEY_BRIEF: body or subject + '.'}
    failures    = cctool.commit.change.check(root, item)
    list_part   = []
    list_remove = sorted(row[0] for row in failures.get('unannounced_removal', []))
    list_rename = sorted(failures.get('unannounced_rename', []))

    if list_remove:
        list_part.append('It removes {list}.'.format(list = ', '.join(list_remove)))
    if list_rename:
        list_part.append('It renames {list}.'.format(
                            list = ', '.join('{old} to {new}'.format(old = old, new = new)
                                             for (old, new) in list_rename)))

    message = compose(subject, item[KEY_BRIEF], ' '.join(list_part) or None)

    return message + ''.join('\n' + line for line in list_comment)


# -----------------------------------------------------------------------------
def _branch(root: pathlib.Path) -> str:
    """
    Return the name of the branch checked out in the repository at
    root, which a merge is made into.

    """

    return subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                          cwd            = root,
                          capture_output = True,
                          text           = True,
                          check          = True).stdout.strip()


# -----------------------------------------------------------------------------
def _fitted(subject: str) -> str:
    """
    Return the subject line of a revert, with the title it quotes cut
    to fit in the length of a title.

    """

    if len(subject) <= LENGTH_TITLE:
        return subject

    (verb, quoted) = REGEX_REVERT.match(subject).groups()
    room           = LENGTH_TITLE - len(verb) - len(' ""') - len(MARK_CUT)

    return '{verb} "{quoted}{cut}"'.format(verb = verb, quoted = quoted[:room], cut = MARK_CUT)


# -----------------------------------------------------------------------------
def parse(text: str) -> tuple[str, dict]:
    """
    Return the subject line of the commit message text, and the commit
    item it holds. Lines that git treats as comments are left out.

    """

    list_line = [line for line in text.split('\n') if not line.startswith(MARK_COMMENT)]

    if len(list_line) < 3 or list_line[1] != '' or list_line[2] != LINE_OPEN:
        raise ErrorMessage('A commit message is a subject line, a blank line, and then the '
                           'commit item, opened by {open}.'.format(open = LINE_OPEN))
    if LINE_CLOSE not in list_line:
        raise ErrorMessage('The commit item is not closed by {close}.'.format(close = LINE_CLOSE))

    end = list_line.index(LINE_CLOSE)

    try:
        item = cctool.graph.parse.load('\n'.join(list_line[2:end + 1]))
    except cctool.graph.parse.ERROR as error:
        raise ErrorMessage('The commit item is not YAML: {error}'.format(
                                            error = ' '.join(str(error).split()))) from error

    if not isinstance(item, dict):
        raise ErrorMessage('The commit item is not a mapping.')

    return (list_line[0], item)


# -----------------------------------------------------------------------------
def violations(root: pathlib.Path, text: str) -> list[str]:
    """
    Return a sentence for each way the commit message text fails
    sch_commit, as the tree at root or a tree it consumes holds it, or
    fails to match its own subject line and guid.

    """

    try:
        (subject, item) = parse(text)
    except ErrorMessage as error:
        return [str(error)]

    map_document = cctool.check.segment.union(root)
    list_schema  = [document for (document, _) in map_document.values()
                    if isinstance(document, dict)
                    and cctool.check.schema.KEY_ID_SCHEMA in document
                    and cctool.check.schema.META.is_valid(document)]
    map_schema   = {str(schema.get(KEY_ID_SELF)): schema for schema in list_schema}

    if ID_SCHEMA not in map_schema:
        return ['{id} cannot be found in the tree.'.format(id = ID_SCHEMA)]

    validator = cctool.check.schema.Validator(
                    map_schema[ID_SCHEMA],
                    registry = cctool.check.schema.registry_of(list_schema))

    list_found = [_sentence(error) for error in cctool.check.schema.errors(validator, item)]

    if not str(item.get(KEY_TITLE, '')).isprintable():
        list_found.append('The title holds a line break, a tab or another character that '
                          'is not printed.')
    elif item.get(KEY_TITLE) != subject:
        list_found.append('The subject line is not the title of the commit item.')

    id_self   = str(item.get(KEY_ID_SELF, ''))
    guid_self = str(item.get(KEY_GUID_SELF, ''))
    suffix    = guid_self.partition('_')[2][:LENGTH_SUFFIX]
    if not (suffix and id_self.endswith('_' + suffix)):
        list_found.append('The id does not end with the first {count} hex digits of the '
                          'guid.'.format(count = LENGTH_SUFFIX))

    set_member = _members(map_document)
    for guid in contributors(text):
        if guid not in set_member:
            list_found.append('The Contributor trailer names {guid}, which no team member '
                              'register holds.'.format(guid = guid or 'no guid'))

    return sorted(set(list_found), key = list_found.index)


# -----------------------------------------------------------------------------
def author_violations(root: pathlib.Path, ident: str) -> list[str]:
    """
    Return a sentence if ident, the author of a commit as git gives it,
    such as 'Name <email> 1767225600 +0000', is not the git_author of
    a team member that a team member register of the tree at root
    holds. Registers that give no git_author check nothing.

    """

    set_author = _authors(cctool.check.segment.union(root))
    match      = REGEX_IDENT.match(ident.strip())
    author     = match.group(1) if match else ident.strip()

    if not set_author or author in set_author:
        return []

    return ['The commit is authored by {author}, who is not the git_author of a team member '
            'that a team member register holds. Commit as the member responsible for the '
            'change, and name an agent that helped in a Co-Authored-By trailer.'.format(
                author = author or 'no one')]


# -----------------------------------------------------------------------------
def signature_violations(root: pathlib.Path, status: str, list_key: list[str]) -> list[str]:
    """
    Return a sentence if a commit is not signed with the git_signing_key
    of a team member that a team member register of the tree at root
    holds.
    status is the letter git gives for its signature, as %G? prints
    it, and list_key the ids and fingerprints of the key that made it,
    as %GK, %GF and %GP print them. Registers that give no
    git_signing_key check nothing.

    git gives G for a good signature, and U for a good one by a key
    whose owner the keyring does not vouch for; either is a signature
    by the key it names. Any other letter is no signature that can be
    trusted to be one.

    """

    set_key = _signing_keys(cctool.check.segment.union(root))

    if not set_key:
        return []
    if status not in SET_STATUS_GOOD:
        return ['The commit {state}, and a team member that a team member register holds signs '
                'each commit with their git_signing_key. Sign it with git commit --amend -S, '
                'or several with git rebase --force-rebase -S.'.format(
                    state = MAP_STATUS.get(status, 'has a signature git cannot verify'))]
    if any(key.upper().endswith(member) for key in list_key if key for member in set_key):
        return []

    key = next((key for key in list_key if key), 'unknown')

    return ['The commit is signed with the key {key}, which is the git_signing_key of no team '
            'member that a team member register holds.'.format(key = key)]


# -----------------------------------------------------------------------------
def contributors(text: str) -> list[str]:
    """
    Return the guid that each Contributor trailer of the commit message
    text names, in order. Trailers follow the commit item.

    """

    list_line = [line for line in text.split('\n') if not line.startswith(MARK_COMMENT)]

    if LINE_CLOSE not in list_line:
        return []

    end = list_line.index(LINE_CLOSE)

    return [match.group(1) for match in map(REGEX_CONTRIBUTOR.match, list_line[end + 1:])
            if match]


# -----------------------------------------------------------------------------
def _members(map_document: dict) -> set[str]:
    """
    Return the guid of each team member that a team member register in
    map_document holds.

    """

    return {str(entry.get(KEY_GUID_SELF)) for entry in _member_entries(map_document)}


# -----------------------------------------------------------------------------
def _authors(map_document: dict) -> set[str]:
    """
    Return the git_author of each team member that a team member
    register in map_document holds.

    """

    return {str(entry[KEY_GIT_AUTHOR]) for entry in _member_entries(map_document)
            if entry.get(KEY_GIT_AUTHOR)}


# -----------------------------------------------------------------------------
def _signing_keys(map_document: dict) -> set[str]:
    """
    Return the git_signing_key of each team member that a team member
    register in map_document holds, in capitals.

    """

    return {str(entry[KEY_SIGNING_KEY]).upper() for entry in _member_entries(map_document)
            if entry.get(KEY_SIGNING_KEY)}


# -----------------------------------------------------------------------------
def _member_entries(map_document: dict) -> list[dict]:
    """
    Return each team member entry that a team member register in
    map_document holds: the register that type_team_member names with
    relation_has_items_held_in_register, and each register that names
    type_team_member with its inverse, as a register in a peer does.

    """

    list_document = [document for (document, _) in map_document.values()
                     if isinstance(document, dict)]
    list_entry    = [entry for document in list_document for entry in _entries(document)]
    set_inverse   = {str(entry[KEY_INVERSE].get(KEY_ID_SELF)) for entry in list_entry
                     if entry.get(KEY_ID_SELF) == RELATION_HELD
                     and isinstance(entry.get(KEY_INVERSE), dict)}
    set_register  = {str(edge.get(KEY_ID_TARGET)) for entry in list_entry
                     if entry.get(KEY_ID_SELF) == ID_TYPE_MEMBER
                     for edge in _edges(entry)
                     if edge.get(KEY_ID_RELATION) == RELATION_HELD}

    return [entry for document in list_document
            if document.get(KEY_ID_SELF) in set_register
            or any(edge.get(KEY_ID_RELATION) in set_inverse
                   and edge.get(KEY_ID_TARGET) == ID_TYPE_MEMBER for edge in _edges(document))
            for entry in _entries(document)]


# -----------------------------------------------------------------------------
def _entries(document: dict) -> list[dict]:
    """
    Return the entries that the register document holds, or none if it
    is not a register.

    """

    map_entry = document.get(KEY_ENTRIES)
    if not isinstance(map_entry, dict):
        return []
    return [entry for entry in map_entry.values() if isinstance(entry, dict)]


# -----------------------------------------------------------------------------
def _edges(item: dict) -> list[dict]:
    """
    Return the edges of item that are mappings.

    """

    list_edge = item.get(KEY_EDGE)
    if not isinstance(list_edge, list):
        return []
    return [edge for edge in list_edge if isinstance(edge, dict)]


# -----------------------------------------------------------------------------
def _sentence(error: jsonschema.ValidationError) -> str:
    """
    Return a sentence that reports error, found in a commit item.

    """

    list_part = list(error.absolute_path)

    if list_part == [KEY_TITLE] and error.validator == 'pattern':
        return 'The title is not built from a template in {id}: {title}'.format(
                                                        id = ID_SCHEMA, title = error.instance)

    return '{path}: {message}'.format(path    = '/'.join(map(str, list_part)) or 'item',
                                      message = ' '.join(error.message.split()))

