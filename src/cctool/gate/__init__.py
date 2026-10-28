"""
---

id_self:                pyp_cctool.gate
guid_self:              pyp_4aea5c4e11d5432ebffb7f30e6847a4a
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Commit gate
brief:                  |
                        Refuse a commit whose content fails the check,
                        the lint or the tests.
description:            |
                        This package holds the gate that the
                        pre-commit hook runs over the content a commit
                        would record.

edge:

  - id_relation:        relation_realizes
    guid_relation:      relation_c1f1f5ffece0495981ab2b6ebb32a92f
    id_target:          lco_tooling_gate
    guid_target:        lco_32ec17050dab45ba9cfbf2a3a3338eb2

...
"""
