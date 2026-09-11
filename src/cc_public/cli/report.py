"""
---

id_self:                pym_cc_public.cli.report
guid_self:              pym_24937d5ee1fa47109752773ea2a636d8
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Report presentation
brief:                  |
                        Present a check report.
description:            |
                        Writes a check report as text for a person, or
                        as JSON, YAML or XML for a program, and
                        renders what the other commands show: a run, a
                        trace, an impact, an item and its edges, and
                        the glossary as a list, a lookup, a sense
                        report or a gap report. Findings go to
                        standard output in every format; standard
                        error is reserved for failures of the analysis
                        itself.
relation:               []

...
"""


import json
import pathlib
import sys

import click
import rich.console
import rich.table
import rich.text

import cc_public.query


FORMAT_TEXT = 'text'
FORMAT_JSON = 'json'
LIMIT_GAP   = 40
FORMAT_YAML = 'yaml'
FORMAT_XML  = 'xml'
FORMAT_ALL  = (FORMAT_TEXT, FORMAT_JSON, FORMAT_YAML, FORMAT_XML)

STATUS_OK   = 'ok'
STATUS_ADV  = 'advisory'
STATUS_BAD  = 'nonconformity'
STATUS_ERR  = 'error'

STYLE       = {STATUS_OK:  'green',
               STATUS_ADV: 'cyan',
               STATUS_BAD: 'yellow',
               STATUS_ERR: 'red'}

SEVERITY_STYLE = {'critical': 'yellow',
                  'advisory': 'cyan'}


# -----------------------------------------------------------------------------
def _short(filepath):
    """
    Return filepath relative to the working directory where it lies below it.

    Only for display. The serialised report keeps the path it was given.

    """

    try:
        return str(pathlib.Path(filepath).relative_to(pathlib.Path.cwd()))
    except ValueError:
        return str(filepath)


# -----------------------------------------------------------------------------
def write(report: dict,
          id_format: str = FORMAT_TEXT,
          filepath_out: pathlib.Path | None = None) -> list:
    """
    Write report, returning a list of any errors met in doing so.

    """

    list_error = []
    file_out   = sys.stdout

    if filepath_out is not None:
        try:
            file_out = open(filepath_out, 'w', encoding = 'utf-8')   # noqa: SIM115  closed below by the caller's contract
        except OSError as err:
            list_error.append({'id_check':  '',
                               'message':   'Could not open {path} for '
                                            'output, writing to the console '
                                            'instead: {err}'.format(
                                                    path = filepath_out,
                                                    err  = err),
                               'traceback': ''})
            file_out = sys.stdout

    try:
        if id_format == FORMAT_TEXT:
            _write_text(report, file_out)
        else:
            _write_data(report, id_format, file_out)
    finally:
        if file_out is not sys.stdout:
            file_out.close()

    return list_error


# -----------------------------------------------------------------------------
def write_error(list_error: list) -> None:
    """
    Write analysis failures to standard error.

    These are failures of the tool rather than findings about the data,
    so they are kept off stdout where the report is.

    """

    if not list_error:
        return

    console = rich.console.Console(file = sys.stderr, stderr = True)

    for error in list_error:

        prefix = ('[{id_check}] '.format(id_check = error['id_check'])
                                                if error['id_check'] else '')

        console.print('[bold red]ANALYSIS FAILED[/bold red] {prefix}'
                      '{message}'.format(prefix  = prefix,
                                         message = error['message']))

        if error['traceback']:
            console.print(rich.text.Text(error['traceback'],
                                         style = 'dim'))


# -----------------------------------------------------------------------------
def _write_data(report, id_format, file_out):
    """
    Write the report in a machine readable serialisation.

    """

    if id_format == FORMAT_JSON:
        json.dump(report, file_out, indent = 2)
        file_out.write('\n')
        return

    if id_format == FORMAT_YAML:
        import ruamel.yaml
        yaml = ruamel.yaml.YAML(typ = 'safe')
        yaml.default_flow_style = False
        yaml.dump(report, file_out)
        return

    if id_format == FORMAT_XML:
        import xmltodict
        file_out.write(xmltodict.unparse(_xml_safe(report), pretty = True))
        file_out.write('\n')
        return

    raise ValueError('Unknown format: {id_format}'.format(id_format = id_format))


# -----------------------------------------------------------------------------
def _xml_safe(node):
    """
    Return node with values XML can carry.

    An XML document holds text, so booleans and numbers are rendered as
    text, and an empty list is dropped rather than written as an empty
    element that would read back as a string.

    """

    if isinstance(node, dict):
        return {key: _xml_safe(value) for (key, value) in node.items()
                                      if  value not in ([], {})}

    if isinstance(node, list):
        return [_xml_safe(value) for value in node]

    if isinstance(node, bool):
        return 'true' if node else 'false'

    if isinstance(node, (int, float)):
        return str(node)

    return node


# -----------------------------------------------------------------------------
def _write_text(report, file_out):
    """
    Write the report as a table and a section per finding.

    """

    console = rich.console.Console(file = file_out, highlight = False)
    body    = report['report']
    summary = body['summary']

    table = rich.table.Table(show_edge = False, box = None, pad_edge = False)
    table.add_column('check',  style = 'bold')
    table.add_column('status')
    table.add_column('counted',  justify = 'right')
    table.add_column('critical', justify = 'right')
    table.add_column('advisory', justify = 'right')
    table.add_column('title',    style = 'dim')

    for entry in body['check']:
        count_critical = sum(1 for item in entry['nonconformity']
                               if  item['severity'] == 'critical')
        count_advisory = sum(1 for item in entry['nonconformity']
                               if  item['severity'] == 'advisory')
        table.add_row(entry['id_check'],
                      rich.text.Text(entry['status'],
                                     style = STYLE.get(entry['status'], '')),
                      '{count} {noun}(s)'.format(count = entry['count_item'],
                                                 noun  = entry['noun']),
                      str(count_critical),
                      str(count_advisory),
                      entry['title'])

    console.print(table)

    for entry in body['check']:
        for (key, value) in sorted((entry.get('detail') or {}).items()):
            console.print('[dim]{id_check}: {key} {value}[/dim]'.format(
                                        id_check = entry['id_check'],
                                        key      = key,
                                        value    = value))

    for entry in body['check']:
        _write_entry(console, entry)

    console.print()
    console.print('[bold]{count_critical}[/bold] critical, '
                  '[bold]{count_advisory}[/bold] advisory over '
                  '{count_check} check(s)'.format(
                            count_critical = summary['count_critical'],
                            count_advisory = summary['count_advisory'],
                            count_check    = summary['count_check']),
                  style = 'yellow' if summary['count_critical'] else
                          'cyan'   if summary['count_advisory'] else 'green')


# -----------------------------------------------------------------------------
def _write_entry(console, entry):
    """
    Write the findings and notes of one check.

    """

    if entry['note']:
        console.print()
        console.print('[dim]{id_check}: {count} note(s)[/dim]'
                      .format(id_check = entry['id_check'],
                              count    = len(entry['note'])))
        for note in entry['note']:
            console.print('  [dim]{filepath}[/dim]  {message}'.format(
                                        filepath = _short(note['filepath']),
                                        message  = note['message']),
                          no_wrap = True,
                          overflow = 'ellipsis')

    if not entry['nonconformity']:
        return

    console.print()
    console.print('[bold yellow]{id_check}[/bold yellow]  {title}'.format(
                                            id_check = entry['id_check'],
                                            title    = entry['title']))

    for item in entry['nonconformity']:
        console.print('  [{style}]{severity}[/{style}]'.format(
                    style    = SEVERITY_STYLE.get(item['severity'], ''),
                    severity = item['severity']), end = '  ')
        where = _short(item['filepath'])
        if item['path']:
            where = '{filepath}  {path}'.format(filepath = where,
                                                path     = item['path'])
        console.print('  {where}'.format(where = where),
                      style    = 'cyan',
                      no_wrap  = True,
                      overflow = 'ellipsis')
        for line in item['message'].splitlines():
            console.print('    {line}'.format(line = line))


# -----------------------------------------------------------------------------
def write_trace(list_record, id_format):
    """
    Write the projection, as text or as json.

    """

    if id_format == 'json':
        click.echo(json.dumps([plain_record(r) for r in list_record], indent = 2))
        return

    for r in list_record:
        click.echo('{id}  {status}{leaf}'.format(
                        id = r.id_self, status = r.status,
                        leaf = '  leaf' if r.is_leaf else ''))
        for (label, names) in (('derives from', r.derives_from),
                               ('children', r.children),
                               ('implemented by', r.implemented_by),
                               ('verified by', r.verified_by),
                               ('unresolved', r.unresolved)):
            if names:
                click.echo('    {label:15} {names}'.format(label = label,
                                                          names = ', '.join(names)))
        if r.verification:
            click.echo('    {label:15} {v}{c}'.format(
                            label = 'verification', v = r.verification,
                            c = ', criteria' if r.has_criteria else ', NO CRITERIA'))
        for gap in r.gap:
            click.echo('    {sev:15} {path}: {msg}'.format(
                            sev = gap.severity.upper(), path = gap.path, msg = gap.message))

    click.echo('{n} requirement(s), {g} with gaps.'.format(
                    n = len(list_record), g = sum(1 for r in list_record if r.gap)))



# -----------------------------------------------------------------------------
def write_impact(list_impact, id_format):
    """
    Write what each source item may affect, as text or as json.

    """

    if id_format == 'json':
        click.echo(json.dumps([{'id_self':    i.id_self,
                                'guid_self':  i.guid_self,
                                'implements': [plain_record(r) for r in i.implements],
                                'verifies':   [plain_record(r) for r in i.verifies]}
                               for i in list_impact], indent = 2))
        return

    if not list_impact:
        click.echo('No item here implements or verifies a requirement.')

    for i in list_impact:
        click.echo('{id}'.format(id = i.id_self))
        for (label, records) in (('implements', i.implements), ('verifies', i.verifies)):
            for r in records:
                click.echo('    {label:12} {req}  verified by {v}'.format(
                                label = label, req = r.id_self,
                                v = ', '.join(r.verified_by) or 'nothing'))
        if not (i.implements or i.verifies):
            click.echo('    implements and verifies no requirement.')



# -----------------------------------------------------------------------------
def write_changed(list_changed, list_dependent, list_suspect, id_format):
    """
    Write what changed, by kind, what rests on it, and what describes
    it, as text or as json.

    """

    if id_format == 'json':
        click.echo(json.dumps({'changed':   [c._asdict() for c in list_changed],
                               'dependent': [d._asdict() for d in list_dependent],
                               'suspect':   list(list_suspect)},
                              indent = 2))
        return

    by_prefix = {}
    for c in list_changed:
        by_prefix.setdefault(c.prefix, []).append(c)

    for (prefix, items) in sorted(by_prefix.items()):
        click.echo('{prefix}  ({n})'.format(prefix = prefix, n = len(items)))
        for c in items:
            click.echo('    {id:44} {title}{held}'.format(
                            id = c.id_self, title = c.title or '',
                            held = '  [holds {n}]'.format(n = c.held) if c.held else ''))
            if c.decided_by:
                click.echo('    {pad:44} decided by {d}'.format(
                                pad = '', d = ', '.join(c.decided_by)))

    if list_dependent:
        click.echo('rests on what changed  ({n})'.format(n = len(list_dependent)))
        for d in list_dependent:
            click.echo('    {id:44} {rel:22} {target}{via}'.format(
                            id = d.id_self, rel = d.id_relation, target = d.id_target,
                            via = ('' if d.changed == d.id_target
                                   else '  (through to {c})'.format(c = d.changed))))

    if list_suspect:
        click.echo('describes what changed, so read it again  ({n})'.format(
                        n = len(list_suspect)))
        for one in list_suspect:
            click.echo('    {id}'.format(id = one))

    click.echo('{n} item(s) changed, {m} resting on them, {k} describing '
               'them.'.format(n = len(list_changed), m = len(list_dependent),
                              k = len(list_suspect)))


# -----------------------------------------------------------------------------
def plain_record(record):
    """
    Return a projection record as plain data, gaps included.

    """

    out        = record._asdict()
    out['gap'] = [g._asdict() for g in record.gap]

    return out



# -----------------------------------------------------------------------------
def rate(value):
    """
    Return a rate for the table, or a dash where there is none.

    """

    return '-' if value is None else value



# -----------------------------------------------------------------------------
def write_run(report):
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
        _write_pass(e)
    if report['execution']:
        click.echo('  execution {e}  {o}'.format(e = report['execution'],
                                                 o = report.get('outcome') or ''))
    if report['commit']:
        click.echo('  commit    {h}'.format(h = report['commit'][:10]))
    if report['stopped']:
        click.echo('  STOPPED   {r}'.format(r = report['stopped']))



# -----------------------------------------------------------------------------
def _write_halt(e):
    """
    Print why a node did not run: skipped on this pass, or waiting for
    a performer, with the brief.

    """

    if e.get('skipped'):
        click.echo('    skipped  {why}'.format(why = e['skipped']))
    for line in (e.get('waiting') or '').splitlines():
        click.echo('    waiting  ' + line if line else '')


# -----------------------------------------------------------------------------
def _write_pass(e):
    """
    Print one node's entry of a run report: what it would do on a dry
    run, else what it made, judged, fired and declined.

    """

    if 'input' in e:                                     # dry run
        click.echo('  {node}: {out}'.format(
                        node = e['node'],
                        out  = '; '.join(f'{p} {what}' for (p, what) in e['output'].items())))
        return

    click.echo('  {node}{n}'.format(node = e['node'],
                                    n = '' if e.get('pass', 1) == 1 else
                                        '  pass {n}'.format(n = e['pass'])))
    _write_halt(e)
    for (label, items) in (('made    ', e['made']), ('revised ', e['revised'])):
        for i in items:
            click.echo('    {label} {i}'.format(label = label, i = i))
    for (port, vs) in e['verdict'].items():
        for (ev, v) in vs:
            click.echo('    {v:6} {port}  {ev}'.format(v = v, port = port, ev = ev))
    for (label, items) in (('fired    -> ', e['fired']),
                           ('declined -> ', e['declined']),
                           ('note     ', e.get('note') or [])):
        for t in items:
            click.echo('    {label}{t}'.format(label = label, t = t))
    for t in e.get('exhausted') or []:
        click.echo('    exhausted -> {t}  (budget spent)'.format(t = t))
    if e.get('commit'):
        click.echo('    commit   {h}'.format(h = e['commit'][:10]))


# -----------------------------------------------------------------------------
def write_neighbourhood(found, id_format):
    """
    Write one item and the edges at it, as text or as json.

    """

    if id_format == 'json':
        out = found._asdict()
        out['outgoing'] = [list(e) for e in found.outgoing]
        out['incoming'] = [list(e) for e in found.incoming]
        click.echo(json.dumps(out, indent = 2))
        return

    click.echo('{id}  {guid}'.format(id = found.id_self, guid = found.guid_self))
    click.echo('    {label:12} {v}'.format(label = 'at', v = found.location))
    for (label, value) in (('title', found.title), ('brief', found.brief)):
        if value:
            click.echo('    {label:12} {v}'.format(label = label, v = value))
    for (rel, target) in found.outgoing:
        click.echo('    {label:12} {rel}  {target}'.format(label = 'holds', rel = rel,
                                                          target = target))
    for (source, rel) in found.incoming:
        click.echo('    {label:12} {source}  {rel}'.format(label = 'pointed at by',
                                                          source = source, rel = rel))
    if not (found.outgoing or found.incoming):
        click.echo('    no edges')


# -----------------------------------------------------------------------------
def write_walk(list_step, id_format, list_edge = None):
    """
    Write the steps of a walk or a path: as text, as json, or as a
    drawing in dot or mermaid with the edges given, or those the walk
    reached each item by.

    """

    if id_format in ('dot', 'mermaid'):
        click.echo(cc_public.query.drawing(list_step, id_format, list_edge), nl = False)
        return

    if id_format == 'json':
        click.echo(json.dumps([s._asdict() for s in list_step], indent = 2))
        return

    for s in list_step:
        if s.id_from is None:
            click.echo(s.id_self)
        else:
            arrow = '->' if s.direction == 'out' else '<-'
            click.echo('{pad}{arrow} {rel:28} {id}'.format(pad = '  ' * s.depth, arrow = arrow,
                                                          rel = s.id_relation, id = s.id_self))
    click.echo('{n} item(s).'.format(n = len(list_step)))


# -----------------------------------------------------------------------------
def write_rows(names, rows, id_format):
    """
    Write the rows of a query, as a table or as json.

    """

    if id_format == 'json':
        click.echo(json.dumps([dict(zip(names, row, strict = True)) for row in rows], indent = 2))
        return

    width = [max([len(n)] + [len(str(r[i])) for r in rows]) for (i, n) in enumerate(names)]
    click.echo('  '.join(n.ljust(w) for (n, w) in zip(names, width, strict = True)))
    for row in rows:
        click.echo('  '.join(str(v).ljust(w) for (v, w) in zip(row, width, strict = True)))
    click.echo('{n} row(s).'.format(n = len(rows)))


# -----------------------------------------------------------------------------
def write_glossary(list_term, id_format):
    """
    Write every term, as text or as json.

    """

    if id_format == FORMAT_JSON:
        click.echo(json.dumps([t._asdict() for t in list_term], indent = 2))
        return

    for term in list_term:
        click.echo('{id:40} {word}'.format(id = term.id_self, word = term.term))

    click.echo('{n} term(s).'.format(n = len(list_term)))


# -----------------------------------------------------------------------------
def write_glossary_lookup(word, found, id_format):
    """
    Write the entries that claim a word and the entries that reject it,
    as text or as json.

    """

    (accepted, avoided) = found

    if id_format == FORMAT_JSON:
        click.echo(json.dumps({'word':     word,
                               'accepted': [t._asdict() for t in accepted],
                               'avoided':  [t._asdict() for t in avoided]}, indent = 2))
        return

    for term in accepted:
        _write_term(term)

    for term in avoided:
        click.echo('{id}  rejects {word}: write {term}.'.format(
                        id = term.id_self, word = word, term = term.term))
        click.echo('    {brief}'.format(brief = term.brief))

    if len(accepted) > 1:
        click.echo('{word} names {n} concepts. An occurrence of it names one of '
                   'them.'.format(word = word, n = len(accepted)))
    elif not accepted and not avoided:
        click.echo('No glossary in this tree holds {word}.'.format(word = word))


# -----------------------------------------------------------------------------
def _write_term(term):
    """
    Write one term entry.

    """

    click.echo('{id}  {word}'.format(id = term.id_self, word = term.term))
    click.echo('    {brief}'.format(brief = term.brief))

    for (label, value) in (('also', ', '.join(term.also)),
                           ('avoid', ', '.join(term.avoid)),
                           ('decided by', ', '.join(term.decider))):
        if value:
            click.echo('    {label:11} {value}'.format(label = label, value = value))


# -----------------------------------------------------------------------------
def write_glossary_senses(found, id_format):
    """
    Write the words more than one entry claims, and the readable ids
    that number a sense, as text or as json.

    """

    (shared, numbered) = found

    if id_format == FORMAT_JSON:
        click.echo(json.dumps({'shared':   [{'word': w, 'id_self': list(ids)}
                                            for (w, ids) in shared],
                               'numbered': list(numbered)}, indent = 2))
        return

    for (word, list_id) in shared:
        click.echo('{word:24} {ids}'.format(word = word, ids = ', '.join(list_id)))

    for id_self in numbered:
        click.echo('{id}  numbers a sense. A readable id distinguishes one in '
                   'words.'.format(id = id_self))

    click.echo('{n} word(s) named by more than one concept.'.format(n = len(shared)))


# -----------------------------------------------------------------------------
def write_glossary_gaps(found, minimum, id_format):
    """
    Write the words and pairs of words prose uses that no glossary
    holds, and the terms no record decides, as text or as json.

    """

    (list_word, list_pair, undecided) = found

    if id_format == FORMAT_JSON:
        click.echo(json.dumps({'word':      [{'phrase': p, 'count_item': n}
                                             for (p, n) in list_word],
                               'pair':      [{'phrase': p, 'count_item': n}
                                             for (p, n) in list_pair],
                               'undecided': list(undecided)}, indent = 2))
        return

    for (title, rows) in (('Pairs', list_pair), ('Words', list_word)):
        click.echo(title)
        for (phrase, count) in rows[:LIMIT_GAP]:
            click.echo('    {count:5}  {phrase}'.format(count = count, phrase = phrase))
        click.echo('    {n} in all.'.format(n = len(rows)))

    click.echo('{n} term(s) no record decides.'.format(n = len(undecided)))
    click.echo('A candidate is a word used by {m} item(s) or more that no glossary holds. '
               'It is not a finding.'.format(m = minimum))


# -----------------------------------------------------------------------------
def write_execution_test(document, list_report, list_problem, written, id_format):
    """
    Write what one test run observed, the reports a failure makes, and
    what of it was kept, as text or as json.

    """

    if id_format == FORMAT_JSON:
        click.echo(json.dumps({'execution': document,
                               'report':    list(list_report),
                               'problem':   list(list_problem),
                               'written':   list(written)},
                              indent = 2, default = str))
        return

    result = document['result']['main']

    click.echo('{id_self}  {outcome}'.format(id_self = document['id_self'],
                                             outcome = document['execution_outcome']))

    for (label, value) in (('case',       document['id_case']),
                           ('method',     document['id_method']),
                           ('under test', document['id_under_test']),
                           ('result',     result.get('conformance_result',
                                                     'none, it did not run'))):
        click.echo('    {label:15} {value}'.format(label = label, value = value))

    for line in result['observation'].strip().splitlines()[:12]:
        click.echo('        ' + line)

    for report in list_report:
        click.echo('    {label:15} {brief}'.format(label = 'report',
                                                   brief = report['brief'].strip()))
        click.echo('        expected  ' + report['expected'].strip().splitlines()[0])

    for problem in list_problem:
        click.echo('    PROBLEM         ' + problem)

    click.echo('Wrote {what}.'.format(what = ', '.join(written)) if written
               else 'Nothing was written.')


# -----------------------------------------------------------------------------
def write_criticality(record, id_format):
    """
    Write the effective criticality of every item a requirement
    reaches, as text or as json.

    An item absent from the derivation is at the base of every
    dimension, and so is a dimension absent from an item that carries
    another.

    """

    if id_format == FORMAT_JSON:
        click.echo(json.dumps({'base':    record.base,
                               'derived': record.derived}, indent = 2))
        return

    dimension = sorted(record.base)

    click.echo('base  ' + '  '.join('{d} {n}'.format(d = d, n = record.base[d])
                                    for d in dimension))

    if not record.derived:
        click.echo('Nothing declares a criticality, so every item is at the base.')
        return

    click.echo('')

    for name in sorted(record.derived):
        level = record.derived[name]
        click.echo('  {name:<52}{level}'.format(
                    name  = name,
                    level = '  '.join(
                        '{d} {n}'.format(d = d, n = level.get(d, record.base.get(d)))
                        for d in dimension)))

    click.echo('')
    click.echo('{n} item(s) a requirement reaches.'.format(n = len(record.derived)))
