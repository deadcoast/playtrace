# Playtrace Reconstruction and Lineage Follow-Up Design

## Goal

Finish the next recovery slice by treating improved live-data reconstruction as the dependency anchor, then deepening the `inspect`, `sources`, and `export` command surfaces on top of that repaired truth layer.

This follow-up covers two linked phases:

1. improve executable identity, canonical title selection, duplicate handling, and session reconstruction on real persisted datasets
2. upgrade `inspect`, `sources`, and `export` into richer lineage-driven command surfaces that explain repaired truth clearly

This design extends the recovered evidence-first CLI. It does not trim features, narrow the command surface, or shift Playtrace toward user-authored truth. Reconstruction remains evidence-backed first, with override surfaces kept narrow and exceptional.

## Problem Statement

The current recovery work restored the command surface and rebuilt the shared truth layer, but two follow-up gaps remain:

- real-world title and session reconstruction still needs stronger heuristics on larger live datasets
- `inspect`, `sources`, and `export` still lag behind the stronger visual and explanatory quality of `scan`, `me`, `report`, and `doctor`

These two problems are coupled. Improving command visuals before repairing truth would only make unstable results look more polished. The correct order is:

1. repair the underlying reconstruction path
2. expose that repaired lineage through stronger inspection and export surfaces

## Product Decisions

The following design decisions were established during approval:

- this work is captured as one combined spec, not two separate specs
- phase 1 is truth-first: executable/title identity and session reconstruction come before visual upgrades
- the first dependency-critical variable to correct is executable/title identity resolution
- improved heuristics must support rebuilding existing databases, not just future scans
- rebuilds happen only through explicit user actions
- both `scan --rebuild` and `doctor --repair` are first-class repair surfaces with distinct UX roles
- rebuild mutation requires preview first and an explicit `--yes`
- rebuilds may replace derived state in place as long as output shows exactly what changed
- Playtrace remains evidence-first; it should discover truth rather than depend on manual mappings for normal correctness
- `map` remains an expert override or exception surface, not the primary way the application becomes correct

## Design Principles

### 1. Truth Before Presentation

Command polish must follow truth repair, not substitute for it.

### 2. Evidence First

Executable identity, titles, sessions, duplicates, and confidence are derived from persisted evidence. The system should improve inference quality rather than shifting responsibility onto the user.

### 3. Explicit Mutation Only

Repair flows must preview planned changes and mutate only when the user passes `--yes`.

### 4. Rebuildability Is the Contract

Derived truth remains rebuildable from persisted evidence plus narrow override surfaces. Existing databases must be correctable through explicit rebuilds.

### 5. Lineage Must Be Explainable

When Playtrace resolves a title or session, the system should be able to explain why that result won and where uncertainty remains.

### 6. Unknown Beats Fake Precision

If evidence is weak or conflicting, the system should retain explicit ambiguous or unknown states instead of inventing certainty.

## Scope

### In Scope

- evidence ranking improvements for live data
- stronger executable identity resolution
- stronger canonical title selection
- duplicate grouping improvements
- stronger session reconstruction based on repaired identities
- explicit rebuild preview and apply flows
- `scan --rebuild`
- `doctor --repair`
- lineage-driven upgrades for `inspect`
- lineage-driven upgrades for `sources`
- richer, truthful export views for repaired lineage and repair diffs
- hands-on validation updates in `docs/VALTEST.md`

### Out of Scope

- replacing the current command surface with a reduced set of commands
- silent automatic rebuilds on open or read paths
- introducing a new primary truth source outside persisted evidence
- treating manual mappings as the main correctness path

## Architecture

The combined follow-up should be organized around one repaired truth pipeline and three richer command surfaces.

### Evidence Ranking Layer

This layer scores conflicting signals from artifacts, metadata, launcher relationships, paths, hashes, and repeated observations so later stages consume weighted evidence instead of flat records.

### Executable Identity Resolver

This component produces stable executable identities first. It is the dependency anchor for canonical title selection, duplicate handling, session rebuilding, and lineage views.

### Canonical Title Resolver

This component chooses the best title per executable group, preserves alternate observed labels, detects duplicate candidate groups, and records why the canonical title won.

### Session Rebuilder

This component reconstructs sessions from repaired executable and title identities rather than merging weak title strings directly.

### Rebuild Planner and Applier

This shared pipeline powers both `scan --rebuild` and `doctor --repair`. It computes the planned mutations first, renders an explicit diff, and mutates derived state only when `--yes` is present.

### Lineage Snapshot Layer

This layer builds shared truth-backed inspection views for:

- `inspect`
- `sources`
- `export`

It should explain where titles, sessions, confidence, duplicates, and unresolved gaps came from.

### Visual Render Layer

This layer upgrades `inspect`, `sources`, and `export` after the truth layer is repaired, using shared lineage and remediation data instead of bespoke per-command presentation logic.

## Data Flow

1. Raw evidence remains the immutable base.
   Collectors and parsed evidence stay persisted as the source material. This design improves how evidence is ranked and reconstructed, not where truth originates.

2. Identity resolution runs before title and session logic.
   Evidence records are grouped into executable candidates using normalized path, hash, metadata, launcher relationships, filename patterns, and repeated co-occurrence.

3. Canonical title resolution runs on top of executable identity.
   Each executable group gets a canonical title, alternate observed labels, evidence reasons, confidence, and duplicate-candidate relationships.

4. Session reconstruction runs from repaired identities rather than raw names.
   Session rebuilding should merge activity windows based on executable identity, title lineage, source timing, and launcher-child continuity.

5. Rebuild preview is a first-class stage.
   `scan --rebuild` and `doctor --repair` both compute the proposed rebuilt state, diff it against current stored derived state, and render exactly what would change.

6. Rebuild apply is in-place, but auditable in output.
   When confirmed, the rebuild replaces derived executable, title, and session state in place and renders what changed and what remains unresolved.

7. `inspect`, `sources`, and `export` read from the same repaired lineage layer.
   They should expose why a title resolved the way it did, which evidence supported it, where ambiguity remains, and what changed after rebuild.

## Repair Surfaces

The rebuild UX should be one shared pipeline exposed through two distinct commands.

### `playtrace scan --rebuild`

This is the operational repair surface. Use it when the user wants to re-run collection and then rebuild truth from the latest persisted evidence.

It should feel like a pipeline command:

- collect
- rank and reconstruct
- preview planned mutations
- apply only with `--yes`

### `playtrace doctor --repair`

This is the diagnostic repair surface. Use it when the user wants the system to explain what is wrong first, then offer a repair plan.

It should feel like:

- audit findings
- repair candidates
- projected improvements
- apply only with `--yes`

### Shared Repair Contract

- no silent mutation
- preview first
- `--yes` required for mutation
- in-place replacement of derived state is allowed
- output must show exactly what changed
- unresolved issues remain visible after rebuild if evidence stays weak

### Preview Metrics

The preview should quantify:

- executable identities merged or split
- canonical titles changed
- duplicate candidate groups removed, added, or still remaining
- sessions merged, split, added, or removed
- confidence increases or decreases
- evidence still unresolved after repair

## Heuristic Components

Phase 1 should define a bounded set of heuristic improvements rather than one vague “better reconstruction” bucket.

### 1. Executable Identity Scoring

Inputs should include:

- canonical path
- hash
- filename
- PE metadata
- signer
- launcher linkage
- install-root proximity
- repeated co-occurrence across scans

The output should be a scored identity candidate rather than a binary first-match decision.

### 2. Evidence Ranking

Evidence sources should not be treated equally.

The ranking model should distinguish between stronger signals such as canonical path, stable hash, signed metadata, and launcher-child relationships, and weaker signals such as noisy display strings or single-source loose matches.

### 3. Canonical Title Selection

Title choice should prefer evidence-backed canonical labels over whichever string appeared first. Alternate observed labels should be preserved so duplicates and ambiguity can be explained later.

### 4. Duplicate Grouping

Duplicate detection should go beyond surface string similarity alone and consider shared executable lineage, metadata similarity, path neighborhoods, launcher ancestry, and evidence overlap.

### 5. Session Reconstruction

Session merging should use repaired executable and title identity, source confidence, timing adjacency, and launcher-child continuity so fragmented or wrongly split sessions improve from the same repaired truth base.

### 6. Confidence Explanation

Every rebuilt title and session should be explainable in terms of why it resolved that way. Default views do not need to dump internals, but the lineage layer must carry enough structure to explain confidence and ambiguity.

### 7. Residual Ambiguity Handling

The system should keep explicit unknown or ambiguous states when evidence is not strong enough. It should not force a false precise answer just to look complete.

## Command Surfaces

Phase 2 should deepen `inspect`, `sources`, and `export` into truth-explaining tools with a stronger visual language, not merely prettier tables.

### `playtrace inspect`

`inspect` should become the primary lineage view for one resolved target.

It should show:

- resolved canonical title and classification
- executable identity summary
- confidence and why
- alternate observed titles
- launcher relationship when present
- source contributions
- session summary for that target
- duplicate suspicion or ambiguity when present
- remediation cues when evidence is weak

Visually, it should feel like a focused diagnostic dossier rather than a raw field dump.

### `playtrace sources`

`sources` should explain provenance clearly.

It should show:

- which sources observed the target
- what each source contributed
- timestamp coverage
- evidence strength per source
- missing or blocked sources when relevant
- conflicts between sources when present

Visually, it should behave like an evidence ledger with strong sectioning and readable comparison rather than a linear printout.

### `playtrace export`

`export` should remain machine-usable, but grounded in the richer lineage model.

It should support exporting:

- resolved entity view
- source lineage view
- repair preview diff
- repair result diff
- ambiguity and duplicate metadata where relevant

The default export contract should stay deterministic and truthful.

### Shared Visual Direction

The visual work should:

- use stronger headers and section hierarchy
- make confidence, ambiguity, duplicate suspicion, and unresolved evidence immediately visible
- preserve explicit unknown states
- stay ASCII-safe and terminal-first
- remain visually consistent with the stronger `scan`, `me`, `report`, and `doctor` surfaces already recovered

## Error Handling

- weak evidence should produce explicit ambiguous or unknown states rather than silent fallbacks or fake certainty
- rebuild preview failures must fail without mutating anything
- `scan --rebuild` and `doctor --repair` without `--yes` must never mutate the database
- if the rebuild planner detects no meaningful changes, the command should say so explicitly
- if a repair would reduce confidence or introduce new ambiguity, the preview should surface that clearly
- if a requested target for `inspect` or `sources` cannot be resolved, output should explain whether it is missing, ambiguous, or blocked by weak evidence
- export should fail clearly on unsupported format or serialization problems and must never imply unresolved truth is resolved

## Testing Strategy

This follow-up needs reconstruction tests and end-to-end command tests.

### Heuristic Tests

Cover:

- evidence ranking
- identity resolution
- canonical title selection
- duplicate grouping
- session rebuild behavior on realistic mixed-source fixtures

### Rebuild Tests

Cover:

- preview-only behavior
- `--yes` mutation behavior
- in-place replacement
- no-op rebuilds
- before and after diff summaries

### Command Behavior Tests

Cover:

- `scan --rebuild`
- `doctor --repair`
- `inspect`
- `sources`
- `export`

against both repaired truth and ambiguous truth.

### Live-Like Regression Fixtures

Add fixtures that reflect the actual bad cases this follow-up is meant to fix:

- duplicate titles
- split sessions
- launcher misattribution
- weak metadata
- partial-source coverage

### Hands-On Validation

Extend `docs/VALTEST.md` with dedicated validation for:

- rebuild preview
- rebuild apply with `--yes`
- before and after database truth changes
- improved `inspect`
- improved `sources`
- improved `export`

## Implementation Order

The implementation order should follow dependency boundaries:

1. evidence ranking inputs and scoring model
2. executable identity resolution improvements
3. canonical title selection and duplicate grouping improvements
4. session reconstruction improvements
5. shared rebuild planner, diff model, and applier
6. `scan --rebuild`
7. `doctor --repair`
8. lineage snapshot model enhancements
9. `inspect` visual and lineage upgrade
10. `sources` visual and lineage upgrade
11. `export` lineage and diff export upgrades
12. live validation updates and documentation

## Risks and Constraints

- aggressive heuristic changes can improve one dataset while regressing another unless fixtures reflect real mixed-source cases
- in-place rebuilds can erode trust if before and after diffs are weak
- duplicate reduction must not collapse distinct executables into one title just because names are similar
- stronger lineage views must not become unreadable dumps; they need hierarchy and prioritization
- explicit override surfaces must remain narrow so the product stays evidence-first in normal operation

## Outcome

When this follow-up is complete, Playtrace should:

- resolve executable and title identity more accurately on live datasets
- rebuild existing databases through explicit, auditable repair flows
- improve session reconstruction from repaired identity rather than weak title strings
- explain reconstructed truth and ambiguity more clearly
- present `inspect`, `sources`, and `export` at the same quality bar as the rest of the recovered CLI
