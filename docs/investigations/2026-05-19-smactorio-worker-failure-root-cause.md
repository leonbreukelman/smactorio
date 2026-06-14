# SmactorIO worker failure root-cause investigation — 2026-05-19

## Phase 0 scope

This is read-only evidence and root-cause analysis for the SmactorIO failure mode behind issue #37, plus adjacent failure-loop risks that can leave low-risk tickets in `smactorio:blocked` instead of a terminal success state.

Evidence sources inspected:

- rtx3070 checkout: `/home/leonb/projects/rtx3070-workshop-ops`
- GitHub repo: `leonbreukelman/rtx3070-workshop-ops`
- live SmactorIO systemd timer/service and recent journal
- SmactorIO runtime state DB on rtx3070
- issue #37, PR #42, PR #43
- current labels, branch protection, CI workflows/runs
- worker prompt, foreman guards, blocked-label policy, duplicate/already-satisfied code paths

Supporting raw/summarized evidence was captured under `/tmp/smactorio-phase0/` on the supervising host. Credential-like values were not retained; any credential value encountered must be represented as `[REDACTED]`.

## Current repo/runtime state at investigation time

Local and rtx3070 canonical checkouts are on `main` at:

- `7b3fbe0ee456bb77bc42c6a22aa995be846a100d`
- merge commit: `Merge pull request #43 from leonbreukelman/fix/issue-37-run-tests-wrapper`

Recent relevant commits:

- `7b3fbe0` — PR #43 merged issue #37 wrapper/defaults fix.
- `84c0339` — branch commit for `fix/issue-37-run-tests-wrapper`.
- `b82530b` — PR #42 merged generated-public-drift cleanup.
- `5dfabc4` — branch commit for `fix/smactorio-generated-side-effect-cleanup`.
- `994dca7` — SmactorIO completed issue #38 through PR #40.

SmactorIO systemd state on rtx3070:

- `smactorio.timer`: loaded, enabled, active/waiting.
- `smactorio.service`: loaded one-shot/simple service, inactive/dead after successful run, `Result=success`, `ExecMainStatus=0`.
- service command: runs `signal-hub/scripts/smactorio_issue_foreman.py` with repo `leonbreukelman/rtx3070-workshop-ops`, repo root `/home/leonb/projects/rtx3070-workshop-ops`, base `main`, and state DB `/home/leonb/.local/state/smactorio/smactorio.sqlite`.
- service uses dedicated SmactorIO Hermes/GitHub config paths and a service attestation environment variable; credential values were not inspected.

## GitHub control-plane state

Relevant labels exist:

- `smactorio`
- `autonomy:ready`
- `risk:low`
- `type:docs`
- `smactorio:claimed`
- `smactorio:blocked`
- `smactorio:done`
- `smactorio:needs-attention`
- `duplicate`

`main` branch protection:

- strict required status check: `signal-hub-guardrails`
- admin enforcement: enabled
- required conversation resolution: enabled
- force pushes/deletions disabled
- no required PR reviews configured

Active workflows:

- `Signal Hub guardrails`
- `Copilot`

Recent CI evidence:

- PR #43 branch first had a failing `Signal Hub guardrails` run, then later green runs; final merge to `main` passed.
- PR #42 branch passed `Signal Hub guardrails`; merge to `main` passed.
- PR #40 / issue #38 SmactorIO path passed guardrails and merged, showing the foreman can complete some low-risk tickets end-to-end.

## Issue #37 evidence

Issue URL: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/37

Issue #37 body included the hidden project-improvement marker:

- candidate id: `pic_smactorio_0ba7cbcbe952`
- dedupe key: `sha256:68ba2bd9056e96511691fe5261f6c0f0aa6c84ed38aed78f92f126b72d56306d`

Issue #37 requested:

- generated issue/runbook verification commands must match commands that exist in the repository;
- documented verification path must be exercised or replaced with the repository's real test command.

The generated verification command was:

```bash
scripts/run_tests.sh signal-hub/tests/ -v
git diff --check
python3 signal-hub/scripts/scan_for_secrets.py signal-hub/docs signal-hub/scripts signal-hub/tests
```

At investigation time issue #37 is closed as completed, has `smactorio:done`, and is closed by PR #43.

## PR evidence

PR #42: https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/42

- Merged: `b82530ba16597bd7c013a424535aa5cf94b3f09e`
- Purpose: discard worker-side generated `signal-hub/public/` HTML drift before the hard clean-worktree gate while preserving unknown source changes.
- Guardrails: `signal-hub-guardrails` success.
- Copilot review ran and commented.

PR #43: https://github.com/leonbreukelman/rtx3070-workshop-ops/pull/43

- Merged: `7b3fbe0ee456bb77bc42c6a22aa995be846a100d`
- Closes: issue #37.
- Purpose: add executable `signal-hub/scripts/run_tests.sh`, update project-improvement verification defaults to use it, teach processor that the wrapper satisfies historical `scripts/run_tests.sh` references, handle selectors/verbosity, reject ambiguous multiple directory selectors.
- Guardrails: one initial branch run failed, later branch runs succeeded, final merge to `main` succeeded.
- Copilot review ran and commented.

## Runtime lifecycle evidence for issue #37

State DB transitions for issue #37 show three SmactorIO attempts.

Attempt 1 — run `20260518T234049-18b0cd5c55df851f`:

- `planned -> preflight`
- `preflight -> claimed`
- `claimed -> worker_running`
- `running -> blocked`
- blocker: worktree dirty with generated public HTML changes under `signal-hub/public/...`.

Attempt 2 — run `20260519T023922-18b0d71a9b40b8f7`:

- manual retry comment removed stale `smactorio:blocked` after canonical checkout was clean;
- `planned -> preflight`
- `preflight -> claimed`
- `claimed -> worker_running`
- `running -> blocked`
- same blocker: generated public HTML drift left the worker checkout dirty.

Attempt 3 — run `20260519T024622-18b0d77c8d673430` after PR #42:

- `planned -> preflight`
- `preflight -> claimed`
- `claimed -> worker_running`
- `worker_running -> worker_done`, material change recorded as `signal-hub/docs/project-improvement-processor-runbook.md`
- `worker_done -> verified`, local verification passed
- `running -> blocked`, independent review blocked.

Independent review blockers from attempt 3:

- verification artifact contained broad raw dumps, file hashes, absolute runtime paths, and generated HTML render artifacts;
- change was only a minor runbook command swap plus oversized verification log;
- no evidence that generated verification commands became executable, such as wrapper creation, chmod/shebang, or generation-default updates;
- tests/evidence were noisy rather than targeted.

Then PR #43 was created/merged outside the SmactorIO worker path and issue #37 was closed with a human/supervising comment.

## Code-path evidence

### Eligibility and blocked semantics

`signal-hub/scripts/smactorio_policy.py` requires open issues to have:

- `smactorio`
- `autonomy:ready`
- `risk:low`

It treats these labels as blocked/terminal for normal pickup:

- `smactorio:claimed`
- `smactorio:blocked`
- `smactorio:done`
- `blocked`, `blocked:human`, `blocked:external`
- high-risk labels and human-blocked labels

This means a `smactorio:blocked` label quarantines a ticket from normal retries until some process removes it or resolves it terminally.

### Worker prompt

The current worker prompt requires:

- no GitHub writes by the worker;
- strict TDD for behavior changes;
- targeted checks;
- local commit for completed implementation;
- if already satisfied, no commits and final stdout line exactly `SMACTORIO_OUTCOME: ALREADY_SATISFIED`.

This already-satisfied stdout contract exists now, but #37 showed the wider lifecycle still lacks a complete retry/classification campaign across edge cases.

### Foreman guards

The foreman currently has several important guards:

- rejects worker output that only changes `signal-hub/docs/verification/` artifacts;
- independent review rejects secrets, runtime state, broad raw dumps, unsafe paths, and unmeaningful evidence;
- detects final-line `SMACTORIO_OUTCOME: ALREADY_SATISFIED` and can complete an issue without PR when the worker produces no commits;
- comments, applies `smactorio:done`, removes claim/block labels, and closes already-satisfied issues;
- removes expired claim labels so crashes do not leave permanent `smactorio:claimed` limbo;
- now discards safe worker-side generated `signal-hub/public/` drift before the clean gate;
- safe `git diff --check` trailing-whitespace auto-repair exists for allowed prefixes;
- PR merge waits for required `signal-hub-guardrails` status and head-SHA match.

### Publisher/dedupe logic

`project_improvement_processor.py` now includes:

- GitHub issue search across configured states, including open and closed states by default;
- generated issue marker matching by candidate id and dedupe key;
- prioritization of open unblocked matching issues, then terminal matching issues;
- terminal link outcome for closed or terminal-labeled existing issues;
- semantic similar-issue linking;
- durable local candidate-state dedupe, including `done`, `published`, `claimed`, `blocked`, and prior-improvement records;
- detection that either root `scripts/run_tests.sh` or allowed `signal-hub/scripts/run_tests.sh` satisfies the historical missing-command signal.

## Root cause summary

Issue #37 did not remain open because the requested work was inherently hard. It remained open/blocked because the operating loop did not yet have a reliable lifecycle contract for low-risk tickets across retryable failures, safe remediation, review failures, and terminal duplicate/already-satisfied outcomes.

The concrete failure chain was:

1. The project-improvement publisher generated a valid low-risk issue whose verification command referenced a non-existent/disallowed `scripts/run_tests.sh` path.
2. SmactorIO correctly claimed the eligible issue.
3. The worker/test path generated `signal-hub/public/` HTML drift.
4. The foreman's hard clean-worktree gate treated that drift as a blocker, not as a safe verification side effect to discard. The blocked label then quarantined the issue from normal retries.
5. After a manual stale-blocked retry, the same dirty-worktree failure repeated.
6. PR #42 patched that single dirty-worktree symptom.
7. On the next retry, the worker produced insufficient implementation and noisy evidence. Independent review correctly blocked the PR path instead of merging a weak/noisy change.
8. PR #43 then fixed the underlying missing executable wrapper/generation-default/dedupe behavior and closed #37, but this was a supervising/manual takeover path, not proof that SmactorIO autonomously resolves this class end-to-end.

The system has useful pieces now, but the root reliability defect is still broader than any one patch: `smactorio:blocked` currently collapses retryable mechanical failures, reviewer-remediable implementation defects, stale claims, true external blockers, duplicates, and already-satisfied work into a skip label that requires external intervention unless a special path has been explicitly tested.

## Failure-loop classes observed or implied by current code

1. Retryable generated drift can become terminal `smactorio:blocked` unless classified and cleaned before the hard gate.
2. Reviewable implementation defects can become terminal `smactorio:blocked` instead of a bounded repair loop.
3. `smactorio:blocked` blocks normal pickup even when the blocker has since become stale or safe to retry.
4. Already-satisfied and duplicate terminal paths exist in code, but need end-to-end live validation and stronger evidence rules.
5. Publisher dedupe must consistently search open and closed issues plus durable local state to avoid regenerating completed work.
6. Verification artifacts need capping/redaction; broad raw dumps can make an otherwise simple ticket fail review.
7. Generated verification commands must be generated from executable, allowed, repo-local commands and must handle selectors/verbosity deterministically.
8. Branch protection and CI status checks are strict; failure classification must distinguish pending/race, failed checks, base-update needed, review comments, and true blockers.
9. GitHub foreman lane and runtime-local lane must remain separate in evidence and status reporting.
10. Self-repair tickets for SmactorIO can be hazardous if the broken worker consumes its own repair issue without bounded recovery.

## Phase 0 conclusion

The complaint is valid. Issue #37 should have reached either:

- a merged PR through SmactorIO that added the executable wrapper/defaults/dedupe fix; or
- a structured terminal duplicate/already-satisfied outcome with evidence; or
- a structured true-blocked outcome only if the next action truly required unsafe/human-only intervention.

Instead, it entered repeated `smactorio:blocked` states for fixable mechanical and reviewable defects, then was resolved by manual/supervising PR takeover. The hardening target must be an explicit issue lifecycle contract with terminal states, retry policies, safe auto-remediation classes, evidence schema, review/CI repair loops, stale-label cleanup, and a real 20+ ticket E2E campaign.

## Phase 1+ research questions

Research/spec must cover at minimum:

- terminal-state design for done, duplicate, already-satisfied, true-blocked, retryable-failed;
- when safe remediation is allowed versus when to stop as a true blocker;
- bounded retry/backoff and stalled-retry detection;
- dirty-worktree classification, generated artifact cleanup, and unknown-source preservation;
- CI failure classification and branch-protection merge handling;
- PR review-comment resolution and conversation-resolution protection;
- stale `smactorio:blocked` cleanup without unsafe blind retries;
- duplicate search across open/closed GitHub issues and local durable state;
- artifact-only PR avoidance and no-PR terminal outcomes;
- self-repair ticket safeguards;
- worker prompt versus foreman guard contradiction tests;
- separation between live runtime lane and GitHub issue foreman lane;
- evidence retention with redaction/capping;
- a deterministic harness for real GitHub ticket campaigns.
