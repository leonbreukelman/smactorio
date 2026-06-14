# Claude Opus adversarial pre-spec review — SmactorIO lifecycle contract

## Provenance

Tool: Claude Code CLI 2.1.143. Command: `claude -p <prompt> --model opus --effort max --tools "" --max-turns 1 --output-format text < model-context.md`. Mode: tools disabled/read-only. Fallback: none required.

## Stderr / tool notes

```text
(none)
```

## Model output

# Adversarial review — SmactorIO reliability hardening (pre-spec)

## Verdict

**ACCEPT_WITH_CHANGES.** Phase 0 root-cause is correct and Phase 1 matrix captures the right pattern shelf, but the implied lifecycle contract still has enough load-bearing ambiguity that writing a spec from it now would re-enter the same "blocked means six different things" trap. The list below must be folded into the spec before implementation.

## Critical contract gaps and unsafe assumptions

1. **`ALREADY_SATISFIED` is a single-line stdout contract.** Foreman accepts the outcome solely from `final_nonempty_line(result.stdout) == "SMACTORIO_OUTCOME: ALREADY_SATISFIED"` and "no commits". This trusts buffered/truncated stdout from a non-zero-exit worker, a worker that crashed after printing the marker, and a worker that committed *and* printed the marker. Contract must require: zero exit, clean worktree, zero diff vs base, structured evidence block (commands run, acceptance criteria evaluated, files inspected), and reject-on-any-contradiction.
2. **Claim TTL collides with worker timeout.** `claim_ttl_minutes=180` and `worker_timeout_seconds=1800` (30 min) are independent; `recover_stale_claims` only removes the label if expiry is past, not if the prior run actually died. Nothing prevents two foreman instances from both running on the same issue inside the TTL after a host reboot. No DB-level claim uniqueness or fencing token is described.
3. **`duplicate` is a publisher concept only.** The foreman has no path to close-as-duplicate after claim. If duplicate is discovered mid-lifecycle (the publisher missed it; or a human filed a second one), the contract has nowhere to land it short of `blocked`.
4. **"Generated drift" allowlist is path-prefix only.** `SAFE_WORKER_GENERATED_SIDE_EFFECT_PREFIXES = ("signal-hub/public/",)` will silently absorb any future worker-authored change under `signal-hub/public/` — including malicious or accidental hand-edits. There is no signature/manifest check that the discarded content is actually generator output.
5. **`type:docs`/`autonomy:ready` is sufficient to consume a smactorio repair issue.** Issue #37 was about the worker's own generation path; the worker can be invited to fix the very generator that generated it. Self-repair gate is research-aspirational, not in policy.
6. **`forbidden_text_fragments` is title-only.** Body intentionally excluded so stop conditions can be documented. But the same string in the title is the only block; an issue title that says "harden docs around 2FA" is blocked, while a title saying "harden docs" plus a body asking for production credential rotation passes. The contract needs an acceptance-criteria scanner, not a title scanner.
7. **`required conversation resolution: enabled` is unhandled.** Copilot reviews on #42/#43 left threads that, on a different repo configuration, would block merge. The foreman has no list-threads / resolve-thread / reply API path. Spec must either disable required conversation resolution explicitly or implement a bounded resolution loop.
8. **`check_path_scope.py` allowlists `.github/workflows/`.** A successful low-risk SmactorIO PR can therefore mutate CI workflow YAML, including the very `signal-hub-guardrails` check that gates its own merges. This is a privilege-escalation primitive the spec must close (either remove `.github/workflows/` from the worker scope, or require a separate higher-trust lane for CI changes).
9. **Evidence comment path does not redact.** `issue_comment` writes a body file straight to `gh issue comment --body-file` without `redact_text(...)`. The blocked-path explicitly inlines `str(exc)[-1800:]` which can carry env-dumps, tokens leaked into stderr by gh, or absolute paths. Investigation already flagged unredacted absolute paths in #37.
10. **`run_verification` is called twice.** Lines 1609 and 1612 run the full verification suite back-to-back around the artifact commit. The second run has no failure-recovery branch and silently doubles wall time / log volume; if the artifact commit itself trips secret-scan, the failure mode is "succeed then fail" with confusing evidence.

## Missing state-machine transitions

- `worker_running → worker_timeout` (process timeout / SIGKILL) — currently collapses into generic exception → `blocked`.
- `claimed → released` (in-flight worker discovers eligibility lost: `autonomy:ready` removed, issue closed by human, label race) — currently raises, lands in `blocked`.
- `worker_done → already_satisfied` (contradictory worker output: marker + commits) — undefined; must be `needs_revision` or `true_blocked`.
- `pr_open → base_update_needed → pr_open` (strict protection rebase loop, including conflict resolution failure → `needs_revision`).
- `pr_open → review_changes_requested → needs_revision` (PR review comments / failing required reviewers).
- `pr_open → ci_failed_retryable → needs_revision` (failed required check whose log signature matches an auto-repair class).
- `pr_open → ci_failed_nonretryable → true_blocked`.
- `merged → post_merge_failure` (next run of `signal-hub-guardrails` on `main` fails — currently no signal back to ticket lifecycle).
- `blocked (stale) → queued` (the reconciler the matrix promises, not yet a transition).
- `published → duplicate_after_publish` (publisher races and creates a second issue under truncated list response).
- Self-repair quarantine: `queued → quarantined_self_repair` is not in the implied state machine at all.
- Crash recovery on `pushed=True` but pre-PR: branch exists remotely, no PR — no transition reclaims/cleans it on next run.

## Missing tests / E2E cases

- Worker emits `ALREADY_SATISFIED` and also commits → must be rejected, not closed.
- Worker emits `ALREADY_SATISFIED` with non-zero exit code → reject.
- Worker stdout truncated mid-marker → reject (no fuzzy match).
- Two foreman processes pick the same issue within TTL (concurrency).
- `gh issue list --state all` truncates (>100/1000 results) for processor dedupe → must fail-closed, not publish.
- Open blocked duplicate exists in the same hidden-marker key set → publisher must not "link to terminal" while a stale blocked open issue remains.
- Closed-as-duplicate (GitHub native reason) — foreman/publisher recognition.
- Issue closed by human mid-run; foreman must release claim cleanly without commenting `blocked`.
- Labels edited by human mid-run (`autonomy:ready` removed) — foreman must re-check eligibility before commenting/closing.
- PR's required check name changes / new required check added mid-lifecycle.
- `mergeStateStatus = BEHIND` requiring rebase before merge (current `pr_checks_are_green` only accepts `CLEAN`/`HAS_HOOKS`, otherwise blocks terminally).
- Merge conflict requiring rebase; rebase fails with conflict → must classify, not loop.
- Force-push race during `wait_for_pr_checks` polling (expected_head changes from foreman's own commit, not a hostile actor).
- Copilot/required reviewer leaves `CHANGES_REQUESTED` review.
- Required conversation resolution: unresolved thread blocks merge despite green checks.
- Evidence redaction: artifact contains absolute paths, `/home/leonb/...`, env vars matching `*TOKEN*`, sha256 fingerprints — all must be stripped before issue comment / artifact write.
- `signal-hub/public/` "drift" actually contains a hand-edited HTML change → must not be silently discarded.
- Worker tries to touch `.github/workflows/` — should be policy-blocked even if path scope allows it for low-risk tickets.
- Self-repair ticket: an issue whose `likely_files` overlap `signal-hub/scripts/smactorio_*.py` must be quarantined.
- E2E campaign: ≥20 real GitHub issues processed end-to-end by the worker/foreman (not supervising-agent takeover) with success/duplicate/already-satisfied/true-blocked mix, claim-recovery from a forced crash, and at least one each of: rebase-needed, review-comment-resolved, ci-failed-retryable.

## Places where duplicate/already-satisfied/blocked can still loop

- **Stale `smactorio:blocked` on an open issue with the same marker as a closed-`smactorio:done` one.** Publisher `find_existing_generated_issue` picks the open issue (bucket 0 unless blocked label demotes it to bucket 2/3); `link_existing_issue_outcome` then returns `blocked` because of the blocked label. The candidate is never republished and the original blocked issue is never retried. Result: terminal cul-de-sac that looks like dedupe success.
- **`recover_stale_claims` only removes claim labels for *claimed* issues.** A `smactorio:blocked` label with an underlying stale/safe failure class is never re-evaluated. The "stale-blocked reconciler" is in the matrix but not in the lifecycle yet.
- **Already-satisfied evidence is unstructured.** If the worker reports `ALREADY_SATISFIED` because it could not understand the issue, foreman closes the ticket. Next publisher run sees a closed `smactorio:done` matching marker and treats it as terminal — the original need is now invisible. Need a "verified-satisfied" structured proof and a publisher counter-signal that closed-done with empty evidence should *not* satisfy dedupe.
- **`PublishLock` is filesystem-only.** Crashed run leaves lock file; no stale-lock TTL described. Next run blocks on the lock or, worse, lock is unlinked manually and two parallel publishes race.
- **`open_pr_mentions_issue` gate.** Human-opened PR mentioning the same issue makes foreman return `no_work`. If the human PR is stalled, the ticket is permanently held off retry without evidence.

## Branch protection / CI / review-comment / evidence hazards

- **Strict required check + no rebase loop.** `wait_for_pr_checks` declares "merge state is not clean" terminal for anything outside `CLEAN`/`HAS_HOOKS`. Real GitHub strict checks frequently land in `BEHIND` after a base push; this maps to terminal blocked instead of rebase-and-retry. Must add bounded rebase + recheck.
- **`--match-head-commit` is set, but no anti-tamper for label/comment race.** Between `wait_for_pr_checks` returning green and `merge_pr`, a human could change a required check; foreman would merge anyway because gh returns success. Add a final pre-merge label/required-checks re-read.
- **Admin enforcement is enabled, no required PR reviews.** Adversarially: SmactorIO can merge its own PRs with only `signal-hub-guardrails` green. The spec should mandate required reviewer (even self-managed Copilot) or document explicitly why "no required reviews" is the chosen risk posture.
- **CI failure logs are never fetched.** No classifier exists. Spec must define: signatures for path-scope/secret-scan/unit-test failures, the subset that auto-repairs (whitespace already covered), and how many attempts before promotion to `true_blocked`.
- **Review comment resolution loop missing.** Copilot review on PR #42 and #43 was observed; foreman has zero code reading `pr.reviewComments`, `pr.reviewThreads`, replying, or resolving threads. With required conversation resolution on, this is a merge-blocking gap.
- **Evidence redaction is publisher-side only.** `redact_text` is used in publisher outcome reason logging (line 1794) but the foreman's issue-comment paths embed `gh` stdout/stderr, exception strings, and porcelain status verbatim. Token-shaped strings, `Authorization:` headers, and `/home/leonb/...` paths can flow to public comments.
- **Verification artifact contains raw command outputs `[-2000:]`.** Per-check cap, no global cap, no scrub for IPs, hashes, tokens, absolute paths, or HTML render dumps. Investigation already cites this as the #37 review-blocker root cause; the cap-only mitigation is insufficient.
- **`token_git_env` / `verification_env` referenced but not shown.** Spec must enumerate the exact subset of env exposed to worker, verification, and git operations, and forbid pass-through of `GH_TOKEN`, `*TOKEN*`, `*SECRET*` to the worker process.

## Required changes to the spec/plan before implementation

1. **Concrete error taxonomy table** (`safe_auto_repair | worker_revision_needed | ci_retryable | ci_nonretryable | review_revision_needed | base_update_needed | true_blocker`) with: signature/detector, allowed next action, max attempts, backoff, terminal label mapping, evidence schema. Only `true_blocker` and `retry_exhausted` may set `smactorio:blocked`.
2. **Attempt ledger schema** keyed by `(issue_number, failure_class, base_sha, head_sha)` with per-class max attempts and stale-attempt expiration; persisted in the same SQLite that owns transitions.
3. **Structured `ALREADY_SATISFIED` evidence contract** — replace the stdout marker with a worker-emitted JSON block on a fenced stdout sentinel (or a worktree file): acceptance criteria evaluated, commands run with exit codes, files inspected with hashes-of-relevant-lines (not whole-file), zero-diff proof. Foreman validates each field before closing the issue. Exit-code-zero + clean-tree + zero-diff are necessary, not sufficient.
4. **Stale-`smactorio:blocked` reconciler invariants**: on each run, list open issues with blocked label, re-evaluate against the current attempt ledger; only remove the label after preflight reproves the failure class is now safe-retryable; otherwise emit needs-attention with reason.
5. **No-PR `duplicate` closure path in foreman** (separate from publisher): on duplicate discovery mid-lifecycle, comment with link to canonical issue, close with `--reason duplicate`, drop claim, do not push a branch.
6. **PR review-comment resolution loop**: list `reviewThreads`, classify each comment as actionable/low-risk/out-of-scope, apply bounded revision attempts, resolve threads via GraphQL (`resolveReviewThread`), and escalate to true-blocker only after a defined cap. Specify what counts as "low-risk actionable" (e.g., comment quotes a single allowed-prefix file, doesn't request scope expansion, doesn't request unsafe action).
7. **CI failure log classifier**: define exact log-line regexes / signal strings for the guardrail's three checks (`check_path_scope.py`, `scan_for_secrets.py`, unit test discover) and the auto-repair mapping. Anything unclassified is `ci_nonretryable` with raw-log-redacted evidence.
8. **Rebase / `BEHIND` handling**: explicit step between `pr_open` and merge that updates the branch via `gh pr update-branch` or `git pull --rebase origin/main` in the (now-deleted) worktree's regenerated form. Record before/after head; rerun the entire check cycle; cap rebase attempts.
9. **Evidence redaction pipeline** applied to every foreman issue comment, every verification artifact, and every transition reason. Filters: env-var-name allowlist; path anonymization (project-relative only); secret regex (token-shaped, key-shaped, JWT-shaped); hash truncation; HTML/binary blob exclusion; per-block char cap + total-size cap with truncation marker.
10. **Self-repair quarantine policy**: an issue whose acceptance criteria or `likely_files` touch any of `signal-hub/scripts/smactorio_*.py`, `signal-hub/scripts/project_improvement_processor.py`, `signal-hub/scripts/smactorio_repo_guard.py`, `signal-hub/tests/test_smactorio_*.py`, `signal-hub/tests/test_project_improvement_processor.py`, or `infra/systemd/system/smactorio.*` must require an explicit human-signed `autonomy:smactorio-self-repair-approved` label before becoming eligible; otherwise auto-strip `autonomy:ready` and comment.
11. **CI scope tightening**: spec must decide whether `.github/workflows/` remains in the worker allow-prefix. Recommend removing it from `risk:low` lane and routing CI changes through a separate, human-reviewed lane.
12. **Concurrency and fencing**: single-foreman invariant — runtime DB unique constraint per `(repo, issue_number)` while non-terminal; or a fencing-token comment marker the merge step re-verifies. Document host-level `flock` already in systemd as the primary defense and the DB/comment check as backup.
13. **Worker-prompt vs foreman-guard contract tests**: a test parses the worker prompt text, extracts every declared worker outcome, and asserts that for each one the foreman has both an accept path and a reject-on-contradiction path. Adding a new prompt outcome without matching foreman code must fail tests.
14. **Live-runtime lane vs GitHub-issue lane separation**: spec invariant that runtime-local Signal Hub work-order skip/failure evidence is never quoted into GitHub issue comments and never counted as ticket completion.
15. **E2E campaign harness**: deterministic creation of ≥20 real low-risk issues with seeded marker/dedupe keys; required outcome distribution across `merged | already_satisfied | duplicate | true_blocked | retry_exhausted`; one forced-crash scenario; one stale-blocked retry scenario; pass criterion is "supervising agent did not write to GitHub during the campaign". Without this harness, the spec must explicitly state that #37 class regression cannot be detected pre-deploy.
16. **Verification doubling**: remove or justify the duplicate `run_verification` call in `run_once` (lines 1609 and 1612). If both are needed, document why and which evidence wins.
17. **Post-merge reconciliation**: on next-run preflight, if `signal-hub-guardrails` on `main` is failing on the merge commit SmactorIO just produced, open a `smactorio:needs-attention` self-report and refuse to claim more work until a human acknowledges.
18. **Issue-age / staleness threshold** (Dependabot pattern): cap retries by wall-clock age too, not only attempt count, to prevent perpetual revival of a ticket whose context has rotted.


---

# Claude Opus adversarial final spec/plan review

## Provenance

Tool: Claude Code CLI 2.1.143. Command: `claude -p <review prompt> --model opus --effort max --tools "" --max-turns 1 --output-format text`, with the draft spec and plan supplied on stdin. Mode: tools disabled/read-only. Fallback: none required.

## Model output

Verdict: ACCEPT_WITH_CHANGES

## 1. Critical blockers before implementation

1. **No defined source for the 20-ticket E2E campaign.** Plan Task 14 says "create/reuse campaign labels" but never specifies where 20 distinct real tickets come from. Organic tickets won't arrive on demand; 20 synthetic merges of trivial issues do not prove the duplicate / already-satisfied / true-blocked / retry-exhausted paths. Without an explicit, mixed-coverage matrix the campaign is unverifiable.

2. **Retry ledger persistence is hand-waved.** Task 1 says "pure helper plus in-memory/fake command runner until DB integration task," but there is no later DB integration task. A retry ledger that does not survive cron restart cannot enforce the caps in spec §"Retry and backoff policy" across ticks. Caps drift to "first tick only."

3. **Worker output wire format is undefined.** Spec §"Worker prompt contract" requires "a parseable fenced JSON block plus a final sentinel line. Foreman rejects if the two disagree," but neither spec nor plan pins the sentinel string, JSON schema name, fence language tag, or tie-break rule. LLM workers will produce parser-divergent output every run.

4. **CI `ci_retryable` signatures are not enumerated and one of them is dangerous as written.** Spec lists "secret scan false-positive in synthetic test fixture with safe test rewrite" as retryable. Without a tight, tested allowlist this is a credential-exfiltration vector: a misclassified signature lets the worker silently mutate a real fixture to make the scanner green.

5. **The "core SmactorIO runtime files" self-repair quarantine set is not enumerated anywhere.** The eligibility rule depends on this list but the list lives nowhere in spec or plan, so the quarantine will diverge from policy on day one.

6. **Generated-artifact provenance allowlist is undefined.** Spec §"Safe auto-remediation classes" gates `signal-hub/public/` drift discard on "known generator provenance or appears in a generated-manifest allowlist." Neither the manifest path, schema, nor refresh mechanism is specified. The dirty classifier will be permissive-by-default or fail-by-default with no test pinning either.

7. **No regression test pinned to the issue #37 failure path.** The plan adds classifiers and ledgers but no test takes the exact trigger that produced the "simple to fix but blocked" loop and asserts a non-blocked terminal state under the new code. The only validation today is the campaign itself.

## 2. Required spec patches

1. Pin the worker output wire format: fence language tag, JSON schema (`schema_version`, required keys per outcome), sentinel byte string, parser tie-break, behavior on multiple JSON blocks, behavior on JSON-without-sentinel, behavior on sentinel-without-JSON.

2. Enumerate `true_blocker` blocker classes and `ci_retryable` failure signatures in tables: detector input, structural matcher, allowed remediation, forbidden remediation, negative example. Tighten "secret scan false-positive" to fixture paths under `signal-hub/tests/**` only, or remove it.

3. Enumerate the protected runtime file list (or link to a versioned source constant) and state the audit/extension process.

4. Specify the generated-manifest file path, schema, and refresh policy. State that unknown generated paths fail-closed to `worker_revision_needed` or `abandoned_safety`, never silent discard.

5. Define the concurrency model: max simultaneous foreman runs, lock granularity (per-issue vs per-repo), behavior under cron overlap, behavior under GitHub primary and secondary rate-limit. The fencing token is mentioned but the global lock semantics are not.

6. Specify retry-ledger persistence: SQLite path, schema, behavior on DB unreadable, behavior on partial transaction, behavior on row-key collision across base SHA changes.

7. Add a foreman validation error-handling contract: when redaction raises, when log fetch times out, when GitHub returns 5xx mid-merge, when the model review subprocess exits non-zero. Currently the 12-step contract specifies the happy path but not failure of the validation steps themselves.

8. Tighten the 7-day wall-clock cap: when the clock starts, whether it resets on `stale_blocked_reconsidered`, interaction with `base_update_needed` blocked on upstream.

9. Specify the eligibility "forbidden action" detection mechanism (regex catalog vs LLM judgment). Today it is implementation lottery.

10. Make `aborted_by_human` (or equivalent) a first-class terminal state for the case where an operator removes `autonomy:ready` or closes the issue mid-run. Spec describes the behavior but does not name a state.

11. Add an explicit minimum coverage matrix for the 20-case campaign: e.g. ≥5 merged, ≥3 already_satisfied, ≥2 duplicate, ≥2 true_blocked, ≥2 retry_exhausted, remainder organic. Without this, "20 cases" is unfalsifiable.

12. State the dirty-worktree classifier's default: unclassifiable diff is `tamper_or_scope_violation`, not a permissive default.

13. State the branch-deletion rule explicitly: when ownership cannot be proven from a surviving fence record, never delete.

14. Specify behavior when branch protection requirements change mid-run (new required check added between claim and merge): re-poll, re-classify, do not bypass.

## 3. Required plan patches

1. Add a concrete retry-ledger persistence task with SQLite schema, migration, and a test that the ledger survives process restart. Either fold into Task 1 with a "no in-memory fake permitted" rule, or add Task 1b.

2. Add an idempotent migration task that converts existing open `smactorio:blocked` issues to structured-evidence form (reclassified-retryable or true-blocked). Without this, Task 7's reconciler runs against label state lacking the structured metadata it expects.

3. Task 11 must specify ticket sourcing (seeded category cases vs organic), teardown semantics for seeded cases, and matching coverage matrix from the spec patch.

4. Task 14 must have an explicit abort condition: e.g. on N consecutive failures with the same root cause, pause the campaign for human review. Otherwise SmactorIO can spam many failing PRs while the harness keeps marching.

5. Task 2 must add round-trip tests covering malformed worker outputs: extra commits with `already_satisfied`, sentinel without JSON, JSON without sentinel, multiple JSON blocks, truncated JSON, unicode-mangled sentinel.

6. Task 4 must add a fail-closed test: if the redactor raises, the comment / artifact / evidence is not written, the run records the redaction failure, and the issue is not labeled blocked because of it.

7. Task 8 must pin the rebase tool path (e.g. `gh pr update-branch` vs `git fetch && git rebase --onto`) and add a test that the post-rebase head SHA is recorded before re-polling checks.

8. Task 9 must enumerate the protected runtime file list as a versioned source constant and assert in test that the list is non-empty and contains the foreman, publisher, policy, and repo-guard scripts.

9. Add a task for GitHub API rate-limit handling with tests proving 429 / secondary-limit responses are classified transient, never terminal blocked.

10. Add a task and test for two simultaneous foreman processes attempting to claim the same issue.

11. Split Tasks 13 and 14: PR review/merge is one milestone, runtime deploy + campaign is another. Add a pre-deploy snapshot/restore step for the rtx3070 timer/service state.

12. Add an issue #37 regression test in Task 1 or Task 2 that reproduces the original trigger and asserts a non-blocked terminal outcome.

13. Add a cleanup/teardown task: campaign-end check that all `smactorio:e2e` issues are terminal, no orphan branches, rtx3070 checkout clean, ledger compacted.

14. Add a deliberate-failure test that confirms `signal-hub-guardrails` is exercised and not bypassed (e.g. seeded linting violation case).

## 4. Missing tests or E2E campaign gaps

1. Two-foreman concurrent-claim test (fencing correctness).
2. GitHub primary and secondary rate-limit transient classification.
3. Human force-pushes onto foreman's branch between checks-green and merge: expected-head merge guard must reject.
4. Worker killed mid-run: claim recoverable but not auto-released until fence proves dead.
5. Unclassifiable failure default-deny (never silently safe).
6. Duplicate-matcher false-positive guard: two superficially similar but distinct issues.
7. Harness rejects "pass" when issue holds both `autonomy:ready` and any terminal label.
8. Path-redaction coverage for absolute paths leaking usernames or host-specific roots (current tests only cover "secret-like").
9. Branch protection changes mid-run (new required check appears).
10. `autonomy:ready` removed mid-run: must release claim cleanly, no blocked label.
11. PR force-pushed by third party after foreman recorded expected head: merge refused with non-blocked terminal evidence.
12. Coverage-matrix enforcement test on the campaign harness itself.
13. Retry-ledger key correctness across base SHA changes (does a rebase preserve or reset the counter?).
14. Evidence-volume cap test: a repeatedly-retried issue does not produce an unbounded comment chain or unbounded artifact files.
15. Publisher behavior when a generated-improvement issue has a closed but reverted PR.
16. Test that worker subprocess environment actually lacks GitHub write credentials (the spec asserts this; nothing proves it).

## 5. Unsafe assumptions or overengineering to remove

Unsafe assumptions:

1. Worker "has no GitHub write authority" is asserted but not proven by a test that inspects the worker process environment / token scope.
2. Secret-scan false-positive auto-remediation as currently scoped is too broad. Either restrict to a fixture-only path allowlist with positive/negative tests, or remove from `ci_retryable`.
3. Dirty-worktree classifier is implicitly trusted to be complete. Default must fail-closed to `tamper_or_scope_violation`; spec does not pin this.
4. Branch-deletion ownership proof depends on the fence record. If the runtime DB is wiped (recovery, host swap), no branch is provably owned and the rule must say "never delete," not "best-effort delete."
5. Per-signature 1-repair budget within a run treats every signature-1 outcome as safe. Add a per-issue-lifetime cap so a misclassified signature cannot recur across runs indefinitely.
6. The 7-day wall-clock cap assumes that all retry classes share one timeline. A `base_update_needed` blocked on upstream may legitimately wait longer than a worker-revision class.

Overengineering to remove:

1. 15 nonterminal states is excessive. `stale_claim_recovered`, `stale_blocked_reconsidered`, `worker_done`, `verified`, `reviewed` are transitional moments inside a single run, not durable persistence states. Collapse to ~6-7 durable states (`queued`, `preflight`, `claimed`, `worker_running`, `pr_open`, `awaiting_external`, terminal); carry sub-state on attempt records, not labels/DB.
2. `abandoned_safety` and `true_blocked` are functionally similar terminal outcomes (issue left for human with evidence). Could be one terminal with a sub-reason.
3. The 12-step foreman validation contract should be expressed as invariants (re-read state, validate exit, validate scope, validate evidence, no admin merge, head-guarded merge), not as a rigid step sequence that future code must mechanically replicate.
4. Plan Task 10 (remove duplicate verification run) is fine, but the plan should state what replaces the lost signal (e.g. pre-merge head re-poll already covers some). Otherwise this is a regression dressed as cleanup.
5. Spec separately specifies "redaction" rules across multiple sections; a single redaction-contract section referenced from each surface would reduce drift risk.

## 6. Final recommendation

ACCEPT_WITH_CHANGES. The spec correctly separates retryable revision gates from terminal blockers and the plan's TDD-first structure with RED/GREEN evidence is the right shape. The structural decisions (fencing token, structured terminal outcomes, evidence schema, expected-head merge guard, campaign-as-validation) are sound.

The blockers above are not architectural — they are concrete gaps that, left unspecified, will cause one of three failures: (a) the dirty classifier or signature catalog drifts into silent unsafe remediation, (b) the retry ledger fails to persist across cron ticks and caps become meaningless, or (c) the 20-case campaign closes on 20 trivial merges and proves nothing about duplicate / already-satisfied / retry-exhausted paths.

Do not begin Task 1 RED until the spec patches for the worker wire format, failure-signature catalog, protected-file list, generator allowlist, and campaign coverage matrix are committed. Those decisions back-propagate into the test names, fixtures, and parser shapes in Tasks 1-3, 5, 8, and 9, and re-doing them later wastes a full TDD pass. Once those land plus the plan patches for persistence, migration, rate-limit, concurrency, the #37 regression test, and explicit campaign abort criteria, this can move to implementation safely.
