"""
---

id_self:                pym_cc_public.render.dossier
guid_self:              pym_a2e01762cb3a44dfb0898d436df4ec33
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Dossier projection
brief:                  |
                        The dossier rooted at an observation, as data.
description:            |
                        Walks the derivations from an observation to
                        needs, concepts and requirements, gathers what
                        each run bound and judged, the findings a
                        check report holds against each requirement
                        and what the trace reports absent, draws the
                        derivations as dot and mermaid, and lists the
                        identities. Nothing about how it looks.
relation:               []

...
"""


import datetime
import pathlib

import cc_public.facts
import cc_public.load.git
import cc_public.need
import cc_public.requirement
import cc_public.trace


KEY_ID_SELF     = 'id_self'
KEY_GUID_SELF   = 'guid_self'
KEY_RELATION    = 'relation'
KEY_ID_REL      = 'id_relation'
KEY_ID_TARGET   = 'id_target'
KEY_ROUND       = 'pass'
KEY_JUDGEMENT   = 'judgement'
KEY_OUTCOME     = 'outcome'
KEY_CANDIDATE   = 'candidate_requirement'
KEY_ASSUMPTION  = 'assumption'
REL_DERIVED     = 'r_is_derived_from'
REL_FRAMED      = 'r_is_framed_by'
REL_BINDS       = 'r_binds'
REL_RAN_UNDER   = 'r_ran_under'
REL_DEPLOYS     = 'r_deploys'
REL_ASSESSES    = 'r_assesses'
REL_CITES       = 'r_cites'
PREFIX_ASSESS   = 'asmt'
KEY_DIMENSION   = 'dimension'
KEY_PRODUCT     = 'product'
WF_RESEARCH     = 'wf_research_concept'
WF_ASSESS       = 'wf_assess_concept'
VERDICT_ORDER   = ('feasible_now', 'feasible_with_development', 'speculative', 'not_feasible')
RATING_STRONG   = 'strong'
PREFIX_NEED     = 'need'
PREFIX_CONCEPT  = 'cpt'
PREFIX_REQ      = 'req'
PREFIX_BINDING  = 'bnd'
ID_CHECK_EVAL   = 'eval'
SIDE_OUTPUT     = '_output_'
SEPARATOR       = '_'
WIDTH_LABEL     = 28


# -----------------------------------------------------------------------------
def dossier(tree, id_observation, report = None):
    """
    Return the dossier rooted at an observation, as plain data with
    nothing of layout in it: the observation, each need drawn from it
    with its concepts and their requirements, what each run did, the
    findings a check report holds against each requirement, what the
    trace reports absent, a drawing of the derivations, and where and
    when the dossier was drawn from.

    """

    index    = _Index(tree)
    obs      = index.document(id_observation)
    list_gap = _gaps(tree)
    findings = _findings(report)
    list_need = []
    list_req  = []
    list_cpt  = []

    for need in index.deriving(obs[KEY_GUID_SELF], PREFIX_NEED):
        entry = _need(need)
        for concept in index.deriving(need[KEY_GUID_SELF], PREFIX_CONCEPT):
            one = _concept(index, concept)
            pointing = index.pointing(concept[KEY_GUID_SELF], REL_ASSESSES, PREFIX_ASSESS)
            one['assessment'] = [_assessment(index, a) for a in pointing]
            _settle_verdict(one)
            for req in index.deriving(concept[KEY_GUID_SELF], PREFIX_REQ):
                row = _requirement(req, one['id'], list_gap, findings)
                one['requirement'].append(row)
                list_req.append(row)
            one['promoted'] = bool(one['requirement'])
            entry['concept'].append(one)
            list_cpt.append(one)
        for req in index.deriving(need[KEY_GUID_SELF], PREFIX_REQ):
            if not any(r['id'] == req[KEY_ID_SELF] for r in list_req):
                row = _requirement(req, None, list_gap, findings)
                entry['requirement'].append(row)
                list_req.append(row)
        entry['concept'].sort(key = _rank)
        list_need.append(entry)

    list_cpt.sort(key = _rank)
    list_asm = [a for c in list_cpt for a in c['assessment']]
    list_exe = index.executions_of([obs] + [index.document(n['id']) for n in list_need]
                                   + [index.document(c['id']) for c in list_cpt]
                                   + [index.document(r['id']) for r in list_req]
                                   + [index.document(a['id']) for a in list_asm])
    _label_assessments(list_asm, list_exe)

    return {'generated_at':  datetime.datetime.now(datetime.UTC).strftime('%-d %B %Y, %H:%M UTC'),
            'revision':      _revision(tree),
            'observation':   _observation(obs),
            'need':          list_need,
            'concept':       list_cpt,
            'requirement':   list_req,
            'execution':     list_exe,
            'assessment':    list_asm,
            'reference':     _references(index, list_cpt),
            'finding_count': sum(len(r['finding']) for r in list_req),
            'graph':         _graph(obs, list_need),
            'identity':      _identities(obs, list_need)}


# -----------------------------------------------------------------------------
class _Index:
    """
    The tree's documents by guid, with the edges into each.

    """

    def __init__(self, tree):
        self.tree     = tree
        self.facts    = cc_public.facts.facts(tree.context.map_document)
        self.map_guid = {item.guid_self: item for item in tree.map_id.values()}
        self.incoming = {}
        for edge in self.facts.edge:
            key = (edge.guid_target, edge.id_relation)
            self.incoming.setdefault(key, []).append(edge.guid_source)

    def document(self, name):
        item = self.tree.resolve(name)
        node = self.tree.context.map_document[item.location]
        for step in (item.path.split('.') if item.path else []):
            node = node[step]
        return node

    def by_guid(self, guid):
        item = self.map_guid.get(guid)
        return None if item is None else self.document(item.id_self)

    def deriving(self, guid, prefix):
        list_doc = [self.by_guid(g) for g in self.incoming.get((guid, REL_DERIVED), [])]
        return sorted([d for d in list_doc
                       if d is not None and d[KEY_ID_SELF].split(SEPARATOR, 1)[0] == prefix],
                      key = lambda d: d[KEY_ID_SELF])

    def pointing(self, guid, id_relation, prefix):
        list_doc = [self.by_guid(g) for g in self.incoming.get((guid, id_relation), [])]
        return sorted([d for d in list_doc
                       if d is not None and d[KEY_ID_SELF].split(SEPARATOR, 1)[0] == prefix],
                      key = lambda d: d[KEY_ID_SELF])

    def cited(self, document):
        """The observations an item's edges cite, as (id, title)."""
        out = []
        for edge in document.get(KEY_RELATION) or []:
            if edge.get(KEY_ID_REL) == REL_CITES:
                doc = self.by_guid(edge.get('guid_target'))
                if doc is not None:
                    out.append({'id': doc[KEY_ID_SELF], 'title': doc.get('title', '')})
        return out

    def target(self, document, id_relation):
        for edge in document.get(KEY_RELATION) or []:
            if edge.get(KEY_ID_REL) == id_relation:
                return self.document(edge[KEY_ID_TARGET])
        return None

    def executions_of(self, list_doc):
        """The runs that bound any of the documents, each once, oldest first."""
        wanted = {d[KEY_GUID_SELF] for d in list_doc}
        seen   = {}
        for item in self.tree.map_id.values():
            if item.id_self.split(SEPARATOR, 1)[0] != PREFIX_BINDING:
                continue
            binding = self.document(item.id_self)
            bound   = [e for e in binding.get(KEY_RELATION) or []
                       if e.get(KEY_ID_REL) == REL_BINDS]
            if not any(self.map_guid.get(e.get('guid_target')) is not None
                       and e.get('guid_target') in wanted for e in bound):
                continue
            exe = self.tree.context.map_document[item.location]
            seen.setdefault(exe[KEY_ID_SELF], (exe, []))[1].append(binding)
        return [self._execution(exe, bindings) for (_, (exe, bindings)) in sorted(seen.items())]

    def _execution(self, exe, bindings):
        dep = self.target(exe, REL_RAN_UNDER) or {}
        wf  = self.target(dep, REL_DEPLOYS) or {}
        judgements = []
        for b in sorted(bindings, key = lambda b: (b.get(KEY_ROUND, 0), b[KEY_ID_SELF])):
            if SIDE_OUTPUT in b[KEY_ID_SELF] and b.get(KEY_JUDGEMENT):
                judgements = [{'eval': j['id_eval'], 'verdict': j['verdict'],
                               'reason': j.get('reason', '')} for j in b[KEY_JUDGEMENT]]
        return {'id':         exe[KEY_ID_SELF],
                'workflow':   wf.get(KEY_ID_SELF),
                'deployment': dep.get(KEY_ID_SELF),
                'model':      dep.get('model'),
                'challenger': dep.get('model_challenge'),
                'budget':     dep.get('budget'),
                'passes':     max([b.get(KEY_ROUND, 1) for b in bindings] or [1]),
                'outcome':    exe.get(KEY_OUTCOME),
                'judgement':  judgements,
                'bound':      sorted({e[KEY_ID_TARGET] for b in bindings
                                      for e in b.get(KEY_RELATION) or []
                                      if e.get(KEY_ID_REL) == REL_BINDS})}


# -----------------------------------------------------------------------------
def _observation(doc):
    return {'id':           doc[KEY_ID_SELF],
            'guid':         doc[KEY_GUID_SELF],
            'title':        doc.get('title'),
            'source_kind':  doc.get('source_kind', '').replace(SEPARATOR, ' '),
            'source_uri':   doc.get('source_uri'),
            'attribution':  doc.get('attribution'),
            'published_at': doc.get('published_at'),
            'observed_at':  doc.get('observed_at'),
            'method':       doc.get('capture_method', '').replace(SEPARATOR, ' '),
            'content':      doc.get('content', ''),
            'digest':       doc.get('content_digest'),
            'note':         doc.get('note')}


def _need(doc):
    return {'id':        doc[KEY_ID_SELF],
            'guid':      doc[KEY_GUID_SELF],
            'title':     doc.get('title'),
            'statement': cc_public.need.statement(doc),
            'subject':   doc.get('subject', ''),
            'outcome':   doc.get('outcome', ''),
            'purpose':   doc.get('purpose', ''),
            'context':   doc.get('context', ''),
            'evidence':  doc.get('evidence', ''),
            'status':    doc.get('status'),
            'concept':   [],
            'requirement': []}


def _concept(index, doc):
    framing = index.target(doc, REL_FRAMED) or {}
    return {'id':           doc[KEY_ID_SELF],
            'guid':         doc[KEY_GUID_SELF],
            'title':        doc.get('title'),
            'brief':        doc.get('brief', ''),
            'entity':       doc.get('entity'),
            'framing':      {'id': framing.get(KEY_ID_SELF), 'title': framing.get('title'),
                             'brief': framing.get('brief', '')},
            'operation':    doc.get('operation', ''),
            'architecture': doc.get('architecture', ''),
            'effect':       doc.get('effect', ''),
            'risk':         doc.get('risk', ''),
            'assumption':   [{'key': k, 'statement': v.get('statement', ''),
                              'evidence': v.get('evidence', '')}
                             for (k, v) in (doc.get(KEY_ASSUMPTION) or {}).items()],
            'candidate':    [{'key': k, 'statement': _statement(v),
                              'rationale': v.get('rationale', ''),
                              'category': v.get('category', '')}
                             for (k, v) in (doc.get(KEY_CANDIDATE) or {}).items()],
            'challenge':    doc.get('challenge', ''),
            'resolution':   doc.get('resolution', ''),
            'status':       doc.get('status'),
            'requirement':  [],
            'promoted':     False}


def _assessment(index, doc):
    return {'id':        doc[KEY_ID_SELF],
            'guid':      doc[KEY_GUID_SELF],
            'title':     doc.get('title'),
            'assessor':  doc.get('assessor'),
            'made_by':   None,
            'verdict':   doc.get('verdict'),
            'summary':   doc.get('summary', ''),
            'status':    doc.get('status'),
            'dimension': [{'key': k, 'rating': v.get('rating'), 'rationale': v.get('rationale', ''),
                           'cited': index.cited(v)}
                          for (k, v) in (doc.get(KEY_DIMENSION) or {}).items()],
            'product':   [{'key': k, 'name': v.get('name'), 'role': v.get('role', ''),
                           'maturity': v.get('maturity'), 'support': v.get('support', ''),
                           'cited': index.cited(v)}
                          for (k, v) in (doc.get(KEY_PRODUCT) or {}).items()],
            'cited':     index.cited(doc)}


def _settle_verdict(concept):
    """The assessment a document leads with: the one with references, else the first."""
    list_asm = concept['assessment']
    lead     = next((a for a in list_asm if a['cited'] or a['assessor']),
                    list_asm[0] if list_asm else None)
    concept['lead']    = lead
    concept['verdict'] = lead['verdict'] if lead else None


def _rank(concept):
    """Most directly feasible first: by verdict, then by strong ratings, then by name."""
    lead  = concept.get('lead')
    order = VERDICT_ORDER.index(lead['verdict']) if lead and lead['verdict'] in VERDICT_ORDER \
            else len(VERDICT_ORDER)
    strong = -sum(1 for d in (lead['dimension'] if lead else []) if d['rating'] == RATING_STRONG)
    return (order, strong, concept['title'] or '')


def _label_assessments(list_asm, list_exe):
    """Say how each assessment was made: by the research agent, by a model, or by hand."""
    for a in list_asm:
        runs = [e for e in list_exe if a['id'] in e['bound']]
        if any(e['workflow'] == WF_RESEARCH for e in runs):
            a['made_by'] = 'agent'
        elif any(e['workflow'] == WF_ASSESS for e in runs):
            a['made_by'] = 'model'
            a['assessor'] = a['assessor'] or next(e['model'] for e in runs
                                                  if e['workflow'] == WF_ASSESS)
        else:
            a['made_by'] = 'person' if a['assessor'] else 'unknown'


def _references(index, list_cpt):
    """Every observation an assessment, dimension or product cites, most cited first."""
    count = {}
    for c in list_cpt:
        for a in c['assessment']:
            cited = list(a['cited'])
            for d in a['dimension']:
                cited += d['cited']
            for pr in a['product']:
                cited += pr['cited']
            for ref in cited:
                count.setdefault(ref['id'], {'id': ref['id'], 'title': ref['title'],
                                             'count': 0})
                count[ref['id']]['count'] += 1
    out = []
    for ref in sorted(count.values(), key = lambda r: (-r['count'], r['id'])):
        doc = index.document(ref['id'])
        out.append({**ref, 'attribution': doc.get('attribution'),
                    'source_uri': doc.get('source_uri'),
                    'published_at': doc.get('published_at'), 'observed_at': doc.get('observed_at'),
                    'source_kind': doc.get('source_kind', '').replace(SEPARATOR, ' '),
                    'digest': doc.get('content_digest'), 'content': doc.get('content', '')})
    return out


def _statement(doc):
    """
    Return the statement of a requirement or a candidate, composed from
    its slots, or nothing where they do not compose.

    """

    try:
        return cc_public.requirement.statement(doc)
    except cc_public.requirement.ErrorSlot:
        return ''


def _requirement(doc, id_concept, list_gap, findings):
    return {'id':        doc[KEY_ID_SELF],
            'guid':      doc[KEY_GUID_SELF],
            'title':     doc.get('title'),
            'statement': _statement(doc),
            'rationale': doc.get('rationale', ''),
            'category':  doc.get('category'),
            'claim':     doc.get('claim'),
            'status':    doc.get('status'),
            'concept':   id_concept,
            'gap':       [g for (guid, g) in list_gap if guid == doc[KEY_GUID_SELF]],
            'finding':   findings.get(doc[KEY_ID_SELF], [])}


# -----------------------------------------------------------------------------
def _gaps(tree):
    return [(record.guid_self, gap.message)
            for record in cc_public.trace.projection(tree.context.map_document, False)
            for gap in record.gap]


def _findings(report):
    """{id_item: [{eval, severity, message}]} from a check report, or nothing."""
    out = {}
    if not report:
        return out
    body = report.get('report', report)
    for check in body.get('check') or []:
        if check.get('id_check') != ID_CHECK_EVAL:
            continue
        for n in check.get('nonconformity') or []:
            out.setdefault(n.get('path'), []).append(
                    {'eval':     pathlib.Path(n.get('filepath', '')).stem,
                     'severity': n.get('severity'),
                     'message':  n.get('message', '')})
    return out


def _revision(tree):
    try:
        head  = cc_public.load.git.git(tree.root, 'rev-parse', '--short', 'HEAD').strip()
        dirty = bool(cc_public.load.git.git(tree.root, 'status', '--porcelain').strip())
    except cc_public.load.git.ErrorGit:
        return None
    return head + (' (with uncommitted changes)' if dirty else '')


# -----------------------------------------------------------------------------
def _graph(obs, list_need):
    """The derivations as dot and as mermaid, labelled by title; a concept carries its
    requirement count rather than a box per requirement."""
    nodes = [(obs['id_self'], obs.get('title', ''), 'observation')]
    edges = []
    for need in list_need:
        nodes.append((need['id'], need['title'], 'need'))
        edges.append((need['id'], obs['id_self']))
        for c in need['concept']:
            count = len(c['requirement'])
            label = c['title'] + (' ({n} requirements)'.format(n = count) if count else '')
            nodes.append((c['id'], label, 'concept'))
            edges.append((c['id'], need['id']))
        for r in need['requirement']:
            nodes.append((r['id'], r['title'], 'requirement'))
            edges.append((r['id'], need['id']))
    shape = {'observation': 'note', 'need': 'box', 'concept': 'box', 'requirement': 'box'}
    fill  = {'observation': '#f4efe6', 'need': '#e8eef7', 'concept': '#e9f3e6',
             'requirement': '#ffffff'}
    dot   = ['digraph dossier {', '  rankdir=RL;', '  node [fontname="Helvetica" fontsize=9 '
             'style="filled,rounded" color="#777777"];', '  edge [color="#777777" arrowsize=0.6];']
    for (id_self, title, kind) in nodes:
        dot.append('  "{i}" [label="{l}" shape={s} fillcolor="{f}"];'.format(
                        i = id_self, l = _wrap(title or id_self), s = shape[kind], f = fill[kind]))
    for (src, dst) in edges:
        dot.append('  "{s}" -> "{d}";'.format(s = src, d = dst))
    dot.append('}')
    mermaid = ['flowchart RL']
    mermaid += ['  {i}["{l}"]'.format(i = i, l = (t or i).replace('"', "'"))
                for (i, t, _) in nodes]
    mermaid += ['  {s} --> {d}'.format(s = s, d = d) for (s, d) in edges]
    return {'dot': '\n'.join(dot), 'mermaid': '\n'.join(mermaid)}


def _wrap(text):
    words, lines, line = text.split(), [], ''
    for w in words:
        if line and len(line) + len(w) + 1 > WIDTH_LABEL:
            lines.append(line)
            line = w
        else:
            line = (line + ' ' + w).strip()
    lines.append(line)
    return '\\n'.join(lines).replace('"', "'")


def _identities(obs, list_need):
    out = [('observation', obs['id_self'], obs['guid_self'])]
    for need in list_need:
        out.append(('need', need['id'], need['guid']))
        for c in need['concept']:
            out.append(('concept', c['id'], c['guid']))
            out.extend(('assessment', a['id'], a['guid']) for a in c['assessment'])
            out.extend(('requirement', r['id'], r['guid']) for r in c['requirement'])
        out.extend(('requirement', r['id'], r['guid']) for r in need['requirement'])
    return out
