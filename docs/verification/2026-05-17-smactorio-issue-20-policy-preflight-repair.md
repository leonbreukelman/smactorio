# SmactorIO Issue #20 Verification: policy, preflight, repair gating

Timestamp: 2026-05-17T16:08:57Z
Branch: fix/smactorio-policy-diagnostics
Issue: https://github.com/leonbreukelman/rtx3070-workshop-ops/issues/20

## What changed

- SmactorIO issue bodies are no longer hard-blocked by raw forbidden phrase matches. Hard eligibility is now state, required labels, blocked labels, and direct high-risk title asks.
- `no_work` now reports body-free per-issue skip reasons so an eligible-looking issue is not silently rejected.
- The foreman now runs a trusted preflight before claim/worker launch to ensure guardrail scripts exist and the baseline diff is clean.
- `git diff --check` whitespace auto-repair is constrained to allowed worker-changed prefixes (`signal-hub/`, `.github/workflows/`) so trusted repair code does not rewrite disallowed paths before terminal scope checks.

## Verification

```text
python3 -m unittest tests.test_smactorio_issue_foreman.SmactorioIssueForemanTest.test_ops_issue_body_can_document_stop_conditions_without_being_blocked tests.test_smactorio_issue_foreman.SmactorioIssueForemanTest.test_no_work_reports_why_each_visible_issue_was_skipped -v
# RED before implementation: failed because body text blocked issue #20-style ops tickets and no skipped_issues existed.
# GREEN after implementation: passed.
```

```text
python3 -m unittest tests.test_smactorio_issue_foreman.SmactorioIssueForemanTest.test_worker_diff_check_repairs_only_allowed_worker_changed_paths tests.test_smactorio_issue_foreman.SmactorioIssueForemanTest.test_trusted_preflight_fails_before_worker_when_guardrail_scripts_are_missing -v
# RED before implementation: failed because disallowed paths were repaired and preflight did not exist.
# GREEN after implementation: passed.
```

```text
python3 -m unittest tests.test_smactorio_issue_foreman -q
# Ran 29 tests: OK
```

```text
python3 -m unittest discover -s tests -q
# Ran 199 tests: OK
# Public generated artifacts produced by tests were reverted afterward; no generated public files are included in this change.
```

```text
git diff --check
python3 signal-hub/scripts/check_path_scope.py --from-file /tmp/smactorio-fix-changed-paths.txt --allow-prefix signal-hub/ --allow-prefix .github/workflows/
python3 signal-hub/scripts/scan_for_secrets.py .github/workflows signal-hub
# All passed; path-scope and secret scan output: []
```

```text
Independent review via delegate_task
# PASS: no blockers found for the policy/no_work diagnostics, trusted preflight, or constrained repair changes.
```
