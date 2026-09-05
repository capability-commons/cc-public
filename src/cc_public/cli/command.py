"""
---

id_self:                pym_cc_public.cli.command
guid_self:              pym_87dddb59e2b44e55960145b2a832cb3d
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Command definitions
brief:                  |
                        The commands the tool offers.
description:            |
                        Declares the options, invokes the checks, and
                        turns the resulting report into an exit
                        status. Holds no knowledge of what checks
                        exist or what they look for.

...
"""


import pathlib
import sys

import click

import dotenv
import ruamel.yaml

import cc_public.check
import cc_public.check.schema
import cc_public.commit
import cc_public.edit.case
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.rename
import cc_public.edit.tree
import cc_public.cli.report
import cc_public.eval.control
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.layout
import cc_public.load.git
import cc_public.question
import cc_public.workflow.generate
import cc_public.workflow.graph
import cc_public.workflow.run


EXIT_OK            = 0
EXIT_NONCONFORMITY = 1
EXIT_ERROR         = 2


# -----------------------------------------------------------------------------
class Odd(click.ParamType):
    """
    An odd positive integer: a count of judgements a majority exists over.

    """

    name = 'odd integer'

    def convert(self, value, param, ctx):
        try:
            return cc_public.eval.runner.check_count(int(value), 'The count')
        except ValueError as err:
            self.fail(str(err), param, ctx)


ODD = Odd()


# -----------------------------------------------------------------------------
@click.group()
def main():
    """
    Capability commons tooling.

    """

    # Credentials for a judge are read from the environment, and a .env
    # file is a convenience for a working copy rather than a place to
    # keep anything in a deployed one.
    #
    dotenv.load_dotenv()


# -----------------------------------------------------------------------------
@main.command()
@click.option('--path',
              'list_path',
              multiple = True,
              type     = click.Path(path_type = pathlib.Path),
              help     = 'A file or directory tree to check. May be given '
                         'more than once, and the check runs over the union '
                         'of all of them. Defaults to the working directory.')
@click.option('--fail-on-nonconformity',
              'is_fail_on_nonconformity',
              is_flag = True,
              help    = 'Exit non zero on a critical nonconformity. '
                        'Advisories never affect the exit status, since an '
                        'unresolved reference is ordinary in a federated '
                        'slice. Without this flag only a failure of the '
                        'analysis itself is reported in the exit status. Set '
                        'it for a continuous integration gate; leave it unset '
                        'for an agentic process that reads the report.')
@click.option('--fail-fast',
              'is_fail_fast',
              is_flag = True,
              help    = 'Stop at the first critical nonconformity and report '
                        'only that one. Advisories neither stop the run nor '
                        'get trimmed. Set this where the feedback loop '
                        'matters more than completeness.')
@click.option('--closed-world',
              'is_closed_world',
              is_flag = True,
              help    = 'Assert that the paths given hold everything a '
                        'reference could resolve to. A reference that does '
                        'not resolve is then a fault rather than a sharing '
                        'boundary, and is reported as critical rather than '
                        'advisory. Set this for a single repository; leave '
                        'it unset for a federated slice.')
@click.option('--eval',
              'is_eval',
              is_flag = True,
              help    = 'Run the evals. Off by default, because an eval '
                        'costs tokens and seconds where every other check '
                        'costs nothing. Any selector below implies this.')
@click.option('--id-eval',    'id_eval',    multiple = True,
              help = 'Select evals by readable id. An anchored regular '
                     'expression, so a plain id matches only itself.')
@click.option('--guid-eval',  'guid_eval',  multiple = True,
              help = 'Select evals by guid. Exact; a guid has no structure '
                     'worth matching part of.')
@click.option('--id-schema',  'id_schema',  multiple = True,
              help = 'Select evals anchored on a schema, by its readable id. '
                     'Regular expression.')
@click.option('--guid-schema','guid_schema',multiple = True,
              help = 'Select evals anchored on a schema, by its guid. Exact.')
@click.option('--id-type',    'id_type',    multiple = True,
              help = 'Select evals anchored on a type, by its readable id. '
                     'Regular expression.')
@click.option('--guid-type',  'guid_type',  multiple = True,
              help = 'Select evals anchored on a type, by its guid. Exact.')
@click.option('--id-item',    'id_item',    multiple = True,
              help = 'Select the items to be judged, by readable id -- every '
                     'eval that applies to them. Regular expression.')
@click.option('--guid-item',  'guid_item',  multiple = True,
              help = 'Select the items to be judged, by guid. Exact.')
@click.option('--judge-model',
              'id_model_eval',
              default      = None,
              envvar       = cc_public.eval.runner.NAME_ENV_MODEL,
              show_envvar  = True,
              help         = 'The model that judges the evals, named as '
                             'dspy names one -- anthropic/claude-sonnet-4-5, '
                             'openai/gpt-5.1. Name it null for a dry run '
                             'that reports what would be judged without '
                             'judging it. Required when evals are asked '
                             'for. Should not be the same model family as '
                             'wrote the items being judged.')
@click.option('--confirm',
              'count_confirm',
              type    = ODD,
              default = cc_public.eval.runner.COUNT_CONFIRM,
              show_default = True,
              help    = 'Over how many judgements an adverse verdict is '
                        'confirmed before it is reported. The screen is one '
                        'call and only what comes back unmet is asked again, '
                        'so on a clean corpus this costs little. One believes '
                        'the screen alone. Odd, so that a majority exists.')
@click.option('--out',
              'filepath_out',
              type    = click.Path(path_type = pathlib.Path),
              default = None,
              help    = 'Write the report to this file rather than to the '
                        'console.')
@click.option('--format',
              'id_format',
              type    = click.Choice(cc_public.cli.report.FORMAT_ALL),
              default = cc_public.cli.report.FORMAT_TEXT,
              show_default = True,
              help    = 'Report serialisation. text is for a person; the '
                        'others are for a program.')
def check(list_path,
          is_fail_on_nonconformity,
          is_fail_fast,
          is_closed_world,
          is_eval,
          id_model_eval,
          id_eval,
          guid_eval,
          id_schema,
          guid_schema,
          id_type,
          guid_type,
          id_item,
          guid_item,
          count_confirm,
          filepath_out,
          id_format):
    """
    Check the data for conformity.

    """

    selector = cc_public.eval.select.Selector(id_eval     = id_eval,
                                              guid_eval   = guid_eval,
                                              id_schema   = id_schema,
                                              guid_schema = guid_schema,
                                              id_type     = id_type,
                                              guid_type   = guid_type,
                                              id_item     = id_item,
                                              guid_item   = guid_item)

    # Any selector implies --eval. Naming what to judge and then not
    # judging it would be a surprising thing for the tool to do.
    #
    if not (is_eval or any(selector)):
        selector = None

    report = cc_public.check.check(list_path       = list_path,
                                   is_fail_fast    = is_fail_fast,
                                   is_closed_world = is_closed_world,
                                   selector_eval   = selector,
                                   id_model_eval   = id_model_eval,
                                   count_confirm   = count_confirm)

    list_error = report['report']['error']
    list_error.extend(cc_public.cli.report.write(report,
                                                 id_format,
                                                 filepath_out))

    cc_public.cli.report.write_error(list_error)

    raise SystemExit(_status(report, list_error, is_fail_on_nonconformity))


# -----------------------------------------------------------------------------
@main.command(name = 'format')
@click.option('--path',
              'list_path',
              multiple = True,
              type     = click.Path(path_type = pathlib.Path),
              help     = 'A file or directory tree to lay out. May be given '
                         'more than once, and the command runs over the '
                         'union of all of them. Defaults to the working '
                         'directory.')
@click.option('--check',
              'is_check',
              is_flag = True,
              help    = 'Report what would change and write nothing. Exits '
                        'non zero where anything would, which is what a '
                        'hook or a pipeline wants.')
def format_(list_path, is_check):
    """
    Lay documents out to the layout convention.

    """

    list_path    = list_path or (pathlib.Path('.'),)
    list_changed = []
    list_error   = []

    for filepath in sorted(set(cc_public.check.iter_filepath_all(list_path))):

        if filepath.suffix not in (cc_public.layout.SUFFIX_YAML,
                                   cc_public.layout.SUFFIX_PYTHON):
            continue

        try:
            text = filepath.read_text(encoding = 'utf-8')
        except (OSError, UnicodeDecodeError) as error:
            list_error.append('{filepath}: {error}'.format(filepath = filepath,
                                                           error    = error))
            continue

        formatted = cc_public.layout.format_source(text, filepath.suffix)

        if formatted == text:
            continue

        list_changed.append(filepath)

        if not is_check:
            filepath.write_text(formatted, encoding = 'utf-8')

    verb = 'would change' if is_check else 'changed'

    for filepath in list_changed:
        click.echo('{verb}  {filepath}'.format(verb = verb, filepath = filepath))

    click.echo('{count} file(s) {verb}.'.format(count = len(list_changed),
                                                verb  = verb))

    cc_public.cli.report.write_error(list_error)

    if list_error:
        raise SystemExit(EXIT_ERROR)

    raise SystemExit(EXIT_NONCONFORMITY if (is_check and list_changed)
                                        else EXIT_OK)


# -----------------------------------------------------------------------------
def _tree(list_root):
    """
    Return the item tree under the roots given, or the working directory.

    """

    return cc_public.edit.tree.Tree(list_root or (pathlib.Path('.'),))


# -----------------------------------------------------------------------------
def _fail(err):
    """
    Report one error and exit as an analysis failure.

    """

    click.echo(str(err), err = True)
    raise SystemExit(EXIT_ERROR)


OPTION_ROOT = click.option('--root', 'list_root', multiple = True,
                           type = click.Path(path_type = pathlib.Path),
                           help = 'A directory tree holding the items. May '
                                  'be given more than once. Defaults to the '
                                  'working directory.')


# -----------------------------------------------------------------------------
@main.command()
@click.argument('id_type')
@click.argument('id_self')
@click.option('--out', 'dirpath_out', default = None,
              type = click.Path(path_type = pathlib.Path),
              help = 'Where to write the item. Defaults to where items of '
                     'this type already live.')
@OPTION_ROOT
def new(id_type, id_self, dirpath_out, list_root):
    """
    Make a data item of ID_TYPE called ID_SELF.

    Its identity is minted and every field its schema requires is
    present and empty, so it fails the checks until written. Rights
    come from [tool.cctool.new] in pyproject.toml.

    """

    try:
        tree     = _tree(list_root)
        filepath = cc_public.edit.new.new(tree, id_type, id_self,
                                          tree.defaults(), dirpath_out)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        _fail(err)

    click.echo(str(filepath))


# -----------------------------------------------------------------------------
@main.command(name = 'set')
@click.argument('name')
@click.argument('path')
@click.argument('value', required = False)
@click.option('--prose', 'is_prose', is_flag = True,
              help = 'Read the value from standard input and store it as '
                     'prose, a block scalar the printer fills.')
@OPTION_ROOT
def set_(name, path, value, is_prose, list_root):
    """
    Set PATH within the item called NAME to VALUE.

    NAME is a readable id or a guid, of a top level or an embedded item.
    VALUE is read as YAML, so 3 is a number and [] is a list; quote a
    string that would otherwise read as something else.

    """

    if is_prose == (value is not None):
        _fail('Give VALUE, or --prose with the text on standard input.')

    try:
        item = cc_public.edit.field.set_field(
                    _tree(list_root), name, path,
                    value = (ruamel.yaml.YAML(typ = 'safe').load(value)
                             if value is not None else None),
                    prose = sys.stdin.read() if is_prose else None)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        _fail(err)

    click.echo('{file}  {item}.{path}'.format(file = item.filepath,
                                              item = item.id_self,
                                              path = path))


# -----------------------------------------------------------------------------
@main.command()
@click.argument('name_source')
@click.argument('id_relation')
@click.argument('name_target')
@OPTION_ROOT
def link(name_source, id_relation, name_target, list_root):
    """
    Add an edge NAME_SOURCE --ID_RELATION--> NAME_TARGET.

    Both names are readable ids or guids, of top level or embedded
    items. The relation must be in the relation register. The edge is
    appended to the source's relation list, created where absent.

    """

    try:
        (source, target) = cc_public.edit.link.link(
                    _tree(list_root), name_source, id_relation, name_target)
    except cc_public.edit.tree.ErrorItem as err:
        _fail(err)

    click.echo('{file}  {src} {rel} {dst}'.format(file = source.filepath,
                                                 src  = source.id_self,
                                                 rel  = id_relation,
                                                 dst  = target.id_self))


# -----------------------------------------------------------------------------
@main.command()
@click.argument('id_type')
@click.argument('name')
@click.option('--into', 'name_container', required = True,
              help = 'The item to put it in, by readable id or guid.')
@click.option('--at', 'path_collection', default = None,
              help = 'The collection within that item, as a dot path. '
                     'Defaults to table where the item is a register.')
@click.option('--id', 'id_self', default = None,
              help = 'The readable id to give it, where the derived one '
                     'is not wanted.')
@OPTION_ROOT
def insert(id_type, name, name_container, path_collection, id_self, list_root):
    """
    Put a new item of ID_TYPE called NAME into a collection of another.

    Its shape comes from the container's schema, every required field
    empty. In a register the key is the id; elsewhere NAME is the key
    and the id is qualified by the container. A list is appended to.

    """

    try:
        (key, made) = cc_public.edit.insert.insert(
                        _tree(list_root), id_type, name, name_container,
                        path_collection, id_self)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        _fail(err)

    click.echo('{container}.{key}  {made}'.format(container = name_container,
                                                  key       = key,
                                                  made      = made or ''))


# -----------------------------------------------------------------------------
@main.command()
@click.option('--id-eval', 'id_eval', required = True,
              help = 'The eval to measure, by readable id.')
@click.option('--samples', 'count_sample', default = 5,
              type = ODD, show_default = True,
              help = 'Fresh judgements per case. Odd, so that a majority exists.')
@click.option('--record', 'is_record', is_flag = True,
              help = 'Write the rates onto the eval as its confidence for '
                     'this judge model, replacing earlier rows for it.')
@click.option('--judge-model', 'id_model_eval', default = None,
              envvar = cc_public.eval.runner.NAME_ENV_MODEL, show_envvar = True,
              help = 'The model that judges. Required.')
@OPTION_ROOT
def measure(id_eval, count_sample, is_record, id_model_eval, list_root):
    """
    Judge the control cases for an eval and report the error rates.

    Every case is judged SAMPLES times without the cache. False
    positive is the share of met cases the judge called unmet; false
    negative the share of unmet cases it called met; unanimous the
    share of cases it answered the same way every time. Reported per
    origin and pooled.

    """

    tree = _tree(list_root)

    try:
        item   = tree.resolve(id_eval)
        runner = cc_public.eval.runner.build(id_model_eval)
    except Exception as err:
        _fail(err)

    document_eval  = tree.context.map_document[item.filepath]
    (rows, detail) = cc_public.eval.measure.measure(tree.context, document_eval,
                                                    runner, count_sample)

    for (id_case, origin, want, tally) in detail:
        click.echo('  {want:5} {origin:10} {tally}  {id_case}'.format(
                            want = want, origin = origin, id_case = id_case,
                            tally = '/'.join('U' if v == 'unmet' else 'M'
                                             if v == 'met' else '?'
                                             for v in tally)))
    click.echo()
    click.echo('  {:10} {:>5} {:>7} {:>14} {:>14} {:>9}'.format(
                    'origin', 'cases', 'samples', 'false_positive',
                    'false_negative', 'unanimous'))
    for row in rows:
        click.echo('  {origin:10} {cases:5} {samples:7} {fp:>14} {fn:>14} '
                   '{un:9}'.format(origin = row['origin'], cases = row['cases'],
                                   samples = row['samples'],
                                   fp = _rate(row['false_positive']),
                                   fn = _rate(row['false_negative']),
                                   un = row['unanimous']))

    if is_record:
        cc_public.eval.measure.record(tree, id_eval, rows, runner.id_model)
        click.echo('  recorded on {id_eval} for {model}'.format(
                                    id_eval = id_eval, model = runner.id_model))


# -----------------------------------------------------------------------------
@main.command(name = 'case')
@click.option('--id-eval', 'id_eval', required = True,
              help = 'The eval the finding came from.')
@click.option('--item', 'name_item', required = True,
              help = 'The item the finding was on, by readable id or guid.')
@click.option('--verdict', 'verdict', required = True,
              type = click.Choice(['met', 'unmet']),
              help = 'What a person holds the subject to. met answers the '
                     'finding; unmet confirms it.')
@click.option('--origin', 'origin', default = None,
              type = click.Choice(cc_public.eval.control.ORIGIN_ALL),
              help = 'Where the case came from. Defaults to suppressed for '
                     'met and confirmed for unmet; written marks a subject '
                     'a person wrote and holds to the verdict.')
@click.option('--note', 'note', default = '',
              help = 'Why. Kept with the case and shown when it answers.')
@OPTION_ROOT
def case_(id_eval, name_item, verdict, origin, note, list_root):
    """
    Turn a finding into a control case.

    The item is rendered for the eval exactly as a sweep renders it,
    and that text becomes the case's subject. A later sweep matching
    the same words finds the case: met answers the finding as a note,
    unmet confirms it.

    """

    try:
        (id_set, id_case) = cc_public.edit.case.case(
                    _tree(list_root), id_eval, name_item, verdict, note,
                    origin)
    except cc_public.edit.tree.ErrorItem as err:
        _fail(err)

    click.echo('{set}  {case}'.format(set = id_set, case = id_case))


# -----------------------------------------------------------------------------
def _rate(value):
    """
    Return a rate for the table, or a dash where there is none.

    """

    return '-' if value is None else value


# -----------------------------------------------------------------------------
@main.command()
@click.argument('name')
@click.argument('path')
@OPTION_ROOT
def unset(name, path, list_root):
    """
    Remove PATH from the item called NAME.

    """

    try:
        item = cc_public.edit.field.unset_field(_tree(list_root), name, path)
    except (cc_public.edit.tree.ErrorItem, KeyError) as err:
        _fail(err)

    click.echo('{file}  {item}.{path} removed'.format(file = item.filepath,
                                                     item = item.id_self,
                                                     path = path))


# -----------------------------------------------------------------------------
@main.command()
@click.argument('name')
@click.argument('id_new')
@OPTION_ROOT
def rename(name, id_new, list_root):
    """
    Rename the item called NAME to ID_NEW.

    The guid stays. The readable id changes where it is declared, in
    the file name, in every embedded item it qualifies, and in every
    reference. Prose mentioning the old id is listed and left alone.

    """

    try:
        report = cc_public.edit.rename.rename(_tree(list_root), name, id_new)
    except cc_public.edit.tree.ErrorItem as err:
        _fail(err)

    for (old, new) in report.map_rename.items():
        click.echo('{old}  ->  {new}'.format(old = old, new = new))
    for filepath in report.list_filepath:
        click.echo(str(filepath))
    for (filepath, path) in report.list_mention:
        click.echo('mention  {file}  {path}'.format(file = filepath, path = path))


# -----------------------------------------------------------------------------
@main.command()
@click.option('--open', 'is_open_only', is_flag = True,
              help = 'Only the questions nothing has answered.')
@OPTION_ROOT
def questions(is_open_only, list_root):
    """
    List what the design decisions leave open, and what answered it.

    """

    list_row = cc_public.question.report(_tree(list_root).context.map_document)
    count    = 0

    for (_id_record, id_question, text, list_answerer) in list_row:
        if is_open_only and list_answerer:
            continue
        count += 1
        state = 'open' if not list_answerer else 'answered by ' + ', '.join(list_answerer)
        click.echo('{q}\n    {state}\n    {text}'.format(
                        q = id_question, state = state,
                        text = text if len(text) <= 100 else text[:97] + '...'))

    click.echo('{n} question(s){only}.'.format(n = count,
                                            only = ' open' if is_open_only else ''))


# -----------------------------------------------------------------------------
@main.command()
@click.argument('title')
@click.option('--brief', 'brief', default = None,
              help = 'One sentence on what the commit is for. Defaults to '
                     'the title.')
@click.option('--description', 'description', default = None,
              help = 'Why, at whatever length it needs.')
@click.option('--checkpoint', 'is_checkpoint', is_flag = True,
              help = 'Commit although the checks fail, and say so in the '
                     'record.')
@click.option('--execution', 'id_execution', default = None,
              help = 'The execution this commit results from, where a '
                     'workflow made it.')
@click.option('--trailer', 'list_trailer', multiple = True,
              help = 'A trailer line appended after the record.')
@click.option('--link', 'list_link', multiple = True, nargs = 2,
              metavar = 'RELATION TARGET',
              help = 'An edge from the record to an item, by any relation '
                     'in the register: what this commit relates to on '
                     'purpose. May be given more than once.')
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path),
              help = 'The repository. Defaults to the working directory.')
def commit(title, brief, description, is_checkpoint, id_execution,
           list_trailer, list_link, root):
    """
    Commit what has changed, with a commit record in the message.

    TITLE is the first line of the message and the record's title. The
    checks run first; a critical finding refuses the commit unless
    --checkpoint is given.

    """

    try:
        (hash, id_self) = cc_public.commit.commit(
                    root, title, brief, description, is_checkpoint,
                    id_execution, list_trailer, list_link)
    except (cc_public.commit.ErrorCommit, cc_public.edit.tree.ErrorItem) as err:
        _fail(err)

    click.echo('{hash}  {id_self}'.format(hash = hash[:10], id_self = id_self))


# -----------------------------------------------------------------------------
@main.command()
@click.option('-n', 'count', default = 10, type = click.IntRange(min = 1),
              show_default = True, help = 'How many commits to read.')
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path))
def log(count, root):
    """
    Read the commit records in the history, newest first, and say
    which are valid.

    """

    tree       = _tree([root])
    map_schema = cc_public.check.schema.map_schema(tree.context.map_document)
    registry   = cc_public.check.schema._registry(map_schema)

    for c in cc_public.load.git.iter_commit(root, count):

        if c.document is None:
            click.echo('{hash}  -  {title}'.format(hash = c.hash[:10],
                                                   title = c.title))
            continue

        list_error = cc_public.check.schema._validate(
                        c.document, map_schema['sch_commit'], registry)
        state = 'ok' if not list_error else 'INVALID'

        if c.document.get('title') != c.title:
            state += ', title differs from first line'

        click.echo('{hash}  {id}  {status}  {crit}c/{adv}a  {state}  {title}'.format(
                        hash   = c.hash[:10],
                        id     = c.document.get('id_self', '?'),
                        status = c.document.get('status', '?'),
                        crit   = (c.document.get('check') or {}).get('critical', '?'),
                        adv    = (c.document.get('check') or {}).get('advisory', '?'),
                        state  = state,
                        title  = c.title))


# -----------------------------------------------------------------------------
@main.command(name = 'run')
@click.argument('id_workflow')
@click.option('--deployment', 'id_deployment', required = True,
              help = 'The deployment to run under: model, budget, what to '
                     'judge, when to commit.')
@click.option('--bind', 'list_bind', multiple = True, metavar = 'PORT=ITEM',
              help = 'Bind one of the workflow\'s own inputs, node.input.port, '
                     'to an item by readable id. May be given more than once.')
@click.option('--dry-run', 'is_dry', is_flag = True,
              help = 'Show the order and what each node would do. Writes '
                     'nothing and calls no model.')
@click.option('--judge-model', 'id_model_judge', default = None,
              envvar = cc_public.eval.runner.NAME_ENV_MODEL, show_envvar = True,
              help = 'The model that judges what the run produces. Needed '
                     'unless the deployment judges nothing.')
@click.option('--trailer', 'list_trailer', multiple = True,
              help = 'A trailer line for any commit the run makes.')
@click.option('--format', 'id_format', default = 'text',
              type = click.Choice(['text', 'json']), show_default = True)
@click.option('--root', 'root', default = pathlib.Path('.'),
              type = click.Path(path_type = pathlib.Path))
def run_(id_workflow, id_deployment, list_bind, is_dry, id_model_judge,
         list_trailer, id_format, root):
    """
    Run a dataflow workflow once under a deployment.

    """

    import json

    map_bind = {}
    for pair in list_bind:
        if '=' not in pair:
            _fail('--bind takes node.input.port=ITEM')
        (k, v) = pair.split('=', 1)
        map_bind[k.strip()] = v.strip()

    tree = _tree([root])

    try:
        dep       = tree.context.map_document[tree.resolve(id_deployment).filepath]
        generator = (cc_public.workflow.generate.NullGenerator() if is_dry
                     else cc_public.workflow.generate.build(dep.get('model')))
        generator_challenge = (None if is_dry or not dep.get('model_challenge')
                               else cc_public.workflow.generate.build(dep.get('model_challenge')))
        runner    = None
        if not is_dry and dep.get('judge', 'always') != 'never' and id_model_judge:
            runner = cc_public.eval.runner.build(id_model_judge)
        report = cc_public.workflow.run.run(root, id_workflow, id_deployment,
                                            map_bind, generator, runner,
                                            is_dry, list_trailer,
                                            generator_challenge = generator_challenge)
    except (cc_public.workflow.run.Stop, cc_public.workflow.graph.ErrorGraph,
            cc_public.edit.tree.ErrorItem, cc_public.commit.ErrorCommit) as err:
        _fail(err)

    if id_format == 'json':
        click.echo(json.dumps(report, indent = 2, default = str))
    else:
        _write_run(report)

    raise SystemExit(EXIT_NONCONFORMITY if report['stopped'] else EXIT_OK)


# -----------------------------------------------------------------------------
def _write_run(report):
    """
    Print a run report for a person.

    """

    click.echo('{wf} under {dep}  judge={j} confirm={c} commit={k}'.format(
                    wf = report['workflow'], dep = report['deployment'],
                    j = report['policy']['judge'], c = report['policy']['confirm'],
                    k = report['policy']['commit']))
    for (port, item) in (report.get('bound') or {}).items():
        click.echo('  bound  {port} = {item}'.format(port = port, item = item))
    for e in report['node']:
        if 'input' in e:                                     # dry run
            click.echo('  {node}: {out}'.format(
                            node = e['node'],
                            out  = '; '.join(f'{p} {what}' for (p, what) in e['output'].items())))
            continue
        click.echo('  {node}{n}'.format(node = e['node'],
                                        n = '' if e.get('pass', 1) == 1 else
                                            '  pass {n}'.format(n = e['pass'])))
        for i in e['made']:
            click.echo('    made     {i}'.format(i = i))
        for i in e['revised']:
            click.echo('    revised  {i}'.format(i = i))
        for (port, vs) in e['verdict'].items():
            for (ev, v) in vs:
                click.echo('    {v:6} {port}  {ev}'.format(v = v, port = port, ev = ev))
        for t in e['fired']:
            click.echo('    fired    -> {t}'.format(t = t))
        for t in e['declined']:
            click.echo('    declined -> {t}'.format(t = t))
        for n in e.get('note') or []:
            click.echo('    note     {n}'.format(n = n))
        for t in e.get('exhausted') or []:
            click.echo('    exhausted -> {t}  (budget spent)'.format(t = t))
        if e.get('commit'):
            click.echo('    commit   {h}'.format(h = e['commit'][:10]))
    if report['execution']:
        click.echo('  execution {e}'.format(e = report['execution']))
    if report['commit']:
        click.echo('  commit    {h}'.format(h = report['commit'][:10]))
    if report['stopped']:
        click.echo('  STOPPED   {r}'.format(r = report['stopped']))


# -----------------------------------------------------------------------------
def _status(report, list_error, is_fail_on_nonconformity):
    """
    Return the exit status.

    A failure of the analysis is always reported in the exit status. A
    critical nonconformity is reported only when asked for, because the
    ordinary case is a caller that wants to read the report rather than
    be stopped by it. An advisory never affects the exit status at all --
    it is something to know about, and in a federated slice there may
    always be some.

    """

    if list_error:
        return EXIT_ERROR

    if is_fail_on_nonconformity and report['report']['summary'][
                                                    'count_critical']:
        return EXIT_NONCONFORMITY

    return EXIT_OK


# -----------------------------------------------------------------------------
if __name__ == '__main__':

    main()
