# SmactorIO autonomous ticket resolution hardening plan — 2026-05-19

> For Hermes: implement this plan with strict TDD. Use subagent-driven-development only for independent review/implementation slices after the spec/plan review is patched.

Goal: make SmactorIO autonomously resolve eligible low-risk GitHub issues end-to-end, including duplicate/already-satisfied/retryable edge cases, without generic “simple to fix but blocked” loops.

Architecture: preserve the existing foreman/publisher shape and add first-class lifecycle classification, structured terminal outcomes, retry/stale-label handling, PR/CI/review gates, evidence redaction, and a live E2E campaign harness. Avoid broad rewrites unless a failing test proves the existing architecture cannot support the contract.

Tech stack: Python scripts/tests under `signal-hub/`, GitHub CLI/API, SQLite runtime state, systemd SmactorIO timer/service on rtx3070.

---

## Evidence status before implementation

- CONFIRMED: `main` branch protection requires strict `signal-hub-guardrails`, admin enforcement, and conversation resolution.
- CONFIRMED: issue #37 was low-risk and should have reached merged, duplicate, or already-satisfied terminal state rather than staying blocked.
- CONFIRMED: current code has first pieces of already-satisfied, stale-claim, run-tests wrapper, generated drift, and whitespace repair handling.
- CONFIRMED: model review found remaining gaps in generic blocked exception handling, structured evidence, duplicate foreman path, stale blocked reconciliation, CI/review/rebase handling, redaction, and self-repair quarantine.
- PARTIALLY CONFIRMED: review-comment resolution behavior needs live verification during the campaign because current repo has conversation resolution enabled but no required PR review.
- NEEDS IMPLEMENTATION: failure-class retry ledger, structured terminal outcome parser, first-class dirty classifier, redaction/evidence writer, E2E harness, and real-ticket campaign.

## Task 1: Add failure taxonomy and attempt-ledger characterization tests

Objective: define expected retry/blocking behavior before touching production code.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Later production target: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing tests:
   - `test_worker_failure_records_retryable_state_without_blocked_label_for_safe_class`
   - `test_true_blocker_is_the_only_generic_path_that_applies_blocked_label`
   - `test_retry_exhausted_gets_needs_attention_with_structured_class`
2. Run RED:
   - `cd signal-hub && scripts/run_tests.sh tests/test_smactorio_issue_foreman.py -k 'retryable_state or true_blocker or retry_exhausted' -v`
   - Expected: fail because classifier/ledger APIs do not exist or generic blocked path is current behavior.
3. Implement minimal classifier/ledger helpers:
   - `FailureClass` constants or enum.
   - `classify_foreman_failure(...)` helper.
   - attempt record write/read helpers using existing runtime DB pattern if present; otherwise pure helper plus in-memory/fake command runner until DB integration task.
4. Run GREEN targeted test.
5. Run full foreman test file.

## Task 2: Enforce structured already-satisfied and duplicate terminal outcomes

Objective: replace marker-only no-PR outcomes with validated structured evidence and no-diff proof.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing tests:
   - `test_already_satisfied_requires_structured_evidence_and_no_diff`
   - `test_already_satisfied_with_commits_is_rejected`
   - `test_already_satisfied_with_nonzero_exit_is_rejected`
   - `test_duplicate_terminal_outcome_closes_without_pr`
2. Run RED with `signal-hub/scripts/run_tests.sh` targeted selectors.
3. Implement parser for fenced JSON worker terminal outcome plus final sentinel.
4. Update worker prompt generation to describe allowed outcomes.
5. Update foreman accept/reject-on-contradiction logic.
6. Run targeted GREEN and full foreman tests.

## Task 3: Add prompt-vs-foreman contract tests

Objective: prevent worker prompt outcomes from drifting away from foreman guards.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source only if test exposes prompt helper gaps.

Steps:
1. Write failing test `test_worker_prompt_outcomes_have_foreman_accept_and_reject_paths`.
2. The test should parse prompt text for outcome names and assert each has an entry in an outcome handler registry.
3. Run RED.
4. Introduce a small explicit outcome registry used by both prompt rendering and foreman parsing.
5. Run GREEN.

## Task 4: Add redacted evidence writer and apply it to comments/artifacts

Objective: ensure every foreman evidence surface is capped/redacted.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`
- Possibly reuse/align with redaction helpers in `signal-hub/scripts/project_improvement_processor.py`

Steps:
1. Write failing tests:
   - `test_issue_comment_redacts_secret_like_values_and_absolute_paths`
   - `test_verification_artifact_caps_and_redacts_output`
   - `test_blocked_exception_comment_uses_redacted_evidence`
2. Inject secret-shaped strings by constructing them from split literals so repository secret scans do not flag the test source.
3. Run RED.
4. Implement `redact_evidence_text`, `cap_evidence_block`, and evidence-schema helpers.
5. Route every `issue_comment`, verification artifact, and exception summary through the helper.
6. Run GREEN plus repository secret scan.

## Task 5: Replace broad generated cleanup with dirty-worktree classifier

Objective: distinguish material changes, safe generated drift, repairable whitespace, unknown source edits, and unsafe paths.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing tests:
   - `test_generated_public_drift_discard_requires_known_generated_file`
   - `test_unknown_source_change_is_not_discarded`
   - `test_missing_executable_bit_on_new_script_is_repaired`
   - `test_diff_check_trailing_whitespace_repairs_allowed_path_only`
2. Run RED.
3. Implement dirty classifier returning explicit class objects and remediation plans.
4. Replace raw `reset --hard`/`clean` calls with classifier-scoped cleanup.
5. Run GREEN.

## Task 6: Harden publisher dedupe and closed/blocked terminal handling

Objective: stop duplicate ticket loops across open/closed/stale-blocked issue states.

Files:
- Modify test: `signal-hub/tests/test_project_improvement_processor.py`
- Modify source: `signal-hub/scripts/project_improvement_processor.py`

Steps:
1. Write failing tests:
   - `test_closed_blocked_done_generated_issue_links_terminal_not_blocked`
   - `test_publish_blocks_when_github_issue_list_may_be_truncated`
   - `test_duplicate_hidden_marker_matching_uses_exact_fields_not_substrings`
   - `test_existing_blocked_open_issue_does_not_create_duplicate_candidate`
2. Run RED.
3. Patch `link_existing_issue_outcome()` ordering so terminal closed/done wins over stale blocked labels.
4. Add enumeration completeness/fail-closed guard or targeted search fallback.
5. Run GREEN.

## Task 7: Add stale blocked-label reconciler

Objective: make stale `smactorio:blocked` retryable when current code can safely remediate it, without erasing true blockers.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing tests:
   - `test_stale_blocked_retryable_issue_is_unblocked_with_evidence`
   - `test_true_blocked_issue_remains_blocked`
   - `test_successful_terminal_outcome_removes_blocked_and_ready_labels`
2. Run RED.
3. Implement `recover_stale_blocked_issues(...)` after stale-claim recovery and before queue selection.
4. Ensure evidence comments are redacted/capped.
5. Run GREEN.

## Task 8: Add PR gate classification for CI, base update, and review comments

Objective: treat PR blockers as revision gates before terminal blocking.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing tests:
   - `test_ci_failed_required_check_classified_for_revision_not_terminal_block`
   - `test_merge_state_behind_requests_base_update_before_timeout`
   - `test_unresolved_review_thread_enters_review_revision_gate`
   - `test_pr_checks_are_green_requires_expected_head_and_final_label_reread`
2. Run RED.
3. Split PR state polling into explicit classification result:
   - `green`, `pending`, `failed_retryable`, `failed_nonretryable`, `behind`, `conflicted`, `review_blocked`, `head_changed`.
4. Implement base-update/recheck path with cap.
5. Implement read-only review comment/thread listing and classification. Resolve/reply only where tool/API path is available and low-risk.
6. Run GREEN.

## Task 9: Add self-repair quarantine and `.github/workflows` low-risk exclusion

Objective: prevent broken SmactorIO from consuming its own repair tickets or modifying CI guardrails under the low-risk lane.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_policy.py`
- Modify source: `signal-hub/scripts/smactorio_repo_guard.py` if path scope lives there

Steps:
1. Write failing tests:
   - `test_smactorio_self_repair_issue_requires_explicit_approval_label`
   - `test_low_risk_issue_cannot_modify_github_workflows`
   - `test_self_repair_approval_label_allows_controlled_pickup`
2. Run RED.
3. Implement policy helper that scans title/body/acceptance/likely files for core runtime files.
4. Remove `.github/workflows/**` from default low-risk allowlist or require higher-trust label.
5. Run GREEN.

## Task 10: Remove or justify duplicate verification run

Objective: avoid confusing double verification and evidence bloat.

Files:
- Modify test: `signal-hub/tests/test_smactorio_issue_foreman.py`
- Modify source: `signal-hub/scripts/smactorio_issue_foreman.py`

Steps:
1. Write failing test `test_run_once_invokes_verification_once_per_material_attempt`.
2. Run RED if current code calls it twice.
3. Remove duplicate call or split into named pre/post artifact verification with explicit evidence rules.
4. Run GREEN.

## Task 11: Build real-ticket E2E campaign harness

Objective: create deterministic, auditable real GitHub issues and record worker/foreman outcomes without manual closure.

Files:
- Create test/helper: `signal-hub/scripts/smactorio_e2e_campaign.py`
- Create tests: `signal-hub/tests/test_smactorio_e2e_campaign.py`
- Output doc: `signal-hub/docs/verification/2026-05-19-smactorio-20-ticket-e2e-campaign.md`

Steps:
1. Write failing unit tests for campaign record schema and pass/fail rules:
   - `test_campaign_case_requires_claim_and_terminal_outcome`
   - `test_manual_closure_does_not_count`
   - `test_success_case_cannot_leave_blocked_and_ready_labels`
2. Run RED.
3. Implement dry-run harness for issue creation/selection, one-at-a-time invocation, evidence collection, and markdown matrix writing.
4. Run GREEN.
5. Do not run live campaign until hardening PR is merged/deployed.

## Task 12: Targeted and full local verification before PR

Objective: prove unit/integration behavior locally.

Steps:
1. Run targeted suites after each task with `signal-hub/scripts/run_tests.sh`.
2. Run full Signal Hub suite:
   - `cd signal-hub && scripts/run_tests.sh`
3. Run `git diff --check`.
4. Run secret scan over changed docs/scripts/tests/public artifacts.
5. Fix failures with TDD regressions only.

## Task 13: Independent code review and PR

Objective: land hardening through normal branch/PR/CI.

Steps:
1. Run independent review with `requesting-code-review` dimensions or strong CLI reviewer.
2. Fix valid findings with tests first.
3. Commit logical changes on `harden/smactorio-reliability-20260519`.
4. Push branch and open PR.
5. Inspect Copilot/GitHub review comments.
6. Amend for valid review feedback, rerun tests/scans, push.
7. Verify `signal-hub-guardrails` passes.
8. Merge without admin bypass.

## Task 14: Deploy/verify rtx3070 runtime and run 20+ issue campaign

Objective: prove the real live worker/foreman path handles edge cases.

Steps:
1. SSH to rtx3070 and verify clean checkout/service/timer before deploy.
2. Pull merged main or otherwise update canonical checkout via normal git flow.
3. Verify `smactorio.timer` and `smactorio.service` health.
4. Create/reuse campaign labels: `smactorio:e2e`, `smactorio`, `risk:low`, `autonomy:ready`.
5. Run cases one at a time unless concurrency has been proven safe.
6. For each failed/blocked case:
   - diagnose root cause;
   - add regression test;
   - implement/merge fix;
   - redeploy/update runtime;
   - rerun that case until it passes.
7. Stop only after at least 20 cases pass under the contract.
8. Save matrix to `signal-hub/docs/verification/2026-05-19-smactorio-20-ticket-e2e-campaign.md`.

## Task 15: Final verification and clean handoff

Objective: prove implementation and runtime health.

Steps:
1. Run relevant targeted tests.
2. Run full `signal-hub/scripts/run_tests.sh`.
3. Run `git diff --check`.
4. Run secret scan over changed docs/scripts/tests/public artifacts.
5. Verify all hardening PR checks passed.
6. Verify 20+ E2E issues terminally resolved by worker/foreman.
7. Verify no successful case has stale `smactorio:blocked` plus `autonomy:ready`.
8. Verify `smactorio.timer`/`smactorio.service` on rtx3070.
9. Verify canonical rtx3070 checkout clean: `git status --short --branch`.
10. If live pages changed, verify `http://192.168.30.10:8765/` and browser console.
11. Provide concise proof-based final response.

---

## Post-Opus review implementation patches

These patches incorporate the final Claude Opus/max-effort review. They are mandatory before Task 1 implementation starts.

### Task 0A: Pin source constants and worker wire format before RED tests

Files:
- Source target: `signal-hub/scripts/smactorio_issue_foreman.py`
- Tests: `signal-hub/tests/test_smactorio_issue_foreman.py`

Add tests first for constants/format before relying on them:

- `test_worker_outcome_wire_format_accepts_single_json_block_and_final_sentinel`
- `test_worker_outcome_wire_format_rejects_sentinel_without_json`
- `test_worker_outcome_wire_format_rejects_json_without_sentinel`
- `test_worker_outcome_wire_format_rejects_multiple_json_blocks`
- `test_worker_outcome_wire_format_rejects_truncated_or_mangled_sentinel`
- `test_protected_smactorio_runtime_paths_constant_is_non_empty_and_load_bearing`

Then implement only the constants/parser skeleton needed for those tests.

### Task 0B: Add persistent retry-ledger schema and restart test

Do not use a purely in-memory ledger except inside narrow unit fakes.

Tests:

- `test_attempt_ledger_persists_retry_count_across_reopen`
- `test_attempt_ledger_base_sha_change_keeps_issue_wall_clock_cap`
- `test_attempt_ledger_unreadable_db_fails_closed_before_claim`
- `test_two_foremen_cannot_claim_same_issue`

Implementation:

- Add SQLite table/migration for `issue_attempts` in the configured SmactorIO state DB.
- Wrap claim and attempt writes in a transaction.
- Make DB-unavailable a transient infrastructure failure before GitHub mutation.

### Task 0C: Pin dirty/generated/default-deny policy

Tests:

- `test_unclassifiable_dirty_diff_defaults_to_tamper_or_scope_violation`
- `test_generated_public_drift_requires_manifest_entry_or_marker`
- `test_missing_generated_manifest_fails_closed`
- `test_branch_without_fence_record_is_not_deleted`

Implementation:

- Add manifest path `signal-hub/public/.smactorio-generated-manifest.json` if production code needs it.
- Do not silently discard public drift without manifest/marker proof.

### Task 0D: Add issue #37 exact regression fixture

Tests:

- `test_issue_37_run_tests_wrapper_failure_becomes_retryable_or_terminal_not_blocked`
- `test_issue_37_already_closed_done_duplicate_links_terminal_not_blocked`

The fixture must model the original failure class: generated verification command not executable in repo / stale blocked-loop risk. Expected result is safe remediation, already-satisfied, duplicate/done link, or material PR path; never generic `smactorio:blocked`.

### Task 0E: Add deterministic failure signature catalogs

Tests:

- `test_ci_retryable_signature_catalog_is_exact_and_fixture_secret_case_is_tests_only`
- `test_forbidden_action_catalog_scans_title_body_comments_acceptance_and_likely_files`
- `test_github_rate_limit_is_transient_not_issue_blocked`
- `test_branch_protection_change_midrun_repolls_required_checks`

Implementation:

- Implement exact catalogs from the spec.
- Remove or narrow any broad secret-scan false-positive auto-repair behavior.

### Task 0F: Add existing blocked-label metadata migration/reconciler prework

Tests:

- `test_legacy_blocked_issue_without_structured_metadata_is_needs_attention_not_silent_retry`
- `test_structured_retryable_blocked_issue_is_unblocked_with_evidence`
- `test_closed_done_with_stale_blocked_label_is_terminal_for_dedupe`

Implementation:

- Reconciler must treat legacy unstructured blocked labels conservatively.
- Migration/comment only after redaction passes.

### Task 0G: Make campaign harness coverage explicit before live run

Tests:

- `test_campaign_matrix_requires_minimum_outcome_distribution`
- `test_campaign_aborts_after_three_same_root_cause_failures`
- `test_campaign_pass_rejects_terminal_label_plus_autonomy_ready`
- `test_campaign_teardown_requires_no_orphan_owned_branches`
- `test_manual_closure_does_not_count`

Implementation:

- Seed issue generator must create safe real GitHub issues with `smactorio:e2e` and deterministic expected outcome class.
- Harness must cap simultaneous open nonterminal campaign issues at five and default to one-at-a-time execution.

### Task 0H: Prove worker subprocess lacks GitHub write credentials

Tests:

- `test_worker_environment_omits_github_write_tokens`
- `test_worker_cannot_call_gh_issue_close_with_inherited_credentials`

Implementation:

- Worker env allowlist must exclude `GH_TOKEN`, `GITHUB_TOKEN`, token-like variables, and credential-bearing git URL env.
- Git operations requiring auth remain foreman-owned only.

### Task sequencing update

Run Tasks 0A through 0H before the original Task 1. Then continue with original Tasks 1-15, adjusting task names as needed.

Task 8 must explicitly choose and test the base-update tool path:

- preferred: `gh pr update-branch <pr> --repo leonbreukelman/rtx3070-workshop-ops` when branch protection supports it;
- fallback: `git fetch origin main && git rebase origin/main` in the isolated worktree only;
- always record pre/post head SHA before rerunning checks.

Task 13 and Task 14 are separate milestones:

- Task 13: code review, PR, CI, merge.
- Task 14: rtx3070 pre-deploy snapshot, runtime update, service/timer restoration, and live campaign.

Pre-deploy snapshot must record:

- `git status --short --branch`;
- `systemctl --user status smactorio.timer smactorio.service` or system scope equivalent;
- current timer enabled/active state;
- recent journal pointer/time window.

Campaign cleanup/teardown is a mandatory final step before Phase 6.
