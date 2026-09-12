"""
---

id_self:                pym_cc_public.workflow.component
guid_self:              pym_4fcb8b39bcdc4048a9a6402410525085
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  The tool's own components
brief:                  |
                        Functions that implement components of the
                        tool's own workflows.
description:            |
                        Each function in this module is named by a
                        component through an r_is_implemented_by edge
                        and follows the contract of a component in
                        code. The function takes the tree, the ledger
                        and the inputs by port. It returns the id of
                        an item for each output port, and it notes on
                        the ledger what it changes before changing it.
                        The first such function accepts a requirement.
relation:               []

...
"""


import importlib.metadata

import cc_public.control
import cc_public.decision
import cc_public.edit.accept
import cc_public.edit.field
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.evidence
import cc_public.facts
import cc_public.item
import cc_public.requirement


PORT_REQUIREMENT = 'requirement'
PORT_ACCEPTED    = 'accepted'
PORT_VERIFIED    = 'verified'
PORT_CONCEPT     = 'concept'
PORT_PROMOTED    = 'promoted'
KEY_CANDIDATE    = 'candidate_requirement'
KEY_RELATION     = 'relation'
KEY_ID_REL       = 'id_relation'
KEY_ID_TARGET    = 'id_target'
KEY_STATUS       = 'status'
KEY_ID_SELF      = 'id_self'
STATUS_PROPOSED  = 'proposed'
TYPE_REQUIREMENT = 't_textual_requirement'

# What a promoted requirement takes from its candidate as it stands:
# the slots of the statement, the claim and the category. The
# statement itself is composed from the slots wherever it is shown.
#
FIELD_COPIED     = (cc_public.requirement.KEY_CONDITION_KIND,
                    cc_public.requirement.KEY_CONDITION,
                    cc_public.requirement.KEY_ENTITY,
                    cc_public.requirement.KEY_OBLIGATION,
                    cc_public.requirement.KEY_ACTIVITY,
                    cc_public.requirement.KEY_ACTOR,
                    cc_public.requirement.KEY_PROCESS,
                    cc_public.requirement.KEY_OBJECT,
                    cc_public.requirement.KEY_QUALIFIER,
                    'claim', 'category', 'quote')
PREFIX_REQ       = 'req'
REL_DERIVED      = 'r_is_derived_from'
WIDTH_TITLE      = 80
PREFIX_KEY       = ('cr', 'crq', 'req')
REL_ADMITTED     = 'r_is_admitted_by'
REL_CITES        = 'r_cites'
REL_RAN_UNDER    = 'r_ran_under'
REL_DEPLOYS      = 'r_deploys'
REL_BINDS        = 'r_binds'
WF_CONCEPT       = 'wf_concept_from_need'
PREFIX_EXECUTION = 'exe'
PREFIX_OBS       = 'obs'
OUTCOME_COMPLETE = 'completed'
KEY_BINDING      = 'binding'
KEY_GUID_TARGET  = 'guid_target'
KEY_OUTCOME      = 'outcome'
KEY_CLAIM        = 'claim'
KEY_QUOTE        = 'quote'
KEY_CONTENT      = 'content'
CLAIM_EVIDENTIAL = 'evidential'
REL_VERIFIES     = 'r_verifies'
PREFIX_FUNCTION  = 'pyf'
SEPARATOR        = '_'


# -----------------------------------------------------------------------------
def accept(tree, ledger, map_input):
    """
    ---

    id_self:                pyf_cc_public.workflow.component.accept
    guid_self:              pyf_074e3769a2d640ed9f73ec7e241169de
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Accept a requirement
    brief:                  |
                            Accept the requirement bound to the
                            requirement input, where its assurance is
                            complete, and return it on the requirement
                            output.

                            The contract of a component in code: the tree,
                            the ledger and the inputs by port come in; the
                            id of an item for each output port goes out;
                            what is changed is noted on the ledger first,
                            so that a stop puts it back; and a refusal is
                            raised, which stops the run.
    description:            |
                            This is the first component in code. It notes
                            the requirement's file on the ledger, accepts
                            the requirement through the edit tier's accept
                            function, which refuses where the assurance is
                            incomplete, and returns the same id on the
                            accepted output.
    relation:               []

    ...
    """

    id_requirement = map_input[PORT_REQUIREMENT]

    ledger.note_modify(tree.resolve(id_requirement).filepath)
    cc_public.edit.accept.accept(tree, id_requirement)

    return {PORT_ACCEPTED: id_requirement}


# -----------------------------------------------------------------------------
def verify(tree, ledger, map_input):
    """
    ---

    id_self:                pyf_cc_public.workflow.component.verify
    guid_self:              pyf_7a3befec6f8946bca5f4f0dc70793ed9
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Verify a requirement
    brief:                  |
                            Run the tests that verify the requirement
                            bound to the requirement input, record what
                            they observed as evidence, and return the
                            requirement on the verified output. Refuse
                            where any did not pass, so that the run stops
                            and says which.

                            A requirement nothing verifies by test runs
                            nothing: its evidence, if any, is an
                            attestation, and the accept node says what it
                            lacks. The evidence file is noted on the
                            ledger first, so that a stop puts the tree
                            back as it was, the failure being in the
                            report.
    description:            |
                            The second component in code. Finds the
                            function items that verify the requirement,
                            runs them under pytest in a subprocess,
                            records what they observed through the same
                            evidence writer the test session uses, and
                            refuses where any did not pass.
    relation:               []

    ...
    """

    id_requirement = map_input[PORT_REQUIREMENT]
    list_nodeid    = _nodeids(tree, tree.resolve(id_requirement))

    if not list_nodeid:
        return {PORT_VERIFIED: id_requirement}

    path = tree.root / cc_public.evidence.DIR_EVIDENCE \
                     / (cc_public.evidence.ID_PYTEST + cc_public.evidence.SUFFIX)
    (ledger.note_modify if path.exists() else ledger.note_create)(path)

    map_outcome = cc_public.evidence.observe(tree.root, list_nodeid)
    written     = cc_public.evidence.from_pytest(tree.root, map_outcome,
                                                 importlib.metadata.version('pytest'))
    if written is not None:
        tree.refresh(written)

    list_bad = sorted(n for (n, o) in map_outcome.items()
                        if o != cc_public.evidence.OUTCOME_PASSED)
    if list_bad:
        raise cc_public.edit.tree.ErrorItem(
                '{n} of {m} test(s) verifying {req} did not pass: {which}.'.format(
                        n = len(list_bad), m = len(map_outcome), req = id_requirement,
                        which = '; '.join('{t} {o}'.format(t = t, o = map_outcome[t])
                                          for t in list_bad)))

    return {PORT_VERIFIED: id_requirement}


# -----------------------------------------------------------------------------
def _nodeids(tree, requirement):
    """
    Return the pytest node ids of the function items that verify the
    requirement, path::name, sorted.

    """

    facts     = cc_public.facts.facts(tree.context.map_document)
    map_guid  = {item.guid_self: item for item in tree.map_id.values()}
    list_item = [map_guid[e.guid_source] for e in facts.edge
                 if e.id_relation == REL_VERIFIES and e.guid_target == requirement.guid_self
                 and e.guid_source in map_guid]

    return sorted('::'.join([str(item.filepath.relative_to(tree.root)),
                             *item.location.anchor])
                  for item in list_item
                  if cc_public.item.prefix_of(item.id_self) == PREFIX_FUNCTION)


# -----------------------------------------------------------------------------
def promote(tree, ledger, map_input):
    """
    ---

    id_self:                pyf_cc_public.workflow.component.promote
    guid_self:              pyf_d060a8befcfd44f0afa24ad9ae147c43
    copyright:              Copyright 2026 William Payne
    license:                Apache-2.0

    protective_mark:

      - id_mark:            mark_public
        guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

    title:                  Promote a concept
    brief:                  |
                            Make a proposed textual requirement item from
                            each candidate requirement of the concept
                            bound to the concept input, deriving from the
                            concept and from the need the concept derives
                            from, and return the concept on the promoted
                            output. Refuse where a requirement the
                            promotion would make exists already.

                            The candidate entries stay in the concept as
                            the record of what was proposed; the items are
                            what the requirement evals judge and
                            acceptance binds. The boundary from
                            exploration to assurance, done mechanically.
    description:            |
                            This is the third component in code. It reads
                            the candidate requirement entries of the
                            concept and makes a proposed textual
                            requirement item from each through the edit
                            tier. Each item derives from the concept and
                            from the need the concept derives from. The
                            component refuses where a requirement it would
                            make exists already.
    relation:               []

    ...
    """

    id_concept = map_input[PORT_CONCEPT]
    concept    = tree.context.map_document[tree.resolve(id_concept).location]
    id_need    = _target_of(concept, REL_DERIVED)
    stem       = id_concept.split(SEPARATOR, 1)[1]
    id_admit   = _admission(tree, id_concept)

    for (key, entry) in (concept.get(KEY_CANDIDATE) or {}).items():

        id_requirement = SEPARATOR.join([PREFIX_REQ, stem, key])

        if id_requirement in tree.map_id:
            raise cc_public.edit.tree.ErrorItem(
                    '{id} exists already; {concept} was promoted before.'.format(
                            id = id_requirement, concept = id_concept))

        id_cited = _citation(tree, id_concept, key, entry)

        ledger.note_create(cc_public.edit.new.new(tree, TYPE_REQUIREMENT, id_requirement,
                                                  tree.defaults()))
        cc_public.edit.field.set_field(tree, id_requirement, 'title',
                                       value = _title(key))
        cc_public.edit.field.set_field(tree, id_requirement, 'rationale',
                                       prose = str(entry.get('rationale') or ''))
        for field in FIELD_COPIED:
            if entry.get(field):
                cc_public.edit.field.set_field(tree, id_requirement, field,
                                               value = str(entry[field]))
        cc_public.edit.field.set_field(tree, id_requirement, KEY_STATUS,
                                       value = STATUS_PROPOSED)
        cc_public.edit.link.link(tree, id_requirement, REL_DERIVED, id_concept)
        cc_public.edit.link.link(tree, id_requirement, REL_DERIVED, id_need)
        cc_public.edit.link.link(tree, id_requirement, REL_ADMITTED, id_admit)
        if id_cited is not None:
            cc_public.edit.link.link(tree, id_requirement, REL_CITES, id_cited)

    return {PORT_PROMOTED: id_concept}


# -----------------------------------------------------------------------------
def _admission(tree, id_concept):
    """
    Return the id of what admits the concept to promotion: the latest
    run of the concept workflow that bound it, where its challenge
    concluded; else the latest waiver decision that still holds over
    it. Refuse where there is neither, saying what is lacking.

    """

    guid    = tree.resolve(id_concept).guid_self
    latest  = None

    for document in tree.context.map_document.values():
        if not isinstance(document, dict) or cc_public.item.prefix_of(
                        document.get(KEY_ID_SELF)) != PREFIX_EXECUTION:
            continue
        if not _binds(document, guid) or _workflow_of(tree, document) != WF_CONCEPT:
            continue
        if latest is None or document[KEY_ID_SELF] > latest[KEY_ID_SELF]:
            latest = document

    if latest is not None and latest.get(KEY_OUTCOME) == OUTCOME_COMPLETE:
        return latest[KEY_ID_SELF]

    map_guid = cc_public.decision.index(tree.context.map_document)
    waiver   = None

    for document in tree.context.map_document.values():
        is_waiver = (cc_public.decision.is_decision(document)
                     and document.get(cc_public.decision.KEY_OUTCOME)
                             == cc_public.decision.OUTCOME_WAIVE)
        if not is_waiver \
                or not any(s.get(cc_public.decision.KEY_GUID_ITEM) == guid
                           for s in document.get(cc_public.decision.KEY_SUBJECT) or []) \
                or not cc_public.decision.holds(document, map_guid):
            continue
        if waiver is None or document[KEY_ID_SELF] > waiver[KEY_ID_SELF]:
            waiver = document

    if waiver is not None:
        return waiver[KEY_ID_SELF]

    ended = ('its challenge ended {outcome}'.format(outcome = latest.get(KEY_OUTCOME))
             if latest is not None else 'no run of {wf} bound it'.format(wf = WF_CONCEPT))
    raise cc_public.edit.tree.ErrorItem(
            '{concept} is not admitted to promotion: {ended}, and no waiver decision '
            'that still holds is over it. Record one with cctool decide waive --on '
            '{concept}, naming who takes the risk and until when.'.format(
                                                    concept = id_concept, ended = ended))


# -----------------------------------------------------------------------------
def _citation(tree, id_concept, key, entry):
    """
    Return the id of the observation an evidential candidate cites,
    having checked that its quote is there, or None for a design
    candidate. The candidate may name the observation by an r_cites
    edge; otherwise the observations behind the concept's need are
    searched for the quote. Refuse an evidential candidate with no
    quote, or a quote no observation holds.

    """

    if entry.get(KEY_CLAIM) != CLAIM_EVIDENTIAL:
        return None

    where = '{concept}.{key}'.format(concept = id_concept, key = key)
    quote = cc_public.control.normalise(str(entry.get(KEY_QUOTE) or ''))

    if not quote:
        raise cc_public.edit.tree.ErrorItem(
                '{where} is an evidential claim with no quote: an evidential claim is '
                'defended by quoting the span of a captured source it rests on, word '
                'for word, or it is a design claim.'.format(where = where))

    cited = [edge[KEY_ID_TARGET] for edge in entry.get(KEY_RELATION) or []
             if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_CITES]

    for id_observation in cited or _observations_behind(tree, id_concept):
        content = tree.context.map_document[tree.resolve(id_observation).location] \
                      .get(KEY_CONTENT, '')
        if quote in cc_public.control.normalise(str(content)):
            return id_observation

    raise cc_public.edit.tree.ErrorItem(
            '{where} quotes words that {which} holds: the quote is the span of the '
            'source, word for word.'.format(
                    where = where,
                    which = ('none of ' + ', '.join(cited)) if cited
                            else 'no observation behind the concept'))


# -----------------------------------------------------------------------------
def _observations_behind(tree, id_concept):
    """
    Return the ids of the observations the concept's need derives from,
    and any the concept derives from itself.

    """

    out = []

    for id_item in (id_concept, _target_of(
                        tree.context.map_document[tree.resolve(id_concept).location],
                        REL_DERIVED)):
        document = tree.context.map_document[tree.resolve(id_item).location]
        for edge in document.get(KEY_RELATION) or []:
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_DERIVED \
                    and cc_public.item.prefix_of(edge.get(KEY_ID_TARGET)) == PREFIX_OBS:
                out.append(edge[KEY_ID_TARGET])

    return out


# -----------------------------------------------------------------------------
def _binds(execution, guid):
    """
    Return whether any binding of the execution binds the item with
    this guid.

    """

    for binding in (execution.get(KEY_BINDING) or {}).values():
        for edge in (binding.get(KEY_RELATION) or []) if isinstance(binding, dict) else []:
            if isinstance(edge, dict) and edge.get(KEY_ID_REL) == REL_BINDS \
                    and edge.get(KEY_GUID_TARGET) == guid:
                return True

    return False


# -----------------------------------------------------------------------------
def _workflow_of(tree, execution):
    """
    Return the id of the workflow an execution ran, through the
    deployment it ran under, or None where that cannot be told.

    """

    try:
        id_deployment = _target_of(execution, REL_RAN_UNDER)
        if id_deployment not in tree.map_id:
            return None
        deployment = tree.context.map_document[tree.resolve(id_deployment).location]
        return _target_of(deployment, REL_DEPLOYS)
    except cc_public.edit.tree.ErrorItem:
        return None


# -----------------------------------------------------------------------------
def _target_of(document, id_relation):
    """
    Return the readable id at the far end of the document's first
    edge of the relation, or refuse where it has none.

    """

    for edge in document.get(KEY_RELATION) or []:
        if edge.get(KEY_ID_REL) == id_relation:
            return edge[KEY_ID_TARGET]

    raise cc_public.edit.tree.ErrorItem(
            '{id} carries no {rel} edge.'.format(id = document.get('id_self'),
                                                rel = id_relation))


# -----------------------------------------------------------------------------
def _title(key):
    """
    Return the title a candidate's key gives its requirement: the key
    as words, less a prefix the model gave its keys, capitalised, cut to
    the title's bound.

    """

    words = key.replace(SEPARATOR, ' ').strip()
    for prefix in PREFIX_KEY:                    # a model's own prefix on its keys is not a title
        if words.startswith(prefix + ' '):
            words = words[len(prefix) + 1:]
    title = words[:1].upper() + words[1:]

    return title[:WIDTH_TITLE].rstrip()
