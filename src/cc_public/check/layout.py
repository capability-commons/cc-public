"""
---

id_self:                pym_cc_public.check.layout
guid_self:              pym_c5f42478b5bd426d89b1f15a4be94945
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Layout check
brief:                  |
                        Check that documents are laid out as the
                        printer would lay them out.
description:            |
                        Compares each YAML file, and the metadata
                        document in the docstring of each python file,
                        with its own formatting. A file that differs
                        is reported at the first line where it does.
usage:                  |
                        Run as part of cctool check. What it reports,
                        cctool format fixes.
relation:               []

...
"""


import cc_public.check.result
import cc_public.layout


ID_CHECK = 'layout'
TITLE    = 'Documents are laid out as the printer lays them out'
NOUN     = 'file'

SUFFIX   = (cc_public.layout.SUFFIX_YAML, cc_public.layout.SUFFIX_PYTHON)


# -----------------------------------------------------------------------------
def check(context):
    """
    Return a Result naming every file the printer would change.

    """

    count_file         = 0
    list_nonconformity = []
    list_note          = []

    for filepath in sorted(context.list_filepath):

        if filepath.suffix not in SUFFIX:
            continue

        try:
            text = filepath.read_text(encoding = 'utf-8')
        except (OSError, UnicodeDecodeError):
            continue

        count_file += 1

        try:
            laid_out = cc_public.layout.format_source(text, filepath.suffix)
        except cc_public.layout.Unsupported as err:
            list_note.append(cc_public.check.result.Note(
                    filepath = str(filepath),
                    message  = 'Not examined. {err}'.format(err = err)))
            continue
        except Exception as err:
            list_note.append(cc_public.check.result.Note(
                    filepath = str(filepath),
                    message  = 'Not examined. The printer failed: '
                               '{err}'.format(err = err)))
            continue

        if laid_out == text:
            continue

        list_nonconformity.append(cc_public.check.result.Nonconformity(
                filepath = str(filepath),
                path     = str(_first_difference(text, laid_out)),
                message  = 'Not laid out as cctool format would lay it '
                           'out. Run cctool format.',
                severity = cc_public.check.result.SEVERITY_ADVISORY))

    return cc_public.check.result.Result(count_item         = count_file,
                                         list_nonconformity = list_nonconformity,
                                         list_note          = list_note)


# -----------------------------------------------------------------------------
def _first_difference(text, other):
    """
    Return the one based line number at which two texts first differ.

    """

    list_a = text.splitlines()
    list_b = other.splitlines()

    for (index, (a, b)) in enumerate(zip(list_a, list_b, strict = False), 1):
        if a != b:
            return index

    return min(len(list_a), len(list_b)) + 1
