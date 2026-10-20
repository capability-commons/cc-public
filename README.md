# Capability commons

A document-oriented engineering system. Every artifact is a data item
with an identity: a type, a schema, a concept, a concern, an option,
an annotation, a python module. Items refer to one another by typed
edges, and the whole graph is checked mechanically before it is
committed.

## What is here

| path                  | holds                                          |
|-----------------------|------------------------------------------------|
| `_data/register/`     | registers: types, relations, concepts, concerns, protective marks, writing style rules |
| `_data/schema/`       | the JSON Schema of every kind of item          |
| `src/cc_public/graph` | fact extraction, Datalog and SQL over the graph |
| `src/cc_public/check` | the checks, in Datalog, and schema validation  |
| `src/cc_public/edit`  | edits that refuse to add a failure, and the layout printer |
| `src/cc_public/cli`   | `cctool`, the command line                     |

Every item has an id and a guid, each beginning with the prefix of its
type (`con_concept`, `con_820f...`). A YAML file under `_data` holds a
standalone item or a register of entries. A python module holds its
item in its module docstring, a class or function that something
points at holds one in its own docstring, and any other file holds
one in a comment at its head.

## Getting started

Development is supported on Linux and on macOS with Apple silicon.
The environment is also locked for Intel Macs, but it is not tested
there, so that platform is unsupported: it should work, and nobody has
checked that it does. Windows is not supported as a development
environment: the repository holds symbolic links, and the tools assume
a POSIX shell.

The environment is managed by [pixi](https://pixi.sh). It includes
[clingo](https://potassco.org/clingo/), which evaluates the rules of
the checker and of Datalog queries.

    pixi install
    pixi run hooks        # once per clone: gate every commit
    pixi run check        # cctool check: every check over the tree
    pixi run test         # pytest, one worker for each processor
    pixi run lint         # ruff
    pixi run slow         # the tests on Python 3.12, 3.13 and 3.14

The slow run is too slow for every commit, so the gate leaves it out.
The gate also leaves out the tests marked slow, which grow with the
data or repeat its check stage; `pixi run test` runs them.
Run it on its own, such as overnight or before a release.

Once `pixi run hooks` has run, git runs `cctool gate` before each
commit. It copies the staged content, which is what the commit will
record, and runs the check, the lint and the tests over the copy. A
failure stops the commit. The commit-msg hook then checks that the
message holds a commit item whose title is built from one of the
templates in `sch_commit`, and checks the commit against the graph
before and after it: no item disappears or changes type without the
commit naming it, and the verb of the title is true of the change.
For a merge or a revert, the prepare-commit-msg hook first makes the
message git drafts into one that passes. git runs no pre-commit hook
for a merge, so the pre-merge-commit hook runs the gate in its place.
A revert is not gated: it restores content that passed when it was
committed. git runs no commit-msg hook for a revert either, so the
message of a revert is first checked by the pre-push hook.

The commit hooks give early feedback, and git skips them for a rebase
or a cherry-pick, as does anyone with `--no-verify` or a clone without
`pixi run hooks`. The check of record is `cctool history check`: it
checks each commit from what it records, however it was made. The
pre-push hook runs it with `--gate` on what a push would send.

## cctool

    cctool check                            check the tree
    cctool gate                             check, lint and test what is staged
    cctool message new TITLE --brief TEXT   write a commit message
    cctool message check FILE               check a commit message
    cctool history check [RANGE] [--gate]   check commits already made
    cctool format [--check]                 lay out every document
    cctool query sql|datalog QUERY          query the graph
    cctool query sparql|jq QUERY            query the graph
    cctool query schema                     list the relations and columns
    cctool export obsidian|okf OUT          write the graph as markdown pages
    cctool new ID [--field NAME VALUE]... [--link RELATION TARGET]...
    cctool header PATH [ID] [--field NAME VALUE]... [--link ...]
    cctool link SOURCE RELATION TARGET
    cctool unlink SOURCE RELATION TARGET
    cctool set ID PATH VALUE [--yaml]
    cctool unset ID PATH
    cctool remove ID
    cctool rename OLD NEW
    cctool batch FILE                       several edits as one

Each edit is checked with the tree as it would be, and written only if
it adds no failure. `--dry-run` prints it as a diff instead.

## Licence

Apache License 2.0. See `LICENSE` and `NOTICE`.
