# Codex model audit — SmactorIO implementation hazards and test gaps

## Provenance

Tool: Codex CLI 0.131.0.

- Attempted requested Codex-family model: `gpt-5.1-codex-mini`.
- Result: unavailable for this ChatGPT-account Codex configuration (`model is not supported when using Codex with a ChatGPT account`).
- Fallback used successfully: default Codex CLI model `gpt-5.5`, provider `openai`.
- Command: `codex exec -C /home/leonb/projects/rtx3070-workshop-ops --sandbox read-only --ephemeral -o /tmp/smactorio-phase2/codex-output.txt <prompt> < /tmp/smactorio-phase2/model-context.md`.
- Mode: read-only sandbox, no approvals, no repo writes.

## Tool notes

The full Codex event transcript included the supplied model context and is intentionally not copied into this repository to avoid duplicating large raw investigation/code snippets. The final model report is preserved below.

## Model output

**1. Highest-Risk Current Code Hazards**

- The foreman still collapses most failures into terminal `smactorio:blocked`: the broad `except` path comments “SmactorIO blocked” and applies the blocked label for worker failures, review failures, CI failures, merge-state races, dirty worktrees, and true external blockers alike in [smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/smactorio_issue_foreman.py:1653).
- `run_independent_review()` does not enforce its own “final line” contract. It accepts `SMACTORIO_VERDICT: PASS` anywhere in output unless `BLOCK` also appears, which is weaker than the prompt in [smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/smactorio_issue_foreman.py:698).
- Already-satisfied completion trusts a final stdout marker plus clean/no-diff state, but does not preserve or validate structured worker evidence/checks before closing in [smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/smactorio_issue_foreman.py:1562).
- `discard_verification_side_effects()` runs broad `reset --hard HEAD` and `clean -fd -- signal-hub .github/workflows`; it is probably intended after verification, but it has no first-class classifier or path cap, so evidence/diagnostics cannot distinguish safe generated drift from unknown source-side effects in [smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/smactorio_issue_foreman.py:1056).
- PR checks are boolean/terminal too early. Failed required checks immediately raise; `BEHIND`/blocked merge states just poll until timeout; there is no branch update, CI log fetch, retry, or repair loop in [smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/smactorio_issue_foreman.py:1268).
- Publisher duplicate detection depends on one `gh issue list --state all --limit 1000` result; if truncated/stale/API-filtered, `find_existing_generated_issue()` can miss a prior issue and create another in [project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/project_improvement_processor.py:743).
- `link_existing_issue_outcome()` treats blocked labels before terminal state. A closed/done issue that still has `smactorio:blocked` can be returned as `blocked` rather than `linked_existing_terminal` in [project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/scripts/project_improvement_processor.py:879).

**2. Concrete Tests To Add First**

- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_review_pass_marker_must_be_final_nonempty_line`
- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_worker_failure_records_retryable_state_without_blocked_label_for_safe_class`
- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_ci_failed_required_check_classified_for_revision_not_terminal_block`
- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_merge_state_behind_requests_base_update_before_timeout`
- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_already_satisfied_requires_structured_evidence_and_no_diff`
- [test_smactorio_issue_foreman.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_smactorio_issue_foreman.py:1): `test_verification_artifact_redacts_tokens_paths_and_caps_output`
- [test_project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_project_improvement_processor.py:1): `test_closed_blocked_done_generated_issue_links_terminal_not_blocked`
- [test_project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_project_improvement_processor.py:1): `test_publish_blocks_when_github_issue_list_may_be_truncated`
- [test_project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_project_improvement_processor.py:1): `test_duplicate_hidden_marker_matching_uses_exact_fields_not_substrings`
- [test_project_improvement_processor.py](/home/leonb/projects/rtx3070-workshop-ops/signal-hub/tests/test_project_improvement_processor.py:1): `test_existing_blocked_open_issue_does_not_create_duplicate_candidate`

**3. Minimal Implementation Surfaces Likely Needed**

- A small failure classifier around the `run_once()` exception path: `true_blocked`, `retryable_failed`, `needs_revision`, `ci_failed_retryable`, `base_update_needed`, `review_changes_requested`.
- A structured terminal worker outcome parser for `ALREADY_SATISFIED`, including checks run and acceptance evidence.
- A redacted evidence writer used by verification artifacts, blocked comments, command-error summaries, and review output.
- A dirty-worktree classifier returning explicit path classes instead of raw status strings.
- A PR gate abstraction that separates pending, failed, missing, behind, conflicted, draft, head-changed, and review-thread-blocked states.
- Publisher dedupe should either query by marker/search more directly or fail closed when issue enumeration is incomplete.

**4. Branch/PR/CI/Review Handling Gaps**

- No GitHub review-thread/conversation-resolution handling despite required conversation resolution.
- No CI log fetch or safe patch loop for failed `signal-hub-guardrails`.
- No rebase/base-update path for strict branch protection.
- No retry ledger keyed by issue, failure class, base/head, and attempt count.
- `open_pr_mentions_issue()` causes `no_work` when a PR exists, but there is no reconciliation path to inspect whether that PR is stale, merged, failed, or needs cleanup.

**5. Redaction/Evidence-Size Risks**

- Verification artifacts include command text and tail output without the processor’s redaction filters.
- Error comments include `str(exc)[-1800:]`; command errors can contain absolute paths or raw tool output.
- `run_verification()` embeds absolute worktree paths in scan commands.
- Generated side-effect evidence stores raw porcelain status tails; capped, but not redacted or schema-bound.
- There is no aggregate artifact size cap, only per-command tail caps.

**6. Worker Prompt vs Foreman Guard Contradictions**

- Reviewer prompt says final line must be `SMACTORIO_VERDICT: PASS`; foreman accepts PASS anywhere.
- Worker prompt says final response should summarize files/checks, but already-satisfied completion discards that detail and only records the marker.
- Worker is told to commit completed implementation, while foreman later adds and commits verification artifacts itself; artifact-only output is rejected, but the prompt does not clearly describe that boundary.
- Prompt asks for targeted checks and evidence; foreman can still reject noisy evidence only through reviewer judgment, not deterministic evidence schema tests.
