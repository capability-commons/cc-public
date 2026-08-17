# Capability Commons schema design notes — item identity & traceability

**Status:** working design proposal for review (not committed to any schema
except where noted below)
**Date:** 2026-08-17
**Purpose:** Resolve a tension both the RE-process schema work
(`draft_item` → `expanded_item` → `item_set`, in `schema/`) and the
sensor-simulation schema work (`CC_SCHEMA_DESIGN_NOTES_SENSOR_SIM.md`) ran
into independently: sometimes a requirement (or other data item) wants to be
its own standalone document, and sometimes it wants to be one entry in a list
inside a larger document — and today those two situations use different,
incompatible identity models. This note proposes a single scheme that covers
both, so relation-edge tooling never needs to special-case which situation
it's looking at, now or for any future trace type.

---

## 1. The problem, stated precisely

`base.schema.yaml` gives every **standalone** data item two-part identity:
`guid_item` (immutable UUIDv4, the canonical target for `relation` edges) and
`id_item` (readable, rarely-changing name). This works well and is the only
thing `relation` edges know how to point at today — an edge is always
`{guid_item, id_rel}`.

**Embedded entries don't get this.** `functional_requirement.schema.yaml`
says so explicitly for its embedded shape: "It carries no `guid_item`,
`relation`, or `workflow` of its own — the owning item supplies identity,
traceability, and lifecycle for the whole set." The same is true of
`glossary`'s `term[]`, and it's how the RE-process schemas were first drafted
too (`item_set.item[]` originally had only a locally-unique `id_item_entry`,
no `guid_item`).

The consequence: **nothing outside the owning document can point precisely
at one embedded entry.** A test can't cite exactly one embedded requirement
by a stable global reference. An `open_question_log` entry can't cite exactly
which `critique` finding it was raised by, except by an ad hoc string. A
future `functional_chain_specification` can't say "this chain obligation is
satisfied by requirement #7 inside block spec X" as a real graph edge — only
"by block spec X" as a whole.

This is exactly the tension both design threads hit from different
directions:

- **Sensor-sim** (`CC_SCHEMA_DESIGN_NOTES_SENSOR_SIM.md` §3): defaults to
  embedding `requirement[]`, promotes to standalone only when the same
  requirement is reused across containers — a **reuse-driven** promotion
  trigger. Open question #2 there ("when do we promote?") is really asking
  "what does promotion cost, and can we defer the decision?"
- **RE-process**: `draft_item`/`expanded_item` are standalone by default
  (they need to be independently addressable so `critique` and `pass_run`
  can point at exactly one candidate mid-pipeline), only becoming embedded
  once folded into a final `item_set` — a **process-granularity-driven**
  need for identity, not a reuse-driven one.

Two different pressures, same underlying gap: identity and storage location
are currently the same decision, and they shouldn't be.

---

## 2. Two candidate schemes

**A. Path-based addressing.** Keep embedded entries identity-less; let a
`relation` edge target a compound reference — owning `guid_item` plus a
JSON-Pointer-style path or local id (`{guid_item}#/requirement/id=fr_003`).
Cheap to author (no per-entry UUID), but it gives the relation-edge shape two
different target forms depending on where the target happens to live, which
is exactly the kind of special-casing meant to be avoided. Every tool that
walks the graph — traversal, visualisation, "what points at this," "what
does this depend on" — needs to know how to resolve both a bare `guid_item`
and a `guid_item`+pointer, and needs path stability guarantees (what happens
when an array is reordered, or a nested container gets restructured) that a
pointer scheme has to solve on its own, indefinitely, as new nesting shapes
appear.

**B. Storage-agnostic identity (recommended).** Decouple identity from
storage location entirely: **every entry that might ever need to be an
independent trace target gets its own `guid_item` + `id_item`, whether it
lives in its own file or as one entry in another item's array.** Embedding
vs. standalone becomes purely an authoring/storage convenience — "do we want
one file per item, or several co-edited together in one file" — with zero
effect on identity or on how relation edges resolve. A `relation` edge is
always exactly `{guid_item, id_rel}`, forever, regardless of nesting depth
or which schema the target conforms to.

---

## 3. Why B is the actual universal answer

The thing being asked for — "a universal scheme so we can add new trace
types without reworking the traceability-graph tooling" — already has half
its answer built into CC today: `id_rel` is already open vocabulary, so
adding a **new relation type** (a new kind of edge) has never required
tooling changes. What's missing is that adding a **new relation target
shape** (an embedded entry, or an entry nested inside an entry) currently
*would* require tooling changes, because embedded entries fall outside the
one addressing mechanism (`guid_item`) the tooling understands.

Scheme B closes that gap by making `guid_item` the *only* thing a
relation edge ever needs to resolve, no matter where the target actually
lives. A traversal tool never needs to know or care whether a given
`guid_item` belongs to a whole file or to entry #7 of some other file's
array — it just needs a `guid_item → location` lookup, which is not part
of the graph model at all, just an index (buildable by scanning every file
for `guid_item` occurrences, top-level or embedded, and recording where each
one was found). The relation/graph model itself never has to change again
as new document shapes, new embedding depths, or new schemas get added.

This also makes promotion (embedded → standalone) **lossless**: since
`guid_item` doesn't change when an entry is lifted out into its own file
(only the surrounding envelope — `protective_mark`, `copyright`, `license`,
its own `relation`, its own `workflow` — gets added), every existing edge
that already pointed at that entry keeps resolving without any repair.
Sensor-sim's open question #2 gets a clean answer: promotion is no longer a
identity-migration event, so it can happen at any time, cheaply, whenever
reuse pressure (or any other reason) makes it worth a file of its own.

Precedent for this exact move — identity independent of serialization
location — shows up wherever a project has needed to reference things across
files reliably: content-addressed storage (git blobs, addressed by hash
regardless of which tree references them), ReqIF (`SpecObject` identifiers
stable regardless of which `SpecificationType`/module groups them), RDF/IRI
identity (any resource gets a name independent of which graph or document
serializes it). Nothing here requires adopting any of those systems — YAML
and UUIDv4 are enough — just the same underlying principle.

---

## 4. What changes, concretely

**Entries gain identity, not the full base envelope.** An embedded array
entry adds two required fields —

```yaml
guid_item:   { $ref: "https://capability-commons.org/schema/base.schema.yaml#/$defs/uuidv4" }
id_item:     { $ref: "https://capability-commons.org/schema/base.schema.yaml#/$defs/identifier" }
```

— but does **not** gain `protective_mark`, `copyright`, `license`, its own
`relation` array, or its own `workflow`. Those stay properties of the owning
item, exactly as today. An entry is addressable but not yet a fully
independent governed item; promotion adds the rest of the envelope without
touching `guid_item`.

**Relation edges never change shape.** Still always `{guid_item, id_rel}`.
An edge pointing at an embedded entry looks identical to one pointing at a
standalone item — which is the entire point.

**Where a pointer previously had to be a bare string because there was
nothing else to point at**, it becomes a proper `guid_item` reference
instead. Concretely in the RE-process schemas drafted so far:
`open_question_log.entry[].source_ref` was a free-text string identifying
which `critique` finding or `item_set` entry raised the question; it should
become a `guid_item` reference now that both have one.

**Minting discipline.** A `guid_item` is assigned once, on first creation of
an entry, and preserved across every later edit to that entry — the same
discipline `base.schema.yaml` already states for top-level items, now
extended to entries. Tooling (including an LLM regenerating or revising a
document) must carry existing entries' `guid_item`s forward rather than
re-minting them, or every inbound edge silently breaks.

---

## 5. Local vs. cross-document references — a refinement

§4's "where a pointer previously had to be a bare string, it becomes a
`guid_item` reference" is the right default, but applied literally
everywhere it overcorrects. In practice, three edits made since §4 was
written (`functional_requirement`, `functional_block_specification`,
`glossary` — §7) needed a narrower rule, stated here so it's written down
rather than only implicit in those diffs:

- **A `guid_item` reference is required when a pointer must resolve
  independently, repository-wide** — i.e. the reader has no other context
  narrowing which document or which entry is meant.
  `open_question_log.entry[].source_ref`, `critique.finding[].
  affected_item[]`, and `functional_block_specification.requirement[].
  verifies` are all this shape: nothing else in the document tells you
  which `critique` or which requirement is meant, so the reference has to
  be globally resolvable on its own.
- **A local, human-readable key remains legitimate — and is preferable —
  when the reference is already scoped**, either by an accompanying
  `relation` edge or by being within the same document. `glossary`'s
  `related_to`/`prefers` fields reference `id_term` (not `guid_item`)
  because they always point at another term *within the same glossary* —
  there is no cross-document case to support, so a `guid_item` would add
  indirection without adding resolving power.
  `expanded_item.coverage[].id_category` is the same shape: it references
  a category inside the specific `coverage_checklist` already linked via
  the item's `checked_against` relation edge, so the edge does the
  cross-document resolving and the local key only needs to disambiguate
  within it. `functional_requirement`'s own `id_requirement` was kept
  (not renamed) for the same reason — it is how `functional_block_
  specification.requirement[]` entries refer to each other and to
  themselves *within one block spec*; `guid_item` was added alongside it
  for anything that needs to reach in from outside, but the local key
  didn't stop earning its keep.
- **A third, narrower case needs no `guid_item` at all: local schema/
  type-definition content.** `interface_control_document.payload_field[]`
  and `coordinate_frame.axis[]` are struct-like field definitions — they
  describe the *shape* of something, not an independently-traceable
  "thing" a relation edge would ever want to name. The same reasoning
  applies to `workflow_step_run.tool_call[]` (§7): a tool-call log entry
  is ephemeral provenance, not a data item; if a specific tool call's
  result needs to be cited later, the right move is to promote that
  result to a proper data item (e.g. a `source_item`), not to give the
  log entry a `guid_item`.

Rule of thumb: ask whether a reference already has a `relation` edge or
document boundary doing the scoping work. If yes, a local key is fine. If
the reference has to stand on its own, it needs `guid_item`.

---

## 6. What this note does *not* decide

- **Whether every embedded array in every schema needs this today.**
  Recommendation: apply it where a concrete need already exists (an entry
  that's already being pointed at, or that plausibly will be soon), not
  reflexively everywhere — and apply §5's refinement before reaching for
  `guid_item` by default. `coverage_checklist.category[]` and
  `extraction_note.candidate[]` don't have a concrete cross-document
  pointing-at need yet — apply the same principle to them if and when one
  shows up, rather than pre-emptively.
- **The `guid_item → location` index/resolver itself.** Out of scope here;
  a separate, later piece of tooling, and simple enough (a scan) that it
  shouldn't block adopting the identity convention now.
- **Whether `register.schema.yaml`/`skill_register.schema.yaml` entries or
  `simulated_sensor_sample_metadata.schema.yaml` should follow this
  scheme.** Deliberately not — these are different problems wearing a
  similar shape. A register entry's whole purpose is a stable
  snake_case join-key for a controlled vocabulary, not a graph-traceable
  "thing"; giving it a `guid_item` would just be two identifiers for one
  concept with no second one adding resolving power.
  `simulated_sensor_sample_metadata` is explicitly a runtime payload
  contract, not a CC data item, per the sensor-sim design notes' own
  statement of that as a non-goal — out of scope for this note by that
  document's own design, not an oversight here.

---

## 7. Applied in this pass

Original pass:

- `item_set.schema.yaml` — `item[]` entries now carry `guid_item` + `id_item`.
- `critique.schema.yaml` — `finding[]` entries now carry `guid_item` + `id_item`;
  `affected_item[]` changed from `id_item` values to `guid_item` values.
- `open_question_log.schema.yaml` — `entry[].source_ref` changed from a bare
  string to a `guid_item` reference.

Follow-up pass (existing CC v1 "official" schemas — the amendment §5's
predecessor text had flagged but deferred):

- `functional_requirement.schema.yaml` — `$defs/requirement_fields` gained
  `guid_item` alongside the existing `id_requirement` (kept, not renamed —
  see §5's local-key case); `verifies` changed from `id_check` values to
  `guid_item` values.
- `functional_block_specification.schema.yaml` — `$defs/acceptance_check`
  gained `guid_item` alongside the existing `id_check` (kept, not renamed).
- `glossary.schema.yaml` — `$defs/glossary_term` gained `guid_item`
  alongside the existing `id_term` (kept — `related_to`/`prefers` still use
  it, per §5); the schema's own top-level description, which previously
  and incorrectly stated terms "are not separate data items" and "cannot"
  be relation targets, was corrected to match.

Workflow-step pass (`workflow_step_type.schema.yaml`,
`workflow_step_run.schema.yaml` — new schemas, not an amendment):

- `workflow_step_run`'s input/output are `relation` edges (`consumed`/
  `produced`), not a bespoke field — the general graph-identity model this
  note describes applied directly to a new schema rather than retrofitted.
- `pass_run.schema.yaml` retired (stub left in place; deletion isn't
  available in this environment) — generalised into `workflow_step_type` +
  `workflow_step_run`, see that stub for the mapping.

See `SYNTHESIS - SOPHIST methodology distilled for LLM prompts.md` §14 (in
the requirements-engineering reference library) for how this connects back
to the wider requirements-process design this schema work is implementing.
