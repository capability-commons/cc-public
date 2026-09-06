"""
---

id_self:                pym_cc_public.cli.rendering
guid_self:              pym_0ebbac10169d48ee856c9df0b4261283
copyright:              Copyright 2026 William Payne
license:                Apache-2.0

protective_mark:

  - id_mark:            mark_public
    guid_mark:          mark_0c96ccb7b7534574acf6ed42f9deba0f

title:                  Rendering command
brief:                  |
                        render: the dossier rooted at an observation,
                        as two documents.
description:            |
                        Reads the tree and, where given, a findings
                        report, projects the dossier, draws its graph,
                        renders the briefing and the technical
                        appendix, and writes them as HTML, PDF or both
                        into a directory. Writes nothing into the
                        tree.
relation:               []

...
"""


import json
import pathlib

import click

import cc_public.cli.group
import cc_public.edit.tree


FORMATS  = ('pdf', 'html', 'both')
NAMES    = ('briefing', 'appendix')


# -----------------------------------------------------------------------------
@cc_public.cli.group.main.command(name = 'render')
@click.argument('id_observation')
@click.option('--out', 'dirpath_out', default = pathlib.Path('render'),
              type = click.Path(file_okay = False, path_type = pathlib.Path),
              help = 'The directory the documents are written into.')
@click.option('--findings', 'path_report', default = None,
              type = click.Path(exists = True, dir_okay = False, path_type = pathlib.Path),
              help = 'A report from check --eval --format json --out FILE, whose eval '
                     'findings the appendix lists against each requirement.')
@click.option('--format', 'id_format', default = 'both', type = click.Choice(FORMATS),
              show_default = True)
@cc_public.cli.group.OPTION_ROOT
def render_(id_observation, dirpath_out, path_report, id_format, list_root):
    """
    Render the dossier rooted at an observation as two documents, a
    briefing and a technical appendix. Reads the tree and a findings
    report; writes nothing into the tree.

    """

    # The render tier is imported here, not at the top: it needs the
    # render extra, and a tree that never draws a document should not
    # have to install it to check or edit.
    #
    import cc_public.render.dossier
    import cc_public.render.graph
    import cc_public.render.html
    import cc_public.render.pdf

    tree   = cc_public.cli.group.tree(list_root)
    report = json.loads(path_report.read_text(encoding = 'utf-8')) if path_report else None

    try:
        projection = cc_public.render.dossier.dossier(tree, id_observation, report)
    except cc_public.edit.tree.ErrorItem as err:
        cc_public.cli.group.fail(err)

    svg   = cc_public.render.graph.svg(projection['graph']['dot'])
    pages = {'briefing': cc_public.render.html.briefing(projection),
             'appendix': cc_public.render.html.appendix(projection, svg)}
    dirpath_out.mkdir(parents = True, exist_ok = True)

    for (name, text) in pages.items():
        if id_format in ('html', 'both'):
            path = dirpath_out / (name + '.html')
            path.write_text(text, encoding = 'utf-8')
            click.echo(path)
        if id_format in ('pdf', 'both'):
            click.echo(cc_public.render.pdf.write(text, dirpath_out / (name + '.pdf')))
