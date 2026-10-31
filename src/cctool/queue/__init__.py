"""
---

id_self:                pyp_cctool.queue
guid_self:              pyp_52547fc028a6496ab2292c78150728a2
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Landing queue
brief:                  |
                        Take submitted patches in turn, replay and
                        sign each onto dev, run the landing gate, and
                        land only what passed.
description:            |
                        A thread submits finished work as a branch
                        under queue/00_candidate, and moves on. The
                        daemon, run by cctool queue run, takes the
                        oldest eligible patch, replays and signs its
                        own commits onto dev in a private worktree,
                        and runs the history check on each and the
                        gate on the tip. A patch that conflicts goes
                        to queue/01_conflict, and one that fails to
                        queue/03_rework, for an agent to fix and
                        resubmit. A patch that passes is landed by a
                        fast-forward of dev in the main checkout. A
                        record of each patch, held in the git
                        directory and kept alive by refs under
                        refs/queue, says what it is, what it depends
                        on, and every attempt made at it.

edge:

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          lco_landing_queue
    guid_target:        lco_6fb8deebc0c04a5f85904d6e59dddc54

...
"""
