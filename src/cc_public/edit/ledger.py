"""
---

id_self:                pym_cc_public.edit.ledger
guid_self:              pym_2ca905d838364b58b8f936667aea6b02
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Ledger
brief:                  |
                        What an operation has written, so that it can
                        be put back.
description:            |
                        A file the operation made is deleted. A file
                        it changed is rewritten from the bytes it had
                        before. A file it moved is moved back. Nothing
                        else is touched. The executor and the multi
                        file edit commands keep one, so that a run
                        that stops and an edit that fails leave the
                        tree as they found it.
relation:               []

...
"""


import pathlib


# -----------------------------------------------------------------------------
class Ledger:
    """
    What an operation has written, so that it can be put back.

    Restoring is done in the reverse of the order things happen in: a
    moved file goes back to where it was, then a changed file gets its
    bytes back, then a made file goes. Restoring twice does nothing the
    second time.

    """

    def __init__(self):
        self.created  = []
        self.modified = {}
        self.moved    = []

    # -------------------------------------------------------------------------
    def note_create(self, path):
        """
        Note that path is about to be made.

        """

        self.created.append(pathlib.Path(path))

    # -------------------------------------------------------------------------
    def note_modify(self, path):
        """
        Note that path is about to change, keeping the bytes it has.

        A file noted twice keeps the bytes it had the first time, and a
        file this ledger made is not kept at all, since it goes.

        """

        path = pathlib.Path(path)

        if path not in self.modified and path not in self.created:
            self.modified[path] = path.read_bytes()

    # -------------------------------------------------------------------------
    def note_move(self, source, target):
        """
        Note that source is about to become target.

        """

        self.moved.append((pathlib.Path(source), pathlib.Path(target)))

    # -------------------------------------------------------------------------
    def restore(self):
        """
        Put everything noted back, and forget it.

        """

        for (source, target) in reversed(self.moved):
            if target.exists() and not source.exists():
                target.rename(source)

        for (path, data) in self.modified.items():
            path.write_bytes(data)

        for path in reversed(self.created):
            if path.exists():
                path.unlink()

        self.clear()

    # -------------------------------------------------------------------------
    def clear(self):
        """
        Forget everything noted, because it is to be kept.

        """

        self.created  = []
        self.modified = {}
        self.moved    = []
