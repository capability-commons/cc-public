"""
---

id_self:                pym_cc_public.workflow.run
guid_self:              pym_7cb6d25c271a4a1487f6367760bc8d63
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Run a workflow
brief:                  |
                        Execute a dataflow workflow once, under a
                        deployment, and record what happened.
description:            |
                        Binds the graph's inputs, orders the nodes,
                        and for each has the generator fill the items
                        its output ports produce or revise, through
                        the edit package. After every node the checks
                        run and a critical finding stops the run; the
                        anchored evals are judged as the deployment
                        says; forward edges fire by their guards; and
                        the bindings go on the execution. A stopped
                        run restores every file it touched. A finished
                        one commits as the deployment says.

...
"""


import datetime
import pathlib
import re
import uuid

import cc_public.check
import cc_public.commit
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.workflow.graph


KEY_TABLE      = 'table'
KEY_PREFIX     = 'prefix'
KEY_REGEX_ID   = 'regex_id'
KEY_ID_TYPE    = 'id_type'
KEY_PROMPT     = 'prompt'
KEY_REVISES    = 'revises'
KEY_OPTIONAL   = 'optional'
KEY_RELATION   = 'relation'
KEY_ID_REL     = 'id_relation'
KEY_GUID_TGT   = 'guid_target'

REL_JUDGED_BY  = 'r_is_judged_by'
REL_RAN_UNDER  = 'r_ran_under'
REL_BINDS      = 'r_binds'

JUDGE_ALWAYS   = 'always'
JUDGE_GUARDS   = 'guards'
JUDGE_NEVER    = 'never'

COMMIT_RUN     = 'run'
COMMIT_NODE    = 'node'
COMMIT_NEVER   = 'never'

VERDICT_MET    = cc_public.eval.runner.VERDICT_MET
VERDICT_UNMET  = cc_public.eval.runner.VERDICT_UNMET

PREFIX_EXE     = 'exe'
DIR_EXECUTION  = 'execution'
FORMAT_STAMP   = '%Y%m%d%H%M%S'
LENGTH_TAG     = 6
WIDTH_VALUE    = 50

# Envelope fields the tool fills; never asked of the generator.
#
FIELD_OWN      = ('id_self', 'guid_self', 'copyright', 'license',
                  'protective_mark', 'relation', 'status')


# -----------------------------------------------------------------------------
class Stop(Exception):
    """
    Raised where a run cannot go on. The reason is the message.

    """

    pass


# -----------------------------------------------------------------------------
class Ledger:
    """
    What a run has written, so that it can be put back.

    A file the run made is deleted. A file it changed is rewritten
    from the bytes it had before. Nothing else is touched.

    """

    def __init__(self):
        self.created  = []
        self.modified = {}

    def note_create(self, path):
        self.created.append(pathlib.Path(path))

    def note_modify(self, path):
        path = pathlib.Path(path)
        if path not in self.modified and path not in self.created:
            self.modified[path] = path.read_bytes()

    def restore(self):
        for (path, data) in self.modified.items():
            path.write_bytes(data)
        for path in reversed(self.created):
            if path.exists():
                path.unlink()
        self.clear()

    def clear(self):
        self.created  = []
        self.modified = {}


# -----------------------------------------------------------------------------
def run(root, id_workflow, id_deployment, map_bind, generator, runner,
        is_dry = False, list_trailer = ()):
    """
    Run the workflow and return the report.

    map_bind maps 'node.input.port' to the readable id of the item
    bound there. runner judges; it may be None where the deployment
    judges nothing.

    """

    root   = pathlib.Path(root).resolve()
    tree   = cc_public.edit.tree.Tree([root])
    graph  = cc_public.workflow.graph.Graph(tree, id_workflow)
    dep    = tree.context.map_document[tree.resolve(id_deployment).filepath]
    policy = {'judge':   dep.get('judge', JUDGE_ALWAYS),
              'confirm': dep.get('confirm', cc_public.eval.runner.COUNT_CONFIRM),
              'commit':  dep.get('commit', COMMIT_RUN)}
    report = {'workflow': graph.id_self, 'deployment': id_deployment,
              'policy': policy, 'order': graph.order(), 'node': [],
              'execution': None, 'commit': None, 'stopped': None}

    # The graph's inputs, from --bind. Every required one must be given.
    #
    bound = {}

    for (path, name) in map_bind.items():
        part = path.split('.')
        if len(part) != 3 or part[1] != 'input' or part[0] not in graph.node \
                or part[2] not in graph.inputs(part[0]):
            raise Stop('{path} is not an input port of this workflow.'.format(
                                                                path = path))
        if graph.incoming(part[0], part[2]):
            raise Stop('{path} is fed by an edge and cannot be bound.'.format(
                                                                path = path))
        bound[(part[0], part[2])] = tree.resolve(name).id_self

    for (node, port, is_optional) in graph.unbound():
        if (node, port) not in bound and not is_optional:
            raise Stop('{node}.input.{port} is required and nothing binds '
                       'it. Give --bind.'.format(node = node, port = port))

    report['bound'] = {f'{n}.input.{p}': i for ((n, p), i) in bound.items()}

    if is_dry:
        for local in report['order']:
            report['node'].append(_plan(graph, local, bound))
        return report

    if policy['commit'] != COMMIT_NEVER and cc_public.commit.changed(root):
        raise Stop('The working tree is not clean, and this deployment '
                   'commits. Commit or stash first, or deploy with commit: '
                   'never.')

    ledger = Ledger()

    try:
        id_exe = _execution(tree, ledger, graph.id_self, id_deployment)
        report['execution'] = id_exe

        for local in report['order']:
            entry = _node(tree, graph, local, bound, generator, runner,
                          policy, ledger, id_exe, root)
            report['node'].append(entry)

            if policy['commit'] == COMMIT_NODE:
                (hash, _) = cc_public.commit.commit(
                        root, 'Run {wf}: {node}'.format(wf = graph.id_self,
                                                        node = local),
                        description = _summary([entry]),
                        id_execution = id_exe, list_trailer = list_trailer)
                entry['commit'] = hash
                ledger.clear()

        cc_public.edit.field.set_field(tree, id_exe, 'description',
                                       prose = _summary(report['node']))

        if policy['commit'] == COMMIT_RUN:
            (hash, _) = cc_public.commit.commit(
                    root, 'Run {wf} under {dep}'.format(wf  = graph.id_self,
                                                        dep = id_deployment),
                    description = _summary(report['node']),
                    id_execution = id_exe, list_trailer = list_trailer)
            report['commit'] = hash

    except Stop as stop:
        ledger.restore()
        report['stopped'] = str(stop)
        if policy['commit'] != COMMIT_NODE:
            report['execution'] = None

    return report


# -----------------------------------------------------------------------------
def _plan(graph, local, bound):
    """
    Return what a node would do, for a dry run.

    """

    return {'node':    local,
            'input':   {p: bound.get((local, p)) for p in graph.inputs(local)},
            'output':  {p: ('revises ' + spec[KEY_REVISES]
                            if spec.get(KEY_REVISES) else 'makes ' + spec.get(KEY_ID_TYPE, '?'))
                        for (p, spec) in graph.outputs(local).items()}}


# -----------------------------------------------------------------------------
def _execution(tree, ledger, id_workflow, id_deployment):
    """
    Make the execution record and return its id.

    """

    guid   = PREFIX_EXE + '_' + uuid.uuid4().hex
    stamp  = datetime.datetime.now(datetime.timezone.utc).strftime(FORMAT_STAMP)
    id_exe = '{p}_{stamp}_{tag}'.format(p = PREFIX_EXE, stamp = stamp,
                                        tag = guid.split('_', 1)[1][:LENGTH_TAG])

    # Executions have a directory of their own. They accumulate, one
    # per run, and would otherwise bury the definitions they ran.
    #
    root = _root(tree)
    path = cc_public.edit.new.new(tree, 't_execution', id_exe,
                                  cc_public.edit.tree.defaults(),
                                  dirpath_out = root / DIR_EXECUTION, guid = guid)
    ledger.note_create(path)

    title = 'Run of {wf} under {dep}'.format(wf = id_workflow, dep = id_deployment)
    cc_public.edit.field.set_field(tree, id_exe, 'title', value = title)
    cc_public.edit.field.set_field(tree, id_exe, 'brief', prose = title + '.')
    cc_public.edit.field.set_field(tree, id_exe, 'description',
                                   prose = 'Started, and not yet finished.')
    cc_public.edit.link.link(tree, id_exe, REL_RAN_UNDER, id_deployment)

    return id_exe


# -----------------------------------------------------------------------------
def _root(tree):
    """
    Return the root the tree was built from.

    """

    return tree.root


# -----------------------------------------------------------------------------
def _node(tree, graph, local, bound, generator, runner, policy, ledger,
          id_exe, root):
    """
    Run one node and return its report entry.

    """

    entry     = {'node': local, 'made': [], 'revised': [], 'verdict': {},
                 'fired': [], 'declined': [], 'commit': None}
    map_input = {}

    for (port, spec) in graph.inputs(local).items():
        if (local, port) in bound:
            map_input[port] = _text(tree, bound[(local, port)])
        elif not spec.get(KEY_OPTIONAL):
            raise Stop('{node}.input.{port} is required and was never bound; '
                       'the edge feeding it declined.'.format(node = local,
                                                              port = port))

    for (port, spec) in graph.outputs(local).items():
        id_item = _produce(tree, graph, local, port, spec, map_input,
                           generator, ledger, bound)
        bound[(local, port)] = id_item
        entry['revised' if spec.get(KEY_REVISES) else 'made'].append(id_item)

    _bind(tree, graph, local, bound, id_exe)

    report = cc_public.check.check(list_path = [root])['report']
    faults = [n['message'] for c in report['check'] for n in c['nonconformity']
                if n['severity'] == 'critical']
    if faults:
        raise Stop('After {node}, {n} critical finding(s): {first}'.format(
                            node = local, n = len(faults), first = faults[0]))

    for (port, spec) in graph.outputs(local).items():

        id_item  = bound[(local, port)]
        outgoing = graph.outgoing(local, port)
        is_gated = any(guard for (_, _, guard) in outgoing)

        if policy['judge'] == JUDGE_ALWAYS or \
                (policy['judge'] == JUDGE_GUARDS and is_gated):
            entry['verdict'][port] = _judge(tree, spec, id_item, runner,
                                            policy['confirm'])
        elif is_gated:
            raise Stop('An edge from {node}.output.{port} carries a guard, '
                       'and the deployment judges nothing.'.format(
                                                node = local, port = port))

        verdicts = [v for (_, v) in entry['verdict'].get(port, [])]

        for (node_dst, port_dst, guard) in outgoing:
            fires = (guard is None
                     or (guard == VERDICT_MET and all(v == VERDICT_MET for v in verdicts))
                     or (guard == VERDICT_UNMET and any(v == VERDICT_UNMET for v in verdicts)))
            target = f'{node_dst}.input.{port_dst}'
            if fires:
                bound[(node_dst, port_dst)] = id_item
                entry['fired'].append(target)
            else:
                entry['declined'].append(target)

    return entry


# -----------------------------------------------------------------------------
def _produce(tree, graph, local, port, spec, map_input, generator, ledger,
             bound):
    """
    Make or revise the item on one output port. Return its id.

    """

    table   = tree.type_register()[KEY_TABLE]
    id_type = spec.get(KEY_ID_TYPE)

    if id_type not in table:
        raise Stop('{node}.output.{port} carries {t}, which is not a '
                   'type.'.format(node = local, port = port, t = id_type))

    entry_type = table[id_type]
    (required, properties) = cc_public.edit.new._shape(tree, entry_type)
    list_field = [f for f in required if f not in FIELD_OWN
                  and (properties.get(f) or {}).get('type', 'string') == 'string']
    prompt     = spec.get(KEY_PROMPT) or ''

    if spec.get(KEY_REVISES):
        id_item = bound.get((local, spec[KEY_REVISES]))
        if id_item is None:
            raise Stop('{node}.output.{port} revises {src}, which is not '
                       'bound.'.format(node = local, port = port,
                                       src = spec[KEY_REVISES]))
        answer = generator.produce(prompt, map_input, list_field, False)
        ledger.note_modify(tree.resolve(id_item).filepath)
    else:
        answer  = generator.produce(prompt, map_input, list_field, True)
        guid    = entry_type[KEY_PREFIX] + '_' + uuid.uuid4().hex
        slug    = re.sub(r'[^a-z0-9_]', '_', str(answer.get('slug', '')).lower())
        id_item = entry_type[KEY_PREFIX] + '_' + slug
        if not slug or not re.fullmatch(entry_type[KEY_REGEX_ID], id_item) \
                or id_item in tree.map_id:
            id_item = '{p}_{node}_{tag}'.format(p = entry_type[KEY_PREFIX],
                                                node = local,
                                                tag = guid.split('_', 1)[1][:LENGTH_TAG])
        path = cc_public.edit.new.new(tree, id_type, id_item,
                                      cc_public.edit.tree.defaults(), guid = guid)
        ledger.note_create(path)

    for field in list_field:
        text = str(answer.get(field, '') or '')
        if not text.strip():
            continue                      # left empty: the checks will say so
        # One short line is a value; anything longer, or with a break in
        # it, is prose and goes in as a block scalar. The same line the
        # printer draws.
        #
        sub = properties.get(field) or {}
        if 'enum' in sub or 'pattern' in sub or (
                '\n' not in text.strip() and len(text.strip()) <= WIDTH_VALUE):
            cc_public.edit.field.set_field(tree, id_item, field, value = text.strip())
        else:
            cc_public.edit.field.set_field(tree, id_item, field, prose = text)

    return id_item


# -----------------------------------------------------------------------------
def _bind(tree, graph, local, bound, id_exe):
    """
    Put a binding on the execution for every bound port of the node.

    """

    node = graph.node[local]

    for (side, ports) in (('input', graph.inputs(local)),
                          ('output', graph.outputs(local))):
        for (port, spec) in ports.items():
            id_item = bound.get((local, port))
            if id_item is None:
                continue
            (_, id_bnd) = cc_public.edit.insert.insert(
                                tree, 't_binding', f'{local}_{side}_{port}_1',
                                id_exe, 'binding')
            item = tree.resolve(id_item)
            for (key, value) in (('id_node',   node['id_self']),
                                 ('guid_node', node['guid_self']),
                                 ('id_port',   spec['id_self']),
                                 ('guid_port', spec['guid_self']),
                                 ('pass',      '1')):
                cc_public.edit.field.set_field(tree, id_bnd, key, value = value)
            cc_public.edit.link.link(tree, id_bnd, REL_BINDS, item.id_self)


# -----------------------------------------------------------------------------
def _judge(tree, spec, id_item, runner, count_confirm):
    """
    Return [(id_eval, verdict)] for the evals anchored to a port.

    """

    if runner is None:
        raise Stop('The deployment judges, and no judge was given.')

    out  = []
    item = tree.resolve(id_item)
    doc  = tree.context.map_document[item.filepath]

    for edge in spec.get(KEY_RELATION) or []:
        if edge.get(KEY_ID_REL) != REL_JUDGED_BY:
            continue
        ev      = tree.resolve(edge[KEY_GUID_TGT])
        doc_ev  = tree.context.map_document[ev.filepath]
        task    = cc_public.eval.select.Task(
                        id_eval       = ev.id_self,
                        document_eval = doc_ev,
                        id_subject    = (id_item,),
                        filepath      = str(item.filepath),
                        text_input    = cc_public.eval.select._render(
                                                ((id_item, doc),), doc_ev))
        verdict = runner.run(task)
        if verdict.verdict == VERDICT_UNMET:
            verdict = runner.confirm(task, verdict, count_confirm)
        out.append((ev.id_self, verdict.verdict))

    return out


# -----------------------------------------------------------------------------
def _text(tree, id_item):
    """
    Return an item as prose, for a generator to read.

    """

    item = tree.resolve(id_item)

    return cc_public.eval.select._render(
                ((id_item, tree.context.map_document[item.filepath]),), {})


# -----------------------------------------------------------------------------
def _summary(list_entry):
    """
    Return what a run did, as prose.

    """

    lines = []

    for e in list_entry:
        lines.append('{node}: made {made}; revised {rev}; fired {f}; declined '
                     '{d}.'.format(node = e['node'],
                                   made = ', '.join(e['made']) or 'nothing',
                                   rev  = ', '.join(e['revised']) or 'nothing',
                                   f    = ', '.join(e['fired']) or 'nothing',
                                   d    = ', '.join(e['declined']) or 'nothing'))

    return '\n\n'.join(lines) or 'Nothing ran.'
