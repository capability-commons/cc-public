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
                        and walks them, keeping what a run carries
                        from node to node in one state. Each node has
                        its output ports materialised by the produce
                        module, its bindings put on the execution, the
                        checks run, its ports judged as the deployment
                        says and its edges fired by their guards. A
                        critical finding or an incomplete analysis
                        stops the run, and a stopped run restores
                        every file it touched. A finished one commits
                        as the deployment says.
relation:               []

...
"""


import datetime
import pathlib
import uuid

import cc_public.check
import cc_public.check.confidence
import cc_public.commit
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.ledger
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.path
import cc_public.workflow
import cc_public.workflow.graph
import cc_public.workflow.agent
import cc_public.workflow.code
import cc_public.workflow.produce


KEY_ID_TYPE    = 'id_type'
KEY_REVISES    = 'revises'
KEY_CHALLENGER = 'challenger'
KEY_PRIORITY   = 'priority'
KEY_ADMIT      = 'admit_unmeasured'
KEY_JUDGEMENT  = 'judgement'
CARRIES_JUDGE  = 'judgement'
KEY_OPTIONAL   = 'optional'
KEY_RELATION   = 'relation'
KEY_ID_REL     = 'id_relation'
KEY_GUID_TGT   = 'guid_target'
KEY_MODEL      = 'model'
KEY_CONFIDENCE = 'confidence'
KEY_OUTCOME    = 'outcome'

OUTCOME_COMPLETED = 'completed'
OUTCOME_EXHAUSTED = 'exhausted'
OUTCOME_WAITING   = 'waiting'
KEY_PERFORMER     = 'performer'
PERFORMER_AGENT   = 'agent'
KEY_STATE         = 'state'
SIDE_INPUT        = 'input'
SIDE_OUTPUT       = 'output'
KEY_WAITING       = 'waiting'
REL_DEPLOYS       = 'r_deploys'

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

Stop = cc_public.workflow.Stop


# -----------------------------------------------------------------------------
class State:
    """
    What one run carries from node to node.

    The tree and the graph, the policy read from the deployment, the
    generators and the judge, the ledger of what has been written, the
    execution being recorded, the bindings of every port so far, and
    how many passes each node has taken.

    """

    def __init__(self, root, tree, graph, policy, generator, generator_challenge,
                 runner):
        self.root                = root
        self.tree                = tree
        self.graph               = graph
        self.policy              = policy
        self.generator           = generator
        self.generator_challenge = generator_challenge
        self.runner              = runner
        self.ledger              = cc_public.edit.ledger.Ledger()
        self.id_exe              = None
        self.bound               = {}
        self.map_pass            = {}
        self.resumed   = None       # the agent node a resumed segment starts at


    # -------------------------------------------------------------------------
    def generator_for(self, local):
        """
        Return the generator a node runs on: the challenging one where
        the node challenges.

        """

        return self.generator_challenge if self.graph.node[local].get(KEY_CHALLENGER) \
               else self.generator


# -----------------------------------------------------------------------------
def run(root, id_workflow, id_deployment, map_bind, generator, runner,
        is_dry = False, list_trailer = (), generator_challenge = None):
    """
    Run the workflow and return the report.

    map_bind maps 'node.input.port' to the readable id of the item
    bound there. runner judges; it may be None where the deployment
    judges nothing. generator_challenge is what a challenging node
    runs on; absent, the generator, which a deployment naming two
    models does not allow.

    """

    root   = pathlib.Path(root).resolve()
    tree   = cc_public.edit.tree.Tree([root])
    graph  = cc_public.workflow.graph.Graph(tree, id_workflow)
    dep    = tree.context.map_document[tree.resolve(id_deployment).location]
    state  = State(root, tree, graph, _policy(dep, graph), generator,
                   generator_challenge or generator, runner)
    report = {'workflow': graph.id_self, 'deployment': id_deployment,
              'policy': state.policy, 'order': graph.order(), 'node': [],
              'execution': None, 'commit': None, 'stopped': None, 'outcome': None}

    state.bound = _bound(tree, graph, map_bind)
    report['bound'] = {f'{n}.input.{p}': i for ((n, p), i) in state.bound.items()}
    state.policy['budget'] = _budget(tree, dep, state.bound.values())

    if is_dry:
        report['node'] = [_plan(graph, local, state.bound) for local in report['order']]
        return report

    if state.policy['commit'] != COMMIT_NEVER and cc_public.commit.changed(root):
        raise Stop('The working tree is not clean, and this deployment '
                   'commits. Commit or stash first, or deploy with commit: '
                   'never.')

    try:
        _execute(state, report, id_deployment, list_trailer)
    except Stop as stop:
        state.ledger.restore()
        report['stopped'] = str(stop)
        if state.policy['commit'] != COMMIT_NODE:
            report['execution'] = None
    except Exception:
        state.ledger.restore()       # a crash leaves nothing half written
        raise

    return report


# -----------------------------------------------------------------------------
def _policy(dep, graph):
    """
    Return the run's policy, read from the deployment.

    A challenge is built by a process other than the one that made the
    claim, or it is the claim restated. A deployment of a graph with a
    challenging node names a second model, and it differs.

    """

    if any(graph.node[n].get(KEY_CHALLENGER) for n in graph.node) and (
            not dep.get('model_challenge')
            or dep.get('model_challenge') == dep.get(KEY_MODEL)):
        raise Stop('The workflow has a challenging node, and the deployment '
                   'names no model_challenge different from its model.')

    return {'judge':   dep.get('judge', JUDGE_ALWAYS),
            'confirm': dep.get('confirm', cc_public.eval.runner.COUNT_CONFIRM),
            'commit':  dep.get('commit', COMMIT_RUN),
            'budget':  dep.get('budget', 1),
            'admit_unmeasured': bool(dep.get(KEY_ADMIT, False))}


# -----------------------------------------------------------------------------
def _bound(tree, graph, map_bind):
    """
    Return {(node, port): id_item} for the graph's inputs, from the
    bindings given. Every required one must be given, and none may be
    fed by an edge.

    """

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

    return bound


# -----------------------------------------------------------------------------
def _execute(state, report, id_deployment, list_trailer):
    """
    Make the execution record, then walk the nodes.

    """

    state.id_exe        = _execution(state, report['workflow'], id_deployment)
    report['execution'] = state.id_exe
    state.map_pass      = dict.fromkeys(report['order'], 0)
    _walk(state, report, list(report['order']), id_deployment, list_trailer)


# -----------------------------------------------------------------------------
def _walk(state, report, queue, id_deployment, list_trailer):
    """
    Walk the queued nodes, and commit as the policy says.

    The forward order is walked once; a back edge that fires puts the
    nodes from its target to its source back on the front of the queue
    for another pass, while the target's budget allows. An agent node
    parks the run: its state goes on the record and the walk returns,
    for resume to take up.

    """

    while queue:
        local = queue.pop(0)
        state.map_pass[local] += 1
        entry = _node(state, local)

        if entry.get('waiting'):
            _park(state, report, local, queue, entry, list_trailer)
            return

        _after(state, report, local, entry, queue, list_trailer)

    _finish(state, report, id_deployment, list_trailer)


# -----------------------------------------------------------------------------
def _after(state, report, local, entry, queue, list_trailer):
    """
    Record a node's entry, requeue for a back edge that fired, and
    commit the node as the policy says.

    """

    order = report['order']
    report['node'].append(entry)

    if entry['back']:
        node_dst = min(entry['back'], key = order.index)
        queue[:0] = order[order.index(node_dst):order.index(local) + 1]

    if state.policy['commit'] == COMMIT_NODE:
        entry['commit'] = _commit(state, 'Run {wf}: {node}'.format(
                                            wf = report['workflow'], node = local),
                                  [entry], list_trailer)


# -----------------------------------------------------------------------------
def _finish(state, report, id_deployment, list_trailer):
    """
    Close the record: how the run ended is a field, so that a run the
    budget cut short cannot be read as one the guards let finish.

    """

    report['outcome'] = OUTCOME_EXHAUSTED if any(e['exhausted'] for e in report['node']) \
                        else OUTCOME_COMPLETED
    for key in (KEY_STATE, KEY_WAITING):
        if key in state.tree.context.map_document[state.tree.resolve(state.id_exe).location]:
            cc_public.edit.field.unset_field(state.tree, state.id_exe, key)
    cc_public.edit.field.set_field(state.tree, state.id_exe, KEY_OUTCOME,
                                   value = report['outcome'])
    cc_public.edit.field.set_field(state.tree, state.id_exe, 'description',
                                   prose = _summary(report['node']))

    # A deployment that commits per node has committed every node; the
    # closing of the record is the last thing left to commit.
    #
    if state.policy['commit'] == COMMIT_RUN:
        report['commit'] = _commit(state, 'Run {wf} under {dep}'.format(
                                            wf = report['workflow'], dep = id_deployment),
                                   report['node'], list_trailer)
    elif state.policy['commit'] == COMMIT_NODE:
        report['commit'] = _commit(state, 'Run {wf}: {outcome}'.format(
                                            wf = report['workflow'], outcome = report['outcome']),
                                   report['node'], list_trailer)


# -----------------------------------------------------------------------------
def _park(state, report, local, queue, entry, list_trailer):
    """
    Put the run's state on the record and mark it waiting at the node,
    committing where the policy commits at all, so that the performer
    starts from a clean tree.

    """

    tree = state.tree
    report['node'].append(entry)
    report['outcome'] = OUTCOME_WAITING
    _bind(state, local, state.map_pass[local], (SIDE_INPUT,))

    bound = [{'port': f'{node}.input.{port}', 'id_item': id_item,
              'guid_item': tree.resolve(id_item).guid_self}
             for ((node, port), id_item) in sorted(state.bound.items())]
    cc_public.edit.field.set_field(tree, state.id_exe, KEY_STATE,
                                   value = {'queue': list(queue),
                                            'pass':  dict(state.map_pass),
                                            'bound': bound})
    cc_public.edit.field.set_field(tree, state.id_exe, KEY_WAITING,
                                   value = {'node': local, 'brief': entry['waiting']})
    cc_public.edit.field.set_field(tree, state.id_exe, KEY_OUTCOME, value = OUTCOME_WAITING)
    cc_public.edit.field.set_field(tree, state.id_exe, 'description',
                                   prose = 'Waiting at {node}.'.format(node = local))

    if state.policy['commit'] != COMMIT_NEVER:
        entry['commit'] = _commit(state, 'Run {wf}: waiting at {node}'.format(
                                            wf = report['workflow'], node = local),
                                  [entry], list_trailer)


# -----------------------------------------------------------------------------
def resume(root, id_execution, generator, runner, list_trailer = (),
           generator_challenge = None):
    """
    Continue a waiting run from its execution record and return the
    report: the agent node's outputs are read from the tree, and the
    walk goes on from there.

    """

    root   = pathlib.Path(root).resolve()
    tree   = cc_public.edit.tree.Tree([root])
    record = tree.context.map_document[tree.resolve(id_execution).location]

    if record.get(KEY_OUTCOME) != OUTCOME_WAITING:
        raise Stop('{exe} is not waiting; its outcome is {o}.'.format(
                        exe = id_execution, o = record.get(KEY_OUTCOME)))

    id_deployment = _target(record, REL_RAN_UNDER)
    dep           = tree.context.map_document[tree.resolve(id_deployment).location]
    id_workflow   = _target(dep, REL_DEPLOYS)
    graph         = cc_public.workflow.graph.Graph(tree, id_workflow)
    state         = State(root, tree, graph, _policy(dep, graph), generator,
                          generator_challenge or generator, runner)
    local         = record[KEY_WAITING]['node']
    report        = {'workflow': graph.id_self, 'deployment': id_deployment,
                     'policy': state.policy, 'order': graph.order(), 'node': [],
                     'execution': id_execution, 'commit': None, 'stopped': None,
                     'outcome': None, 'resumed': local}

    state.id_exe   = id_execution
    state.resumed  = local
    state.map_pass = dict(record[KEY_STATE]['pass'])
    state.bound    = {tuple(b['port'].split('.')[::2]): b['id_item']
                      for b in record[KEY_STATE]['bound']}
    report['bound'] = {f'{n}.input.{p}': i for ((n, p), i) in state.bound.items()}
    state.policy['budget'] = _budget(tree, dep, state.bound.values())

    if state.policy['commit'] != COMMIT_NEVER and cc_public.commit.changed(root):
        raise Stop('The working tree is not clean, and this deployment '
                   'commits. Commit or stash first.')

    # The record is this segment's to change, and a stop puts it back
    # to waiting with the brief it had.
    #
    state.ledger.note_modify(tree.resolve(id_execution).filepath)

    try:
        entry = _node(state, local)
        _after(state, report, local, entry, queue := list(record[KEY_STATE]['queue']),
               list_trailer)
        _walk(state, report, queue, id_deployment, list_trailer)
    except Stop as stop:
        state.ledger.restore()
        report['stopped'] = str(stop)
        report['outcome'] = OUTCOME_WAITING
    except Exception:
        state.ledger.restore()
        raise

    return report


# -----------------------------------------------------------------------------
def _target(document, id_relation):
    """
    Return the readable id at the end of the document's edge of the
    relation.

    """

    for edge in document.get(KEY_RELATION) or []:
        if edge.get(KEY_ID_REL) == id_relation:
            return edge['id_target']

    raise Stop('{id} carries no {rel} edge.'.format(id = document.get('id_self'),
                                                    rel = id_relation))


# -----------------------------------------------------------------------------
def _commit(state, title, list_entry, list_trailer):
    """
    Commit what the run has written so far and return the hash. What
    is committed is durable, so the ledger forgets it.

    """

    (hash, _) = cc_public.commit.commit(state.root, title,
                                        description  = _summary(list_entry),
                                        id_execution = state.id_exe,
                                        list_trailer = list_trailer)
    state.ledger.clear()

    return hash


# -----------------------------------------------------------------------------
def _fires(guard, verdicts):
    """
    Return whether an edge with this guard fires on these verdicts: an
    unguarded edge always, met when every verdict is met, unmet when any
    is.

    """

    return (guard is None
            or (guard == VERDICT_MET and all(v == VERDICT_MET for v in verdicts))
            or (guard == VERDICT_UNMET and any(v == VERDICT_UNMET for v in verdicts)))


# -----------------------------------------------------------------------------
def _budget(tree, dep, list_id_bound):
    """
    Return the most passes a node may take: the budget by the highest
    priority among what is bound, where the deployment gives one, else
    the budget.

    """

    by_priority = dep.get('budget_by_priority') or {}
    found       = []

    for id_item in list_id_bound:
        doc = tree.context.map_document[tree.resolve(id_item).location]
        for step in cc_public.path.split(tree.resolve(id_item).path):
            doc = doc[int(step)] if isinstance(doc, list) else doc[step]
        if isinstance(doc, dict) and doc.get(KEY_PRIORITY) in by_priority:
            found.append(by_priority[doc[KEY_PRIORITY]])

    return max(found) if found else dep.get('budget', 1)


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
def _execution(state, id_workflow, id_deployment):
    """
    Make the execution record and return its id.

    Executions have a directory of their own. They accumulate, one per
    run, and would otherwise bury the definitions they ran.

    """

    tree   = state.tree
    guid   = PREFIX_EXE + '_' + uuid.uuid4().hex
    stamp  = datetime.datetime.now(datetime.UTC).strftime(FORMAT_STAMP)
    id_exe = '{p}_{stamp}_{tag}'.format(p = PREFIX_EXE, stamp = stamp,
                                        tag = guid.split('_', 1)[1][:LENGTH_TAG])
    path   = cc_public.edit.new.new(tree, 't_execution', id_exe, tree.defaults(),
                                    dirpath_out = state.root / DIR_EXECUTION,
                                    guid = guid)
    state.ledger.note_create(path)

    cc_public.edit.field.set_field(tree, id_exe, 'title',
                                   value = 'Run of ' + id_workflow)
    cc_public.edit.field.set_field(tree, id_exe, 'brief',
                                   prose = 'Under {dep}.'.format(dep = id_deployment))
    cc_public.edit.field.set_field(tree, id_exe, 'description',
                                   prose = 'Started, and not yet finished.')
    cc_public.edit.link.link(tree, id_exe, REL_RAN_UNDER, id_deployment)

    return id_exe


# -----------------------------------------------------------------------------
def _node(state, local):
    """
    Run one node and return its report entry.

    back lists the target node of each back edge that fired, and
    exhausted the back edges whose guard was met with no budget left.

    """

    n_pass    = state.map_pass[local]
    entry     = {'node': local, 'pass': n_pass, 'made': [], 'revised': [],
                 'verdict': {}, 'fired': [], 'declined': [], 'back': [],
                 'exhausted': [], 'note': [], 'commit': None, 'skipped': None,
                 'waiting': None}
    map_id = _inputs(state, local, entry)

    if map_id is None:
        return entry

    # A function runs once for the node and fills every output port; a
    # model is asked once per port, with its inputs rendered as prose;
    # an agent parks the run, and on resume its outputs are read from
    # the tree.
    #
    component = state.graph.component[local]
    is_agent  = component.get(KEY_PERFORMER) == PERFORMER_AGENT
    found     = cc_public.workflow.code.implementation(state.tree, component)

    outputs = state.graph.outputs(local)

    if is_agent and state.resumed != local:
        entry['waiting'] = cc_public.workflow.agent.brief(state, local, state.id_exe, map_id)
        return entry
    if is_agent:
        map_output    = cc_public.workflow.agent.outputs(state, local, map_id)
        state.resumed = None
    elif found is not None:
        (raw, set_new) = cc_public.workflow.code.call(state, local, found, map_id)
        map_output     = {port: cc_public.workflow.code.output(state, local, port, spec,
                                                               raw, set_new)
                          for (port, spec) in outputs.items()}
    else:
        map_output = None
        map_input  = {port: cc_public.workflow.produce.render(state.tree, id_item)
                      for (port, id_item) in map_id.items()}

    for (port, spec) in outputs.items():
        was_bound = spec.get(KEY_REVISES) and (local, spec[KEY_REVISES]) in state.bound
        id_item   = (map_output[port] if map_output is not None else
                     cc_public.workflow.produce.produce(state, local, port, spec,
                                                        map_input, entry))
        state.bound[(local, port)] = id_item
        entry['revised' if was_bound else 'made'].append(id_item)

    # A park bound the inputs of an agent node already.
    #
    map_bnd = _bind(state, local, n_pass, (SIDE_OUTPUT,) if is_agent
                                          else (SIDE_INPUT, SIDE_OUTPUT))
    refusal = cc_public.check.refusal(cc_public.check.check(list_path = [state.root]))

    if refusal is not None:
        raise Stop('After {node}, {why}'.format(node = local, why = refusal.message))

    for (port, spec) in state.graph.outputs(local).items():
        _deliver(state, local, port, spec, entry, map_bnd[('output', port)])

    return entry


# -----------------------------------------------------------------------------
def _inputs(state, local, entry):
    """
    Return {port: id} for the node's bound inputs, or None where the
    node is skipped on this pass.

    A required input fed by an edge that did not fire means the branch
    this node is on was not taken: the node is skipped, the entry says
    so, and what it would have produced goes nowhere.

    """

    map_input = {}

    for (port, spec) in state.graph.inputs(local).items():
        if (local, port) in state.bound:
            map_input[port] = state.bound[(local, port)]
        elif spec.get(KEY_OPTIONAL):
            continue
        elif state.graph.incoming(local, port):
            entry['skipped'] = ('{node}.input.{port} is required and the edge '
                                'feeding it did not fire.'.format(node = local,
                                                                  port = port))
            return None
        else:
            raise Stop('{node}.input.{port} is required and nothing binds '
                       'it.'.format(node = local, port = port))

    return map_input


# -----------------------------------------------------------------------------
def _deliver(state, local, port, spec, entry, id_bnd):
    """
    Judge one output port as the policy says, then fire its edges.

    An edge that does not fire delivers nothing, and takes back what it
    delivered on an earlier pass: a node downstream reads what reached
    it on this pass or finds nothing, never what reached it last time.
    A back edge fires only while its target node has budget left; met
    with none, it is exhausted and the run goes on without it.

    """

    id_item  = state.bound[(local, port)]
    outgoing = state.graph.outgoing(local, port)
    back     = state.graph.outgoing_back(local, port)
    is_gated = any(guard for (_, _, guard, _) in outgoing + back)
    policy   = state.policy

    if policy['judge'] == JUDGE_ALWAYS or (policy['judge'] == JUDGE_GUARDS and is_gated):
        judgement = _judge(state, spec, id_item, is_gated)
        entry['verdict'][port] = [(j['id_eval'], j['verdict']) for j in judgement]
        if judgement:
            cc_public.edit.field.set_field(state.tree, id_bnd, KEY_JUDGEMENT,
                                           value = judgement)
    elif is_gated:
        raise Stop('An edge from {node}.output.{port} carries a guard, '
                   'and the deployment judges nothing.'.format(node = local, port = port))

    verdicts = [v for (_, v) in entry['verdict'].get(port, [])]

    for (node_dst, port_dst, guard, carries) in outgoing + back:
        is_back = (node_dst, port_dst, guard, carries) in back
        target  = f'{node_dst}.input.{port_dst}'
        if not _fires(guard, verdicts):
            state.bound.pop((node_dst, port_dst), None)
            entry['declined'].append(target)
        elif is_back and state.map_pass.get(node_dst, 0) >= policy['budget']:
            state.bound.pop((node_dst, port_dst), None)
            entry['exhausted'].append(target)
        else:
            state.bound[(node_dst, port_dst)] = id_bnd if carries == CARRIES_JUDGE \
                                                else id_item
            entry['fired'].append(target)
            if is_back:
                entry['back'].append(node_dst)


# -----------------------------------------------------------------------------
def _bind(state, local, n_pass, sides = (SIDE_INPUT, SIDE_OUTPUT)):
    """
    Put a binding on the execution for every bound port of the node on
    the sides given. Return {(side, port): id_binding}.

    """

    tree = state.tree
    node = state.graph.node[local]
    out  = {}

    for (side, ports) in ((SIDE_INPUT, state.graph.inputs(local)),
                          (SIDE_OUTPUT, state.graph.outputs(local))):
        if side not in sides:
            continue
        for (port, spec) in ports.items():
            id_item = state.bound.get((local, port))
            if id_item is None:
                continue
            (_, id_bnd) = cc_public.edit.insert.insert(
                                tree, 't_binding', f'{local}_{side}_{port}_{n_pass}',
                                state.id_exe, 'binding')
            for (key, value) in (('id_node',   node['id_self']),
                                 ('guid_node', node['guid_self']),
                                 ('id_port',   spec['id_self']),
                                 ('guid_port', spec['guid_self']),
                                 ('pass',      n_pass)):
                cc_public.edit.field.set_field(tree, id_bnd, key, value = value)
            cc_public.edit.link.link(tree, id_bnd, REL_BINDS, tree.resolve(id_item).id_self)
            out[(side, port)] = id_bnd

    return out


# -----------------------------------------------------------------------------
def _judge(state, spec, id_item, is_gated):
    """
    Return the judgement of a port: one row per eval anchored to it, with
    the verdict and the judge's reason.

    A guarded port decides what happens next, so an eval guarding one
    must carry current confidence for the judge in use, or the
    deployment must say that an unmeasured judge is admitted.

    """

    runner = state.runner

    if runner is None:
        raise Stop('The deployment judges, and no judge was given.')

    tree = state.tree
    out  = []
    item = tree.resolve(id_item)
    doc  = tree.context.map_document[item.location]

    for edge in spec.get(KEY_RELATION) or []:
        if edge.get(KEY_ID_REL) != REL_JUDGED_BY:
            continue
        ev      = tree.resolve(edge[KEY_GUID_TGT])
        doc_ev  = tree.context.map_document[ev.location]
        if is_gated and not state.policy['admit_unmeasured'] \
                and not _measured(doc_ev, runner.id_model, tree.context.map_document):
            raise Stop('{ev} guards an edge and carries no current confidence '
                       'for {model}. Measure it, or deploy with '
                       'admit_unmeasured: true.'.format(ev    = ev.id_self,
                                                        model = runner.id_model))
        task    = cc_public.eval.select.Task(
                        id_eval       = ev.id_self,
                        document_eval = doc_ev,
                        id_subject    = (id_item,),
                        filepath      = str(item.filepath),
                        text_input    = cc_public.eval.select.render(
                                                ((id_item, doc, item.location),), doc_ev))
        verdict = runner.run(task)
        if verdict.verdict == VERDICT_UNMET:
            verdict = runner.confirm(task, verdict, state.policy['confirm'])
        out.append({'id_eval':   ev.id_self,
                    'guid_eval': ev.guid_self,
                    'verdict':   verdict.verdict,
                    'criterion': str(doc_ev.get('criterion', '')).rstrip('\n') + '\n',
                    'reason':    (' '.join(str(verdict.feedback or '').split())
                                  or 'No reason given.') + '\n'})   # prose

    return out


# -----------------------------------------------------------------------------
def _measured(doc_ev, id_model, map_document):
    """
    Return whether the eval carries current confidence for the model.

    """

    return any(isinstance(row, dict) and row.get(KEY_MODEL) == id_model
               and cc_public.check.confidence.is_current(row, doc_ev, map_document)
               for row in doc_ev.get(KEY_CONFIDENCE) or [])


# -----------------------------------------------------------------------------
def _summary(list_entry):
    """
    Return what a run did, as prose.

    """

    lines = []

    for e in list_entry:
        if e.get('waiting'):
            lines.append('{node}, pass {n}: parked for a performer.'.format(
                            node = e['node'], n = e.get('pass', 1)))
            continue
        if e.get('skipped'):
            lines.append('{node}, pass {n}: skipped, {why}'.format(
                            node = e['node'], n = e.get('pass', 1), why = e['skipped']))
            continue
        lines.append('{node}, pass {n}: made {made}; revised {rev}; fired {f}; declined '
                     '{d}.'.format(node = e['node'], n = e.get('pass', 1),
                                   made = ', '.join(e['made']) or 'nothing',
                                   rev  = ', '.join(e['revised']) or 'nothing',
                                   f    = ', '.join(e['fired']) or 'nothing',
                                   d    = ', '.join(e['declined']) or 'nothing'))

    return '\n\n'.join(lines) or 'Nothing ran.'
