# SmactorIO Service GitHub-Issue Runtime Spec

Date: 2026-05-17
Status: reviewed for implementation planning
Target repo: `/home/leonb/projects/rtx3070-workshop-ops`
GitHub repo: `leonbreukelman/rtx3070-workshop-ops`

## Plain-language goal

Replace the old MÆI orchestrator service with a new `smactorio.service` runtime.

The simple contract is:

```text
GitHub issue opened
-> SmactorIO claims it
-> SmactorIO creates an isolated branch/worktree
-> a worker completes the work
-> tests/checks run
-> independent verification/review runs
-> PR opens or updates
-> evidence is posted back to GitHub
-> failures are repaired or quarantined with evidence
-> PR merges only when safe
-> issue is closed/updated
-> repo is left clean
```

Leon should not need to read code, review PRs, interpret CI, clean branches, or manage dirty repositories. SmactorIO/Hermes must either merge verified low-risk PRs autonomously or fail/quarantine with evidence. It must not hand PR review, CI interpretation, merge decisions, or code decisions back to Leon.

## Current diagnosis

Observed on 2026-05-17:

- `maei-orchestrator.service` exists as a system service and is active/enabled.
- `smactorio.service` does not exist yet.
- The target repo is clean on `main` and tracks `origin/main`.
- GitHub issue #1 is open with labels: `smactorio`, `type:ops`, `autonomy:ready`, `risk:low`.
- Current SmactorIO code is not GitHub-issue-first.
- `signal-hub/scripts/smactorio_improvement_runner.py` consumes local SQLite actions and records intended GitHub lifecycle evidence, but does not create branches, commits, pushes, PRs, or merges.
- `signal-hub/state/signal_loop.db` is currently empty of active work.
- Existing Signal Hub guardrail CI required by branch protection is named `signal-hub-guardrails`.

## Non-goals for v1

- Do not build a broad dashboard-first autonomy platform.
- Do not keep local SQLite actions as the main SmactorIO inbox.
- Do not consume roadmap prose, X lists, RSS, logs, or arbitrary external sources as v1 work input.
- Do not use GitHub Projects as a hard dependency for v1.
- Do not allow high-risk, destructive, paid, credential, deployment, or public-account work to run automatically.
- Do not let both `maei-orchestrator.service` and `smactorio.service` execute issue work at the same time.
- Do not install/enable/disable service units from ordinary low-risk issues.

## Source of truth

For v1, GitHub Issues are the inbox and visible work record.

SQLite may exist only as local runtime history/cache. It must not be the canonical backlog.

Every meaningful SmactorIO phase must be visible on GitHub through at least one of:

- issue label
- issue comment
- branch
- PR
- commit
- CI/check result
- evidence artifact committed intentionally under `signal-hub/docs/verification/`

Dashboard or SQLite state alone must never mean “done”. Done means GitHub-visible evidence plus a clean repo.

## Roles and authority boundaries

### Foreman

The foreman process owns all GitHub and git authority:

- issue comments/labels
- branch creation
- commits/pushes after verification
- PR creation/update
- merge
- issue closure/update

### Worker

The worker receives a bounded task packet and writes source changes only inside an isolated worktree.

The worker must not own GitHub mutations. During worker execution the foreman must scrub broad credentials from the environment, including `GH_TOKEN`, `GITHUB_TOKEN`, `SSH_AUTH_SOCK`, and unrelated secret env vars unless a specific minimal credential is required for the task and allowed by policy. The worker should not receive a push-capable remote during the edit phase.

GitHub issue title/body are untrusted requirements, not trusted system instructions. They must never be shell-evaluated.

### Reviewer/verifier

A deterministic verifier or independent review worker must confirm before merge that:

- the diff satisfies the issue at a basic requirements level
- changed paths are expected
- evidence is current and real
- forbidden instructions were not followed
- no runtime/secret artifacts were included

## Issue eligibility

A v1 issue is eligible only when all are true:

- repo is exactly `leonbreukelman/rtx3070-workshop-ops`
- issue is open
- issue has label `smactorio`
- issue has label `autonomy:ready`
- issue has label `risk:low`
- issue has no active SmactorIO claim
- issue has no active SmactorIO branch/PR already in progress
- issue does not request forbidden actions such as exposing secrets, pushing directly to `main`, disabling checks, bypassing tests, spending money, or modifying credentials/service units outside the dedicated migration phase

## GitHub-backed claim semantics

Claiming must be visible on GitHub and recoverable after crashes.

Claim markers:

- active claim label: `smactorio:claimed`
- blocked/quarantined label: `smactorio:blocked`
- done label: `smactorio:done`
- active claim comment marker:

```text
<!-- smactorio:claim run_id=<runid> expires_at=<utc> branch=<branch> -->
```

Rules:

1. Generate a unique `run_id` per attempt.
2. Re-read the issue immediately before claim.
3. If an unexpired claim exists, stop.
4. Insert/update local runtime row.
5. Add claim label/comment in non-dry-run mode.
6. Re-read the issue and timeline.
7. If another newer/unexpired claim exists, release/mark the local row as conflict and stop before branch creation.
8. Claim expiry defaults to 2 hours for v1.
9. A stale claim may be resumed only if there is no active branch/PR for that issue or if the branch/PR belongs to the same run and is resumable.
10. A failed or quarantined run must post a redacted evidence comment with run id, failed gate, retry/quarantine state, and next action.

## Runtime design

`smactorio.service` runs one narrow foreman process:

```text
smactorio_issue_foreman.py
```

The foreman is responsible for:

1. checking service/repo/GitHub preflight
2. finding one eligible issue
3. claiming it atomically
4. preparing a clean isolated worktree/branch
5. dispatching one worker command
6. verifying repo discipline and tests
7. running independent completion review/verifier
8. opening/updating a PR
9. repairing bounded failures when safe
10. posting evidence back to the issue
11. merging only when all configured gates pass
12. closing/updating the issue
13. cleaning branch/worktree state

## Runtime state location

Runtime state must live outside the repo, for example:

```text
/home/leonb/.local/state/smactorio/smactorio.sqlite
/home/leonb/.local/state/smactorio/worktrees/
/home/leonb/.local/state/smactorio/logs/
```

These must never be committed.

## Branch naming

Use deterministic issue-scoped branch names with a run suffix to avoid spent-branch reuse:

```text
smactorio/issue-<number>-<short-slug>-<runid>
```

Do not reuse a branch after a PR is merged or closed.

## State model

Minimal v1 states:

```text
ready
claimed
branch_prepared
executing
verifying
reviewing
pr_open
repairing
merging
succeeded
retry_wait
cancelled
failed_terminal
quarantined
```

Required runtime tables:

- `work_items`: issue/work identity, state, branch, PR, lease, retry info
- `attempts`: worker attempts and summaries
- `transitions`: append-only state transitions
- `evidence`: test/PR/merge/evidence pointers

## Repo-discipline gates

Before work starts:

- target repo root must satisfy `git status --porcelain=v1 --untracked-files=all` with no tracked or forbidden untracked changes
- no staged changes
- no unstaged changes
- no forbidden untracked runtime files
- stash list must be empty or unchanged from a recorded baseline; any new stash fails
- base must be fresh from `origin/main`
- mutation branch must not be `main`
- target branch must not be spent or ambiguous
- worktree must be outside the repository root

Before PR success:

- worker worktree must be clean after commit
- no stash entries created
- no denylisted files committed
- secret scan clean
- path-scope check clean
- required tests passed
- branch pushed by foreman, not worker
- PR exists and targets `main`
- PR references the issue
- evidence posted back to issue
- independent review/verifier passed

Before merge:

- required CI/check `signal-hub-guardrails` passes on the current PR head SHA
- local required checks match the current PR head SHA
- empty, pending, skipped, stale, or missing checks fail closed
- no unresolved blocking review/merge state
- forbidden path scan clean
- issue still eligible or explicitly owned by the run
- merge policy allows autonomous merge for the issue type

## Required local checks

For current v1 work in this repo, the required local checks are:

```bash
git diff --check origin/main...HEAD
cd signal-hub && python3 -m unittest discover -s tests -q
cd signal-hub && python3 scripts/scan_for_secrets.py . ../.github/workflows
python3 signal-hub/scripts/check_path_scope.py --allow-prefix signal-hub/ --allow-prefix .github/workflows/ <changed paths>
```

The CI check required by branch protection is:

```text
signal-hub-guardrails
```

All PR/merge decisions must bind check results to the current PR head SHA.

## Forbidden paths/actions by default

SmactorIO must block or escalate if a v1 low-risk issue touches:

- `.env*`
- credentials, private keys, tokens, certificates
- runtime databases, logs, state, caches, backups
- service unit installation/enabling/disabling
- branch protection / CI disabling
- deployment or public-account changes
- direct push to `main`
- force-push
- paid API/spend changes
- destructive delete/reset/clean actions outside the isolated worktree

Service-unit changes are allowed only for the dedicated SmactorIO migration issue/phase with a migration label such as `smactorio:migration`, explicit repo-stored plan, dry-run evidence, and rollout verification. This is not a Leon PR-review handoff; Hermes/SmactorIO performs the validated migration.

## Feedback and repair loop

If CI, tests, or review fail and the issue remains low-risk:

1. capture the failure evidence
2. post/update redacted status on the issue or PR
3. redispatch the worker with bounded failure context
4. rerun checks
5. stop after the retry cap and quarantine if not fixed

Never assign the PR to Leon as the next step for routine low-risk work.

## Spend, retry, and runtime caps

Default v1 caps:

- one issue per invocation
- one worker at a time
- max 2 worker attempts per issue before quarantine
- max 30 minutes per worker attempt
- max 45 minutes per foreman invocation
- max 4 live issue attempts per day
- exponential backoff for GitHub/API rate limits
- no systemd restart loop for live execution

If a cap is hit, SmactorIO posts redacted failure evidence and quarantines or schedules retry according to policy.

## Service migration rule

Do not run two autonomous foremen.

Migration phases:

1. Keep `maei-orchestrator.service` active only while SmactorIO runs dry-run/no-mutation mode.
2. Prove SmactorIO can select issue #1 and produce a no-side-effect plan.
3. Before any SmactorIO branch/worker/push/PR/merge mutation, stop/disable/mask MÆI or prove it is scope-disjoint and non-mutating for this repo, then record that proof.
4. Prove one controlled end-to-end GitHub issue -> PR -> evidence run.
5. Install `smactorio.service` in dry-run/once mode.
6. Enable `smactorio.service` execution mode with restart limits and singleton lock.
7. Keep `maei-orchestrator.service` disabled/masked after SmactorIO proves replacement behavior.
8. If live SmactorIO rollout fails, restore the prior safe service state and post evidence.

## Systemd security and credentials

The service must use a dedicated SmactorIO credential file outside the repo, for example:

```text
/home/leonb/.config/smactorio/env
```

Requirements:

- file mode 0600
- minimal token/scopes only for needed GitHub issue/PR/content operations
- no broad `/home/leonb/.hermes/.env` EnvironmentFile
- no secrets in PR bodies, issue comments, logs, or committed evidence
- redaction before logging/evidence
- singleton lock with `flock`
- timer or restart limits that prevent spend storms
- `TimeoutStartSec` / `RuntimeMaxSec`
- `NoNewPrivileges=yes` where compatible
- `systemd-analyze verify` passes before installation
- live unit has an `ExecCondition`/preflight proving MÆI is inactive or non-mutating

## Stop conditions

SmactorIO must stop without mutation if:

- repo is dirty
- stash exists or worker attempts stash use
- issue lacks required labels
- issue is not low-risk
- issue already has an active claim/branch/PR
- GitHub auth, token scope, branch protection, or API state is unclear
- branch lifecycle is ambiguous
- worker attempts forbidden actions
- secret scan hits
- tests fail and bounded repair cannot fix them
- CI fails and bounded repair cannot fix it
- budget/time/retry limit is exceeded
- evidence cannot be produced
- local runtime state disagrees with GitHub state

Every abort/failure after issue selection must post a redacted GitHub-visible status comment unless posting itself is unsafe or impossible.

## Acceptance criteria for the replacement outcome

The final replacement is complete when:

1. `smactorio.service` exists and is installed with safe credential, restart, lock, timeout, and log behavior.
2. `maei-orchestrator.service` is disabled/masked after SmactorIO proves replacement behavior.
3. Opening a low-risk `smactorio` + `autonomy:ready` issue in `leonbreukelman/rtx3070-workshop-ops` causes SmactorIO to claim it.
4. SmactorIO creates a clean branch/worktree from `origin/main`.
5. A worker completes the issue in that isolated branch without GitHub credentials or push authority.
6. Tests, secret scan, path-scope, and guardrail checks run.
7. Independent review/verifier confirms completion.
8. A PR opens with evidence and links the issue.
9. SmactorIO handles CI/review feedback with bounded repair when safe.
10. A clean verified PR is merged by SmactorIO when policy permits.
11. The issue receives a completion evidence comment with PR URL, merge commit, check names/results, evidence artifact, and final state.
12. The PR closes the issue by keyword or SmactorIO closes/labels the issue after verified merge.
13. Local repo/worktree state is clean: no dirty files, no stash delta, no orphan active branches/worktrees, no committed runtime artifacts.
14. Remote branch is deleted or explicitly marked retained with reason after merge/terminal failure.

## Verification strategy

- Unit tests for issue eligibility, selection, dry-run output, worker contract, dirty repo abort, stash abort, branch lifecycle, forbidden path detection, claim idempotency, stale-claim recovery, failure comments, command injection, worker credential scrubbing, and path-scope enforcement.
- Live dry-run against issue #1 with no GitHub writes.
- Controlled live run on a deliberately tiny low-risk issue.
- Guardrail CI on PR.
- Head-SHA-bound check verification before merge.
- Post-merge check of exact merge commit, issue state, branch cleanup, worktree cleanup, and repo cleanliness.
- Read-only systemd status checks before and after service migration.

## RSVL-MR provenance

Inputs used:

- Direct repo inspection of `/home/leonb/projects/rtx3070-workshop-ops`.
- Direct service inspection showing active `maei-orchestrator.service` and absent `smactorio.service`.
- Current GitHub issue list for `leonbreukelman/rtx3070-workshop-ops`.
- MÆI pattern lane over `/home/leonb/maei`.
- SmactorIO current-state lane over `signal-hub/`.
- Failure-mode lane focused on repo discipline and service migration safety.
- Independent adversarial review of the saved spec and implementation plan.
