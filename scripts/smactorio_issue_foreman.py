#!/usr/bin/env python3
"""SmactorIO GitHub issue foreman.

The foreman owns the GitHub lifecycle and repo hygiene.  A worker may edit and
commit inside an isolated worktree, but the foreman is responsible for claim,
verification, PR creation, merge, evidence comments, and cleanup.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any, Callable, Sequence

import smactorio_policy
import smactorio_repo_guard as repo_guard
import smactorio_runtime_state as runtime_state

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# SmactorIO now lives in its own checkout.  The default target remains the
# rtx3070 workshop repo it was originally built to operate on; callers can still
# override this with --repo-root / SMACTORIO_REPO_ROOT for other lanes.
DEFAULT_REPO_ROOT = Path.home() / "projects" / "rtx3070-workshop-ops"
DEFAULT_SHARE_DIR = Path.home() / ".local" / "share" / "smactorio"
CLAIM_RE = re.compile(r"<!--\s*smactorio:claim\s+(?P<payload>\{.*?\})\s*-->", re.DOTALL)
SAFE_BRANCH_RE = re.compile(r"[^a-z0-9._/-]+")
SENSITIVE_ENV_FRAGMENTS = (
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "ACCESS_KEY",
    "PRIVATE_KEY",
    "CREDENTIAL",
    "AUTH_SOCK",
)
TRUSTED_PREFLIGHT_FILES = (
    "signal-hub/scripts/check_path_scope.py",
    "signal-hub/scripts/scan_for_secrets.py",
)
REPAIR_ALLOWED_PREFIXES = ("signal-hub/docs/", "signal-hub/tests/", "signal-hub/scripts/", "signal-hub/config/")
PROTECTED_SMACTORIO_RUNTIME_PATHS = (
    "signal-hub/scripts/smactorio_issue_foreman.py",
    "signal-hub/scripts/project_improvement_processor.py",
    "signal-hub/scripts/smactorio_policy.py",
    "signal-hub/scripts/smactorio_repo_guard.py",
    "signal-hub/scripts/smactorio_runtime_state.py",
    "signal-hub/tests/test_smactorio_issue_foreman.py",
    "signal-hub/tests/test_project_improvement_processor.py",
    "infra/systemd/system/smactorio.service",
    "infra/systemd/system/smactorio.timer",
)
LOW_RISK_REPAIR_PREFIXES = (
    "signal-hub/docs/",
    "signal-hub/tests/",
    "signal-hub/scripts/",
    "signal-hub/config/",
)
WORKER_OUTCOME_SENTINEL_PREFIX = "SMACTORIO_OUTCOME_JSON_V1:"
WORKER_OUTCOME_BLOCK_RE = re.compile(r"```smactorio-outcome-json\s*\n(?P<payload>.*?)\n```", re.DOTALL)
STRUCTURED_WORKER_OUTCOMES = {"ALREADY_SATISFIED"}
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?P<name>[A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|PASSWD|API_KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL)[A-Z0-9_]*)\s*(?:=|:)\s*(?P<value>\"[^\"]*\"|'[^']*'|[^\s`'\"]+)"
)
GITHUB_SECRET_RE = re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{12,})\b")
BEARER_HEADER_RE = re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[^\s`'\"<>]+")
ABSOLUTE_PATH_RE = re.compile(r"/(?:home|tmp|var|srv|etc|root|workspace|mnt|opt|Users)/[^\s`'\"<>)]*")
MAX_COMMENT_BODY_CHARS = 6000


class SmactorioError(RuntimeError):
    """Runtime failure that should be reported as blocked evidence."""


def _read_worker_provider(config_path: Path) -> str:
    """Read the configured Hermes provider without loading secrets."""
    try:
        text = config_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in text.splitlines():
        match = re.match(r"\s*provider\s*:\s*['\"]?([^'\"#\s]+)", line)
        if match:
            return match.group(1).strip().lower()
    return ""


def _wrapper_exec_targets(path: Path) -> list[Path]:
    try:
        if not path.is_file() or path.stat().st_size > 8192:
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return []
    targets: list[Path] = []
    for pattern in (r'exec\s+"([^"]+)"', r"exec\s+'([^']+)'", r"exec\s+(\S+)"):
        for match in re.finditer(pattern, text):
            target = match.group(1).strip()
            if target.startswith("/"):
                targets.append(Path(target))
    return targets


def _path_under_any(path: Path, roots: Sequence[str]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        resolved = path.absolute()
    for root_text in roots:
        root = Path(root_text).expanduser()
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _hermes_command_is_allowed(hermes_path: str, allowed_roots: Sequence[str]) -> bool:
    if not allowed_roots:
        return True
    path = Path(hermes_path).expanduser()
    candidates = [path, *_wrapper_exec_targets(path)]
    return any(_path_under_any(candidate, allowed_roots) for candidate in candidates)


def runtime_environment_errors(
    policy: smactorio_policy.SmactorioPolicy,
    *,
    base_env: dict[str, str] | None = None,
    hostname: str | None = None,
    hermes_path: str | None = None,
) -> list[str]:
    """Return reasons this process is not the canonical SmactorIO runtime.

    This prevents a developer shell or another host from claiming GitHub issues
    with a different Hermes provider/auth setup.
    """
    env = dict(base_env or os.environ)
    errors: list[str] = []
    actual_host = hostname or socket.gethostname()
    if policy.required_host and actual_host != policy.required_host:
        errors.append(f"host {actual_host!r} is not required host {policy.required_host!r}")
    attest = env.get(policy.runtime_attest_env, "")
    if policy.required_runtime_attest and attest != policy.required_runtime_attest:
        errors.append(f"missing runtime attestation {policy.runtime_attest_env}")
    hermes_home = env.get("HERMES_HOME", "")
    worker_home = env.get(policy.worker_hermes_home_env, hermes_home)
    if not hermes_home:
        errors.append("HERMES_HOME is not set")
    if worker_home != hermes_home:
        errors.append(f"{policy.worker_hermes_home_env} does not match HERMES_HOME")
    resolved_hermes = hermes_path or shutil.which("hermes") or ""
    if not resolved_hermes:
        errors.append("hermes command is not on PATH")
    elif not _hermes_command_is_allowed(resolved_hermes, policy.allowed_hermes_roots):
        errors.append(f"hermes command {resolved_hermes} is outside allowed roots")
    if hermes_home:
        provider = _read_worker_provider(Path(hermes_home) / "config.yaml")
        if provider not in policy.allowed_worker_providers:
            errors.append(f"worker provider {provider or '(missing)'} is not allowed")
    return errors


def enforce_runtime_environment(policy: smactorio_policy.SmactorioPolicy) -> dict[str, Any] | None:
    errors = runtime_environment_errors(policy)
    if not errors:
        return None
    return {"status": "refused", "reason": "runtime_environment", "errors": errors}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def run_id() -> str:
    stamp = utc_now().replace("-", "").replace(":", "").replace("Z", "")
    return f"{stamp}-{time.time_ns():x}"


def default_command_runner(argv: Sequence[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    if isinstance(argv, str):
        raise TypeError("commands must be argv sequences, not shell strings")
    return subprocess.run(
        list(argv),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        **kwargs,
    )


def run_checked(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 120,
    command_runner: CommandRunner = default_command_runner,
) -> subprocess.CompletedProcess[str]:
    result = command_runner(list(argv), cwd=str(cwd) if cwd else None, env=env, timeout=timeout)
    if result.returncode != 0:
        raise SmactorioError(
            f"command failed ({result.returncode}): {' '.join(argv)}\nSTDOUT:\n{result.stdout[-2000:]}\nSTDERR:\n{result.stderr[-2000:]}"
        )
    return result


def load_issues(repo: str, *, command_runner: CommandRunner = default_command_runner, limit: int = 50) -> list[dict[str, Any]]:
    result = run_checked(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,labels,state,url,updatedAt,body",
        ],
        command_runner=command_runner,
        timeout=120,
    )
    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise SmactorioError(f"failed to parse gh issue list JSON: {exc}") from exc
    if not isinstance(payload, list):
        raise SmactorioError("gh issue list did not return a list")
    return [issue for issue in payload if isinstance(issue, dict)]


def load_issue_detail(repo: str, issue_number: int, *, command_runner: CommandRunner = default_command_runner) -> dict[str, Any]:
    result = run_checked(
        ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "number,title,labels,state,url,updatedAt,body"],
        command_runner=command_runner,
        timeout=120,
    )
    payload = json.loads(result.stdout or "{}")
    if not isinstance(payload, dict):
        raise SmactorioError(f"gh issue view did not return an object for issue #{issue_number}")
    return payload


def open_pr_mentions_issue(repo: str, issue_number: int, *, command_runner: CommandRunner = default_command_runner) -> bool:
    result = run_checked(
        ["gh", "pr", "list", "--repo", repo, "--state", "open", "--limit", "50", "--json", "number,title,body,headRefName"],
        command_runner=command_runner,
        timeout=120,
    )
    prs = json.loads(result.stdout or "[]")
    needle_hash = f"#{issue_number}"
    needle_url = f"/issues/{issue_number}"
    for pr in prs if isinstance(prs, list) else []:
        if not isinstance(pr, dict):
            continue
        text = f"{pr.get('title') or ''}\n{pr.get('body') or ''}\n{pr.get('headRefName') or ''}"
        if needle_hash in text or needle_url in text or f"issue-{issue_number}-" in text:
            return True
    return False


def select_issue(issues: list[dict[str, Any]], policy: smactorio_policy.SmactorioPolicy | None = None) -> dict[str, Any] | None:
    eligible = smactorio_policy.filter_eligible(issues, policy or smactorio_policy.default_policy())
    return eligible[0] if eligible else None


def skipped_issue_summaries(issues: list[dict[str, Any]], policy: smactorio_policy.SmactorioPolicy) -> list[dict[str, Any]]:
    """Return concise, body-free diagnostics for visible issues skipped by policy."""
    skipped: list[dict[str, Any]] = []
    for issue in issues:
        reasons = smactorio_policy.issue_ineligibility_reasons(issue, policy)
        if not reasons:
            continue
        skipped.append(
            {
                "number": issue.get("number"),
                "title": issue.get("title"),
                "url": issue.get("url"),
                "reasons": reasons,
            }
        )
    return skipped


def slugify(text: str, *, max_len: int = 48) -> str:
    text = text.lower().strip()
    text = re.sub(r"[`$\\'\"(){}\[\];:&|<>!?*/]", " ", text)
    text = SAFE_BRANCH_RE.sub("-", text)
    text = re.sub(r"-+", "-", text).strip("-._/")
    return (text or "work")[:max_len].strip("-") or "work"


def branch_name_for_issue(issue: dict[str, Any], *, run_id: str | None = None) -> str:
    number = int(issue.get("number") or 0)
    title = slugify(str(issue.get("title") or "work"), max_len=42)
    suffix = slugify(run_id or "run", max_len=24)
    return f"smactorio/issue-{number}-{title}-{suffix}"


def claim_marker(*, run_id: str, expires_at: str, branch: str) -> str:
    payload = json.dumps({"run_id": run_id, "expires_at": expires_at, "branch": branch}, sort_keys=True, separators=(",", ":"))
    return f"<!-- smactorio:claim {payload} -->"


def parse_claim_marker(text: str) -> dict[str, Any]:
    match = CLAIM_RE.search(text or "")
    if not match:
        return {}
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def normalize_worker_command(command: Sequence[str]) -> list[str]:
    if isinstance(command, str):
        raise TypeError("worker command must be argv list, not a shell string")
    normalized = [str(part) for part in command]
    if not normalized or any(not part or "\x00" in part for part in normalized):
        raise ValueError("worker command must be a non-empty argv list of safe strings")
    return normalized


def sanitized_worker_env(*, base_env: dict[str, str] | None = None, worker_env: dict[str, str] | None = None) -> dict[str, str]:
    base = dict(base_env or os.environ)
    clean: dict[str, str] = {}
    keep_exact = {
        "HOME",
        "PATH",
        "LANG",
        "LC_ALL",
        "TZ",
        "USER",
        "LOGNAME",
        "SHELL",
        "PYTHONPATH",
        "VIRTUAL_ENV",
        "HERMES_HOME",
        "HERMES_INFERENCE_PROVIDER",
        "HERMES_INFERENCE_MODEL",
    }
    for key, value in base.items():
        upper = key.upper()
        if key in keep_exact:
            clean[key] = value
            continue
        if any(fragment in upper for fragment in SENSITIVE_ENV_FRAGMENTS):
            continue
        if upper.startswith(("AWS_", "GOOGLE_", "CLOUDFLARE_", "CF_", "GITHUB_", "GH_", "NPM_")):
            continue
        if upper.startswith("HERMES_"):
            clean[key] = value
            continue
        clean[key] = value
    clean.update(worker_env or {})
    return clean


def _bwrap_bind_parents(path: Path) -> list[str]:
    parents: list[str] = []
    current = Path("/")
    for part in path.resolve().parts[1:-1]:
        current = current / part
        parents.extend(["--dir", str(current)])
    return parents


def _bwrap_ro_bind_path(args: list[str], path: str | Path) -> None:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        return
    candidate = candidate.resolve()
    args.extend(_bwrap_bind_parents(candidate))
    args.extend(["--ro-bind", str(candidate), str(candidate)])


def _hermes_wrapper_targets(wrapper: Path) -> list[Path]:
    """Return executable targets referenced by simple local Hermes wrappers."""
    if not wrapper.is_file():
        return []
    try:
        text = wrapper.read_text(encoding="utf-8", errors="ignore")[:1000]
    except OSError:
        return []
    targets: list[Path] = []
    for match in re.finditer(r"exec\s+[\"'](?P<target>/[^\"']+)[\"']", text):
        targets.append(Path(match.group("target")))
    return targets


def _executable_bind_roots(executable: Path) -> list[Path]:
    """Return paths that make a local console-script executable usable."""
    roots = [executable]
    resolved = executable.resolve()
    roots.append(resolved)
    parts = resolved.parts
    if ".venv" in parts:
        venv_index = parts.index(".venv")
        if venv_index > 1:
            roots.append(Path(*parts[:venv_index]))
    elif "venv" in parts:
        venv_index = parts.index("venv")
        if venv_index > 1:
            roots.append(Path(*parts[:venv_index]))
    return roots


def _host_tool_readonly_binds(args: list[str]) -> None:
    """Bind just enough host tooling for Hermes/Python to start in the sandbox."""
    paths: list[Path | str] = [
        "/home/leonb/hermes",
        "/home/leonb/projects/hermes-agent",
        "/home/leonb/.local/bin",
        "/home/leonb/.local/share/uv",
        "/home/leonb/.cache/uv",
        "/home/leonb/.nvm/versions/node",
    ]
    hermes = shutil.which("hermes")
    if hermes:
        hermes_path = Path(hermes)
        paths.extend(_executable_bind_roots(hermes_path))
        for target in _hermes_wrapper_targets(hermes_path):
            paths.extend(_executable_bind_roots(target))
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        _bwrap_ro_bind_path(args, path)


def sandbox_worker_command(command: Sequence[str], *, worktree: Path, runtime_dir: Path, env: dict[str, str]) -> tuple[list[str], dict[str, str]]:
    """Return a bubblewrap command that hides Leon's home and GitHub credentials.

    The worker receives only the isolated worktree, a temporary HOME, and an
    optional dedicated HERMES_HOME.  The canonical home, ~/.ssh, ~/.config/gh,
    and the foreman's GitHub token env are not mounted into the sandbox.
    """
    bwrap = shutil.which("bwrap")
    if not bwrap:
        if os.environ.get("SMACTORIO_ALLOW_UNSANDBOXED_WORKER") == "1":
            return list(command), env
        raise SmactorioError("bubblewrap is required for SmactorIO worker isolation")

    runtime_dir.mkdir(parents=True, exist_ok=True)
    worker_home = runtime_dir / "worker-home"
    worker_home.mkdir(parents=True, exist_ok=True)
    worktree = worktree.resolve()
    hermes_home = Path(env.get("HERMES_HOME") or os.environ.get("SMACTORIO_WORKER_HERMES_HOME") or (runtime_dir / "hermes-home")).expanduser().resolve()
    hermes_home.mkdir(parents=True, exist_ok=True)
    env = dict(env)
    env["HOME"] = str(worker_home)
    env["HERMES_HOME"] = str(hermes_home)
    for forbidden in ("GH_TOKEN", "GITHUB_TOKEN", "SSH_AUTH_SOCK", "GIT_ASKPASS"):
        env.pop(forbidden, None)

    bind_args: list[str] = [
        bwrap,
        "--die-with-parent",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/lib",
        "/lib",
    ]
    if Path("/lib64").exists():
        bind_args.extend(["--ro-bind", "/lib64", "/lib64"])
    for optional in ("/etc/ssl", "/etc/ca-certificates", "/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf"):
        if Path(optional).exists():
            bind_args.extend(["--ro-bind", optional, optional])
    _host_tool_readonly_binds(bind_args)
    bind_args.extend(_bwrap_bind_parents(worktree))
    bind_args.extend(["--bind", str(worktree), str(worktree)])
    bind_args.extend(_bwrap_bind_parents(worker_home))
    bind_args.extend(["--bind", str(worker_home), str(worker_home)])
    bind_args.extend(_bwrap_bind_parents(hermes_home))
    bind_args.extend(["--bind", str(hermes_home), str(hermes_home)])
    bind_args.extend([
        "--setenv",
        "HOME",
        str(worker_home),
        "--setenv",
        "HERMES_HOME",
        str(hermes_home),
        "--unsetenv",
        "GH_TOKEN",
        "--unsetenv",
        "GITHUB_TOKEN",
        "--unsetenv",
        "SSH_AUTH_SOCK",
        "--unsetenv",
        "GIT_ASKPASS",
        "--chdir",
        str(worktree),
    ])
    bind_args.extend(command)
    return bind_args, env


def verification_env() -> dict[str, str]:
    return sanitized_worker_env(base_env=dict(os.environ), worker_env={"GH_TOKEN": "", "GITHUB_TOKEN": "", "SSH_AUTH_SOCK": "", "GIT_ASKPASS": ""})


def run_trusted_preflight(
    repo_root: Path,
    *,
    base: str,
    policy: smactorio_policy.SmactorioPolicy,
    trusted_files: Sequence[str] | None = None,
    trusted_signal_hub: Path = PROJECT_ROOT,
) -> list[str]:
    """Fail before worker launch if trusted foreman guardrails are unavailable.

    The worker never gets to define these commands. Signal Hub work keeps the
    historical behavior of requiring guardrails inside the managed repo. Other
    repo lanes (for example Leon's Hermes fork) use the trusted Signal Hub
    checkout that launched the foreman, not worker-controlled files.
    """
    repo_root = repo_root.resolve()
    trusted_files = tuple(trusted_files or policy.trusted_preflight_files or TRUSTED_PREFLIGHT_FILES)
    trusted_root = repo_root if policy.trusted_preflight_files_root == "repo" else trusted_signal_hub.resolve()
    missing = [rel for rel in trusted_files if not (trusted_root / rel).is_file()]
    if missing:
        raise SmactorioError("preflight missing trusted files: " + ", ".join(missing))
    repo_guard.assert_clean(repo_root)
    result = subprocess.run(
        ["git", "diff", "--check", f"origin/{base}...HEAD"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=verification_env(),
        timeout=policy.check_timeout_seconds,
    )
    if result.returncode != 0:
        raise SmactorioError("preflight baseline diff check failed:\n" + result.stdout[-2000:])
    return [
        "trusted guardrail files present: " + ", ".join(str(Path(trusted_root, rel)) for rel in trusted_files),
        f"baseline diff check clean against origin/{base}",
    ]


def path_is_allowed_for_repair(rel_path: str, allowed_prefixes: Sequence[str] | None = None) -> bool:
    prefixes = LOW_RISK_REPAIR_PREFIXES if allowed_prefixes is None else allowed_prefixes
    raw = rel_path.replace(os.sep, "/").replace("\\", "/")
    if raw.startswith("./"):
        raw = raw[2:]
    normalized = raw
    if not normalized or normalized.startswith("../") or normalized.startswith("/") or "/../" in normalized or normalized == "..":
        return False
    if normalized in PROTECTED_SMACTORIO_RUNTIME_PATHS or normalized in TRUSTED_PREFLIGHT_FILES:
        return False
    for prefix in prefixes:
        clean_prefix = prefix.replace(os.sep, "/").lstrip("/")
        if normalized == clean_prefix.rstrip("/") or normalized.startswith(clean_prefix):
            return True
    return False


def lock_down_worker_git_metadata(worktree: Path) -> None:
    """Remove worker-controlled git hooks/config before foreman privileged steps."""
    git_dir = worktree / ".git"
    if not git_dir.is_dir():
        raise SmactorioError(f"worker checkout has no private .git directory: {worktree}")
    hooks_dir = git_dir / "hooks"
    if hooks_dir.exists():
        shutil.rmtree(hooks_dir)
    hooks_dir.mkdir(parents=True, exist_ok=True)
    # Rewrite local config from scratch before invoking git.  This wipes
    # include/includeIf, fsmonitor, hooksPath, credential helpers, URL rewrites,
    # and any other worker-controlled executable git settings.
    (git_dir / "config").write_text(
        textwrap.dedent(
            """
            [core]
                repositoryformatversion = 0
                filemode = true
                bare = false
                logallrefupdates = true
            [user]
                name = SmactorIO
                email = smactorio@users.noreply.github.com
            [commit]
                gpgsign = false
            """
        ).lstrip(),
        encoding="utf-8",
    )
    repo_guard.run_git(worktree, ["config", "user.name", "SmactorIO"], timeout=60)
    repo_guard.run_git(worktree, ["config", "user.email", "smactorio@users.noreply.github.com"], timeout=60)
    repo_guard.run_git(worktree, ["config", "commit.gpgsign", "false"], timeout=60)


def run_git_locked(worktree: Path, args: Sequence[str], *, timeout: int = 120, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    safe_hooks = worktree / ".git" / "hooks"
    safe_hooks.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "-c", f"core.hooksPath={safe_hooks}", "-c", "commit.gpgsign=false", *args],
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise SmactorioError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def create_worker_checkout(source_repo: Path, checkout: Path, *, branch: str, base: str) -> None:
    """Create a disposable full clone for the worker.

    Linked git worktrees require metadata under the parent repo's `.git`, which
    is intentionally not exposed inside the worker sandbox.  A full local clone
    gives the worker a self-contained `.git` directory while keeping the
    canonical checkout free of temporary local branches.
    """
    source_repo = source_repo.resolve()
    checkout = checkout.resolve()
    if checkout.exists():
        raise SmactorioError(f"worker checkout already exists: {checkout}")
    checkout.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--no-local", "--branch", base, "--single-branch", str(source_repo), str(checkout)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    if result.returncode != 0:
        raise SmactorioError(f"worker checkout clone failed: {result.stderr[-2000:] or result.stdout[-2000:]}")
    repo_guard.run_git(checkout, ["switch", "-c", branch], timeout=120)
    repo_guard.run_git(checkout, ["config", "user.name", "SmactorIO"], timeout=60)
    repo_guard.run_git(checkout, ["config", "user.email", "smactorio@users.noreply.github.com"], timeout=60)
    repo_guard.run_git(checkout, ["config", "commit.gpgsign", "false"], timeout=60)
    repo_guard.assert_clean(checkout)


def remove_worker_checkout(checkout: Path) -> None:
    shutil.rmtree(checkout, ignore_errors=True)


def default_worker_command(prompt: str) -> list[str]:
    hermes = shutil.which("hermes") or "/home/leonb/.local/bin/hermes"
    return [
        hermes,
        "--yolo",
        "--toolsets",
        "terminal,file",
        "--skills",
        "test-driven-development,github-pr-workflow,systematic-debugging",
        "-z",
        prompt,
    ]


def default_reviewer_command(prompt: str) -> list[str]:
    hermes = shutil.which("hermes") or "/home/leonb/.local/bin/hermes"
    return [
        hermes,
        "--yolo",
        "--toolsets",
        "terminal,file",
        "--skills",
        "requesting-code-review,systematic-debugging",
        "-z",
        prompt,
    ]


def default_worker_preflight_command() -> list[str]:
    return default_worker_command("Return exactly SMACTORIO_PREFLIGHT_OK. Do not call tools.")


def run_worker_preflight(
    worktree: Path,
    *,
    runtime_dir: Path,
    command_runner: CommandRunner,
    policy: smactorio_policy.SmactorioPolicy,
) -> str | None:
    """Smoke-test the exact sandboxed worker before claiming a GitHub issue."""
    if os.environ.get("SMACTORIO_SKIP_WORKER_PREFLIGHT") == "1":
        return None
    command = default_worker_preflight_command()
    env = sanitized_worker_env(worker_env={"SMACTORIO_PREFLIGHT": "1"})
    result_command, env = sandbox_worker_command(command, worktree=worktree, runtime_dir=runtime_dir / "preflight", env=env)
    result = command_runner(result_command, cwd=str(worktree), env=env, timeout=policy.worker_preflight_timeout_seconds)
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    if result.returncode != 0:
        return f"worker preflight failed ({result.returncode}): {output[-1800:]}"
    if "SMACTORIO_PREFLIGHT_OK" not in output:
        return f"worker preflight did not return expected marker: {output[-1800:]}"
    return None


def changed_paths_since_base(worktree: Path, *, base: str) -> list[str]:
    result = run_git_locked(worktree, ["diff", "--name-only", f"origin/{base}...HEAD"], timeout=120)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def assert_worker_material_change(worktree: Path, *, base: str, policy: smactorio_policy.SmactorioPolicy) -> list[str]:
    changed = changed_paths_since_base(worktree, base=base)
    material = [path for path in changed if not any(path.startswith(prefix) for prefix in policy.foreman_artifact_prefixes)]
    if not material:
        raise SmactorioError("worker produced only SmactorIO verification/artifact files; refusing to create PR")
    return material


def review_prompt(issue: dict[str, Any], *, repo: str, branch: str, head: str) -> str:
    return textwrap.dedent(
        f"""
        You are the independent SmactorIO verifier for GitHub issue #{issue.get('number')}: {issue.get('title')}.

        Review only. Do not modify files, commit, push, edit labels, open PRs, or merge.
        Verify whether the work in this checkout satisfies the issue safely and within scope.

        Repository: {repo}
        Branch: {branch}
        Head: {head}
        Issue URL: {issue.get('url')}

        Required review:
        - Inspect the local diff against origin/main.
        - Check security/scope risks, especially secrets, runtime state, broad raw dumps, and unsafe paths.
        - Check that tests/verification evidence are meaningful for the issue.
        - If there is any blocker, explain it and do not emit a pass verdict.

        Final line contract:
        - Emit exactly `SMACTORIO_VERDICT: PASS` only if there are no blockers.
        - Otherwise emit `SMACTORIO_VERDICT: BLOCK` and list blockers.
        """
    ).strip()


def run_independent_review(
    worktree: Path,
    *,
    issue: dict[str, Any],
    repo: str,
    branch: str,
    runtime_dir: Path,
    command_runner: CommandRunner,
    policy: smactorio_policy.SmactorioPolicy,
    reviewer_command: Sequence[str] | None = None,
) -> str:
    before_head = repo_guard.current_head(worktree)
    before_status = repo_guard.status_porcelain(worktree)
    prompt = review_prompt(issue, repo=repo, branch=branch, head=before_head)
    command = normalize_worker_command(reviewer_command) if reviewer_command is not None else default_reviewer_command(prompt)
    env = sanitized_worker_env(worker_env={"SMACTORIO_REVIEW_ONLY": "1", "SMACTORIO_REPO": repo, "SMACTORIO_BRANCH": branch})
    result_command, env = sandbox_worker_command(command, worktree=worktree, runtime_dir=runtime_dir / "review", env=env)
    result = command_runner(result_command, cwd=str(worktree), env=env, timeout=policy.review_timeout_seconds)
    output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    if result.returncode != 0:
        raise SmactorioError(f"independent review failed ({result.returncode}):\n{output[-4000:]}")
    lock_down_worker_git_metadata(worktree)
    after_status = repo_guard.status_porcelain(worktree)
    after_head = repo_guard.current_head(worktree)
    if after_head != before_head or after_status != before_status:
        raise SmactorioError("independent review modified the checkout; refusing to merge")
    if "SMACTORIO_VERDICT: PASS" not in output:
        raise SmactorioError(f"independent review did not pass:\n{output[-4000:]}")
    if "SMACTORIO_VERDICT: BLOCK" in output:
        raise SmactorioError(f"independent review blocked:\n{output[-4000:]}")
    return output[-4000:]


def worker_prompt(issue: dict[str, Any], *, repo: str, branch: str) -> str:
    body = str(issue.get("body") or "").strip()
    labels = sorted(smactorio_policy.label_names(issue))
    outcome_example = json.dumps(
        {
            "schema_version": 1,
            "outcome": "ALREADY_SATISFIED",
            "issue_number": issue.get("number"),
            "run_id": "$SMACTORIO_RUN_ID",
            "acceptance_criteria": [{"criterion": "...", "status": "satisfied", "evidence": "..."}],
            "commands": [{"command": "signal-hub/scripts/run_tests.sh ...", "exit_code": 0, "summary": "..."}],
            "files_inspected": ["signal-hub/..."],
            "base_sha": "...",
            "diff_status": "clean",
            "commit_count": 0,
        },
        separators=(",", ":"),
    )
    return textwrap.dedent(
        f"""
        You are the SmactorIO worker for GitHub issue #{issue.get('number')}: {issue.get('title')}.

        Leon is not the developer. You own the implementation work in this isolated worktree.
        Work only in this worktree and keep repo discipline exceptional.

        Repository: {repo}
        Branch: {branch}
        Labels: {', '.join(labels) if labels else '(none)'}
        Issue URL: {issue.get('url')}

        Issue body:
        {body or '(empty)'}

        Required worker contract:
        - Do not ask Leon questions. If acceptance is ambiguous, implement the smallest safe interpretation and record evidence.
        - Do not push, open PRs, merge PRs, edit GitHub labels, or close issues. The SmactorIO foreman owns GitHub writes.
        - Do not create stashes. Do not leave uncommitted changes. Do not leave orphan branches.
        - Do not commit runtime state, secrets, DBs, logs, caches, backups, .env files, credentials, tokens, or broad raw dumps.
        - Use strict TDD for behavior changes: write failing tests first, make them pass, then refactor.
        - Run targeted checks and the repository-specific verification suite where relevant.
        - Commit the completed implementation locally with a clear conventional commit message.
        - For normal implementation that creates one or more commits, do not emit smactorio-outcome-json and do not emit any SMACTORIO_OUTCOME_JSON_V1 sentinel; just summarize files changed and checks run.
        - If the issue is already satisfied by the existing base checkout, do not create commits. Verify every acceptance criterion against the existing base checkout, run relevant checks, and end with one fenced structured outcome block followed by the final sentinel line below.
        - Already-satisfied output format must be exactly one JSON block plus final sentinel, with no text after the sentinel:
          ```smactorio-outcome-json
          {outcome_example}
          ```
          SMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED
        - Final response should summarize files changed and checks run.
        """
    ).strip()


def final_nonempty_line(value: str | None) -> str:
    for line in reversed((value or "").splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return ""



def redact_operational_evidence(value: str, *, max_chars: int = MAX_COMMENT_BODY_CHARS) -> str:
    redacted = SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group('name')}=[REDACTED]", value or "")
    redacted = BEARER_HEADER_RE.sub("Authorization: Bearer [REDACTED]", redacted)
    redacted = GITHUB_SECRET_RE.sub("[REDACTED]", redacted)
    redacted = ABSOLUTE_PATH_RE.sub("[REDACTED_PATH]", redacted)
    if len(redacted) > max_chars:
        redacted = redacted[:max_chars].rstrip() + "\n[TRUNCATED]"
    return redacted


def parse_worker_outcome(result: subprocess.CompletedProcess[str], *, issue_number: int | None = None) -> dict[str, Any]:
    if result.returncode != 0:
        raise SmactorioError(f"worker outcome unavailable because worker exited {result.returncode}")
    stdout = result.stdout or ""
    matches = list(WORKER_OUTCOME_BLOCK_RE.finditer(stdout))
    if len(matches) != 1:
        raise SmactorioError(f"worker must emit exactly one smactorio-outcome-json block, found {len(matches)}")
    final_line = final_nonempty_line(stdout)
    if not final_line.startswith(WORKER_OUTCOME_SENTINEL_PREFIX):
        raise SmactorioError("worker structured outcome missing final SMACTORIO_OUTCOME_JSON_V1 sentinel")
    try:
        payload = json.loads(matches[0].group("payload"))
    except json.JSONDecodeError as exc:
        raise SmactorioError(f"worker structured outcome JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise SmactorioError("worker structured outcome JSON must be an object")
    if payload.get("schema_version") != 1:
        raise SmactorioError("worker structured outcome schema_version must be 1")
    outcome = str(payload.get("outcome") or "")
    if not outcome:
        raise SmactorioError("worker structured outcome missing outcome")
    if outcome not in STRUCTURED_WORKER_OUTCOMES:
        raise SmactorioError(f"worker structured outcome is not supported: {outcome}")
    expected_sentinel = f"{WORKER_OUTCOME_SENTINEL_PREFIX} {outcome}"
    if final_line != expected_sentinel:
        raise SmactorioError(f"worker structured outcome sentinel mismatch: expected {expected_sentinel!r}, got {final_line!r}")
    if issue_number is not None:
        try:
            reported_issue = int(payload.get("issue_number"))
        except (TypeError, ValueError) as exc:
            raise SmactorioError("worker structured outcome issue_number is missing or invalid") from exc
        if reported_issue != issue_number:
            raise SmactorioError(f"worker structured outcome issue mismatch: expected {issue_number}, got {reported_issue}")
    if outcome == "ALREADY_SATISFIED":
        if payload.get("diff_status") != "clean":
            raise SmactorioError("ALREADY_SATISFIED outcome requires diff_status=clean")
        if int(payload.get("commit_count") or 0) != 0:
            raise SmactorioError("ALREADY_SATISFIED outcome requires commit_count=0")
        if not payload.get("acceptance_criteria"):
            raise SmactorioError("ALREADY_SATISFIED outcome requires acceptance_criteria evidence")
        if not payload.get("commands"):
            raise SmactorioError("ALREADY_SATISFIED outcome requires command evidence")
    return payload


def worker_reported_already_satisfied(result: subprocess.CompletedProcess[str], *, issue_number: int | None = None) -> bool:
    try:
        return parse_worker_outcome(result, issue_number=issue_number).get("outcome") == "ALREADY_SATISFIED"
    except SmactorioError:
        return False


def worker_emitted_structured_outcome(result: subprocess.CompletedProcess[str]) -> bool:
    stdout = result.stdout or ""
    return bool(WORKER_OUTCOME_BLOCK_RE.search(stdout) or final_nonempty_line(stdout).startswith(WORKER_OUTCOME_SENTINEL_PREFIX))


def worker_terminal_outcome_should_be_parsed(result: subprocess.CompletedProcess[str], *, material_paths: Sequence[str] | None) -> bool:
    """Only no-material-change terminal worker outcomes are parsed as control messages.

    A material worker commit is the source of truth for the normal PR path. If a
    model accidentally echoes the already-satisfied sentinel after producing a
    real material commit, the foreman should continue through validation instead
    of entering a simple contract-block loop.
    """
    if material_paths:
        return False
    return worker_emitted_structured_outcome(result)


def material_paths_or_contract_violation(
    worktree: Path,
    *,
    base: str,
    policy: smactorio_policy.SmactorioPolicy,
    worker_result: subprocess.CompletedProcess[str],
) -> list[str]:
    try:
        return assert_worker_material_change(worktree, base=base, policy=policy)
    except SmactorioError as exc:
        if worker_emitted_structured_outcome(worker_result):
            raise SmactorioError(
                "worker structured outcome contract violation: worker emitted a terminal structured outcome "
                "but did not produce a material implementation commit"
            ) from exc
        raise


def classify_failure(message: str) -> str:
    lowered = (message or "").lower()
    if "worker failed" in lowered:
        return "worker_failed"
    if "verification failed" in lowered:
        return "verification_failed"
    if "pr checks" in lowered or "status context" in lowered or "check not" in lowered:
        return "ci_failed"
    if "pr merge" in lowered or "merge state" in lowered:
        return "merge_failed"
    if "structured outcome" in lowered or "already_satisfied" in lowered and "contradictory" in lowered:
        return "contract_contradiction"
    return "smactorio_error"


def failure_signature(message: str) -> str:
    redacted = redact_operational_evidence(message, max_chars=2000).lower()
    normalized = re.sub(r"[0-9a-f]{7,64}", "<sha>", redacted)
    normalized = re.sub(r"run-[a-z0-9._-]+", "<run>", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    digest = hashlib.sha256(normalized.encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"{classify_failure(message)}:{digest}"


def issue_context_fingerprint(issue: dict[str, Any], *, base_sha: str | None) -> str:
    labels = sorted(label for label in smactorio_policy.label_names(issue) if not label.startswith("smactorio:"))
    payload = {
        "base_sha": base_sha or "",
        "body": str(issue.get("body") or ""),
        "labels": labels,
        "number": int(issue.get("number") or 0),
        "title": str(issue.get("title") or ""),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8", errors="replace")).hexdigest()[:16]
    return f"ctx:{digest}"


def scoped_failure_signature(issue: dict[str, Any], *, base_sha: str | None, message: str) -> str:
    return f"{issue_context_fingerprint(issue, base_sha=base_sha)}:{failure_signature(message)}"


def ensure_label(repo: str, name: str, *, color: str, description: str, command_runner: CommandRunner) -> None:
    result = command_runner(
        ["gh", "label", "create", name, "--repo", repo, "--color", color, "--description", description, "--force"],
        timeout=120,
    )
    if result.returncode != 0:
        raise SmactorioError(f"failed to ensure label {name}: {result.stderr or result.stdout}")


def issue_comment(repo: str, issue_number: int, body: str, *, command_runner: CommandRunner) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        body_file = Path(handle.name)
        handle.write(redact_operational_evidence(body))
    try:
        run_checked(["gh", "issue", "comment", str(issue_number), "--repo", repo, "--body-file", str(body_file)], command_runner=command_runner, timeout=120)
    finally:
        body_file.unlink(missing_ok=True)


def close_issue(repo: str, issue_number: int, *, command_runner: CommandRunner) -> None:
    """Close a completed SmactorIO issue idempotently.

    PR bodies still include a GitHub closing keyword, but the foreman must not
    rely on GitHub parsing Markdown to clear completed work from the open issue
    queue. Explicit close makes completion state first-class.
    """
    result = command_runner(["gh", "issue", "close", str(issue_number), "--repo", repo], timeout=120)
    if result.returncode == 0:
        return
    combined = f"{result.stdout}\n{result.stderr}".lower()
    if "already" in combined and "closed" in combined:
        return
    raise SmactorioError(f"failed to close issue #{issue_number}: {result.stderr or result.stdout}")


def edit_issue_labels(repo: str, issue_number: int, *, add: Sequence[str] = (), remove: Sequence[str] = (), command_runner: CommandRunner) -> None:
    argv = ["gh", "issue", "edit", str(issue_number), "--repo", repo]
    for label in add:
        argv.extend(["--add-label", label])
    for label in remove:
        argv.extend(["--remove-label", label])
    if len(argv) > 6:
        run_checked(argv, command_runner=command_runner, timeout=120)


def _parse_utc_timestamp(value: str) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def latest_claim_for_issue(repo: str, issue_number: int, *, command_runner: CommandRunner) -> dict[str, Any]:
    result = run_checked(
        ["gh", "issue", "view", str(issue_number), "--repo", repo, "--json", "comments"],
        command_runner=command_runner,
        timeout=120,
    )
    payload = json.loads(result.stdout or "{}")
    comments = payload.get("comments") or []
    for comment in reversed(comments):
        marker = parse_claim_marker(str((comment or {}).get("body") or ""))
        if marker:
            return marker
    return {}


def recover_stale_claims(repo: str, issues: list[dict[str, Any]], *, policy: smactorio_policy.SmactorioPolicy, command_runner: CommandRunner) -> bool:
    """Remove expired claim labels so crashed runs do not block work forever."""
    recovered = False
    now = dt.datetime.now(dt.timezone.utc)
    for issue in issues:
        labels = smactorio_policy.label_names(issue)
        if policy.claim_label not in labels:
            continue
        issue_number = int(issue.get("number") or 0)
        marker = latest_claim_for_issue(repo, issue_number, command_runner=command_runner)
        expires = _parse_utc_timestamp(str(marker.get("expires_at") or ""))
        if expires is not None and expires > now:
            continue
        edit_issue_labels(repo, issue_number, remove=[policy.claim_label], command_runner=command_runner)
        issue_comment(
            repo,
            issue_number,
            f"SmactorIO recovered an expired claim and returned this issue to the queue.\n\nPrevious claim: `{json.dumps(marker, sort_keys=True)}`",
            command_runner=command_runner,
        )
        recovered = True
    return recovered


def _issue_would_be_eligible_without_retryable_blocked_label(issue: dict[str, Any], policy: smactorio_policy.SmactorioPolicy) -> bool:
    labels = smactorio_policy.label_names(issue)
    if policy.blocked_label not in labels:
        return False
    if policy.needs_attention_label in labels or policy.done_label in labels or policy.claim_label in labels:
        return False
    remaining_labels = labels - {policy.blocked_label}
    if not policy.required_labels <= remaining_labels:
        return False
    other_blockers = (remaining_labels & policy.blocked_labels) - {policy.blocked_label}
    return not other_blockers


def issue_has_terminal_retry_exhaustion(
    state_db: Path,
    *,
    repo: str,
    issue: dict[str, Any],
    base_sha: str,
    policy: smactorio_policy.SmactorioPolicy,
) -> bool:
    try:
        issue_number = int(issue.get("number") or 0)
    except (TypeError, ValueError):
        return False
    if issue_number <= 0:
        return False
    try:
        conn = runtime_state.init_db(state_db)
    except Exception:
        return True
    try:
        context = issue_context_fingerprint(issue, base_sha=base_sha)
        return (
            runtime_state.exhausted_issue_attempt(
                conn,
                repo=repo,
                issue_number=issue_number,
                max_attempts=policy.max_attempts_per_failure_signature,
                failure_signature_prefix=f"{context}:",
            )
            is not None
        )
    finally:
        conn.close()


def recover_retryable_blocked_issues(
    repo: str,
    issues: list[dict[str, Any]],
    *,
    policy: smactorio_policy.SmactorioPolicy,
    command_runner: CommandRunner,
    terminal_issue_predicate: Callable[[dict[str, Any]], bool] | None = None,
) -> bool:
    """Return retryable smactorio:blocked issues to the queue.

    Non-terminal worker/foreman failures set smactorio:blocked so operators can
    see the failure.  They should not become permanent limbo once the issue is
    still otherwise eligible.  True terminal blockers also carry
    smactorio:needs-attention, which this recovery deliberately leaves alone.
    """
    recovered = False
    for issue in issues:
        if not _issue_would_be_eligible_without_retryable_blocked_label(issue, policy):
            continue
        if terminal_issue_predicate is not None and terminal_issue_predicate(issue):
            continue
        issue_number = int(issue.get("number") or 0)
        if issue_number <= 0:
            continue
        edit_issue_labels(repo, issue_number, remove=[policy.blocked_label], command_runner=command_runner)
        issue_comment(
            repo,
            issue_number,
            "SmactorIO recovered a retryable blocked label and returned this issue to the autonomous queue. "
            "Terminal true-blocked issues keep smactorio:needs-attention and are not auto-retried.",
            command_runner=command_runner,
        )
        recovered = True
    return recovered


def plan_once(
    *,
    repo: str,
    dry_run: bool,
    command_runner: CommandRunner = default_command_runner,
    policy: smactorio_policy.SmactorioPolicy | None = None,
) -> dict[str, Any]:
    policy = policy or smactorio_policy.default_policy()
    issues = load_issues(repo, command_runner=command_runner, limit=policy.max_open_issues)
    selected = select_issue(issues, policy)
    if selected is None:
        return {"status": "no_work", "repo": repo, "issue_count": len(issues), "skipped_issues": skipped_issue_summaries(issues, policy)}
    rid = run_id()
    return {
        "status": "dry_run" if dry_run else "planned",
        "repo": repo,
        "selected_issue_number": int(selected["number"]),
        "selected_issue_title": selected.get("title"),
        "selected_issue_url": selected.get("url"),
        "branch": branch_name_for_issue(selected, run_id=rid),
        "run_id": rid,
    }


def write_changed_paths(worktree: Path, base_ref: str) -> Path:
    paths = repo_guard.changed_paths(worktree, base_ref)
    path_file = Path("/tmp/smactorio-changed-paths.txt")
    path_file.write_text("\n".join(paths) + ("\n" if paths else ""), encoding="utf-8")
    return path_file


def normalize_repo_path(raw: str) -> str | None:
    path = (raw or "").replace(os.sep, "/").replace("\\", "/").strip()
    if not path or path.startswith("/") or path.startswith("../") or "/../" in path or path == ".." or "://" in path:
        return None
    while path.startswith("./"):
        path = path[2:]
    return path


def _matches_policy_prefix(path: str, prefix: str) -> bool:
    clean = normalize_repo_path(prefix.rstrip("/"))
    if not clean:
        return False
    return path == clean or path.startswith(clean.rstrip("/") + "/")


def _matches_policy_path(path: str, policy_path: str) -> bool:
    clean = normalize_repo_path(policy_path)
    if not clean:
        return False
    if path == clean:
        return True
    # Treat a root-level conftest.py ban as a ban on any nested pytest
    # collection hook. Upstream sync conflict recovery must not gain the
    # ability to alter test collection/bootstrap behavior implicitly.
    if clean == "conftest.py" and path.endswith("/conftest.py"):
        return True
    return False


def validate_changed_paths_for_policy(paths: Sequence[str], policy: smactorio_policy.SmactorioPolicy) -> None:
    findings: list[str] = []
    for raw in paths:
        path = normalize_repo_path(raw)
        if path is None:
            findings.append(f"{raw}: invalid or unsafe repository path")
            continue
        if any(_matches_policy_prefix(path, prefix) for prefix in policy.foreman_artifact_prefixes):
            continue
        if any(_matches_policy_path(path, forbidden) for forbidden in policy.forbidden_change_paths):
            findings.append(f"{path}: forbidden by repo policy")
            continue
        blocked_prefix = next((prefix for prefix in policy.forbidden_change_prefixes if _matches_policy_prefix(path, prefix)), None)
        if blocked_prefix:
            findings.append(f"{path}: forbidden by repo policy prefix {blocked_prefix}")
            continue
        if not policy.allowed_change_prefixes:
            findings.append(f"{path}: no repository policy prefixes are allowed")
            continue
        if not any(_matches_policy_prefix(path, prefix) for prefix in policy.allowed_change_prefixes):
            findings.append(f"{path}: outside allowed repo policy prefixes")
    if findings:
        raise SmactorioError("changed paths violate SmactorIO repo policy:\n" + "\n".join(findings[:40]))


def changed_secret_scan_targets(worktree: Path, changed_paths: Sequence[str]) -> list[Path]:
    targets: list[Path] = []
    for raw in changed_paths:
        path = normalize_repo_path(raw)
        if not path:
            continue
        candidate = worktree / path
        if candidate.is_file() and candidate.suffix.lower() in {".html", ".json", ".md", ".txt", ".py", ".yaml", ".yml", ".css", ".js", ".ts", ".tsx"}:
            targets.append(candidate)
    return targets


def _diff_check_output_is_trailing_whitespace_only(output: str) -> bool:
    diagnostics = 0
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("+", "-")):
            continue
        if ": trailing whitespace." in stripped or ": new blank line at EOF." in stripped:
            diagnostics += 1
            continue
        return False
    return diagnostics > 0


def _fix_diff_check_whitespace_bytes(data: bytes) -> bytes:
    fixed_lines: list[bytes] = []
    for line in data.splitlines(keepends=True):
        if line.endswith(b"\r\n"):
            fixed_lines.append(line[:-2].rstrip(b" \t") + b"\r\n")
        elif line.endswith(b"\n"):
            fixed_lines.append(line[:-1].rstrip(b" \t") + b"\n")
        else:
            fixed_lines.append(line.rstrip(b" \t"))
    while fixed_lines and fixed_lines[-1].rstrip(b"\r\n") == b"":
        fixed_lines.pop()
    return b"".join(fixed_lines)


def repair_worker_diff_check_whitespace(
    worktree: Path,
    *,
    base: str,
    allowed_prefixes: Sequence[str] = REPAIR_ALLOWED_PREFIXES,
) -> list[str]:
    """Amend the worker commit for safe git diff --check whitespace failures.

    The foreman should not terminally block on mechanical whitespace that Git
    itself can diagnose. Only plain trailing-whitespace diagnostics are fixed;
    conflict markers or other semantic diff-check failures remain fail-closed.
    Repairs are constrained to the same source prefixes that later path-scope
    verification allows, so a worker cannot get disallowed paths rewritten by
    trusted foreman code before the terminal scope check blocks them.
    """
    base_ref = f"origin/{base}"
    result = subprocess.run(
        ["git", "diff", "--check", f"{base_ref}...HEAD"],
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=verification_env(),
        timeout=120,
    )
    if result.returncode == 0:
        return []
    if not _diff_check_output_is_trailing_whitespace_only(result.stdout):
        return []

    root = worktree.resolve()
    repaired: list[str] = []
    for rel in repo_guard.changed_paths(worktree, base_ref):
        if not path_is_allowed_for_repair(rel, allowed_prefixes):
            continue
        candidate = (worktree / rel).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if not candidate.is_file():
            continue
        data = candidate.read_bytes()
        if b"\x00" in data:
            continue
        fixed = _fix_diff_check_whitespace_bytes(data)
        if fixed == data:
            continue
        candidate.write_bytes(fixed)
        repaired.append(rel)

    if not repaired:
        return []

    lock_down_worker_git_metadata(worktree)
    run_git_locked(worktree, ["add", "--", *repaired], timeout=120)
    run_git_locked(worktree, ["commit", "--amend", "--no-edit"], timeout=180)
    repo_guard.assert_clean(worktree)
    return repaired



SAFE_WORKER_GENERATED_SIDE_EFFECT_PREFIXES = ("signal-hub/public/",)


def porcelain_status_paths(status: str) -> list[str]:
    """Return paths mentioned by git porcelain v1 status lines."""
    paths: list[str] = []
    for line in status.splitlines():
        if not line.strip() or len(line) < 4:
            continue
        raw = line[3:].strip()
        if " -> " in raw:
            paths.extend(part.strip() for part in raw.split(" -> ", 1) if part.strip())
        elif raw:
            paths.append(raw)
    return paths


def is_safe_worker_generated_side_effect_path(path: str, policy: smactorio_policy.SmactorioPolicy | None = None) -> bool:
    prefixes = policy.safe_worker_generated_side_effect_prefixes if policy is not None else SAFE_WORKER_GENERATED_SIDE_EFFECT_PREFIXES
    return any(path.startswith(prefix) for prefix in prefixes)


def discard_worker_generated_side_effects(worktree: Path, policy: smactorio_policy.SmactorioPolicy | None = None) -> str:
    """Discard safe generated public-page drift left by the worker checkout.

    Worker agents sometimes run the same page builders/tests that the operating
    loop runs. Those commands refresh tracked `signal-hub/public/` HTML, but
    that output is deployment/cache material, not SmactorIO implementation work.
    Drop it before the hard cleanliness gate. Unknown source changes remain in
    place so the normal dirty-worktree blocker still preserves valuable work.
    """
    status = repo_guard.status_porcelain(worktree)
    if not status.strip():
        return ""
    paths = porcelain_status_paths(status)
    if not paths or any(not is_safe_worker_generated_side_effect_path(path, policy) for path in paths):
        return ""
    lock_down_worker_git_metadata(worktree)
    run_git_locked(worktree, ["reset", "--hard", "HEAD"], timeout=180)
    clean_pathspecs = list((policy.safe_worker_generated_side_effect_prefixes if policy is not None else SAFE_WORKER_GENERATED_SIDE_EFFECT_PREFIXES) or ())
    if clean_pathspecs:
        run_git_locked(worktree, ["clean", "-fd", "--", *clean_pathspecs], timeout=180)
    repo_guard.assert_clean(worktree)
    return status

def discard_verification_side_effects(worktree: Path, policy: smactorio_policy.SmactorioPolicy | None = None) -> str:
    """Restore successful verification commands back to committed HEAD.

    Some repository tests regenerate public files or bytecode caches. Verification
    may prove the code works, but those command side effects are not worker
    implementation and must not be accidentally committed or reviewed.
    """
    status = repo_guard.status_porcelain(worktree)
    if not status.strip():
        return ""
    lock_down_worker_git_metadata(worktree)
    run_git_locked(worktree, ["reset", "--hard", "HEAD"], timeout=180)
    clean_pathspecs = list((policy.discard_verification_side_effect_pathspecs if policy is not None else ("signal-hub", ".github/workflows")) or ())
    if clean_pathspecs:
        run_git_locked(worktree, ["clean", "-fd", "--", *clean_pathspecs], timeout=180)
    repo_guard.assert_clean(worktree)
    return status


def run_verification(worktree: Path, *, policy: smactorio_policy.SmactorioPolicy, base: str, trusted_signal_hub: Path = PROJECT_ROOT) -> list[str]:
    base_ref = f"origin/{base}"
    changed_paths = repo_guard.changed_paths(worktree, base_ref)
    changed_path_file = Path("/tmp/smactorio-changed-paths.txt")
    changed_path_file.write_text("\n".join(changed_paths) + ("\n" if changed_paths else ""), encoding="utf-8")
    validate_changed_paths_for_policy(changed_paths, policy)
    outputs: list[str] = []
    path_scope_argv = [
        "python3",
        str(trusted_signal_hub / "scripts" / "check_path_scope.py"),
        "--from-file",
        str(changed_path_file),
    ]
    for prefix in tuple(dict.fromkeys((*policy.allowed_change_prefixes, *policy.foreman_artifact_prefixes))):
        path_scope_argv.extend(["--allow-prefix", prefix])

    commands: list[tuple[list[str], Path]] = [
        (["git", "diff", "--check", f"origin/{base}...HEAD"], worktree),
        (path_scope_argv, worktree),
    ]
    if policy.secret_scan_changed_paths_only:
        scan_targets = changed_secret_scan_targets(worktree, changed_paths)
        if scan_targets:
            commands.append(
                (["python3", str(trusted_signal_hub / "scripts" / "scan_for_secrets.py"), *(str(path) for path in scan_targets)], worktree)
            )
        else:
            outputs.append("$ smactorio changed-file secret scan\nexit=0\nNo changed text files to scan.")
    elif policy.secret_scan_paths:
        commands.append(
            (
                ["python3", str(trusted_signal_hub / "scripts" / "scan_for_secrets.py"), *(str(worktree / rel) for rel in policy.secret_scan_paths)],
                worktree,
            )
        )
    for command in policy.verification_test_commands:
        cwd = worktree / policy.verification_test_cwd if policy.verification_test_cwd not in {"", "."} else worktree
        commands.append((list(command), cwd))

    lock_down_worker_git_metadata(worktree)
    for argv, cwd in commands:
        result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=verification_env(), timeout=policy.check_timeout_seconds)
        outputs.append(f"$ {' '.join(argv)}\nexit={result.returncode}\n{result.stdout[-2000:]}")
        if result.returncode != 0:
            raise SmactorioError("verification failed:\n" + outputs[-1])
    side_effects = discard_verification_side_effects(worktree, policy)
    if side_effects:
        outputs.append(
            "$ smactorio discard verification side effects\n"
            "exit=0\n"
            "Successful verification left generated/untracked worktree changes; discarded before commit/review:\n"
            + side_effects[-2000:]
        )
    return outputs


def write_verification_artifact(
    worktree: Path,
    *,
    issue: dict[str, Any],
    pr_url: str | None,
    checks: Sequence[str],
    rid: str,
    policy: smactorio_policy.SmactorioPolicy | None = None,
) -> Path:
    policy = policy or smactorio_policy.default_policy()
    date = utc_now()[:10]
    issue_number = int(issue["number"])
    artifact_prefix = policy.verification_artifact_prefixes[0] if policy.verification_artifact_prefixes else "signal-hub/docs/verification/"
    rel = Path(artifact_prefix) / f"{date}-smactorio-issue-{issue_number}-{slugify(rid, max_len=10)}.md"
    path = worktree / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    check_summary = "\n\n".join(f"```text\n{check.strip()}\n```" for check in checks)
    path.write_text(
        textwrap.dedent(
            f"""
            # SmactorIO Issue #{issue_number} Verification

            Run: `{rid}`
            Issue: {issue.get('url')}
            PR: {pr_url or '(created after this artifact)'}
            Timestamp: {utc_now()}

            ## Checks

            {check_summary}
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return rel


def commit_all(worktree: Path, message: str, policy: smactorio_policy.SmactorioPolicy | None = None) -> bool:
    policy = policy or smactorio_policy.default_policy()
    lock_down_worker_git_metadata(worktree)
    run_git_locked(worktree, ["add", "--", *policy.commit_pathspecs], timeout=120)
    status = repo_guard.status_porcelain(worktree)
    if not status_is_commit_worthy(status):
        return False
    run_git_locked(worktree, ["commit", "-m", message], timeout=180)
    return True


def status_is_commit_worthy(status: str) -> bool:
    return bool(status.strip())


def make_askpass(runtime_dir: Path) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    script = runtime_dir / "git-askpass.sh"
    script.write_text(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *Username*) printf '%s\\n' x-access-token ;;\n"
        "  *Password*) printf '%s\\n' \"$GITHUB_TOKEN\" ;;\n"
        "  *) printf '%s\\n' \"$GITHUB_TOKEN\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    script.chmod(0o700)
    return script


def token_git_env(runtime_dir: Path, *, base_env: dict[str, str] | None = None) -> dict[str, str]:
    token_env = dict(base_env or os.environ)
    if not token_env.get("GITHUB_TOKEN") and token_env.get("GH_TOKEN"):
        token_env["GITHUB_TOKEN"] = token_env["GH_TOKEN"]
    askpass = make_askpass(runtime_dir)
    token_env["GIT_ASKPASS"] = str(askpass)
    token_env["GIT_TERMINAL_PROMPT"] = "0"
    return token_env


def ensure_repo_seed_clone(repo_root: Path, *, repo: str, base: str, env: dict[str, str] | None = None) -> None:
    """Create the dedicated SmactorIO seed clone when a lane root is absent."""
    if (repo_root / ".git").exists():
        return
    if repo_root.exists() and any(repo_root.iterdir()):
        raise SmactorioError(f"seed clone path exists but is not a git repository and is not empty: {repo_root}")
    repo_root.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--branch", base, "--single-branch", f"https://github.com/{repo}.git", str(repo_root)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=300,
    )
    if result.returncode != 0:
        raise SmactorioError(f"seed clone failed for {repo}: {result.stderr[-2000:] or result.stdout[-2000:]}")


def push_branch(worktree: Path, *, repo: str, branch: str, env: dict[str, str] | None = None, runtime_dir: Path) -> None:
    token_env = token_git_env(runtime_dir, base_env={**os.environ, **(env or {})})
    url = f"https://github.com/{repo}.git"
    lock_down_worker_git_metadata(worktree)
    result = subprocess.run(
        ["git", "-c", f"core.hooksPath={worktree / '.git' / 'hooks'}", "-c", "commit.gpgsign=false", "push", url, f"HEAD:refs/heads/{branch}"],
        cwd=worktree,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=token_env,
        timeout=240,
    )
    if result.returncode != 0:
        raise SmactorioError(f"git push failed: {result.stderr[-2000:] or result.stdout[-2000:]}")


def delete_remote_branch(repo: str, branch: str, *, runtime_dir: Path) -> None:
    token_env = token_git_env(runtime_dir)
    subprocess.run(
        ["git", "push", f"https://github.com/{repo}.git", f":refs/heads/{branch}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=token_env,
        timeout=240,
        check=False,
    )


def build_pr_body(issue: dict[str, Any], *, body_extra: str) -> str:
    issue_number = int(issue["number"])
    return "\n".join(
        [
            f"SmactorIO completed issue #{issue_number}.",
            "",
            f"Issue: {issue.get('url')}",
            "",
            "Verification:",
            body_extra.strip(),
            "",
            f"Closes #{issue_number}",
        ]
    ).strip() + "\n"


def create_pr(repo: str, issue: dict[str, Any], *, branch: str, base: str, body_extra: str, command_runner: CommandRunner) -> tuple[int, str]:
    issue_number = int(issue["number"])
    body = build_pr_body(issue, body_extra=body_extra)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".md", delete=False) as handle:
        body_file = Path(handle.name)
        handle.write(body)
    try:
        result = run_checked(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--base",
                base,
                "--head",
                branch,
                "--title",
                f"smactorio: complete issue #{issue_number} - {issue.get('title')}",
                "--body-file",
                str(body_file),
            ],
            command_runner=command_runner,
            timeout=180,
        )
    finally:
        body_file.unlink(missing_ok=True)
    url = result.stdout.strip().splitlines()[-1]
    view = run_checked(["gh", "pr", "view", url, "--repo", repo, "--json", "number,url"], command_runner=command_runner, timeout=120)
    payload = json.loads(view.stdout)
    return int(payload["number"]), str(payload["url"])


def pr_checks_are_green(payload: dict[str, Any], *, expected_head: str | None = None, required_workflow_name: str = "signal-hub-guardrails") -> tuple[bool, str]:
    if payload.get("isDraft"):
        return False, "PR is draft"
    if expected_head and payload.get("headRefOid") != expected_head:
        return False, f"PR head changed: expected {expected_head}, got {payload.get('headRefOid')}"
    rollup = payload.get("statusCheckRollup") or []
    if not isinstance(rollup, list) or not rollup:
        return False, "no status checks reported"
    required_seen = False
    for check in rollup:
        if not isinstance(check, dict):
            return False, f"unexpected status check payload: {check!r}"
        name = str(check.get("name") or check.get("workflowName") or check.get("context") or "")
        workflow = str(check.get("workflowName") or "")
        context = str(check.get("context") or "")
        if required_workflow_name in {name, workflow, context}:
            required_seen = True
        state = str(check.get("state") or "").upper()
        status = str(check.get("status") or "").upper()
        conclusion = str(check.get("conclusion") or "").upper()
        if state and state != "SUCCESS":
            return False, f"status context not successful: {name or context} state={state}"
        if status and status != "COMPLETED":
            return False, f"check not complete: {name} status={status} conclusion={conclusion}"
        if conclusion and conclusion != "SUCCESS":
            return False, f"check not successful: {name} status={status} conclusion={conclusion}"
        if not state and not status and not conclusion:
            return False, f"check has no terminal state: {name}"
    if not required_seen:
        return False, f"required workflow not seen: {required_workflow_name}"
    if payload.get("mergeStateStatus") not in {"CLEAN", "HAS_HOOKS"}:
        return False, f"merge state is not clean: {payload.get('mergeStateStatus')}"
    return True, "checks green"


def _pr_check_failure_is_terminal(reason: str) -> bool:
    terminal_prefixes = (
        "PR is draft",
        "PR head changed",
        "status context not successful",
        "check not successful",
        "check has no terminal state",
        "unexpected status check payload",
    )
    return reason.startswith(terminal_prefixes)


def wait_for_pr_checks(
    repo: str,
    pr_number: int,
    *,
    command_runner: CommandRunner,
    expected_head: str | None = None,
    timeout_seconds: int = 1800,
    poll_interval_seconds: float = 10.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_payload = "{}"
    last_reason = "not checked"
    while True:
        view = run_checked(
            ["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", "mergeStateStatus,statusCheckRollup,isDraft,headRefOid"],
            command_runner=command_runner,
            timeout=120,
        )
        last_payload = view.stdout
        payload = json.loads(view.stdout)
        ok, reason = pr_checks_are_green(payload, expected_head=expected_head)
        if ok:
            return
        last_reason = reason
        if _pr_check_failure_is_terminal(reason):
            raise SmactorioError(f"PR checks not green/fresh: {reason}\n{view.stdout}")
        if time.monotonic() >= deadline:
            raise SmactorioError(f"PR checks not green/fresh after waiting: {last_reason}\n{last_payload}")
        time.sleep(poll_interval_seconds)


def merge_pr(repo: str, pr_number: int, *, command_runner: CommandRunner, expected_head: str | None = None) -> tuple[str, str]:
    argv = ["gh", "pr", "merge", str(pr_number), "--repo", repo, "--squash", "--delete-branch"]
    if expected_head:
        argv.extend(["--match-head-commit", expected_head])
    result = command_runner(argv, timeout=300)
    if result.returncode != 0:
        raise SmactorioError(f"PR merge failed without using admin override: {result.stderr or result.stdout}")
    view = run_checked(
        ["gh", "pr", "view", str(pr_number), "--repo", repo, "--json", "url,mergeCommit,state,mergedAt"],
        command_runner=command_runner,
        timeout=120,
    )
    payload = json.loads(view.stdout)
    if payload.get("state") != "MERGED":
        raise SmactorioError(f"PR did not reach merged state: {payload}")
    merge_commit = (payload.get("mergeCommit") or {}).get("oid") or ""
    return str(payload.get("url") or ""), str(merge_commit)


def complete_issue(
    repo: str,
    issue_number: int,
    *,
    pr_url: str,
    merge_commit: str,
    artifact_rel: Path,
    rid: str,
    policy: smactorio_policy.SmactorioPolicy,
    command_runner: CommandRunner,
) -> None:
    issue_comment(
        repo,
        issue_number,
        textwrap.dedent(
            f"""
            SmactorIO completed this issue.

            PR: {pr_url}
            Merge commit: `{merge_commit}`
            Verification artifact: `{artifact_rel}`
            Run: `{rid}`

            Checks:
            - local verification passed
            - independent review passed
            - PR checks passed before merge
            - PR merged by SmactorIO foreman with head-SHA match
            - issue closed by SmactorIO foreman
            """
        ).strip(),
        command_runner=command_runner,
    )
    edit_issue_labels(repo, issue_number, add=[policy.done_label], remove=[policy.claim_label, policy.blocked_label], command_runner=command_runner)
    close_issue(repo, issue_number, command_runner=command_runner)


def complete_already_satisfied_issue(
    repo: str,
    issue_number: int,
    *,
    rid: str,
    branch: str,
    policy: smactorio_policy.SmactorioPolicy,
    command_runner: CommandRunner,
) -> None:
    issue_comment(
        repo,
        issue_number,
        textwrap.dedent(
            f"""
            SmactorIO completed this issue as already satisfied by the existing base checkout.

            No PR was opened because the worker verified the issue requirements without producing code or artifact commits.
            Run: `{rid}`
            Worker branch: `{branch}`

            Checks:
            - worker reported `SMACTORIO_OUTCOME_JSON_V1: ALREADY_SATISFIED` with structured evidence
            - worker checkout remained clean
            - worker branch had no diff from base
            - issue closed by SmactorIO foreman
            """
        ).strip(),
        command_runner=command_runner,
    )
    edit_issue_labels(repo, issue_number, add=[policy.done_label], remove=[policy.claim_label, policy.blocked_label], command_runner=command_runner)
    close_issue(repo, issue_number, command_runner=command_runner)


def run_once(
    *,
    repo: str,
    repo_root: Path,
    base: str,
    state_db: Path,
    dry_run: bool,
    worker_command: Sequence[str] | None = None,
    command_runner: CommandRunner = default_command_runner,
    policy: smactorio_policy.SmactorioPolicy | None = None,
) -> dict[str, Any]:
    policy_supplied = policy is not None
    policy = policy or smactorio_policy.policy_for_repo(repo)
    if dry_run:
        return plan_once(repo=repo, dry_run=True, command_runner=command_runner, policy=policy)

    runtime_refusal = enforce_runtime_environment(policy)
    if runtime_refusal is not None:
        runtime_refusal["repo"] = repo
        return runtime_refusal

    repo_root = repo_root.expanduser().resolve()
    state_db = state_db.expanduser().resolve()
    if runtime_state.path_is_inside(state_db, repo_root):
        raise SmactorioError(f"state db must live outside repo: {state_db}")

    rid = run_id()
    share_dir = Path(os.environ.get("SMACTORIO_SHARE_DIR") or DEFAULT_SHARE_DIR).expanduser()
    runtime_dir = share_dir / "runs" / rid
    github_remote = f"https://github.com/{repo}.git"
    github_env = token_git_env(runtime_dir)
    ensure_repo_seed_clone(repo_root, repo=repo, base=base, env=github_env)
    repo_guard.assert_clean(repo_root)
    stash_before = repo_guard.stash_list(repo_root)
    repo_guard.fetch(repo_root, remote=github_remote, env=github_env)
    repo_guard.ensure_base_checked_out_and_updated(repo_root, base, remote=github_remote, env=github_env)
    run_trusted_preflight(repo_root, base=base, policy=policy)
    current_base_sha = repo_guard.current_head(repo_root)

    issues = load_issues(repo, command_runner=command_runner, limit=policy.max_open_issues)
    recovered_labels = False
    if recover_stale_claims(repo, issues, policy=policy, command_runner=command_runner):
        recovered_labels = True
    if recover_retryable_blocked_issues(
        repo,
        issues,
        policy=policy,
        command_runner=command_runner,
        terminal_issue_predicate=lambda candidate: issue_has_terminal_retry_exhaustion(
            state_db,
            repo=repo,
            issue=candidate,
            base_sha=current_base_sha,
            policy=policy,
        ),
    ):
        recovered_labels = True
    if recovered_labels:
        issues = load_issues(repo, command_runner=command_runner, limit=policy.max_open_issues)
    issue = select_issue(issues, policy)
    if issue is None:
        return {"status": "no_work", "repo": repo, "issue_count": len(issues), "skipped_issues": skipped_issue_summaries(issues, policy)}

    issue_number = int(issue["number"])
    issue = load_issue_detail(repo, issue_number, command_runner=command_runner)
    if not policy_supplied:
        policy = smactorio_policy.policy_for_issue(repo, issue)
    recheck_reasons = smactorio_policy.issue_ineligibility_reasons(issue, policy)
    if recheck_reasons:
        return {
            "status": "no_work",
            "repo": repo,
            "issue_count": len(issues),
            "reason": "selected issue failed final eligibility recheck",
            "selected_issue_number": issue_number,
            "reasons": recheck_reasons,
        }
    if open_pr_mentions_issue(repo, issue_number, command_runner=command_runner):
        return {"status": "no_work", "repo": repo, "issue_count": len(issues), "reason": f"issue #{issue_number} already has an open PR"}
    branch = branch_name_for_issue(issue, run_id=rid)
    expires_at = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=policy.claim_ttl_minutes)).isoformat(timespec="seconds").replace("+00:00", "Z")
    conn = runtime_state.init_db(state_db)
    work_id = runtime_state.upsert_work_item(
        conn,
        work_key=f"github:{repo}#{issue_number}",
        issue_number=issue_number,
        issue_url=str(issue.get("url") or ""),
        title=str(issue.get("title") or ""),
        branch=branch,
        run_id=rid,
    )
    current_context = issue_context_fingerprint(issue, base_sha=current_base_sha)
    exhausted = runtime_state.exhausted_issue_attempt(
        conn,
        repo=repo,
        issue_number=issue_number,
        max_attempts=policy.max_attempts_per_failure_signature,
        failure_signature_prefix=f"{current_context}:",
    )
    if exhausted is not None:
        for name, color, description in [
            (policy.blocked_label, "B60205", "Blocked by SmactorIO runtime"),
            (policy.needs_attention_label, "D93F0B", "SmactorIO runtime needs operator attention"),
        ]:
            ensure_label(repo, name, color=color, description=description, command_runner=command_runner)
        runtime_state.transition(conn, work_id, "planned", "true_blocked", "retry budget exhausted for repeated failure signature")
        issue_comment(
            repo,
            issue_number,
            textwrap.dedent(
                f"""
                SmactorIO reached a terminal true-blocked outcome for this issue.

                Reason: retry budget exhausted for repeated failure signature.
                Failure class: `{exhausted.get('failure_class')}`
                Attempts: `{exhausted.get('attempt_count')}`
                Signature: `{exhausted.get('failure_signature')}`
                Evidence: `{exhausted.get('evidence_ref') or 'runtime attempt ledger'}`
                Run: `{rid}`

                The issue remains open for operator attention; SmactorIO will not keep reclaiming it until the blocker or labels change.
                """
            ).strip(),
            command_runner=command_runner,
        )
        edit_issue_labels(repo, issue_number, add=[policy.blocked_label, policy.needs_attention_label], remove=[policy.claim_label], command_runner=command_runner)
        conn.close()
        repo_guard.assert_stash_unchanged(stash_before, repo_guard.stash_list(repo_root))
        return {
            "status": "true_blocked",
            "repo": repo,
            "issue_number": issue_number,
            "reason": "retry_exhausted",
            "failure_class": exhausted.get("failure_class"),
            "attempt_count": exhausted.get("attempt_count"),
            "run_id": rid,
        }

    checkout_dir = share_dir / "checkouts"
    worktree = checkout_dir / rid
    pushed = False
    claimed = False
    try:
        checkout_dir.mkdir(parents=True, exist_ok=True)
        create_worker_checkout(repo_root, worktree, branch=branch, base=base)
        runtime_state.transition(conn, work_id, "planned", "preflight", "isolated checkout created before GitHub claim")
        if worker_command is None:
            preflight_error = run_worker_preflight(worktree, runtime_dir=runtime_dir, command_runner=command_runner, policy=policy)
            if preflight_error:
                runtime_state.transition(conn, work_id, "preflight", "preflight_failed", preflight_error[:1000])
                return {
                    "status": "no_work",
                    "repo": repo,
                    "issue_count": len(issues),
                    "selected_issue_number": issue_number,
                    "reason": "worker_preflight_failed",
                    "error": preflight_error[-1000:],
                }

        for name, color, description in [
            (policy.claim_label, "5319E7", "Claimed by SmactorIO runtime"),
            (policy.done_label, "0E8A16", "Completed by SmactorIO runtime"),
            (policy.blocked_label, "B60205", "Blocked by SmactorIO runtime"),
            (policy.needs_attention_label, "D93F0B", "SmactorIO runtime needs operator attention"),
        ]:
            ensure_label(repo, name, color=color, description=description, command_runner=command_runner)
        edit_issue_labels(repo, issue_number, add=[policy.claim_label], remove=[policy.needs_attention_label], command_runner=command_runner)
        claimed = True
        issue_comment(
            repo,
            issue_number,
            f"SmactorIO claimed this issue.\n\n{claim_marker(run_id=rid, expires_at=expires_at, branch=branch)}\n\nBranch: `{branch}`\nExpires: `{expires_at}`",
            command_runner=command_runner,
        )
        runtime_state.transition(conn, work_id, "preflight", "claimed", "GitHub issue claimed after worker preflight passed")
        runtime_state.transition(conn, work_id, "claimed", "worker_running", "worker starting")

        prompt = worker_prompt(issue, repo=repo, branch=branch)
        command = normalize_worker_command(worker_command) if worker_command is not None else default_worker_command(prompt)
        env = sanitized_worker_env(
            worker_env={
                "SMACTORIO_REPO": repo,
                "SMACTORIO_ISSUE_NUMBER": str(issue_number),
                "SMACTORIO_BRANCH": branch,
                "SMACTORIO_RUN_ID": rid,
            }
        )
        result_command, env = sandbox_worker_command(command, worktree=worktree, runtime_dir=runtime_dir, env=env)
        result = command_runner(result_command, cwd=str(worktree), env=env, timeout=policy.worker_timeout_seconds)
        if result.returncode != 0:
            raise SmactorioError(f"worker failed ({result.returncode}):\nSTDOUT:\n{result.stdout[-4000:]}\nSTDERR:\n{result.stderr[-4000:]}")
        lock_down_worker_git_metadata(worktree)
        worker_generated_side_effects = discard_worker_generated_side_effects(worktree, policy)
        repo_guard.assert_clean(worktree)
        has_worker_commit = repo_guard.head_differs_from(worktree, f"origin/{base}")
        material_paths: list[str] | None = None
        if has_worker_commit:
            material_paths = material_paths_or_contract_violation(worktree, base=base, policy=policy, worker_result=result)
        worker_outcome: dict[str, Any] | None = None
        if worker_terminal_outcome_should_be_parsed(result, material_paths=material_paths):
            try:
                worker_outcome = parse_worker_outcome(result, issue_number=issue_number)
            except SmactorioError as outcome_error:
                raise SmactorioError(f"worker structured outcome contract violation: {outcome_error}") from outcome_error
        elif final_nonempty_line(result.stdout) == "SMACTORIO_OUTCOME: ALREADY_SATISFIED":
            raise SmactorioError(
                "worker structured outcome contract violation: legacy SMACTORIO_OUTCOME marker is no longer sufficient; "
                "emit one smactorio-outcome-json block and SMACTORIO_OUTCOME_JSON_V1 sentinel"
            )
        if worker_outcome is not None and worker_outcome.get("outcome") == "ALREADY_SATISFIED":
            if has_worker_commit:
                raise SmactorioError("worker reported ALREADY_SATISFIED but produced commits; refusing contradictory outcome")
            if worker_generated_side_effects:
                raise SmactorioError("worker reported ALREADY_SATISFIED but left generated side effects; refusing unclean already-satisfied outcome")
            runtime_state.transition(conn, work_id, "worker_running", "already_satisfied", "worker verified issue was already satisfied without code changes")
            complete_already_satisfied_issue(
                repo,
                issue_number,
                rid=rid,
                branch=branch,
                policy=policy,
                command_runner=command_runner,
            )
            repo_guard.assert_stash_unchanged(stash_before, repo_guard.stash_list(repo_root))
            remove_worker_checkout(worktree)
            repo_guard.delete_local_branch(repo_root, branch)
            repo_guard.ensure_base_checked_out_and_updated(repo_root, base, remote=github_remote, env=github_env)
            return {
                "status": "already_satisfied",
                "repo": repo,
                "issue_number": issue_number,
                "branch": branch,
                "run_id": rid,
            }
        if material_paths is None:
            raise SmactorioError("worker produced no commit; refusing to create empty PR")
        runtime_state.transition(conn, work_id, "worker_running", "worker_done", "worker returned with material changes: " + ", ".join(material_paths[:8]))

        repairs = repair_worker_diff_check_whitespace(worktree, base=base)
        checks = []
        if worker_generated_side_effects:
            checks.append(
                "$ smactorio discard worker generated side effects\n"
                "exit=0\n"
                "Worker left generated public-page drift; discarded before commit/review:\n"
                + worker_generated_side_effects[-2000:]
            )
        verified_from_state = "worker_done"
        if repairs:
            runtime_state.transition(conn, work_id, "worker_done", "worker_repaired", f"auto-fixed git diff --check whitespace: {', '.join(repairs)}")
            verified_from_state = "worker_repaired"
            checks.append(
                "$ smactorio repair git diff --check\n"
                "exit=0\n"
                "Auto-fixed trailing whitespace in committed worker output before verification:\n"
                + "\n".join(f"- {path}" for path in repairs)
            )
        checks.extend(run_verification(worktree, policy=policy, base=base))
        artifact_rel = write_verification_artifact(worktree, issue=issue, pr_url=None, checks=checks, rid=rid, policy=policy)
        commit_all(worktree, f"docs: add SmactorIO verification for issue #{issue_number}", policy=policy)
        run_verification(worktree, policy=policy, base=base)
        expected_head = repo_guard.current_head(worktree)
        runtime_state.transition(conn, work_id, verified_from_state, "verified", "local verification passed")
        run_independent_review(worktree, issue=issue, repo=repo, branch=branch, runtime_dir=runtime_dir, command_runner=command_runner, policy=policy)
        runtime_state.transition(conn, work_id, "verified", "reviewed", "independent review passed")

        push_branch(worktree, repo=repo, branch=branch, runtime_dir=runtime_dir)
        pushed = True
        pr_number, pr_url = create_pr(repo, issue, branch=branch, base=base, body_extra=f"- Local checks passed.\n- Independent review passed.\n- Verification artifact: `{artifact_rel}`", command_runner=command_runner)
        runtime_state.set_pr(conn, work_id, pr_url=pr_url)
        runtime_state.transition(conn, work_id, "reviewed", "pr_open", f"PR opened: {pr_url}")

        wait_for_pr_checks(repo, pr_number, command_runner=command_runner, expected_head=expected_head)
        pr_url, merge_commit = merge_pr(repo, pr_number, command_runner=command_runner, expected_head=expected_head)
        runtime_state.set_pr(conn, work_id, pr_url=pr_url, merge_commit=merge_commit)
        runtime_state.transition(conn, work_id, "pr_open", "merged", f"PR merged: {merge_commit}")

        complete_issue(
            repo,
            issue_number,
            pr_url=pr_url,
            merge_commit=merge_commit,
            artifact_rel=artifact_rel,
            rid=rid,
            policy=policy,
            command_runner=command_runner,
        )
        repo_guard.assert_stash_unchanged(stash_before, repo_guard.stash_list(repo_root))
        remove_worker_checkout(worktree)
        repo_guard.delete_local_branch(repo_root, branch)
        repo_guard.ensure_base_checked_out_and_updated(repo_root, base, remote=github_remote, env=github_env)
        return {
            "status": "merged",
            "repo": repo,
            "issue_number": issue_number,
            "branch": branch,
            "pr_url": pr_url,
            "merge_commit": merge_commit,
            "verification_artifact": str(artifact_rel),
            "run_id": rid,
        }
    except Exception as exc:
        exc_text = str(exc)
        try:
            runtime_state.transition(conn, None if 'work_id' not in locals() else work_id, "running", "blocked", redact_operational_evidence(exc_text, max_chars=1000))  # type: ignore[arg-type]
        except Exception:
            pass
        exhausted_after_failure = None
        try:
            if 'conn' in locals() and 'issue_number' in locals():
                runtime_state.record_issue_attempt(
                    conn,
                    repo=repo,
                    issue_number=issue_number,
                    run_id=rid if 'rid' in locals() else "unknown",
                    durable_state="blocked" if claimed else "failed_pre_claim",
                    failure_class=classify_failure(exc_text),
                    failure_signature=scoped_failure_signature(issue, base_sha=current_base_sha if 'current_base_sha' in locals() else None, message=exc_text) if 'issue' in locals() else failure_signature(exc_text),
                    base_sha=current_base_sha if 'current_base_sha' in locals() else None,
                    head_sha=expected_head if 'expected_head' in locals() else None,
                    evidence_ref=f"smactorio-run:{rid if 'rid' in locals() else 'unknown'}",
                )
                exhausted_after_failure = runtime_state.exhausted_issue_attempt(
                    conn,
                    repo=repo,
                    issue_number=issue_number,
                    max_attempts=policy.max_attempts_per_failure_signature,
                    failure_signature_prefix=f"{issue_context_fingerprint(issue, base_sha=current_base_sha)}:" if 'issue' in locals() and 'current_base_sha' in locals() else None,
                )
                if exhausted_after_failure is not None and 'work_id' in locals():
                    runtime_state.transition(conn, work_id, "blocked", "true_blocked", "retry budget exhausted after repeated failure signature")
        except Exception:
            pass
        try:
            if pushed and 'branch' in locals():
                delete_remote_branch(repo, branch, runtime_dir=runtime_dir)
        except Exception:
            pass
        try:
            if claimed and 'issue_number' in locals():
                if exhausted_after_failure is not None:
                    issue_comment(
                        repo,
                        issue_number,
                        f"SmactorIO reached terminal true-blocked state.\n\nRun: `{rid if 'rid' in locals() else 'unknown'}`\nFailure class: `{classify_failure(exc_text)}`\nAttempts: `{exhausted_after_failure.get('attempt_count')}`\nReason:\n```text\n{redact_operational_evidence(exc_text[-1800:])}\n```",
                        command_runner=command_runner,
                    )
                    edit_issue_labels(
                        repo,
                        issue_number,
                        add=[policy.blocked_label, policy.needs_attention_label],
                        remove=[policy.claim_label],
                        command_runner=command_runner,
                    )
                else:
                    issue_comment(repo, issue_number, f"SmactorIO blocked.\n\nRun: `{rid if 'rid' in locals() else 'unknown'}`\nFailure class: `{classify_failure(exc_text)}`\nReason:\n```text\n{redact_operational_evidence(exc_text[-1800:])}\n```", command_runner=command_runner)
                    edit_issue_labels(repo, issue_number, add=[policy.blocked_label], remove=[policy.claim_label], command_runner=command_runner)
        except Exception:
            pass
        raise
    finally:
        conn.close()
        if 'worktree' in locals() and Path(worktree).exists():
            remove_worker_checkout(worktree)
        if 'branch' in locals():
            repo_guard.delete_local_branch(repo_root, branch)
        repo_guard.assert_stash_unchanged(stash_before, repo_guard.stash_list(repo_root))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.environ.get("SMACTORIO_REPO", "leonbreukelman/rtx3070-workshop-ops"))
    parser.add_argument("--repo-root", type=Path, default=Path(os.environ.get("SMACTORIO_REPO_ROOT", str(DEFAULT_REPO_ROOT))))
    parser.add_argument("--base", default=os.environ.get("SMACTORIO_BASE_BRANCH", "main"))
    parser.add_argument("--state-db", type=Path, default=runtime_state.default_state_db())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    try:
        result = run_once(repo=args.repo, repo_root=args.repo_root, base=args.base, state_db=args.state_db, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
