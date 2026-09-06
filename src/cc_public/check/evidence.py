"""
---

id_self:                pym_cc_public.check.evidence
guid_self:              pym_88b56f85d0a243fa8981a6216238ade1
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Evidence check
brief:                  |
                        Check that every accepted requirement has
                        evidence that is a pass and is current.
description:            |
                        Computes the digest evidence is stamped with,
                        over the requirement as claimed, the source of
                        every item implementing it and the source of
                        the case, and compares each accepted
                        requirement's evidence to it. Absent, or
                        observed and not a pass, is critical in a
                        closed world and advisory in an open one;
                        stale is advisory, since a tree being edited
                        is ordinarily ahead of its last observation.
relation:               []

...
"""


import hashlib
import json

import cc_public.check.result
import cc_public.control
import cc_public.load.python
import cc_public.requirement
import cc_public.trace


ID_CHECK          = 'evidence'
TITLE             = 'Evidence is current'
NOUN              = 'verification'

KEY_ID_SELF       = 'id_self'
KEY_GUID_SELF     = 'guid_self'
KEY_RELATION      = 'relation'
KEY_ID_REL        = 'id_relation'
KEY_GUID_TGT      = 'guid_target'
KEY_METHOD        = 'method'
KEY_CASE          = 'case'
KEY_GUID_CASE     = 'guid_case'
KEY_GUID_REQ      = 'guid_requirement'
KEY_OUTCOME       = 'outcome'
KEY_DIGEST        = 'digest'

PREFIX_EVIDENCE   = 'evd'
SEPARATOR         = '_'
SUFFIX_PYTHON     = '.py'

REL_IMPLEMENTED   = cc_public.trace.REL_IMPLEMENTED
VERIFICATION_TEST = cc_public.trace.VERIFICATION_TEST
STATUS_ACCEPTED   = cc_public.trace.STATUS_ACCEPTED

OUTCOME_PASSED    = 'passed'

# What a piece of evidence was observed against: the fields of the
# requirement that say what is claimed, the source of what implements
# it, and the source of the case that observed it.
#
FIELD_CLAIMED     = ('statement', 'success_criteria', 'verification')
LENGTH_DIGEST     = cc_public.control.LENGTH_KEY


# -----------------------------------------------------------------------------
def digest(map_document, guid_requirement, guid_case = None):
    """
    Return the digest evidence for guid_requirement is stamped with,
    observed by the case guid_case where there is one.

    Covers what a verdict depends on and nothing else: the requirement
    as claimed, the code of every item implementing it, and the code of
    the case. Code is the syntax tree of the definition with its
    docstrings removed, so that a change to prose or to layout stales
    nothing and a change to what runs stales everything that rests on
    it. A change to anything else, the evidence itself included, does
    not.

    """

    index = _index(map_document)
    (location_req, document_req) = index.get(guid_requirement, (None, {}))

    implementation = [_source(index, edge.get(KEY_GUID_TGT))
                      for edge in (document_req.get(KEY_RELATION) or [])
                      if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_IMPLEMENTED]

    claimed = cc_public.requirement.compose(document_req)
    plain = {'claimed':        {f: claimed.get(f) for f in FIELD_CLAIMED},
             'implementation': implementation,
             'case':           _source(index, guid_case) if guid_case else None}

    return hashlib.sha256(json.dumps(plain, sort_keys = True, default = str)
                                 .encode('utf-8')).hexdigest()[:LENGTH_DIGEST]


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every accepted requirement whose evidence is
    absent, not a pass, or stale.

    An accepted requirement claims to be met, and evidence is what says
    it is. Absent, or observed and not passed, is critical in a closed
    world and advisory in an open one, where the evidence may exist
    elsewhere. Stale is advisory: it says the code or the claim moved
    since the observation, which is the ordinary state of a tree being
    edited, and the merge gate observes afresh. A proposed requirement
    is asked for no evidence; it has claimed nothing yet.

    """

    map_document = context.map_document
    index        = _index(map_document)
    map_id       = {d.get(KEY_ID_SELF): g for (g, (_, d)) in index.items()}
    map_row      = _rows(map_document)
    list_bad     = []
    count        = 0
    elsewhere    = (cc_public.check.result.SEVERITY_CRITICAL if context.is_closed_world
                    else cc_public.check.result.SEVERITY_ADVISORY)

    for record in cc_public.trace.projection(map_document, context.is_closed_world):

        if record.status != STATUS_ACCEPTED:
            continue

        (location, _) = index.get(record.guid_self, (record.id_self, None))
        list_case = [map_id.get(name, name) for name in record.verified_by] \
                    if record.verification == VERIFICATION_TEST else [None]

        for guid_case in list_case:

            count += 1
            row    = map_row.get((record.verification, guid_case, record.guid_self))
            about  = ('by {case} '.format(case = _name(index, guid_case))
                      if guid_case else '')

            if row is None:
                list_bad.append(_finding(location, elsewhere,
                        'Accepted, and no evidence {about}says it is met. '
                        'Evidence by {method} is what an acceptance rests '
                        'on.'.format(about = about, method = record.verification)))
            elif row.get(KEY_OUTCOME) != OUTCOME_PASSED:
                list_bad.append(_finding(location, elsewhere,
                        'Accepted, and the evidence {about}says {outcome}, not '
                        'passed.'.format(about = about, outcome = row.get(KEY_OUTCOME))))
            elif row.get(KEY_DIGEST) != digest(map_document, record.guid_self, guid_case):
                list_bad.append(_finding(location,
                        cc_public.check.result.SEVERITY_ADVISORY,
                        'The evidence {about}is stale: the requirement, what '
                        'implements it or the case has changed since it was '
                        'observed.'.format(about = about)))

    return cc_public.check.result.Result(count_item         = count,
                                         list_nonconformity = list_bad,
                                         list_note          = [])


# -----------------------------------------------------------------------------
def _rows(map_document):
    """
    Return (method, guid_case, guid_requirement) -> row over every
    evidence item in the tree. guid_case is None where the method has
    no case.

    """

    out = {}

    for document in map_document.values():
        if not isinstance(document, dict) or str(
                document.get(KEY_ID_SELF, '')).split(SEPARATOR, 1)[0] != PREFIX_EVIDENCE:
            continue
        for row in (document.get(KEY_CASE) or {}).values():
            if isinstance(row, dict):
                out[(document.get(KEY_METHOD), row.get(KEY_GUID_CASE),
                     row.get(KEY_GUID_REQ))] = row

    return out


# -----------------------------------------------------------------------------
def _index(map_document):
    """
    Return guid -> (location, document) for every document declaring one.

    """

    return {document.get(KEY_GUID_SELF): (location, document)
            for (location, document) in map_document.items()
            if isinstance(document, dict) and isinstance(document.get(KEY_GUID_SELF), str)}


# -----------------------------------------------------------------------------
def _source(index, guid):
    """
    Return what the item guid names is made of: the source of its
    definition for a python item, its document otherwise, or the guid
    where nothing in the tree carries it.

    """

    found = index.get(guid)

    if found is None:
        return guid

    (location, document) = found

    if location.filepath.suffix == SUFFIX_PYTHON:
        return cc_public.load.python.code_of(
                    location.filepath.read_text(encoding = 'utf-8'), location.anchor)

    return json.loads(json.dumps(document, default = str))


# -----------------------------------------------------------------------------
def _name(index, guid):
    """
    Return the readable id of guid, or guid itself.

    """

    found = index.get(guid)

    return found[1].get(KEY_ID_SELF, guid) if found else guid


# -----------------------------------------------------------------------------
def _finding(location, severity, message):
    """
    Return one nonconformity at the requirement.

    """

    return cc_public.check.result.Nonconformity(filepath = str(location),
                                                path     = 'status',
                                                severity = severity,
                                                message  = message)
