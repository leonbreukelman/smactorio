#!/usr/bin/env python3
"""Detect Hermes fork/upstream drift and publish SmactorIO sync work.

The checker is intentionally conservative:
- fast-forward-only pushes are allowed;
- any merge commit requirement is routed to a GitHub issue for the Hermes
  SmactorIO lane;
- conflict evidence is collected only from a scratch checkout and rendered from
  an allowlist of structured fields.
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence

DEFAULT_FORK_REPO = "leonbreukelman/hermes-agent"
DEFAULT_UPSTREAM_REPO = "NousResearch/hermes-agent"
DEFAULT_CHECKOUT = Path("/home/leonb/hermes")
DEFAULT_WORK_ROOT = Path("/home/leonb/.local/share/smactorio/fork-sync/hermes-agent")
DEFAULT_LOCK_FILE = Path("/home/leonb/.local/state/smactorio/hermes-fork.lock")
DEFAULT_ISSUE_REPO = DEFAULT_FORK_REPO
DEFAULT_BASE = "main"
DEFAULT_TITLE = "SmactorIO: verify Hermes upstream sync"
LANE_KEY = "hermes-upstream-sync"
MARKER_PREFIX = "smactorio:hermes-fork-sync"
ISSUE_LABELS = ("smactorio", "autonomy:ready", "risk:low", "type:maintenance", "area:hermes-fork-sync")

TOKEN_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{8,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-.]{12,}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-]{16,}"),
)
LOCAL_PATH_RE = re.compile(r"(?:/home/[^\s)`'\"]+|/tmp/[^\s)`'\"]+|/Users/[^\s)`'\"]+)")
MARKER_RE = re.compile(r"<!--\s*smactorio:hermes-fork-sync\s+(?P<payload>\{.*?\})\s*-->", re.DOTALL)

CommandRunner = Callable[[Sequence[str], Path | None], subprocess.CompletedProcess[str]]


class ForkSyncError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class SyncState:
    fork_sha: str
    upstream_sha: str
    base: str
    timestamp: str
    merge_required: bool
    conflict_files: tuple[str, ...] = ()

    @property
    def marker_payload(self) -> dict[str, Any]:
        return {
            "lane": LANE_KEY,
            "base": self.base,
            "fork_sha": self.fork_sha,
            "upstream_sha": self.upstream_sha,
            "conflict_files": list(self.conflict_files),
        }


def default_runner(argv: Sequence[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(argv), cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)


def configure_git_auth(work_root: Path, *, base_env: dict[str, str] | None = None) -> None:
    """Install a local askpass helper so HTTPS git push can use GH_TOKEN without logging it."""
    env = base_env or os.environ
    token = env.get("GITHUB_TOKEN") or env.get("GH_TOKEN")
    if not token or env.get("GIT_ASKPASS"):
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        return
    work_root.parent.mkdir(parents=True, exist_ok=True)
    askpass = work_root.parent / ".hermes-fork-sync-git-askpass.sh"
    askpass.write_text(
        "#!/usr/bin/env bash\n"
        "case \"$1\" in\n"
        "  *Username*) printf '%s\\n' 'x-access-token' ;;\n"
        "  *Password*) printf '%s\\n' \"$GITHUB_TOKEN\" ;;\n"
        "  *) printf '%s\\n' \"$GITHUB_TOKEN\" ;;\n"
        "esac\n",
        encoding="utf-8",
    )
    askpass.chmod(0o700)
    if not env.get("GITHUB_TOKEN") and env.get("GH_TOKEN"):
        env["GITHUB_TOKEN"] = env["GH_TOKEN"]
    env["GIT_ASKPASS"] = str(askpass)
    env["GIT_TERMINAL_PROMPT"] = "0"


def run_git(work_root: Path, args: Sequence[str], *, check: bool = True, runner: CommandRunner = default_runner) -> subprocess.CompletedProcess[str]:
    result = runner(["git", *args], work_root)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()[-2000:]
        raise ForkSyncError(f"git {' '.join(args)} failed: {detail}")
    return result


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def public_https_url(repo: str) -> str:
    clean = repo.removeprefix("https://github.com/").removesuffix(".git")
    return f"https://github.com/{clean}.git"


def ensure_scratch_clone(work_root: Path, *, fork_repo: str, upstream_repo: str, base: str, runner: CommandRunner = default_runner) -> None:
    if not (work_root / ".git").exists():
        work_root.parent.mkdir(parents=True, exist_ok=True)
        result = runner(["git", "clone", "--branch", base, "--single-branch", public_https_url(fork_repo), str(work_root)], None)
        if result.returncode != 0:
            raise ForkSyncError(f"scratch clone failed: {(result.stderr or result.stdout)[-2000:]}")
    run_git(work_root, ["remote", "set-url", "origin", public_https_url(fork_repo)], runner=runner)
    upstream_url = public_https_url(upstream_repo)
    remotes = run_git(work_root, ["remote"], runner=runner).stdout.splitlines()
    if "upstream" in remotes:
        run_git(work_root, ["remote", "set-url", "upstream", upstream_url], runner=runner)
    else:
        run_git(work_root, ["remote", "add", "upstream", upstream_url], runner=runner)


def fetch_refs(work_root: Path, *, base: str, runner: CommandRunner = default_runner) -> tuple[str, str]:
    run_git(work_root, ["fetch", "--prune", "origin", f"+refs/heads/{base}:refs/remotes/origin/{base}"], runner=runner)
    run_git(work_root, ["fetch", "--prune", "upstream", f"+refs/heads/{base}:refs/remotes/upstream/{base}"], runner=runner)
    fork_sha = run_git(work_root, ["rev-parse", f"origin/{base}"], runner=runner).stdout.strip()
    upstream_sha = run_git(work_root, ["rev-parse", f"upstream/{base}"], runner=runner).stdout.strip()
    return fork_sha, upstream_sha


def is_ancestor(work_root: Path, ancestor: str, descendant: str, *, runner: CommandRunner = default_runner) -> bool:
    result = run_git(work_root, ["merge-base", "--is-ancestor", ancestor, descendant], check=False, runner=runner)
    if result.returncode in {0, 1}:
        return result.returncode == 0
    raise ForkSyncError(f"merge-base failed: {(result.stderr or result.stdout)[-2000:]}")


def fast_forward_push_args(upstream_sha: str, *, base: str) -> list[str]:
    return ["git", "push", "origin", f"{upstream_sha}:refs/heads/{base}"]


def assert_fast_forward_push_safe(argv: Sequence[str]) -> None:
    if any(arg == "--force" or arg.startswith("--force") for arg in argv):
        raise ForkSyncError("refusing force push")
    if any(arg.startswith("+") for arg in argv):
        raise ForkSyncError("refusing force refspec")


def push_fast_forward(work_root: Path, *, upstream_sha: str, base: str, runner: CommandRunner = default_runner, dry_run: bool = False) -> None:
    argv = fast_forward_push_args(upstream_sha, base=base)
    assert_fast_forward_push_safe(argv)
    if dry_run:
        return
    result = runner(argv, work_root)
    if result.returncode != 0:
        raise ForkSyncError(f"fast-forward push failed: {(result.stderr or result.stdout)[-2000:]}")


def normalize_repo_path(raw: str, *, git_path: bool = False) -> str | None:
    path = raw or ""
    if not git_path:
        path = path.replace("\\", "/").strip()
    if not path or path.startswith("/") or path.startswith("../") or "/../" in path or path == ".." or "://" in path:
        return None
    while path.startswith("./"):
        path = path[2:]
    return path


def _append_unique_path(paths: list[str], raw: str, *, git_path: bool = False) -> None:
    path = normalize_repo_path(raw, git_path=git_path)
    if path and path not in paths:
        paths.append(path)


def _parse_nul_paths(stdout: str) -> tuple[str, ...]:
    paths: list[str] = []
    for raw_path in stdout.split("\0"):
        if raw_path:
            _append_unique_path(paths, raw_path, git_path=True)
    return tuple(paths)


def _parse_ls_files_unmerged(stdout: str) -> tuple[str, ...]:
    paths: list[str] = []
    for record in stdout.split("\0"):
        if not record:
            continue
        # Format with -z: "<mode> <object> <stage>\t<path>\0". The path is
        # not C-quoted, so tabs/newlines/quotes/backslashes in filenames remain
        # exact after the first metadata separator.
        _, sep, raw_path = record.partition("\t")
        if sep:
            _append_unique_path(paths, raw_path, git_path=True)
    return tuple(paths)


def unmerged_paths(work_root: Path, *, runner: CommandRunner = default_runner) -> tuple[str, ...]:
    # Git 2.54 on GitHub's runner returned no paths for
    # `git diff --name-only --diff-filter=U` during this merge simulation even
    # though `git status` showed UU. `ls-files -u -z` is index-stage based and
    # preserves exact pathnames without Git C-quoting.
    ls_files = run_git(work_root, ["ls-files", "-u", "-z"], check=False, runner=runner)
    paths = list(_parse_ls_files_unmerged(ls_files.stdout))
    if not paths:
        diff = run_git(work_root, ["diff", "--name-only", "-z", "--diff-filter=U"], check=False, runner=runner)
        paths = list(_parse_nul_paths(diff.stdout))
    return tuple(paths)


def abort_merge_and_clean(work_root: Path, *, fork_sha: str, runner: CommandRunner = default_runner) -> None:
    run_git(work_root, ["merge", "--abort"], check=False, runner=runner)
    run_git(work_root, ["reset", "--hard", fork_sha], runner=runner)
    run_git(work_root, ["clean", "-fd"], runner=runner)


def simulate_merge(work_root: Path, *, fork_sha: str, upstream_sha: str, runner: CommandRunner = default_runner) -> tuple[str, ...]:
    run_git(work_root, ["checkout", "-B", "smactorio-hermes-fork-sync", fork_sha], runner=runner)
    run_git(work_root, ["reset", "--hard", fork_sha], runner=runner)
    run_git(work_root, ["clean", "-fd"], runner=runner)
    result = run_git(
        work_root,
        [
            "-c",
            "user.name=Hermes Fork Sync",
            "-c",
            "user.email=hermes-fork-sync@example.invalid",
            "merge",
            "--no-commit",
            "--no-ff",
            upstream_sha,
        ],
        check=False,
        runner=runner,
    )
    conflicts = unmerged_paths(work_root, runner=runner) if result.returncode != 0 else ()
    abort_merge_and_clean(work_root, fork_sha=fork_sha, runner=runner)
    status = run_git(work_root, ["status", "--porcelain=v1"], runner=runner).stdout.strip()
    if status:
        raise ForkSyncError("scratch checkout left dirty after merge simulation")
    if (work_root / ".git" / "MERGE_HEAD").exists():
        raise ForkSyncError("scratch checkout left mid-merge after simulation")
    return tuple(sorted(conflicts))


def assert_public_text_safe(text: str) -> None:
    if LOCAL_PATH_RE.search(text):
        raise ForkSyncError("refusing to publish local absolute path")
    for pattern in TOKEN_PATTERNS:
        if pattern.search(text):
            raise ForkSyncError("refusing to publish token-shaped text")


def render_issue_body(state: SyncState) -> str:
    marker = f"<!-- {MARKER_PREFIX} {json.dumps(state.marker_payload, sort_keys=True, separators=(',', ':'))} -->"
    conflicts = "\n".join(f"- `{path}`" for path in state.conflict_files) or "- none detected; merge commit still required"
    merge_kind = "conflicted merge" if state.conflict_files else "clean merge commit required"
    body = f"""{marker}
# Hermes upstream sync requires SmactorIO

The scheduled Hermes fork-sync checker found that Leon's fork cannot be updated by a fast-forward-only push.

## Structured evidence
- Lane: `{LANE_KEY}`
- Base branch: `{state.base}`
- Fork SHA: `{state.fork_sha}`
- Upstream SHA: `{state.upstream_sha}`
- Detected at: `{state.timestamp}`
- Merge state: `{merge_kind}`

## Conflict files
{conflicts}

## Acceptance criteria
- Resolve the upstream sync in an isolated worker checkout.
- Preserve Leon's fork-specific commits and custom code.
- Do not force-push and do not use `+` refspecs.
- Do not modify branch protection, workflow security boundaries, secrets, credentials, runtime state, caches, build outputs, or local-only files.
- Open and verify a normal PR against Leon's Hermes fork when changes are needed.
- Run Hermes update tests/smokes and focused tests covering changed files.

## Stop conditions
- Any required secret, 2FA, billing, branch-protection, force-push, or destructive operation must block for human review.
- If this is a clean merge-commit case with no conflict files, block for human review instead of broadening path scope.
- If changed paths fall outside the conflict-file scope, block instead of broadening the lane.
"""
    assert_public_text_safe(body)
    return body


def parse_marker(body: str | None) -> dict[str, Any] | None:
    for match in MARKER_RE.finditer(body or ""):
        try:
            payload = json.loads(match.group("payload"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("lane") == LANE_KEY:
            return payload
    return None


def github_json(argv: Sequence[str], *, runner: CommandRunner = default_runner) -> Any:
    result = runner(argv, None)
    if result.returncode != 0:
        raise ForkSyncError(f"GitHub command failed: {(result.stderr or result.stdout)[-2000:]}")
    return json.loads(result.stdout or "[]")


def list_sync_issues(issue_repo: str, *, runner: CommandRunner = default_runner) -> list[dict[str, Any]]:
    data = github_json(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            issue_repo,
            "--state",
            "open",
            "--label",
            "area:hermes-fork-sync",
            "--limit",
            "50",
            "--json",
            "number,title,body,labels",
        ],
        runner=runner,
    )
    return [item for item in data if parse_marker(str(item.get("body") or ""))]


def temp_body_file(body: str) -> Path:
    fd, name = tempfile.mkstemp(prefix="hermes-fork-sync-", suffix=".md", text=True)
    path = Path(name)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(body)
    return path


def marker_pair(payload: dict[str, Any] | None) -> tuple[str | None, str | None]:
    if not payload:
        return None, None
    return str(payload.get("fork_sha") or ""), str(payload.get("upstream_sha") or "")


def upsert_sync_issue(issue_repo: str, state: SyncState, *, runner: CommandRunner = default_runner, dry_run: bool = False) -> dict[str, Any]:
    body = render_issue_body(state)
    issues = sorted(list_sync_issues(issue_repo, runner=runner), key=lambda item: int(item.get("number") or 0))
    existing = issues[0] if issues else None
    if existing:
        number = int(existing["number"])
        existing_pair = marker_pair(parse_marker(str(existing.get("body") or "")))
        if existing_pair == (state.fork_sha, state.upstream_sha):
            return {"status": "issue_unchanged", "issue_number": number}
        if not dry_run:
            body_file = temp_body_file(body)
            comment = (
                "Hermes upstream sync evidence changed.\n\n"
                f"- Fork SHA: `{state.fork_sha}`\n"
                f"- Upstream SHA: `{state.upstream_sha}`\n"
                f"- Conflict files: {len(state.conflict_files)}\n"
            )
            comment_file = temp_body_file(comment)
            try:
                edit = runner(["gh", "issue", "edit", str(number), "--repo", issue_repo, "--body-file", str(body_file)], None)
                if edit.returncode != 0:
                    raise ForkSyncError(f"issue edit failed: {(edit.stderr or edit.stdout)[-2000:]}")
                comment_result = runner(["gh", "issue", "comment", str(number), "--repo", issue_repo, "--body-file", str(comment_file)], None)
                if comment_result.returncode != 0:
                    raise ForkSyncError(f"issue comment failed: {(comment_result.stderr or comment_result.stdout)[-2000:]}")
            finally:
                body_file.unlink(missing_ok=True)
                comment_file.unlink(missing_ok=True)
        return {"status": "issue_updated", "issue_number": number}

    if dry_run:
        return {"status": "issue_would_create", "title": DEFAULT_TITLE}
    body_file = temp_body_file(body)
    try:
        create = runner(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                issue_repo,
                "--title",
                DEFAULT_TITLE,
                "--body-file",
                str(body_file),
                *sum((["--label", label] for label in ISSUE_LABELS), []),
            ],
            None,
        )
        if create.returncode != 0:
            # Reconcile create/list races by looking again for the oldest marker issue.
            reconciled = sorted(list_sync_issues(issue_repo, runner=runner), key=lambda item: int(item.get("number") or 0))
            if reconciled:
                return {"status": "issue_reconciled", "issue_number": int(reconciled[0]["number"])}
            raise ForkSyncError(f"issue create failed: {(create.stderr or create.stdout)[-2000:]}")
    finally:
        body_file.unlink(missing_ok=True)
    return {"status": "issue_created", "issue_url": create.stdout.strip()}


def acquire_lock(lock_file: Path):
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_file.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(f"pid={os.getpid()}\n")
    handle.flush()
    return handle


def run_check(
    *,
    fork_repo: str = DEFAULT_FORK_REPO,
    upstream_repo: str = DEFAULT_UPSTREAM_REPO,
    work_root: Path = DEFAULT_WORK_ROOT,
    issue_repo: str = DEFAULT_ISSUE_REPO,
    base: str = DEFAULT_BASE,
    dry_run: bool = False,
    runner: CommandRunner = default_runner,
) -> dict[str, Any]:
    configure_git_auth(work_root)
    ensure_scratch_clone(work_root, fork_repo=fork_repo, upstream_repo=upstream_repo, base=base, runner=runner)
    fork_sha, upstream_sha = fetch_refs(work_root, base=base, runner=runner)
    timestamp = utc_now()
    if upstream_sha == fork_sha or is_ancestor(work_root, upstream_sha, fork_sha, runner=runner):
        return {"status": "already_current", "fork_sha": fork_sha, "upstream_sha": upstream_sha}
    if is_ancestor(work_root, fork_sha, upstream_sha, runner=runner):
        push_fast_forward(work_root, upstream_sha=upstream_sha, base=base, runner=runner, dry_run=dry_run)
        return {"status": "fast_forwarded" if not dry_run else "fast_forward_would_push", "fork_sha": fork_sha, "upstream_sha": upstream_sha}

    conflicts = simulate_merge(work_root, fork_sha=fork_sha, upstream_sha=upstream_sha, runner=runner)
    state = SyncState(fork_sha=fork_sha, upstream_sha=upstream_sha, base=base, timestamp=timestamp, merge_required=True, conflict_files=conflicts)
    issue_result = upsert_sync_issue(issue_repo, state, runner=runner, dry_run=dry_run)
    return {"status": "merge_required", "fork_sha": fork_sha, "upstream_sha": upstream_sha, "conflict_files": list(conflicts), **issue_result}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fork-repo", default=DEFAULT_FORK_REPO)
    parser.add_argument("--upstream-repo", default=DEFAULT_UPSTREAM_REPO)
    parser.add_argument("--checkout", type=Path, default=DEFAULT_CHECKOUT, help="Reserved for future remote discovery; not mutated.")
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--issue-repo", default=DEFAULT_ISSUE_REPO)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK_FILE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    _lock = acquire_lock(args.lock_file.expanduser().resolve())
    if _lock is None:
        payload = {"status": "lock_busy"}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(payload["status"])
        return 0
    try:
        result = run_check(
            fork_repo=args.fork_repo,
            upstream_repo=args.upstream_repo,
            work_root=args.work_root.expanduser().resolve(),
            issue_repo=args.issue_repo,
            base=args.base,
            dry_run=args.dry_run,
        )
    except Exception as exc:  # pragma: no cover - CLI wrapper
        payload = {"status": "error", "error": str(exc)}
        if args.json:
            print(json.dumps(payload, sort_keys=True))
        else:
            print(payload["error"], file=sys.stderr)
        return 1
    finally:
        _lock.close()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
