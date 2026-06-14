# Copilot model audit — SmactorIO PR/workflow/branch-protection lane

## Provenance

Tool: GitHub Copilot CLI 1.0.48. Command: `copilot -p <prompt> --allow-all-tools --allow-all-paths --allow-all-urls --output-format text`, with prompt restricted to read-only inspection and context path `/tmp/smactorio-phase2/model-context.md`. Model name was not surfaced by the CLI. Fallback: stdin probe failed/timed out, so file-path reading via tools was used. Git status after run showed no model-written repo changes.

## Stderr / tool notes

```text
Warning: Ignoring invalid allowedUrls entry "https://http//localhost:8080$u". Error: Invalid URL pattern: https://http//localhost:8080$u


Changes   +0 -0
Requests  1 Premium (3m 22s)
Tokens    ↑ 1.4m • ↓ 10.8k • 1.3m (cached) • 5.4k (reasoning)
```

## Model output

Reviewing the SmactorIO PR path now. I’ll read the provided context plus the relevant repo workflow and automation files, then map failure modes to concrete gaps and test cases.

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ 1 line read

● handoff_read (MCP: maei-supervisor)
  └ {"has_handoff":false,"handoff":null}

● Search (glob)
  │ "**/*pull*request*"
  └ No matches found

● Search (glob)
  │ "**/*label*"
  └ 1 file found

● Search (glob)
  │ "**/*copilot*"
  └ 4 files found

● Search (glob)
  │ "**/*branch*protection*"
  └ No matches found

● Search (glob)
  │ "**/*signal*hub*guardrails*"
  └ No matches found

● Search (glob)
  │ "**/*smactorio*"
  └ No matches found

● Search (glob)
  │ ".github/workflows/*"
  └ 4 files found

● Search (glob)
  │ "**/*issue*"
  └ 5 files found

● governance_non_negotiable (MCP: maei-governance) · level: "oneliner"
  └ [{"id":"cg:ANALYZE-1","title":"Problem Decomposition Protocol","severity...

● memory_stats (MCP: maei-memory)
  └ {"total_memories":10495,"by_type":{"conversation":37,"decision":3582,"le...

● memory_search (MCP: maei-memory) · copilot-md canonical · query: "copilot-md canonical", limit: 5
  └ {"summary":"Using 1 trusted memories and 4 needs_review memories; 0 bloc...

● watchdog_status (MCP: maei-supervisor)
  └ {"heartbeat_file":"/home/leonb/maei/.claude/heartbeat","heartbeat_exists...

● heartbeat (MCP: maei-supervisor)
  └ {"timestamp":"2026-05-19T03:40:09.861002+00:00","file":"/home/leonb/maei...

● Read ci.yml
  │ .github/workflows/ci.yml
  └ 74 lines read

● Read auto-update-prs.yml
  │ .github/workflows/auto-update-prs.yml
  └ 28 lines read

● Read auto-merge.yml
  │ .github/workflows/auto-merge.yml
  └ 26 lines read

● Read attribution-drift-check.yml
  │ .github/workflows/attribution-drift-check.yml
  └ 138 lines read

● Search (grep)
  │ "signal-hub-guardrails|strict required checks|conversation
  │ resolution|head.sha|merge head|rebase|base update|branch protection|required
  │ check|pending check|status check|statusCheckRollup|review comment|Copilot
  │ review|branch-name|smactorio:claimed|smactorio:blocked|smactorio:done|autono
  │ my:ready|artifact-only|duplicate|already-satisfied|evidence comment|audit"
  │ in *.{py,ts,js,yml,yaml,md,json} (/tmp/smactorio-phase2)
  └ 8 lines found

● Search (grep)
  │ "signal-hub-guardrails|smactorio:claimed|smactorio:blocked|smactorio:done|au
  │ tonomy:ready|already-satisfied|duplicate|artifact-only|review
  │ comment|copilot|statusCheckRollup|mergeStateStatus|head\.sha|rebase|update-b
  │ ranch|conversation|branch protection|required check|pending check"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 86 lines found

● Search (grep)
  │ "^#|^##|^###|^File:|^Path:|^Source:|\.py|\.yml|\.yaml|\.ts|\.js"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 45 lines found

● Search (grep)
  │ "signal-hub-guardrails|smactorio:claimed|smactorio:blocked|smactorio:done|au
  │ tonomy:ready|already-satisfied|duplicate|artifact-only|review
  │ comment|copilot|statusCheckRollup|mergeStateStatus|head\.sha|rebase|update-b
  │ ranch|conversation|branch protection|required check|pending check" in
  │ *.{py,ts,js,yml,yaml,md,json}
  └ 8 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L44:140 (96 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L302:353 (52 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L157:266 (110 lines read)

● Search (grep)
  │ "def pr_checks_are_green|def wait_for_pr_checks|def
  │ merge_pr|statusCheckRollup|mergeStateStatus|headRefOid|review|conversation|a
  │ rtifact-only|already_satisfied|ALREADY_SATISFIED|duplicate|blocked_label|cla
  │ im_label|done_label|recover_stale_claims|comment|evidence"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 7 lines found

I found the main contract and root-cause sections. Next I’m pulling the embedded foreman and test excerpts that cover check polling, merge guards, duplicate/already-satisfied handling, and label cleanup.

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L514:760 (247 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1030:1110 (81 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1671:2145 (355 lines read)

● Search (grep)
  │ "def pr_checks_are_green|def wait_for_pr_checks|def merge_pr|def
  │ recover_stale_claims|ALREADY_SATISFIED|artifact-only|signal-hub-guardrails|s
  │ tatusCheckRollup|headRefOid|mergeStateStatus|review|comment|duplicate|smacto
  │ rio:blocked|smactorio:done|smactorio:claimed"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 8 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L990:1065 (76 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L2026:2073 (48 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1373:1665 (293 lines read)

● Search (grep)
  │ "test_.*(already_satisfied|duplicate|wait_for_pr_checks|pr_checks|merge_pr|h
  │ ead|conversation|review|blocked|label|claim|artifact|redact|evidence|update)
  │ .*" (/tmp/smactorio-phase2/model-context.md)
  └ 8 lines found

● Search (grep)
  │ "def pr_checks_are_green|def recover_stale_claims|def
  │ branch_name_for_issue|def complete_already_satisfied|def
  │ assert_worker_material_change|def discard_worker_generated_side_effects|def
  │ complete_issue|def close_issue|--match-head-commit|issue
  │ edit|remove.*smactorio:blocked|smactorio:done|autonomy:ready|duplicate"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 44 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L760:930 (171 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1240:1305 (66 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1510:1665 (156 lines read)

● Search (grep)
  │ "def complete_issue|def
  │ complete_already_satisfied_issue|issue_comment\(|edit_issue_labels\(|close_i
  │ ssue\(|remove=\[.*blocked|add=\[.*done|autonomy:ready"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 29 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1110:1185 (76 lines read)

● Search (grep)
  │ "statusCheckRollup.*state|context|WORKFLOW_RUN|CHECK_RUN|PENDING|IN_PROGRESS
  │ |SUCCESS|SKIPPED|FAILURE|NEUTRAL|mergeStateStatus.*BEHIND|BLOCKED|DIRTY|UNST
  │ ABLE|HAS_HOOKS" (/tmp/smactorio-phase2/model-context.md)
  └ 3 lines found

● Search (grep)
  │ "test_.*(pr_checks|merge_pr|head_sha|statusCheckRollup|mergeStateStatus|alre
  │ ady_satisfied|duplicate|recovered|claim|artifact).*"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 5 lines found

● Search (grep)
  │ "pr_checks_are_green\(|required_workflow_name|required_seen|status context
  │ not successful|workflow run|check run|headRefOid"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 7 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1210:1295 (86 lines read)

● Search (grep)
  │ "def pr_checks_are_green\(|expected_head|required_workflow_name|statusCheckR
  │ ollup" (/tmp/smactorio-phase2/model-context.md)
  └ 10 lines found

● Search (grep)
  │ "test_.*(wait_for_pr_checks|merge_pr|head|check).*"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 1 line found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1185:1245 (61 lines read)

● Search (grep)
  │ "required_workflow_name\s*=|headRefOid|statusCheckRollup\)|for check in
  │ payload.get\("statusCheckRollup"|context_name|WORKFLOW_RUN|CHECK_RUN"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 17 lines found

● Search (grep)
  │ "test_.*(already_satisfied|duplicate|stale_claim|blocked_label|done_label|op
  │ en_pr_mentions_issue).*" (/tmp/smactorio-phase2/model-context.md)
  └ No matches found

● Search (grep)
  │ "blocked_labels|terminal_labels|required_labels|preferred_labels|claim_label
  │ |done_label|blocked_label|issue_is_eligible|issue_ineligibility_reasons"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 32 lines found

● Search (grep)
  │ "Copilot review ran and commented|required conversation resolution|no
  │ required PR reviews configured|strict required status check"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 5 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L360:435 (76 lines read)

● Search (grep)
  │ "1800|2000|redact|SENSITIVE_ENV_FRAGMENTS|raw dumps|verification
  │ artifact|comment.*1800|Previous claim|json.dumps\(marker"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 10 lines found

● Search (grep)
  │ "review|independent review|resolve|thread|conversation"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 12 lines found

● Read copilot-tool-output-1779162089031-iji2q0.txt
  │ /tmp/copilot-tool-output-1779162089031-iji2q0.txt
  └ L1:180 (131 lines read)

● Read copilot-tool-output-1779162089030-zj5qle.txt
  │ /tmp/copilot-tool-output-1779162089030-zj5qle.txt
  └ L1:180 (129 lines read)

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L139:156 (17 lines read)

● Search (grep)
  │ "test_.*(branch_name|collision|reuse|behind|blocked|merge_state|conversation
  │ |copilot|review comment|duplicate|already satisfied).*"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 4 lines found

● Search (grep)
  │ "branch_name_for_issue|branch uniqueness|collision|reuse|closed or merged
  │ PRs|PROC-14|review thread per branch lifetime|update-branch|mergeStateStatus
  │ ==|BEHIND|BLOCKED|DIRTY|UNSTABLE" (/tmp/smactorio-phase2/model-context.md)
  └ 5 lines found

● Search (grep)
  │ "except SmactorioError|issue_comment\(repo, issue_number, f"SmactorIO
  │ blocked|needs_attention_label|blocked_label"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 11 lines found

● Read model-context.md
  │ /tmp/smactorio-phase2/model-context.md
  └ L1295:1350 (56 lines read)

● Search (grep)
  │ "open_pr_mentions_issue|gh pr list|headRefName|branch"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 10 lines found

● Search (grep)
  │ "SENSITIVE_ENV_FRAGMENTS|redact|sanitize|mask|censor|absolute runtime
  │ paths|json.dumps\(marker|result.stdout\[-2000:\]|str\(exc\)\[-1800:\]"
  │ (/tmp/smactorio-phase2/model-context.md)
  └ 10 lines found

● Search (grep)
  │ "SENSITIVE_ENV_FRAGMENTS" (/tmp/smactorio-phase2/model-context.md)
  └ 11 lines found

## 1. PR/workflow failure modes and handling recommendations

- **Required-check race / missing-check ambiguity.** Branch protection requires strict `signal-hub-guardrails`, and the foreman polls `statusCheckRollup`, but the visible logic only says “required workflow not seen”, “check not complete”, or “merge state is not clean”. It does **not** separate “GitHub rollup not populated yet” from “required check will never appear”. Recommendation: classify `ci_pending`, `required_check_missing`, and `required_check_failed` separately, with bounded polling only for the first case.

- **Strict branch protection base-update deadlock.** `pr_checks_are_green()` only accepts `mergeStateStatus` of `CLEAN` or `HAS_HOOKS`, but `_pr_check_failure_is_terminal()` does not treat `merge state is not clean` as terminal. A PR that is merely `BEHIND` or needs base update will likely sit until timeout instead of being rebased/updated. Recommendation: add an explicit `base_update_needed` path that updates the branch, records the new head SHA, and reruns checks.

- **Conversation-resolution blind spot.** Branch protection has **required conversation resolution enabled** and **no required PR reviews configured**. That means Copilot review threads can block merge even when checks are green. The visible flow waits for checks and then merges; there is no visible GitHub review-thread read/respond/resolve loop. Recommendation: add a review gate that lists reviews/comments/threads, classifies actionable low-risk feedback, applies bounded fixes, and resolves/responds before merge.

- **Head-SHA race handling is only half done.** The merge uses `--match-head-commit`, which is good, and check polling validates `headRefOid`. But any head change still falls into the generic exception path and becomes `smactorio:blocked`. Recommendation: distinguish external head drift, self-caused rebase/update drift, and true stale-claim drift.

- **Everything post-claim can collapse to `smactorio:blocked`.** The exception path comments “SmactorIO blocked” and adds `smactorio:blocked` for any claimed failure: review failures, CI failures, merge races, missing checks, and real blockers. Recommendation: split outcomes into `review_changes_requested`, `ci_failed_retryable`, `ci_pending`, `base_update_needed`, `true_blocked`, and `retry_exhausted`.

- **Label lifecycle is incomplete.** Completion removes `smactorio:claimed` and `smactorio:blocked`, adds `smactorio:done`, and closes the issue, but does **not** remove `autonomy:ready`. Recommendation: make labels a projection of state and reconcile them on every terminal outcome.

- **Duplicate / already-satisfied no-PR outcomes are uneven.** The already-satisfied no-PR path is visible. Publisher-side dedupe/linking is visible. What is not proven is a full foreman-side duplicate close/link flow with audit evidence and no artifact-only PR. Recommendation: make duplicate and already-satisfied first-class terminal states with the same closure/evidence discipline as merged PRs.

- **Evidence comments are capped, but not cleanly redacted.** The context shows caps like `[-1800:]` and `[-2000:]`, but #37 still failed review for broad raw dumps, file hashes, absolute runtime paths, and generated artifacts. Recommendation: switch from “tail of raw output” to a structured evidence schema: command summary, outcome, capped changed-path list, issue/PR/commit URLs, and explicit redaction filters.

## 2. Implementation/test gaps visible from the current code

- **No visible GitHub review-thread handling** despite required conversation resolution and observed Copilot comments on PR #42 and #43.
- **No visible tests for `mergeStateStatus` classes** like `BEHIND`, `BLOCKED`, or conflict/update-required paths.
- **No visible tests for “required workflow never appears”** versus “check still pending”.
- **No visible stale-`smactorio:blocked` reconciler.** Stale claim recovery exists; stale blocked recovery does not.
- **No visible foreman E2E test for duplicate closure without PR.** The publisher can link existing issues, but the issue-foreman path is not shown doing the same.
- **Branch uniqueness is weakly tested.** The visible test proves shell-safe naming, not remote branch collision avoidance or “never reuse a branch with prior PR history”.
- **Completion leaves `autonomy:ready` behind.**
- **Evidence hygiene is inconsistent.** The processor visibly redacts publication reasons, but foreman comments still emit raw exception tails and raw claim JSON.

## 3. E2E campaign cases most likely to expose real GitHub automation bugs

1. **Rollup delay:** PR opens, `statusCheckRollup` is initially empty, then `signal-hub-guardrails` appears later and passes.
2. **Missing required check:** PR opens, required check never appears because of workflow rename/skip/misconfiguration.
3. **Strict-protection behind case:** PR is green but `mergeStateStatus=BEHIND`; branch update is required before merge.
4. **Copilot thread blocker:** all checks pass, but an unresolved Copilot review thread blocks merge.
5. **Retryable guardrail failure:** required check fails with a safe, deterministic fix path; foreman should patch, push, and continue.
6. **Head-SHA drift:** branch head changes after checks, before merge.
7. **Already satisfied:** worker returns `SMACTORIO_OUTCOME: ALREADY_SATISFIED`, no commits, no PR, issue closes cleanly.
8. **Duplicate open issue:** current ticket should link to an already-open matching issue without creating a PR.
9. **Duplicate closed terminal issue:** current ticket should close/link to a previously closed/done/duplicate issue without reopening work.
10. **Stale claim recovery:** claim TTL expires after crash; issue returns to queue without manual label cleanup.
11. **Artifact-only output:** worker only changes verification artifacts; foreman must reject PR creation and route to a no-PR terminal outcome if appropriate.
12. **Stale blocked cleanup after capability fix:** an issue previously marked `smactorio:blocked` becomes safely retryable after a deployed fix.

## 4. Warnings about unsafe assumptions

- **Passing `signal-hub-guardrails` is not enough** when conversation resolution is also required.
- **A non-clean merge state is not always transient.** `BEHIND` usually needs an update, not more waiting.
- **`smactorio:blocked` is not trustworthy as a terminal meaning today.** It currently mixes retryable failures and true blockers.
- **Output truncation is not redaction.** Tailing raw logs can still leak absolute paths and sensitive context.
- **A unique-looking branch name is not proof against branch-lifecycle collisions** unless remote/history checks enforce it.
- **Issue #37 is not proof of autonomous success.** The context says it was ultimately resolved by supervising/manual takeover via PR #43, not by a complete autonomous repair loop.
