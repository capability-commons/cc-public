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
                        Writes a report as text for a person, or as
                        JSON, YAML or XML for a program. Findings go
                        to standard output in every format; standard
                        error is reserved for failures of the analysis
                        itself.

...
"""


import json
import pathlib
import sys

import rich.console
import rich.table
import rich.text



FORMAT_TEXT = 'text'
FORMAT_JSON = 'json'
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
