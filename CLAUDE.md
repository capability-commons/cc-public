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
- `trace [--requirement X] [--source Y] [--gaps] [--closed-world] [--format json]`
  — what each requirement derives from, what implements it
  (`r_is_implemented_by`, to a package, module, class or function), what
  verifies it (`r_verifies`) and what it lacks; `--source` shows what a
  source item implements and verifies; `--changed-since REF` shows what
  every item in the files changed since a commit may affect. Reads the
  same projection (`cc_public.trace`) as the trace check. Proposed gaps are
  advisory; accepted ones critical (`ddr_implementation_trace`).
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

Rendering

- `render OBSERVATION [--findings report.json] [--out DIR] [--format pdf|html|both]`
  — the dossier rooted at an observation as two documents, a briefing
  and a technical appendix, drawn from the graph: needs, concepts,
  promoted requirements, runs, the findings in a report from `check --eval
  --format json --out FILE`, trace gaps, the derivations drawn by Graphviz.
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

- `pixi run test` — pytest over `test/`, in parallel: the printer's
  content-preservation proof over every file, and the edit commands against
  a copy of the tree. Holds a coverage floor; `pixi run coverage` shows
  what is uncovered.
- `pixi run lint` — ruff over `src` and `test`, configured in `pyproject.toml`
  for the house style, then `lint-imports` holding the seven tiers of
  `ddr_layered_architecture`: a package imports downward only, and an
  underscore name is its module's (tests excepted). Must be clean after any
  code edit; `commit` runs both and refuses on a finding.
- `pixi run gate` — what a pipeline runs: check with the world closed and
  failing on a critical finding, lint, test. `check` alone only reports.
- `pixi run -e demo ui` — the demonstration's temporary Streamlit interface,
  `../demo/ui/app.py`, in its own `demo` environment: a reader over the
  tree and a control panel that shells `cctool` one job at a time. It edits
  no item. Disposable; the projection it reads is not.

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

`ddr/` design decisions · `specimen/` decisions a workflow drafted as a trial · `query/` named queries · `need/` needs · `requirement/` requirements · `evidence/` observed evidence · `schema/` schemas · `register/` type, relation, mark,
term, style, rule, characteristic, framing, methodology and document registers · `eval/` evals and control sets · `workflow/` components,
workflows, deployments · `execution/` runs · `src/cc_public/` the tool.
