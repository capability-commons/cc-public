"""
---

id_self:                pym_cc_public.cli.group
guid_self:              pym_2eafe633dcb14f25a475d4c85e1f8111
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Command group
brief:                  |
                        The group every command registers on, and what
                        every command shares.
description:            |
                        Holds main, which loads the environment for a
                        judge, the root option, the odd-integer type,
                        the exit statuses, and the two helpers a
                        command calls: tree, which opens the roots
                        given or the working directory, and fail,
                        which reports a failure and exits with the
                        error status. Every other module in the
                        package registers its commands here.
relation:               []

...
"""


import pathlib

import click
import dotenv

import cc_public.check
import cc_public.check.schema
import cc_public.cli.report
import cc_public.commit
import cc_public.control
import cc_public.edit.accept
import cc_public.edit.field
import cc_public.edit.insert
import cc_public.edit.link
import cc_public.edit.new
import cc_public.edit.rename
import cc_public.edit.tree
import cc_public.eval.case
import cc_public.eval.check
import cc_public.eval.measure
import cc_public.eval.runner
import cc_public.eval.select
import cc_public.evidence
import cc_public.layout
import cc_public.load.git
import cc_public.question
import cc_public.trace
import cc_public.workflow.generate
import cc_public.workflow.graph
import cc_public.workflow.run


EXIT_OK            = 0
EXIT_NONCONFORMITY = 1
EXIT_ERROR         = 2


# -----------------------------------------------------------------------------
class Odd(click.ParamType):
    """
    An odd positive integer: a count of judgements a majority exists over.

    """

    name = 'odd integer'

    def convert(self, value, param, ctx):
        try:
            return cc_public.eval.runner.check_count(int(value), 'The count')
        except ValueError as err:
            self.fail(str(err), param, ctx)


ODD = Odd()


# -----------------------------------------------------------------------------
@click.group()
def main():
    """
    Capability commons tooling.

    """

    # Credentials for a judge are read from the environment, and a .env
    # file is a convenience for a working copy rather than a place to
    # keep anything in a deployed one.
    #
    dotenv.load_dotenv()


# -----------------------------------------------------------------------------
def tree(list_root):
    """
    Return the item tree under the roots given, or the working directory.

    """

    return cc_public.edit.tree.Tree(list_root or (pathlib.Path('.'),))


# -----------------------------------------------------------------------------
def fail(err):
    """
    Report one error and exit as an analysis failure.

    """

    click.echo(str(err), err = True)
    raise SystemExit(EXIT_ERROR)


OPTION_ROOT = click.option('--root', 'list_root', multiple = True,
                           type = click.Path(path_type = pathlib.Path),
                           help = 'A directory tree holding the items. May '
                                  'be given more than once. Defaults to the '
                                  'working directory.')
