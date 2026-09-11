# cc-public

Capability commons: a document-oriented engineering system. Everything
is a data item with an identity; reasoning lives in design decisions,
not in artifacts. See `ddr/` before changing anything the design
decisions decide.

## Tools

All of these are `pixi run cctool …`; `pixi run check` and `pixi run format`
are shorthands. Every command has `--help`; the writing commands take
`--root DIR` (repeatable), `check` takes `--path`. The commands live in
`src/cc_public/cli/` by kind, and are listed here the same way.

Checking

- `check` — the mechanical checks; `check --help` lists them in the order
  they run, from the driver, so that list is never stale. Must be clean.
  A finding names its file, and for a class or function item the
  definition beneath it: `run.py::State::generator_for`. `--fail-fast`,
  `--closed-world`, `--format json`, `--out FILE`.
- `check --eval` — LLM evals. Needs `CCTOOL_JUDGE_MODEL` in `.env` (never
  paste a key into chat). `--confirm N` re-judges an adverse verdict N times,
  uncached (default 5); `--id-eval`/`--id-item`/`--id-type`/`--id-schema`
  narrow (anchored regex); `--changed-since REF` judges only the items in
  the files changed since a commit, a pair where either end changed, and is
  what to run after writing; `--judge-model null` dry-runs.
- `format [--check]` — lays every document out to the convention.

Judging

- `measure --id-eval X [--samples N] [--record]` — judges X's control cases
  fresh and reports false-positive / false-negative / unanimity per origin;
  `--record` writes them onto the eval as `confidence`, stamped with a digest
  of criterion, examples, scope and cases. Change any of those and the row
  is stale: the confidence check says so, and a guard on that eval is
  refused to that judge until it is measured again (`ddr_eval_admission`).
  N is odd. `--stale` instead of `--id-eval` measures every eval whose
  confidence for the judge is absent or stale.
- `case --id-eval X --item Y --verdict met|unmet --note "…"` — turns a finding
  into a control case (met = suppressed, unmet = confirmed); for an eval over
  pairs give `--item` twice, source then target. A later sweep
  matching the same words reports a met case as a note, not a finding.
  `--origin written` holds a hand-written item to a verdict instead; a
  mutated case is made through the API with its subject text set.

Assurance

- `questions [--open]` — what the design decisions leave open, and what
  answered it.
- `trace [--requirement X] [--source Y] [--gaps] [--criticality] [--closed-world] [--format json]`
  — what each requirement derives from, what implements it
  (`r_is_implemented_by`, to a package, module, class or function), what
  verifies it (`r_verifies`) and what it lacks; `--source` shows what a
  source item implements and verifies; `--changed-since REF` shows what
  every item in the files changed since a commit may affect. Reads the
  same projection (`cc_public.trace`) as the trace check. Proposed gaps are
  advisory; accepted ones critical (`ddr_implementation_trace`). `--criticality`
  shows the effective level of every item a requirement reaches: only a
  requirement declares one, and a source or data item takes the greatest
  reaching it along the relations that declare responsibility. What a level
  requires is `register/reg_criticality.yaml`, read by the trace check where a
  verdict is shared and where a coverage analysis is absent (`ddr_criticality`).
- `changed --since REF [--format json]` — what changed and what rests on it:
  every standalone item in the files changed since a commit, by kind, with
  the decisions that decide it, then every item elsewhere that reaches one
  of them by a chain of edges whose relation declares `dependency` (a
  requirement through what implements it, a case through its method, an
  annotation through what it is about). Where a review starts.
- `glossary [WORD] [--gaps] [--senses] [--min N] [--format json]` — read the
  term registers. WORD returns every entry that claims it, since a word may
  name several concepts, and every entry that rejects it; with no WORD, every
  term. `--senses` names the words more than one entry claims and the readable
  ids that number a sense rather than distinguishing it in words. `--gaps`
  counts the words and pairs of words that the prose of N items or more uses
  and no glossary holds, and the terms no record decides. A gap is a candidate
  for a person, never a finding (`ddr_glossary`, `ddr_term_concept_identity`).
- `show ITEM [--format json]` — one item: where it is, title and brief,
  every edge it holds and every edge pointing at it. Use it before
  grepping for a guid.
- `attest --requirement X --outcome passed|failed --by NAME [--note …]` —
  records a person's or a tool's finding for a requirement verified by
  inspection, demonstration or analysis, into `evidence/evd_attestation`.
  Test evidence is written by `test/conftest.py` at the end of every pytest
  session into `evidence/evd_pytest`, one row per test-function item and
  requirement it verifies, stamped with a digest of the requirement, its
  implementation and the test; the evidence check reports an accepted
  requirement whose evidence is absent, not a pass, or stale
  (`ddr_verification_evidence`). A run that observes something new
  rewrites that one file; a run that observes what the last one did
  leaves it alone.

Querying

- `walk ITEM [--depth N] [--relation R]… [--direction out|in|both] [--format text|json|dot|mermaid]`
  — the neighbourhood of an item, breadth first, each item once with the
  edge that reached it. `path A B` — a shortest path or its absence.
  `orphans` — items nothing points at or holds, and relations no edge uses.
  `query NAME | --sql …` — a named query (an item of type `t_query` in
  `query/`, holding SQL over the tables `item`, `edge`, `containment`) or
  SQL typed here, over facts derived from the tree on every use
  (`ddr_graph_query`). Keep a question asked twice as a `qry_` item.

Reviewing

A review by a model other than the one that did the work recurs, and its
findings are items. Read `changed --since REF` for the scope, then `check`,
`trace --gaps`, `questions --open`, `glossary --senses`, `orphans`,
`query qry_undecided` and `query qry_decides_nothing` for what the tree can
say mechanically, and `check --eval --changed-since REF` for what a judge
can. Record each finding as one annotation, one assertion each: `new
t_annotation ann_x --set title=… --set brief=… --link r_is_about SUBJECT
--link r_is_asserted_by mdl_…`, with `description` holding the evidence and
the consequence; the model asserting it is an entry of `register/reg_model.yaml`
(`ddr_model_register`), and a person's annotation names none. Answer one with
another: `r_challenges` or `r_supports`, never by editing or deleting it. What
nothing has answered is `query qry_annotation_unanswered`; what an annotation
is about, and what answers it, is `show ann_x`. The reviewer fixes nothing in
what it reviews (`ddr_annotation`).

Rendering

- `render OBSERVATION [--findings report.json] [--out DIR] [--format pdf|html|both]`
  — the dossier rooted at an observation as two documents, a briefing
  and a technical appendix, drawn from the graph: needs, concepts,
  promoted requirements, runs, the findings in a report from `check --eval
  --format json --out FILE`, trace gaps, the derivations drawn by Graphviz.
  `--request TEXT` prints what the reader is asked to do on the brief.
  Writes into DIR, never into the tree (`ddr_dossier`). The projection is
  `cc_public.render.dossier.dossier(tree, id, report)`, plain data; the
  templates are beside `cc_public.render.html`.

Running and committing

- `run WORKFLOW --deployment DEP --bind node.input.port=ITEM …` — one run
  of a dataflow workflow. `--dry-run` shows the order and writes nothing.
  Needs a clean tree. Makes items with `new`, fills fields with `set`,
  links what a port `decides:` to what it makes, checks after every node,
  restores on a critical finding, writes an execution record to
  `execution/`, commits if the deployment says so. A component in code
  (`r_is_implemented_by` to a function item, no prompt on any port) is
  called once per node as `f(tree, ledger, {port: id})` and returns an id
  per output port; the tool's own live in `cc_public.workflow.component`
  (`ddr_code_component`). `wf_accept_requirement` with `dep_accept_local`
  accepts a requirement that way. Every component declares its `performer`:
  `function`, `model` or `agent` (`ddr_performer`). A node performed by an
  agent parks the run: the execution record holds the run's state and a
  brief, `run` prints the brief and returns with outcome `waiting`.
  `run` and `resume` take `--root` more than once: the first is the
  repository run in, where items are made and the record is written; the
  rest are the trees it consumes, read only.
- `test CASE --under-test ITEM [--record] [--evidence] [--report] [--format json]`
  — runs one test case against one item. The case names its method by
  `r_uses_test_method`, the method names an installed adapter by identity, and the
  adapter derives what to run from that identity, so no data item carries a command
  or a path. The run is made in a process whose path holds the tree's own `src`, so
  what runs is the code that tree holds. Prints the execution outcome and the
  conformance result, which are two things: an execution that did not complete
  carries no result at all, and a failed one is shown as the report it makes.
  Writes nothing unless asked: `--record` keeps the execution, `--evidence` brings
  the current evidence up to what was observed, and `--report` keeps the reports and
  the execution they name (`ddr_test_execution`, `ddr_nonconformity_report`,
  `ddr_evidence_dependency_closure`).
- `resume EXECUTION` — continues a waiting run once the tree holds what
  the brief asked for. An agent output is read from the graph, never from
  a report: it `revises` an input, or is `found` from one by a relation in
  a direction. A resume that finds nothing stops and leaves the record
  waiting. `wf_implement_requirement` with `dep_implement_local` is the
  first: implement (agent), verify (runs the requirement's tests under
  pytest and records `evd_pytest`; a failure stops and restores), then
  accept. When you are the performer, do the brief through the tool,
  commit, then resume.
- `commit TITLE [--brief …] [--description …] [--link REL ITEM]` — runs the
  checks and the lint, refuses on a critical or lint finding unless
  `--checkpoint` and on an incomplete analysis always, writes a commit
  record into the message. `log [-n N]` reads them back.

Pixi tasks

One command per concern. `gate` is the judgement and is the only aggregate;
everything else is a loop or a diagnostic.

- `pixi run gate` — what a pipeline runs, and the only thing that decides.
  Its `depends-on` is where the order lives: lint, then type, then test, then
  the closed-world check, so the tests refresh the evidence the check reads.
  Do not name that order anywhere else. About thirteen minutes.
- `pixi run quick` — the loop, not the judgement: lint, then the suite with
  the slow tests left out. About six minutes against the gate's thirteen. It
  runs no coverage and no closed-world check, so a green `quick` decides
  nothing. CI never runs it.
- `pixi run test-changed` — the narrowest loop: only the tests a change can
  reach, read from a map `test-map` measures. Every uncertainty runs
  everything and says which rule decided that, so a change to anything but a
  module or a test runs the whole suite. A green `test-changed` decides
  nothing and CI never runs it (`ddr_test_selection`).
- `pixi run test-map` — rebuilds that map: the whole suite, one process per
  test module, about forty minutes. **Writes**: `.test_map.json`, which is
  not committed. Do it after a change that moves what tests reach, and read
  the lines it prints about modules it could not account for.
- `pixi run lint` — ruff over `src` and `test` in the house rule set, then
  `lint-imports` holding the seven tiers of `ddr_layered_architecture`: a
  package imports downward only, and an underscore name is its module's
  (tests excepted).
- `pixi run type` — mypy over the typed island named by `files` in
  `[tool.mypy]`, at full strictness. It says nothing about the other 89
  modules. `mypy -p cc_public` reads the whole package when you want that
  number; it was 63 errors in 31 of 92 files on 2026-09-09.
- `pixi run test` — pytest over `test/`, in parallel, branch-aware coverage
  against the floor. **Writes**: the evidence item, `coverage.xml` and
  `junit.xml`.
- `pixi run test-durations` — the same, plus the twenty-five slowest.
- `pixi run coverage` / `code-coverage-branch` — what is uncovered, by
  statement or by branch and statement together.
- `pixi run code-coverage-diff` — changed-line coverage of what a change
  touched, against `origin/main` by default. Append another
  `--compare-branch` to override it; the later flag wins.
- `pixi run check` / `check-closed-world` — the mechanical checks, reporting
  or failing on a nonconformity with the world asserted closed.
- `pixi run format` / `format-items` — lays every document out to the
  convention. **Writes** every file it touches.
- `pixi run package-check` — builds both distributions, checks their
  metadata, installs the wheel into an environment of its own and runs the
  tool that comes out of it. Not in the gate: it builds and reaches the
  network. Blocking in CI.
- `pixi run security-audit` — known vulnerabilities in the python
  distributions. Reports; blocks nothing.
- `pixi run -e demo ui` — the demonstration's temporary Streamlit interface,
  `../demo/ui/app.py`, in its own `demo` environment: a reader over the tree
  and a control panel that shells `cctool` one job at a time. It edits no
  item. Disposable; the projection it reads is not.

Which commands write: `test` and anything that runs pytest rewrites
`evidence/evd_pytest.yaml` when it observes something new, and drops
`coverage.xml` and `junit.xml`; `format` rewrites documents; `package-check`
writes `dist/`. Everything else reads.

Thresholds, and why they are where they are

| | value | why |
|---|---|---|
| Coverage floor | 87, branch-aware | the measured 87.12 rounded down. **0.12 of a point of headroom**: about thirteen statements or branch exits |
| Changed-line coverage | 90, reporting only | conservative, with no observation behind it yet |
| Test timeout | 600 s | a hang guard, not a budget; the slowest test measured 175 s |
| CI job timeout | 45 min | roughly three times the measured local gate |
| Typed island | 3 modules | every strictness flag applies to them and to nothing else |

Ratchet, never relax. Do not lower a threshold to let an ordinary change
through; make the change carry its own tests. Raise a coverage floor when
sustained coverage leaves a point of headroom. Lower a complexity maximum
only after the real maximum falls. Widen the typed island a coherent package
at a time, and only while the current one is stable.

Read at each release, because each of these goes stale silently: the pinned
action commits and what Dependabot has proposed, the dependency advisories
and their triage, the slowest tests, the coverage floors, the confidence
measured on each eval and its control cases, the scope of the typed island,
and every suppression, objective claim and temporary exception.

What the gate believes, and what it cannot see, is `register/reg_gate_tool.yaml`,
one entry per tool whose failure stops the work. `qry_gate_tool_control` says
which of them have anything demonstrating they can fail. A tool run for
information is not entered there.

## Writing items — use the tool, never hand-edit

- `new TYPE ID [--set PATH=VALUE]… [--prose PATH=TEXT]… [--link REL TARGET]…`
  — mints the identity, writes every required field empty (it fails the
  checks until written), puts it where its type lives (`--out` otherwise).
  Give the fields and edges in the same command and it never exists half
  made; prefer that. A python package or module too: `pym_cc_public.demo.thing`
  becomes `demo/thing.py` beside its parent package, docstring only. A
  class or function too: `new t_python_function pyf_cc_public.path.select`
  turns the docstring of `select` in `path.py` into a document, its prose
  becoming the brief; the id is the module's id then the definition names,
  lower case (`pyf_cc_public.edit.tree.tree.resolve` is `Tree.resolve`).
  Make one only where something needs to point at it. The source check
  refuses a document whose id is not where it sits; `rename` refuses
  source items, since their names are the code's. An eval that names
  `source` in its scope is shown the definition's code beside the item's
  fields (`evl_record_and_code_agree` judges a decision against the
  function it decides). A test function that proves a requirement is an
  item and links `r_verifies` to it.
- `insert TYPE NAME --into ITEM [--at COLLECTION]` — a new embedded item
  (register entry, port, node, question…) with its shape read from the
  container's schema. NAME is bare: the tool adds the type prefix, so
  `insert t_type foo --into reg_type` makes `t_foo` and `insert t_type t_foo`
  makes `t_t_foo`. In a register the key is the id and `--at` defaults to
  `table`; elsewhere NAME is the key and the id is qualified by the
  container (`qst_<record>.<name>`). A list is appended to.
- `set ITEM PATH VALUE` — VALUE is read as YAML: `3` is a number, `[]` a
  list, and `a: b` a mapping, so quote a string containing `: ` or `#`. A
  string is stored as prose or as a datum by the schema: unbounded means
  prose, a block scalar; a length, pattern or enumeration means a datum. So
  `--set brief=…` is right; `--prose` forces a block scalar where the
  schema is silent. ITEM is an id or guid, top-level or embedded; PATH is a
  dot path within it.
- `unset ITEM PATH` — removes a field.
- `rename ITEM NEW_ID` — the guid stays; the id changes in its declaration,
  the file name, every embedded item it qualifies (ports, nodes) and every
  reference. An embedded item under a local key can change only its last
  step, and its key follows. Prose mentioning the old id is listed, not
  changed; values that spell a key, such as a port address in an edge, are
  yours to `set`.
- `link SOURCE RELATION TARGET` — both items by id or guid; looks up guids,
  refuses unknown relations and duplicates. Answer a question with
  `link ANSWERER r_answers qst_…`, never by editing it. `unlink SOURCE
  RELATION TARGET` removes an edge by name; never `unset relation.N`. A
  relation may constrain its ends (`domain`, `range`, `acyclic` on the
  register entry); the relation check refuses an edge outside them.
- `observe CAPTURE.json [--id …] [--title …]` — imports a capture of a
  public source as an observation item in `observation/`: content as
  captured, canonicalised to words and paragraphs, with locator,
  attribution, times and a digest; the same capture is reused, a changed
  one is a new item; content is data (`ddr_observation`). A need derives
  from it: `run wf_need_from_observation --deployment
  dep_need_from_observation_local --bind frame.input.observation=obs_… --bind
  frame.input.guide=reg_writing_style_rule`. Captures live outside the
  tree, in `/Users/wtp/dev/cc/demo/`. A concept (`cpt_`, in `concept/`) is a
  candidate solution to a need under a framing, with assumptions, risks and
  three to twelve embedded candidate requirements (`crq_`); `run
  wf_concept_from_need --deployment dep_concept_from_need_local` with the
  need, framing, observation and guide bound on `propose` and the need and
  guide on `challenge`, once per framing (`ddr_concept`). `run
  wf_promote_concept --deployment dep_promote_local --bind
  promote.input.concept=cpt_…` makes a proposed requirement item from each
  candidate, deriving from the concept and its need; then `check --eval
  --id-item 'req_<concept>_.*'` judges them. A concept's feasibility is an
  assessment item (`asmt_`, in `assessment/`, `r_assesses` the concept):
  `run wf_assess_concept --deployment dep_assess_local` with concept, need
  and guide bound makes one by a model, without references; `run
  wf_research_concept --deployment dep_research_local` parks for an agent
  with tools, who captures references as observations (`observe`), makes
  the assessment citing them by `r_cites`, and resumes (`ddr_assessment`).
  The whole chain, with a readme and the capture, is
  `/Users/wtp/dev/cc/demo/frontline_power/`.
  An output port
  links by `link: {relation: [input ports]}` (`ddr_port_link`); a type
  entry may name its `home` directory so a workflow can make the first item
  of a type.
- `decide OUTCOME --on ITEM… --by ACTOR --role ROLE --authority TEXT --brief TEXT
  [--condition …] [--expiry YYYY-MM-DD]` — records a decision (`dcn_`, in
  `decision/`): `waive` admits a concept whose challenge did not conclude to
  promotion, `select` chooses a concept, `accept` a requirement, `lead` the
  assessment a report opens with. Each subject is stamped with the digest of
  its whole document; the decision check reports a subject changed since or an
  expiry passed (`ddr_decision`). Promotion is an admission: it needs the
  concept's challenge run to have `completed`, or a waiver that still holds,
  and an evidential candidate needs a `quote` found in an observation behind
  the concept's need; the requirement carries `r_is_admitted_by` and `r_cites`.
- `gather CONCEPT [--id …] [--entity …]` — makes a requirement set (`rqs_`, in
  `requirement_set/`) including by `r_includes` every requirement derived from
  the concept, or adds to one that exists. A set is shown to a judge or a
  model with its members projected under `member` as composed statements.
  `run wf_review_set --deployment dep_review_set_local --bind
  review.input.set=rqs_… --bind review.input.guide=reg_writing_style_rule`
  writes its `coverage` table, one entry per scenario class; the requirement
  check reports a member on another entity, a duplicated obligation, an
  unreviewed set and each uncovered class; `evl_set_consistent` judges
  conflict and repetition across the members (`ddr_requirement_set`).
- `sweep REPORT.json --id swp_… [--title …] [--brief …]` — makes a sweep
  (`swp_`, in `sweep/`) from a `check --eval --format json --out` report: the
  findings grouped by eval and rule, largest first, with items and sample
  messages. `run wf_propose_rule --deployment dep_propose_rule_local --bind
  propose.input.sweep=swp_… --bind propose.input.rules=reg_requirement_rule
  --bind propose.input.guide=reg_writing_style_rule` has a model propose one
  rule a check over the slots could apply, as a proposal (`rlp_`, in
  `proposal/`) deriving from the sweep; a person enters it in the register or
  rejects it. Nothing but a person writes the register (`ddr_improvement_loop`).
- `accept REQUIREMENT` — the only path to `status: accepted`: judged as
  accepted in a closed world, the trace must show no gap and the evidence
  check nothing, or it refuses saying what is lacking. Never `set … status
  accepted`.
- Dot paths: `properties.title.maxLength`, `table.t_foo`,
  `edge_back.draft_to_draft.guard`. A key never contains a dot; an address
  such as `draft.output.record` is a value.

For more than a handful of writes use the API under `pixi run python`:
`Tree('.')`, then `edit.new.new(tree, type, id, tree.defaults())`,
`edit.insert.insert(tree, type, name, container, collection)`,
`edit.field.set_field(tree, item, path, value=obj | prose=text)` (value is
a Python object, not YAML text), `edit.link.link(tree, source, rel, target)`.
Each call writes and prints through the printer, so no format step is
needed between them. Amend prose by paragraph: load, replace the collapsed
paragraph, set `prose=`; never match wrapped lines.

Every one of these prints the file it touches. Do not append text to a
file or mint a guid by hand.

## After any edit to a YAML file or a docstring document

1. `pixi run format`
2. `pixi run check`

Never hand-align. The printer decides indentation, the gutter, list form
and blank lines (`ddr_layout_convention`). A plain scalar is a datum
and is left alone however long; prose goes in a `|` block scalar and is
refilled to 70. Separate paragraphs in a block scalar with a blank line.

## Conventions that are not in the code

- Schemas are closed (`ddr_schema_closure`): a concrete schema refuses a
  field no composed schema declares, at the path it was written. Add the
  field to the schema before writing it to an item. A trait carries no
  `additionalProperties` at all; a concrete schema carries
  `unevaluatedProperties: false`. An item naming its own schema names one
  that composes its type's.
- Identity: `id_self`/`guid_self` declare; `id_<role>`/`guid_<role>`
  refer and are checked. A table key equals `id_self` only in a
  register's `table:`; ports, nodes and bindings use a short local key.
- Terminology: the standard, least-surprising name; departures are
  recorded (`ddr_terminology`). The glossary is `register/reg_term.yaml`.
  Check it before naming anything.
- A register entry's `alias` is an alternative *identifier*. Synonyms go
  in a term's `also`, rejected forms in `avoid`.
- Prose follows the writing style guide, `register/reg_writing_style_rule.yaml`:
  seven rules, each with a sentence that follows it and one that breaks
  it. Read it before writing any field.
- A requirement, and a candidate requirement in a concept, is its slots:
  `condition_kind`, `condition`, `entity`, `obligation`, `activity`, `actor`,
  `process`, `object`, `qualifier`, with a `claim` of `evidential` or `design`.
  The statement is composed from them by `cc_public.requirement` wherever it
  is shown and is never written (`ddr_requirement_slots`). The rules a
  statement is judged by are `register/reg_requirement_rule.yaml`, INCOSE's
  and SOPHIST's, each naming the document it is taken from by
  `r_is_taken_from` into `register/reg_document.yaml` (`ddr_document_register`).
  The `process` slot names a verb defined in a process word register the
  item's segment can see (`register/reg_process_word.yaml` in the core); the
  requirement check reports a verb none defines, advisory while proposed and
  critical once accepted (`ddr_process_word`).
  The statement check reads the object and qualifier: a number needs a unit
  from `register/reg_unit.yaml` or a thing it counts, a point value asks for
  its bound, an acronym needs a glossary term, a process word whose entry has
  a `kind` other than process, a light verb, or an object opening with a noun
  made from a defined verb is a question (`ddr_mechanical_form`).
- Prose in an item describes; argument goes in a design decision. Create
  one only for a genuine decision with real alternatives. The item is a
  design decision, never a "design decision record": every item is a
  record of something (`term_design_decision`).
- Commits go through `cctool commit TITLE [--brief …] [--description …]`,
  which runs the checks, refuses on a critical finding unless
  `--checkpoint`, and writes a commit record into the message. Add
  `--trailer 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`
  when you are the one committing. Do not commit unless asked; the user
  commits, and a workflow run commits at its end.

## Segments

This repository is the core (`seg_cc_public`, `ddr_segment`). A repository
declares itself with one `t_segment` item in `segment/`, governs the
directory that directory sits in, and names by `r_consumes` every segment
whose items its own may refer to. A reference may run within its segment
or into one it consumes, never the other way; the segment check refuses
the rest. A file under no segment is passed over.

The core consumes nothing and holds what travels: the tool, the schemas,
types, relations, registers and evals. A consumer holds its own items and
in time its own schemas, usable from it and from anything consuming it,
never from here. A consumer's gate names both roots and asserts the union
closed; this repository's gate names only itself, so a consumer's content
is never checked here and its own gate must run. A consumer commits with
`cctool commit … --root . --path ../cc-public`: the checks read both, the
root alone is committed. The Brave1 demonstration
is `../cc-brave1-demo`.

## Where things are

`ddr/` design decisions · `decision/` decisions by people · `specimen/` decisions a
workflow drafted as a trial · `query/` named queries · `need/` needs · `requirement/`
requirements · `requirement_set/` sets of them · `sweep/` what the evals found ·
`proposal/` rules proposed from it · `evidence/` observed evidence · `schema/` schemas ·
`annotation/` assertions offered for consideration, by a reviewer or anyone ·
`objective/` what a verification standard requires ·
`register/` type, relation, mark, term, style, rule, characteristic, framing, methodology,
document, process word, unit, criticality, gate tool, test method and model registers ·
`eval/` evals and control sets ·
`workflow/` components, workflows, deployments · `execution/` runs of a workflow and of a
test · `interface/` interface control documents · `test_case/` test cases ·
`nonconformity/` reports that were kept · `segment/` this repository's declaration of
itself · `test/` the tests · `src/cc_public/` the tool.

A directory exists once something lives in it: a type's `home` says where its items go,
and several homes above are named before anything occupies them.
