# SmactorIO retirement and pattern-extraction boundary

Status: current boundary note
Date: 2026-05-15
Scope: documentation only; no retired same-name project content is imported here.

## Canonical source of truth

SmactorIO now means the simple Project OS / Signal Hub operating loop being built in this repository.

Signal Hub is the LAN-only cockpit and evidence surface for that Project OS. Its active roadmap inputs are repo-local, explicit, and test-protected.

## Retired same-name project boundary

The earlier same-name project is retired and non-canonical.

Name reuse does not import that project's roadmap, product direction, source tree, generated specs, policy catalog, implementation assumptions, open issues, branches, or GitHub history.

A future extraction from retired material is allowed only when Leon explicitly names a pattern to extract. The extraction must produce an abstract mechanism for the new Project OS, not copied content or a new default source.

## Reusable patterns extracted as abstractions

The retired checkout inspection produced these reusable abstractions only:

1. Persistent Project OS ledgers
   - Keep compact machine-readable state for priorities, blockers, decisions, escalations, and queued work.
   - New implementation target: SQLite/state JSON that backs the LAN pages.

2. Explicit finite-state orchestration
   - Keep typed states, transition evidence, retry/blocker counters, and terminal verification.
   - New implementation target: the existing Signal Hub FSM runner and public proof pages.

3. Centralized artifact writing
   - Keep one write path for generated artifacts with dry-run support, metadata, hash proof, rollback/backup, and path containment.
   - New implementation target: page builders, runtime backups, and deployment validation.

4. Schema-first model/tool boundaries
   - Keep structured outputs, validation, fallback handling, redaction, and budget/cost guards.
   - New implementation target: internal signal extraction, capsule validation, and future LLM-backed actions.

5. Playbooks as data
   - Keep repeatable playbooks with triggers, prechecks, execution steps, validation, rollback, and command allowlists.
   - New implementation target: safe low-risk Project OS actions.

6. Capability registries
   - Keep named capabilities, typed parameters, duplicate detection, lifecycle/status tracking, and safe execution wrappers.
   - New implementation target: sources, actions, tools, and agents in the Signal Hub database.

7. Lightweight observability
   - Keep counters, timing, cache/circuit-breaker state, and per-provider cost tracking when model calls are introduced.
   - New implementation target: FSM run summaries and public proof metrics.

8. Spec/plan/task template discipline
   - Keep small independently verifiable slices, prerequisites, success criteria, task dependencies, and verification checklists.
   - New implementation target: repo-local plans, tests, and project pages.

## Material not carried forward

Do not carry forward retired project domain content, old roadmap items, old generated specs, old package/CLI identity, old GitHub issues/PRs, old branches, old dependency stack, or old public-facing claims.

Do not create Signal Hub source candidates, roadmap records, public pages, or work capsules from retired material unless Leon explicitly names a pattern extraction and approves the new canonical artifact.

## Future named pattern extraction protocol

1. State the exact pattern being evaluated.
2. Inspect retired material read-only.
3. Extract the mechanism in new plain language.
4. Write the result as a new canonical repo-local artifact.
5. Add or update tests if the mechanism affects ingestion, state, public pages, or automation.
6. Verify public/state/DB outputs contain no retired-source markers.

## Quarantine rules

Retired material must not be added to:

- roadmap default sources;
- source cache entries;
- roadmap goal records;
- source candidates;
- project homepage data;
- public HTML;
- internal work capsule source hints.

Allowed mentions are limited to quarantine/blocklist code, tests that enforce the boundary, investigation evidence, and this boundary note.

## Current verification evidence

As of this note:

- Roadmap ingestion default sources are repo-local only.
- Regression tests reject the retired checkout path and retired source markers.
- Active local and production state files contain no retired-source marker hits.
- Active local and production SQLite marker scans returned zero active hits.
- Production LAN pages returned HTTP 200 with zero retired-source marker hits.
