---
name: editing-data-items
description: >
  How to add or change data items in cc-public with cctool, and the
  traps that make an edit be refused. Read this BEFORE adding a type,
  relation, concept, concern, decision or annotation, BEFORE changing
  any YAML under _data or the item in a module docstring or comment
  header, and ALWAYS when cctool refuses an edit or cctool check fails.
---

# Editing data items

The reference is `cctool --help` and `AGENTS.md`. This is the
procedure, and the traps.

> **The one rule:** change the graph through `cctool` where it can, and
> let it refuse you. An edit is checked with the tree as it would be,
> and written only if it adds no failure. A refusal is the checker
> telling you something true; fix the cause, do not work around it.

## The procedure

1. Read the type entry in `_data/register/reg_data_item_type.yaml` and
   the schema it names. They say which fields an item needs and which
   register, if any, holds it.
2. Find what you will link to with `cctool query`, for example
   `cctool query sql "SELECT id FROM type_of WHERE type = 't_concern'"`.
3. Write the edit with `--dry-run` first, and read the diff.
4. Run it. On success it names each file it wrote.
5. `cctool check` and `pixi run test` before you commit.

## Which command

| to                                      | use                                 |
|-----------------------------------------|-------------------------------------|
| add one item                            | `cctool new ID --field ... --link ...` |
| add an edge                             | `cctool link SOURCE RELATION TARGET` |
| change a text field                     | `cctool set ID NAME VALUE`          |
| add items that need each other          | `cctool batch FILE` (or `-` for stdin) |

A field named twice with `--field` becomes a list. In a batch, give a
list as a YAML list.

## The traps

- **A new concept is refused on its own** (`unused_concept`), because
  nothing names it yet. Make it in one `batch` with the item that names
  it, such as the annotation or type that uses it.
- **An annotation or decision is refused without `r_is_about`**
  (`missing_about`). Give `--link r_is_about TARGET` with `new`.
- **`domain_violation` or `range_violation`** means the relation does
  not run between those types. Read the relation's `domain` and `range`
  in `reg_relation.yaml`; do not pick another relation just to pass.
- **An annotation that supports or challenges needs exactly one
  concern** (`concern_count`): add `--link r_argues_for_concern ...`.
- **`schema_violation`** names the file, line and field. A list field
  given once on the command line is a string; name it twice, or use a
  batch.
- **`new` refuses pym, pyp, dls and file ids.** Those items live in the
  file they name. Write the header by hand, then `cctool format`.
- **Renaming an id:** add the old id to `alias` on the entry, and change
  every reference and mention. `outdated_reference` and
  `outdated_mention` find what is left.
- **A guid is never written by hand.** `new` mints it.

## By hand

When there is no command for it, edit the file, then run
`cctool format` and `cctool check`. `unformatted_file` means the layout
differs from what `cctool format` writes; run it rather than fixing the
spacing yourself.
