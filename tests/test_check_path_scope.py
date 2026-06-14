from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


ALLOWED_PREFIXES = ("signal-hub/", ".github/workflows/")


class CheckPathScopeTest(unittest.TestCase):
    def test_allows_safe_signal_hub_source_and_ci_control_plane_paths(self) -> None:
        import check_path_scope

        safe_paths = [
            "signal-hub/scripts/check_path_scope.py",
            "signal-hub/scripts/scan_for_secrets.py",
            "signal-hub/tests/test_check_path_scope.py",
            "signal-hub/docs/specs/guardrails.md",
            "signal-hub/public/index.html",
            "signal-hub/data/project_homepages/smactorio.json",
            "signal-hub/data/smactorio/improvement_candidates.json",
            ".github/workflows/signal-hub-guardrails.yml",
        ]

        self.assertEqual([], check_path_scope.check_paths(safe_paths, allowed_prefixes=ALLOWED_PREFIXES))

    def test_rejects_runtime_state_credentials_tokens_caches_backups_envs_and_raw_data(self) -> None:
        import check_path_scope

        forbidden_paths = [
            "signal-hub/state/signal_loop.db",
            "signal-hub/logs/run.log",
            "signal-hub/cache/sources.json",
            "signal-hub/backups/source.tar.gz",
            "signal-hub/.env.local",
            "signal-hub/credentials/service-account.json",
            "signal-hub/tokens/github.txt",
            "signal-hub/secrets/service-account.json",
            "signal-hub/private_key.json",
            "signal-hub/api_key.json",
            "signal-hub/passwords/local.txt",
            "signal-hub/raw/source-dump.json",
            "signal-hub/raw_data/source-dump.json",
            "signal-hub/data/raw/source-dump.json",
            "signal-hub/data/smactorio/raw/source-dump.json",
            "signal-hub/reports/private-report.html",
        ]

        findings = check_path_scope.check_paths(forbidden_paths, allowed_prefixes=ALLOWED_PREFIXES)
        rejected = {finding.path: finding.reason for finding in findings}

        for path in forbidden_paths:
            self.assertIn(path, rejected)

    def test_normalizes_paths_before_checking_scope_and_denylist_rules(self) -> None:
        import check_path_scope

        findings = check_path_scope.check_paths(
            [
                r"signal-hub\state\signal_loop.db",
                "signal-hub/docs/../state/signal_loop.db",
                "../signal-hub/scripts/check_path_scope.py",
                "/tmp/signal-hub/scripts/check_path_scope.py",
                " signal-hub/scripts/check_path_scope.py",
                "signal-hub/scripts/check_path_scope.py ",
                "README.md",
            ],
            allowed_prefixes=ALLOWED_PREFIXES,
        )
        rejected = {finding.path: finding.reason for finding in findings}

        self.assertIn("signal-hub/state/signal_loop.db", rejected)
        self.assertIn("../signal-hub/scripts/check_path_scope.py", rejected)
        self.assertIn("/tmp/signal-hub/scripts/check_path_scope.py", rejected)
        self.assertIn(" signal-hub/scripts/check_path_scope.py", rejected)
        self.assertIn("signal-hub/scripts/check_path_scope.py ", rejected)
        self.assertIn("README.md", rejected)

    def test_cli_reads_newline_delimited_changed_paths_file(self) -> None:
        import check_path_scope

        with tempfile.TemporaryDirectory() as tmp:
            path_file = Path(tmp) / "changed-paths.txt"
            path_file.write_text(
                "signal-hub/scripts/check_path_scope.py\n"
                "signal-hub/state/signal_loop.db\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = check_path_scope.main([
                    "--from-file",
                    str(path_file),
                    "--allow-prefix",
                    "signal-hub/",
                    "--allow-prefix",
                    ".github/workflows/",
                ])

        self.assertEqual(1, exit_code)
        self.assertIn("signal-hub/state/signal_loop.db", output.getvalue())
    def test_allow_prefix_matching_preserves_path_component_boundaries(self) -> None:
        import check_path_scope

        findings = check_path_scope.check_paths(
            [
                "signal-hub/scripts/check_path_scope.py",
                "signal-hubx/scripts/check_path_scope.py",
                ".github/workflows/signal-hub-guardrails.yml",
                ".github/workflows-extra/unsafe.yml",
            ],
            allowed_prefixes=("signal-hub", ".github/workflows"),
        )
        rejected = {finding.path: finding.reason for finding in findings}

        self.assertNotIn("signal-hub/scripts/check_path_scope.py", rejected)
        self.assertNotIn(".github/workflows/signal-hub-guardrails.yml", rejected)
        self.assertIn("signal-hubx/scripts/check_path_scope.py", rejected)
        self.assertIn(".github/workflows-extra/unsafe.yml", rejected)


if __name__ == "__main__":
    unittest.main()
