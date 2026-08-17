# Capability Commons schema design notes — sensor simulation architecture

**Status:** working design summary for review (not a committed schema release)  
**Date:** 2026-08-17  
**Purpose:** Capture decisions and open questions from the axair-geoengine /
sensor-simulation design discussion, so they can drive the next CC schema
iteration.

Driving use case: re-implementation of the geometry-oracle / sensor-simulation
pipeline (see `axair-geoengine-auto/SPEC_QUESTIONNAIRE.md`). Schema work lives
in `cc-public/schema/`.

---

## 1. Goal

Decompose the system into **functional blocks** (dataflow nodes with
heterogeneous IPC) and capture:

1. **What each block does** — functional requirements + acceptance  
2. **What crosses each boundary** — interface control documents (ICDs)  
3. **Shared vocabulary** — frames, sample metadata, glossary  

Together, block specs + ICDs should be enough for a human or LLM to implement
one block at a time (target: ~5–15 blocks).

Product posture: **maintained internal product**, multi-year, many scenarios;
start with C-UAS (EO + LWIR + simplified RADAR).

---

## 2. Artefact map (agreed separation)

| Artefact | Answers | Schema / location |
|----------|---------|-------------------|
| **Functional block specification** | What *one* block does | `functional_block_specification.schema.yaml` |
| **Functional requirement** | One shall-statement (entry shape) | `functional_requirement.schema.yaml` |
| **Interface control document** | One *directed edge* contract | `interface_control_document.schema.yaml` |
| **Coordinate frame** | Named origin/axes/units | `coordinate_frame.schema.yaml` + `coordinate_frame/*.yaml` |
| **Simulated sensor sample metadata** | Runtime sidecar for one sensor × one `t_sim_s` | `simulated_sensor_sample_metadata.schema.yaml` |
| **Glossary** | Project terms | `glossary.schema.yaml` + `sensor_simulation.glossary.yaml` |
| **Architecture** *(planned)* | Topology: blocks + in-scope edges for an iteration | Not yet |
| **Chain / system functional specs** *(planned)* | Same requirement pattern at chain/system scope | Not yet |
| **Message definition** *(planned)* | Reusable payload types cited by ICDs | Not yet |

### Explicit non-goals for these artefacts

- ICD ≠ full port sheet for one block (compose from edge ICDs + relations)  
- ICD ≠ functional behaviour  
- Block spec ≠ pipeline graph  
- Sample metadata ≠ CC `guid_item` data item (runtime payload contract)  
- Preview RGB ≠ ground truth  

### Do not create yet

- `functional_test_specification` twin of block specs — keep tests in
  `acceptance[]` until shared fixtures force a separate type  
- Separate port-sheet type  
- Per-requirement `guid_item` files as the default  

---

## 3. Functional requirements and specifications

### Decision: one requirement shape, multiple containers

All functional requirements should follow the **same pattern**, whether they
belong to a block, a chain, or the whole system. Scope is allocation, not
dialect.

**Authoring guidance:** INCOSE guide to writing requirements and SOPHIST
methodology should inform statement quality (one idea, shall, verifiable,
unambiguous). Encode INCOSE-useful fields in schema where cheap (`statement`,
optional verification method, rationale); keep SOPHIST mostly as authoring /
review discipline in schema prose and workflow.

### Current shape

**`functional_requirement`** — entry (normally embedded, not a standalone
`guid_item`):

- `id_requirement`, `statement`  
- optional `note`, `verifies[]` → acceptance check ids  

**`functional_block_specification`** — one item = one block:

- `id_block`, `label`  
- `requirement[]` (the body)  
- `provides_icd[]` / `requires_icd[]`  
- `out_of_scope`, optional `constraints`  
- `acceptance[]`, `status`, `statement`  

Removed from earlier draft: chain-in-spec (`subject_kind`, `chain_edge`),
`glossary_term[]`, prose-only `purpose` / `behaviour` / `responsibility`
(replaced by structured requirements).

### Planned containers (same `requirement[]`)

| Container | Scope | Holds |
|-----------|-------|--------|
| Block spec *(exists)* | One node | Behaviour / ownership of that node |
| Chain functional spec | Ordered pipeline | End-to-end obligations; not a re-dump of every block req |
| System functional spec | Whole product | Cross-cutting (error reporting, security, ops) |

**Architecture** (graph) stays separate from **chain functional spec**
(behavioural obligations on that graph).

### Embed vs standalone requirements

**Default:** embed `requirement[]` in the container (like glossary `term[]`).  
**Promote** to shared register / standalone items only when the same
requirement is reused across many containers without copy-paste.

---

## 4. Interface control documents

### Decisions locked

- **One ICD = one directed edge** (producer → consumer), normally a structured
  payload, not a bare scalar  
- **Binding / transport is a property of the edge**, not the identity of the
  contract (socket today, SHM tomorrow, same edge)  
- Bidirectional protocols → two ICDs (or a linked pair), not one undirected doc  
- Block specs cite ICDs via `provides_icd` / `requires_icd`; ICDs cite blocks
  via `id_from` / `id_to` and recommended `from_block` / `to_block` relations  

### Required ICD fields (today)

`id_from`, `id_to`, `direction` (const `directed`), `binding`, `interaction`,
`payload`, `status`, `statement`

Optional: ports, `binding_detail`, `icd_version`, QoS, `error_model`,
`compatibility`

### Known review findings (not all applied yet)

1. Document that `id_from` / `id_to` must match block `id_block`  
2. Clarify `request_reply`: response on this ICD vs paired reverse ICD  
3. Strengthen `error_model` for IPC bindings (B8: ok means applied)  
4. Gate `accepted` status on payload completeness (`field[]` or schema uri/inline)  
5. Cite `simulated_sensor_sample_metadata` under payload / `uses_schema` examples  
6. Draft at least one real ICD instance to stress-test the schema  

Interface obligations live on ICDs; functional requirements live in specs.
Do not merge them.

---

## 5. Runtime sample metadata

Renamed from `capture_frame_metadata` → **`simulated_sensor_sample_metadata`**.

### Granularity

**One metadata document = one sensor = one sample time (`t_sim_s`).**  
Independent frame rates → independent documents. Join streams by time (and
ego/sensor ids), not by a shared global frame index.

### Contents (slimmed after review)

- Identity: `sample_id`, `t_sim_s`, optional `run_id` / `sample_index`  
- `sensor` — profile, modality, pose, boresight, image grid  
- `object[]` — ids, poses, range, bearing, COM, **modal + amodal** boxes, etc.  
- `layer[]` — paths to pixel / mask / radiance products  
- Light provenance: optional `seed`, `code_version`  

Coordinate frame ids are **not** repeated on every sample (avoids duplication).
Frame conventions are fixed in **schema prose**, citing `coordinate_frame`
`id_item` values, so LLMs still see them when reading the schema.

### Object identity

Defined in **experiment / run configuration**; sample metadata *repeats* those
ids with state at `t_sim_s`. Mask `instance_id` is a per-run raster label
mapped to `object.id` — do not treat recycled instance ids as cross-run
identity.

---

## 6. Coordinate frames

Schema: `coordinate_frame.schema.yaml`  
Instances: `coordinate_frame/*.coordinate_frame.yaml`

| `id_item` | Role |
|-----------|------|
| `wgs84_geodetic` | Lat / lon / ellipsoidal height |
| `wgs84_ecef` | Earth-centred Cartesian (m) |
| `local_ned` | Run-anchored NED — multi-platform triangulation / display |
| `sensor_package_ned` | Design optical centre; axes NED |
| `sensor_package_body` | Design optical centre; +Z boresight, +X ↑col, +Y RH |
| `fpa_principal_px` | Principal-point pixels; +X right, +Y up |
| `fpa_readout_rc` | Delivered (row, col) — used by sample metadata pixels |
| `target_ned` | Target CoM; NED |
| `target_los_motion` | Target CoM; +R LOS to ego sensor, +M across-LOS motion, +C = R×M |

**Notes:**

- `local_ned` origin is run metadata (WGS84), not per sample  
- `target_los_motion` is per-(target, sensor); +M undefined when motion is
  purely radial — consumers need an explicit fallback  
- Nominal (design) frames first; measured / calibrated frames later as new
  items, not silent mutation of these  

Sample metadata quantities: poses/velocities in **`local_ned`**; pixels in
**`fpa_readout_rc`**.

---

## 7. Sensor-sim product decisions that constrain schemas

### Architecture / runtime (questionnaire B)

- Renderer = separate process + IPC (mechanism TBD; prefer SHM, loopback OK)  
- Strict puppeting as far as possible  
- Godot now; **swappable** backends later  
- Mostly Python; C only if forced  
- Job queue + workers; **one engine session per worker**; no multi-client-per-engine  
- Renderer **not** reachable off-host  
- Failures visible; SaaS stays up; worker/engine may restart  

### Ground truth / layers (questionnaire C — locked)

**Required:** EO scene-referred radiance (multi-channel / pre-CFA oracle, not
display RGB), LWIR scene-referred field, metric depth, `instance_id`,
`class_id`, preview RGB (non-truth), target patches, simple RADAR as
range+pose from metadata.

**Deferred / omit:** normals, material ID layers, motion-vector GT, rich RADAR.

**Precision:** as-produced (no overstated formats).  
**Bulk pixels:** files on disk beside sample metadata.

### First campaign sensors

- EO: DJI O4 Air Unit Pro class (OV50H working hypothesis)  
- LWIR: Odd Systems Kurbas-640α  
- RADAR: simplified range + pose only  

Radiometry / sensor-model section (D) of the questionnaire is **not yet
answered**.

---

## 8. Candidate functional blocks (early sketch)

Not final — driven by use cases A1–A6:

1. Campaign / experiment design (space-filling vs IID vs sequential)  
2. Scenario / scene scripting (multi-ego, multi-target, multi-sensor)  
3. Renderer / geometry oracle (swappable backend)  
4. Backend IPC / worker session  
5. EO sensor model  
6. LWIR sensor model  
7. Simplified RADAR model  
8. Algorithm-under-test harness  
9. Scoring / metrics  
10. Surrogate / LUT fit (uses 1–2)  
11. Report / deliverable assembly  
12. Dataset exporter (use 3)  
13. Job orchestrator / web API (can start thin)  

Closed-loop synthetic training (use 4) deferred for detailed design.

---

## 9. Suggested schema work for next CC iteration

### High priority

1. **`architecture` schema** — blocks + edges in scope for an iteration  
2. **Harden ICD** — apply review findings; one worked example ICD  
3. **Expand `functional_requirement`** — verification method, kind
   (functional vs constraint), rationale; INCOSE/SOPHIST prose in description  
4. **`functional_chain_specification` + `system_functional_specification`** —
   same `requirement[]` pattern  
5. Continue questionnaire **D–M**; fold answers into requirements / ICDs  

### Medium priority

6. **`message_definition`** — when the same payload is cited by multiple ICDs  
7. Run / experiment configuration schema — owns object identity, `local_ned`
   origin, seeds, sensor profiles  
8. Optional thin `requirement_register` for cross-cutting system reqs only  

### Explicitly later

9. Verification plan / shared fixtures type (only when `acceptance[]` is not
   enough)  
10. Port-sheet view type (compose from ICDs)  
11. Closed-loop training controller artefacts  

---

## 10. Repo layout notes

```
cc-public/
  schema/           # type schemas (including runtime contracts)
  coordinate_frame/ # frame instances
  sensor_simulation.glossary.yaml
  simulated_sensor_sample_metadata.example.yaml

cc-dtu/             # non-PII DTU needs + skill register
cc-dtu-pii/         # member techskills + projects (not yet a git repo)
```

Schemas are untracked / evolving; do not treat this note as a released
baseline until reviewed and versioned intentionally.

---

## 11. Open questions for schema planning

1. Should chain topology live only in `architecture`, or also lightly in
   `functional_chain_specification`?  
2. When do we promote a requirement from embedded entry to standalone /
   register entry?  
3. Is `functional_requirement` ever a full CC base item, or always an entry
   `$ref`?  
4. How much QoS / security belongs on ICD vs system requirements?  
5. Run-header schema: separate type, or fields on architecture / campaign?  
6. Finish questionnaire D (radiometry) before locking EO/LWIR ICD payloads?  

---

## 12. Related files

| Path | Role |
|------|------|
| `schema/functional_block_specification.schema.yaml` | Block container |
| `schema/functional_requirement.schema.yaml` | Requirement entry |
| `schema/interface_control_document.schema.yaml` | Edge contract |
| `schema/coordinate_frame.schema.yaml` | Frame type |
| `schema/simulated_sensor_sample_metadata.schema.yaml` | Sample sidecar |
| `coordinate_frame/*.coordinate_frame.yaml` | Frame instances |
| `sensor_simulation.glossary.yaml` | Terms (incl. sample metadata) |
| `axair-geoengine-auto/SPEC_QUESTIONNAIRE.md` | Product decisions A–C locked |
