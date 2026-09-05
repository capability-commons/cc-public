# Implementation brief: self-hosted software assurance for cctool

## Mandate

Use cctool itself as the first system of interest for developing Capability
Commons' software requirements, implementation traceability, verification
evidence, linting, checking and architectural-review capabilities.

Implement this incrementally, with coherent design decisions and regression
tests at each stage. Preserve the repository's established conventions and
fail-closed trust model.

Where these instructions conflict with a better-supported existing design
decision or prior discussion, make the judgement call, record the reasoning in
a DDR, and preserve the intended outcome rather than mechanically following the
proposed mechanism.

## Intended outcome

Capability Commons shall provide current, navigable and enforceable assurance
from requirement to code to evidence.

For an accepted low-level cctool requirement, an engineer or automated agent
shall be able to determine:

- why the requirement exists;
- the need or higher-level requirement from which it derives;
- which package, module, class or function is responsible for implementing it;
- which test, inspection, demonstration or analysis is intended to verify it;
- whether that verification has passed against the applicable implementation;
- whether the implementation or verification evidence is stale;
- which architectural policies govern the implementation;
- whether any current findings or accepted waivers apply.

From a source element, an engineer or agent shall be able to determine:

- which requirements it implements;
- which verification cases exercise those requirements;
- which assurance may be affected by changing it;
- which architectural constraints apply to it;
- whether its latest required verification evidence remains current.

The resulting mechanisms must be general enough to use in other projects, but
they should be designed and validated against the real source, requirements and
tests of cctool.

## Architectural invariants

Preserve these distinctions throughout the work.

### Intention, implementation and evidence are different

A requirement states intended behaviour.

An implementation link identifies source responsibility. It does not prove
that the requirement is met.

A verification declaration says what test, inspection, demonstration or
analysis is intended to verify the requirement.

A verification result is evidence from a particular observation. The
existence of a test or relation is not itself evidence that the test passed.

### Authored, derived and observed data are different

Authored repository data includes:

- needs and requirements;
- derivation links;
- implementation responsibility;
- verification intent;
- architecture policies;
- design decisions and waivers.

Derived information includes:

- source containment;
- imports and dependencies;
- reverse traceability;
- impact sets;
- test discovery;
- evidence freshness.

Do not require authors to maintain volatile derived graphs manually.

Observed information includes:

- test results;
- lint and check findings;
- architecture findings;
- review results;
- execution environment and revision.

Give observed information an explicit lifetime and freshness model.

### Deterministic and probabilistic assurance remain separate

Mechanical checks, lint and test-run facts must not be conflated with model
judgements.

Severity says what follows from a finding, not how the finding was produced or
how certain it is.

A model-based architectural review must initially be advisory. It must not
become blocking until its criteria, controls, confidence and admission policy
justify that authority.

### Source is inspected statically

Continue using Python's AST. Do not import application modules merely to
discover their definitions, identities or dependencies.

### Traceability is many-to-many

Do not assume:

- one requirement per function;
- one function per requirement;
- one test per requirement;
- or one requirement per test.

Use the narrowest stable implementation target, not the narrowest possible
target. A module or class is preferable where behaviour is distributed across
volatile helpers.

### Function and class items remain optional

Every package and module may remain identifiable as currently designed. Only
add a class, method or function data item when another item needs to name it.

Do not introduce metadata for every private helper merely to maximize apparent
coverage.

### The query and checking logic must not live in the CLI

Build a render-neutral application/query layer used by both checks and CLI
presentation. The future UI must be able to consume the same projections
without parsing console output or calling private checker internals.

## Decisions to make and record first

Before implementing the associated behaviour, settle these matters in one or
more focused DDRs.

### 1. Meaning of implementation traceability

The recommended initial design is to generalize r_is_implemented_by.

Permit a textual requirement, as well as a component, to point to a Python
source item. Initially constrain its domain and range approximately as follows:

- Domain:
  - t_textual_requirement
  - t_component
- Range:
  - t_python_package
  - t_python_module
  - t_python_class
  - t_python_function

Revise the relation description so it applies coherently to both requirements
and components.

The edge should remain outgoing from the requirement or component:

~~~text
requirement --r_is_implemented_by--> source item
~~~

This expresses implementation responsibility. It must not imply successful
verification.

If an allocation relation between requirement and logical component is already
clearly justified, it may also be introduced:

~~~text
requirement -> allocated to component -> implemented by source
~~~

Do not make that extra indirection mandatory for the first tranche.

### 2. Requirement maturity

Define lifecycle-dependent conformity rather than making every field
unconditionally required in JSON Schema.

Recommended semantics:

- proposed
  - may be incomplete while being authored;
  - must still be structurally valid;
  - gaps are visible but generally advisory.
- accepted
  - must have a valid derivation;
  - must have explicit success criteria;
  - must declare a verification method;
  - must have an appropriate realization path;
  - must have the required verification declaration;
  - must have no unresolved critical assurance finding.
- deprecated
  - must retain enough rationale and traceability to explain its history;
  - should identify a replacement where one exists.

Define a leaf requirement as an accepted requirement from which no lower-level
requirement derives in the applicable closed world.

For cctool, an accepted leaf software requirement should have at least one
valid implementation target. A higher-level requirement may instead be
realized through derived child requirements.

Do not silently infer local applicability from a directory name. If the leaf
rule cannot be safely generalized to federated or non-software requirements,
introduce the smallest explicit applicability mechanism or scope the rule to an
assurance profile. Record the decision.

### 3. Verification declarations and evidence

Retain r_verifies for the claim that a test source item verifies a requirement:

~~~text
test module/function --r_verifies--> requirement
~~~

Prefer individual test-function items where the claim belongs to a specific
test. Module-level declarations may remain where a module genuinely provides
the relevant verification as a whole.

Design a separate representation for verification evidence. It must support:

- test;
- inspection;
- demonstration;
- analysis.

Decide whether durable evidence is:

- a repository data item;
- a Git- or CI-attached attestation;
- or an external artifact with a repository-addressable identity.

If evidence is stored in the repository after the execution it describes,
avoid the self-reference problem by binding freshness to relevant content
digests rather than simply requiring the evidence to name the current HEAD.

### 4. Evidence freshness

Specify exactly what makes verification evidence current.

At minimum, consider changes to:

- the requirement statement;
- its success criteria;
- the implementation source elements;
- the verification test or procedure;
- relevant parameters and fixtures;
- the verification runner or configuration.

Unrelated documentation changes and the addition of an evidence record should
not automatically invalidate otherwise applicable evidence.

For clean merge or release evidence, retain the Git revision as provenance even
if content digests determine applicability.

### 5. Architecture policy and enforcement profiles

Decide how architecture policies are represented as data and how they select
source scope.

Separately define development, merge and release assurance profiles. Do not
make one gate serve every stage by accident.

## Phase 1: implementation and verification intent

### Shared trace projection

Introduce a domain/application service that calculates a requirement assurance
projection from the already-loaded repository context.

It should not print, exit, invoke Click or mutate the tree.

For each requirement, return at least:

- readable ID and GUID;
- lifecycle status;
- derivation targets;
- derived child requirements;
- whether it is a leaf in the applicable world;
- implementation source targets;
- verification method;
- verifying source targets;
- success criteria presence;
- current gaps;
- later, verification evidence and freshness.

It should support reverse lookup from a source ID or GUID to affected
requirements and verification declarations.

Use GUIDs as durable identity and readable IDs for presentation.

Both the trace checker and CLI query must consume this shared model. Do not
independently reimplement graph traversal in each.

### Relation constraints

Add domain/range constraints for the selected implementation relation.

Regression tests must prove that:

- a requirement can point to a module, class or function;
- a component can retain its existing source implementation relation;
- invalid subjects are rejected;
- non-source targets are rejected;
- readable-ID changes do not alter the GUID relationship;
- multiple implementation targets are supported.

### Lifecycle checking

Extend or decompose the current trace check to report at least:

- accepted requirement with no valid derivation;
- accepted leaf requirement with no required implementation target;
- accepted verification:test requirement with no verifying test source;
- invalid or missing verification for other declared methods;
- proposed requirement gaps as advisories where useful;
- incomplete analysis as an error, preserving fail-closed behaviour.

Closed-world status matters for determining whether children or implementation
targets are absent. Do not convert a federated boundary into a false critical
finding.

Initially run newly introduced maturity findings as advisories while the
existing corpus is migrated and reviewed. Promote each rule deliberately after
its controls pass and affected requirements conform.

### Read-only trace command

Add a read-only CLI query, tentatively cctool trace or cctool requirements.

It should support:

- selecting a requirement by ID or GUID;
- selecting a source item by ID or GUID for reverse impact;
- listing gaps;
- human-readable output;
- at least one stable machine-readable format, preferably JSON;
- deterministic ordering;
- an explicit closed-world option where its conclusions require one.

The output must distinguish:

- missing authored traceability;
- unresolved references;
- stale evidence;
- analysis failure;
- and analysis not performed.

Do not make the CLI output structure the domain model.

## Phase 2: dogfood the existing requirements

Migrate and mature the existing cctool requirements one at a time. Do not
blanket-promote all requirements to accepted.

Use this order because it progressively increases assurance difficulty:

1. req_printer_idempotent
2. req_checker_locates_each_finding
3. req_renamer_keeps_guid
4. req_judge_confirms_unmet
5. req_judge_reports_confirmed_verdict
6. req_executor_honours_budget
7. req_committer_writes_record

For each requirement:

1. Review the statement and success criteria against actual intended
   behaviour.
2. Confirm or correct its derivation.
3. Identify implementation responsibility at the narrowest stable
   granularity.
4. Add source data items only where required for addressability.
5. Identify the exact verification functions or procedures.
6. Replace overly broad module-level r_verifies declarations where exact
   function-level ownership is appropriate.
7. Add or strengthen regression tests.
8. Demonstrate the complete projection through the trace query.
9. Promote the requirement only when its declared assurance is actually
   present.

Candidate initial mappings include:

- Printer idempotence:
  - implementation around cc_public.layout;
  - verification around test_printer_preserves_and_is_fixpoint.
- Rename preserves GUID:
  - implementation around cc_public.edit.rename;
  - verification around
    test_rename_carries_to_qualified_items_references_and_file.
- Judge confirmation:
  - implementation around cc_public.eval.runner;
  - verification around
    test_an_unmet_screen_is_confirmed_count_times_and_the_majority_reported.
- Executor budget:
  - implementation around cc_public.workflow.run;
  - verification around
    test_back_edge_is_exhausted_when_the_budget_is_spent.

Treat these only as starting hypotheses. Inspect actual responsibility before
adding links.

The inspection-based commit requirement is deliberately important: it must
exercise non-pytest verification evidence rather than being forced into an
artificial test relation.

## Phase 3: verification evidence

### Test-function identity

Use existing Python function source items as the first verification-case
identities.

A renamed or moved test may receive a changed readable ID while retaining its
GUID where it remains the same conceptual test.

Support parameterized tests explicitly:

- the source function GUID identifies the verification procedure;
- the runner's case/node identity distinguishes collected parameter instances;
- a policy determines whether all collected cases must pass;
- zero collected cases must not be reported as successful evidence.

Define outcomes at least for:

- passed;
- failed;
- error;
- skipped;
- not run.

Handle expected failures and unexpected passes deliberately rather than
allowing runner-specific terminology to leak into assurance semantics without
a decision.

### Pytest adapter

Integrate pytest without making it a core dependency of mechanical repository
checking.

Acceptable approaches include:

- a lightweight optional pytest plugin;
- ingestion of JUnit XML plus a deterministic source mapping;
- a dedicated optional adapter package or module.

The adapter must associate results with stable test-function GUIDs and the
requirements those functions claim to verify.

Do not infer verification merely from coverage.

### Generic verification evidence

Define a common evidence shape capable of representing test, inspection,
demonstration and analysis.

Capture at least:

- evidence identity;
- verification method;
- subject requirement GUID;
- verification case or procedure identity;
- outcome;
- observed revision;
- relevant content digests;
- runner/tool and version;
- time;
- environment details sufficient to interpret the result;
- optional duration and supporting artifact location;
- reason for failure, error or skip.

Inspection evidence must identify the inspector or tool and the inspected
criterion. It must not be represented as a passing test merely for convenience.

### Freshness check

Add a deterministic check that reports whether required evidence remains
applicable.

Test these cases:

- implementation source changes;
- test source changes;
- requirement statement changes;
- success criteria change;
- runner or relevant configuration changes;
- unrelated file changes;
- evidence-only commit;
- renamed readable IDs with unchanged GUIDs;
- partial or failed evidence ingestion;
- dirty working-tree evidence versus clean revision evidence.

Malformed evidence or failure to calculate freshness must be an analysis error,
not a clean result.

## Phase 4: impact analysis

Extend the trace service and CLI so that a source change can be mapped back to
potentially affected assurance.

Support:

- direct source item to implementing requirements;
- requirement to verifying cases;
- source item to relevant architecture policies;
- changed files or definitions since a Git reference;
- conservative module-level impact where exact definition spans cannot be
  proven.

The report should say potentially affected rather than claim semantic impact
from a static relationship alone.

Do not manually store call graphs or import edges merely to support this query.

## Phase 5: static architecture analysis

### Static source index

Build a read-only AST-derived index containing, as needed:

- packages and modules;
- classes, functions and methods;
- containment;
- imports and relative imports;
- aliases;
- public and private names;
- source locations;
- source-item GUIDs where declared;
- test discovery metadata.

Reuse parsing work where practical. Do not import modules.

Keep this index separate from authored repository data. It may be cached later,
but correctness must not depend on a cache.

### Architecture policy as data

Introduce the smallest useful architecture-policy item or register structure.

It should be able to express:

- named source scopes or layers;
- permitted and forbidden dependency directions;
- forbidden cycles;
- cross-package private-access rules;
- isolation of optional dependencies;
- rule severity;
- an explicit rule identity suitable for findings and waivers.

Before encoding the cctool policy, write a design decision describing the
desired architecture. Do not treat the current import graph as the desired
design by default.

Initial candidate rules are:

1. Core packages do not depend on cc_public.cli.
2. Mechanical checking does not depend on DSPy or provider-specific model
   code.
3. Cross-package access to private names is forbidden.
4. Package dependency cycles are forbidden.
5. Git, model-provider and pytest/Ruff integration remain behind explicit
   adapters or application boundaries.
6. CLI functions adapt arguments and render results rather than owning domain
   policy.

Begin with rules that can be detected reliably. Report unsupported
dynamic-import cases as limitations rather than pretending the graph is
complete.

### Architecture findings

Every architectural finding should include:

- stable rule identity;
- subject source identity where available;
- filepath and source anchor;
- severity;
- observed dependency or violation;
- applicable policy;
- concise remediation context.

Start new rules in report-only or advisory mode. Promote them only after
fixtures, corpus review and regression tests demonstrate acceptable behaviour.

## Phase 6: unified assurance reporting and gates

Do not force every tool result into one undifferentiated finding type.

Use a common outer analysis envelope while preserving distinct payloads:

- mechanical nonconformities;
- lint findings;
- verification results;
- architecture findings;
- semantic review findings;
- analysis errors;
- not-run state.

The outer envelope should identify:

- tool and version;
- analysis kind;
- scope;
- revision or working-tree identity;
- completed, failed or not-run status;
- counts;
- findings or results;
- errors;
- timing where useful.

Where practical, adapt:

- the current cctool check report;
- Ruff's machine-readable output;
- pytest evidence;
- architecture analysis.

Do not duplicate Ruff's style rules inside cctool.

### Development profile

Fast and structural:

- parse and load;
- identity and reference;
- relation and schema;
- layout;
- source identity placement;
- lint;
- basic trace structure.

Stale test evidence should not make ordinary in-progress editing impossible.

### Merge profile

Require:

- closed-world mechanical conformity;
- lint;
- complete tests;
- coverage floor;
- accepted requirement maturity;
- implementation and verification trace;
- current evidence for changed accepted requirements, according to policy;
- enforced architecture rules;
- no unexplained blocking waiver or analysis failure.

### Release profile

Additionally require:

- source and wheel builds;
- clean installation and command smoke tests;
- supported-platform results;
- required inspection, demonstration and analysis evidence;
- semantic-evaluation admission policy where used;
- release-revision architectural review;
- no incomplete or exhausted run represented as success.

Preserve the current distinction between a report command and a gate command
that fails the process.

## Phase 7: architectural review and waivers

### Review records

Introduce a durable review representation only after its purpose and lifecycle
are clear.

A review should identify:

- reviewed Git revision or relevant content digests;
- source and requirement scope;
- applicable architecture policy;
- reviewer identity or tool/model;
- review method and criteria;
- findings;
- disposition;
- whether the review remains current.

A model-generated review is advisory until its evals and admission policy
justify more authority.

### Waivers

A waiver should be an explicit, reviewable authored fact rather than a comment
or ignored rule.

It should name:

- rule;
- subject or scope;
- rationale;
- approving authority;
- creation revision or date;
- expiry or review condition;
- content digest or other staleness boundary.

Do not persist every transient lint or architecture finding as a data item.
Persist deliberate exceptions and review records.

## Self-hosting and circular trust

Do not let a new checker certify itself merely because it says it passes.

For each new assurance rule:

1. State the requirement and success criteria.
2. Create independent positive and negative fixtures.
3. Implement the rule.
4. Run it in report-only mode.
5. Manually compare its findings with the actual corpus.
6. Add control cases for false findings and missed findings.
7. Make it advisory.
8. Promote it to critical only after its behaviour is established.

The initial external trust base includes:

- Git;
- Python parsing and runtime;
- pytest;
- Ruff;
- JSON Schema validation;
- operating-system filesystem semantics;
- independently curated fixture repositories.

Where valuable, add:

- property-based tests for graph transformations and rename behaviour;
- failure injection around atomic editing and Git;
- selective mutation testing for critical verification claims.

Mutation score should initially be an investigative signal, not a universal
gate.

## Required regression coverage

At minimum, cover the following.

### Traceability

- many requirements to one source;
- one requirement to many sources;
- one test to many requirements;
- one requirement to many tests;
- function, method, class and module implementation targets;
- stable GUID through readable-ID rename;
- missing and mistyped implementation target;
- open-world versus closed-world conclusions;
- proposed versus accepted lifecycle findings;
- high-level requirement with children versus leaf requirement.

### Source indexing

- nested classes and methods;
- async functions;
- decorators;
- aliases;
- relative imports;
- multiple imports on one line;
- type-checking-only imports;
- syntax failure;
- optional metadata;
- source identifier inconsistent with AST location.

### Verification

- pass, fail, error, skip and not-run;
- parameterized tests;
- no collected tests;
- one failed case among passing parameterized cases;
- malformed result data;
- stale requirement;
- stale source;
- stale test;
- unrelated change;
- inspection evidence.

### Architecture

- allowed dependency;
- forbidden dependency;
- cycle;
- cross-package private import;
- qualified private attribute access;
- optional dependency leaking into the mechanical core;
- ambiguous or unsupported dynamic import;
- waiver applying to exactly its declared subject and rule;
- expired or stale waiver.

### Reporting and failure behaviour

- deterministic ordering;
- JSON round-trip or schema validation;
- analysis exception remains distinct from a finding;
- not-run remains distinct from pass;
- malformed policy fails closed;
- report-only command does not mutate;
- gate exit status corresponds to policy;
- text rendering does not determine machine semantics.

## Definition of completion

This tranche is complete when:

1. Every existing accepted cctool leaf requirement has valid derivation,
   implementation responsibility, verification intent and current required
   evidence.
2. Existing proposed requirements have their gaps reported accurately and have
   been reviewed individually rather than automatically accepted.
3. Requirement-to-source and source-to-requirement queries work through a
   shared application layer.
4. Individual test functions can carry stable verification claims.
5. Verification results are distinct from verification declarations and have
   a tested freshness model.
6. Test, inspection, demonstration and analysis can all be represented
   honestly.
7. The initial cctool architecture is recorded as a decision and checked
   mechanically where practical.
8. Lint, mechanical checks, verification and architecture results can be
   consumed through a coherent machine-readable assurance report without
   losing their distinct meanings.
9. Development, merge and release policies are distinct.
10. Every new blocking rule has positive, negative and regression controls.
11. The normal gate passes with no regression in test count, coverage or lint.
12. CI builds and tests the package from a clean environment on the declared
    platforms.
13. The working tree is clean and the implementation is delivered as a
    comprehensible series of commits.

## Explicit non-goals for this tranche

Do not build:

- the HTMX or other end-user UI;
- a requirement for every function;
- a manually maintained import or call graph;
- a general multi-language source-analysis framework;
- automatic acceptance of requirements;
- automatic suppression of findings;
- a model reviewer with commit-blocking authority before measurement;
- a replacement for Ruff or pytest;
- a large server or database merely to support queries;
- a universal federation solution.

Produce render-neutral projections and stable machine-readable results so
those capabilities can be built later.

## Expected handback

At completion, report:

- design decisions made and open questions answered;
- any deliberate departure from this brief;
- data types, relations and checks introduced or changed;
- requirements promoted to accepted and why;
- traceability coverage for the existing cctool requirements;
- verification-evidence and freshness semantics;
- architecture policy and enforced rules;
- development, merge and release gate behaviour;
- tests, coverage, lint and mechanical-check results;
- CI and build results;
- remaining advisories, waivers and deferred work;
- commit list and confirmation that the tree is clean.
