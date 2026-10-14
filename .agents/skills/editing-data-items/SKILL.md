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
| take an edge away                       | `cctool unlink SOURCE RELATION TARGET` |
| change a field                          | `cctool set ID PATH VALUE [--yaml]` |
| take a field out                        | `cctool unset ID PATH`              |
| remove an item                          | `cctool remove ID`                  |
| give an item a new id                   | `cctool rename OLD NEW`             |
| add items that need each other          | `cctool batch FILE` (or `-` for stdin) |

A field named twice with `--field` becomes a list. In a batch, a field
takes any YAML value, so lists and mappings (a schema's `allOf`, say)
are written as YAML.

`set` takes VALUE as text, or as YAML with `--yaml`. PATH is a field
name, or a dotted path into its value in which a number picks an
element of a list: `protective_mark.0.id_mark`. Setting or unsetting
`id_ROLE` sets or takes out `guid_ROLE` with it, so never write a guid
by hand. Edges and aliases are not fields for `set`: use `link`,
`unlink` and `rename`.

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
- **`new`, `remove` and `rename` refuse pym, pyp, dls and file ids.**
  Those items live in the file they name. Write, move or remove the
  file by hand, then `cctool format`.
- **Renaming an id:** use `cctool rename`, never a search and replace.
  It keeps the old id as an alias of a register entry, which the commit
  check requires. Then fix each file it lists as still naming the old
  id, and name both ids in the commit item.
- **Removing an item is refused while anything names it.** Remove or
  change what names it first, in the same `batch`, and name the removed
  id in the commit item, or the commit-msg hook refuses the commit.
- **A guid is never written by hand.** `new` mints it, and fills in
  `guid_<role>` for any `id_<role>` field you give it.

## By hand

When there is no command for it, edit the file, then run
`cctool format` and `cctool check`. `unformatted_file` means the layout
differs from what `cctool format` writes; run it rather than fixing the
spacing yourself.
