"""
---

id_self:                pym_cc_public.edit.sweep
guid_self:              pym_36ed66d741044859a43fd8ce08d95f15
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Sweep
brief:                  |
                        Make a sweep item from a check report: the
                        findings of the evals, grouped by eval and
                        rule.
description:            |
                        Reads the eval check of a report written by
                        check --eval --format json, groups its
                        findings by the eval that raised them and the
                        rule they name, and writes a sweep data item
                        holding one finding group per shape, largest
                        first, with the count, the items and a sample
                        of the messages. The step that turns findings
                        into data the improvement loop can read.
relation:               []

...
"""


import collections
import json
import pathlib
import re

import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.new
import cc_public.edit.tree


TYPE_SWEEP      = 't_sweep'
TYPE_GROUP      = 't_finding_group'
PREFIX_SWEEP    = 'swp'
KEY_REPORT      = 'report'
KEY_CHECK       = 'check'
KEY_ID_CHECK    = 'id_check'
ID_CHECK_EVAL   = 'eval'
KEY_FINDING     = 'nonconformity'
KEY_DETAIL      = 'detail'
KEY_MODEL       = 'id_model'
KEY_COUNT       = 'count_item'
KEY_GROUP       = 'group'
COUNT_SAMPLE    = 3
RE_RULE         = re.compile(r'\brule_[a-z0-9_]+')
RE_SLUG         = re.compile(r'[^a-z0-9]+')
SEPARATOR       = '_'


# -----------------------------------------------------------------------------
def sweep(tree, path_report, id_self, title = None, brief = None):
    """
    Make a sweep item from a check report holding an eval check, its
    findings grouped by eval and by the rule they name, and return the
    Item. Refuse a report with no eval check in it.

    """

    with open(path_report, encoding = 'utf-8') as file:
        report = json.load(file)

    report = report.get(KEY_REPORT, report)
    found  = [c for c in report.get(KEY_CHECK) or [] if c.get(KEY_ID_CHECK) == ID_CHECK_EVAL]

    if not found:
        raise cc_public.edit.tree.ErrorItem(
                '{path} holds no eval check; a sweep is of what the evals '
                'found.'.format(path = path_report))

    check    = found[0]
    findings = check.get(KEY_FINDING) or []
    groups   = _groups(findings)

    cc_public.edit.new.new(tree, TYPE_SWEEP, id_self, tree.defaults())
    cc_public.edit.field.set_field(tree, id_self, 'title', value = title or (
                'Sweep of {n} findings'.format(n = len(findings)))[:80])
    cc_public.edit.field.set_field(tree, id_self, 'brief', prose = brief or (
                'What the evals found over {n} judgements, from the report at {path}, '
                'grouped by eval and rule.'.format(n = check.get(KEY_COUNT, 0),
                                                   path = pathlib.Path(path_report).name)))
    judge = (check.get(KEY_DETAIL) or {}).get(KEY_MODEL) or 'unknown'
    cc_public.edit.field.set_field(tree, id_self, 'judge', value = str(judge))
    cc_public.edit.field.set_field(tree, id_self, 'count_judgement',
                                   value = int(check.get(KEY_COUNT) or 0))
    cc_public.edit.field.set_field(tree, id_self, 'count_finding',
                                   value = len(findings))

    for (key, (id_eval, rule, list_item, list_message)) in groups:
        (_, id_group) = cc_public.edit.insert.insert(tree, TYPE_GROUP, key, id_self, KEY_GROUP)
        cc_public.edit.field.set_field(tree, id_group, 'id_eval', value = id_eval)
        if rule:
            cc_public.edit.field.set_field(tree, id_group, 'rule', value = rule)
        cc_public.edit.field.set_field(tree, id_group, 'count',  value = len(list_item))
        cc_public.edit.field.set_field(tree, id_group, 'item',   prose = ' '.join(list_item))
        cc_public.edit.field.set_field(tree, id_group, 'sample',
                                       prose = '\n\n'.join(list_message[:COUNT_SAMPLE]))

    return tree.resolve(id_self)


# -----------------------------------------------------------------------------
def _groups(findings):
    """
    Return [(key, (id_eval, rule, items, messages))], largest first,
    one per eval and rule named; a finding naming no rule the register
    could hold groups under its eval alone.

    """

    out = collections.OrderedDict()

    for finding in findings:
        id_eval = pathlib.Path(str(finding.get('filepath', ''))).stem
        message = ' '.join(str(finding.get('message', '')).split())
        named   = [r for r in RE_RULE.findall(message) if 'No rule named ' + r not in message]
        rule    = named[0] if named else ''
        parts   = [id_eval.split(SEPARATOR, 1)[-1], rule.split(SEPARATOR, 1)[-1] or 'none']
        key     = RE_SLUG.sub(SEPARATOR, SEPARATOR.join(parts)).strip(SEPARATOR)
        entry   = out.setdefault(key, (id_eval, rule, [], []))
        entry[2].append(str(finding.get('path', '')))
        entry[3].append(message)

    return sorted(out.items(), key = lambda kv: (-len(kv[1][2]), kv[0]))
