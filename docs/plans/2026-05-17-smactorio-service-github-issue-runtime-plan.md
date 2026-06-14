# SmactorIO Service GitHub-Issue Runtime Implementation Plan

> **For Hermes:** Use subagent-driven-development for implementation. Keep the user-facing story simple: GitHub issues in, verified PRs out. Do not hand PR/code decisions to Leon.

Date: 2026-05-17
Status: reviewed plan
Target repo: `/home/leonb/projects/rtx3070-workshop-ops`
Base branch: `main`
Primary spec: `signal-hub/docs/specs/2026-05-17-smactorio-service-github-issue-runtime-spec.md`

## Goal

Build the replacement runtime where `smactorio.service` watches GitHub issues in `leonbreukelman/rtx3070-workshop-ops` and works eligible tickets through claim, branch, isolated worker, tests, review, PR, repair, evidence, safe merge, issue closure, and cleanup.

## Delivery rule

Leon is not the code reviewer or merge operator. Each implementation slice must either:

- merge a verified clean PR autonomously when gates pass, or
- quarantine/fail with GitHub-visible evidence and a clear next automated step.

Do not stop with “Leon should review this PR.”

## Architecture summary

- GitHub Issues are the inbox.
- SmactorIO is the foreman.
- Coding/review/test workers are executors.
- Foreman owns GitHub mutations and git push/merge authority.
- Workers edit isolated worktrees without broad secrets or push authority.
- GitHub comments/branches/PRs/checks are the visible proof trail.
- Runtime state lives outside the repo.
- MÆI is disabled before any non-dry-run SmactorIO mutation for this repo.

## Implementation milestones

### Milestone 0: Policy/config skeleton

Purpose: define exact gates before code starts mutating anything.

Files:

- Create: `signal-hub/scripts/smactorio_policy.py`
- Create/modify tests in: `signal-hub/tests/test_smactorio_issue_foreman.py`

Behavior:

- Repo is fixed to `leonbreukelman/rtx3070-workshop-ops` for v1.
- Required issue labels: `smactorio`, `autonomy:ready`, `risk:low`.
- Required CI check: `signal-hub-guardrails`.
- Required local commands:

```bash
git diff --check origin/main...HEAD
cd signal-hub && python3 -m unittest discover -s tests -q
cd signal-hub && python3 scripts/scan_for_secrets.py . ../.github/workflows
python3 signal-hub/scripts/check_path_scope.py --allow-prefix signal-hub/ --allow-prefix .github/workflows/ <changed paths>
```

- Default caps:
  - one issue per invocation
  - one worker at a time
  - max 2 worker attempts per issue
  - max 30 minutes per worker attempt
  - max 45 minutes per foreman run
  - max 4 live issue attempts per day
- Forbidden paths/actions include secrets, env files, runtime DB/log/state/cache/backup files, service unit changes, CI disabling, direct `main` push, force-push, paid/spend changes, and destructive cleanup outside the isolated worktree.
- Service unit changes require a dedicated migration label/phase, not ordinary low-risk automation.

TDD tasks:

1. Test policy exposes exact required labels/checks/commands.
2. Test ordinary low-risk issue cannot touch service units.
3. Test dedicated migration policy can allow service-unit files only with migration gate.
4. Test caps are loaded and enforceable.

### Milestone 1: GitHub issue foreman dry-run

Purpose: prove SmactorIO can see GitHub issues and select the next safe ticket without side effects.

Files:

- Create: `signal-hub/scripts/smactorio_issue_foreman.py`
- Create/modify: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify only if needed: `signal-hub/README.md`

Behavior:

- CLI command:

```bash
cd signal-hub
python3 scripts/smactorio_issue_foreman.py --repo leonbreukelman/rtx3070-workshop-ops --once --dry-run
```

- Reads open GitHub issues through `gh issue list`.
- Selects the oldest issue with labels:
  - `smactorio`
  - `autonomy:ready`
  - `risk:low`
- Emits one JSON object.
- Does not touch `state/signal_loop.db`.
- Does not read `data/smactorio/improvement_candidates.json`.
- Does not create comments, labels, branches, commits, pushes, PRs, or merges in dry-run mode.
- Issue title/body are parsed as data and never shell-evaluated.

Required JSON fields:

```json
{
  "status": "dry_run",
  "selected_issue_number": 1,
  "selected_issue_url": "...",
  "selected_issue_title": "...",
  "labels": ["..."],
  "branch_name": "smactorio/issue-1-...",
  "worker_env": {"SMACTORIO_ISSUE_NUMBER": "1"},
  "planned_worker_command": null,
  "errors": []
}
```

TDD tasks:

1. Write a test that fake-`gh` returns two issues and only the eligible low-risk issue is selected.
2. Run the test and confirm it fails because the foreman does not exist.
3. Implement minimal issue parsing/selection.
4. Run the focused test and confirm pass.
5. Add tests for missing labels, closed issues, no issues, malformed gh JSON, deterministic branch slug, existing claim, existing branch/PR, and command-injection strings in title/body.
6. Add dry-run no-side-effect test by injecting fake `gh` runner and asserting no write commands are called.
7. Run:

```bash
cd signal-hub
python3 -m unittest tests.test_smactorio_issue_foreman -q
python3 -m unittest discover -s tests -q
python3 scripts/scan_for_secrets.py . ../.github/workflows
python3 scripts/check_path_scope.py --allow-prefix signal-hub/ --allow-prefix .github/workflows/ signal-hub/scripts/smactorio_issue_foreman.py signal-hub/tests/test_smactorio_issue_foreman.py
```

Live verification:

```bash
cd signal-hub
python3 scripts/smactorio_issue_foreman.py --repo leonbreukelman/rtx3070-workshop-ops --once --dry-run
```

Expected: selects issue #1 and writes no GitHub mutations.

### Milestone 2: Runtime state and GitHub-backed claim discipline

Purpose: make issue claiming durable and idempotent without letting SQLite become the backlog.

Files:

- Create: `signal-hub/scripts/smactorio_runtime_state.py`
- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Modify: `signal-hub/tests/test_smactorio_issue_foreman.py`

Behavior:

- Runtime DB path defaults outside repo:

```text
/home/leonb/.local/state/smactorio/smactorio.sqlite
```

- SQLite records work history, attempts, transitions, evidence.
- GitHub remains source of truth.
- Claim label/comment contract:
  - label: `smactorio:claimed`
  - claim marker: `<!-- smactorio:claim run_id=<runid> expires_at=<utc> branch=<branch> -->`
  - expiry: 2 hours for v1
- Claiming sequence:
  1. re-read issue
  2. verify eligible
  3. reject active unexpired claim
  4. insert/claim local work row
  5. add GitHub claim label/comment only in non-dry-run mode
  6. re-read issue/timeline
  7. stop before branch creation on conflict

TDD tasks:

1. Test DB initializes outside repo and creates expected tables.
2. Test duplicate issue creates one work row.
3. Test two foremen racing produce exactly one active claim.
4. Test expired claim can be retried or resumed only when branch/PR state permits.
5. Test dry-run does not write DB unless explicitly passed `--record-dry-run`.
6. Test claim conflict stops before branch creation.
7. Test failure after issue selection posts redacted failure evidence.

Verification:

```bash
cd signal-hub
python3 -m unittest tests.test_smactorio_issue_foreman -q
python3 -m unittest discover -s tests -q
git status --short --ignored
```

Expected: no runtime DB/log/state files are tracked or staged.

### Milestone 3: Repo hygiene and branch guard

Purpose: prevent dirty repos, stashes, spent branches, direct main pushes, and orphan mess.

Files:

- Create: `signal-hub/scripts/smactorio_repo_guard.py`
- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Create or modify tests in `signal-hub/tests/test_smactorio_issue_foreman.py`

Behavior:

Before worker execution, block if:

- `git status --porcelain=v1 --untracked-files=all` shows tracked or forbidden untracked changes
- repo has staged changes
- repo has unstaged changes
- forbidden runtime files exist
- stash baseline changes
- current mutation branch is `main`
- target branch already exists with merged/closed PR
- remote/GitHub state cannot be verified

Use isolated worktrees under outside-repo runtime state:

```text
/home/leonb/.local/state/smactorio/worktrees/<runid>/
```

TDD tasks:

1. Test clean repo passes.
2. Test unstaged dirty file aborts.
3. Test staged file aborts.
4. Test stash aborts and stash delta aborts.
5. Test forbidden runtime file aborts.
6. Test existing active PR allows resume only for same run/issue.
7. Test spent branch blocks reuse.
8. Test worktree path is outside the repo.
9. Test root repo and worktree are clean after terminal success/failure.

Verification:

```bash
cd signal-hub
python3 -m unittest tests.test_smactorio_issue_foreman -q
python3 -m unittest discover -s tests -q
git status --short --branch
```

### Milestone 4: Worker sandbox contract with fake worker

Purpose: prove foreman-to-worker execution without giving the worker GitHub authority.

Files:

- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Modify: `signal-hub/tests/test_smactorio_issue_foreman.py`

Behavior:

- Add `--worker-cmd` as an argv/config value, not a shell-interpolated string.
- Foreman passes issue data through environment variables:
  - `SMACTORIO_REPO`
  - `SMACTORIO_ISSUE_NUMBER`
  - `SMACTORIO_ISSUE_URL`
  - `SMACTORIO_ISSUE_TITLE`
  - `SMACTORIO_BRANCH`
  - `SMACTORIO_WORKTREE`
- Foreman scrubs `GH_TOKEN`, `GITHUB_TOKEN`, `SSH_AUTH_SOCK`, broad env secrets, and unrelated credential variables before worker execution.
- Worker has no push-capable remote during the edit phase where feasible.
- Fake worker tests can exit 0 or nonzero.
- Nonzero worker result records failure and does not mark success.

TDD tasks:

1. Test fake worker receives expected environment.
2. Test worker success advances to verification-needed state.
3. Test worker failure records failure and leaves issue actionable.
4. Test worker cannot run when repo guard fails.
5. Test worker cannot perform `git push`, `gh pr`, `gh issue`, or read scrubbed secret env.
6. Test worker command and issue body/title injection attempts are not shell-executed.

Verification:

```bash
cd signal-hub
python3 -m unittest tests.test_smactorio_issue_foreman -q
python3 -m unittest discover -s tests -q
```

### Milestone 5: PR/evidence path for one controlled issue

Purpose: move from dry-run to a real branch/PR for a deliberately tiny low-risk issue.

Files:

- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Create if useful: `signal-hub/scripts/smactorio_pr_verifier.py`
- Modify tests.

Behavior:

- Before non-dry-run mutation, prove `maei-orchestrator.service` is inactive/non-mutating for this repo or stop it for the controlled run and record proof.
- Foreman creates branch/worktree.
- Worker makes the change and commits locally.
- Foreman runs required local checks:

```bash
git diff --check origin/main...HEAD
cd signal-hub && python3 -m unittest discover -s tests -q
cd signal-hub && python3 scripts/scan_for_secrets.py . ../.github/workflows
python3 signal-hub/scripts/check_path_scope.py --allow-prefix signal-hub/ --allow-prefix .github/workflows/ <changed paths>
```

- Foreman pushes branch.
- Foreman opens/updates PR linking issue.
- Foreman posts evidence comment to issue.
- No auto-merge in this milestone; the next milestones add review/repair/merge so the final system does not hand work to Leon.

TDD tasks:

1. Test PR body includes issue link and evidence summary.
2. Test failed tests block PR success.
3. Test secret scan failure blocks PR success and redacts evidence.
4. Test forbidden path blocks PR success.
5. Test GitHub command failures fail closed.
6. Test worker-created runtime/log/db files are not committed.
7. Test branch is pushed by foreman only.

Live controlled test:

- Create or use a tiny low-risk `smactorio` issue.
- Let SmactorIO create branch/PR/evidence.
- Verify PR checks.
- Continue immediately into review/repair/merge milestones rather than handing the PR to Leon.

### Milestone 6: Independent review and repair loop

Purpose: make SmactorIO handle PR quality and feedback instead of stopping at “PR open”.

Files:

- Create if useful: `signal-hub/scripts/smactorio_review_worker.py`
- Create if useful: `signal-hub/scripts/smactorio_repair_loop.py`
- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Modify tests.

Behavior:

- Run deterministic verifier or independent review worker after PR creation/update.
- Verify the diff satisfies the issue, expected paths changed, evidence is current, and no forbidden instruction was followed.
- Read PR check state and bind it to current head SHA.
- If CI/review fails and work remains low-risk:
  1. capture failure evidence
  2. redispatch worker with bounded failure context
  3. push fix commit through foreman
  4. rerun checks
  5. stop at retry cap and quarantine if unresolved
- Never assign routine low-risk PR repair to Leon.

TDD tasks:

1. Test review worker pass is required before merge.
2. Test review failure triggers bounded repair.
3. Test CI failure triggers bounded repair.
4. Test same failure twice quarantines.
5. Test issue gets redacted failure/quarantine comment.
6. Test high-risk label added during repair blocks further mutation.

### Milestone 7: Safe merge policy and issue closure

Purpose: allow SmactorIO to merge clean PRs without handing routine work to Leon.

Files:

- Modify: `signal-hub/scripts/smactorio_issue_foreman.py`
- Create if useful: `signal-hub/scripts/smactorio_merge_policy.py`
- Modify tests.

Behavior:

Autonomous merge allowed only if:

- issue was eligible at claim time and remains owned by the run
- PR targets `main`
- PR references issue and uses a closing keyword or closure plan
- required local checks passed on current head
- required CI check `signal-hub-guardrails` passed on current PR head SHA
- no empty, pending, skipped, stale, or missing required checks
- no forbidden paths
- independent review/verifier passed
- no unresolved review/merge block
- no high-risk label was added
- branch is current or safely mergeable

After merge:

- post completion comment with PR URL, merge commit, check names/results, evidence artifact, and final state
- close/label issue if not closed by PR keyword
- delete remote branch or mark retained with reason
- remove local worktree
- verify root repo clean and no stash delta

TDD tasks:

1. Test green PR can merge when merge policy gates pass.
2. Test red/pending/missing/stale/skipped CI blocks merge.
3. Test unresolved review blocks merge.
4. Test high-risk label added after claim blocks merge.
5. Test completion comment includes PR, merge commit, checks, evidence, and final state.
6. Test issue closes/labels after merge.
7. Test branch/worktree cleanup after merge and after terminal failure.

Verification:

```bash
gh pr view <PR> --json number,state,mergeStateStatus,statusCheckRollup,headRefOid,mergedAt,mergeCommit,url
gh issue view <ISSUE> --json number,state,labels,comments,url
git status --porcelain=v1 --untracked-files=all
git stash list
```

### Milestone 8: systemd service replacement

Purpose: install the new runtime and retire the old service safely.

Files:

- Create: `infra/systemd/system/smactorio.service`
- Create: `infra/systemd/system/smactorio.timer`
- Create: `signal-hub/docs/verification/YYYY-MM-DD-smactorio-service-rollout.md`

Dedicated credentials:

```text
/home/leonb/.config/smactorio/env
```

Requirements:

- mode 0600
- minimal GitHub token/scopes only
- no broad `/home/leonb/.hermes/.env` EnvironmentFile
- no secrets in logs/evidence

Recommended first service mode:

```ini
[Unit]
Description=SmactorIO GitHub Issue Runtime
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=leonb
WorkingDirectory=/home/leonb/projects/rtx3070-workshop-ops/signal-hub
Environment=HOME=/home/leonb
EnvironmentFile=/home/leonb/.config/smactorio/env
ExecCondition=/usr/bin/python3 scripts/smactorio_issue_foreman.py --preflight-systemd --require-maei-inactive-or-nonmutating
ExecStartPre=/usr/bin/mkdir -p /home/leonb/.local/state/smactorio
ExecStart=/usr/bin/flock -n /home/leonb/.local/state/smactorio/smactorio.lock /usr/bin/python3 scripts/smactorio_issue_foreman.py --repo leonbreukelman/rtx3070-workshop-ops --once --dry-run
TimeoutStartSec=300
RuntimeMaxSec=2700
NoNewPrivileges=yes
```

Use a timer first to avoid restart-loop spend storms.

Rollout sequence:

1. Install dry-run service/timer only.
2. Run `systemd-analyze verify` on service/timer files.
3. Run `systemctl daemon-reload`.
4. Run one manual dry-run unit.
5. Verify logs show selected issue and no mutation.
6. Stop/disable/mask `maei-orchestrator.service` before live SmactorIO mutation for this repo.
7. Run one controlled live PR path manually outside systemd.
8. Change service from dry-run to execution mode only after controlled live path passes.
9. Verify `maei-orchestrator.service` stopped/disabled/masked and `smactorio.service`/timer healthy.
10. If rollout fails, restore prior safe service state and post verification evidence.

Commands for rollout verification:

```bash
systemctl status maei-orchestrator.service --no-pager
systemctl status smactorio.service --no-pager
systemctl list-timers --all --no-pager
journalctl -u smactorio.service -n 100 --no-pager
systemd-analyze verify infra/systemd/system/smactorio.service infra/systemd/system/smactorio.timer
```

## Commit/PR expectations

Each milestone should be its own branch/PR unless a slice is tiny and review-proven safe.

Branch naming:

```text
smactorio/policy-skeleton
smactorio/github-issue-foreman
smactorio/runtime-state-claims
smactorio/repo-guard
smactorio/worker-contract
smactorio/pr-evidence-path
smactorio/review-repair-loop
smactorio/merge-policy
smactorio/service-rollout
```

Before every PR:

```bash
git status --short --branch
git diff --check
cd signal-hub && python3 -m unittest discover -s tests -q
cd signal-hub && python3 scripts/scan_for_secrets.py . ../.github/workflows
python3 signal-hub/scripts/check_path_scope.py --allow-prefix signal-hub/ --allow-prefix .github/workflows/ <changed paths>
```

Stage explicit paths only. Never use `git add -A` in a mixed tree.

## First implementation session recommendation

Start with Milestone 0 and Milestone 1.

That is the smallest useful slice:

```text
Policy is explicit.
GitHub issue #1 is visible to SmactorIO.
SmactorIO can select it safely.
No side effects happen yet.
The old local SQLite candidate machinery is no longer the future inbox.
```

After that is merged, continue milestone by milestone until service replacement is safe.

## True blockers

None for writing or starting Milestones 0-1.

Do not disable `maei-orchestrator.service` for dry-run planning. Do disable/stop/mask it before non-dry-run SmactorIO mutation for this repo unless a documented preflight proves it is non-mutating and scope-disjoint.
