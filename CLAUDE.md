# cc-public

Capability commons: a document-oriented engineering system. Everything
is a data item with an identity; reasoning lives in design decisions,
not in artifacts. See `ddr/` before changing anything the design
decisions decide.

## Tools

All of these are `pixi run cctool …`; `pixi run check` and `pixi run format`
are shorthands. Every command has `--help`; the writing commands take
`--root DIR` (repeatable), `check` takes `--path`.

- `check` — eleven mechanical checks (parse, guid, identifier, source,
  reference, relation, schema, layout, workflow, trace, confidence). Must
  be clean. A finding names its file, and for a class or function item
  the definition beneath it: `run.py::State::generator_for`. `--fail-fast`, `--closed-world`,
  `--format json`, `--out FILE`.
- `check --eval` — LLM evals. Needs `CCTOOL_JUDGE_MODEL` in `.env` (never
  paste a key into chat). `--confirm N` re-judges an adverse verdict N times,
  uncached (default 5); `--id-eval`/`--id-item`/`--id-type`/`--id-schema`
  narrow (anchored regex); `--judge-model null` dry-runs.
- `measure --id-eval X [--samples N] [--record]` — judges X's control cases
  fresh and reports false-positive / false-negative / unanimity per origin;
  `--record` writes them onto the eval as `confidence`, stamped with a digest
  of criterion, examples, scope and cases. Change any of those and the row
  is stale: the confidence check says so, and a guard on that eval is
  refused to that judge until it is measured again (`ddr_eval_admission`).
  N is odd.
- `case --id-eval X --item Y --verdict met|unmet --note "…"` — turns a finding
  into a control case (met = suppressed, unmet = confirmed). A later sweep
  matching the same words reports a met case as a note, not a finding.
  `--origin written` holds a hand-written item to a verdict instead; a
  mutated case is made through the API with its subject text set.
- `questions [--open]` — what the design decisions leave open, and what
  answered it.
- `trace [--requirement X] [--source Y] [--gaps] [--closed-world] [--format json]`
  — what each requirement derives from, what implements it
  (`r_is_implemented_by`, to a package, module, class or function), what
  verifies it (`r_verifies`) and what it lacks; `--source` shows what a
  source item implements and verifies. Reads the same projection
  (`cc_public.trace`) as the trace check. Proposed gaps are advisory;
  accepted ones critical (`ddr_implementation_trace`).
- `run WORKFLOW --deployment DEP --bind node.input.port=ITEM …` — one run
  of a dataflow workflow. `--dry-run` shows the order and writes nothing.
  Needs a clean tree. Makes items with `new`, fills fields with `set`,
  links what a port `decides:` to what it makes, checks after every node,
  restores on a critical finding, writes an execution record to
  `execution/`, commits if the deployment says so.
- `commit TITLE [--brief …] [--description …] [--link REL ITEM]` — runs the
  checks and the lint, refuses on a critical or lint finding unless
  `--checkpoint` and on an incomplete analysis always, writes a commit
  record into the message. `log [-n N]` reads them back.
- `pixi run test` — pytest over `test/`: the printer's content-preservation
  proof over every file, and the edit commands against a copy of the tree.
  Holds a coverage floor; `pixi run coverage` shows what is uncovered.
- `pixi run lint` — ruff over `src` and `test`, configured in `pyproject.toml`
  for the house style, then `lint-imports` holding the seven tiers of
  `ddr_layered_architecture`: a package imports downward only, and an
  underscore name is its module's (tests excepted). Must be clean after any
  code edit; `commit` runs both and refuses on a finding.
- `pixi run gate` — what a pipeline runs: check with the world closed and
  failing on a critical finding, lint, test. `check` alone only reports.

## Writing items — use the tool, never hand-edit

- `new TYPE ID` — mints the identity, writes every required field empty (it
  fails the checks until written), puts it where its type lives (`--out`
  otherwise). A python package or module too: `pym_cc_public.demo.thing`
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
  list, and `a: b` a mapping, so quote a string containing `: ` or `#`.
  Prose: `set ITEM PATH --prose <<'EOF' … EOF`. ITEM is an id or guid,
  top-level or embedded; PATH is a dot path within it.
- `unset ITEM PATH` — removes a field.
- `rename ITEM NEW_ID` — the guid stays; the id changes in its declaration,
  the file name, every embedded item it qualifies (ports, nodes) and every
  reference. An embedded item under a local key can change only its last
  step, and its key follows. Prose mentioning the old id is listed, not
  changed; values that spell a key, such as a port address in an edge, are
  yours to `set`.
- `link SOURCE RELATION TARGET` — both items by id or guid; looks up guids,
  refuses unknown relations and duplicates. Answer a question with
  `link ANSWERER r_answers qst_…`, never by editing it. A relation may
  constrain its ends (`domain`, `range`, `acyclic` on the register entry);
  the relation check refuses an edge outside them. A test module names the
  requirement it verifies with `link pym_test.test_x r_verifies req_y`.
- Dot paths: `properties.title.maxLength`, `table.t_foo`,
  `edge_back.draft_to_draft.guard`. A key never contains a dot; an address
  such as `draft.output.record` is a value.

For more than a handful of writes use the API under `pixi run python`:
`Tree('.')`, then `edit.new.new(tree, type, id, edit.tree.defaults())`,
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

## Where things are

`ddr/` design decisions · `need/` needs · `requirement/` requirements · `schema/` schemas · `register/` type, relation, mark,
term, style, rule, characteristic, framing and methodology registers · `eval/` evals and control sets · `workflow/` components,
workflows, deployments · `execution/` runs · `src/cc_public/` the tool.
