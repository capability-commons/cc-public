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
  `cat .git/worktrees/*/locked` lists each worktree with its claimant
  and the area it changes. If another worktree claims files you need,
  agree it with the claimant, or ask the maintainer, WTP, first.
- Start a topic from the main checkout. TOPIC is a short name for the
  work, in lower case with hyphens:

  ```bash
  git worktree add -b TOPIC ../cc-public-TOPIC dev
  echo "gitdir: ../cc-public/.git/worktrees/cc-public-TOPIC" > ../cc-public-TOPIC/.git
  echo "CLAIMANT: AREA" > .git/worktrees/cc-public-TOPIC/locked
  ```

  The second line makes the link from the worktree relative. Git
  writes an absolute path, and the folder has a different path on
  each machine and in each remote session, so an absolute link
  breaks. The third line locks the worktree, so git never prunes it,
  and records who claims it and what it changes. Do not run
  `git worktree repair` or `git worktree move`: both write absolute
  paths again.
- Work, check and commit in your worktree. The first `pixi run` there
  installs its environment. Where pixi cannot run, use the environment
  of the main checkout with `src` first on the path:
  `PYTHONPATH=src ../cc-public/.pixi/envs/default/bin/python -B -m cctool.cli.command check`.
- Land the branch only when its work is agreed. In the worktree, run
  `git rebase dev`, then `cctool history check dev..TOPIC --gate`. It
  checks each rebased commit, and checks, lints and tests the content
  of the newest with every test but those marked slow. `pixi run gate`
  does not do this: it gates only what is staged, and after a rebase
  nothing is. Then, in the main checkout, run
  `git merge --ff-only TOPIC`. `dev` only moves forward, so its
  history stays linear. If the merge refuses because `dev` has moved,
  rebase again.
- To move commits between machines, such as from a remote session to
  the machine that holds the worktree, use `git bundle`:

  ```bash
  cctool repo bundle TOPIC                    # where the commits are
  cctool repo land ../TOPIC.bundle            # on dev, where they go
  ```

  `cctool repo land` replays the commits onto `dev`, signs each, runs
  `cctool history check` on them and only then moves `dev` forward.
  Every commit pushed must be signed by a team member's key, which a
  remote session does not hold, so its commits are signed when they
  land. If a session committed under its own name, `--reset-author`
  on `cctool repo land` or `cctool repo sign` makes whoever runs it
  the author too. `cctool repo sign` signs the commits not yet pushed, and
  `cctool repo push` pushes once they are. Never use
  `git format-patch` and `git am`: `am` ends a commit message at its
  first `---` line, which opens the commit item, so every copied
  commit loses its item.
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
- Every commit is authored by William Payne <wtpayne@gmail.com>, the
  person responsible for its being correct, whoever drafted it. Set
  `git config user.name "William Payne"` and
  `git config user.email wtpayne@gmail.com` in a new clone or
  session; an agent says it helped in a `Co-Authored-By` trailer.
  The commit-msg hook refuses an author who is not the `git_author`
  of an entry in reg_team_member, and `cctool history check` reports
  one.
- The pre-commit hook runs `cctool gate`, which checks, lints and
  tests the staged content. The tests leave out those marked slow,
  prepush and fuzz; a commit of data with no code runs only the tests
  marked reads_data, and a commit of decisions alone runs none. Never bypass it with
  `--no-verify`. If it fails, fix the cause, or report it.
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
  `remove`, `rename`, `move` and `batch` to editing YAML by hand. They mint
  guids, fill in rights, keep the layout, and refuse an edit that adds
  a failure. An edit runs every check `cctool check` runs but one,
  `consumed_release_disagreement`, whose rows follow from which releases
  are installed. Use `--dry-run` to see an edit first.
- Give a new python module, logic program file or script its item with
  `cctool header FILEPATH`. The id of a module follows from its path. A
  class or function gets an item only when something must point at
  it, with `cctool header FILEPATH::NAME`.
- Never write a guid by hand. A guid is the prefix of the type and 32
  hex digits, minted once and never changed.
- A new type's prefix is three letters, one whole word of its
  preferred term, or the first three letters of two or three of its
  words in a row (relcon for relation constraint), and differs by more than one letter from every other
  prefix unless both types share a `prefix_family`. The checks
  prefix_form and prefix_near enforce it.
- A new concept must be named by some other item, so make the concept
  and the item that names it together, with `cctool batch`.
- After any edit by hand, run `cctool format`, then `cctool check`.
- Rename an id with `cctool rename OLD NEW`. It changes every YAML
  document that names the id, moves the file of a standalone item, and
  keeps the old id in the `alias` list of a register entry. It lists
  any file, such as a test, that still names the old id outside a YAML
  document; change those by hand.
- Use the preferred term of a concept in `_data/register/reg_concept.yaml`
  in names and in prose. Never use a term it lists as deprecated. A term
  is held to its concept's sense where it is used as a term: in an id, a
  requirement slot, a title or a link. Elsewhere an everyday word, such
  as keep or refuse, keeps its everyday senses.
- Two fields are strict: the brief of a concept (its definition) and the
  text slots of a requirement (condition, object, qualifier). There every
  registered term is a link (check `unlinked_term`); a word not meant as
  the term is reworded. A concept's brief may link any concept, with no
  edge, as a concept is defined in the terms of the others. Elsewhere,
  `term_to_link` advises where an item writes a term of a concept it
  declares without a link; it never fails.
- A short term may stand for a longer preferred term in prose, written
  as a wiki link: `[[item]]` for an admitted term, or
  `[[concept_identifiable_data_item|item]]` (target first) where the
  item holding the prose uses two concepts with the same term. The item,
  or the register that holds it, needs an edge `relation_uses_concept`
  to each concept it links this way. Outside the strict fields, brackets
  are optional but encouraged; quoted text is not read. Never declare the sense on a type.

## Failures and errors

Every failure and error that cctool reports says what is wrong, in
terms of the items and files it names, and what to do about it. An
agent can act on it without reading the rule behind it.

- Each shown predicate of a logic program holds an item in the
  comment header above its `% decl`, with the prefix `lpp`. Its
  `did` field is a sentence that names the columns of a row in braces,
  such as `{holder} names {id} in its {field} field, and no item has
  that id or guid.` Its `fix` field is the usual remedy, and says what
  not to do where a wrong remedy is tempting. A test fails any shown
  predicate that lacks either. `cctool header PATH::NAME` makes the
  item from the comment above the declaration; give `did` and `fix`
  as fields. A check written in python gives the same two in
  `cctool.check.check`.
- cctool prints each failure as its file and line, where it has them,
  the name of the check, and the did sentence, then the fix once for
  each check. The name of the check is the stable code that tests and
  scripts match on; the sentences may change.
- An error, exit status 2, says what is wrong with what was given and,
  where that is not plain, what to give instead or which command does
  the job.
- Fix the cause a failure names. Do not delete what a failure points
  at only to quiet the check.

## Skills

Procedures, and the traps in them, are skills in `.agents/skills/`,
in the Agent Skills format. Codex reads them there, and Claude Code
reads them through `.claude/skills`, a link to the same directory.
`editing-data-items` covers adding and changing items with cctool.
`reviewing-the-repository` covers the scheduled reviews and
retrospectives, and how to record what they find.

## Finding things out

- `cctool query predicates` lists every predicate and its columns.
- `cctool query text "WORDS"` finds items by the words of their prose,
  best first, and names the decision of each, how it was settled, and
  the concerns it speaks for. With `--decision` it gives one row for each
  decision. Use it before you argue or change something, to find the
  arguments and rulings already made on the point. A query
  that names a concept also matches its other preferred and admitted
  terms; `--exact` turns that off. `cctool query logic --text
  "WORDS"` gives the same hits to rules as `text_hit(id, field, rank)`.
- `cctool query sql "SELECT ..."` for joins and counts, and
  `cctool query logic '...'` for anything recursive, such as reach
  through edges. `cctool query sparql '...'` sees the items as RDF
  triples, and `cctool query jq '...'` sees the YAML documents as written.
- Read the schema of a type before writing an item of it: the type
  entry in `reg_data_item_type.yaml` names it.
- `cctool impact REV` lists the items a commit adds, removes, renames
  or changes, and the untouched items linked to them. `--staged` does
  the same for the commit you are about to make. Read it before you
  review a change, to see what else the change bears on.

## Style

- Prose fields are ASCII, in short, plain sentences in the present
  tense. `reg_writing_style_rule.yaml` holds the rules.
- Python follows the house style of the existing modules: a data item
  in the module docstring, a 79-column `# ---` line above each
  function, aligned `=`, `.format()` rather than f-strings, whole-module
  imports, and names prefixed by type (`list_NAME`, `map_NAME`, `path_NAME`).
- Logic programs follow the house style of `check.lp`: a separator and
  a comment above each predicate, a `% decl` line that names its
  columns, variables named for the columns they fill (capitalized, as
  clingo requires), and one body atom per line.
- Where a recognized standard covers the ground (ISO 1087, ISO/IEC
  25010, ISO/IEC/IEEE 42010), follow its structure and terms, and cite
  it.

## Improving as you go

- Design rules are in `_data/register/reg_design_rule.yaml`. Follow
  them as you follow the writing style rules.
- Note what could be better as you work: an awkward name, a check you
  had to word around, a command that could be simpler. Fix it if it is
  small and inside the scope of your task. Otherwise say so in your
  report, so that it can become a decision. Do not widen your task to
  fix it.
- Do not word around a check, quote a word to dodge it, or add an
  exception to a rule without saying so. Each of these is a tension,
  and it is reported, not hidden.

## Keep it small

The previous iteration grew faster than it could be reviewed. Add a
type, relation, field or command only when a real instance needs it,
and keep each change small enough to read in one sitting.
