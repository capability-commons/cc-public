# Guidance for agents

This file is for any coding agent working in cc-public. `README.md`
says what the repository is and how to run it. This file says how to
work in it.

## Before you finish

- `pixi run check`, `pixi run test` and `pixi run lint` all pass.
- `cctool check` reports 0 failures. A failure that was there before
  your change is still yours to report, not to hide.
- Commit locally. Do not push unless asked.

## Changing data items

- Prefer `cctool new`, `link`, `set` and `batch` to editing YAML by
  hand. They mint guids, fill in rights, keep the layout, and refuse an
  edit that adds a failure. Use `--dry-run` to see an edit first.
- Never write a guid by hand. A guid is the prefix of the type and 32
  hex digits, minted once and never changed.
- A new concept must be named by some other item, so make the concept
  and the item that names it together, with `cctool batch`.
- After any edit by hand, run `cctool format`, then `cctool check`.
- An id is renamed by adding the old id to the `alias` list of the
  entry. Nothing else may still name the old id.
- Use the preferred term of a concept in `_data/register/reg_concept.yaml`
  in names and in prose. Never use a term it lists as deprecated.

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
- Datalog follows the house style of `check.dl`: a separator and a
  comment above each relation, one declared column per line with names
  and types aligned, variables named for the columns they fill, and one
  body atom per line.
- Where a recognised standard covers the ground (ISO 1087, ISO/IEC
  25010, ISO/IEC/IEEE 42010), follow its structure and terms, and cite
  it.

## Keep it small

The previous iteration grew faster than it could be reviewed. Add a
type, relation, field or command only when a real instance needs it,
and keep each change small enough to read in one sitting.
