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
import json
import pathlib
import re
import uuid

import cc_public.check
import cc_public.commit
import cc_public.edit.field
import cc_public.edit.ledger
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.eval.runner
import cc_public.eval.measure
import cc_public.eval.select
import cc_public.path
import cc_public.workflow.graph


KEY_TABLE      = 'table'
KEY_PREFIX     = 'prefix'
KEY_REGEX_ID   = 'regex_id'
KEY_ID_TYPE    = 'id_type'
KEY_PROMPT     = 'prompt'
KEY_REVISES    = 'revises'
KEY_DECIDES    = 'decides'
KEY_DERIVES    = 'derives'
KEY_FIELD      = 'field'
KEY_CHALLENGER = 'challenger'
KEY_PRIORITY   = 'priority'
KEY_STATUS     = 'status'
STATUS_PROPOSED = 'proposed'
REL_DERIVED    = 'r_is_derived_from'
KEY_ADMIT      = 'admit_unmeasured'
KEY_JUDGEMENT  = 'judgement'
CARRIES_JUDGE  = 'judgement'
REL_DECIDES    = 'r_decides'
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
WIDTH_LINE     = 80

# A cut line does not end on one of these.
#
WORDS_DANGLING = {'and', 'or', 'with', 'of', 'for', 'to', 'the', 'a', 'an',
                  'by', 'in', 'on', 'at', 'from', 'as', 'but', 'nor'}

# Envelope fields the tool fills; never asked of the generator.
#
FIELD_OWN      = ('id_self', 'guid_self', 'copyright', 'license',
                  'protective_mark', 'relation', 'status')


# -----------------------------------------------------------------------------
class Stop(Exception):
    """
    Raised where a run cannot go on. The reason is the message.

    """



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
    dep    = tree.context.map_document[tree.resolve(id_deployment).filepath]
    policy = {'judge':   dep.get('judge', JUDGE_ALWAYS),
              'confirm': dep.get('confirm', cc_public.eval.runner.COUNT_CONFIRM),
              'commit':  dep.get('commit', COMMIT_RUN),
              'budget':  dep.get('budget', 1),
              'admit_unmeasured': bool(dep.get(KEY_ADMIT, False))}

    # A challenge is built by a process other than the one that made
    # the claim, or it is the claim restated. A deployment of a graph
    # with a challenging node names a second model, and it differs.
    #
    if any(graph.node[n].get(KEY_CHALLENGER) for n in graph.node) and (
            not dep.get('model_challenge')
            or dep.get('model_challenge') == dep.get('model')):
        raise Stop('The workflow has a challenging node, and the deployment '
                   'names no model_challenge different from its model.')
    if generator_challenge is None:
        generator_challenge = generator
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

    report['bound']  = {f'{n}.input.{p}': i for ((n, p), i) in bound.items()}
    policy['budget'] = _budget(tree, dep, bound.values())

    if is_dry:
        for local in report['order']:
            report['node'].append(_plan(graph, local, bound))
        return report

    if policy['commit'] != COMMIT_NEVER and cc_public.commit.changed(root):
        raise Stop('The working tree is not clean, and this deployment '
                   'commits. Commit or stash first, or deploy with commit: '
                   'never.')

    ledger = cc_public.edit.ledger.Ledger()

    try:
        id_exe = _execution(tree, ledger, graph.id_self, id_deployment)
        report['execution'] = id_exe

        # The forward order, walked once; a back edge that fires puts
        # the nodes from its target to its source back on the front of
        # the queue for another pass, while the target's budget allows.
        #
        order    = report['order']
        queue    = list(order)
        map_pass = {local: 0 for local in order}      # passes each node has run

        while queue:
            local = queue.pop(0)
            map_pass[local] += 1
            entry = _node(tree, graph, local, bound,
                          generator_challenge if graph.node[local].get(KEY_CHALLENGER)
                          else generator,
                          runner, policy, ledger, id_exe, root, map_pass)
            report['node'].append(entry)

            if entry['back']:
                node_dst = min(entry['back'], key = order.index)
                queue    = order[order.index(node_dst):order.index(local) + 1] \
                         + queue

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
    except Exception:
        ledger.restore()             # a crash leaves nothing half written
        raise

    return report


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
        doc = tree.context.map_document[tree.resolve(id_item).filepath]
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
def _execution(tree, ledger, id_workflow, id_deployment):
    """
    Make the execution record and return its id.

    """

    guid   = PREFIX_EXE + '_' + uuid.uuid4().hex
    stamp  = datetime.datetime.now(datetime.UTC).strftime(FORMAT_STAMP)
    id_exe = '{p}_{stamp}_{tag}'.format(p = PREFIX_EXE, stamp = stamp,
                                        tag = guid.split('_', 1)[1][:LENGTH_TAG])

    # Executions have a directory of their own. They accumulate, one
    # per run, and would otherwise bury the definitions they ran.
    #
    root = _root(tree)
    path = cc_public.edit.new.new(tree, 't_execution', id_exe,
                                  tree.defaults(),
                                  dirpath_out = root / DIR_EXECUTION, guid = guid)
    ledger.note_create(path)

    cc_public.edit.field.set_field(tree, id_exe, 'title',
                                   value = 'Run of ' + id_workflow)
    cc_public.edit.field.set_field(tree, id_exe, 'brief',
                                   prose = 'Under {dep}.'.format(dep = id_deployment))
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
          id_exe, root, map_pass = None):
    """
    Run one node and return its report entry.

    back lists the target node of each back edge that fired, and
    exhausted the back edges whose guard was met with no budget left.

    """

    map_pass  = map_pass if map_pass is not None else {local: 1}
    n_pass    = map_pass[local]
    entry     = {'node': local, 'pass': n_pass, 'made': [], 'revised': [],
                 'verdict': {}, 'fired': [], 'declined': [], 'back': [],
                 'exhausted': [], 'note': [], 'commit': None, 'skipped': None}
    map_input = {}

    for (port, spec) in graph.inputs(local).items():
        if (local, port) in bound:
            map_input[port] = _text(tree, bound[(local, port)])
        elif spec.get(KEY_OPTIONAL):
            continue
        elif graph.incoming(local, port):
            # The branch this node is on was not taken: the edge that
            # feeds it did not fire on this pass. The node is skipped,
            # and what it would have produced goes nowhere.
            #
            entry['skipped'] = ('{node}.input.{port} is required and the edge '
                                'feeding it did not fire.'.format(node = local,
                                                                  port = port))
            return entry
        else:
            raise Stop('{node}.input.{port} is required and nothing binds '
                       'it.'.format(node = local, port = port))

    for (port, spec) in graph.outputs(local).items():
        id_item = _produce(tree, graph, local, port, spec, map_input,
                           generator, ledger, entry, bound)
        bound[(local, port)] = id_item
        was_bound = spec.get(KEY_REVISES) and (local, spec[KEY_REVISES]) in bound
        entry['revised' if was_bound else 'made'].append(id_item)

    map_bnd = _bind(tree, graph, local, bound, id_exe, n_pass)

    refusal = cc_public.check.refusal(cc_public.check.check(list_path = [root]))
    if refusal is not None:
        raise Stop('After {node}, {why}'.format(node = local,
                                                why  = refusal.message))

    for (port, spec) in graph.outputs(local).items():

        id_item  = bound[(local, port)]
        outgoing = graph.outgoing(local, port)
        back     = graph.outgoing_back(local, port)
        is_gated = any(guard for (_, _, guard, _) in outgoing + back)

        if policy['judge'] == JUDGE_ALWAYS or \
                (policy['judge'] == JUDGE_GUARDS and is_gated):
            judgement = _judge(tree, spec, id_item, runner, policy, is_gated)
            entry['verdict'][port] = [(j['id_eval'], j['verdict']) for j in judgement]
            if judgement:
                cc_public.edit.field.set_field(tree, map_bnd[('output', port)],
                                               KEY_JUDGEMENT, value = judgement)
        elif is_gated:
            raise Stop('An edge from {node}.output.{port} carries a guard, '
                       'and the deployment judges nothing.'.format(
                                                node = local, port = port))

        verdicts = [v for (_, v) in entry['verdict'].get(port, [])]

        # What an edge delivers: the item, or the judgement of it, which
        # is the binding of this port on this pass.
        #
        def delivered(carries, id_item = id_item, id_bnd = map_bnd[('output', port)]):
            return id_bnd if carries == CARRIES_JUDGE else id_item

        # An edge that does not fire delivers nothing, and takes back
        # what it delivered on an earlier pass: a node downstream reads
        # what reached it on this pass or finds nothing, never what
        # reached it last time.
        #
        for (node_dst, port_dst, guard, carries) in outgoing:
            target = f'{node_dst}.input.{port_dst}'
            if _fires(guard, verdicts):
                bound[(node_dst, port_dst)] = delivered(carries)
                entry['fired'].append(target)
            else:
                bound.pop((node_dst, port_dst), None)
                entry['declined'].append(target)

        # A back edge returns the item for another pass. It fires only
        # while its target node has budget left; met with none, it is
        # exhausted and the run goes on without it.
        #
        for (node_dst, port_dst, guard, carries) in back:
            target = f'{node_dst}.input.{port_dst}'
            if not _fires(guard, verdicts):
                bound.pop((node_dst, port_dst), None)
                entry['declined'].append(target)
            elif map_pass.get(node_dst, 0) >= policy['budget']:
                bound.pop((node_dst, port_dst), None)
                entry['exhausted'].append(target)
            else:
                bound[(node_dst, port_dst)] = delivered(carries)
                entry['fired'].append(target)
                entry['back'].append(node_dst)

    return entry


# -----------------------------------------------------------------------------
def _produce(tree, graph, local, port, spec, map_input, generator, ledger, entry,
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
    # The fields the model fills: those the port names, else every
    # required prose field. A table field, an object of entries, is
    # filled from a list the model returns.
    #
    if spec.get(KEY_FIELD):
        list_field = [f for f in spec[KEY_FIELD] if f in properties]
    else:
        list_field = [f for f in required if f not in FIELD_OWN
                      and (properties.get(f) or {}).get('type', 'string') == 'string']
    list_table = [f for f in list_field if _is_table(properties.get(f))]
    prompt     = spec.get(KEY_PROMPT) or ''
    if list_table:
        prompt = prompt.rstrip() + '\n\n' + ' '.join(
            '{f} is a JSON list of objects, each with a key of lowercase letters and '
            'underscores and the fields the prompt names for it; answer it with the JSON '
            'and nothing else.'.format(f = f) for f in list_table)

    # A port revising an input returns that input's item, changed in
    # place. Where the input is optional and nothing is bound there, as
    # on the first pass through a loop, a new item is made instead.
    #
    id_item = bound.get((local, spec[KEY_REVISES])) if spec.get(KEY_REVISES) \
              else None

    if spec.get(KEY_REVISES) and id_item is None \
            and not graph.inputs(local)[spec[KEY_REVISES]].get(KEY_OPTIONAL):
        raise Stop('{node}.output.{port} revises {src}, which is not '
                   'bound.'.format(node = local, port = port,
                                   src = spec[KEY_REVISES]))

    # What the schema bounds, the model is told, so that a title comes
    # back within its line rather than being cut to it afterwards.
    #
    hints = ['{f} is one line of at most {n} characters'.format(
                                            f = f, n = properties[f]['maxLength'])
             for f in list_field
             if 'maxLength' in (properties.get(f) or {})
             and properties[f]['maxLength'] <= WIDTH_LINE]
    if hints:
        prompt = prompt.rstrip() + '\n\n' + '. '.join(hints) + '.'

    if id_item is not None:
        answer = generator.produce(prompt, map_input, list_field, False)
        ledger.note_modify(tree.resolve(id_item).filepath)
    else:
        answer  = generator.produce(prompt, map_input, list_field, True)
        guid    = entry_type[KEY_PREFIX] + '_' + uuid.uuid4().hex
        tag     = guid.split('_', 1)[1][:LENGTH_TAG]
        slug    = _slug(answer.get('slug', ''), entry_type[KEY_PREFIX])
        id_item = entry_type[KEY_PREFIX] + '_' + slug
        if not slug or not re.fullmatch(entry_type[KEY_REGEX_ID], id_item):
            id_item = '{p}_{node}_{tag}'.format(p = entry_type[KEY_PREFIX],
                                                node = local, tag = tag)
            entry['note'].append('{node}.output.{port}: the slug offered, {s!r}, '
                                 'was not usable; {id} minted.'.format(
                                    node = local, port = port,
                                    s = answer.get('slug', ''), id = id_item))
        elif id_item in tree.map_id:
            id_item = id_item + '_' + tag
            entry['note'].append('{node}.output.{port}: {s} is taken; {id} '
                                 'minted.'.format(node = local, port = port,
                                                  s = entry_type[KEY_PREFIX] + '_' + slug,
                                                  id = id_item))
        path = cc_public.edit.new.new(tree, id_type, id_item,
                                      tree.defaults(), guid = guid)
        ledger.note_create(path)
        if spec.get(KEY_DECIDES):
            id_decided = bound.get((local, spec[KEY_DECIDES]))
            if id_decided is None:
                raise Stop('{node}.output.{port} decides {src}, which is not '
                           'bound.'.format(node = local, port = port,
                                           src = spec[KEY_DECIDES]))
            cc_public.edit.link.link(tree, id_item, REL_DECIDES, id_decided)
        if spec.get(KEY_DERIVES):
            id_source = bound.get((local, spec[KEY_DERIVES]))
            if id_source is None:
                raise Stop('{node}.output.{port} derives from {src}, which is not '
                           'bound.'.format(node = local, port = port,
                                           src = spec[KEY_DERIVES]))
            cc_public.edit.link.link(tree, id_item, REL_DERIVED, id_source)
        # What a workflow makes is proposed until a person accepts it.
        #
        if STATUS_PROPOSED in ((properties.get(KEY_STATUS) or {}).get('enum') or []) \
                and KEY_STATUS not in list_field:
            cc_public.edit.field.set_field(tree, id_item, KEY_STATUS, value = STATUS_PROPOSED)

    for field in list_field:
        text = str(answer.get(field, '') or '')
        if not text.strip():
            continue                      # left empty: the checks will say so
        if field in list_table:
            _fill_table(tree, id_item, field, text, entry)
            continue
        # A field the schema bounds to a line is one line whatever the
        # model returned, so its whitespace is collapsed. Otherwise one
        # short line is a value and anything longer is prose, the same
        # line the printer draws.
        #
        sub     = properties.get(field) or {}
        is_line = 'maxLength' in sub and sub['maxLength'] <= WIDTH_LINE
        if is_line:
            text = _line(' '.join(text.split()), sub['maxLength'])
        if is_line or 'enum' in sub or 'pattern' in sub or (
                '\n' not in text.strip() and len(text.strip()) <= WIDTH_VALUE):
            cc_public.edit.field.set_field(tree, id_item, field, value = text.strip())
        else:
            cc_public.edit.field.set_field(tree, id_item, field, prose = text)

    return id_item


# -----------------------------------------------------------------------------
def _is_table(subschema):
    return isinstance(subschema, dict) and subschema.get('type') == 'object' \
           and isinstance(subschema.get('additionalProperties'), dict)


# -----------------------------------------------------------------------------
def _fill_table(tree, id_item, field, text, entry):
    """
    Insert one entry under field for each object in the JSON list the
    model returned. The entry's type is the table's name: assumption
    holds t_assumption, question holds t_question. A list that does
    not parse is noted and the table left empty.

    """

    start = text.find('[')
    end   = text.rfind(']')
    try:
        list_row = json.loads(text[start:end + 1]) if start >= 0 <= end else None
    except ValueError:
        list_row = None

    if not isinstance(list_row, list):
        entry['note'].append('{item}.{field}: the model did not return a JSON '
                             'list; left empty.'.format(item = id_item, field = field))
        return

    # The list replaces the table: an entry whose key is kept keeps its
    # identity and takes the new fields, a new key is inserted, and a
    # key the model no longer returns is removed.
    #
    item_doc = tree.context.map_document[tree.resolve(id_item).filepath]
    existing = dict(item_doc.get(field) or {})
    kept     = set()

    for (n, row) in enumerate(list_row):
        if not isinstance(row, dict):
            continue
        name = _slug(row.get('key', ''), '') or 'a{n}'.format(n = n + 1)
        kept.add(name)
        if name in existing:
            id_entry = existing[name]['id_self']
        else:
            try:
                (_, id_entry) = cc_public.edit.insert.insert(tree, 't_' + field, name,
                                                             id_item, field)
            except cc_public.edit.tree.ErrorItem as err:
                entry['note'].append('{item}.{field}: {err}'.format(item = id_item,
                                                                    field = field, err = err))
                continue
        for (key, value) in row.items():
            if key in ('key', 'id_self', 'guid_self') or not isinstance(value, str) \
                    or not value.strip():
                continue
            cc_public.edit.field.set_field(tree, id_entry, key, prose = value)

    for name in existing:
        if name not in kept:
            cc_public.edit.field.unset_field(tree, id_item,
                                             cc_public.path.join(field, name))


# -----------------------------------------------------------------------------
def _line(text, width):
    """
    Return text cut to width at a word boundary, where it is longer.

    A model told the bound and overrunning it anyway would otherwise
    stop the whole run on a title, and the ledger would throw the pass
    away. A cut title is visible and cheap to mend; a lost pass is not.

    """

    if len(text) <= width:
        return text

    words = text[:width].rsplit(' ', 1)[0].split(' ')

    while words and words[-1].rstrip(',;:').lower() in WORDS_DANGLING:
        words.pop()

    cut = ' '.join(words).rstrip(' ,;:')

    return cut or text[:width]


# -----------------------------------------------------------------------------
def _slug(offered, prefix):
    """
    Return the slug a model offered as the body of a readable id: lower
    case, runs of anything else made one underscore, a repeated type
    prefix dropped, and nothing at either end.

    """

    slug = re.sub(r'[^a-z0-9]+', '_', str(offered or '').lower()).strip('_')

    if slug.startswith(prefix + '_'):
        slug = slug[len(prefix) + 1:]

    return slug


# -----------------------------------------------------------------------------
def _bind(tree, graph, local, bound, id_exe, n_pass = 1):
    """
    Put a binding on the execution for every bound port of the node.
    Return {(side, port): id_binding}.

    """

    node = graph.node[local]
    out  = {}

    for (side, ports) in (('input', graph.inputs(local)),
                          ('output', graph.outputs(local))):
        for (port, spec) in ports.items():
            id_item = bound.get((local, port))
            if id_item is None:
                continue
            (_, id_bnd) = cc_public.edit.insert.insert(
                                tree, 't_binding', f'{local}_{side}_{port}_{n_pass}',
                                id_exe, 'binding')
            item = tree.resolve(id_item)
            for (key, value) in (('id_node',   node['id_self']),
                                 ('guid_node', node['guid_self']),
                                 ('id_port',   spec['id_self']),
                                 ('guid_port', spec['guid_self']),
                                 ('pass',      n_pass)):
                cc_public.edit.field.set_field(tree, id_bnd, key, value = value)
            cc_public.edit.link.link(tree, id_bnd, REL_BINDS, item.id_self)
            out[(side, port)] = id_bnd

    return out


# -----------------------------------------------------------------------------
def _judge(tree, spec, id_item, runner, policy, is_gated):
    """
    Return the judgement of a port: one row per eval anchored to it, with
    the verdict and the judge's reason.

    A guarded port decides what happens next, so an eval guarding one
    must carry current confidence for the judge in use, or the
    deployment must say that an unmeasured judge is admitted.

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
        if is_gated and not policy['admit_unmeasured'] and not any(
                isinstance(row, dict) and row.get('model') == runner.id_model
                and cc_public.eval.measure.is_current(row, doc_ev,
                                                      tree.context.map_document)
                for row in doc_ev.get('confidence') or []):
            raise Stop('{ev} guards an edge and carries no current confidence '
                       'for {model}. Measure it, or deploy with '
                       'admit_unmeasured: true.'.format(ev    = ev.id_self,
                                                        model = runner.id_model))
        task    = cc_public.eval.select.Task(
                        id_eval       = ev.id_self,
                        document_eval = doc_ev,
                        id_subject    = (id_item,),
                        filepath      = str(item.filepath),
                        text_input    = cc_public.eval.select._render(
                                                ((id_item, doc),), doc_ev))
        verdict = runner.run(task)
        if verdict.verdict == VERDICT_UNMET:
            verdict = runner.confirm(task, verdict, policy['confirm'])
        out.append({'id_eval':   ev.id_self,
                    'guid_eval': ev.guid_self,
                    'verdict':   verdict.verdict,
                    'criterion': str(doc_ev.get('criterion', '')).rstrip('\n') + '\n',
                    'reason':    (' '.join(str(verdict.feedback or '').split())
                                  or 'No reason given.') + '\n'})   # prose

    return out


# -----------------------------------------------------------------------------
def _text(tree, id_item):
    """
    Return an item as prose, for a generator to read.

    """

    item = tree.resolve(id_item)
    node = tree.context.map_document[item.filepath]

    for step in cc_public.path.split(item.path):       # an embedded item
        node = node[int(step)] if isinstance(node, list) else node[step]

    return cc_public.eval.select._render(((id_item, node),), {})


# -----------------------------------------------------------------------------
def _summary(list_entry):
    """
    Return what a run did, as prose.

    """

    lines = []

    for e in list_entry:
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
