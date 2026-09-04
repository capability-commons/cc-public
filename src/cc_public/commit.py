"""
---

id_self:                pym_cc_public.commit
guid_self:              pym_d1a0197b9dd444b4a74a5a294a070a0d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit
brief:                  |
                        Commit the working tree with a commit record
                        in the message.
description:            |
                        Runs the checks, mints the record, validates
                        it against its schema, stages what changed and
                        commits. What changed is not written into the
                        record; the diff says it. A critical finding
                        refuses the commit unless a checkpoint is
                        asked for, in which case the record says so.

...
"""


import datetime
import io
import subprocess
import uuid

import ruamel.yaml
import ruamel.yaml.comments

import cc_public.check
import cc_public.check.schema
import cc_public.edit.tree
import cc_public.layout


PREFIX          = 'cmt'
ID_SCHEMA       = 'sch_commit'
ID_TYPE_COMMIT  = 't_commit'
ID_TYPE_REL     = 't_relation'
KEY_TABLE       = 'table'

STATUS_CLEAN    = 'clean'
STATUS_CHECKPT  = 'checkpoint'

REL_RESULTS     = 'r_results_from'

MARKER_OPEN     = '---'
MARKER_CLOSE    = '...'

LENGTH_GUID_TAG = 6

FORMAT_STAMP    = '%Y%m%d%H%M%S'


# -----------------------------------------------------------------------------
class ErrorCommit(Exception):
    """
    Raised where a commit cannot be made as asked.

    """

    pass


# -----------------------------------------------------------------------------
def changed(root):
    """
    Return [(status, path)] for every path the working tree has changed,
    untracked files included, renames as their new path.

    """

    text = _git(root, 'status', '--porcelain', '--untracked-files=all')
    out  = []

    for line in text.splitlines():

        if len(line) < 4:
            continue

        (status, path) = (line[:2], line[3:])

        if ' -> ' in path:
            path = path.split(' -> ', 1)[1]

        out.append((status.strip() or '?', path))

    return out


# -----------------------------------------------------------------------------
def commit(root, title, brief = None, description = None,
           is_checkpoint = False, id_execution = None, list_trailer = (),
           list_link = ()):
    """
    Make the record, commit everything that changed, and return
    (hash, id_self).

    """

    root = root.resolve()

    if not (root / '.git').exists():
        raise ErrorCommit('{root} is not the root of a git repository.'.format(
                                                                root = root))

    list_changed = changed(root)

    if not list_changed:
        raise ErrorCommit('Nothing has changed, so there is nothing to commit.')

    report   = cc_public.check.check(list_path = [root])['report']
    count    = {'count':    len(report['check']),
                'critical': sum(1 for c in report['check']
                                  for n in c['nonconformity']
                                  if n['severity'] == 'critical'),
                'advisory': sum(1 for c in report['check']
                                  for n in c['nonconformity']
                                  if n['severity'] == 'advisory')}

    if count['critical'] and not is_checkpoint:
        raise ErrorCommit(
            '{n} critical finding(s). A commit with the checks failing is a '
            'checkpoint; ask for one with --checkpoint and it will be '
            'recorded as such.'.format(n = count['critical']))

    tree     = cc_public.edit.tree.Tree([root])
    document = record(tree, title, brief, description,
                      STATUS_CHECKPT if is_checkpoint else STATUS_CLEAN,
                      count, id_execution, list_link)

    text = message(document, list_trailer)

    _git(root, 'add', '-A', '--', *[path for (_, path) in list_changed])
    _git(root, 'commit', '--quiet', '-F', '-', input = text)

    return (_git(root, 'rev-parse', 'HEAD').strip(), document['id_self'])


# -----------------------------------------------------------------------------
def record(tree, title, brief, description, status, count, id_execution,
           list_link):
    """
    Return the commit record as a document, validated.

    What the commit changed is not recorded: the diff says it, exactly
    and for nothing. The record carries what the diff cannot -- why,
    in what state, and what the commit relates to on purpose.

    """

    guid  = PREFIX + '_' + uuid.uuid4().hex
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(FORMAT_STAMP)

    document = ruamel.yaml.comments.CommentedMap()
    document['id_self']     = '{prefix}_{stamp}_{tag}'.format(
                                    prefix = PREFIX, stamp = stamp,
                                    tag    = guid.split('_', 1)[1][:LENGTH_GUID_TAG])
    document['guid_self']   = guid
    document['title']       = title
    document['brief']       = ruamel.yaml.scalarstring.LiteralScalarString(
                                    (brief or title).rstrip('\n') + '\n')
    document['description'] = ruamel.yaml.scalarstring.LiteralScalarString(
                                    (description or title).rstrip('\n') + '\n')
    document['status']      = status

    check = ruamel.yaml.comments.CommentedMap()
    for key in ('count', 'critical', 'advisory'):
        check[key] = count[key]
    document['check'] = check

    table = tree.relation_register()[KEY_TABLE]
    edges = ruamel.yaml.comments.CommentedSeq()

    if id_execution is not None:
        edges.append(_edge(REL_RESULTS, table, tree.resolve(id_execution)))

    for (id_relation, name_target) in list_link:
        if id_relation not in table:
            raise ErrorCommit('{rel} is not in the relation register.'.format(
                                                            rel = id_relation))
        edges.append(_edge(id_relation, table, tree.resolve(name_target)))

    document['relation'] = edges

    # Validated as any item is, once, here.
    #
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema._registry(map_schema)
    list_error = cc_public.check.schema._validate(
                        _plain(document), map_schema[ID_SCHEMA], registry)

    if list_error:
        raise ErrorCommit('The commit record is not valid: {err}'.format(
                                    err = '; '.join(m for (_, m) in list_error)))

    return document


# -----------------------------------------------------------------------------
def message(document, list_trailer = ()):
    """
    Return the commit message: the title, then the record between its
    markers, laid out by the printer, then any trailers.

    """

    stream = io.StringIO()
    ruamel.yaml.YAML(typ = 'rt').dump(document, stream)

    body = cc_public.layout.format(stream.getvalue())
    text = (document['title'] + '\n\n' + MARKER_OPEN + '\n\n' + body + '\n'
            + MARKER_CLOSE + '\n')

    if list_trailer:
        text += '\n' + '\n'.join(list_trailer) + '\n'

    return text


# -----------------------------------------------------------------------------
def _edge(id_relation, table, item):
    """
    Return one four field edge.

    """

    edge = ruamel.yaml.comments.CommentedMap()
    edge['id_relation']   = id_relation
    edge['guid_relation'] = table[id_relation]['guid_self']
    edge['id_target']     = item.id_self
    edge['guid_target']   = item.guid_self

    return edge


# -----------------------------------------------------------------------------
def _plain(node):
    """
    Return node as plain python, for the validator.

    """

    if isinstance(node, dict):
        return {k: _plain(v) for (k, v) in node.items()}
    if isinstance(node, list):
        return [_plain(v) for v in node]
    return str(node) if isinstance(node, ruamel.yaml.scalarstring.ScalarString) \
                     else node


# -----------------------------------------------------------------------------
def _git(root, *args, input = None):
    """
    Run one git command at root and return its output.

    """

    done = subprocess.run(['git', '-C', str(root), *args],
                          capture_output = True, text = True, input = input)

    if done.returncode != 0:
        raise ErrorCommit('git {args}: {err}'.format(
                                    args = ' '.join(args[:2]),
                                    err  = done.stderr.strip()))

    return done.stdout
