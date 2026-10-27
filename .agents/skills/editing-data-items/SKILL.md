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
   `cctool query sql "SELECT id FROM has_type WHERE type = 'type_concern'"`.
3. Write the edit with `--dry-run` first, and read the diff.
4. Run it. On success it names each file it wrote.
5. `cctool check` and `pixi run test` before you commit.

## Which command

| to                                      | use                                 |
|-----------------------------------------|-------------------------------------|
| add one item                            | `cctool new ID --field ... --link ...` |
| give a source file its item             | `cctool header FILEPATH [ID] --field ...` |
| give a python class or function its item | `cctool header FILEPATH::NAME --field title ...` |
| give a predicate of a logic program its item | `cctool header FILEPATH::NAME --field did ... --field fix ...` |
| add an edge                             | `cctool link SOURCE RELATION TARGET` |
| take an edge away                       | `cctool unlink SOURCE RELATION TARGET` |
| change a field                          | `cctool set ID FIELDPATH VALUE [--yaml]` |
| take a field out                        | `cctool unset ID FIELDPATH`         |
| remove an item                          | `cctool remove ID`                  |
| give an item a new id                   | `cctool rename OLD NEW`             |
| add items that need each other          | `cctool batch FILEPATH` (or `-` for stdin) |
| bring in classes or relations of a standard ontology | `cctool import FILEPATH IRI... --namespace IRI SHORT RELEASE` |
| compare those classes and relations with their release | `cctool import FILEPATH --namespace IRI SHORT RELEASE --check` |

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
- **A deliberation lives in the folder of its decision.** Start one with a
  decision (`new dec_NAME --link relation_is_about lco_NAME`), then give each option
  `--link relation_is_option_for dec_NAME` (`option_count` refuses an option that
  is linked to no decision, or to two) and each annotation `--link relation_is_about
  dec_NAME`. `new` writes all of them, and rulings, in
  `_data/decision/dec_NAME/`; anything moved there by hand is checked by
  `misplaced_document`.
- **An annotation or decision is refused without `relation_is_about`**
  (`missing_about`). Give `--link relation_is_about TARGET` with `new`.
- **A bracketed term is refused unless its concept is used**
  (`unresolved_term`, `ambiguous_term`). Prose may write `[[item]]` or
  `[[concept_identifiable_data_item|item]]`; give the holding item, or its
  register, `cctool link ID relation_uses_concept CONCEPT`. Write the explicit
  form wherever two used concepts share the term.
- **A ruling is refused unless it upholds or rejects an option**
  (`no_option_in_ruling`). Link it to the option, not to the decision:
  give `--link relation_upholds OPT` or `--link relation_rejects OPT`,
  once for each option it settles. A link to the decision breaks
  `constraint_violation`. A ruling also needs a `title` and a `brief`,
  as `sch_ruling` requires:
  `cctool new ruling_NAME --field title TITLE --field brief TEXT --link relation_rejects OPT`.
  Only record a ruling that a person has made; the commit that adds it
  says who and when. The brief ends `Ruled by WTP on YYYY-MM-DD.`,
  with the maker's initials and the date only, never a time of day. It
  may summarize or paraphrase what they said; it claims no more than
  they said. The same holds wherever prose cites a statement by a
  maintainer or developer: initials and date, such as
  `(WTP, 2026-10-25)`.
- **A ruling that upholds an option is refused while a driver
  is unargued** (`unargued_driver`). Every concern that the logical
  component the decision is about `relation_is_driven_by` needs an annotation
  for it that supports or challenges the option or another option for
  the same decision. So does every concern the decision names itself
  with `relation_is_driven_by`: the component's drivers are the least a
  decision is argued for, and a decision may add one that bears on it
  more than on the rest of the component. Rejecting an option needs no such annotation.
  Argue it; do not drop the driver to pass.
- **A second ruling of a decision is refused**
  (`competing_rulings`). A decision has at most one. When the
  person who settled it changes their ruling, edit that ruling
  in place with `set`, `link` and `unlink`; the commits that change its
  file are the history of the ruling.
- **`constraint_violation`** means an end of the edge does not meet a
  relation constraint its relation names (`relation_constrains_source` or
  `relation_constrains_target` in `reg_relation.yaml`). A constraint admits or
  excludes roles, and a type's items play the roles its entry in
  `reg_data_item_type.yaml` names with `relation_has_items_that_play`. Do not
  pick another relation just to pass. A new type takes part in a
  relation by playing the role it needs, not by changing the relation.
- **An annotation that supports or challenges an option needs at least
  one concern** (`argument_without_concern`), and one that bears on no
  option needs none (`concern_without_option`). A premise several
  concerns rest on is one annotation linked to each concern, not one
  annotation per concern.
- **Check the facts of an argument before you write it.** An
  annotation drafted elsewhere, by an advocate or from notes, states
  facts about the tree as it was: lines, counts, commits, quotes, what
  a file holds. Check each against the tree as it is now, and correct
  or drop the claim that no longer holds, before it goes in. The
  verifier of a run of advocates is not enough on its own: the tree
  moves between the draft and the write.
- **Re-read the cited code after a change to it, before you commit
  the arguments.** When one piece of work changes code and drafts
  arguments together, as when an argument prompts a fix, the arguments
  are often written against the code before the change. After the
  code commits, read again each part the arguments cite (`cctool query
  text`, or a grep of `_data/decision` for its path) and correct what
  the change made untrue. If the change undoes what an argument argued,
  add an annotation that challenges it rather than rewording it. The
  daily review of 2026-10-27 found an argument on test evidence that
  was committed after the gate change it described as not yet made.
- **A citation of a file of the tree by line number is refused**
  (`line_citation`), since the lines move as the file changes. Name the
  part that holds the line: `PATH within NAME` for a
  function, `Class.method`, constant or predicate of code;
  `pyproject.toml at project.dependencies` for a field of a
  configuration or data file, or `just after KEY.PATH` for a line that
  is not a field; `README.md#getting-started` for a section of
  markdown. A named part the file does not hold is refused too
  (`unresolved_citation`). Lines of one commit may be cited as
  `REV:PATH lines N-M`. Files outside the tree are not checked.
- **`schema_violation`** names the file, line and field. A list field
  given once on the command line is a string; name it twice, or use a
  batch.
- **`new`, `remove` and `rename` refuse pym, pyp, pycls, pyf, lpf, file
  and shell ids.** Those items live in the file they name. Give a file
  its item with `cctool header FILEPATH` (the id of a python module or
  of a logic program file follows from its path; any other file needs
  ID, such as `shell_githooks_pre_commit`). Move or remove the file by
  hand, then `cctool format`.
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
