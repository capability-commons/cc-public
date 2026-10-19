# Guidance for agents

This file is for any coding agent working in cc-public. `README.md`
says what the repository is and how to run it. This file says how to
work in it.

## Working beside other agents

Several agents work in this repository at once. Each works in a git
worktree of its own, on a branch of its own, so no agent sees the
unfinished edits of another.

- `dev` is the integration branch. The main checkout, `cc-public`,
  stays on `dev`. Nobody edits files there; it is only where finished
  branches land.
- Read the claims before you start. In the main checkout,
  `cat .git/worktrees/*/locked` lists each worktree with its owner and
  the area it changes. If another worktree claims files you need,
  agree it with the owner, or ask Will, first.
- Start a topic from the main checkout. TOPIC is a short name for the
  work, in lower case with hyphens:

  ```bash
  git worktree add -b TOPIC ../cc-public-TOPIC dev
  echo "gitdir: ../cc-public/.git/worktrees/cc-public-TOPIC" > ../cc-public-TOPIC/.git
  echo "OWNER: AREA" > .git/worktrees/cc-public-TOPIC/locked
  ```

  The second line makes the link from the worktree relative. Git
  writes an absolute path, and the folder has a different path on
  each machine and in each remote session, so an absolute link
  breaks. The third line locks the worktree, so git never prunes it,
  and records who owns it and what it changes. Do not run
  `git worktree repair` or `git worktree move`: both write absolute
  paths again.
- Work, check and commit in your worktree. The first `pixi run` there
  installs its environment. Where pixi cannot run, use the environment
  of the main checkout with `src` first on the path:
  `PYTHONPATH=src ../cc-public/.pixi/envs/default/bin/python -B -m cc_public.cli.command check`.
- Land the branch only when its work is agreed. In the worktree, run
  `git rebase dev`, then `cctool history check dev..TOPIC` and
  `pixi run gate`. Then, in the main checkout, run
  `git merge --ff-only TOPIC`. `dev` only moves forward, so its
  history stays linear. If the merge refuses because `dev` has moved,
  rebase again.
- Once the branch is on `dev` and `git status` in the worktree is
  clean, remove the worktree from the main checkout:

  ```bash
  git worktree unlock cc-public-TOPIC
  git worktree remove cc-public-TOPIC
  git branch -d TOPIC
  ```

  If the folder is still there afterwards, because the worktree was
  made in another session, delete it.

## Before you finish

- `pixi run check`, `pixi run test` and `pixi run lint` all pass.
- `cctool check` reports 0 failures. A failure that was there before
  your change is still yours to report, not to hide.
- Commit locally. Do not push unless asked.
- The pre-commit hook runs `cctool gate`, which checks, lints and
  tests the staged content. Never bypass it with `--no-verify`. If it
  fails, fix the cause, or report it.
- Write each commit message with `cctool message new TITLE --brief
  TEXT`, then add the trailers. The title is an imperative sentence
  built from a template in `sch_commit`, such as `Add OBJECT` or
  `Change OBJECT so that STATEMENT`. One commit does one thing. The
  commit-msg hook checks the message, and checks the commit against
  the graph before and after it.
- For a merge or a revert, keep the message git drafts. The
  prepare-commit-msg hook gives it its commit item, and names what it
  removes or renames.
- The commit hooks are early feedback; git skips them for a rebase or
  a cherry-pick. `cctool history check RANGE` is the check of record,
  and the pre-push hook runs it. After a rebase, run it on the
  rebased commits. Do not add hooks to cover more of git's paths: a
  rule that keeps needing exceptions is fixed in the rule.
- Name in the commit item (title, brief or description) the id of
  every item the commit removes or renames. A renamed register entry
  keeps its old id in `alias`. The verb must be true of the change:
  `Add` removes nothing, `Remove` adds nothing, `Rename` and `Move`
  neither add nor remove, and `Reformat` changes only layout.

## Changing data items

- Prefer `cctool new`, `header`, `link`, `unlink`, `set`, `unset`,
  `remove`, `rename` and `batch` to editing YAML by hand. They mint
  guids, fill in rights, keep the layout, and refuse an edit that adds
  a failure. Use `--dry-run` to see an edit first.
- Give a new python module, Datalog file or script its item with
  `cctool header PATH`. The id of a module follows from its path. A
  class or function gets an item only when something must point at
  it, with `cctool header PATH::NAME`.
- Never write a guid by hand. A guid is the prefix of the type and 32
  hex digits, minted once and never changed.
- A new concept must be named by some other item, so make the concept
  and the item that names it together, with `cctool batch`.
- After any edit by hand, run `cctool format`, then `cctool check`.
- Rename an id with `cctool rename OLD NEW`. It changes every document
  that names the id, moves the file of a standalone item, and keeps
  the old id in the `alias` list of a register entry. It lists any
  file, such as a test, that still names the old id outside a
  document; change those by hand.
- Use the preferred term of a concept in `_data/register/reg_concept.yaml`
  in names and in prose. Never use a term it lists as deprecated.

## Skills

Procedures, and the traps in them, are skills in `.agents/skills/`,
in the Agent Skills format. Codex reads them there, and Claude Code
reads them through `.claude/skills`, a link to the same directory.
`editing-data-items` covers adding and changing items with cctool.

## Finding things out

- `cctool query schema` lists every relation and its columns.
- `cctool query sql "SELECT ..."` for joins and counts, and
  `cctool query datalog '...'` for anything recursive, such as reach
  through edges.
- Read the schema of a type before writing an item of it: the type
  entry in `reg_data_item_type.yaml` names it.

## Style

- Prose fields are ASCII, in short, plain sentences in the present
  tense. `reg_writing_style_rule.yaml` holds the rules.
- Python follows the house style of the existing modules: a data item
  in the module docstring, a 79-column `# ---` line above each
  function, aligned `=`, `.format()` rather than f-strings, whole-module
  imports, and names prefixed by type (`list_x`, `map_x`, `path_x`).
- Logic programs follow the house style of `check.lp`: a separator and
  a comment above each relation, a `% decl` line that names its
  columns, variables named for the columns they fill (capitalised, as
  clingo requires), and one body atom per line.
- Where a recognised standard covers the ground (ISO 1087, ISO/IEC
  25010, ISO/IEC/IEEE 42010), follow its structure and terms, and cite
  it.

## Keep it small

The previous iteration grew faster than it could be reviewed. Add a
type, relation, field or command only when a real instance needs it,
and keep each change small enough to read in one sitting.
