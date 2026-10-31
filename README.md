# Capability Commons

An engineering system built on one graph. Almost every file in it is a
data item, and the graph is made of the data items that also have an
identity: a type, a schema, a concept, a concern, a decision, an option,
an annotation, a python module. These identifiable data items refer to
one another by typed edges, and the whole graph is checked mechanically
before it is committed.

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
| `src/cctool/graph`                   | fact extraction, logic programs, and the SQL, SPARQL, jq and text queries over the graph |
| `src/cctool/check`                   | the checks, as logic program rules, and schema validation |
| `src/cctool/edit`                    | edits that refuse to add a failure, and the layout printer |
| `src/cctool/commit`                  | the commit item of each commit message, and the checks of a commit and of history |
| `src/cctool/gate`                    | the gate: check and lint what a commit records, and test what a push sends |
| `src/cctool/queue`                   | the landing queue, which tests each patch and lands it on `dev` |
| `src/cctool/export`                  | the graph as pages of markdown, for Obsidian and OKF |
| `src/cctool/requirement`             | the statement of a requirement, composed from its slots |
| `src/cctool/web`                     | the review pages that `cctool serve` serves    |
| `src/cctool/cli`                     | `cctool`, the command line                     |
| `.githooks/`                         | the git hooks that `pixi run hooks` turns on   |
| `systemd/`                           | the user timer that runs the landing queue on atlas |
| `.agents/skills/`                    | procedures for coding agents; `AGENTS.md` is their guide |

Every item has an id and a guid, each beginning with the prefix of its
type (`concept_concept`, `concept_4c11...`). A YAML file under `_data`
holds a standalone item or a register of entries. A python module holds
its item in its module docstring, a class or function that something
points at holds one in its own docstring, and most other files hold
one in a comment at their head. Some files hold no item: the Markdown
guides (this file, `AGENTS.md` and the skills), the license texts
(`LICENSE`, `NOTICE` and the license of the fonts), the generated lock
file `pixi.lock`, the binary fonts, and the style sheet and script of
the review pages. No check yet asks that a file hold an item.

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
record, and runs the check and the lint over the copy, in seconds. A
failure stops the commit. No test runs at commit: the landing queue
runs every test but those marked slow on the tip of each patch before
it lands on `dev`, and the gate of a push runs them on what the push
sends, unless a gate result proves that the tip passed them.

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
store, `.git/cctool_store`, which every worktree of the clone
shares: whether each file is laid out as `cctool format` writes it,
and whether each document conforms to its schema. A verdict is reused
for the same text checked by the same code of cctool. The checks of
the logic programs are run afresh each time. The gate of a push uses
no store. Set `CC_PUBLIC_STORE` to a directory to have `cctool check`
use a store too.

Each run of the gate, of a commit or of a push, times each stage and
appends a line for it to a log, `.git/cctool_timing.jsonl`, which
every worktree shares and no commit records. A line holds when the
stage started, its wall seconds, its outcome, the tree it gated, the
host and the python, and for the tests the seconds of each test and
the name of each test that failed.
`cctool timing` sums up the newest runs.

The commit hooks give early feedback, and git skips them for a rebase
or a cherry-pick, as does anyone with `--no-verify` or a clone without
`pixi run hooks`. The check of record is `cctool history check`: it
checks each commit from what it records, however it was made. The
pre-push hook runs it with `--gate` on the commits a push of a branch
would send; a pushed tag names history already made, and is passed over.

## The landing queue

Work reaches `dev` only through the landing queue. A thread commits on
its topic branch and runs `cctool queue submit ID_PATCH`, which makes
the branch `queue/00_candidate/THREAD/KEY` and returns at once. The
key is the UTC time of submission and the name of the patch.

A systemd user timer on atlas runs `cctool queue run --once` each
minute in the main checkout. A run takes the oldest patch that is
ready, replays and signs its own commits onto `dev` in a worktree of
its own, runs `cctool history check` on each and the gate of a push on
the tip, and writes a gate result for the tip. A patch that conflicts
goes to `queue/01_conflict`, and one that fails to `queue/03_rework`,
with a note; no test is retried. A patch that passes is landed by a
fast-forward of `dev` in the main checkout, and `dev` is pushed. A
failure of the queue itself, such as a dirty main checkout or a key
that cannot sign, pauses it until `cctool queue run --once --resume`.

Work from a machine that cannot reach the queue, such as a remote
session, comes as a bundle: `cctool queue bundle ID_PATCH` writes the
commits beyond `dev` into the inbox that `git config queue.inbox` names,
`/media/wtp/Data1/dev/cc/_queue_inbox` on atlas. Each run of the daemon
submits each bundle there and moves it to `processed`, or to
`rejected` with a note that says why. `cctool queue submit PATH.bundle`
submits one by hand.

The records, the journal, the gate results and a summary for each day
are kept in the git directory: `.git/cctool_queue/`,
`.git/cctool_queue.jsonl`, `.git/cctool_gate_result/` and
`.git/cctool_queue_summary/`. `cctool queue status [--measures]` reads
them.

To set the queue up on atlas, WTP makes two keys, which only atlas
holds:

1. A signing key with no passphrase, for the queue alone. Make it with
   `gpg --batch --passphrase '' --quick-gen-key 'William Payne (cc-public
   landing queue) <wtpayne@gmail.com>' ed25519 sign never`, read its
   long key id with `gpg --list-secret-keys --keyid-format long`, and
   tell git with `git config queue.signingKey KEYID` in the main
   checkout. Register it in a commit signed with the personal key:
   `cctool set member_william_payne git_queue_signing_key KEYID`.
2. A deploy key that can write to cc-public only. Make it with
   `ssh-keygen -t ed25519 -N '' -f ~/.ssh/cc_public_queue`, add the
   public half to the repository on GitHub as a deploy key with write
   access, and give it a host alias of its own in `~/.ssh/config`
   (`Host github-cc-public-queue`, `HostName github.com`, `User git`,
   `IdentityFile ~/.ssh/cc_public_queue`, `IdentitiesOnly yes`). Then
   `git remote add queue git@github-cc-public-queue:capability-commons/cc-public.git`
   and `git config queue.remote queue` in the main checkout.

Then copy `systemd/cctool-queue-run` to `~/.local/bin/`, and
`systemd/cctool-queue.service` and `systemd/cctool-queue.timer` to
`~/.config/systemd/user/`, set `WorkingDirectory` to the main checkout
with `systemctl --user edit cctool-queue.service`, and run
`systemctl --user enable --now cctool-queue.timer`. The script runs
the queue while the main checkout is on `dev`, and pauses it with the
reason while it is not, since a checkout on another branch may hold no
queue at all.

## The night

Each night a systemd user timer on atlas runs `cctool queue night` in
the main checkout. It takes the lock of the landing queue, so landings
wait while it runs, and runs the overnight tasks on the tip of `dev` in
a worktree of its own: `pixi run slow`, `pixi run fuzz`,
`pixi run coverage` and `pixi run check-full`. If every task passes, it
moves the branch `verified` forward to that commit and pushes it; if
not, `verified` stays where it was. The night is recorded in
`.git/cctool_night/`, and its outcome is a gate result of the commit.
Then Claude Code reviews the tree, headless, in a worktree beside the
main checkout, as the daily review describes, or, on Thursday, as the
weekly in-depth review does. It may only read, run
cctool and commit, and it submits its findings, as annotations, to the
queue. Its report is kept in `.git/cctool_review/`, and the summary of
the day shows how the night went.

To set the night up, copy `systemd/cctool-night-run` to `~/.local/bin/`,
and `systemd/cctool-night.service` and `systemd/cctool-night.timer` to
`~/.config/systemd/user/`, set `WorkingDirectory` and `PATH` with
`systemctl --user edit cctool-night.service` as for the queue, with
the folder that holds `claude` on the `PATH`, and run
`systemctl --user enable --now cctool-night.timer`.

## cctool

    cctool check                            check the tree
    cctool friction                         report signals of friction
    cctool gate                             check and lint what is staged
    cctool timing [--runs N]                sum up the times of the gate
    cctool coverage [--data FILEPATH]       check coverage against maturity
    cctool message new TITLE --brief TEXT   write a commit message
    cctool message check FILEPATH           check a commit message
    cctool message draft FILEPATH           give a merge or revert message its item
    cctool history check [RANGE]... [--gate]
                                            check commits already made
    cctool history check --pre-push REMOTE  check what a push would send
    cctool impact [REV] [--staged]          what a commit touches, and what is near
    cctool queue submit ID_PATCH|BUNDLE     hand finished work to the landing queue
    cctool queue bundle ID_PATCH            bundle work for the queue on another machine
    cctool queue resubmit REF               hand back a patch once it is fixed
    cctool queue withdraw REF               take a patch out of the queue
    cctool queue status [--measures]        where each patch stands, and why
    cctool queue run --once [--resume]      one run of the daemon of the queue
    cctool queue night [--no-review]        the overnight tasks, verified and the review
    cctool release prepare --brief TEXT --maturity ID
                                            write the release item and the version
    cctool release check TAG [REV]          check a commit before it is tagged
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
