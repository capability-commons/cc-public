"""
---

id_self:                pym_cc_public.evidence
guid_self:              pym_b3aa2f235f4a42749db6ef939d90a456
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Evidence
brief:                  |
                        Write what an observer found about a
                        requirement, stamped with what it was observed
                        against.
description:            |
                        Turns an observation into rows on an evidence
                        item: the outcome of a case over its collected
                        instances, the requirement it verifies, and
                        the digest of the requirement, its
                        implementation and the case as they were. The
                        pytest adapter hands it a session's outcomes
                        by node id; cctool attest hands it a person's
                        finding. Rows replace rows for the same case
                        and requirement, so a partial run observes
                        only what it ran.
relation:               []

...
"""


import datetime
import hashlib
import pathlib

import ruamel.yaml.scalarstring

import cc_public.check.evidence
import cc_public.control
import cc_public.edit.field
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.load
import cc_public.load.git
import cc_public.trace


ID_TYPE          = 't_verification_evidence'
DIR_EVIDENCE     = 'evidence'
ID_PYTEST        = 'evd_pytest'
ID_ATTESTATION   = 'evd_attestation'

KEY_CASE         = 'case'
KEY_METHOD       = 'method'
KEY_OBSERVER     = 'observer'
KEY_REVISION     = 'revision'
KEY_DIRTY        = 'is_dirty'
KEY_TIME         = 'time'

METHOD_TEST      = 'test'

OUTCOME_PASSED   = 'passed'
OUTCOME_FAILED   = 'failed'
OUTCOME_ERROR    = 'error'
OUTCOME_SKIPPED  = 'skipped'
OUTCOME_NOT_RUN  = 'not_run'

# What each outcome outranks: one instance that errs makes the case
# err, one that fails makes it fail, and one skipped leaves a hole a
# pass cannot fill.
#
RANK             = (OUTCOME_ERROR, OUTCOME_FAILED, OUTCOME_SKIPPED, OUTCOME_PASSED)

FORMAT_TIME      = '%Y-%m-%dT%H:%M:%SZ'
LENGTH_KEY       = cc_public.control.LENGTH_KEY


# -----------------------------------------------------------------------------
def outcome_of(list_outcome):
    """
    Return (outcome, count_collected, count_passed) for one case over
    the outcomes of its collected instances.

    No instance at all is not_run: nothing observed is not a pass.

    """

    list_outcome = list(list_outcome)

    if not list_outcome:
        return (OUTCOME_NOT_RUN, 0, 0)

    outcome = next(o for o in RANK if o in list_outcome)

    return (outcome, len(list_outcome), list_outcome.count(OUTCOME_PASSED))


# -----------------------------------------------------------------------------
def key_of(guid_case, guid_requirement):
    """
    Return the local name of the row for this case and requirement.

    """

    text = '{case}|{req}'.format(case = guid_case or '', req = guid_requirement)

    return 'c' + hashlib.sha256(text.encode('utf-8')).hexdigest()[:LENGTH_KEY]


# -----------------------------------------------------------------------------
def head(root):
    """
    Return (revision, is_dirty) for the repository at root: the commit
    checked out, and whether anything but evidence has changed since.

    """

    try:
        revision = cc_public.load.git.git(root, 'rev-parse', 'HEAD').strip()
        status   = cc_public.load.git.git(root, 'status', '--porcelain',
                                          '--untracked-files=all')
    except cc_public.load.git.ErrorGit:
        return (None, True)

    is_dirty = any(line[3:].split('/', 1)[0] != DIR_EVIDENCE
                   for line in status.splitlines() if len(line) > 3)

    return (revision, is_dirty)


# -----------------------------------------------------------------------------
def now():
    """
    Return the time, as evidence records it.

    """

    return datetime.datetime.now(datetime.UTC).strftime(FORMAT_TIME)


# -----------------------------------------------------------------------------
def row(tree, guid_requirement, outcome, guid_case = None, **extra):
    """
    Return one evidence row, stamped with the digest of what it was
    observed against.

    """

    map_document = tree.context.map_document
    index        = {d.get('guid_self'): d.get('id_self') for d in map_document.values()
                    if isinstance(d, dict)}
    out          = {'id_requirement':   index.get(guid_requirement),
                    'guid_requirement': guid_requirement,
                    'outcome':          outcome,
                    'digest':           cc_public.check.evidence.digest(
                                            map_document, guid_requirement, guid_case),
                    'time':             now()}
    if guid_case is not None:
        out = {'id_case': index.get(guid_case), 'guid_case': guid_case, **out}

    for (key, value) in extra.items():
        if value is not None and value != '':
            out[key] = value

    return out


# -----------------------------------------------------------------------------
def record(tree, id_item, method, observer, list_row, title):
    """
    Write the rows into the evidence item id_item, making it where it
    is absent, and return its file.

    A row replaces the row for the same case and requirement; rows for
    other cases stay, since a partial run observes only what it ran.

    """

    if id_item not in tree.map_id:
        cc_public.edit.new.new(tree, ID_TYPE, id_item, tree.defaults(),
                               dirpath_out = tree.root / DIR_EVIDENCE)
        cc_public.edit.field.set_field(tree, id_item, 'title', value = title)
        cc_public.edit.field.set_field(tree, id_item, 'brief', prose =
            'What {observer} observed about the requirements verified by '
            '{method}.\n'.format(observer = observer, method = method))
        cc_public.edit.field.set_field(tree, id_item, 'description', prose =
            'One row per case and requirement, each stamped with the digest '
            'of the requirement, the code implementing it and the case as they '
            'were when observed, so that the evidence check can say whether '
            'the observation still applies. Rewritten by each observation; '
            'the history is in git.\n')

    item     = tree.resolve(id_item)
    document = tree.context.map_document[item.location]
    table    = dict(document.get(KEY_CASE) or {})
    is_same  = True

    # A row that says what the row before it said, time aside, is the
    # same observation again and leaves the item as it was, so that a
    # run that changes nothing dirties nothing.
    #
    for one in list_row:
        key = key_of(one.get('guid_case'), one['guid_requirement'])
        if _observed(table.get(key)) == _observed(one):
            continue
        table[key] = _blocks(one)
        is_same    = False

    if is_same and document.get(KEY_METHOD) == method \
            and document.get(KEY_OBSERVER) == observer:
        return item.filepath

    (revision, is_dirty) = head(tree.root)

    for (key, value) in ((KEY_METHOD, method), (KEY_OBSERVER, observer),
                         (KEY_REVISION, revision), (KEY_DIRTY, is_dirty),
                         (KEY_TIME, now()), (KEY_CASE, table)):
        if value is not None:
            cc_public.edit.field.set_field(tree, id_item, key, value = value)

    return item.filepath


# -----------------------------------------------------------------------------
def from_pytest(root, map_outcome, version):
    """
    Turn what a pytest session observed into evidence and write it.
    Return the file written, or None where no collected test is an item.

    map_outcome maps a node id, test/x.py::Class::name[param], to the
    outcome of that instance. Instances of one function are one case;
    a function that is not an item is not a case anything names, and
    is passed over.

    """

    tree         = cc_public.edit.tree.Tree([root])
    map_document = tree.context.map_document
    map_case     = {}                                # guid_case -> [outcome]

    for (nodeid, outcome) in map_outcome.items():
        guid = _guid_of(tree, root, nodeid)
        if guid is not None:
            map_case.setdefault(guid, []).append(outcome)

    if not map_case:
        return None

    map_guid = {r.id_self: r for r in cc_public.trace.projection(map_document)}
    list_row = []

    for (guid_case, list_outcome) in sorted(map_case.items()):
        (outcome, collected, passed) = outcome_of(list_outcome)
        id_case = tree.map_guid[guid_case].id_self
        for record_req in map_guid.values():
            if id_case in record_req.verified_by:
                list_row.append(row(tree, record_req.guid_self, outcome, guid_case,
                                    count_collected = collected, count_passed = passed))

    if not list_row:
        return None

    return record(tree, ID_PYTEST, METHOD_TEST, 'pytest ' + version, list_row,
                  'Pytest evidence')


# -----------------------------------------------------------------------------
def attest(tree, name_requirement, outcome, observer, note = None):
    """
    Record that observer found the requirement met or not by the
    method it declares, which is not test, and return the file written.

    """

    item     = tree.resolve(name_requirement)
    document = tree.context.map_document[item.location]
    method   = document.get('verification')

    if not method or method == METHOD_TEST:
        raise cc_public.edit.tree.ErrorItem(
                '{req} is verified by {method}, and an attestation stands for '
                'inspection, demonstration or analysis; a test observes itself.'.format(
                        req = item.id_self, method = method or 'nothing'))

    one = row(tree, item.guid_self, outcome, observer = observer, note = note)

    return record(tree, ID_ATTESTATION, method, 'attestation', [one], 'Attestations')


# -----------------------------------------------------------------------------
def _guid_of(tree, root, nodeid):
    """
    Return the guid of the function item a pytest node id names, or None.

    """

    (path, *names) = nodeid.split('::')

    if not names:
        return None

    names[-1] = names[-1].split('[', 1)[0]
    location  = cc_public.load.Location((pathlib.Path(root) / path).resolve(), tuple(names))
    document  = tree.context.map_document.get(location)

    return document.get('guid_self') if isinstance(document, dict) else None


# -----------------------------------------------------------------------------
def _observed(row):
    """
    Return what a row observed, which is everything in it but when.

    """

    if not isinstance(row, dict):
        return None

    return {k: str(v).strip() for (k, v) in row.items() if k != KEY_TIME}


# -----------------------------------------------------------------------------
def _blocks(one):
    """
    Return the row with any multi line string as a block scalar.

    """

    return {k: (ruamel.yaml.scalarstring.LiteralScalarString(v)
                if isinstance(v, str) and '\n' in v else v)
            for (k, v) in one.items()}
