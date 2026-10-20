---
name: editing-data-items
description: >
  How to add or change data items in cc-public with cctool, and the
  traps that make an edit be refused. Read this BEFORE adding a type,
  relation, concept, concern, option or annotation, BEFORE changing
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
| give a source file its item             | `cctool header PATH [ID] --field ...` |
| give a python class or function its item | `cctool header PATH::NAME --field title ...` |
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
`id_FIELD` sets or takes out `guid_FIELD` with it, so never write a guid
by hand. Edges and aliases are not fields for `set`: use `link`,
`unlink` and `rename`.

## The traps

- **A new concept is refused on its own** (`unused_concept`), because
  nothing names it yet. Make it in one `batch` with the item that names
  it, such as the annotation or type that uses it.
- **An argument lives in the folder of its issue.** Start one with an
  issue (`new iss_NAME --link r_is_about lc_NAME`), then give each option
  `--link r_is_option_for iss_NAME` (`answer_count` refuses an option that
  answers no issue, or two) and each annotation `--link r_is_about
  iss_NAME`. `new` writes all of them, and determinations, in
  `_data/issue/iss_NAME/`; anything moved there by hand is checked by
  `misplaced_document`.
- **An annotation or issue is refused without `r_is_about`**
  (`missing_about`). Give `--link r_is_about TARGET` with `new`.
- **A determination is refused unless it upholds or rejects an option**
  (`determination_without_option`). Give `--link r_upholds DEC` or
  `--link r_rejects DEC`. Only record a determination that a person
  has made; the commit that adds it says who and when.
- **A determination that upholds an option is refused while a driver
  is unargued** (`unargued_driver`). Every concern that the logical
  component the issue is about `r_is_driven_by` needs an annotation
  for it that supports or challenges the option or another option for
  the same issue. Rejecting an option needs no such annotation.
  Argue it; do not drop the driver to pass.
- **A second determination of an issue is refused**
  (`competing_determinations`). An issue has at most one. When the
  person who settled it changes their ruling, edit that determination
  in place with `set`, `link` and `unlink`; the commits that change its
  file are the history of the ruling.
- **`restriction_violation`** means an end of the edge does not meet a
  relation restriction its relation names (`r_restricts_source` or
  `r_restricts_target` in `reg_relation.yaml`). A restriction admits or
  excludes roles, and a type's items play the roles its entry in
  `reg_data_item_type.yaml` names with `r_has_items_that_play`. Do not
  pick another relation just to pass. A new type takes part in a
  relation by playing the role it needs, not by changing the relation.
- **An annotation that supports or challenges an option needs at least
  one concern** (`argument_without_concern`), and one that bears on no
  option needs none (`concern_without_option`). A premise several
  concerns rest on is one annotation linked to each concern, not one
  annotation per concern.
- **`schema_violation`** names the file, line and field. A list field
  given once on the command line is a string; name it twice, or use a
  batch.
- **`new`, `remove` and `rename` refuse pym, pyp, pyc, pyf, lpf and
  file ids.** Those items live in the file they name. Give a file its
  item with `cctool header PATH` (a module's id follows from its path;
  any other file needs ID, such as `file_githooks_pre_commit`). Move or
  remove the file by hand, then `cctool format`.
- **A class or function gets an item only when something must point
  at it.** `cctool header src/x.py::Thing::run --field title Run`
  writes it in the docstring, and the prose the docstring held becomes
  its brief. Its id follows from where it is defined.
- **`header` refuses a module that has a docstring already.** Take
  the docstring out, and give its text to the item as `description`.
- **Renaming an id:** use `cctool rename`, never a search and replace.
  It keeps the old id as an alias of a register entry, which the commit
  check requires. Then fix each file it lists as still naming the old
  id, and name both ids in the commit item.
- **Removing an item is refused while anything names it.** Remove or
  change what names it first, in the same `batch`, and name the removed
  id in the commit item, or the commit-msg hook refuses the commit.
- **A guid is never written by hand.** `new` mints it, and fills in
  `guid_<field>` for any `id_<field>` field you give it. An embedded
  item you give in a field to `new` or `set`, such as a member of an
  interface control document, gets `guid_self` minted after its
  `id_self`.

## By hand

When there is no command for it, edit the file, then run
`cctool format` and `cctool check`. `unformatted_file` means the layout
differs from what `cctool format` writes; run it rather than fixing the
spacing yourself.
