"""
---

id_self:                pyp_cc_public.workflow
guid_self:              pyp_3d35b87fc79c44ae9ae60d97e82f0128
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Workflow package
brief:                  |
                        Run a dataflow workflow: order its nodes, have
                        each produce or revise its items, judge them,
                        fire its edges, and record what happened.
description:            |
                        Every write a run makes goes through the edit
                        package, so nothing a model produces can be
                        badly formed or badly laid out. The checks run
                        after every node and a critical finding stops
                        the run; what the run touched is then put
                        back.

...
"""


# -----------------------------------------------------------------------------
class Stop(Exception):
    """
    Raised where a run cannot go on. The reason is the message.

    A domain stop, not a crash: the executor catches it, restores what
    the run wrote, and reports the reason. Anything else that is raised
    is a defect and is raised again after the restore.

    """
