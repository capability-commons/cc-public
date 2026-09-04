# cc-public

Capability commons: a document-oriented engineering system. Everything
is a data item with an identity; reasoning lives in design decisions,
not in artifacts. See `ddr/` before changing anything the design
decisions decide.

## Tools

All of these are `pixi run cctool …`; `pixi run check` and `pixi run format`
are shorthands. Every command has `--help`; the writing commands take
`--root DIR` (repeatable), `check` takes `--path`.

- `check` — seven mechanical checks (parse, guid, identifier, reference,
  schema, layout, workflow). Must be clean. `--fail-fast`, `--closed-world`,
  `--format json`, `--out FILE`.
- `check --eval` — LLM evals. Needs `CCTOOL_JUDGE_MODEL` in `.env` (never
  paste a key into chat). `--confirm N` re-judges an adverse verdict N times,
  uncached (default 5); `--id-eval`/`--id-item`/`--id-type`/`--id-schema`
  narrow (anchored regex); `--judge-model null` dry-runs.
- `measure --id-eval X [--samples N] [--record]` — judges X's control cases
  fresh and reports false-positive / false-negative / unanimity per origin;
  `--record` writes them onto the eval as `confidence`.
- `case --id-eval X --item Y --verdict met|unmet --note "…"` — turns a finding
  into a control case (met = suppressed, unmet = confirmed). A later sweep
  matching the same words reports a met case as a note, not a finding.
  `--origin written` holds a hand-written item to a verdict instead; a
  mutated case is made through the API with its subject text set.
- `questions [--open]` — what the design decisions leave open, and what
  answered it.
- `run WORKFLOW --deployment DEP --bind node.input.port=ITEM …` — one run
  of a dataflow workflow. `--dry-run` shows the order and writes nothing.
  Needs a clean tree. Makes items with `new`, fills fields with `set`,
  links what a port `decides:` to what it makes, checks after every node,
  restores on a critical finding, writes an execution record to
  `execution/`, commits if the deployment says so.
- `commit TITLE [--brief …] [--description …] [--link REL ITEM]` — runs the
  checks, refuses on a critical finding unless `--checkpoint`, writes a
  commit record into the message. `log [-n N]` reads them back.
- `pixi run test` — pytest over `test/`: the printer's content-preservation
  proof over every file, and the edit commands against a copy of the tree.

## Writing items — use the tool, never hand-edit

- `new TYPE ID` — mints the identity, writes every required field empty (it
  fails the checks until written), puts it where its type lives (`--out`
  otherwise). A python package or module too: `pym_cc_public.demo.thing`
  becomes `demo/thing.py` beside its parent package, docstring only.
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
  `link ANSWERER r_answers qst_…`, never by editing it.
- Dot paths: `properties.title.maxLength`, `table.t_foo`,
  `edge.review_to_draft.guard`. A key never contains a dot; an address
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

`ddr/` design decisions · `schema/` schemas · `register/` type, relation, mark and
term registers · `eval/` evals and control sets · `workflow/` components,
workflows, deployments · `execution/` runs · `src/cc_public/` the tool.
