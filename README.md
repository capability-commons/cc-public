# Capability commons

An engineering system built on one graph. Every file in it is a data
item, and the graph is made of the data items that also have an identity:
a type, a schema, a concept, a concern, a decision, an option, an
annotation, a python module. These identifiable data items refer to
one another by typed edges, and the whole graph is checked
mechanically before it is committed.

## What is here

| path                                 | holds                                          |
|--------------------------------------|------------------------------------------------|
| `_data/register/`                    | the registers: concepts, concerns, types, relations, relation constraints, roles, protective marks, writing style rules |
| `_data/schema/`                      | the JSON Schema of every type of item          |
| `_data/decision/`                    | a folder for each decision, with its options, annotations and ruling |
| `_data/logical_component/`           | the logical components that decisions are about |
| `_data/requirement/`                 | requirements                                   |
| `_data/external_document/`           | the standards and other documents that items cite |
| `_data/interface_control_document/`  | interface control documents                    |
| `_data/dataflow_graph/`              | dataflow graphs                                |
| `src/cc_public/graph`                | fact extraction, logic programs, and the SQL, SPARQL, jq and text queries over the graph |
| `src/cc_public/check`                | the checks, as logic program rules, and schema validation |
| `src/cc_public/edit`                 | edits that refuse to add a failure, and the layout printer |
| `src/cc_public/commit`               | the commit item of each commit message, and the checks of a commit and of history |
| `src/cc_public/gate`                 | the gate: check, lint and test what a commit records |
| `src/cc_public/export`               | the graph as pages of markdown, for Obsidian and OKF |
| `src/cc_public/requirement`          | the statement of a requirement, composed from its slots |
| `src/cc_public/web`                  | the review pages that `cctool serve` serves    |
| `src/cc_public/cli`                  | `cctool`, the command line                     |
| `.githooks/`                         | the git hooks that `pixi run hooks` turns on   |
| `.agents/skills/`                    | procedures for coding agents; `AGENTS.md` is their guide |

Every item has an id and a guid, each beginning with the prefix of its
type (`concept_concept`, `concept_820f...`). A YAML file under `_data` holds a
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
the checker and of logic program queries.

    pixi install
    pixi run hooks        # once per clone: gate every commit
    pixi run browsers     # once: the Chromium that the browser tests drive
    pixi run check        # cctool check: every check over the tree
    pixi run test         # pytest, one worker for each processor
    pixi run lint         # ruff
    pixi run slow         # the tests on Python 3.12, 3.13 and 3.14

The slow run is too slow for every commit, so the gate leaves it out.
Run it on its own, such as overnight or before a release. The gate
also leaves out the tests marked slow, which grow with the data or
repeat its check stage; `pixi run test` runs them.

Once `pixi run hooks` has run, git runs `cctool gate` before each
commit. It copies the staged content, which is what the commit will
record, and runs the check, the lint and the tests over the copy. A
failure stops the commit. The tests run only when code is staged:
something under `src/` or `.githooks/`, or a change to
`pyproject.toml` or `pixi.lock`. A commit of data alone is checked and
linted, but not tested. The gate of a commit also leaves out the tests
marked prepush, which test the commit and history machinery. The gate
of a push runs every test but those marked slow, on what the push
sends.

The commit-msg hook then checks that the message holds a commit item
whose title is built from one of the templates in `sch_commit`, and
checks the commit against the graph before and after it: no item
disappears or changes type without the commit naming it, and the verb
of the title is true of the change. For a merge or a revert, the
prepare-commit-msg hook first makes the message git drafts into one
that passes. git runs no pre-commit hook for a merge, so the
pre-merge-commit hook runs the gate in its place. A revert is not
gated: it restores content that passed when it was committed. git runs
no commit-msg hook for a revert either, so the message of a revert is
first checked by the pre-push hook.

The check in the gate of a commit keeps two kinds of verdict in a
store, `.git/cc_public_store`, which every worktree of the clone
shares: whether each file is laid out as `cctool format` writes it,
and whether each document conforms to its schema. A verdict is reused
for the same text checked by the same code of cc_public. The checks of
the logic programs are run afresh each time. The gate of a push uses
no store. Set `CC_PUBLIC_STORE` to a directory to have `cctool check`
use a store too.

The commit hooks give early feedback, and git skips them for a rebase
or a cherry-pick, as does anyone with `--no-verify` or a clone without
`pixi run hooks`. The check of record is `cctool history check`: it
checks each commit from what it records, however it was made. The
pre-push hook runs it with `--gate` on the commits a push of a branch
would send; a pushed tag names history already made, and is passed over.

## cctool

    cctool check                            check the tree
    cctool gate                             check, lint and test what is staged
    cctool message new TITLE --brief TEXT   write a commit message
    cctool message check FILEPATH           check a commit message
    cctool message draft FILEPATH           give a merge or revert message its item
    cctool history check [RANGE]... [--gate]
                                            check commits already made
    cctool history check --pre-push REMOTE  check what a push would send
    cctool impact [REV] [--staged]          what a commit touches, and what is near
    cctool format [--check]                 lay out every YAML document
    cctool query sql|logic [QUERY]          query the predicates of the graph
    cctool query sparql [QUERY]             query the graph as RDF triples
    cctool query jq [QUERY]                 query the YAML documents as written
    cctool query text [QUERY]               find items by the words of their prose
    cctool query predicates                 list the predicates and columns
    cctool export obsidian|okf DIRPATH      write the graph as markdown pages
    cctool serve [--port PORT]              serve the review pages of the decisions
    cctool new ID [--field NAME VALUE]... [--link RELATION TARGET]...
    cctool header FILEPATH [ID] [--field NAME VALUE]... [--link ...]
    cctool link SOURCE RELATION TARGET
    cctool unlink SOURCE RELATION TARGET
    cctool set ID FIELDPATH VALUE [--yaml]
    cctool unset ID FIELDPATH
    cctool remove ID
    cctool rename OLD NEW
    cctool batch FILEPATH                   several edits as one

Each edit is checked with the tree as it would be, and written only if
it adds no failure. `--dry-run` prints it as a diff instead.

## License

Apache License 2.0. See `LICENSE` and `NOTICE`.
