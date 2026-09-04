# cc-public

Capability commons: a document-oriented engineering system. Everything
is a data item with an identity; reasoning lives in decision records,
not in artifacts. See `ddr/` before changing anything the records
decide.

## Tools

- `pixi run check` — seven mechanical checks (parse, guid, identifier,
  reference, schema, layout, workflow). Must be clean.
- `pixi run format` — the printer. Lays out every YAML file and every
  document held in a python docstring (module, class or function, found
  via the syntax tree) to the convention. Idempotent.
- `cctool measure --id-eval X [--samples N] [--record]` — judges X's control
  cases fresh and reports false-positive / false-negative / unanimity per
  origin; `--record` writes them onto the eval as `confidence`.
- `cctool case --id-eval X --item Y --verdict met|unmet --note "…"` — turns a
  finding into a control case (met = suppressed, unmet = confirmed). A later
  sweep matching the same words reports a met case as a note, not a finding.
- `pixi run cctool check --eval` — LLM evals. Needs `CCTOOL_JUDGE_MODEL`
  in `.env` (never paste a key into chat). `--confirm N` re-judges an
  adverse verdict N times, uncached; `--id-eval`/`--id-item` narrow.

- `pixi run test` — pytest over `test/`: the printer's content-preservation
  proof over every file, and the edit commands against a copy of the tree.

## Writing items — use the tool, never hand-edit

- `cctool new TYPE ID` — mints the identity, writes every required field
  empty (it fails the checks until written), puts it where its type lives.
  A python package or module too: `pym_cc_public.demo.thing` becomes
  `demo/thing.py` beside its parent package, docstring only.
- `cctool insert TYPE NAME --into ITEM [--at COLLECTION]` — a new embedded
  item (register entry, port, node…) with its shape read from the
  container's schema. `--at` defaults to `table` for a register.
- `cctool set ITEM PATH VALUE` — VALUE is YAML (`3`, `[]`, `true`); for
  prose: `cctool set ITEM PATH --prose <<'EOF' … EOF`. ITEM is an id or
  guid, top-level or embedded; PATH is a dot path within it.
- `cctool unset ITEM PATH` — removes a field.
- `cctool questions [--open]` — what the records leave open, and what
  answered it. A question is an entry under a record's `question:`; answer
  one with `cctool link ANSWERER r_answers qst_…`, never by editing it.
- `cctool link SOURCE RELATION TARGET` — both items by id or guid; looks
  up guids, refuses unknown relations and duplicates.

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
- Prose in an item describes; argument goes in a decision record. Create
  a record only for a genuine decision with real alternatives.
- Commits go through `cctool commit TITLE [--brief …] [--description …]`,
  which runs the checks, refuses on a critical finding unless
  `--checkpoint`, and writes a commit record into the message. Add
  `--trailer 'Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>'`
  when you are the one committing. Do not commit unless asked; the user
  commits, and a workflow run commits at its end.

## Where things are

`ddr/` records · `schema/` schemas · `register/` type, relation, mark and
term registers · `eval/` evals · `workflow/` components, workflows,
deployments · `src/cc_public/` the tool.
