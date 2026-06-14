# SmactorIO GitHub-backed Full Autonomy Implementation Plan v2

Status: revised after adversarial Opus review
Date: 2026-05-16
Spec: `docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
Review artifact: `docs/verification/2026-05-16-smactorio-github-backed-full-autonomy-plan-opus-review.md`
Owner: SmactorIO / Signal Hub

## Goal

Move SmactorIO from a local Improvement OS into a GitHub-backed autonomous project system where roadmap items become prioritized Candidates, Candidates enter a governed development loop, work is versioned through issues/branches/commits/PRs, rollback is done through git revert/tags, and the project site shows the current state clearly.

## Load-bearing decisions

1. Prioritization is a standalone governed step between normalization and candidate selection.
2. GitHub Issues are the canonical backlog. GitHub Projects are the preferred visible status layer, but issue metadata plus Candidate docs are acceptable until Project fields exist.
3. The current GitHub home is `leonbreukelman/rtx3070-workshop-ops`, with SmactorIO/Signal Hub under `signal-hub/`.
4. Normal rollback is git-native: revert PR/commit, reopen/update issue, record rollback proof. Tarballs are not version control.
5. Current slice is docs/site/bootstrap only. Runtime FSM automation is a later Candidate branch after safe source packaging is complete.
6. Direct push to `main` is not allowed for this slice. Use branch + PR. Human merge is required unless Leon separately changes the policy.
7. Reviewed artifacts are immutable for future runtime work. Revisions after review create a new dated or version-suffixed file.

## Cross-cutting invariants

- Max 3 new GitHub issues per run.
- Max 1 PR per Candidate per day.
- Max 1 selected Candidate per improvement-loop run.
- Max 10 outstanding open `smactorio` issues before the agent must triage instead of creating more.
- No force-push rollback. If branch history must be rewritten for hygiene, use `--force-with-lease` only on the agent-owned feature branch before review/merge.
- Tags under `smactor/*` are append-only. Moving or deleting one is forbidden.
- Runtime state, logs, databases, caches, broad raw `data/` dumps, and credentials are never committed.
- All commits by autonomous runs should use an explicit bot identity, e.g. `smactorio-bot <smactorio-bot@users.noreply.github.com>`, unless the run is intentionally performed as Leon and documented.

## Phase 0 — Bootstrap source into GitHub safely

Purpose: get current safe Signal Hub/SmactorIO source under version control without leaking runtime data or deleting remote-only content.

### 0.1 Prepare clean packaging worktree

1. Clone or fetch `leonbreukelman/rtx3070-workshop-ops` into a clean packaging worktree.
2. Create branch `smactor/bootstrap-github-backed-autonomy` from `origin/main`.
3. Confirm `main` branch protection. If it is absent, record that as a blocker for autonomous runtime phases. For this docs/site/bootstrap slice, still use PR and do not direct-push `main`.

### 0.2 Path mapping

Use this mapping only:

| Local source | GitHub repo target |
| --- | --- |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/docs/**` | `signal-hub/docs/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/scripts/**` | `signal-hub/scripts/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/tests/**` | `signal-hub/tests/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/public/**` | `signal-hub/public/**` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/pages.json` | `signal-hub/pages.json` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/data/project_homepages/smactorio.json` | `signal-hub/data/project_homepages/smactorio.json` |
| `/home/leonb/projects/ai-tech-signal-brief/leon-signal-hub/data/smactorio/*.json` | `signal-hub/data/smactorio/*.json` |

Anything outside this table requires a new review note before staging.

### 0.3 Divergence audit

Before copying files, write:

`signal-hub/docs/verification/2026-05-16-bootstrap-divergence.md`

It must list:

- local-only files selected for import;
- remote-only files preserved untouched;
- conflicting files and file-by-file disposition;
- staged allowlist;
- explicit statement: no remote-only file deletions in this slice.

Adds and updates only. Do not use `rsync --delete`.

### 0.4 Denylist and allowlist checks

Denylist patterns:

```text
state/
logs/
cache/
backups/
*.db
*.sqlite
*.sqlite3
*.db-wal
*.db-shm
.env
.env.*
*credential*
*secret*
*token*
```

Before commit:

1. Run `git status --short`.
2. Review `git diff --cached --name-only` against the path mapping.
3. Abort if any staged file matches the denylist.
4. Run `git check-ignore` spot checks for known runtime paths.
5. Run the named secret scan:

```bash
python3 signal-hub/scripts/scan_for_secrets.py signal-hub/docs signal-hub/data/project_homepages signal-hub/data/smactorio signal-hub/public signal-hub/scripts signal-hub/tests
```

Any scanner finding fails the slice unless it is a documented false positive in a committed allowlist reviewed by Leon.

### 0.5 Commit, push, PR

1. Stage explicit pathspecs only.
2. Commit with a docs/site/bootstrap message.
3. Push branch.
4. Open PR.
5. Do not self-merge.
6. If rollback is needed, create a revert branch + PR. Do not revert directly on `main`.

Acceptance:

- GitHub branch contains current safe source needed for SmactorIO pages/docs/tests.
- Runtime state remains ignored/uncommitted.
- Secret scan is clean.
- PR exists and can be reviewed/merged by a human.
- No remote-only file was deleted.

## Phase 1 — Publish reviewed spec and plan

Purpose: make the architecture durable and recoverable outside chat.

Tasks:

1. Save reviewed full-autonomy spec under `docs/specs/`.
2. Save Opus spec review under `docs/verification/`.
3. Save initial plan under `docs/plans/`.
4. Save Opus adversarial plan review under `docs/verification/`.
5. Save this v2 plan rather than mutating the reviewed draft in place.
6. Link the latest reviewed plan/spec from the SmactorIO homepage; older versions go to history or remain in docs, not the main simple cockpit.

Acceptance:

- Spec, plan v2, and both review artifacts exist.
- Review findings are reflected in v2.
- The plan names tests, verification, GitHub lifecycle, PR policy, and rollback steps.

## Phase 2 — Update simple roadmap and project cockpit

Purpose: show the new autonomy model without overwhelming Leon.

Tasks:

1. Keep the simple roadmap at one-screen summary level.
2. Add only these top-level simple concepts:
   - Priority gate decides what runs next.
   - GitHub-backed loop records work and rollback.
   - Development loop runs one selected Candidate at a time.
   - Operator dry run proves the result before handoff.
3. Move detailed development-loop/GitHub mechanics into linked spec/plan pages.
4. Update `data/project_homepages/smactorio.json` so the cockpit shows:
   - Priority gate;
   - GitHub-backed loop;
   - current Candidate: `bootstrap-github-backed-smactorio-source-001`;
   - priority score or `—` with clear pending reason if no runtime Candidate object exists yet;
   - rollback through git revert;
   - links to latest spec, plan v2, and reviews.
5. Empty GitHub fields render as `—` and, where HTML attributes are supported, `data-empty="true"`.
6. Add structured page markers where the builder permits:

```html
<meta name="smactor:section" content="priority-gate">
<meta name="smactor:section" content="github-backed-loop">
<meta name="smactor:section" content="rollback-through-git-revert">
<meta name="smactor:section" content="development-loop">
<meta name="smactor:section" content="operator-dry-run">
```

7. Add or update tests to verify markers by structure or deterministic source data, not by a loose unrelated substring.
8. Build pages twice and check determinism. If generated timestamps differ, document the allowed field.

Acceptance:

- Homepage and roadmap answer what is next in plain English.
- Generated pages include priority/GitHub/rollback/dry-run markers.
- Simple page is still readable as a simple status cockpit.

## Phase 3 — GitHub backlog foundation

Purpose: make GitHub the actionable queue without causing duplicate issue spam.

Dedup key definition:

```text
candidate_dedup_key = sha256(normalized_source_type + "\n" + normalized_source_ref + "\n" + normalized_candidate_kind)
```

Normalization:

- lowercase;
- trim leading/trailing whitespace;
- collapse internal whitespace to one space;
- canonicalize path separators to `/`;
- do not include mutable fields such as status, timestamp, priority score, page text, or generated HTML.

Tasks:

1. Search existing issues for the hidden marker before creating a new issue.
2. Add hidden marker to issue body:

```text
<!-- smactor:dedup=<candidate_dedup_key> -->
```

3. Reuse existing branch and PR for the same dedup key. Reopen prior PR when appropriate; do not create a duplicate.
4. Add labels:
   - `smactorio`
   - `type:roadmap|ops|feature|bug|research`
   - `autonomy:ready|needs-review|blocked|quarantined`
   - `risk:low|medium|high`
   - `rollback` when reverted.
5. If no GitHub Project exists, store equivalent fields in the issue body and Candidate docs.

Tests later required:

- two title/source variants that normalize the same produce the same dedup key;
- two distinct source refs do not collide;
- second run creates no new issue/branch/PR for same dedup key.

Acceptance:

- At least one Candidate can be represented by a GitHub Issue.
- Duplicate issue creation is prevented by dedup marker search.
- No more than 3 issues are created by one run.

## Phase 4 — Runtime Candidate model and priority scorer

Purpose: make scoring/selecting runnable and testable in a later Candidate.

Files likely affected later:

- `scripts/smactorio_improvement_runner.py`
- `scripts/run_operating_loop.py`
- `scripts/signal_loop_db.py`
- `tests/test_full_autonomy_fsm.py`
- new `tests/test_smactorio_candidate_priority.py`
- fixture `tests/fixtures/candidate_priority_golden.json`

Priority score:

```text
score = impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface
```

Axis bounds:

- every axis integer 0-5;
- effective score range -15 to +25;
- `min_autonomous_score = 6`;
- per-axis autonomous floors: `impact >= 2`, `confidence >= 2`, `evidence_strength >= 1`;
- `max_risk_for_autonomy = medium`;
- `min_classification_confidence = 2`.

Tie-break:

1. lower risk;
2. older `created_at`;
3. lower GitHub issue number;
4. stable Candidate id lexicographic order.

Lock:

- single writer implemented with `flock` on an untracked runtime path such as `state/smactorio.lock`;
- default lease/timeout 30 minutes;
- locks older than 60 minutes are considered abandoned only after logging stale-lock recovery evidence;
- lock files are never committed.

Tests:

- classification does not select;
- prioritization does not mutate selection status;
- low-score Candidate is refused unless pinned;
- high-risk or low-confidence risk is refused;
- golden fixture score matches expected;
- tie-break is deterministic;
- second dry run creates no duplicate Candidate;
- concurrent lock returns skipped/clear status.

Acceptance:

- Scoring is reproducible from `tests/fixtures/candidate_priority_golden.json`.
- Selection is deterministic, safe, and auditable.

## Phase 5 — FSM integration

Purpose: make SmactorIO autonomy visible in the top-level operating loop.

Tasks:

1. Add formal state `RUN_SMACTORIO_IMPROVEMENT_LOOP` only with an explicit DB migration if SQLite constraints require it.
2. If migration is not safe in the same slice, record a named run step first and plan the migration separately.
3. Migration script must backfill prior records from `IMPROVE_SMACTORIO` if that old name was used.
4. Runner subprocess gets a default 30-minute timeout, configurable.
5. On timeout: SIGTERM, then SIGKILL, then evidence record and safe loop status.
6. Idempotent skip/lock is expected non-failure status.
7. Top-level loop still rebuilds/publishes pages if runner is skipped safely.

Acceptance:

- Dry-run output and persisted trace use the same state name.
- Failure/timeout creates evidence and does not crash the parent loop.
- Two consecutive dry runs create no new issue/branch/PR on the second run.

## Phase 6 — Development-loop phase gates

Purpose: make the development loop enforced rather than narrative.

Phase records:

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

Rules:

1. Each phase needs an artifact path.
2. Review artifacts must record `reviewer_actor_id`, model/provider or tool, timestamp, prompt scope, and verdict.
3. `reviewer_actor_id` must differ from `implementer_actor_id`; otherwise status becomes `needs-review`.
4. If reviewer unavailable, move to `Needs Review` or quarantine; do not skip.
5. Automated tests are required before dry run.
6. Dry-run report is stored under `docs/verification/<date>-<candidate-id>-dry-run.md`.
7. Dry-run findings are requeued by dedup key with `max_requeue_count = 3`; delete/recreate does not reset the count.

Acceptance:

- Candidate cannot jump directly from selection to implementation.
- Missing artifacts block advancement.
- Dry-run findings feed back without infinite loops.

## Phase 7 — Project page and proof publication

Purpose: make autonomy understandable and auditable.

Tasks:

1. Render current Candidate on `/projects/smactorio/`.
2. Render empty GitHub fields as `—` with `data-empty="true"` where applicable.
3. Show priority score and one-line reason.
4. Show issue/branch/PR/commit links when available.
5. Show rollback ref or revert instruction.
6. Show last run, next run, proof checks, and dry-run status.
7. Keep advanced detail below the simple summary.
8. Latest spec/plan links only in top card; old versions go to history/archive.

Acceptance:

- Leon can see what is selected, why, what changed, how it was verified, and how rollback works.
- Future agents can machine-check page markers.
- Two consecutive page builds are byte-identical except for explicitly allowed generated timestamp fields.

## Phase 8 — External source expansion

Purpose: let external sources inform SmactorIO without steering it randomly.

Tasks:

1. Treat external sources as proposals, not direct actions.
2. Require linkage to internal goal/issue/roadmap item before Candidate creation.
3. Score external authority/freshness/usefulness/safety.
4. Auto-add only safe, free, read-only sources.
5. Keep public/social/spend/login mutations human-gated.

Acceptance:

- External signals cannot bypass internal priorities.
- External source Candidates are visible and reviewable.

## Verification plan for current docs/site/bootstrap slice

From the local Signal Hub source tree:

```bash
python3 scripts/build_smactorio_simple_roadmap_page.py
python3 scripts/build_project_homepages.py
python3 -m unittest tests.test_page_manifest_and_navigation
python3 scripts/scan_for_secrets.py docs data/project_homepages data/smactorio public/projects/smactorio public/smactorio_simple_roadmap.html
```

From the clean GitHub packaging worktree before commit:

```bash
git diff --cached --name-only
git diff --cached --check
python3 signal-hub/scripts/scan_for_secrets.py signal-hub/docs signal-hub/data/project_homepages signal-hub/data/smactorio signal-hub/public signal-hub/scripts signal-hub/tests
```

Idempotent page build check:

```bash
python3 signal-hub/scripts/build_smactorio_simple_roadmap_page.py
python3 signal-hub/scripts/build_project_homepages.py
sha256sum signal-hub/public/projects/smactorio/index.html signal-hub/public/smactorio_simple_roadmap.html
python3 signal-hub/scripts/build_smactorio_simple_roadmap_page.py
python3 signal-hub/scripts/build_project_homepages.py
sha256sum signal-hub/public/projects/smactorio/index.html signal-hub/public/smactorio_simple_roadmap.html
```

If timestamp churn prevents identical output, document the exact allowed field and do not treat the whole page as stable.

## Future runtime verification

```bash
python3 -m unittest tests.test_full_autonomy_fsm
python3 -m unittest tests.test_smactorio_candidate_priority
python3 scripts/run_operating_loop.py --skip-scan --dry-run
python3 scripts/run_operating_loop.py --skip-scan --dry-run
```

After the two dry runs, assert that the second run created no new:

- GitHub issue;
- Candidate record;
- branch;
- PR;
- page claim for the same source signal.

## Rollback plan

Current docs/site/bootstrap slice:

1. Create revert branch from `origin/main`.
2. `git revert <commit-or-merge-sha>`.
3. Re-run page tests and secret scan.
4. Open rollback PR.
5. On merge, reopen/update the originating Candidate issue with label `rollback`.
6. Record revert SHA on the proof page or verification artifact.

Future runtime slices:

- revert merge commit or branch commits through PR;
- use milestone tag `smactor/<yyyy-mm-dd>-<short-slug>` as read-only anchor;
- never move/delete an existing `smactor/*` tag;
- avoid direct `main` mutation and force-push rollback.

## Done definition for this slice

This slice is done when:

- reviewed spec exists;
- plan v2 exists and incorporates adversarial review blockers;
- SmactorIO roadmap/homepage reflect prioritization, GitHub backing, and git rollback;
- page marker tests pass;
- secret scan passes;
- no path outside the allowlist is staged in the GitHub packaging branch;
- no `smactorio` issue is created without a dedup marker if issue creation is performed;
- homepage renders consistently enough to verify markers on two builds;
- GitHub branch/PR exists for the verified files, or a blocker is recorded plainly;
- final handoff states what is in GitHub, what remains runtime-only, and the next runtime Candidate.
