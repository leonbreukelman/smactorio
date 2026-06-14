#!/usr/bin/env python3
"""Policy for the SmactorIO GitHub-issue runtime.

This policy is deliberately small and local.  GitHub Issues are the visible
backlog; the service only needs enough policy to decide whether a ticket may be
claimed autonomously and what labels mean terminal/blocked state.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Iterable


HERMES_FORK_SYNC_MARKER_RE = re.compile(r"<!--\s*smactorio:hermes-fork-sync\s+(?P<payload>\{.*?\})\s*-->", re.DOTALL)

SIGNAL_HUB_REPO = "leonbreukelman/rtx3070-workshop-ops"
HERMES_AGENT_REPO = "leonbreukelman/hermes-agent"

SIGNAL_HUB_ALLOWED_CHANGE_PREFIXES = ("signal-hub/", ".github/workflows/")
SIGNAL_HUB_SECRET_SCAN_PATHS = (".github/workflows", "signal-hub")
SIGNAL_HUB_VERIFICATION_TEST_COMMANDS = (("python3", "-m", "unittest", "discover", "-s", "tests", "-q"),)
SIGNAL_HUB_VERIFICATION_ARTIFACT_PREFIXES = ("signal-hub/docs/verification/",)
SIGNAL_HUB_COMMIT_PATHSPECS = ("signal-hub", ".github/workflows")

HERMES_BASE_ALLOWED_CHANGE_PREFIXES = (
    "agent/",
    "tools/",
    "gateway/",
    "hermes_cli/",
    "plugins/",
    "skills/",
    "optional-skills/",
    "tests/",
    "scripts/",
    "website/",
    "ui-tui/",
    "tui_gateway/",
    "acp_adapter/",
    "cron/",
    "docs/",
    "run_agent.py",
    "model_tools.py",
    "toolsets.py",
    "cli.py",
    "hermes_state.py",
    "hermes_constants.py",
    "hermes_logging.py",
    "batch_runner.py",
)
HERMES_FORBIDDEN_CHANGE_PATHS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "conftest.py",
    "tests/conftest.py",
    ".github/dependabot.yml",
    ".github/dependabot.yaml",
)
HERMES_FORBIDDEN_CHANGE_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
    ".github/dependabot/",
    ".hermes/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    "logs/",
    "runtime/",
    "cache/",
    ".cache/",
    ".pytest_cache/",
    ".mypy_cache/",
    ".ruff_cache/",
)
HERMES_VERIFICATION_TEST_COMMANDS = (
    (
        "python3",
        "-m",
        "pytest",
        "tests/hermes_cli/test_cmd_update.py",
        "tests/hermes_cli/test_update_check.py",
        "tests/cli/test_update_command.py",
        "-q",
    ),
)


@dataclass(frozen=True)
class SmactorioPolicy:
    """Bounded-autonomy policy used by the issue foreman."""

    eligible_states: frozenset[str] = frozenset({"OPEN", "open"})
    blocked_labels: frozenset[str] = frozenset(
        {
            "smactorio:claimed",
            "smactorio:blocked",
            "smactorio:done",
            "blocked",
            "blocked:human",
            "blocked:external",
            "risk:high",
            "risk:medium",
            "risk:strategic",
            "risk:production",
            "risk:security-compliance",
            "type:research",
            "type:research-proposal",
            "needs-human",
            "needs:human",
            "autonomy:blocked",
        }
    )
    required_labels: frozenset[str] = frozenset({"smactorio", "autonomy:ready", "risk:low"})
    preferred_labels: frozenset[str] = frozenset({"autonomy:ready", "smactorio"})
    forbidden_text_fragments: frozenset[str] = frozenset(
        {
            "delete repo",
            "delete repository",
            "rotate secret",
            "production credential",
            "disable branch protection",
            "admin override",
            "2fa",
            "two-factor",
            "$50",
            "payment",
            "billing",
        }
    )
    claim_label: str = "smactorio:claimed"
    done_label: str = "smactorio:done"
    blocked_label: str = "smactorio:blocked"
    needs_attention_label: str = "smactorio:needs-attention"
    max_open_issues: int = 50
    claim_ttl_minutes: int = 180
    max_attempts_per_failure_signature: int = 3
    worker_timeout_seconds: int = 1800
    worker_preflight_timeout_seconds: int = 120
    review_timeout_seconds: int = 1800
    check_timeout_seconds: int = 600
    required_host: str = "rtx3070"
    runtime_attest_env: str = "SMACTORIO_RUNTIME_ATTEST"
    required_runtime_attest: str = "rtx3070-smactorio-systemd"
    worker_hermes_home_env: str = "SMACTORIO_WORKER_HERMES_HOME"
    allowed_hermes_roots: tuple[str, ...] = ("/home/leonb/projects/hermes-agent/",)
    allowed_worker_providers: frozenset[str] = frozenset({"xai", "grok"})

    # Repository-specific verification / mutation policy.  Defaults preserve
    # the original Signal Hub lane behavior.
    allowed_change_prefixes: tuple[str, ...] = SIGNAL_HUB_ALLOWED_CHANGE_PREFIXES
    forbidden_change_paths: tuple[str, ...] = ()
    forbidden_change_prefixes: tuple[str, ...] = ()
    secret_scan_paths: tuple[str, ...] = SIGNAL_HUB_SECRET_SCAN_PATHS
    secret_scan_changed_paths_only: bool = False
    verification_test_commands: tuple[tuple[str, ...], ...] = SIGNAL_HUB_VERIFICATION_TEST_COMMANDS
    verification_test_cwd: str = "signal-hub"
    verification_artifact_prefixes: tuple[str, ...] = SIGNAL_HUB_VERIFICATION_ARTIFACT_PREFIXES
    # Backward-compatible alias.  __post_init__ mirrors the canonical field
    # when callers do not pass a legacy value explicitly.
    foreman_artifact_prefixes: tuple[str, ...] = ()
    commit_pathspecs: tuple[str, ...] = SIGNAL_HUB_COMMIT_PATHSPECS
    discard_verification_side_effect_pathspecs: tuple[str, ...] = SIGNAL_HUB_COMMIT_PATHSPECS
    safe_worker_generated_side_effect_prefixes: tuple[str, ...] = ("signal-hub/public/",)
    trusted_preflight_files: tuple[str, ...] = (
        "signal-hub/scripts/check_path_scope.py",
        "signal-hub/scripts/scan_for_secrets.py",
    )
    trusted_preflight_files_root: str = "repo"  # "repo" or "signal-hub"
    check_commands: tuple[tuple[str, ...], ...] = field(
        default_factory=lambda: (
            ("git", "diff", "--check", "origin/main...HEAD"),
            (
                "python3",
                "scripts/check_path_scope.py",
                "--from-file",
                "/tmp/smactorio-changed-paths.txt",
                "--allow-prefix",
                "signal-hub/",
                "--allow-prefix",
                ".github/workflows/",
            ),
            ("python3", "scripts/scan_for_secrets.py", ".github/workflows", "signal-hub"),
            ("python3", "-m", "unittest", "discover", "-s", "tests", "-q"),
        )
    )

    def __post_init__(self) -> None:
        if not self.foreman_artifact_prefixes:
            object.__setattr__(self, "foreman_artifact_prefixes", self.verification_artifact_prefixes)


def default_policy() -> SmactorioPolicy:
    return SmactorioPolicy()


def _normalize_repo(repo: str) -> str:
    return (repo or "").strip().lower().removeprefix("https://github.com/").removesuffix(".git")


def parse_hermes_fork_sync_marker(body: str | None) -> dict[str, object] | None:
    """Parse the hidden fork-sync marker embedded in SmactorIO issue bodies."""
    for match in HERMES_FORK_SYNC_MARKER_RE.finditer(body or ""):
        try:
            payload = json.loads(match.group("payload"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("lane") == "hermes-upstream-sync":
            return payload
    return None


def _safe_marker_paths(payload: dict[str, object] | None) -> tuple[str, ...]:
    if not payload:
        return ()
    raw_paths = payload.get("conflict_files")
    if not isinstance(raw_paths, list):
        return ()
    safe: list[str] = []
    for raw in raw_paths:
        path = str(raw or "").replace("\\", "/").strip()
        if not path or path.startswith("/") or path.startswith("../") or "/../" in path or "://" in path:
            continue
        if path not in safe:
            safe.append(path)
    return tuple(safe)


def hermes_policy(*, marker_payload: dict[str, object] | None = None) -> SmactorioPolicy:
    marker_paths = _safe_marker_paths(marker_payload)
    # The Hermes upstream-sync lane is intentionally narrow: after the issue is
    # loaded, only the conflict files emitted by the checker may be touched. A
    # clean merge that requires a merge commit but reports no conflict files will
    # therefore block for human review instead of granting broad source access.
    allowed = marker_paths
    return SmactorioPolicy(
        allowed_hermes_roots=("/home/leonb/hermes/", "/home/leonb/projects/hermes-agent/"),
        allowed_change_prefixes=allowed,
        forbidden_change_paths=HERMES_FORBIDDEN_CHANGE_PATHS,
        forbidden_change_prefixes=HERMES_FORBIDDEN_CHANGE_PREFIXES,
        secret_scan_paths=(),
        secret_scan_changed_paths_only=True,
        verification_test_commands=HERMES_VERIFICATION_TEST_COMMANDS,
        verification_test_cwd=".",
        verification_artifact_prefixes=(".smactorio/verification/",),
        commit_pathspecs=(".",),
        discard_verification_side_effect_pathspecs=(".",),
        safe_worker_generated_side_effect_prefixes=(),
        trusted_preflight_files=("scripts/check_path_scope.py", "scripts/scan_for_secrets.py"),
        trusted_preflight_files_root="signal-hub",
    )


def fail_closed_policy() -> SmactorioPolicy:
    """Policy for unsupported repositories: claim nothing and mutate nothing."""
    return SmactorioPolicy(
        eligible_states=frozenset(),
        required_labels=frozenset({"smactorio:unsupported-repo"}),
        preferred_labels=frozenset(),
        allowed_change_prefixes=(),
        forbidden_change_paths=(),
        forbidden_change_prefixes=(),
        secret_scan_paths=(),
        secret_scan_changed_paths_only=True,
        verification_test_commands=(),
        verification_test_cwd=".",
        verification_artifact_prefixes=(),
        commit_pathspecs=(),
        discard_verification_side_effect_pathspecs=(),
        safe_worker_generated_side_effect_prefixes=(),
        trusted_preflight_files=(),
        trusted_preflight_files_root="signal-hub",
    )


def policy_for_repo(repo: str) -> SmactorioPolicy:
    """Return the policy for a repository lane.

    Unknown repositories receive a closed policy so a typo or unexpected repo
    cannot be claimed or broaden SmactorIO's mutation scope.
    """
    normalized = _normalize_repo(repo)
    if normalized == SIGNAL_HUB_REPO:
        return default_policy()
    if normalized == HERMES_AGENT_REPO:
        return hermes_policy()
    return fail_closed_policy()


def policy_for_issue(repo: str, issue: dict) -> SmactorioPolicy:
    if _normalize_repo(repo) == HERMES_AGENT_REPO:
        return hermes_policy(marker_payload=parse_hermes_fork_sync_marker(str(issue.get("body") or "")))
    return policy_for_repo(repo)


def label_names(issue: dict) -> set[str]:
    labels = issue.get("labels") or []
    names: set[str] = set()
    for label in labels:
        if isinstance(label, dict):
            name = str(label.get("name") or "").strip()
        else:
            name = str(label or "").strip()
        if name:
            names.add(name)
    return names


def issue_ineligibility_reasons(issue: dict, policy: SmactorioPolicy | None = None) -> list[str]:
    """Return human-readable reasons an issue cannot be claimed.

    The policy intentionally treats issue labels and the title as the hard
    eligibility gate. Bodies are worker instructions / acceptance criteria and
    often need to document stop conditions (for example 2FA, billing, or
    credentials). Blocking on body substring matches made the queue silently
    reject valid low-risk repair tickets, so body text is not a hard gate here.
    """
    policy = policy or default_policy()
    reasons: list[str] = []
    state = issue.get("state")
    if state not in policy.eligible_states:
        reasons.append(f"ineligible state: {state or '(missing)'}")
    labels = label_names(issue)
    missing = sorted(policy.required_labels - labels)
    if missing:
        reasons.append("missing required labels: " + ", ".join(missing))
    blocked = sorted(labels & policy.blocked_labels)
    if blocked:
        reasons.append("blocked labels present: " + ", ".join(blocked))
    title = str(issue.get("title") or "").lower()
    title_fragments = sorted(fragment for fragment in policy.forbidden_text_fragments if fragment in title)
    if title_fragments:
        reasons.append("forbidden title fragment: " + ", ".join(title_fragments))
    return reasons


def issue_is_eligible(issue: dict, policy: SmactorioPolicy | None = None) -> bool:
    return not issue_ineligibility_reasons(issue, policy)


def issue_priority_key(issue: dict, policy: SmactorioPolicy | None = None) -> tuple[int, int]:
    """Sort key: preferred-label issues first, then oldest/smallest issue number."""
    policy = policy or default_policy()
    labels = label_names(issue)
    preferred = 0 if labels & policy.preferred_labels else 1
    try:
        number = int(issue.get("number") or 0)
    except (TypeError, ValueError):
        number = 0
    return preferred, number


def filter_eligible(issues: Iterable[dict], policy: SmactorioPolicy | None = None) -> list[dict]:
    policy = policy or default_policy()
    return sorted((issue for issue in issues if issue_is_eligible(issue, policy)), key=lambda item: issue_priority_key(item, policy))
