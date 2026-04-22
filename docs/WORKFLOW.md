# WORKFLOW

This document defines the operating workflow for Playtrace feature work.

The project does not treat implementation, review, and documentation as separate optional activities. They are one loop:

1. Create the spec.
2. Use the spec to develop the source code.
3. Create a pull request, wait for review, apply applicable corrections, and re-validate.
4. If implementation is complete, return to step 1 for the next scoped pass. If implementation is not complete, continue step 2 from the same spec and plan set.

## Core Rules

- No feature work starts without a written spec.
- Implementation follows the approved spec; it does not replace it.
- Plans are execution documents derived from specs.
- Review feedback is evaluated technically, then applied when correct.
- Validation is required before claiming completion.
- Completed docs are moved into `complete/` or `archive/`; they are not silently discarded.
- Scope may be migrated, unified, reformatted, or reintegrated, but it is not silently reduced under labels like "streamlined" or "optimized".

## Document Layout

### Active Design Specs

Path: `docs/superpowers/specs/`

Use this directory for current feature or recovery design documents that are still being executed or revised.

Naming convention:

- `YYYY-MM-DD-<topic>-design.md`

Purpose:

- define the goal
- lock product decisions
- declare scope and non-scope
- document architecture and invariants
- provide the basis for implementation planning

### Completed Design Specs

Path: `docs/superpowers/specs/complete/`

Move a design spec here when the scoped implementation and review loop for that pass are complete.

### Active Implementation Plans

Path: `docs/superpowers/plans/`

Use this directory for execution plans derived from approved specs.

Naming convention:

- `YYYY-MM-DD-<topic>.md`
- or `YYYY-MM-DD-<topic>-implementation.md`

Purpose:

- translate the approved spec into executable tasks
- identify touched files
- define test-first checkpoints
- sequence implementation in dependency order
- provide concrete validation commands

### Completed Implementation Plans

Path: `docs/superpowers/plans/complete/`

Move an implementation plan here when the scoped work is implemented, reviewed, validated, and no longer the active execution document.

### Deferred And Historical Notes

Paths:

- `docs/archive/notes/`
- `docs/archive/specs/`
- `docs/archive/`

Use the archive for completed or superseded material that should remain discoverable. Deferred outliers and follow-up performance notes belong in `docs/archive/notes/` until they receive a new spec pass.

## End-To-End Delivery Loop

### Phase 1: Spec

Create or update a design spec before touching behavior.

The spec should answer:

- what problem is being solved
- what stays explicitly in scope
- what is out of scope for this pass
- what invariants must survive the change
- what downstream commands or services must remain integrated

A spec is complete enough to execute when it is specific about behavior, integration points, and non-goals.

### Phase 2: Plan

Create an implementation plan from the approved spec.

The plan should include:

- file map
- task breakdown
- test-first checkpoints
- validation commands
- documentation updates required by the pass

The plan is the execution contract. If implementation reveals a real architectural gap, update the spec and then update the plan. Do not let implementation drift silently away from the design.

### Phase 3: Implement

Implement from the plan in dependency order.

Expected discipline:

- start with the failing test or failing validation where practical
- keep CLI entrypoints thin and move logic into services/domain layers
- preserve documented behavior unless an approved spec changes it
- keep documentation synchronized with the shipped behavior

### Phase 4: Validate

Validation is required before opening or updating a PR.

Validation includes, as applicable:

- targeted pytest runs for the changed subsystem
- broader focused suites for nearby integration surfaces
- full test suite
- hands-on command checks for CLI behavior
- documentation updates in `docs/VALTEST.md` when manual validation is part of the pass

Do not claim completion from static inspection alone.

### Phase 5: PR Review Loop

Open the PR only after the scoped pass is materially implemented and validated.

PR cycle:

1. Create the PR with a summary and test plan.
2. Wait for review output.
3. Review each suggestion technically.
4. Apply the applicable corrections.
5. Re-run validation.
6. Reply in-thread with the concrete fix commit when useful.
7. Resolve addressed threads.
8. Repeat until the PR is ready to merge.

External review comments are inputs to evaluate, not instructions to follow blindly. Correct feedback is implemented. Incorrect or non-applicable feedback is answered with technical reasoning.

### Phase 6: Merge And Reintegration

When the PR is complete:

- merge the PR
- sync local and remote branches
- verify the target branch state if needed
- move finished spec and plan docs into their `complete/` locations
- update shared project docs such as `docs/TODO.md`, `docs/CHANGELOG.md`, and `docs/VALTEST.md`

Then start the next scoped pass from a new or updated spec.

## Definition Of Complete

A scoped pass is complete only when all of the following are true:

- the approved spec has been implemented for the pass
- applicable review feedback has been addressed
- required tests are passing
- required hands-on validation has been recorded
- affected docs are updated
- active spec and plan docs have been moved to their completed locations, or there is an explicit reason they remain active

If any of those are false, the work returns to implementation rather than pretending to be finished.

## Project Tracking Documents

Use these documents alongside the workflow:

- `docs/TODO.md`: high-level outstanding work and completion log
- `docs/CHANGELOG.md`: shipped behavior changes
- `docs/VALTEST.md`: hands-on validation evidence
- `docs/requirements.md`: requirement-level contract
- `docs/design.md`: broader architecture and model guidance
- `docs/tasks.md`: deeper implementation task inventory where applicable

## Practical Operating Pattern

For normal feature development, the expected sequence is:

1. Write or update the spec in `docs/superpowers/specs/`.
2. Write or update the execution plan in `docs/superpowers/plans/`.
3. Implement and validate against that plan.
4. Open or update the PR.
5. Process review feedback until the PR is ready.
6. Merge and reintegrate.
7. Move completed docs into `docs/superpowers/specs/complete/` and `docs/superpowers/plans/complete/`.
8. Return to the next spec.

That is the default Playtrace development loop.
