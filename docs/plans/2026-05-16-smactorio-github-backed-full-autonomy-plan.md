# SmactorIO GitHub-backed Full Autonomy Implementation Plan

Status: draft for adversarial Opus review
Date: 2026-05-16
Spec: `docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
Owner: SmactorIO / Signal Hub

## Goal

Move SmactorIO from a locally visible Improvement OS into a GitHub-backed autonomous project system where roadmap items become prioritized Candidates, Candidates enter a governed development loop, work is versioned through commits/branches/PRs, rollback is done through git revert/tags, and the project site shows the current state clearly.

## Direct design decisions

1. Prioritization is standalone between normalization and selection.
2. GitHub Issues/Projects are the canonical backlog/status layer.
3. The existing private repo `leonbreukelman/rtx3070-workshop-ops` is the current GitHub home; SmactorIO lives in `signal-hub/` unless later split out.
4. Normal rollback is git-native: revert commit/merge, tag verified milestones, no tarball-as-version-control.
5. The current implementation slice is documentation/site/bootstrap, not full runtime automation.
6. Runtime FSM changes come next after the source is safely GitHub-backed.

## Phase 0 — Bootstrap source into GitHub safely

Purpose: get the current safe Signal Hub/SmactorIO source under version control without leaking runtime data.

Tasks:

1. Clone/fetch `leonbreukelman/rtx3070-workshop-ops`.
2. Create branch `smactor/bootstrap-github-backed-autonomy`.
3. Compare current local `leon-signal-hub` source against remote `signal-hub/` baseline.
4. Sync source files needed for docs/site/tests/builders.
5. Keep denylisted paths out of git:
   - `state/`
   - databases, WAL/SHM files
   - logs
   - caches
   - backups/tarballs
   - `.env*`
   - credentials
   - raw broad `data/` dumps
6. Allowlist source-safe SmactorIO data needed by generated pages:
   - `signal-hub/data/project_homepages/smactorio.json`
   - `signal-hub/data/smactorio/*.json`
   - only additional `data/internal_work_capsules/smactorio-*.json` if a page/test requires it and secret scan is clean.
7. Update `.gitignore` so this policy is durable.
8. Run secret scan before commit.
9. Commit and push the branch.
10. Create a PR or, if the repo policy is intentionally direct-private, push a verified checkpoint and record rollback instructions.

Acceptance:

- GitHub contains current safe source needed for SmactorIO pages/docs/tests.
- Runtime state remains ignored/uncommitted.
- Secret scan is clean.
- `git revert <commit>` is enough to roll back the documentation/site/bootstrap slice.

## Phase 1 — Publish the reviewed autonomy spec and plan

Purpose: make the architecture durable and recoverable outside chat.

Tasks:

1. Save the full autonomy spec under `docs/specs/`.
2. Save the Opus spec review under `docs/verification/`.
3. Patch the spec for Opus blockers:
   - bootstrap Candidate;
   - idempotency keys;
   - path scope;
   - autonomous score floor;
   - risk revalidation;
   - concurrency lock;
   - page marker contract.
4. Save this implementation plan under `docs/plans/`.
5. Save adversarial plan review under `docs/verification/`.
6. Patch this plan for review findings.
7. Link spec/plan/review artifacts from the SmactorIO project homepage.

Acceptance:

- Spec and plan files exist in the repo.
- Review artifacts exist.
- The plan names test/verification/rollback steps.
- The project page points to the new direction in plain English.

## Phase 2 — Update the simple roadmap and project cockpit

Purpose: make the new model understandable without overwhelming Leon.

Tasks:

1. Update `docs/plans/2026-05-15-smactorio-simple-automation-roadmap.md`.
2. Keep the simple loop visible:
   - Goal
   - State
   - Priority gate
   - Do
   - Check
   - Show
3. Add the development loop as the next governed layer:
   - Problem/root-cause
   - Research/reuse-first
   - Spec
   - Review
   - Plan
   - Adversarial review
   - Implement
   - Test
   - Operator dry run
   - Proof
4. Add GitHub backing:
   - Issue/Candidate
   - Branch/commit/push
   - PR/review
   - git revert/tag rollback
5. Update `data/project_homepages/smactorio.json` so the cockpit shows:
   - Priority is a first-class gate;
   - GitHub-backed loop;
   - selected Candidate / current Candidate;
   - rollback through git revert;
   - links to spec, plan, and reviews.
6. Update page builders/tests so generated pages expose required markers:
   - `Priority gate`
   - `GitHub-backed loop`
   - `Rollback through git revert`
   - `Priority score`
   - `Development loop`
   - `Operator dry run`
7. Rebuild pages.

Acceptance:

- The homepage and roadmap tell Leon what happens next in simple language.
- Tests verify the priority/GitHub/rollback markers.
- The generated pages contain no scripts, unsafe URLs, or credential-like content.

## Phase 3 — GitHub backlog foundation

Purpose: make GitHub the actionable queue.

Tasks:

1. Create or update a GitHub Issue for the bootstrap Candidate.
2. Add hidden dedup marker to issue body:
   - `<!-- smactor:dedup=<sha256> -->`
3. Define issue labels:
   - `smactorio`
   - `type:roadmap`
   - `type:ops`
   - `priority:p0..p3`
   - `autonomy:ready`
   - `autonomy:needs-review`
   - `risk:low|medium|high`
4. If a GitHub Project exists, add fields from the spec.
5. If no Project exists, do not block runtime work; store equivalent metadata in issue body and repo Candidate docs until the Project is created.
6. Add search-before-create logic to future runner plan.

Acceptance:

- At least one SmactorIO Candidate is represented by a GitHub Issue.
- Duplicate issue creation is prevented by the dedup marker.
- The project site references GitHub as the backing backlog even if Project fields are staged later.

## Phase 4 — Runtime Candidate model and priority scorer

Purpose: make the loop runnable and testable.

Files likely affected:

- `scripts/smactorio_improvement_runner.py`
- `scripts/run_operating_loop.py`
- `scripts/signal_loop_db.py`
- `tests/test_full_autonomy_fsm.py`
- new tests for candidate scoring/selection

Tasks:

1. Add Candidate schema helper with required fields from the spec.
2. Add deterministic `candidate_dedup_key` function.
3. Add priority score function:
   - impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface.
4. Add threshold constants:
   - `min_autonomous_score = 6`
   - `max_risk_for_autonomy = medium`
   - `min_classification_confidence = 2`
5. Add selection function separate from scoring.
6. Add single-writer lock.
7. Add quarantine result model.
8. Test:
   - classification does not select;
   - prioritization does not mutate selection state;
   - selection refuses low-score Candidate unless pinned;
   - selection refuses high-risk or low-confidence risk;
   - second run does not duplicate Candidate;
   - concurrent lock returns clear skipped status.

Acceptance:

- Unit tests prove classification/normalization/prioritization/selection are distinct.
- Candidate scoring is reproducible from a fixture.
- Selection behavior is deterministic and safe.

## Phase 5 — FSM integration

Purpose: make SmactorIO autonomy visible in the top-level operating loop.

Tasks:

1. Add formal top-level state `RUN_SMACTORIO_IMPROVEMENT_LOOP` if migration constraints permit.
2. If existing SQLite constraints make immediate state migration unsafe, record it as a named run step first and plan an explicit DB migration.
3. Wire `run_operating_loop.py` to enter the state before invoking the runner subprocess.
4. Preserve subprocess isolation so runner failure does not crash the top-level loop.
5. Treat idempotent skip/lock as expected non-failure status.
6. Update tests that currently expect older names such as `IMPROVE_SMACTORIO`.

Acceptance:

- Dry-run output and persisted trace show the same state name.
- A failed runner creates an evidence record and safe loop status.
- Existing daily brief/page generation still completes when runner is skipped.

## Phase 6 — Development-loop phase gates

Purpose: turn the development loop from narrative into enforced checkpoints.

Tasks:

1. Add phase records for:
   - problem
   - research
   - spec
   - spec_review
   - plan
   - plan_review
   - implement
   - test
   - dryrun
   - proof
2. Require artifact paths for each phase.
3. Require configured reviewer model for review phases.
4. If review fails/unavailable, move Candidate to `Needs Review` instead of continuing silently.
5. Require automated tests before dry run.
6. Require dry-run report before proof publication.
7. Convert dry-run findings into new/updated Candidates with max requeue count.

Acceptance:

- A Candidate cannot jump directly from selection to implementation.
- Missing spec/plan/review artifacts block execution.
- Dry-run findings feed back into the queue without infinite loops.

## Phase 7 — Project page and proof publication

Purpose: make autonomy understandable and auditable.

Tasks:

1. Render current Candidate data on `/projects/smactorio/`.
2. Show priority score and one-line reason.
3. Show GitHub issue/branch/PR/commit links when available.
4. Show rollback ref or revert instruction.
5. Show last run, next run, proof checks, and dry-run status.
6. Keep advanced detail below the simple summary.
7. Add tests for marker contract and no unsafe scripts/URLs.

Acceptance:

- Leon can see what is selected, why, what changed, how it was verified, and how rollback works.
- Future agents can machine-check the page markers.

## Phase 8 — External source expansion

Purpose: let external sources inform SmactorIO without steering it randomly.

Tasks:

1. Add external source proposals, not direct actions.
2. Require linkage to internal goal/issue/roadmap item before Candidate creation.
3. Score external source authority/freshness/usefulness/safety.
4. Auto-add only safe, free, read-only sources.
5. Keep social/public mutation human-gated.

Acceptance:

- External signals cannot bypass internal priorities.
- External source candidates are visible and reviewable.

## Verification plan

Run after documentation/site update:

```bash
python3 scripts/build_smactorio_simple_roadmap_page.py
python3 scripts/build_project_homepages.py
python3 -m unittest tests.test_page_manifest_and_navigation
python3 scripts/scan_for_secrets.py docs data/project_homepages data/smactorio public/projects/smactorio public/smactorio_simple_roadmap.html
```

Run after runtime phases are later implemented:

```bash
python3 -m unittest tests.test_full_autonomy_fsm
python3 -m unittest tests.test_smactorio_candidate_priority
python3 scripts/run_operating_loop.py --skip-scan --dry-run
python3 scripts/run_operating_loop.py --skip-scan --dry-run
```

## Rollback plan

For this documentation/site/bootstrap slice:

1. Use `git status` and `git log` to identify the commit.
2. Roll back with `git revert <commit>` on a new branch or on `main` only if direct-private repo policy allows it.
3. Re-run page tests and secret scan.
4. Push rollback commit.
5. Update the SmactorIO issue/page proof if needed.

For future runtime slices:

- revert merge commit or branch commits;
- use milestone tag `smactor/<yyyy-mm-dd>-<short-slug>` as anchor;
- avoid force-push rollback unless explicitly approved.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Local source ahead of GitHub baseline | Branch-only bootstrap, path-scope, secret scan, explicit allowlist. |
| Runtime data leak | Durable `.gitignore`, force-add only reviewed safe data. |
| Priority score becomes false authority | Require evidence justification and selection risk revalidation. |
| Duplicate GitHub Issues/PRs | Dedup marker, search-before-create, branch/PR reuse. |
| Loop runs twice concurrently | Single-writer lock and clear skipped status. |
| Pages become too complex | Keep simple top card; advanced details below. |
| GitHub Project fields unavailable | Fall back to issue body + Candidate docs, do not block core loop. |
| Review model unavailable | Quarantine/Needs Review, do not skip review silently. |

## Current slice done definition

This slice is done when:

- the reviewed spec exists;
- this reviewed plan exists;
- SmactorIO roadmap/homepage reflect prioritization, GitHub backing, and git rollback;
- relevant page tests pass;
- secret scan passes;
- the GitHub repo contains the verified files through a pushed commit/branch;
- final handoff states what is in GitHub, what remains runtime-only, and the next runtime Candidate.
