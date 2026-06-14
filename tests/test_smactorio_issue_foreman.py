from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SmactorioIssueForemanTest(unittest.TestCase):
    def test_selects_oldest_ready_low_risk_issue(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        ready = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]
        issues = [
            {"number": 5, "title": "newer", "state": "OPEN", "url": "https://example.test/5", "labels": ready},
            {"number": 2, "title": "older", "state": "OPEN", "url": "https://example.test/2", "labels": ready},
        ]

        selected = foreman.select_issue(issues, smactorio_policy.default_policy())

        self.assertIsNotNone(selected)
        self.assertEqual(2, selected["number"])

    def test_skips_claimed_done_blocked_and_high_risk_issues(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        ready = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]
        issues = [
            {"number": 1, "title": "claimed", "state": "OPEN", "url": "u1", "labels": [*ready, {"name": "smactorio:claimed"}]},
            {"number": 2, "title": "done", "state": "OPEN", "url": "u2", "labels": [*ready, {"name": "smactorio:done"}]},
            {"number": 3, "title": "blocked", "state": "OPEN", "url": "u3", "labels": [*ready, {"name": "smactorio:blocked"}]},
            {"number": 4, "title": "high", "state": "OPEN", "url": "u4", "labels": [*ready, {"name": "risk:high"}]},
            {"number": 5, "title": "eligible", "state": "OPEN", "url": "u5", "labels": ready},
        ]

        selected = foreman.select_issue(issues, smactorio_policy.default_policy())

        self.assertEqual(5, selected["number"])

    def test_unlabeled_or_forbidden_title_issues_are_not_eligible(self) -> None:
        import smactorio_policy

        ready = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]
        self.assertFalse(smactorio_policy.issue_is_eligible({"number": 9, "title": "unlabeled", "state": "OPEN", "labels": []}))
        self.assertFalse(smactorio_policy.issue_is_eligible({"number": 10, "title": "disable branch protection", "state": "OPEN", "labels": ready}))
        self.assertFalse(smactorio_policy.issue_is_eligible({"number": 11, "title": "rotate secret for the runtime", "state": "OPEN", "body": "plain body", "labels": ready}))

    def test_ops_issue_body_can_document_stop_conditions_without_being_blocked(self) -> None:
        import smactorio_policy

        labels = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}, {"name": "type:ops"}]
        body = """
        Acceptance criteria:
        - keep the service low-risk and repairable
        - stop instead of proceeding if work would require 2FA, billing/payment,
          admin override, or production credential access
        """

        self.assertTrue(smactorio_policy.issue_is_eligible({"number": 20, "title": "fix repairable verification", "state": "OPEN", "body": body, "labels": labels}))

    def test_recover_retryable_blocked_issues_clears_non_terminal_blocked_label(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        policy = smactorio_policy.default_policy()
        ready = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]
        issues = [
            {"number": 45, "title": "retry me", "state": "OPEN", "url": "u45", "labels": [*ready, {"name": policy.blocked_label}]},
            {"number": 46, "title": "true blocked", "state": "OPEN", "url": "u46", "labels": [*ready, {"name": policy.blocked_label}, {"name": policy.needs_attention_label}]},
            {"number": 47, "title": "terminal label drift", "state": "OPEN", "url": "u47", "labels": [*ready, {"name": policy.blocked_label}], "terminal": True},
        ]
        commands: list[list[str]] = []
        comments: list[str] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "issue", "comment"]:
                body_file = Path(argv[argv.index("--body-file") + 1])
                comments.append(body_file.read_text(encoding="utf-8"))
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:3] == ["gh", "issue", "edit"]:
                return subprocess.CompletedProcess(argv, 0, "", "")
            raise AssertionError(argv)

        recovered = foreman.recover_retryable_blocked_issues(
            "owner/repo",
            issues,
            policy=policy,
            command_runner=fake_run,
            terminal_issue_predicate=lambda issue: bool(issue.get("terminal")),
        )

        self.assertTrue(recovered)
        edits = [cmd for cmd in commands if cmd[:3] == ["gh", "issue", "edit"]]
        self.assertEqual(1, len(edits), edits)
        self.assertIn("45", edits[0])
        self.assertIn("--remove-label", edits[0])
        self.assertIn(policy.blocked_label, edits[0])
        self.assertTrue(any("retryable blocked label" in comment.lower() for comment in comments))

    def test_retryable_blocked_recovery_skips_when_attempt_ledger_unreadable(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        policy = smactorio_policy.default_policy()
        issue = {
            "number": 48,
            "title": "ledger unknown",
            "state": "OPEN",
            "url": "u48",
            "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}, {"name": policy.blocked_label}],
        }
        commands: list[list[str]] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch.object(foreman.runtime_state, "init_db", side_effect=OSError("permission denied")):
            recovered = foreman.recover_retryable_blocked_issues(
                "owner/repo",
                [issue],
                policy=policy,
                command_runner=fake_run,
                terminal_issue_predicate=lambda candidate: foreman.issue_has_terminal_retry_exhaustion(
                    Path("/unreadable/state.sqlite"),
                    repo="owner/repo",
                    issue=candidate,
                    base_sha="base123",
                    policy=policy,
                ),
            )

        self.assertFalse(recovered)
        self.assertEqual([], commands)

    def test_no_work_reports_why_each_visible_issue_was_skipped(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        commands: list[list[str]] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "issue", "list"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps([
                    {"number": 1, "title": "missing risk label", "state": "OPEN", "url": "https://github.test/1", "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}]},
                    {"number": 2, "title": "disable branch protection", "state": "OPEN", "url": "https://github.test/2", "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]},
                ]), "")
            raise AssertionError(f"unexpected command: {argv}")

        result = foreman.plan_once(
            repo="leonbreukelman/rtx3070-workshop-ops",
            dry_run=True,
            command_runner=fake_run,
            policy=smactorio_policy.default_policy(),
        )

        self.assertEqual("no_work", result["status"])
        self.assertEqual(2, result["issue_count"])
        skipped = result["skipped_issues"]
        self.assertEqual(2, len(skipped))
        self.assertEqual(1, skipped[0]["number"])
        self.assertIn("missing required labels", skipped[0]["reasons"][0])
        self.assertEqual(2, skipped[1]["number"])
        self.assertIn("forbidden title fragment", skipped[1]["reasons"][0])

    def test_docs_issues_can_document_stop_conditions_without_being_blocked(self) -> None:
        import smactorio_policy

        labels = [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}, {"name": "type:docs"}]
        body = """
        Security and Secrets
        - stop conditions:
          - production credentials
          - 2FA
          - billing/payment
          - admin override
          - destructive actions
        """
        self.assertTrue(smactorio_policy.issue_is_eligible({"number": 12, "title": "docs: create wiki", "state": "OPEN", "body": body, "labels": labels}))
        self.assertFalse(smactorio_policy.issue_is_eligible({"number": 13, "title": "docs: disable branch protection", "state": "OPEN", "body": body, "labels": labels}))

    def test_branch_name_is_issue_scoped_and_shell_safe(self) -> None:
        import smactorio_issue_foreman as foreman

        branch = foreman.branch_name_for_issue(
            {"number": 7, "title": "Fix $(rm -rf /) `evil` && ship!!!", "labels": []},
            run_id="abc12345",
        )

        self.assertEqual("smactorio/issue-7-fix-rm-rf-evil-ship-abc12345", branch)
        long_branch = foreman.branch_name_for_issue({"number": 8, "title": "work", "labels": []}, run_id="20260517T030710-18b03c59cab3d4c2")
        self.assertTrue(long_branch.endswith("20260517t030710-18b03c59"), long_branch)
        self.assertNotIn("$", branch)
        self.assertNotIn("`", branch)
        self.assertNotIn("&&", branch)

    def test_dry_run_loads_issues_and_performs_no_github_writes(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        commands: list[list[str]] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "issue", "list"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps([
                    {"number": 1, "title": "Do work", "state": "OPEN", "url": "https://github.test/1", "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]}
                ]), "")
            raise AssertionError(f"unexpected command: {argv}")

        result = foreman.plan_once(
            repo="leonbreukelman/rtx3070-workshop-ops",
            dry_run=True,
            command_runner=fake_run,
            policy=smactorio_policy.default_policy(),
        )

        self.assertEqual("dry_run", result["status"])
        self.assertEqual(1, result["selected_issue_number"])
        write_verbs = [(cmd[1], cmd[2]) for cmd in commands if len(cmd) > 2 and cmd[0] == "gh" and cmd[1] in {"issue", "pr"} and cmd[2] not in {"list", "view"}]
        self.assertEqual([], write_verbs)

    def test_pr_checks_must_be_current_clean_and_include_guardrails(self) -> None:
        import smactorio_issue_foreman as foreman

        ok, reason = foreman.pr_checks_are_green(
            {
                "isDraft": False,
                "headRefOid": "abc",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"name": "signal-hub-guardrails", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            },
            expected_head="abc",
        )
        self.assertTrue(ok, reason)

        stale, stale_reason = foreman.pr_checks_are_green(
            {
                "isDraft": False,
                "headRefOid": "new",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"name": "signal-hub-guardrails", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            },
            expected_head="old",
        )
        self.assertFalse(stale)
        self.assertIn("head changed", stale_reason)

        missing, missing_reason = foreman.pr_checks_are_green(
            {"isDraft": False, "headRefOid": "abc", "mergeStateStatus": "UNKNOWN", "statusCheckRollup": []},
            expected_head="abc",
        )
        self.assertFalse(missing)
        self.assertIn("no status checks", missing_reason)

        skipped, skipped_reason = foreman.pr_checks_are_green(
            {
                "isDraft": False,
                "headRefOid": "abc",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"name": "signal-hub-guardrails", "status": "COMPLETED", "conclusion": "SKIPPED"}],
            },
            expected_head="abc",
        )
        self.assertFalse(skipped)
        self.assertIn("not successful", skipped_reason)

        substring_only, substring_reason = foreman.pr_checks_are_green(
            {
                "isDraft": False,
                "headRefOid": "abc",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"name": "other-signal-hub-check", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            },
            expected_head="abc",
        )
        self.assertFalse(substring_only)
        self.assertIn("required workflow", substring_reason)

    def test_wait_for_pr_checks_polls_until_github_populates_rollup(self) -> None:
        import smactorio_issue_foreman as foreman

        views = [
            {"isDraft": False, "headRefOid": "abc", "mergeStateStatus": "BLOCKED", "statusCheckRollup": []},
            {
                "isDraft": False,
                "headRefOid": "abc",
                "mergeStateStatus": "CLEAN",
                "statusCheckRollup": [{"name": "signal-hub-guardrails", "status": "COMPLETED", "conclusion": "SUCCESS"}],
            },
        ]
        commands: list[list[str]] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "pr", "view"]:
                payload = views.pop(0)
                return subprocess.CompletedProcess(argv, 0, json.dumps(payload), "")
            raise AssertionError(argv)

        foreman.wait_for_pr_checks("owner/repo", 1, command_runner=fake_run, expected_head="abc", timeout_seconds=2, poll_interval_seconds=0)

        self.assertEqual(2, len([cmd for cmd in commands if cmd[:3] == ["gh", "pr", "view"]]))
        self.assertEqual([], views)

    def test_merge_uses_match_head_commit(self) -> None:
        import smactorio_issue_foreman as foreman

        commands: list[list[str]] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "pr", "merge"]:
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:3] == ["gh", "pr", "view"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps({"url": "https://github.test/pr/1", "state": "MERGED", "mergeCommit": {"oid": "abc"}}), "")
            raise AssertionError(argv)

        foreman.merge_pr("owner/repo", 1, command_runner=fake_run, expected_head="expected-sha")

        merge_cmd = commands[0]
        self.assertIn("--match-head-commit", merge_cmd)
        self.assertIn("expected-sha", merge_cmd)

    def test_create_pr_body_uses_parseable_closing_keyword(self) -> None:
        import smactorio_issue_foreman as foreman

        bodies: list[str] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            if argv[:3] == ["gh", "pr", "create"]:
                body_file = Path(argv[argv.index("--body-file") + 1])
                bodies.append(body_file.read_text(encoding="utf-8"))
                return subprocess.CompletedProcess(argv, 0, "https://github.test/owner/repo/pull/7\n", "")
            if argv[:3] == ["gh", "pr", "view"]:
                return subprocess.CompletedProcess(argv, 0, json.dumps({"number": 7, "url": "https://github.test/owner/repo/pull/7"}), "")
            raise AssertionError(argv)

        foreman.create_pr(
            "owner/repo",
            {"number": 12, "title": "docs: create wiki", "url": "https://github.test/owner/repo/issues/12"},
            branch="smactorio/issue-12-test",
            base="main",
            body_extra="- Local checks passed.\n- Independent review passed.",
            command_runner=fake_run,
        )

        self.assertEqual(1, len(bodies))
        self.assertIn("\nCloses #12\n", f"\n{bodies[0]}\n")
        self.assertNotIn("\n        Closes #12", bodies[0])

    def test_complete_issue_comments_labels_and_closes_issue(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        commands: list[list[str]] = []
        comments: list[str] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            commands.append(argv)
            if argv[:3] == ["gh", "issue", "comment"]:
                body_file = Path(argv[argv.index("--body-file") + 1])
                comments.append(body_file.read_text(encoding="utf-8"))
                return subprocess.CompletedProcess(argv, 0, "", "")
            if argv[:3] in (["gh", "issue", "edit"], ["gh", "issue", "close"]):
                return subprocess.CompletedProcess(argv, 0, "", "")
            raise AssertionError(argv)

        foreman.complete_issue(
            "owner/repo",
            12,
            pr_url="https://github.test/owner/repo/pull/7",
            merge_commit="abc123",
            artifact_rel=Path("signal-hub/docs/verification/issue-12.md"),
            rid="run123",
            policy=smactorio_policy.default_policy(),
            command_runner=fake_run,
        )

        self.assertIn("SmactorIO completed this issue.", comments[0])
        self.assertIn("Merge commit: `abc123`", comments[0])
        self.assertTrue(any(cmd[:3] == ["gh", "issue", "edit"] and "--add-label" in cmd and "smactorio:done" in cmd for cmd in commands))
        self.assertTrue(any(cmd[:3] == ["gh", "issue", "close"] for cmd in commands))

    def _worker_outcome_stdout(self, outcome: str = "ALREADY_SATISFIED", *, issue_number: int = 12, extra: dict | None = None) -> str:
        payload = {
            "schema_version": 1,
            "outcome": outcome,
            "issue_number": issue_number,
            "run_id": "run123",
            "acceptance_criteria": [{"criterion": "docs exist", "status": "satisfied", "evidence": "verified existing file"}],
            "commands": [{"command": "signal-hub/scripts/run_tests.sh tests/test_docs.py", "exit_code": 0, "summary": "passed"}],
            "files_inspected": ["signal-hub/docs/runbook.md"],
            "base_sha": "abc123",
            "diff_status": "clean",
            "commit_count": 0,
        }
        if extra:
            payload.update(extra)
        return "\n".join(
            [
                "Verified base checkout.",
                "```smactorio-outcome-json",
                json.dumps(payload, sort_keys=True),
                "```",
                f"SMACTORIO_OUTCOME_JSON_V1: {outcome}",
                "",
            ]
        )

    def test_worker_prompt_uses_structured_no_commit_already_satisfied_contract(self) -> None:
        import smactorio_issue_foreman as foreman

        prompt = foreman.worker_prompt(
            {"number": 12, "title": "docs: already done", "body": "Verify the docs exist.", "url": "https://github.test/12", "labels": []},
            repo="owner/repo",
            branch="smactorio/issue-12-test",
        )

        self.assertIn("```smactorio-outcome-json", prompt)
        self.assertIn("SMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED", prompt)
        self.assertIn("do not create commits", prompt.lower())
        self.assertIn("do not emit smactorio-outcome-json", prompt.lower())
        self.assertIn("normal implementation", prompt.lower())
        self.assertNotIn("add a small verification artifact", prompt)

    def test_worker_outcome_wire_format_accepts_single_json_block_and_final_sentinel(self) -> None:
        import smactorio_issue_foreman as foreman

        result = subprocess.CompletedProcess(["worker"], 0, self._worker_outcome_stdout(issue_number=12), "")

        outcome = foreman.parse_worker_outcome(result, issue_number=12)

        self.assertEqual("ALREADY_SATISFIED", outcome["outcome"])
        self.assertEqual("clean", outcome["diff_status"])
        self.assertTrue(foreman.worker_reported_already_satisfied(result, issue_number=12))

    def test_worker_outcome_wire_format_rejects_marker_only_and_malformed_output(self) -> None:
        import smactorio_issue_foreman as foreman

        malformed_results = [
            subprocess.CompletedProcess(["worker"], 0, "Verified.\nSMACTORIO_OUTCOME: ALREADY_SATISFIED\n", ""),
            subprocess.CompletedProcess(["worker"], 0, "```smactorio-outcome-json\n{}\n```\n", ""),
            subprocess.CompletedProcess(["worker"], 0, "SMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED\n", ""),
            subprocess.CompletedProcess(["worker"], 0, self._worker_outcome_stdout(issue_number=12) + self._worker_outcome_stdout(issue_number=12), ""),
            subprocess.CompletedProcess(["worker"], 1, self._worker_outcome_stdout(issue_number=12), ""),
            subprocess.CompletedProcess(["worker"], 0, self._worker_outcome_stdout(issue_number=99), ""),
            subprocess.CompletedProcess(["worker"], 0, self._worker_outcome_stdout(issue_number=12, extra={"outcome": "TRUE_BLOCKED"}), ""),
            subprocess.CompletedProcess(["worker"], 0, self._worker_outcome_stdout("TRUE_BLOCKED", issue_number=12), ""),
        ]
        for result in malformed_results:
            with self.subTest(stdout=result.stdout, returncode=result.returncode):
                with self.assertRaises(foreman.SmactorioError):
                    foreman.parse_worker_outcome(result, issue_number=12)
                self.assertFalse(foreman.worker_reported_already_satisfied(result, issue_number=12))

    def test_material_commit_path_ignores_stray_structured_outcome_sentinel(self) -> None:
        import smactorio_issue_foreman as foreman

        result = subprocess.CompletedProcess(["worker"], 0, "Implemented with a commit.\nSMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED\n", "")

        self.assertFalse(foreman.worker_terminal_outcome_should_be_parsed(result, material_paths=["signal-hub/docs/operator.md"]))
        self.assertTrue(foreman.worker_terminal_outcome_should_be_parsed(result, material_paths=None))

    def test_non_material_commit_with_structured_outcome_is_contract_violation(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub" / "docs" / "verification").mkdir(parents=True)
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            artifact = checkout / "signal-hub" / "docs" / "verification" / "issue-1.md"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("evidence only\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", str(artifact.relative_to(checkout))], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "docs: add evidence"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            result = subprocess.CompletedProcess(["worker"], 0, "Implemented with a commit.\nSMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED\n", "")

            with self.assertRaisesRegex(foreman.SmactorioError, "structured outcome contract violation"):
                foreman.material_paths_or_contract_violation(
                    checkout,
                    base="main",
                    policy=smactorio_policy.default_policy(),
                    worker_result=result,
                )

    def test_issue_context_fingerprint_ignores_smactorio_operational_label_churn(self) -> None:
        import smactorio_issue_foreman as foreman

        base_issue = {
            "number": 87,
            "title": "docs: stabilize retries",
            "state": "OPEN",
            "body": "Fix the retry loop.",
            "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
            "updatedAt": "2026-05-19T00:00:00Z",
        }
        operationally_touched_issue = {
            **base_issue,
            "labels": base_issue["labels"]
            + [{"name": "smactorio:claimed"}, {"name": "smactorio:blocked"}, {"name": "smactorio:needs-attention"}],
            "updatedAt": "2026-05-19T00:10:00Z",
        }
        substantively_changed_issue = {
            **base_issue,
            "labels": base_issue["labels"] + [{"name": "component:docs"}],
        }

        baseline = foreman.issue_context_fingerprint(base_issue, base_sha="base123")

        self.assertEqual(baseline, foreman.issue_context_fingerprint(operationally_touched_issue, base_sha="base123"))
        self.assertNotEqual(baseline, foreman.issue_context_fingerprint(substantively_changed_issue, base_sha="base123"))
        self.assertNotEqual(baseline, foreman.issue_context_fingerprint(base_issue, base_sha="base456"))

    def test_run_once_already_satisfied_marker_completes_without_pr_or_artifact_commit(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            issue = {
                "number": 24,
                "title": "docs: already present",
                "state": "OPEN",
                "url": "https://github.test/24",
                "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
                "body": "Ensure the existing runbook is present.",
            }
            commands: list[list[str]] = []
            comments: list[str] = []

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(argv)
                if argv == ["worker"]:
                    return subprocess.CompletedProcess(argv, 0, self._worker_outcome_stdout(issue_number=24), "")
                if argv[:3] == ["gh", "issue", "comment"]:
                    body_file = Path(argv[argv.index("--body-file") + 1])
                    comments.append(body_file.read_text(encoding="utf-8"))
                    return subprocess.CompletedProcess(argv, 0, "", "")
                if argv[:3] in (["gh", "label", "create"], ["gh", "issue", "edit"], ["gh", "issue", "close"]):
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError(argv)

            with mock.patch.object(foreman, "enforce_runtime_environment", return_value=None), \
                mock.patch.object(foreman.repo_guard, "assert_clean"), \
                mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]), \
                mock.patch.object(foreman.repo_guard, "fetch"), \
                mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"), \
                mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"), \
                mock.patch.object(foreman.repo_guard, "delete_local_branch"), \
                mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"), \
                mock.patch.object(foreman.repo_guard, "head_differs_from", return_value=False), \
                mock.patch.object(foreman, "run_trusted_preflight"), \
                mock.patch.object(foreman, "load_issues", return_value=[issue]), \
                mock.patch.object(foreman, "recover_stale_claims", return_value=False), \
                mock.patch.object(foreman, "load_issue_detail", return_value=issue), \
                mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False), \
                mock.patch.object(foreman, "create_worker_checkout"), \
                mock.patch.object(foreman, "remove_worker_checkout"), \
                mock.patch.object(foreman, "lock_down_worker_git_metadata"), \
                mock.patch.object(foreman, "discard_worker_generated_side_effects", return_value=""), \
                mock.patch.object(foreman, "sandbox_worker_command", side_effect=lambda command, worktree, runtime_dir, env: (command, env)):
                result = foreman.run_once(
                    repo="owner/repo",
                    repo_root=repo,
                    base="main",
                    state_db=db,
                    dry_run=False,
                    worker_command=["worker"],
                    command_runner=fake_run,
                    policy=smactorio_policy.default_policy(),
                )

        self.assertEqual("already_satisfied", result["status"])
        self.assertEqual(24, result["issue_number"])
        self.assertTrue(any("already satisfied" in comment.lower() for comment in comments))
        self.assertTrue(any(cmd[:3] == ["gh", "issue", "edit"] and "--add-label" in cmd and "smactorio:done" in cmd for cmd in commands))
        self.assertTrue(any(cmd[:3] == ["gh", "issue", "close"] for cmd in commands))
        self.assertFalse(any(cmd[:3] == ["gh", "pr", "create"] for cmd in commands), commands)

    def test_run_once_already_satisfied_rejects_generated_side_effects(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            issue = {
                "number": 25,
                "title": "docs: already present but dirty",
                "state": "OPEN",
                "url": "https://github.test/25",
                "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
                "body": "Ensure the existing runbook is present.",
            }

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                if argv == ["worker"]:
                    return subprocess.CompletedProcess(argv, 0, self._worker_outcome_stdout(issue_number=25), "")
                if argv[:3] in (["gh", "label", "create"], ["gh", "issue", "edit"], ["gh", "issue", "comment"]):
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError(argv)

            with contextlib.ExitStack() as stack:
                stack.enter_context(mock.patch.object(foreman, "enforce_runtime_environment", return_value=None))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "assert_clean"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "fetch"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "delete_local_branch"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"))
                stack.enter_context(mock.patch.object(foreman.repo_guard, "head_differs_from", return_value=False))
                stack.enter_context(mock.patch.object(foreman, "run_trusted_preflight"))
                stack.enter_context(mock.patch.object(foreman, "load_issues", return_value=[issue]))
                stack.enter_context(mock.patch.object(foreman, "recover_stale_claims", return_value=False))
                stack.enter_context(mock.patch.object(foreman, "load_issue_detail", return_value=issue))
                stack.enter_context(mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False))
                stack.enter_context(mock.patch.object(foreman, "create_worker_checkout"))
                stack.enter_context(mock.patch.object(foreman, "remove_worker_checkout"))
                stack.enter_context(mock.patch.object(foreman, "lock_down_worker_git_metadata"))
                stack.enter_context(mock.patch.object(foreman, "discard_worker_generated_side_effects", return_value=" M signal-hub/public/index.html\n"))
                stack.enter_context(mock.patch.object(foreman, "sandbox_worker_command", side_effect=lambda command, worktree, runtime_dir, env: (command, env)))
                with self.assertRaisesRegex(foreman.SmactorioError, "generated side effects"):
                    foreman.run_once(
                        repo="owner/repo",
                        repo_root=repo,
                        base="main",
                        state_db=db,
                        dry_run=False,
                        worker_command=["worker"],
                        command_runner=fake_run,
                        policy=smactorio_policy.default_policy(),
                    )

    def test_run_once_worker_failure_records_durable_attempt_before_blocking(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy
        import smactorio_runtime_state as runtime_state

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            issue = {
                "number": 41,
                "title": "docs: fix small typo",
                "state": "OPEN",
                "url": "https://github.test/41",
                "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
                "body": "Fix a typo.",
                "updatedAt": "2026-05-19T00:00:00Z",
            }

            commands: list[list[str]] = []
            failure_text = "worker failed (2):\nSTDOUT:\n\nSTDERR:\nverification failed: scripts/run_tests.sh missing"
            conn = runtime_state.init_db(db)
            for run_id in ("previous1", "previous2"):
                runtime_state.record_issue_attempt(
                    conn,
                    repo="owner/repo",
                    issue_number=41,
                    run_id=run_id,
                    durable_state="blocked",
                    failure_class="worker_failed",
                    failure_signature=foreman.scoped_failure_signature(issue, base_sha="base123", message=failure_text),
                    evidence_ref=f"smactorio-run:{run_id}",
                )
            conn.close()

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(argv)
                if argv == ["worker"]:
                    return subprocess.CompletedProcess(argv, 2, "", "verification failed: scripts/run_tests.sh missing")
                if argv[:3] == ["gh", "issue", "comment"]:
                    return subprocess.CompletedProcess(argv, 0, "", "")
                if argv[:3] in (["gh", "label", "create"], ["gh", "issue", "edit"]):
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError(argv)

            with mock.patch.object(foreman, "enforce_runtime_environment", return_value=None), \
                mock.patch.object(foreman.repo_guard, "assert_clean"), \
                mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]), \
                mock.patch.object(foreman.repo_guard, "fetch"), \
                mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"), \
                mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"), \
                mock.patch.object(foreman.repo_guard, "delete_local_branch"), \
                mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"), \
                mock.patch.object(foreman, "run_trusted_preflight"), \
                mock.patch.object(foreman, "run_worker_preflight", return_value=""), \
                mock.patch.object(foreman, "load_issues", return_value=[issue]), \
                mock.patch.object(foreman, "recover_stale_claims", return_value=False), \
                mock.patch.object(foreman, "load_issue_detail", return_value=issue), \
                mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False), \
                mock.patch.object(foreman, "create_worker_checkout"), \
                mock.patch.object(foreman, "remove_worker_checkout"), \
                mock.patch.object(foreman, "lock_down_worker_git_metadata"), \
                mock.patch.object(foreman, "sandbox_worker_command", side_effect=lambda command, worktree, runtime_dir, env: (command, env)):
                with self.assertRaisesRegex(foreman.SmactorioError, "worker failed"):
                    foreman.run_once(
                        repo="owner/repo",
                        repo_root=repo,
                        base="main",
                        state_db=db,
                        dry_run=False,
                        worker_command=["worker"],
                        command_runner=fake_run,
                        policy=smactorio_policy.default_policy(),
                    )

            conn = runtime_state.init_db(db)
            attempts = runtime_state.issue_attempts(conn, repo="owner/repo", issue_number=41)

        self.assertEqual(1, len(attempts))
        self.assertEqual("blocked", attempts[0]["durable_state"])
        self.assertEqual("worker_failed", attempts[0]["failure_class"])
        self.assertEqual(3, int(attempts[0]["attempt_count"]))
        self.assertTrue(
            any(
                cmd[:3] == ["gh", "issue", "edit"]
                and "--add-label" in cmd
                and "smactorio:needs-attention" in cmd
                for cmd in commands
            ),
            commands,
        )

    def test_run_once_retry_exhaustion_reaches_terminal_true_blocked_without_reclaiming(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy
        import smactorio_runtime_state as runtime_state

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            policy = smactorio_policy.default_policy()
            issue = {
                "number": 42,
                "title": "docs: retry exhausted",
                "state": "OPEN",
                "url": "https://github.test/42",
                "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
                "body": "Fix docs.",
                "updatedAt": "2026-05-19T00:00:00Z",
            }
            context = foreman.issue_context_fingerprint(issue, base_sha="base123")
            conn = runtime_state.init_db(db)
            for run_id in ("run1", "run2", "run3"):
                runtime_state.record_issue_attempt(
                    conn,
                    repo="owner/repo",
                    issue_number=42,
                    run_id=run_id,
                    durable_state="blocked",
                    failure_class="worker_failed",
                    failure_signature=f"{context}:worker_failed:same",
                    evidence_ref=f"smactorio-run:{run_id}",
                )
            conn.close()
            commands: list[list[str]] = []

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(argv)
                if argv[:3] == ["gh", "issue", "comment"]:
                    return subprocess.CompletedProcess(argv, 0, "", "")
                if argv[:3] in (["gh", "issue", "edit"], ["gh", "label", "create"]):
                    return subprocess.CompletedProcess(argv, 0, "", "")
                raise AssertionError(argv)

            with mock.patch.object(foreman, "enforce_runtime_environment", return_value=None), \
                mock.patch.object(foreman.repo_guard, "assert_clean"), \
                mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]), \
                mock.patch.object(foreman.repo_guard, "fetch"), \
                mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"), \
                mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"), \
                mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"), \
                mock.patch.object(foreman, "run_trusted_preflight"), \
                mock.patch.object(foreman, "load_issues", return_value=[issue]), \
                mock.patch.object(foreman, "recover_stale_claims", return_value=False), \
                mock.patch.object(foreman, "load_issue_detail", return_value=issue), \
                mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False), \
                mock.patch.object(foreman, "create_worker_checkout") as create_checkout:
                result = foreman.run_once(
                    repo="owner/repo",
                    repo_root=repo,
                    base="main",
                    state_db=db,
                    dry_run=False,
                    worker_command=["worker"],
                    command_runner=fake_run,
                    policy=policy,
                )

        self.assertEqual("true_blocked", result["status"])
        self.assertEqual("retry_exhausted", result["reason"])
        create_checkout.assert_not_called()
        self.assertFalse(any(cmd == ["worker"] for cmd in commands), commands)
        self.assertTrue(
            any(
                cmd[:3] == ["gh", "issue", "edit"]
                and "--add-label" in cmd
                and "smactorio:needs-attention" in cmd
                for cmd in commands
            ),
            commands,
        )

    def test_run_once_retry_exhaustion_resets_when_issue_context_changes(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy
        import smactorio_runtime_state as runtime_state

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            policy = smactorio_policy.default_policy()
            old_issue = {
                "number": 43,
                "title": "docs: retry reset",
                "state": "OPEN",
                "url": "https://github.test/43",
                "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}],
                "body": "Fix docs.",
                "updatedAt": "2026-05-19T00:00:00Z",
            }
            current_issue = {**old_issue, "body": "Fix docs after operator narrowed the request.", "updatedAt": "2026-05-19T00:15:00Z"}
            old_context = foreman.issue_context_fingerprint(old_issue, base_sha="base123")
            conn = runtime_state.init_db(db)
            for run_id in ("run1", "run2", "run3"):
                runtime_state.record_issue_attempt(
                    conn,
                    repo="owner/repo",
                    issue_number=43,
                    run_id=run_id,
                    durable_state="blocked",
                    failure_class="worker_failed",
                    failure_signature=f"{old_context}:worker_failed:same",
                    evidence_ref=f"smactorio-run:{run_id}",
                )
            conn.close()

            commands: list[list[str]] = []

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(argv)
                return subprocess.CompletedProcess(argv, 0, "", "")

            with mock.patch.object(foreman, "enforce_runtime_environment", return_value=None), \
                mock.patch.object(foreman.repo_guard, "assert_clean"), \
                mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]), \
                mock.patch.object(foreman.repo_guard, "fetch"), \
                mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"), \
                mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"), \
                mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"), \
                mock.patch.object(foreman, "run_trusted_preflight"), \
                mock.patch.object(foreman, "load_issues", return_value=[current_issue]), \
                mock.patch.object(foreman, "recover_stale_claims", return_value=False), \
                mock.patch.object(foreman, "load_issue_detail", return_value=current_issue), \
                mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False), \
                mock.patch.object(foreman, "create_worker_checkout") as create_checkout, \
                mock.patch.object(foreman, "run_worker_preflight", return_value="No worker backend configured"):
                result = foreman.run_once(
                    repo="owner/repo",
                    repo_root=repo,
                    base="main",
                    state_db=db,
                    dry_run=False,
                    worker_command=None,
                    command_runner=fake_run,
                    policy=policy,
                )

        self.assertEqual("no_work", result["status"])
        self.assertEqual("worker_preflight_failed", result["reason"])
        create_checkout.assert_called_once()
        self.assertFalse(any(cmd[:3] == ["gh", "issue", "edit"] and "smactorio:needs-attention" in cmd for cmd in commands), commands)

    def test_protected_runtime_paths_and_low_risk_repair_scope_are_pinned(self) -> None:
        import smactorio_issue_foreman as foreman

        protected = set(foreman.PROTECTED_SMACTORIO_RUNTIME_PATHS)
        self.assertIn("signal-hub/scripts/smactorio_issue_foreman.py", protected)
        self.assertIn("signal-hub/scripts/project_improvement_processor.py", protected)
        self.assertIn("signal-hub/scripts/smactorio_policy.py", protected)
        self.assertIn("signal-hub/scripts/smactorio_repo_guard.py", protected)
        self.assertIn("signal-hub/tests/test_smactorio_issue_foreman.py", protected)
        self.assertIn("infra/systemd/system/smactorio.timer", protected)
        self.assertFalse(foreman.path_is_allowed_for_repair(".github/workflows/smactorio.yml"))
        for trusted_path in foreman.TRUSTED_PREFLIGHT_FILES:
            self.assertFalse(foreman.path_is_allowed_for_repair(trusted_path), trusted_path)
        self.assertFalse(foreman.path_is_allowed_for_repair("../signal-hub/docs/escape.md"))
        self.assertFalse(foreman.path_is_allowed_for_repair("signal-hub/tests/test_smactorio_issue_foreman.py"))
        self.assertTrue(foreman.path_is_allowed_for_repair("signal-hub/docs/runbook.md"))

    def test_issue_comment_redacts_secret_like_values_and_absolute_paths(self) -> None:
        import smactorio_issue_foreman as foreman

        comments: list[str] = []

        def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
            self.assertEqual(["gh", "issue", "comment"], argv[:3])
            body_file = Path(argv[argv.index("--body-file") + 1])
            comments.append(body_file.read_text(encoding="utf-8"))
            return subprocess.CompletedProcess(argv, 0, "", "")

        token_value = "gh" + "p_" + "A" * 36
        api_value = "sk-" + "B" * 24
        secret_value = "quoted-secret-value"
        bearer_value = "header-secret-value-12345"
        foreman.issue_comment(
            "owner/repo",
            99,
            f"Failure in /home/leonb/projects/rtx3070-workshop-ops with GH_TOKEN={token_value} API_KEY: \"{api_value}\" SECRET='{secret_value}' Authorization: Bearer {bearer_value}",
            command_runner=fake_run,
        )

        self.assertEqual(1, len(comments))
        self.assertIn("GH_TOKEN=[REDACTED]", comments[0])
        self.assertIn("API_KEY=[REDACTED]", comments[0])
        self.assertIn("SECRET=[REDACTED]", comments[0])
        self.assertIn("Authorization: Bearer [REDACTED]", comments[0])
        for unsafe in (token_value, api_value, secret_value, bearer_value):
            self.assertNotIn(unsafe, comments[0])
        self.assertNotIn("/home/leonb", comments[0])
        self.assertIn("[REDACTED_PATH]", comments[0])

    def test_redaction_caps_evidence_and_redacts_common_absolute_paths(self) -> None:
        import smactorio_issue_foreman as foreman

        raw = (
            "paths /root/.config/tool /workspace/build/log /mnt/shared/file /opt/app/bin /Users/leon/tmp "
            + "x" * 200
        )

        redacted = foreman.redact_operational_evidence(raw, max_chars=80)

        self.assertLessEqual(len(redacted), 92)
        self.assertIn("[TRUNCATED]", redacted)
        for unsafe in ("/root", "/workspace", "/mnt", "/opt", "/Users"):
            self.assertNotIn(unsafe, redacted)
        self.assertIn("[REDACTED_PATH]", redacted)

    def test_attempt_ledger_persists_retry_count_across_reopen(self) -> None:
        import smactorio_runtime_state as runtime_state

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "state.sqlite"
            conn = runtime_state.init_db(db)
            runtime_state.record_issue_attempt(
                conn,
                repo="owner/repo",
                issue_number=37,
                run_id="run1",
                durable_state="claimed",
                failure_class="worker_revision_needed",
                failure_signature="issue37-run-tests-wrapper",
                base_sha="base1",
                head_sha="head1",
                evidence_ref="local://evidence",
            )
            conn.close()

            reopened = runtime_state.init_db(db)
            runtime_state.record_issue_attempt(
                reopened,
                repo="owner/repo",
                issue_number=37,
                run_id="run2",
                durable_state="claimed",
                failure_class="worker_revision_needed",
                failure_signature="issue37-run-tests-wrapper",
                base_sha="base1",
                head_sha="head1",
                evidence_ref="local://evidence2",
            )
            attempts = runtime_state.issue_attempts(reopened, repo="owner/repo", issue_number=37)

        self.assertEqual(1, len(attempts))
        self.assertEqual(2, attempts[0]["attempt_count"])
        self.assertEqual("run2", attempts[0]["run_id"])

    def test_trusted_preflight_fails_before_worker_when_guardrail_scripts_are_missing(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (repo / "signal-hub").mkdir()
            (repo / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            with self.assertRaisesRegex(foreman.SmactorioError, "preflight missing trusted files"):
                foreman.run_trusted_preflight(repo, base="main", policy=smactorio_policy.default_policy())

    def test_worker_environment_scrubs_github_and_ssh_credentials(self) -> None:
        import smactorio_issue_foreman as foreman

        env = foreman.sanitized_worker_env(
            base_env={
                "PATH": "/usr/bin",
                "GH_TOKEN": "secret",
                "GITHUB_TOKEN": "secret",
                "SSH_AUTH_SOCK": "/tmp/agent.sock",
                "AWS_SECRET_ACCESS_KEY": "secret",
            },
            worker_env={"SMACTORIO_ISSUE_NUMBER": "1"},
        )

        self.assertEqual("/usr/bin", env["PATH"])
        self.assertEqual("1", env["SMACTORIO_ISSUE_NUMBER"])
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)
        self.assertNotIn("SSH_AUTH_SOCK", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)

    def test_worker_command_must_be_argv_not_shell_string(self) -> None:
        import smactorio_issue_foreman as foreman

        with self.assertRaises(TypeError):
            foreman.normalize_worker_command("echo unsafe && rm -rf /")  # type: ignore[arg-type]

        self.assertEqual(["python3", "worker.py"], foreman.normalize_worker_command(["python3", "worker.py"]))

    def test_worker_diff_check_trailing_whitespace_is_auto_repaired(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            bad_file = checkout / "signal-hub" / "docs" / "bad.md"
            bad_file.parent.mkdir(parents=True, exist_ok=True)
            bad_file.write_text("# Bad   \n\t\ncontent\t\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "signal-hub/docs/bad.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-m", "docs: add bad whitespace"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            before = subprocess.run(["git", "-C", str(checkout), "diff", "--check", "origin/main...HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertNotEqual(0, before.returncode)

            repaired = foreman.repair_worker_diff_check_whitespace(checkout, base="main")

            after = subprocess.run(["git", "-C", str(checkout), "diff", "--check", "origin/main...HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertEqual(0, after.returncode, after.stdout + after.stderr)
            self.assertEqual(["signal-hub/docs/bad.md"], repaired)
            self.assertEqual("# Bad\n\ncontent\n", bad_file.read_text(encoding="utf-8"))
            self.assertEqual("", subprocess.run(["git", "-C", str(checkout), "status", "--porcelain=v1"], check=True, text=True, stdout=subprocess.PIPE).stdout)
            self.assertEqual("docs: add bad whitespace", subprocess.run(["git", "-C", str(checkout), "log", "-1", "--pretty=%s"], check=True, text=True, stdout=subprocess.PIPE).stdout.strip())

    def test_worker_diff_check_repairs_only_allowed_worker_changed_paths(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            disallowed = checkout / "outside.txt"
            disallowed.write_text("outside   \n", encoding="utf-8")
            workflow = checkout / ".github" / "workflows" / "smactorio.yml"
            workflow.parent.mkdir(parents=True, exist_ok=True)
            workflow.write_text("name: smactorio   \n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "outside.txt", ".github/workflows/smactorio.yml"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-m", "docs: add disallowed whitespace"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            repaired = foreman.repair_worker_diff_check_whitespace(checkout, base="main")

            after = subprocess.run(["git", "-C", str(checkout), "diff", "--check", "origin/main...HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertEqual([], repaired)
            self.assertNotEqual(0, after.returncode)
            self.assertEqual("outside   \n", disallowed.read_text(encoding="utf-8"))
            self.assertEqual("name: smactorio   \n", workflow.read_text(encoding="utf-8"))

    def test_worker_diff_check_conflict_markers_are_not_auto_repaired(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            conflict_file = checkout / "signal-hub" / "conflict.md"
            conflict_file.write_text("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "signal-hub/conflict.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-m", "docs: add conflict marker"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            repaired = foreman.repair_worker_diff_check_whitespace(checkout, base="main")

            after = subprocess.run(["git", "-C", str(checkout), "diff", "--check", "origin/main...HEAD"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            self.assertEqual([], repaired)
            self.assertNotEqual(0, after.returncode)
            self.assertIn("leftover conflict marker", after.stdout + after.stderr)
            self.assertEqual("", subprocess.run(["git", "-C", str(checkout), "status", "--porcelain=v1"], check=True, text=True, stdout=subprocess.PIPE).stdout)

    def test_run_verification_discards_successful_test_side_effects(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub" / "tests").mkdir(parents=True)
            (source / "signal-hub" / "docs").mkdir(parents=True)
            (source / ".github" / "workflows").mkdir(parents=True)
            (source / "signal-hub" / "tests" / "test_side_effect.py").write_text(
                "from pathlib import Path\n"
                "import unittest\n"
                "class SideEffectTest(unittest.TestCase):\n"
                "    def test_writes_generated_file(self):\n"
                "        path = Path(__file__).resolve().parents[1] / 'public' / 'generated.html'\n"
                "        path.parent.mkdir(parents=True, exist_ok=True)\n"
                "        path.write_text('<p>generated</p>    ' + chr(10), encoding='utf-8')\n",
                encoding="utf-8",
            )
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            changed = checkout / "signal-hub" / "docs" / "wiki.md"
            changed.parent.mkdir(parents=True, exist_ok=True)
            changed.write_text("wiki\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "signal-hub/docs/wiki.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "commit", "-m", "docs: add wiki"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            outputs = foreman.run_verification(checkout, policy=smactorio_policy.SmactorioPolicy(check_timeout_seconds=60), base="main")

            self.assertEqual("", subprocess.run(["git", "-C", str(checkout), "status", "--porcelain=v1"], check=True, text=True, stdout=subprocess.PIPE).stdout)
            self.assertFalse((checkout / "signal-hub" / "public" / "generated.html").exists())
            self.assertIn("discard verification side effects", "\n".join(outputs))

    def test_run_verification_allows_foreman_artifact_prefix_alongside_conflict_files(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "agent").mkdir(parents=True)
            (source / "agent" / "provider.py").write_text("VALUE = 'base'\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-9-test", base="main")
            (checkout / "agent" / "provider.py").write_text("VALUE = 'resolved'\n", encoding="utf-8")
            artifact = checkout / ".smactorio" / "verification" / "issue-9.md"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("verified\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "agent/provider.py", ".smactorio/verification/issue-9.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "fix: resolve provider conflict"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            policy = smactorio_policy.SmactorioPolicy(
                allowed_change_prefixes=("agent/provider.py",),
                verification_artifact_prefixes=(".smactorio/verification/",),
                verification_test_commands=(),
                verification_test_cwd=".",
                secret_scan_paths=(),
                secret_scan_changed_paths_only=True,
                discard_verification_side_effect_pathspecs=(),
                check_timeout_seconds=60,
            )

            outputs = foreman.run_verification(checkout, policy=policy, base="main")

        self.assertIn("check_path_scope.py", "\n".join(outputs))

    def test_ensure_repo_seed_clone_clones_into_empty_precreated_directory(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repos" / "hermes-agent"
            repo_root.mkdir(parents=True)
            with mock.patch.object(
                foreman.subprocess,
                "run",
                return_value=subprocess.CompletedProcess(["git"], 0, "", ""),
            ) as run:
                foreman.ensure_repo_seed_clone(repo_root, repo="leonbreukelman/hermes-agent", base="main", env={})

        run.assert_called_once()
        self.assertEqual(str(repo_root), run.call_args.args[0][-1])

    def test_ensure_repo_seed_clone_rejects_nonempty_non_repo_directory(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repos" / "hermes-agent"
            repo_root.mkdir(parents=True)
            (repo_root / "README.md").write_text("not cloned\n", encoding="utf-8")
            with self.assertRaisesRegex(foreman.SmactorioError, "not a git repository"):
                foreman.ensure_repo_seed_clone(repo_root, repo="leonbreukelman/hermes-agent", base="main", env={})

    def test_worker_sandbox_wraps_command_and_hides_home_and_github_credentials(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktree"
            runtime = root / "runtime"
            hermes_home = root / "hermes-home"
            worktree.mkdir()
            hermes_home.mkdir()
            env = {
                "PATH": "/usr/bin",
                "HOME": "/home/leonb",
                "HERMES_HOME": str(hermes_home),
                "GH_TOKEN": "secret",
                "GITHUB_TOKEN": "secret",
                "SSH_AUTH_SOCK": "/tmp/agent.sock",
            }

            with mock.patch("shutil.which", return_value="/usr/bin/bwrap"):
                command, sandbox_env = foreman.sandbox_worker_command(["python3", "-c", "print('ok')"], worktree=worktree, runtime_dir=runtime, env=env)

        self.assertIn("bwrap", command[0])
        self.assertIn("--bind", command)
        self.assertIn(str(worktree), command)
        self.assertIn("--unsetenv", command)
        self.assertNotIn("/home/leonb/.ssh", " ".join(command))
        self.assertNotIn("GH_TOKEN", sandbox_env)
        self.assertNotIn("GITHUB_TOKEN", sandbox_env)
        self.assertNotIn("SSH_AUTH_SOCK", sandbox_env)
        self.assertNotEqual("/home/leonb", sandbox_env["HOME"])

    def test_worker_sandbox_binds_local_hermes_wrapper_target_root(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project_root = root / "projects" / "hermes-agent"
            target = project_root / ".venv" / "bin" / "hermes"
            wrapper = root / ".local" / "bin" / "hermes"
            target.parent.mkdir(parents=True)
            wrapper.parent.mkdir(parents=True)
            target.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
            wrapper.write_text(f'#!/usr/bin/env bash\nexec "{target}" "$@"\n', encoding="utf-8")

            args: list[str] = []
            with mock.patch("shutil.which", return_value=str(wrapper)):
                foreman._host_tool_readonly_binds(args)

        self.assertIn(str(project_root), args)

    def test_worker_checkout_is_full_clone_git_works_inside_sandbox(self) -> None:
        import shutil
        import smactorio_issue_foreman as foreman

        if not shutil.which("bwrap"):
            self.skipTest("bubblewrap is required for sandboxed git smoke")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            runtime = root / "runtime"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run([
                "git",
                "-C",
                str(source),
                "-c",
                "user.name=Unit Test",
                "-c",
                "user.email=unit@example.test",
                "commit",
                "-m",
                "seed",
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            command, env = foreman.sandbox_worker_command(["git", "status", "--short"], worktree=checkout, runtime_dir=runtime, env={"PATH": os.environ["PATH"], "HOME": "/home/leonb"})
            result = subprocess.run(command, cwd=checkout, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            source_branch = subprocess.run(["git", "-C", str(source), "branch", "--list", "smactorio/issue-1-test"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            git_dir_is_directory = (checkout / ".git").is_dir()

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout.strip())
        self.assertTrue(git_dir_is_directory)
        self.assertEqual("", source_branch.stdout.strip())

    def test_worker_sandbox_can_start_default_hermes_binary_help(self) -> None:
        import shutil
        import smactorio_issue_foreman as foreman

        hermes = shutil.which("hermes")
        if not hermes or not shutil.which("bwrap"):
            self.skipTest("hermes and bubblewrap are required for this host-specific smoke")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worktree = root / "worktree"
            runtime = root / "runtime"
            hermes_home = root / "hermes-home"
            worktree.mkdir()
            hermes_home.mkdir()
            command, env = foreman.sandbox_worker_command([hermes, "--help"], worktree=worktree, runtime_dir=runtime, env={"PATH": os.environ["PATH"], "HOME": "/home/leonb", "HERMES_HOME": str(hermes_home)})
            result = subprocess.run(command, cwd=worktree, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)

        self.assertEqual(0, result.returncode, result.stderr[-1000:])
        self.assertIn("usage", (result.stdout + result.stderr).lower())

    def test_independent_review_requires_pass_marker_and_clean_checkout(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            runtime = root / "runtime"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            (checkout / "signal-hub" / "reviewed.txt").write_text("done\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", "signal-hub/reviewed.txt"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "feat: test"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            with mock.patch.dict(os.environ, {"SMACTORIO_ALLOW_UNSANDBOXED_WORKER": "1"}, clear=False):
                output = foreman.run_independent_review(
                    checkout,
                    issue={"number": 1, "title": "Review me", "url": "https://github.test/1", "labels": []},
                    repo="owner/repo",
                    branch="smactorio/issue-1-test",
                    runtime_dir=runtime,
                    command_runner=foreman.default_command_runner,
                    policy=smactorio_policy.SmactorioPolicy(review_timeout_seconds=60),
                    reviewer_command=["python3", "-c", "print('SMACTORIO_VERDICT: PASS')"],
                )

        self.assertIn("SMACTORIO_VERDICT: PASS", output)

    def test_worker_git_metadata_lockdown_removes_hooks_and_unsafe_config(self) -> None:
        import smactorio_issue_foreman as foreman

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub").mkdir()
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "signal-hub/README.md"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            hook = checkout / ".git" / "hooks" / "pre-push"
            hook.parent.mkdir(exist_ok=True)
            hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            hook.chmod(0o700)
            subprocess.run(["git", "-C", str(checkout), "config", "core.hooksPath", str(hook.parent)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "config", "url.https://evil.example/.insteadOf", "https://github.com/"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            foreman.lock_down_worker_git_metadata(checkout)
            config = (checkout / ".git" / "config").read_text(encoding="utf-8")

        self.assertFalse(hook.exists())
        self.assertNotIn("hooksPath", config)
        self.assertNotIn("insteadOf", config)
        self.assertIn("SmactorIO", config)

    def test_repo_guard_rejects_dirty_status_and_stash_delta(self) -> None:
        import smactorio_repo_guard as guard

        self.assertTrue(guard.status_is_clean(""))
        self.assertFalse(guard.status_is_clean(" M signal-hub/file.py\n"))
        self.assertFalse(guard.stash_is_unchanged("", "stash@{0}: WIP\n"))
        self.assertTrue(guard.stash_is_unchanged("stash@{0}: old\n", "stash@{0}: old\n"))

    def test_repo_guard_fetch_and_pull_accept_token_env_and_https_remote(self) -> None:
        import smactorio_repo_guard as guard

        calls: list[tuple[list[str], dict[str, str] | None]] = []

        def fake_run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append((argv, kwargs.get("env")))  # type: ignore[arg-type]
            return subprocess.CompletedProcess(argv, 0, "", "")

        with mock.patch("subprocess.run", side_effect=fake_run):
            guard.fetch("/tmp/repo", remote="https://github.com/owner/repo.git", env={"GIT_ASKPASS": "/tmp/askpass"})
            guard.ensure_base_checked_out_and_updated("/tmp/repo", "main", remote="https://github.com/owner/repo.git", env={"GIT_ASKPASS": "/tmp/askpass"})

        self.assertIn(["git", "fetch", "--prune", "https://github.com/owner/repo.git", "+refs/heads/*:refs/remotes/origin/*"], [call[0] for call in calls])
        self.assertIn(["git", "pull", "--ff-only", "https://github.com/owner/repo.git", "main"], [call[0] for call in calls])
        self.assertTrue(all(call_env is None or call_env.get("GIT_ASKPASS") == "/tmp/askpass" for _, call_env in calls))

    def test_runtime_state_lives_outside_repo_and_records_transitions(self) -> None:
        import smactorio_runtime_state as state

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            conn = state.init_db(db)
            try:
                work_id = state.upsert_work_item(
                    conn,
                    work_key="github:owner/repo#1",
                    issue_number=1,
                    issue_url="https://github.test/1",
                    title="Test issue",
                    branch="smactorio/issue-1-test-run",
                    run_id="run",
                )
                state.transition(conn, work_id, None, "claimed", "unit-test")
                rows = conn.execute("SELECT to_state, reason FROM transitions").fetchall()
            finally:
                conn.close()

            self.assertFalse(state.path_is_inside(db, repo))
            self.assertEqual([("claimed", "unit-test")], rows)

    def test_claim_comment_marker_round_trips(self) -> None:
        import smactorio_issue_foreman as foreman

        marker = foreman.claim_marker(run_id="run123", expires_at="2026-05-17T03:00:00Z", branch="smactorio/issue-1-test-run123")
        parsed = foreman.parse_claim_marker(f"Working\n{marker}\n")

        self.assertEqual("run123", parsed["run_id"])
        self.assertEqual("2026-05-17T03:00:00Z", parsed["expires_at"])
        self.assertEqual("smactorio/issue-1-test-run123", parsed["branch"])

    def test_service_files_are_hardened_and_do_not_load_broad_hermes_env(self) -> None:
        service_path = ROOT / "infra" / "systemd" / "system" / "smactorio.service"
        timer_path = ROOT / "infra" / "systemd" / "system" / "smactorio.timer"

        service = service_path.read_text(encoding="utf-8")
        timer = timer_path.read_text(encoding="utf-8")

        self.assertIn("NoNewPrivileges=yes", service)
        self.assertIn("RuntimeMaxSec=7200", service)
        self.assertIn("smactorio_service_preflight.sh", service)
        self.assertIn("maei-orchestrator", (ROOT / "scripts" / "smactorio_service_preflight.sh").read_text(encoding="utf-8"))
        self.assertIn("ProtectHome=read-only", service)
        self.assertIn("InaccessiblePaths=-/home/leonb/.ssh -/home/leonb/.config/gh -/home/leonb/.git-credentials -/home/leonb/.hermes", service)
        self.assertIn("Environment=GH_CONFIG_DIR=/home/leonb/.config/smactorio/gh", service)
        self.assertIn("EnvironmentFile=/home/leonb/.config/smactorio/env", service)
        self.assertNotIn("/home/leonb/.hermes/.env", service)
        self.assertIn("flock", service)
        self.assertIn("OnCalendar=*:0/15", timer)

    def test_retired_hermes_lane_service_files_are_not_shipped(self) -> None:
        self.assertFalse((ROOT / "infra" / "systemd" / "system" / "smactorio-hermes-fork.service").exists())
        self.assertFalse((ROOT / "infra" / "systemd" / "system" / "smactorio-hermes-fork.timer").exists())
        self.assertFalse((ROOT / "infra" / "systemd" / "user" / "hermes-fork-sync-check.service").exists())
        self.assertFalse((ROOT / "infra" / "systemd" / "user" / "hermes-fork-sync-check.timer").exists())


    def test_runtime_environment_rejects_noncanonical_worker_identity(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hermes_home = root / "hermes-home"
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  provider: openai-codex\n", encoding="utf-8")
            hermes = root / "bin" / "hermes"
            hermes.parent.mkdir()
            hermes.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

            errors = foreman.runtime_environment_errors(
                smactorio_policy.default_policy(),
                base_env={
                    "HERMES_HOME": str(hermes_home),
                    "SMACTORIO_WORKER_HERMES_HOME": str(hermes_home),
                },
                hostname="4090",
                hermes_path=str(hermes),
            )

        joined = "\n".join(errors)
        self.assertIn("required host", joined)
        self.assertIn("missing runtime attestation", joined)
        self.assertIn("outside allowed roots", joined)
        self.assertIn("openai-codex", joined)

    def test_runtime_environment_accepts_attested_rtx3070_xai_worker(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "projects" / "hermes-agent"
            hermes_home = root / "hermes-home"
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  provider: xai\n", encoding="utf-8")
            hermes = project / ".venv" / "bin" / "hermes"
            hermes.parent.mkdir(parents=True)
            hermes.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            policy = smactorio_policy.SmactorioPolicy(allowed_hermes_roots=(str(project) + "/",))

            errors = foreman.runtime_environment_errors(
                policy,
                base_env={
                    "HERMES_HOME": str(hermes_home),
                    "SMACTORIO_WORKER_HERMES_HOME": str(hermes_home),
                    "SMACTORIO_RUNTIME_ATTEST": "rtx3070-smactorio-systemd",
                },
                hostname="rtx3070",
                hermes_path=str(hermes),
            )

        self.assertEqual([], errors)

    def test_runtime_environment_accepts_local_bin_wrapper_when_exec_target_is_allowed(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "hermes"
            hermes_home = root / "hermes-home"
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  provider: xai\n", encoding="utf-8")
            target = project / "venv" / "bin" / "hermes"
            target.parent.mkdir(parents=True)
            target.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            wrapper = root / ".local" / "bin" / "hermes"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text(f"#!/usr/bin/env bash\nexec \"{target}\" \"$@\"\n", encoding="utf-8")
            policy = smactorio_policy.SmactorioPolicy(allowed_hermes_roots=(str(project) + "/",))

            errors = foreman.runtime_environment_errors(
                policy,
                base_env={
                    "HERMES_HOME": str(hermes_home),
                    "SMACTORIO_WORKER_HERMES_HOME": str(hermes_home),
                    "SMACTORIO_RUNTIME_ATTEST": "rtx3070-smactorio-systemd",
                },
                hostname="rtx3070",
                hermes_path=str(wrapper),
            )

        self.assertEqual([], errors)

    def test_runtime_environment_rejects_local_bin_wrapper_with_unrelated_target(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "hermes"
            hermes_home = root / "hermes-home"
            hermes_home.mkdir()
            (hermes_home / "config.yaml").write_text("model:\n  provider: xai\n", encoding="utf-8")
            unrelated = root / "bin" / "hermes"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
            wrapper = root / ".local" / "bin" / "hermes"
            wrapper.parent.mkdir(parents=True)
            wrapper.write_text(f"#!/usr/bin/env bash\nexec \"{unrelated}\" \"$@\"\n", encoding="utf-8")
            policy = smactorio_policy.SmactorioPolicy(allowed_hermes_roots=(str(project) + "/",))

            errors = foreman.runtime_environment_errors(
                policy,
                base_env={
                    "HERMES_HOME": str(hermes_home),
                    "SMACTORIO_WORKER_HERMES_HOME": str(hermes_home),
                    "SMACTORIO_RUNTIME_ATTEST": "rtx3070-smactorio-systemd",
                },
                hostname="rtx3070",
                hermes_path=str(wrapper),
            )

        self.assertIn("outside allowed roots", "\n".join(errors))

    def test_retired_hermes_policy_has_no_change_scope(self) -> None:
        import smactorio_policy

        issue = {
            "body": '<!-- smactorio:hermes-fork-sync {"lane":"hermes-upstream-sync","conflict_files":["agent/provider.py","tests/test_provider.py"]} -->'
        }
        policy = smactorio_policy.policy_for_issue("leonbreukelman/hermes-agent", issue)

        self.assertEqual(frozenset(), policy.eligible_states)
        self.assertEqual((), policy.allowed_change_prefixes)
        self.assertEqual((), policy.verification_artifact_prefixes)

    def test_write_verification_artifact_uses_signal_hub_policy_prefix(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            worktree = Path(tmp)
            policy = smactorio_policy.policy_for_repo("leonbreukelman/rtx3070-workshop-ops")
            rel = foreman.write_verification_artifact(
                worktree,
                issue={"number": 9, "title": "Signal Hub work", "url": "https://example.test/9"},
                pr_url=None,
                checks=["ok"],
                rid="run123",
                policy=policy,
            )

        self.assertTrue(str(rel).startswith("signal-hub/docs/verification/"), rel)

    def test_worker_material_change_rejects_verification_only_commits(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub" / "docs" / "verification").mkdir(parents=True)
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            artifact = checkout / "signal-hub" / "docs" / "verification" / "issue-1.md"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("evidence only\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", str(artifact.relative_to(checkout))], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "docs: add evidence"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            with self.assertRaisesRegex(foreman.SmactorioError, "only SmactorIO verification"):
                foreman.assert_worker_material_change(checkout, base="main", policy=smactorio_policy.default_policy())

    def test_worker_material_change_accepts_real_signal_hub_change(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            checkout = root / "checkout"
            subprocess.run(["git", "init", "-b", "main", str(source)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (source / "signal-hub" / "docs").mkdir(parents=True)
            (source / "signal-hub" / "README.md").write_text("seed\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(source), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            foreman.create_worker_checkout(source, checkout, branch="smactorio/issue-1-test", base="main")
            doc = checkout / "signal-hub" / "docs" / "operator.md"
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text("operator note\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(checkout), "add", str(doc.relative_to(checkout))], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(checkout), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "docs: add operator note"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            self.assertEqual(["signal-hub/docs/operator.md"], foreman.assert_worker_material_change(checkout, base="main", policy=smactorio_policy.default_policy()))



    def test_discards_safe_generated_public_side_effects_from_worker_checkout(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_repo_guard as guard

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            public = repo / "signal-hub" / "public"
            public.mkdir(parents=True)
            tracked = public / "index.html"
            tracked.write_text("stable\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            tracked.write_text("generated drift\n", encoding="utf-8")
            (public / "projects" / "smactorio").mkdir(parents=True)
            (public / "projects" / "smactorio" / "index.html").write_text("new generated page\n", encoding="utf-8")

            discarded = foreman.discard_worker_generated_side_effects(repo)

            self.assertIn("signal-hub/public/index.html", discarded)
            self.assertIn("signal-hub/public/projects/smactorio/index.html", discarded)
            self.assertEqual("stable\n", tracked.read_text(encoding="utf-8"))
            self.assertFalse((public / "projects" / "smactorio" / "index.html").exists())
            guard.assert_clean(repo)

    def test_does_not_discard_unknown_worker_source_changes(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_repo_guard as guard

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (repo / "signal-hub" / "public").mkdir(parents=True)
            (repo / "signal-hub" / "scripts").mkdir(parents=True)
            (repo / "signal-hub" / "public" / "index.html").write_text("stable\n", encoding="utf-8")
            script = repo / "signal-hub" / "scripts" / "important.py"
            script.write_text("print('stable')\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", "seed"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            (repo / "signal-hub" / "public" / "index.html").write_text("generated drift\n", encoding="utf-8")
            script.write_text("print('valuable')\n", encoding="utf-8")

            discarded = foreman.discard_worker_generated_side_effects(repo)

            self.assertEqual("", discarded)
            status = guard.status_porcelain(repo)
            self.assertIn("signal-hub/public/index.html", status)
            self.assertIn("signal-hub/scripts/important.py", status)

    def test_run_once_worker_preflight_failure_does_not_claim_or_block_issue(self) -> None:
        import smactorio_issue_foreman as foreman
        import smactorio_policy

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            (repo / ".git").mkdir()
            db = Path(tmp) / "state" / "smactorio.sqlite"
            commands: list[list[str]] = []
            issue = {"number": 24, "title": "simple docs", "state": "OPEN", "url": "https://github.test/24", "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}], "body": "Do it."}

            def fake_run(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                commands.append(argv)
                return subprocess.CompletedProcess(argv, 0, "", "")

            with mock.patch.object(foreman, "enforce_runtime_environment", return_value=None), \
                mock.patch.object(foreman.repo_guard, "assert_clean"), \
                mock.patch.object(foreman.repo_guard, "stash_list", return_value=[]), \
                mock.patch.object(foreman.repo_guard, "fetch"), \
                mock.patch.object(foreman.repo_guard, "ensure_base_checked_out_and_updated"), \
                mock.patch.object(foreman, "run_trusted_preflight"), \
                mock.patch.object(foreman.repo_guard, "current_head", return_value="base123"), \
                mock.patch.object(foreman, "load_issues", return_value=[issue]), \
                mock.patch.object(foreman, "recover_stale_claims", return_value=False), \
                mock.patch.object(foreman, "load_issue_detail", return_value=issue), \
                mock.patch.object(foreman, "open_pr_mentions_issue", return_value=False), \
                mock.patch.object(foreman, "create_worker_checkout"), \
                mock.patch.object(foreman, "run_worker_preflight", return_value="No Codex credentials stored"), \
                mock.patch.object(foreman, "remove_worker_checkout"), \
                mock.patch.object(foreman.repo_guard, "delete_local_branch"), \
                mock.patch.object(foreman.repo_guard, "assert_stash_unchanged"):
                result = foreman.run_once(repo="owner/repo", repo_root=repo, base="main", state_db=db, dry_run=False, command_runner=fake_run, policy=smactorio_policy.default_policy())

        self.assertEqual("no_work", result["status"])
        self.assertEqual("worker_preflight_failed", result["reason"])
        self.assertFalse(any(cmd[:3] == ["gh", "issue", "edit"] for cmd in commands), commands)
        self.assertFalse(any(cmd[:3] == ["gh", "issue", "comment"] for cmd in commands), commands)


if __name__ == "__main__":
    unittest.main()
