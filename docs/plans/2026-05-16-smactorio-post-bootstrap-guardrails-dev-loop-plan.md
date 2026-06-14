# SmactorIO Post-Bootstrap Guardrails Dev-Loop Plan

> **For Hermes:** Use the development loop. Produce or refine the spec, plan, and fresh-session prompt before runtime implementation.

**Goal:** Turn the post-Phase-0 vision into a reviewed, executable guardrails package and the first real implementation slice for SmactorIO autonomy.

**Architecture:** This is a documentation and control-plane slice. It records the post-merge truth, defines the guardrails, and anchors Phase 1A implementation in GitHub issue #3 and PR #4. Runtime FSM/code autonomy comes later.

**Tech Stack:** GitHub Issues/PRs, GitHub Actions, protected `main`, Signal Hub docs under `signal-hub/docs/`, Python unit tests, existing Signal Hub secret scanner, and a tested changed-path scope guard.

---

## Current truth this plan must preserve

- Phase 0 source bootstrap is merged through PR #2.
- Issue #1 is closed as completed.
- Safe source now lives under `signal-hub/` in `leonbreukelman/rtx3070-workshop-ops`.
- Local post-merge tests passed: 153 tests and 14 subtests.
- Secret scan passed with 0 findings.
- Normal CI was not configured after Phase 0; Phase 1A PR #4 now adds `signal-hub-guardrails`.
- `main` branch protection was not enabled after Phase 0; it now requires `signal-hub-guardrails`, enforces admins, blocks force pushes/deletions, and requires conversation resolution.
- Leon is not the code reviewer; Hermes must verify and report outcomes in plain English.

## Slice boundary

This plan prepares the next work. It does not implement runtime autonomy.

Allowed:

- create or update post-bootstrap spec/plan/prompt docs;
- create a GitHub issue for the next guardrails Candidate if a new session is explicitly executing the prompt;
- create a branch and PR for doc updates if the prompt execution authorizes GitHub persistence;
- run doc checks and secret scans.

Not allowed without explicit re-authorization:

- direct push to `main`;
- merging the PR;
- changing live `/srv` content;
- changing runtime DB/state;
- creating schedulers;
- public/social/spend/destructive actions;
- broad external source ingestion.

## Files

Create or maintain:

- `signal-hub/docs/specs/2026-05-16-smactorio-post-bootstrap-guardrails-spec.md`
- `signal-hub/docs/plans/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop-plan.md`
- `signal-hub/docs/prompts/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop.md`

Do not mutate reviewed files in place unless the new session explicitly decides to create a new `v3` or addendum file:

- `signal-hub/docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
- `signal-hub/docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`

## Task 1: Preflight the repo and existing docs

**Objective:** Confirm the session is operating on the GitHub-backed repo and understand the current artifact set.

**Commands:**

```bash
cd /home/leonb/projects/rtx3070-workshop-ops
pwd
git rev-parse --show-toplevel
git status --short --branch
git remote -v
gh pr view 2 --repo leonbreukelman/rtx3070-workshop-ops --json number,state,mergedAt,url
gh issue view 1 --repo leonbreukelman/rtx3070-workshop-ops --json number,state,stateReason,url
gh api repos/leonbreukelman/rtx3070-workshop-ops/branches/main/protection || true
gh api repos/leonbreukelman/rtx3070-workshop-ops/actions/workflows --jq '{total:.total_count, workflows:[.workflows[] | {name,path,state}]}'
```

**Expected:** The repo is `rtx3070-workshop-ops`, PR #2 is merged, issue #1 is closed, and branch protection/CI gaps are explicit.

## Task 2: Preserve existing reviewed artifacts

**Objective:** Treat reviewed spec/plan files as prior evidence, not scratchpads.

Read:

- `signal-hub/docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
- `signal-hub/docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`
- `signal-hub/docs/verification/2026-05-16-bootstrap-divergence.md`

**Rule:** If the new facts conflict with older wording, create a new addendum or versioned file instead of silently editing reviewed artifacts in place.

## Task 3: Write or refine the post-bootstrap spec

**Objective:** Make the next guardrails explicit.

Spec must include:

- confirmed post-Phase-0 state;
- real CI gap;
- absent branch protection;
- Candidate queue through GitHub Issues;
- priority gate split from classification and selection;
- one Candidate per run;
- first-class Signal Hub FSM state;
- development-loop phase gates;
- simple cockpit contract;
- human gates;
- acceptance criteria.

**Verification:** The spec must make clear that Phase 0 is complete but runtime autonomy is not complete.

## Task 4: Write or refine this plan

**Objective:** Make implementation of the docs package obvious to a fresh agent.

Plan must include:

- exact files;
- exact preflight commands;
- scope boundaries;
- verification commands;
- optional GitHub issue/branch/PR flow;
- no-merge rule;
- no-direct-main rule;
- plain-English final report rule.

## Task 5: Write the fresh-session prompt

**Objective:** Create a prompt that a future Hermes session can read and execute without needing this chat.

Prompt must include:

- load these skills first: `signal-hub-operating-loop-verification`, `disciplined-project-delivery`, `writing-plans`, `github-issues`, `github-pr-workflow`, and `requesting-code-review` if committing/pushing;
- post-Phase-0 confirmed state;
- goal: deliver the guardrails spec, plan, and next implementation prompt;
- allowed actions;
- forbidden actions;
- exact source files to inspect;
- exact output files;
- verification commands;
- final response format.

## Task 6: Verify docs locally

**Objective:** Ensure the docs are safe and clean.

Run from repo root:

```bash
git diff --check
python3 signal-hub/scripts/scan_for_secrets.py   signal-hub/docs/specs/2026-05-16-smactorio-post-bootstrap-guardrails-spec.md   signal-hub/docs/plans/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop-plan.md   signal-hub/docs/prompts/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop.md
git status --short --branch
```

**Expected:** whitespace check passes; secret scan returns no findings; only the intended docs are changed or untracked.

## Task 7: Optional GitHub persistence lane

Only if the user explicitly asks to commit/push/open a PR in the new session:

1. Create/reuse an issue for the guardrails docs Candidate.
2. Create branch `smactor/post-bootstrap-guardrails-docs` from `origin/main`.
3. Stage explicit doc paths only.
4. Commit with a docs message.
5. Push the branch.
6. Open a PR.
7. Do not merge.

**Suggested Candidate id:** `post-bootstrap-smactorio-guardrails-docs-001`

## Done definition

Done means:

- post-bootstrap spec is saved;
- post-bootstrap plan is saved;
- fresh-session prompt is saved;
- checks pass;
- no runtime or credential-bearing files are introduced;
- final report is plain-English and does not ask Leon to review code or PRs.
