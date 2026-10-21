"""
---

id_self:                pym_cc_public.graph.jq
guid_self:              pym_35e318dfc56949c2ab352487558b200c
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  jq evaluation
brief:                  |
                        Evaluate a jq filter over the documents of the
                        graph of data items, with the jq program.
description:            |
                        This module gives jq the YAML documents of the
                        tree as one JSON array, with an object for
                        each file that holds a document: its file, the
                        line its document starts on, and the document.
                        Unlike the SQL and logic program queries,
                        which see the facts extracted from the
                        documents, a jq filter sees the documents
                        themselves, nested as they are written. The jq
                        program is run as a subprocess, and changes
                        nothing.
edge:                   []

...
"""


import json
import subprocess

import cc_public.graph.extract


PROGRAM           = 'jq'
KEY_FILE          = 'file'
KEY_LINE          = 'line'
KEY_DOCUMENT      = 'document'


# -----------------------------------------------------------------------------
class ErrorJq(Exception):
    """
    A jq filter that cannot be evaluated, or no jq program to run it.

    """


# -----------------------------------------------------------------------------
def records(map_document: cc_public.graph.extract.Documents) -> list[dict]:
    """
    Return a record for each document in map_document: its file, the
    line of its file that it starts on, and the document. Files that
    hold no document are left out.

    """

    return [{KEY_FILE: file, KEY_LINE: line, KEY_DOCUMENT: document}
            for (file, (document, line)) in map_document.items()
            if cc_public.graph.extract.is_document(document)]


# -----------------------------------------------------------------------------
def query(map_document: cc_public.graph.extract.Documents, text: str) -> list:
    """
    Return each result of the jq filter text, evaluated over the
    records of map_document as one array. Raise ErrorJq if it cannot
    be evaluated.

    """

    # A value YAML reads that JSON has no type for, such as a date,
    # is given to jq as text.
    #
    data = json.dumps(records(map_document), default = str)

    try:
        process = subprocess.run([PROGRAM, '--compact-output', text],
                                 input          = data,
                                 capture_output = True,
                                 text           = True,
                                 check          = False)
    except FileNotFoundError as error:
        raise ErrorJq('There is no jq program to run. Run pixi install, '
                      'which installs it into the environment.') from error

    if process.returncode != 0:
        raise ErrorJq(process.stderr.strip())

    return [json.loads(line) for line in process.stdout.splitlines()]
