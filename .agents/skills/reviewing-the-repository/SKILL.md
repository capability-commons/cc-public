---
name: reviewing-the-repository
description: >
  How to run the scheduled reviews of cc-public (the daily shallow
  review and the weekly in-depth review) and a retrospective, and how
  to record what they find. Read this WHENEVER you are asked to review
  the repository, to run the daily or weekly review, or to hold a
  retrospective.
---

# Reviewing the repository

Continual improvement in cc-public is a loop: something is sensed, what
it finds is a finding, and each finding gets a response that fits its
kind. The reviews are the main sensing mechanism after the checks. They
are run by agents, on a schedule, and both are mandatory. A missed run
is itself a finding.

The terms are in `_data/register/reg_concept.yaml`: finding,
nonconformity, tension, opportunity for improvement, lesson learned,
correction, corrective action. Use them in their registered senses. A
finding is a tension only if something is bent to fit an earlier
choice; do not call everything a tension.

## Kinds of finding, and the usual response

| kind | usual response |
|---|---|
| nonconformity: a requirement, design rule or check not met | a correction; a corrective action if it recurs |
| tension: nothing broken, something bent to fit an earlier choice | a correction now if the blast radius is small, else a decision: fix now or accept |
| opportunity for improvement | fix it if small and in scope, else propose it |
| lesson learned | an annotation about what it concerns; perhaps a design rule or a change to how we work |

## Before a scheduled review

- Read the previous report, and the newest `notes-for-*.md` in the
  reviews folder if there is one. The notes carry lessons and focus
  points from the maintainer, and take precedence over this skill
  where they are more specific.
- In a cloud container there is no pixi. Install with `pip install -e .`
  (again after each checkout, since the package changes) and run
  each command as in `PYTHONPATH=src python3 -m cctool.cli.command check`.
  The commit hooks call pixi to run the gate and cctool, so put a
  stand-in script named pixi on PATH that drops its own options and
  runs the same command through python. Set `core.hooksPath` to
  `.githooks` and commit as the maintainer.
- Start `cctool history check RANGE` in the background first: it
  takes several seconds a commit.

## The daily review (shallow)

1. Read the commits since the last daily review: `git log` and
   `cctool impact REV` for each. The previous report names its range;
   start after its last commit.
2. Run `cctool check` and read the advice as well as the failures.
3. Run `cctool friction` and compare its counts with the last report.
   It lists terms that two concepts share, rules that need
   exceptions, decisions with no ruling, and the count of each kind of
   advice.
4. Look for the friction it cannot see yet in the day's work: text
   reworded to get past a check, words put in double quotes to dodge
   a check, links written only to settle which concept is meant,
   large renames.
5. Fact-check the arguments that the day's work may have made stale.
   Facts shift as the tree changes, so this runs every day, not only
   when an argument is drafted. For each file the commits changed,
   find the annotations that cite it (`cctool query text`, or a grep
   of `_data/decision` for its path), and check each line, count,
   commit and quote they give against the tree. Fix what no longer
   holds in a commit titled `Fix the arguments on TOPIC so that their
   facts hold`, on the branch of the review. Where the design changed,
   so that what an argument argued no longer holds, add an annotation
   that challenges it rather than rewording it. Report how many
   arguments were checked and how many fixed.
6. Check each ruling recorded in the range against the maintainer's
   words: it names the maker by initials, gives the date only (no time
   of day), and claims no more than they said. Note any ruling
   corrected after it was recorded.
7. Use the instruments: `cctool timing --runs 20` for the gate (its
   log is per git directory, so say where it was read), and
   `cctool release check` against the newest release item if there is
   one. Report any check, command or interface control document added
   in the range, and whether it passes.
8. List the work waiting to land: each git bundle in the shared notes
   folder whose head is not on `dev` (`git bundle list-heads`, then
   `git merge-base --is-ancestor`), and how far behind `dev` it is. A
   finished branch left unlanded drifts.
9. Write the report (below). State its range and the counts it
   compares at the top. Keep it short.

## The weekly review (in depth)

1. Everything in the daily review, over the week.
2. Read the repository area by area: registers and concepts, schemas,
   decisions, code, logic programs, skills and AGENTS.md. Split the
   areas between agents if the work is large, and merge their findings.
3. Judge the design rules. List them with
   `cctool query jq '.[] | select(.file=="_data/register/reg_design_rule.yaml") | .document.entries[] | {id: .id_self, brief}'`
   and, for each, report where the repository breaks the parts of it
   that no check holds. Do the same for the writing style rules in
   `reg_writing_style_rule.yaml`.
4. Fact-check a wider slice of the arguments than the daily review
   reaches, such as those of the decisions still open, and of one
   area in turn, so that every argument is checked again from time
   to time.
5. Count what trends: advice by kind, exception entries, the time the
   gate takes, and the arguments fixed by fact-checks.
6. Write the report (below).

## A retrospective

Held when the maintainer asks, usually after an episode of work such as
a naming round. Read the commits and the threads of the episode, and
ask: what went well, what cost more than it should have, and what would
we do differently. Each answer that will matter again is a lesson
learned.

## Recording findings

Not every finding goes into the graph. Recording everything grows the
graph faster than it can be reviewed.

- **Fixed at once:** no record beyond its commit.
- **Needs a choice** (fix now or accept, which rule to adopt): a
  decision in `_data/decision`, with options and, once the maintainer
  rules, a ruling. See `editing-data-items`.
- **A lesson learned:** an annotation about what it concerns.
- **A new or changed design rule:** an entry in
  `_data/register/reg_design_rule.yaml`, edited in place; git holds its
  history. Only the maintainer adopts a design rule.

## The report

One file per review in a folder named reviews in the project's shared
notes folder, named `YYYY-MM-DD-daily.md`, `YYYY-MM-DD-weekly.md` or
`YYYY-MM-DD-retrospective.md`. It lists each finding with its kind,
where it is, the evidence, and the proposed response, and ends with
what needs the maintainer: decisions to rule on and rules to adopt.
Clear fixes are made in a branch of their own, as any other change.
