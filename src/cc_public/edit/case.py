"""
---

id_self:                pym_cc_public.edit.case
guid_self:              pym_526d7635fff54b9181e88a61a869704b
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Add a control case
brief:                  |
                        Turn a live finding into a control case, with
                        the subject captured as the judge saw it.
description:            |
                        Renders the item for the eval exactly as a
                        sweep would, and holds that text as the case's
                        subject. The verdict a person gives sets the
                        origin: met is a suppressed finding, unmet a
                        confirmed one. The case goes into the eval's
                        control set, made where absent, keyed by the
                        content of its subject.
relation:               []

...
"""



import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.tree
import cc_public.eval.control
import cc_public.eval.select
import cc_public.path


PREFIX_SET     = 'ctl'
SEPARATOR      = '_'
DIR_SET        = 'eval'
REL_MEASURES   = 'r_measures'
REL_SNAPSHOT   = 'r_is_snapshot_of'
VERDICT_MET    = 'met'
ORIGIN_MET     = 'suppressed'
ORIGIN_UNMET   = 'confirmed'


# -----------------------------------------------------------------------------
def case(tree, id_eval, name_item, verdict, note, origin = None):
    """
    Add the case and write it. Return (id_set, id_case).

    origin says where the case came from. Absent, a met verdict is a
    finding suppressed and an unmet one a finding confirmed; written
    marks a subject a person wrote and holds to the verdict.

    """

    eval_item = tree.resolve(id_eval)
    subj_item = tree.resolve(name_item)
    doc_eval  = tree.context.map_document[eval_item.filepath]
    doc_subj  = tree.context.map_document[subj_item.filepath]

    node = doc_subj
    for step in cc_public.path.split(subj_item.path):
        node = node[int(step)] if isinstance(node, list) else node[step]

    text = cc_public.eval.select.render(((subj_item.id_self, node),),
                                         doc_eval)

    if not text.strip():
        raise cc_public.edit.tree.ErrorItem(
                '{item} has nothing in the scope of {eval}, so there is '
                'nothing to hold as a subject.'.format(item = subj_item.id_self,
                                                       eval = id_eval))

    id_set = _set_for(tree, id_eval)
    key    = cc_public.eval.control.key_of(text)

    (key, id_case) = cc_public.edit.insert.insert(tree, 't_control_case', key,
                                                  id_set, 'case')

    cc_public.edit.field.set_field(tree, id_case, 'subject', prose = text)
    cc_public.edit.field.set_field(tree, id_case, 'verdict', value = verdict)
    cc_public.edit.field.set_field(tree, id_case, 'origin',
                                   value = origin or (ORIGIN_MET if verdict == VERDICT_MET
                                                      else ORIGIN_UNMET))
    if note:
        cc_public.edit.field.set_field(tree, id_case, 'note', prose = note)

    cc_public.edit.link.link(tree, id_case, REL_SNAPSHOT, subj_item.id_self)

    return (id_set, id_case)


# -----------------------------------------------------------------------------
def _set_for(tree, id_eval):
    """
    Return the id of the control set for the eval, making one if none.

    """

    id_set = PREFIX_SET + SEPARATOR + id_eval.split(SEPARATOR, 1)[1]

    if id_set in tree.map_id:
        return id_set

    root = tree.resolve(id_eval).filepath.parent

    cc_public.edit.new.new(tree, 't_control_set', id_set,
                           tree.defaults(), root)

    cc_public.edit.field.set_field(tree, id_set, 'title',
                                   value = 'Control set for ' + id_eval)
    cc_public.edit.field.set_field(tree, id_set, 'brief',
                                   prose = 'Cases with known verdicts for '
                                           + id_eval + '.')
    cc_public.edit.field.set_field(tree, id_set, 'description',
                                   prose = 'Each case holds a subject as the '
                                           'judge is shown it, the verdict a '
                                           'person holds it to, and where the '
                                           'case came from.')
    cc_public.edit.link.link(tree, id_set, REL_MEASURES, id_eval)

    return id_set
