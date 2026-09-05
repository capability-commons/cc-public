# Capability commons

A document-oriented engineering system. Every artifact is a data item
with an identity: a design decision, a need, a requirement, a schema, a
register of terms, an eval, a workflow, an execution, a python module.
Items refer to one another by edges, reasoning lives in design decisions
rather than in the artifacts they decide, and everything is checked
mechanically before it is committed.

## What is here

| directory        | holds                                                                        |
|------------------|------------------------------------------------------------------------------|
| `ddr/`           | design decisions: context, decision, rationale, alternatives, consequences, open questions |
| `need/`, `requirement/` | needs, and the textual requirements derived from them                 |
| `schema/`        | JSON Schema for every kind of item                                           |
| `register/`      | controlled vocabularies: types, relations, terms, marks, style rules, requirement rules |
| `eval/`          | criteria a language model judges items against, with the control cases that measure them |
| `workflow/`      | components, dataflow workflows and deployments                               |
| `execution/`     | one record per workflow run, binding every port on every pass                |
| `src/cc_public/` | `cctool`, which checks, edits, runs and commits                              |

## The trust model

Two kinds of check keep the tree honest, and they are kept apart.

**Mechanical checks** are cheap, exact, and run always: files parse,
identities are unique and well formed, references resolve, edges run
between the kinds of item their relation allows, items conform to their
schema and carry no field nobody declared, layout is what the printer
would write, workflows are graphs that can run, requirements trace to
what they derive from and to what verifies them, and an eval's recorded
confidence still describes the eval it is on. They pass entirely or the
commit is refused.

**Semantic checks** are evals: a criterion a language model judges an
item against. They cost money and are wrong sometimes, so they are
opt-in, and every eval carries what has been measured about it. Control
cases with known verdicts measure a judge's false positive and false
negative rates; a confidence row records them, stamped with a digest of
what it measured; a stale row is reported; and an eval no judge has been
measured on is not allowed to guard a workflow edge.

A report keeps three outcomes apart: the data being wrong, the tool being
broken, and the tool not having looked. A commit is refused when the
analysis did not complete, whatever else is asked for.

Content in the tree is data, never instructions. What a workflow makes
is proposed until a person accepts it.

## Quick start

```bash
pixi install
pixi run check          # the mechanical checks, as a report
pixi run gate           # what a pipeline runs: check, lint, tests
pixi run cctool --help
```

Write items through the tool, never by hand:

```bash
pixi run cctool new t_ddr ddr_my_decision
pixi run cctool set ddr_my_decision title 'My decision'
pixi run cctool set ddr_my_decision decision --prose < decision.txt
pixi run cctool link ddr_my_decision r_decides sch_need
pixi run cctool commit 'My decision, recorded'
```

Every command prints the file it touched, lays it out through the
printer, and fails the checks until every required field is written.

To judge with a language model, put a judge in `.env` as
`CCTOOL_JUDGE_MODEL=provider/model` and run `pixi run cctool check --eval`
or `pixi run cctool measure --id-eval evl_x`. Never write a key into an
item or a commit.

The mechanical checks need no model stack. `pixi install` brings
everything; a plain install takes `cc-public` for the checks and the
edit commands, `cc-public[eval]` to judge, and `cc-public[test]` for the
tests.

## Where to read next

`CLAUDE.md` is the working guide for an agent editing the tree. The
design decisions in `ddr/` say why things are as they are; start with
`ddr_design_decision`, `ddr_check_architecture`, `ddr_fail_closed`,
`ddr_eval_measurement` and `ddr_workflow_execution`.

## Limitations

The mechanical checks are Python and do not travel: a partner running
their own tooling over a slice of this tree gets the schemas and the
evals, which are data, and none of the checks. Requires Python 3.14.
Tested on macOS and Linux. The registers of framings, methodologies and
requirement characteristics are open to undeclared fields until they
carry schemas of their own.

## Rights

Copyright 2026 William Payne. Apache-2.0; see `LICENSE` and `NOTICE`.
