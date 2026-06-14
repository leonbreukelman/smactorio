# SmactorIO Post-Bootstrap Guardrails Spec

Status: implementation addendum; Phase 1A guardrails PR opened
Date: 2026-05-16
Applies to: `leonbreukelman/rtx3070-workshop-ops`, `signal-hub/`
Related Phase 0 PR: https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/2
Related Phase 0 issue: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/1
Related Phase 1A issue: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/3
Related Phase 1A PR: https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/4
Builds on: `docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
Builds on: `docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`
Fresh-session prompt: `docs/prompts/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop.md`

## Plain answer

Phase 0 made the safe Signal Hub/SmactorIO source GitHub-backed.

The next work is not "more AI" first. The next work is the safety and operating guardrails that make autonomy trustworthy:

1. real GitHub checks;
2. protected `main`;
3. GitHub Issues as the Candidate queue;
4. a visible priority gate;
5. one selected Candidate at a time;
6. a first-class SmactorIO state in the Signal Hub operating loop;
7. enforced development-loop phases;
8. a simple cockpit that tells Leon what is happening, why, proof, and rollback.

## Confirmed post-Phase-0 state

Confirmed after PR #2 was merged:

- Safe Signal Hub/SmactorIO source exists under `signal-hub/` in the private GitHub repo.
- PR #2 is merged into `main`.
- Issue #1 is closed as completed.
- Local post-merge verification passed: 153 tests and 14 subtests.
- Secret scan returned 0 findings.
- GitHub reported no normal CI/check runs for the merge commit.
- The only workflow visible at that time was Copilot review.
- `main` branch protection was absent.
- Phase 1A issue #3 and PR #4 now add the first real guardrail implementation: `signal-hub-guardrails` CI, a tested path-scope guard, full Signal Hub secret scanning, and documented PR evidence.
- `main` branch protection now requires `signal-hub-guardrails`, enforces admins, blocks force pushes/deletions, and requires conversation resolution.

This means Phase 0 succeeded and Phase 1A guardrails are in place as branch protection plus an open implementation PR. Runtime autonomy still must not proceed beyond the next bounded slice until PR #4 is merged or deliberately superseded.

## Goal

Make SmactorIO a private project operating system that can notice work, score it, select one safe reversible Candidate, move it through a governed development loop, prove the result, update the cockpit, and ask Leon only for true owner-level decisions.

## Non-goals for the next session

The next session must not jump straight into broad runtime autonomy.

Out of scope unless explicitly re-authorized:

- broad external source discovery;
- public publishing;
- social account actions;
- spend;
- destructive cleanup;
- production deploy;
- raw conversation dump ingestion;
- direct push to `main`;
- automatic merge of implementation PRs;
- multiple unrelated Candidates in one run.

## Guardrail contract

### 1. GitHub checks and protected main

Before autonomy can safely merge code, the repo needs a real required-check surface.

Required checks should include at minimum:

- Signal Hub unit test discovery from `signal-hub/`;
- focused SmactorIO/FSM/page tests;
- the existing secret scanner against safe source paths;
- a path-scope check that rejects runtime state, DBs, logs, caches, backups, local environment files, credentials, keys, and broad raw data;
- a generated-doc whitespace check such as `git diff --check`.

`main` should then require those checks before merge.

### 2. GitHub Issues are the Candidate queue

Each actionable unit of work should have a GitHub Issue with a stable dedupe marker. The issue is the durable backlog object. Local state is a cache and execution journal, not the canonical backlog.

Each Candidate issue should show:

- candidate id;
- dedupe marker;
- source/provenance;
- problem or goal;
- evidence links;
- risk;
- priority score and short reason;
- selected/not selected state;
- branch/PR/proof/rollback links when available.

### 3. Priority gate is separate from classification

Classification says what an item is. Prioritization decides whether it is worth doing. Selection picks one bounded unit to run.

The priority gate should be cockpit-visible and deterministic. It must explain the score in plain language.

Minimum score model:

```text
score = impact + confidence + reversibility + dependency_unblock + evidence_strength - effort - risk - regression_surface
```

Autonomous run floors:

- impact at least 2;
- confidence at least 2;
- evidence strength at least 1;
- risk no higher than medium;
- score at least 6 unless Leon explicitly pins the Candidate.

### 4. One Candidate per run

SmactorIO must avoid thrashing. A run selects at most one Candidate, creates/reuses one branch, and opens/updates at most one PR.

If an in-progress SmactorIO branch or PR already exists, the next run should either continue that Candidate or stop with a clear blocked status.

### 5. First-class FSM state

SmactorIO autonomy should be visible in the top-level Signal Hub loop, not hidden as an incidental script call.

Target top-level shape:

```text
SYNTHESIZE_DAILY_BRIEF
  -> RUN_SMACTORIO_IMPROVEMENT_LOOP
  -> REBUILD_PROJECT_PAGES
  -> PUBLISH_LOCAL_SITE
  -> IDLE
```

Inside `RUN_SMACTORIO_IMPROVEMENT_LOOP`:

```text
INTAKE_WORK_SOURCES
  -> CLASSIFY_WORK_ITEMS
  -> NORMALIZE_CANDIDATES
  -> PRIORITIZE_CANDIDATES
  -> SELECT_DEVELOPMENT_CANDIDATE
  -> RUN_DEVELOPMENT_LOOP
  -> VERIFY_AND_DRY_RUN
  -> PUBLISH_PROOF_AND_ROLLBACK_ANCHOR
  -> LEARN_AND_REQUEUE
```

Unsafe or unclear work goes to `QUARANTINE_CANDIDATE` with reason, proof, and next unblock condition.

### 6. Development-loop phases are enforced

A selected Candidate should not jump from idea to code. It must pass through:

1. problem or clear goal;
2. research/reuse-first check;
3. spec;
4. independent spec review;
5. revised spec;
6. implementation plan;
7. adversarial plan review;
8. revised plan;
9. implementation;
10. automated tests;
11. operator-as-user dry run;
12. proof/handoff;
13. learning/requeue of findings.

Every phase leaves a durable artifact or an explicit blocked/quarantined reason.

### 7. Cockpit is simple first

The SmactorIO cockpit top card must answer:

- Goal;
- Current step;
- One action being taken;
- Why this Candidate was selected;
- Proof/check;
- Rollback path;
- Next step.

Advanced scoring, history, and detailed artifacts may exist below or behind links. The first screen should stay understandable to Leon without code review or log review.

### 8. Human gates

Autonomy may proceed without asking for local, private, free, reversible, low/medium-risk work that has tests or a dry-run check.

Ask Leon only for:

- public/social actions;
- spend;
- destructive or irreversible changes;
- login/2FA blockers;
- production deploys not already authorized;
- security/legal/compliance claims;
- unclear naming/product direction/value judgments.

Do not ask Leon to review PRs, code, diffs, logs, or CI details as a routine handoff. The agent must perform verification and report the plain-English outcome.

## Acceptance criteria for the next guardrails package

The next complete guardrails planning package is done when:

1. a post-bootstrap spec exists and reflects the confirmed Phase 0 state;
2. a post-bootstrap implementation plan exists;
3. a fresh-session prompt exists for the next autonomous session;
4. the plan names exact files, tests, checks, GitHub operations, rollback, and human gates;
5. the prompt limits scope to one coherent guardrail slice;
6. generated docs pass whitespace checks;
7. the secret scanner has no findings for the new docs;
8. no runtime state or credentials are introduced;
9. if committed/pushed later, it happens through a branch and PR, not direct `main`.
