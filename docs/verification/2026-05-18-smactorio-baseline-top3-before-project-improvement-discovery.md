# Baseline top 3 SmactorIO improvements before project-improvement discovery implementation

Purpose: quick manual/reference estimate before implementing the refreshed project-model + discovery/research/modeling Project Improvement System. The finished system should be compared against this list; it should be able to discover equal-or-better fresh candidates from the project model, prior-improvement register, docs/code/issues, and current north star without relying on these hand-written items.

## 1. Make project-improvement lanes non-blocking unless `blocking=true`

Likely issue title: `fix(signal-hub): make project-improvement lanes non-blocking unless blocking=true`

Why now: the generic project-improvement processor must return per-project statuses. The current operating loop has legacy coupling that can block the whole loop on project-lane blocked/degraded/locked outcomes, even when dashboard/brief refresh should continue.

Value: keeps the LAN dashboard and daily brief alive during one-project failures, makes migration to the project-agnostic system safer, and prevents confusing whole-service blocked states when GitHub issue/PR work succeeded elsewhere.

Risk: medium-low. Preserve hard stops for unsafe publication, DB corruption, secret leakage, invalid JSON, or explicit `blocking=true`.

Evidence:
- `scripts/run_operating_loop.py` currently contains the legacy `IMPROVE_SMACTORIO` transition and whole-loop block behavior around the improvement/publisher path.
- `docs/specs/2026-05-18-project-improvement-signal-processor-spec.md` says per-project blocked/degraded publication gates should not automatically block render/publication unless explicitly blocking.
- Live evidence showed Signal Hub and the separate GitHub issue foreman can disagree: a local/runtime work-order lane can block while GitHub-backed issue execution succeeds.

## 2. Refresh the SmactorIO cockpit/homepage with current GitHub issue-runtime status

Likely issue title: `docs/ui: refresh SmactorIO cockpit with current GitHub issue runtime status`

Why now: SmactorIO's visible cockpit/project-homepage data can become stale relative to the actual GitHub-backed runtime and prior completed issues. Stale pages are also bad input to future project-model discovery.

Value: improves the human control surface, reduces duplicate/stale issue generation, and gives the project-improvement system more accurate structured evidence.

Risk: low. Mostly structured JSON/docs/page generation; no service/timer/runtime mutation required.

Evidence:
- `data/project_homepages/smactorio.json` has historically lagged behind completed GitHub-backed runtime work.
- Recent verification docs show project-improvement issue publication, SmactorIO pickup, PR merge, and issue closure are already live paths.

## 3. Make generated verification commands executable in this repo

Likely issue title: `chore(signal-hub): make generated verification commands executable in this repo`

Why now: generated project-improvement issues and runbooks should tell workers/operators to run commands that actually exist in the target repo. Dead verification commands will become more damaging once the discovery system generates more issues.

Value: reduces worker confusion, prevents false verification failures, and makes generated tickets directly actionable.

Risk: low. Either add a thin repo-local wrapper around the existing unittest command or update registry/docs/default verification commands to match the commands used by CI and SmactorIO policy.

Evidence:
- The registry/runbook has referenced `scripts/run_tests.sh`-style commands while this Signal Hub package generally uses `python3 -m unittest discover -s tests -q` and policy-defined verification checks.
- The project-improvement generator should source verification defaults from the refreshed project model/registry, not from stale fixture text.
