from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.strip()


def commit_all(repo: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Unit Test", "-c", "user.email=unit@example.test", "commit", "-m", message],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return git(repo, "rev-parse", "HEAD")


class FakeGhRunner:
    def __init__(self, issues: list[dict] | None = None) -> None:
        self.issues = issues or []
        self.calls: list[list[str]] = []
        self.bodies: dict[str, str] = {}

    def __call__(self, argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        self.calls.append(args)
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(self.issues), stderr="")
        if args[:3] == ["gh", "issue", "edit"]:
            path = Path(args[args.index("--body-file") + 1])
            self.bodies["edit"] = path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["gh", "issue", "comment"]:
            path = Path(args[args.index("--body-file") + 1])
            self.bodies["comment"] = path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
        if args[:3] == ["gh", "issue", "create"]:
            path = Path(args[args.index("--body-file") + 1])
            self.bodies["create"] = path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess(args, 0, stdout="https://github.com/leonbreukelman/hermes-agent/issues/123\n", stderr="")
        raise AssertionError(f"unexpected command: {args}")


class CreateCollisionRunner(FakeGhRunner):
    def __init__(self, reconciled_issue: dict) -> None:
        super().__init__([])
        self.reconciled_issue = reconciled_issue
        self.list_count = 0

    def __call__(self, argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        args = list(argv)
        if args[:3] == ["gh", "issue", "list"]:
            self.calls.append(args)
            self.list_count += 1
            issues = [] if self.list_count == 1 else [self.reconciled_issue]
            return subprocess.CompletedProcess(args, 0, stdout=json.dumps(issues), stderr="")
        if args[:3] == ["gh", "issue", "create"]:
            self.calls.append(args)
            path = Path(args[args.index("--body-file") + 1])
            self.bodies["create"] = path.read_text(encoding="utf-8")
            return subprocess.CompletedProcess(args, 1, stdout="", stderr="already exists")
        return super().__call__(argv, cwd)


class HermesForkSyncCheckTest(unittest.TestCase):
    def test_issue_body_uses_structured_marker_without_local_path_or_token_leakage(self) -> None:
        import hermes_fork_sync_check as sync

        state = sync.SyncState(
            fork_sha="f" * 40,
            upstream_sha="u" * 40,
            base="main",
            timestamp="2026-05-28T00:00:00Z",
            merge_required=True,
            conflict_files=("agent/provider.py", "tests/test_provider.py"),
        )

        body = sync.render_issue_body(state)
        marker = sync.parse_marker(body)

        self.assertEqual("hermes-upstream-sync", marker["lane"])
        self.assertEqual(["agent/provider.py", "tests/test_provider.py"], marker["conflict_files"])
        self.assertNotIn("/home/", body)
        self.assertNotIn("/tmp/", body)
        self.assertNotRegex(body, r"gh[pousr]_[A-Za-z0-9_]{8,}")

    def test_upsert_issue_updates_existing_marker_once_per_sha_pair(self) -> None:
        import hermes_fork_sync_check as sync

        old_state = sync.SyncState(
            fork_sha="1" * 40,
            upstream_sha="2" * 40,
            base="main",
            timestamp="2026-05-28T00:00:00Z",
            merge_required=True,
            conflict_files=("agent/old.py",),
        )
        new_state = sync.SyncState(
            fork_sha="3" * 40,
            upstream_sha="4" * 40,
            base="main",
            timestamp="2026-05-28T01:00:00Z",
            merge_required=True,
            conflict_files=("agent/new.py",),
        )
        runner = FakeGhRunner([{"number": 42, "title": sync.DEFAULT_TITLE, "body": sync.render_issue_body(old_state), "labels": []}])

        result = sync.upsert_sync_issue("leonbreukelman/hermes-agent", new_state, runner=runner)

        self.assertEqual({"status": "issue_updated", "issue_number": 42}, result)
        self.assertIn("agent/new.py", runner.bodies["edit"])
        self.assertIn("Conflict files: 1", runner.bodies["comment"])
        self.assertTrue(any(call[:3] == ["gh", "issue", "edit"] for call in runner.calls))
        self.assertTrue(any(call[:3] == ["gh", "issue", "comment"] for call in runner.calls))

    def test_upsert_issue_skips_update_when_sha_pair_is_unchanged(self) -> None:
        import hermes_fork_sync_check as sync

        state = sync.SyncState(
            fork_sha="a" * 40,
            upstream_sha="b" * 40,
            base="main",
            timestamp="2026-05-28T00:00:00Z",
            merge_required=True,
            conflict_files=("agent/file.py",),
        )
        runner = FakeGhRunner([{"number": 7, "title": sync.DEFAULT_TITLE, "body": sync.render_issue_body(state), "labels": []}])

        result = sync.upsert_sync_issue("leonbreukelman/hermes-agent", state, runner=runner)

        self.assertEqual({"status": "issue_unchanged", "issue_number": 7}, result)
        self.assertFalse(any(call[:3] == ["gh", "issue", "edit"] for call in runner.calls))
        self.assertFalse(any(call[:3] == ["gh", "issue", "comment"] for call in runner.calls))

    def test_upsert_issue_reconciles_create_race_to_existing_marker_issue(self) -> None:
        import hermes_fork_sync_check as sync

        state = sync.SyncState(
            fork_sha="c" * 40,
            upstream_sha="d" * 40,
            base="main",
            timestamp="2026-05-28T00:00:00Z",
            merge_required=True,
            conflict_files=("agent/race.py",),
        )
        runner = CreateCollisionRunner({"number": 88, "title": sync.DEFAULT_TITLE, "body": sync.render_issue_body(state), "labels": []})

        result = sync.upsert_sync_issue("leonbreukelman/hermes-agent", state, runner=runner)

        self.assertEqual({"status": "issue_reconciled", "issue_number": 88}, result)
        self.assertEqual(2, runner.list_count)
        self.assertTrue(any(call[:3] == ["gh", "issue", "create"] for call in runner.calls))

    def test_configure_git_auth_uses_askpass_without_serializing_token(self) -> None:
        import hermes_fork_sync_check as sync

        with tempfile.TemporaryDirectory() as tmp:
            env = {"GH_TOKEN": "TOKEN_PLACEHOLDER"}
            sync.configure_git_auth(Path(tmp) / "repo", base_env=env)
            askpass = Path(env["GIT_ASKPASS"])
            text = askpass.read_text(encoding="utf-8")

        self.assertIn("GITHUB_TOKEN", text)
        self.assertNotIn("TOKEN_PLACEHOLDER", text)
        self.assertEqual("TOKEN_PLACEHOLDER", env["GITHUB_TOKEN"])
        self.assertEqual("0", env["GIT_TERMINAL_PROMPT"])

    def test_fast_forward_push_argv_never_uses_force_or_plus_refspec(self) -> None:
        import hermes_fork_sync_check as sync

        argv = sync.fast_forward_push_args("a" * 40, base="main")

        sync.assert_fast_forward_push_safe(argv)
        self.assertNotIn("--force", argv)
        self.assertFalse(any(arg.startswith("+") for arg in argv), argv)
        self.assertIn("refs/heads/main", argv[-1])

    def test_unmerged_paths_parses_index_stages_when_diff_filter_is_empty(self) -> None:
        import hermes_fork_sync_check as sync

        calls: list[list[str]] = []

        def fake_runner(argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            args = list(argv)
            calls.append(args)
            if args == ["git", "ls-files", "-u", "-z"]:
                return subprocess.CompletedProcess(
                    args,
                    0,
                    stdout=(
                        "100644 df967 1\tagent/provider.py\0"
                        "100644 f468 2\tagent/provider.py\0"
                        "100644 0459 3\tagent/provider.py\0"
                    ),
                    stderr="",
                )
            if args == ["git", "diff", "--name-only", "-z", "--diff-filter=U"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            raise AssertionError(args)

        self.assertEqual(("agent/provider.py",), sync.unmerged_paths(Path("/repo"), runner=fake_runner))
        self.assertNotIn(["git", "diff", "--name-only", "-z", "--diff-filter=U"], calls)

    def test_unmerged_paths_preserves_nul_delimited_git_pathnames(self) -> None:
        import hermes_fork_sync_check as sync

        weird_path = 'agent/quote" tab\tback\\slash.py'
        stdout = f"100644 df967 1\t{weird_path}\0" f"100644 f468 2\t{weird_path}\0"

        self.assertEqual((weird_path,), sync._parse_ls_files_unmerged(stdout))

    def test_unmerged_paths_falls_back_to_nul_delimited_diff_paths(self) -> None:
        import hermes_fork_sync_check as sync

        calls: list[list[str]] = []

        def fake_runner(argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
            args = list(argv)
            calls.append(args)
            if args == ["git", "ls-files", "-u", "-z"]:
                return subprocess.CompletedProcess(args, 0, stdout="", stderr="")
            if args == ["git", "diff", "--name-only", "-z", "--diff-filter=U"]:
                return subprocess.CompletedProcess(args, 0, stdout="agent/provider.py\0", stderr="")
            raise AssertionError(args)

        self.assertEqual(("agent/provider.py",), sync.unmerged_paths(Path("/repo"), runner=fake_runner))
        self.assertEqual(
            [["git", "ls-files", "-u", "-z"], ["git", "diff", "--name-only", "-z", "--diff-filter=U"]],
            calls,
        )

    def test_acquire_lock_returns_none_without_truncating_holder_on_contention(self) -> None:
        import hermes_fork_sync_check as sync

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "hermes-fork.lock"
            first = sync.acquire_lock(lock_path)
            self.assertIsNotNone(first)
            try:
                holder_text = lock_path.read_text(encoding="utf-8")
                self.assertIn("pid=", holder_text)
                second = sync.acquire_lock(lock_path)
                self.assertIsNone(second)
                self.assertEqual(holder_text, lock_path.read_text(encoding="utf-8"))
            finally:
                first.close()

    def test_main_reports_lock_busy_without_running_check_when_lock_is_held(self) -> None:
        import hermes_fork_sync_check as sync

        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "hermes-fork.lock"
            first = sync.acquire_lock(lock_path)
            self.assertIsNotNone(first)
            try:
                stdout = io.StringIO()
                with mock.patch.object(sync, "run_check", side_effect=AssertionError("run_check should not start")):
                    with mock.patch("sys.stdout", stdout):
                        code = sync.main(["--json", "--lock-file", str(lock_path), "--work-root", str(Path(tmp) / "work")])
                self.assertEqual(0, code)
                self.assertEqual({"status": "lock_busy"}, json.loads(stdout.getvalue()))
            finally:
                first.close()

    def test_merge_simulation_collects_conflicts_and_leaves_scratch_clean(self) -> None:
        import hermes_fork_sync_check as sync

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            (repo / "agent").mkdir()
            (repo / "agent" / "provider.py").write_text("base\n", encoding="utf-8")
            base_sha = commit_all(repo, "seed")

            git(repo, "checkout", "-b", "fork", base_sha)
            (repo / "agent" / "provider.py").write_text("fork\n", encoding="utf-8")
            fork_sha = commit_all(repo, "fork change")

            git(repo, "checkout", "-b", "upstream", base_sha)
            (repo / "agent" / "provider.py").write_text("upstream\n", encoding="utf-8")
            upstream_sha = commit_all(repo, "upstream change")

            with mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull}, clear=False):
                conflicts = sync.simulate_merge(repo, fork_sha=fork_sha, upstream_sha=upstream_sha)

            self.assertEqual(("agent/provider.py",), conflicts)
            self.assertEqual("", git(repo, "status", "--porcelain=v1"))
            self.assertFalse((repo / ".git" / "MERGE_HEAD").exists())


if __name__ == "__main__":
    unittest.main()
