# SmactorIO autonomous ticket resolution contract — 2026-05-19

## Status

Reviewed-draft contract for hardening SmactorIO so eligible low-risk GitHub issues reach an explicit terminal outcome without “simple to fix but blocked” loops.

Inputs:

- Phase 0 investigation: `signal-hub/docs/investigations/2026-05-19-smactorio-worker-failure-root-cause.md`
- Phase 1 research matrix: `signal-hub/docs/research/2026-05-19-autonomous-issue-worker-patterns.md`
- Model research/audits:
  - `signal-hub/docs/verification/2026-05-19-smactorio-model-backend-discovery.md`
  - `signal-hub/docs/verification/2026-05-19-smactorio-model-research-gemini.md`
  - `signal-hub/docs/verification/2026-05-19-smactorio-model-audit-codex.md`
  - `signal-hub/docs/verification/2026-05-19-smactorio-model-audit-copilot.md`
  - `signal-hub/docs/verification/2026-05-19-smactorio-opus-spec-review.md`

This contract intentionally separates retryable/revision gates from terminal blockers. `smactorio:blocked` is not allowed to be the first response to a deterministic, low-risk, auto-repairable failure.

## Goals

1. Eligible low-risk GitHub issues are autonomously processed end-to-end.
2. Each issue reaches exactly one explicit terminal outcome:
   - merged PR closes the issue;
   - duplicate close/link with evidence;
   - already-satisfied close with evidence;
   - true-blocked terminal outcome with evidence;
   - retry-exhausted terminal outcome with evidence and no silent loop.
3. Safe mechanical failures are classified and remediated before any terminal blocker label is applied.
4. Issue labels are a projection of state, not a permanent failure memory.
5. Evidence is concise, redacted, capped, and durable enough to audit.
6. The E2E campaign proves the real GitHub issue foreman/worker path, not manual supervisor closure.

## Non-goals

- No broad rewrite of SmactorIO architecture unless a test proves the current shape cannot satisfy this contract.
- No admin bypass of branch protection.
- No autonomous changes to secrets, credentials, billing, 2FA, destructive operations, external production systems, or public/social account state.
- No low-risk lane changes to GitHub Actions workflow files unless a separate higher-trust approval label is present.
- No counting runtime-local Signal Hub work-order skips/failures as GitHub ticket completion.

## Definitions

- **Foreman**: `signal-hub/scripts/smactorio_issue_foreman.py`; owns issue eligibility, claim lease, worker launch, validation, PR/check/merge, and terminal comments/labels.
- **Worker**: the coding agent subprocess launched by the foreman. It may edit only the isolated worktree and must not write GitHub state directly.
- **Publisher**: `signal-hub/scripts/project_improvement_processor.py`; creates or links generated improvement issues.
- **GitHub issue lane**: repo-backed issue -> branch -> PR -> checks -> merge/close path. This is the only lane counted in the 20-ticket campaign.
- **Runtime-local lane**: Signal Hub local work-order path. It may be health evidence but never ticket completion evidence.
- **Safe auto-remediation**: deterministic, allowlisted repair under existing low-risk scope, e.g. generated artifact cleanup, trailing whitespace repair, executable bit on a new script, default verification selector normalization.
- **True blocker**: a condition requiring external authority or unsafe action: missing credentials/2FA, destructive or out-of-scope mutation, public/social account action, billing/spend, security policy decision, human product judgment, or unclassified CI/review failure after retry cap.

## Issue lifecycle state machine

The state machine is persisted in the SmactorIO runtime DB and projected onto GitHub labels/comments.

### Nonterminal states

1. `queued`
   - Issue is open.
   - Required labels are present.
   - No active terminal or blocking labels remain after stale-label reconciliation.

2. `preflight`
   - Foreman verifies repo path, clean base checkout, branch protection metadata, required scripts, worker provider smoke check, no in-progress claim for the issue, and issue still eligible.
   - Preflight may produce `quarantined_self_repair`, `true_blocked`, or `queued`.

3. `claimed`
   - Foreman writes a claim lease label/comment with run id, branch name, expiry, base SHA, and a fencing token.
   - The runtime DB has a nonterminal unique row for `(repo, issue_number)` or an equivalent fencing invariant.

4. `worker_running`
   - Worker is running in an isolated worktree.
   - Worker has no GitHub write authority.
   - Worker receives explicit outcome contract and verification command contract.

5. `worker_done`
   - Worker exited 0 and produced material commits or a structured no-PR terminal outcome.
   - Foreman re-checks issue labels/state before continuing.

6. `needs_revision`
   - Worker, review, CI, or merge gates produced a safe actionable revision within retry cap.
   - The foreman may relaunch worker or apply a deterministic repair.

7. `verified`
   - Local verification succeeded.
   - Dirty-worktree classifier reports clean or only safe-cleaned verification side effects.

8. `reviewed`
   - Independent model/local review passes, with final marker contract enforced.
   - Review output is redacted/capped and never committed as an artifact-only PR.

9. `pr_open`
   - PR exists for expected branch/head and mentions/closes the issue.
   - PR metadata, expected head SHA, base SHA, and check names are recorded.

10. `ci_pending`
    - Required checks are missing/pending and still inside polling/backoff budget.

11. `ci_failed_retryable`
    - Required check failed with a classified safe signature and retry budget remains.

12. `review_changes_requested`
    - PR reviews/comments/threads are actionable under low-risk scope and retry budget remains.

13. `base_update_needed`
    - Strict branch protection or merge state reports branch behind/stale but branch can be updated safely.

14. `stale_claim_recovered`
    - Prior claim lease expired or run died. Claim label is removed only after proving no active worker owns the fence.

15. `stale_blocked_reconsidered`
    - Open issue has `smactorio:blocked` from an older safe/retryable failure. Foreman has classified it as retryable under the new code and removed/replaced labels with evidence.

### Terminal states

1. `merged`
   - PR merged with expected head SHA.
   - Required check(s) passed on the PR head.
   - Issue is closed by PR or foreman follow-up.
   - Labels include `smactorio:done`; labels do not include `smactorio:blocked`, `smactorio:claimed`, or `autonomy:ready` unless policy intentionally keeps a closed issue queryable.

2. `duplicate`
   - Foreman or publisher identifies canonical issue/PR/commit.
   - Current issue is closed or marked duplicate with comment evidence.
   - No PR is opened for the duplicate.

3. `already_satisfied`
   - Base checkout already satisfies acceptance criteria.
   - Worker/foreman provide structured evidence with commands, files inspected, criteria status, and zero-diff proof.
   - No PR is opened.

4. `true_blocked`
   - Work requires unsafe/external human action.
   - Issue gets `smactorio:blocked` and `smactorio:needs-attention` with a specific blocker class.

5. `retry_exhausted`
   - Safe retry budget or wall-clock age cap exhausted.
   - Issue gets `smactorio:needs-attention`; `smactorio:blocked` is allowed only with the explicit class `retry_exhausted`, not as a generic catch-all.

6. `abandoned_safety`
   - Foreman detects tampering, privilege-boundary change, out-of-scope mutation, or unredactable evidence.
   - Issue is left for human intervention with labels/comments; no branch/PR merge occurs.

## Eligibility rules

An issue is eligible only if all are true:

- State is open.
- Required labels include `smactorio`, `risk:low`, and `autonomy:ready`.
- No active `smactorio:claimed` lease owned by another live run.
- No terminal labels: `smactorio:done`, `duplicate` with closed state, or equivalent terminal marker.
- No true-blocked/retry-exhausted label unless stale-blocked reconciliation explicitly reclassifies it as retryable.
- Title, body, acceptance criteria, likely files, comments, and labels do not request forbidden action: credentials/secrets, billing, 2FA, destructive operations, public/social account mutation, external production mutation, or human product/legal judgment.
- Scope is within allowed paths for the low-risk lane:
  - `signal-hub/docs/**`
  - `signal-hub/tests/**`
  - `signal-hub/scripts/**` except self-repair quarantine paths unless approved
  - non-sensitive generated public artifacts only when explicitly part of acceptance
  - no `.github/workflows/**` in the default low-risk lane.
- Self-repair quarantine: if title/body/acceptance/likely files touch any of the core SmactorIO runtime files, eligibility requires `autonomy:smactorio-self-repair-approved` or the issue is commented/quarantined without worker launch.

## Claim rules

- Claim is a lease, not success.
- Claim comment includes run id, issue number, branch, base SHA, expiry timestamp, and fencing token.
- Claim label `smactorio:claimed` is applied only after preflight passes.
- Before every GitHub mutation after claim, foreman re-reads issue state/labels and verifies the fence still belongs to the current run.
- Claim TTL must exceed maximum worker/retry cycle or be renewed explicitly. Claim TTL and worker timeout cannot drift independently without a test.
- If foreman crashes, next run recovers expired claims after proving no worker process still owns the fence.
- If a human closes the issue or removes `autonomy:ready` mid-run, foreman releases claim and stops without applying `smactorio:blocked`.

## Retry and backoff policy

Retry ledger key:

```text
(repo, issue_number, failure_class, base_sha, head_sha_or_worker_attempt_sha)
```

Each attempt record stores:

- run id and timestamp;
- failure class;
- detector/signature;
- safe next action;
- commands/checks run;
- branch/head/base state;
- redacted evidence pointer/comment URL;
- retry count and wall-clock age.

Failure classes:

| Class | Meaning | Next action | Terminal label mapping |
|---|---|---|---|
| `safe_auto_repair` | deterministic allowlisted mechanical repair | repair once per signature, rerun verification | no blocked unless repair fails repeatedly |
| `worker_revision_needed` | worker made wrong/incomplete low-risk edit | relaunch/amend within cap | `retry_exhausted` after cap |
| `review_revision_needed` | independent/GitHub reviewer asks low-risk change | amend/respond/resolve within cap | `retry_exhausted` after cap |
| `ci_retryable` | required check failed with known safe signature | fetch logs, patch/amend/rerun | `retry_exhausted` after cap |
| `base_update_needed` | strict protection requires branch update | update/rebase, rerun checks | `retry_exhausted` or `true_blocked` on conflicts |
| `ci_nonretryable` | unclassified required-check failure | stop with evidence | `true_blocked` or `needs-attention` |
| `true_blocker` | external/unsafe action required | stop | `smactorio:blocked` |
| `tamper_or_scope_violation` | unexpected out-of-scope/unknown source change | stop, preserve evidence | `abandoned_safety` |

Default caps:

- safe auto-repair: 1 repair per signature per run, 2 total attempts per issue;
- worker revision: 2 attempts;
- CI retryable: 2 attempts per distinct failure signature;
- review revision: 2 attempts;
- base update: 2 attempts;
- wall-clock cap: 7 days from first claim for a seeded E2E ticket unless campaign specifically tests long staleness.

## Terminal outcome rules

### Merged PR

Required proof:

- PR URL.
- Expected head SHA before merge.
- Required check rollup green for expected head.
- `gh pr merge --match-head-commit <head>` or equivalent head-guarded merge.
- Merge commit SHA.
- Issue closed state and final labels.

### Duplicate

Required proof:

- Canonical issue URL and, if available, PR/commit URL.
- Matching evidence: hidden marker, dedupe key, same candidate id, same acceptance text, or semantically equivalent closed/done issue.
- Comment explaining no new PR is needed.
- Close as duplicate when supported; otherwise close with duplicate label and link.

Foreman must support duplicate discovery after claim, not only publisher-time dedupe.

### Already satisfied

Worker may not complete already-satisfied with a bare stdout marker. Required structured evidence:

```json
{
  "outcome": "already_satisfied",
  "issue_number": 123,
  "acceptance_criteria": [
    {"criterion": "...", "status": "satisfied", "evidence": "..."}
  ],
  "commands": [
    {"command": "signal-hub/scripts/run_tests.sh ...", "exit_code": 0, "summary": "..."}
  ],
  "files_inspected": ["project-relative/path"],
  "base_sha": "...",
  "diff_status": "clean"
}
```

Foreman validates:

- worker exit code is 0;
- structured outcome parses and matches issue number;
- worktree has zero material diff and no commits beyond branch base;
- at least one verification command or direct evidence addresses each acceptance criterion;
- no contradictory material changes exist;
- evidence passes redaction/size rules.

Contradictions such as already-satisfied plus commits, non-zero exit, truncated marker, missing criteria, or dirty worktree become `worker_revision_needed` or `abandoned_safety`, not terminal close.

## Safe auto-remediation classes

Allowed in the low-risk lane:

- `git diff --check` trailing whitespace in worker-authored allowed paths; repair whitespace and rerun diff check.
- Missing executable bit on a new script under allowed scope; set `chmod +x` and rerun checks.
- Generated verification drift under `signal-hub/public/` only when the file matches known generator provenance or appears in a generated-manifest allowlist; discard and record capped relative paths.
- Verification selector normalization:
  - root `scripts/run_tests.sh` references become `signal-hub/scripts/run_tests.sh` where appropriate;
  - `-v` and default quiet flags do not conflict;
  - pytest selector forms `file.py::Class.test`, directory selectors, and unambiguous file selectors map to the wrapper.
- Branch-name collision with stale local/remote branch; generate unique safe branch or delete only a branch proven owned by the same abandoned run.
- Strict branch base update when there are no conflicts.

Not allowed:

- discarding unknown source changes;
- workflow file changes in low-risk lane;
- editing secrets/env/config credentials;
- modifying external production systems;
- admin bypassing checks;
- broad `reset --hard`/`clean -fd` outside classified allowlists.

## Worker prompt contract

The worker prompt must state:

- Worker must resolve the issue, not just explain why it is blocked.
- Worker must use `signal-hub/scripts/run_tests.sh` for generated verification commands in this repo.
- Worker may edit only allowed paths and must not write GitHub state.
- Worker must not commit verification-only artifacts.
- Worker outcomes are exactly:
  - `MATERIAL_CHANGE_READY`: commits exist and verification summary is provided.
  - `ALREADY_SATISFIED`: structured no-PR evidence as above and no commits.
  - `DUPLICATE_FOUND`: structured duplicate evidence with canonical issue/PR/commit and no commits.
  - `TRUE_BLOCKED`: specific blocker class and evidence proving unsafe/external condition.
- Any outcome must be emitted in a parseable fenced JSON block plus a final sentinel line. Foreman rejects if the two disagree.
- Prompt and foreman guard tests must fail whenever a prompt-declared outcome lacks a foreman accept/reject-on-contradiction path.

## Foreman validation contract

Foreman must validate, in order:

1. Re-read issue state/labels and claim fence.
2. Validate worker exit code and parse structured outcome.
3. Validate path scope and dirty-worktree classification.
4. Validate verification commands/check results.
5. Apply safe repairs only via classifier outputs.
6. Validate evidence redaction/size caps before writing docs/comments.
7. Run independent review and enforce final-line verdict exactly.
8. Open or update PR only when material changes exist.
9. Poll/check PR status by expected head SHA.
10. Handle CI/review/base-update revision gates before merge.
11. Merge only with expected head and no admin bypass.
12. Write terminal comment/labels and release claim.

Generic exception handling must not directly apply `smactorio:blocked`. It must call the failure classifier and state-transition writer.

## CI, review, and merge handling

### Required checks

- Required status check names are read from branch protection at run time.
- For this repo, `signal-hub-guardrails` is required and strict.
- Missing/pending checks enter `ci_pending` with bounded polling.
- Failed checks fetch redacted logs and enter `ci_retryable` only if signatures match known safe classes:
  - path-scope failure in worker-authored path;
  - secret scan false-positive in synthetic test fixture with safe test rewrite;
  - unit-test failure in touched tests/code;
  - diff/check/format failure in allowed path.
- Unclassified check failures are `ci_nonretryable`.

### Branch update

- If merge/check state is `BEHIND`, `STALE`, or equivalent strict-protection behind state, foreman updates/rebases the branch safely, records before/after head, reruns checks, and caps attempts.
- Merge conflicts become `base_update_needed` then `true_blocked` or `retry_exhausted` depending on whether worker can resolve safely.

### Review comments / conversation resolution

- Foreman lists PR review comments and review threads before merge.
- Actionable low-risk comments are fed into a revision attempt:
  - comment references allowed path;
  - request is concrete;
  - request does not expand scope or require human judgment.
- Foreman amends branch, reruns checks, replies, and resolves thread when API/tool supports it.
- Unresolved required conversations after retry cap become `review_revision_needed` -> `retry_exhausted` or `true_blocked`.

### Merge

- Use expected-head merge guard.
- Re-read issue state/labels and branch protection before merge.
- No admin bypass.
- Delete branch only after merge or after proven abandoned-owned cleanup.

## Stale label cleanup

On every run before queue selection:

- Closed/done/duplicate/already-satisfied issues must not retain `smactorio:blocked`, `smactorio:claimed`, or `autonomy:ready` unless deliberately retained for closed issue search; if retained, it must not affect eligibility.
- Open `smactorio:claimed` labels are recovered only when claim expired and no active process/fence owns them.
- Open `smactorio:blocked` labels are re-evaluated:
  - if blocker class is now safely retryable, comment why, remove blocked, and queue;
  - if true blocker remains, keep blocked and refresh evidence only if stale;
  - if no structured blocker metadata exists, add `smactorio:needs-attention` and do not silently retry until an operator or migration classifies it.

## Evidence schema and redaction

All foreman comments, verification docs, transition reasons, run summaries, and model/review artifacts pass through the same redaction pipeline.

```json
{
  "schema_version": 1,
  "run_id": "...",
  "issue_url": "...",
  "state": "...",
  "outcome": "...",
  "failure_class": "...",
  "base_sha": "...",
  "head_sha": "...",
  "branch": "...",
  "pr_url": "...",
  "merge_commit": "...",
  "commands": [
    {"name": "targeted_tests", "command": "...", "exit_code": 0, "summary": "...", "tail": "..."}
  ],
  "changed_paths": ["project-relative/path"],
  "discarded_generated_paths": ["project-relative/path"],
  "review_threads": ["redacted summary"],
  "redactions_applied": ["secret-like", "absolute-path", "long-output"],
  "truncated": false
}
```

Rules:

- Paths are project-relative unless a live host path is essential; host/user home paths are replaced with `[REDACTED_PATH]` or project-relative form.
- Secret-like strings, credential-bearing URLs, tokens, passwords, API keys, auth headers, JWTs, private keys, connection strings, and sensitive query params are `[REDACTED]`.
- Evidence is capped per block and globally; truncation marker is explicit.
- Raw HTML/binary/generated-page bodies are not embedded.
- Hashes are omitted or truncated unless they are the proof handle.
- No environment dumps.

## E2E campaign rules

A case counts only when:

- A real GitHub issue is opened or selected.
- Issue has required campaign labels, e.g. `smactorio:e2e`, `smactorio`, `risk:low`, `autonomy:ready`.
- SmactorIO worker/foreman claims or otherwise processes it.
- Worker/foreman reaches a correct terminal outcome:
  - merged PR closing issue;
  - structured duplicate close/link;
  - structured already-satisfied close;
  - true-blocked only for deliberate true-blocker test cases.
- Supervising agent does not manually close the ticket.
- No successful case ends with both `autonomy:ready` and `smactorio:blocked`.

Campaign harness must record for each case:

- case ID;
- issue URL;
- expected behavior;
- worker claim evidence;
- PR URL if applicable;
- merge commit if applicable;
- final issue state/labels;
- logs/evidence path;
- pass/fail;
- if failed: root cause, fix PR/commit, rerun result.

Run one issue at a time until concurrency is proven safe.

## Rollback and safety boundaries

- Use normal GitHub rollback: branch/PR/revert, not tarball backups, for repo-backed SmactorIO work.
- Keep canonical rtx3070 checkout clean before and after deployment/campaign runs.
- Pause `smactorio.timer` only when deterministic single-issue campaign execution requires it; record before/after timer state and restore it.
- Never delete user/human branches unless branch ownership marker matches SmactorIO run id and the branch is abandoned.
- Preserve evidence for failed E2E cases until the regression test/fix/rerun passes.
- If CI on `main` fails after a SmactorIO merge, stop claiming new work and open/mark a needs-attention self-report.

## Acceptance criteria for this hardening effort

- Spec and implementation plan receive independent strong-model adversarial review with verdict and patched findings.
- All production changes are introduced with failing tests first and recorded RED/GREEN evidence.
- Targeted and full Signal Hub suites pass through `signal-hub/scripts/run_tests.sh`.
- Branch protection/CI passes for all hardening PRs.
- At least 20 real-ticket E2E cases pass under the campaign rules.
- Final repo and rtx3070 checkout are clean.

---

## Post-Opus review normative patches

These patches are normative and supersede any looser wording above. They incorporate the final Claude Opus/max-effort review verdict `ACCEPT_WITH_CHANGES` saved in `signal-hub/docs/verification/2026-05-19-smactorio-opus-spec-review.md`.

### Durable state model

The persistent lifecycle has a compact durable state set. Transitional moments may be stored as attempt sub-states but must not become unbounded labels or long-lived queue states.

Durable states:

| Durable state | Meaning |
|---|---|
| `queued` | Eligible issue waiting for a run. |
| `preflight` | Current run is validating eligibility, locks, branch protection, local checkout, backend, and duplicate/already-satisfied candidates. |
| `claimed` | Current run owns a lease/fencing token for this issue. |
| `worker_running` | Worker subprocess is active in an isolated worktree. |
| `pr_open` | A PR exists for the run branch/head and the foreman is handling checks, branch updates, reviews, and merge. |
| `awaiting_external` | Human or external system action is required; issue is not eligible until labels/evidence change. |
| Terminal states | `merged`, `duplicate`, `already_satisfied`, `true_blocked`, `retry_exhausted`, `aborted_by_human`, `abandoned_safety`. |

Sub-states such as `ci_failed_retryable`, `base_update_needed`, `review_changes_requested`, `stale_claim_recovered`, and `stale_blocked_reconsidered` live in the attempt ledger, not as permanent GitHub labels.

`aborted_by_human` is terminal for a run when the issue is closed, `autonomy:ready` is removed, or a claim is otherwise revoked by a human during processing. It releases the claim and does not apply `smactorio:blocked`.

### Worker output wire format

Foreman accepts worker terminal outcomes only via this exact wire format on stdout:

```text
```smactorio-outcome-json
{ ... JSON object ... }
```
SMACTORIO_OUTCOME_JSON_V1: <OUTCOME>
```

Rules:

- The fence language tag is exactly `smactorio-outcome-json`.
- The final non-empty stdout line is exactly `SMACTORIO_OUTCOME_JSON_V1: <OUTCOME>` where `<OUTCOME>` is one of `MATERIAL_CHANGE_READY`, `ALREADY_SATISFIED`, `DUPLICATE_FOUND`, `TRUE_BLOCKED`.
- The JSON object has `schema_version: 1`, `outcome`, `issue_number`, `run_id`, `acceptance_criteria`, `commands`, `files_inspected`, `base_sha`, and `diff_status` when applicable.
- `outcome` in JSON must equal the final sentinel outcome.
- Multiple fenced outcome blocks are invalid.
- Sentinel without JSON is invalid.
- JSON without sentinel is invalid.
- Truncated JSON, malformed JSON, non-UTF-8 output, or unicode-mangled sentinel is invalid.
- Invalid worker output is `worker_revision_needed` if safely retryable; otherwise `abandoned_safety`. It is never `already_satisfied` and never generic `smactorio:blocked`.

Required JSON fields by outcome:

| Outcome | Extra required fields |
|---|---|
| `MATERIAL_CHANGE_READY` | `changed_paths`, `verification_summary`, `commit_count` > 0 |
| `ALREADY_SATISFIED` | `acceptance_criteria[]` all `satisfied`, `commands[]` or direct file evidence, `files_inspected[]`, `diff_status: clean`, `commit_count: 0` |
| `DUPLICATE_FOUND` | `canonical_issue_url` and at least one of `canonical_pr_url`, `canonical_commit`, `dedupe_key`, or `matching_hidden_marker` |
| `TRUE_BLOCKED` | `blocker_class`, `unsafe_or_external_action`, `evidence_summary` |

### Protected runtime file list and self-repair approval

The low-risk worker lane must quarantine issues touching any protected runtime path unless label `autonomy:smactorio-self-repair-approved` is present:

- `signal-hub/scripts/smactorio_issue_foreman.py`
- `signal-hub/scripts/project_improvement_processor.py`
- `signal-hub/scripts/smactorio_policy.py`
- `signal-hub/scripts/smactorio_repo_guard.py`
- `signal-hub/scripts/check_path_scope.py`
- `signal-hub/scripts/scan_for_secrets.py`
- `signal-hub/tests/test_smactorio_issue_foreman.py`
- `signal-hub/tests/test_project_improvement_processor.py`
- `signal-hub/tests/test_smactorio_policy.py`
- `signal-hub/tests/test_smactorio_repo_guard.py`
- `infra/systemd/system/smactorio.service`
- `infra/systemd/system/smactorio.timer`

This list must be represented as a versioned source constant and covered by a test that asserts it is non-empty and contains at least the foreman, publisher, policy, repo guard, path-scope checker, and systemd units.

### Generated artifact provenance allowlist

Safe generated drift cleanup is fail-closed by default.

Allowed generated drift under `signal-hub/public/` requires one of:

1. file path appears in versioned manifest `signal-hub/public/.smactorio-generated-manifest.json`; or
2. file content contains a recognized generator marker from the manifest's `markers` list; or
3. an explicit test fixture marks the path as generated for a unit test.

Manifest schema:

```json
{
  "schema_version": 1,
  "generated_roots": ["signal-hub/public/"],
  "paths": ["signal-hub/public/index.html"],
  "markers": ["<!-- Generated by Signal Hub -->"],
  "owner": "signal-hub",
  "last_verified_by": "signal-hub/scripts/run_tests.sh"
}
```

Unknown generated-looking paths, hand edits under `signal-hub/public/`, and missing/unreadable manifest cases default to `worker_revision_needed` or `tamper_or_scope_violation`, never silent discard.

### Retry ledger persistence

The retry/attempt ledger is persisted in `/home/leonb/.local/state/smactorio/smactorio.sqlite` or the configured SmactorIO state DB path. It must survive process restarts and cron ticks.

Minimum table shape:

```sql
CREATE TABLE IF NOT EXISTS issue_attempts (
  id INTEGER PRIMARY KEY,
  repo TEXT NOT NULL,
  issue_number INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  durable_state TEXT NOT NULL,
  sub_state TEXT,
  failure_class TEXT,
  failure_signature TEXT,
  base_sha TEXT,
  head_sha TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 1,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  evidence_ref TEXT,
  UNIQUE(repo, issue_number, failure_class, failure_signature, base_sha, head_sha)
);
```

Behavior:

- If the DB is unreadable, foreman must fail closed before claiming new work and must not label issues blocked.
- Writes are transactional around claim/attempt updates.
- A base SHA change does not erase history; it creates a new ledger row but wall-clock cap uses the earliest row for the issue.
- Per-issue lifetime caps prevent infinite repeats of the same failure class across process restarts.
- Partial transaction or row-key collision is retryable infrastructure failure, not an issue blocker.

### Concurrency, locking, and rate limits

- Default concurrency is one foreman run per repository. A host-level flock/systemd guard is primary; DB claim fencing is backup.
- Claim uniqueness is per `(repo, issue_number)` while state is nonterminal.
- Two simultaneous foreman processes must not both claim the same issue. One must observe the existing lease/fence and exit without mutating GitHub labels.
- GitHub primary/secondary rate limits, 429, and 5xx during non-merge operations are transient infrastructure failures with backoff; they are not issue-level `smactorio:blocked` outcomes.
- If rate limit or 5xx happens after a PR head is green but before merge, foreman records `merge_transient_failure`, releases/renews claim according to fence, and retries later using expected-head validation.
- Branch protection changes mid-run require a fresh protection/readiness poll. New required checks are honored; no bypass.

### Error-handling defaults

- Unclassifiable dirty diff defaults to `tamper_or_scope_violation`.
- Unclassifiable CI/review/worker failure defaults to `ci_nonretryable`/`worker_revision_needed`/`review_revision_needed` as applicable, with no generic blocked label unless the true-blocker detector matches.
- Redaction failure is fail-closed: do not publish the unsafe evidence; record a local redaction failure reference; release or await external depending on severity; do not label the issue blocked solely because redaction failed.
- Log fetch timeout is transient and retryable within CI polling cap.
- Model review subprocess non-zero is `review_revision_needed` if the failure is prompt/output-form related, or transient infrastructure if provider/tool failure is detected.
- GitHub API 5xx, DNS, and network timeouts are transient infrastructure failures.

### Forbidden-action and true-blocker catalog

Forbidden-action detection is deterministic first, with optional model review only as a secondary conservative signal. The deterministic scanner checks title, body, comments, acceptance criteria, and likely files.

True-blocker classes:

| Class | Detector examples | Allowed action |
|---|---|---|
| `credentials_or_secret_required` | asks for token/password/private key/API key/connection string or env secret rotation | comment evidence, stop |
| `two_factor_or_human_auth` | 2FA, OAuth consent, CAPTCHA, interactive login | comment evidence, stop |
| `billing_or_spend` | paid resource creation or spend > approved threshold | comment evidence, stop |
| `destructive_or_data_loss` | delete database, purge backups, wipe disks, destructive migration | comment evidence, stop |
| `external_production_mutation` | modify non-repo production system outside SmactorIO scope | comment evidence, stop |
| `public_social_account_action` | post from or integrate public/social account | comment evidence, stop |
| `human_product_judgment` | requires subjective product/legal/brand decision | comment evidence, stop |
| `security_boundary_change` | weakens branch protection/secret scan/path scope or CI guardrails in low-risk lane | quarantine/stop |

### CI retryable signature catalog

Retryable CI failures are exact and narrow:

| Signature | Detector input | Allowed remediation | Negative example |
|---|---|---|---|
| `diff_check_trailing_whitespace` | `git diff --check` reports whitespace in worker-authored allowed path | trim whitespace in that path only | binary/generated blob rewrite |
| `missing_executable_bit` | test/check reports new script under allowed path is not executable | `chmod +x` that new script only | chmod existing runtime scripts without issue scope |
| `path_scope_allowed_correction` | path-scope check reports worker edit just outside allowed signal-hub-relative path due to wrapper/path prefix error | move/correct the worker-authored change into allowed path | any `.github/workflows/**` edit |
| `pytest_targeted_failure_touched_code` | failing test selector targets touched code/test and log has assertion/failure traceback | worker revision within same scope | unrelated integration/service outage |
| `secret_scan_fixture_false_positive` | secret scan flags a synthetic fixture under `signal-hub/tests/**` using split-token test data pattern | rewrite fixture to avoid token-shaped literal while preserving test semantics | any secret-like value outside `signal-hub/tests/**`, any real env/config file |

Everything else is nonretryable until explicitly added with tests.

### Campaign coverage matrix

The 20+ real-ticket campaign must include at least:

- 5 merged PR cases.
- 3 already-satisfied no-PR terminal cases.
- 2 duplicate terminal cases, including one open duplicate and one closed/done duplicate.
- 2 deliberate true-blocked/quarantine cases that prove no generic blocked loop.
- 2 retry-exhausted or abandoned-safety cases from controlled unfixable low-risk failures.
- 1 stale-blocked cleanup/retry case.
- 1 worker interruption/service restart recovery case.
- 1 strict base-update/rebase case or simulated branch-protection-behind equivalent using a real PR.
- 1 review-comment/amend case or a documented live-repo equivalent if no required reviewer can be safely configured.
- 1 evidence redaction/capping case.
- Remaining cases may cover the user-provided selector/generated-artifact/path-scope list.

The campaign aborts for supervisor review if three consecutive cases fail with the same root cause, if more than five campaign issues are open and nonterminal simultaneously, if branch protection or CI is degraded, or if any evidence publication would expose secrets.

Campaign seeded issues are legitimate real GitHub issues but must be labelled `smactorio:e2e` and written so they are safe, reversible, and auditable. Manual supervisor closure never counts as pass.

### Branch and cleanup safety

- If branch ownership cannot be proven from a surviving fence record, never delete the branch automatically.
- At campaign end: all `smactorio:e2e` issues must be terminal or explicitly documented as non-counting leftovers; no orphan SmactorIO branches owned by the campaign; no open successful issue with both `autonomy:ready` and a terminal label; canonical checkout clean.
