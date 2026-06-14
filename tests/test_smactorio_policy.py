from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class SmactorioResearchSafetyPolicyTest(unittest.TestCase):
    def test_research_and_medium_risk_labels_block_pickup_even_if_ready_labels_are_present(self) -> None:
        import smactorio_policy

        base_issue = {
            "number": 101,
            "state": "OPEN",
            "title": "Research-backed architecture proposal",
            "labels": [
                {"name": "smactorio"},
                {"name": "autonomy:ready"},
                {"name": "risk:low"},
                {"name": "type:research"},
                {"name": "risk:medium"},
            ],
        }
        reasons = smactorio_policy.issue_ineligibility_reasons(base_issue)
        self.assertTrue(any("type:research" in reason for reason in reasons), reasons)
        self.assertTrue(any("risk:medium" in reason for reason in reasons), reasons)
        self.assertEqual([], smactorio_policy.filter_eligible([base_issue]))

    def test_research_proposal_and_needs_human_block_pickup_even_if_low_risk_is_accidentally_present(self) -> None:
        import smactorio_policy

        issue = {
            "number": 102,
            "state": "OPEN",
            "title": "Review external research recommendation",
            "labels": ["smactorio", "autonomy:ready", "risk:low", "type:research-proposal", "needs-human"],
        }
        reasons = smactorio_policy.issue_ineligibility_reasons(issue)
        self.assertTrue(any("type:research-proposal" in reason for reason in reasons), reasons)
        self.assertTrue(any("needs-human" in reason for reason in reasons), reasons)
        self.assertFalse(smactorio_policy.issue_is_eligible(issue))

    def test_existing_low_risk_smactorio_issue_remains_eligible(self) -> None:
        import smactorio_policy

        issue = {
            "number": 103,
            "state": "OPEN",
            "title": "Add docs test for deterministic processor",
            "labels": ["smactorio", "autonomy:ready", "risk:low", "type:docs"],
        }
        self.assertEqual([], smactorio_policy.issue_ineligibility_reasons(issue))
        self.assertEqual([issue], smactorio_policy.filter_eligible([issue]))

    def test_hermes_repo_is_retired_and_fail_closed_like_unknown_repos(self) -> None:
        import smactorio_policy

        signal_hub = smactorio_policy.policy_for_repo("leonbreukelman/rtx3070-workshop-ops")
        hermes = smactorio_policy.policy_for_repo("leonbreukelman/hermes-agent")
        unknown = smactorio_policy.policy_for_repo("someone/else")

        self.assertEqual(("signal-hub/", ".github/workflows/"), signal_hub.allowed_change_prefixes)
        self.assertEqual(frozenset(), hermes.eligible_states)
        self.assertEqual(frozenset({"smactorio:unsupported-repo"}), hermes.required_labels)
        self.assertEqual((), hermes.allowed_change_prefixes)
        self.assertEqual((), hermes.verification_artifact_prefixes)
        self.assertEqual(frozenset(), unknown.eligible_states)
        self.assertEqual((), unknown.allowed_change_prefixes)
        unsupported_issue = {"state": "OPEN", "labels": [{"name": "smactorio"}, {"name": "autonomy:ready"}, {"name": "risk:low"}]}
        self.assertIn("missing required labels", "\n".join(smactorio_policy.issue_ineligibility_reasons(unsupported_issue, unknown)))
        self.assertIn("missing required labels", "\n".join(smactorio_policy.issue_ineligibility_reasons(unsupported_issue, hermes)))

    def test_retired_hermes_issue_marker_does_not_reopen_policy_scope(self) -> None:
        import smactorio_policy

        issue = {
            "body": '<!-- smactorio:hermes-fork-sync {"lane":"hermes-upstream-sync","conflict_files":["agent/foo.py","../bad","/tmp/leak"]} -->',
        }
        policy = smactorio_policy.policy_for_issue("leonbreukelman/hermes-agent", issue)

        self.assertEqual(frozenset(), policy.eligible_states)
        self.assertEqual((), policy.allowed_change_prefixes)
        self.assertEqual((), policy.verification_artifact_prefixes)


if __name__ == "__main__":
    unittest.main()
