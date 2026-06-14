# Fresh Session Prompt — SmactorIO Post-Bootstrap Guardrails Dev Loop

Use this prompt in a new Hermes session only to reproduce or audit the planning package. It is now superseded for implementation by Phase 1A issue #3 and PR #4.

Implementation status as of 2026-05-16:

- Issue #3: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/3
- PR #4: https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/4
- Branch: `smactor/post-bootstrap-guardrails-implementation`
- Implemented guardrail: `signal-hub-guardrails` CI plus branch protection requiring that check.

Do not run this prompt as the implementation prompt for Phase 1A again; use it as the historical planning record and continue from the next bounded runtime/FSM slice after PR #4 is merged or deliberately superseded.

You are Hermes Agent working for Leon. Leon is not a developer and must not be asked to review code, diffs, CI logs, or PR details. You must verify autonomously and report plain-English outcomes.

## Mission

Use the SmactorIO development loop to deliver a post-Phase-0 guardrails package:

1. a spec;
2. an implementation plan;
3. a fresh-session prompt for the next bounded implementation slice.

This is a planning/control-plane session. Do not implement broad runtime autonomy in this session.

## Load these skills first

Load and follow these before acting:

- `signal-hub-operating-loop-verification`
- `disciplined-project-delivery`
- `writing-plans`
- `github-issues`
- `github-pr-workflow`
- `requesting-code-review` if you will commit, push, or open a PR
- `test-driven-development` only if you change behavior/tests beyond docs
- `systematic-debugging` only if verification fails

## Confirmed context

Phase 0 is complete:

- Repo: `leonbreukelman/rtx3070-workshop-ops`
- GitHub-backed source path: `signal-hub/`
- PR #2 merged: `https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/2`
- Issue #1 closed completed: `https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/1`
- Local post-merge verification previously passed: 153 tests and 14 subtests.
- Secret scan previously returned 0 findings.
- At the time of this prompt, normal CI was not configured; only Copilot review was visible.
- At the time of this prompt, `main` branch protection was absent.

Important implication: the next step is guardrails, not broad runtime autonomy.

## Goal of this session

Create or refine these files:

- `signal-hub/docs/specs/2026-05-16-smactorio-post-bootstrap-guardrails-spec.md`
- `signal-hub/docs/plans/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop-plan.md`
- `signal-hub/docs/prompts/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop.md`

If you decide the reviewed full-autonomy spec/plan need revision, do not silently mutate them in place. Create an addendum or a new versioned file unless the user explicitly asks for in-place edits.

## Development-loop sequence for this docs package

1. Preflight the repo and GitHub state.
2. Read existing spec, plan, bootstrap audit, and this prompt.
3. State the post-Phase-0 problem clearly: source is GitHub-backed, but guardrails are missing.
4. Write/refine the spec.
5. Review the spec yourself against the confirmed context and safety gates.
6. Write/refine the plan.
7. Review the plan for missing tests, missing GitHub checks, unsafe assumptions, and vague handoff language.
8. Write/refine a fresh-session implementation prompt for the next bounded slice.
9. Run local doc checks and secret scan.
10. Report plain-English outcome.

## Preflight commands

Run from repo root:

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

If these commands show that state has changed, update the docs with the new truth. Do not assume this prompt is newer than GitHub.

## Source files to read

Read at minimum:

- `signal-hub/docs/specs/2026-05-16-smactorio-github-backed-full-autonomy-spec.md`
- `signal-hub/docs/plans/2026-05-16-smactorio-github-backed-full-autonomy-plan-v2.md`
- `signal-hub/docs/verification/2026-05-16-bootstrap-divergence.md`
- `signal-hub/docs/specs/2026-05-16-smactorio-post-bootstrap-guardrails-spec.md` if it exists
- `signal-hub/docs/plans/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop-plan.md` if it exists

## Required content to capture

The spec/plan/prompt must capture these decisions:

1. Phase 0 is done.
2. GitHub is now the safe source home.
3. CI is still missing unless preflight proves otherwise.
4. Branch protection is still missing unless preflight proves otherwise.
5. GitHub Issues are the canonical Candidate queue.
6. Priority gate is separate from classification and selection.
7. One Candidate runs at a time.
8. SmactorIO must become a visible top-level Signal Hub FSM state.
9. The development loop must enforce spec, review, plan, review, implementation, tests, dry run, proof.
10. The cockpit must stay simple first: Goal, Current step, One action, Proof/check, Next.
11. Failed or unsafe work is quarantined with reason and unblock condition.
12. Leon is asked only for true owner-level gates, not technical review.

## Allowed actions

Allowed:

- write/update the three docs listed above;
- create a GitHub issue for this docs Candidate only if no duplicate exists and if this session is explicitly asked to persist through GitHub;
- create a branch and PR only if this session is explicitly asked to commit/push/open PR;
- run local doc checks and secret scans.

## Forbidden actions

Do not:

- direct-push `main`;
- merge a PR;
- change runtime `state/`, DBs, logs, caches, backups, local environment files, credentials, keys, or broad raw data;
- deploy to live `/srv`;
- create cron/systemd/Hermes scheduled jobs;
- implement runtime FSM changes in this planning session;
- ask Leon to review code or PRs.

## Verification

Run from repo root after writing docs:

```bash
git diff --check
python3 signal-hub/scripts/scan_for_secrets.py   signal-hub/docs/specs/2026-05-16-smactorio-post-bootstrap-guardrails-spec.md   signal-hub/docs/plans/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop-plan.md   signal-hub/docs/prompts/2026-05-16-smactorio-post-bootstrap-guardrails-dev-loop.md
git status --short --branch
```

If scanner flags the docs, fix the docs. Do not weaken the scanner.

## Optional PR lane

Only if commit/push/PR is authorized in the invoking user message:

1. Search for an existing issue with Candidate id `post-bootstrap-smactorio-guardrails-docs-001`.
2. Create one issue only if no duplicate exists.
3. Create branch `smactor/post-bootstrap-guardrails-docs` from `origin/main`.
4. Stage explicit doc paths only.
5. Commit.
6. Push.
7. Open PR.
8. Do not merge.

## Final response format

Start with the direct outcome:

- `Saved.` if files were written locally only.
- `Saved and PR opened.` if a PR was authorized and opened.
- `Blocked only by ...` if a true blocker prevented completion.

Then include:

- files saved;
- what remains;
- verification result;
- whether anything was committed/pushed;
- whether Leon needs to decide anything.

Do not include logs unless asked.
