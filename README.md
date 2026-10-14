# Capability commons

A document-oriented engineering system. Every artifact is a data item
with an identity: a type, a schema, a concept, a concern, a decision,
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
item in its module docstring, and any other file in a comment at its
head.

## Getting started

Development is supported on Linux and macOS. Windows is not
supported as a development environment: the repository holds symbolic
links, and the tools assume a POSIX shell.

The environment is managed by [pixi](https://pixi.sh). Datalog is
evaluated by [souffle](https://souffle-lang.github.io), which is found
on the PATH or through the SOUFFLE environment variable.

    pixi install
    pixi run hooks        # once per clone: gate every commit
    pixi run check        # cctool check: every check over the tree
    pixi run test         # pytest
    pixi run lint         # ruff

Once `pixi run hooks` has run, git runs `cctool gate` before each
commit. It copies the staged content, which is what the commit will
record, and runs the check, the lint and the tests over the copy. A
failure stops the commit.

## cctool

    cctool check                            check the tree
    cctool gate                             check, lint and test what is staged
    cctool format [--check]                 lay out every document
    cctool query sql|datalog QUERY          query the graph
    cctool query schema                     list the relations and columns
    cctool new ID [--field NAME VALUE]... [--link RELATION TARGET]...
    cctool link SOURCE RELATION TARGET
    cctool set ID NAME VALUE
    cctool batch FILE                       several edits as one

Each edit is checked with the tree as it would be, and written only if
it adds no failure. `--dry-run` prints it as a diff instead.

## Licence

Apache License 2.0. See `LICENSE` and `NOTICE`.
