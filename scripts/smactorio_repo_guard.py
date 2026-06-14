#!/usr/bin/env python3
"""Repository-discipline helpers for SmactorIO."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


class RepoGuardError(RuntimeError):
    """Raised when repo hygiene would be violated."""


def run_git(repo: str | Path, args: Sequence[str], *, timeout: int = 60, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=Path(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
        env=env,
    )
    if check and result.returncode != 0:
        raise RepoGuardError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def status_porcelain(repo: str | Path) -> str:
    return run_git(repo, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout


def status_is_clean(status: str) -> bool:
    return not status.strip()


def stash_list(repo: str | Path) -> str:
    return run_git(repo, ["stash", "list"]).stdout


def stash_is_unchanged(before: str, after: str) -> bool:
    return before == after


def assert_clean(repo: str | Path) -> None:
    status = status_porcelain(repo)
    if not status_is_clean(status):
        raise RepoGuardError(f"worktree is dirty:\n{status}")


def assert_stash_unchanged(before: str, after: str) -> None:
    if not stash_is_unchanged(before, after):
        raise RepoGuardError("stash list changed during SmactorIO run")


def current_branch(repo: str | Path) -> str:
    return run_git(repo, ["branch", "--show-current"]).stdout.strip()


def current_head(repo: str | Path) -> str:
    return run_git(repo, ["rev-parse", "HEAD"]).stdout.strip()


def fetch(repo: str | Path, remote: str = "origin", *, env: dict[str, str] | None = None) -> None:
    run_git(repo, ["fetch", "--prune", remote, "+refs/heads/*:refs/remotes/origin/*"], timeout=180, env=env)


def ensure_base_checked_out_and_updated(repo: str | Path, base: str, *, remote: str = "origin", env: dict[str, str] | None = None) -> None:
    assert_clean(repo)
    run_git(repo, ["switch", base], timeout=120)
    run_git(repo, ["pull", "--ff-only", remote, base], timeout=180, env=env)
    assert_clean(repo)


def changed_paths(repo: str | Path, base_ref: str) -> list[str]:
    result = run_git(repo, ["diff", "--name-only", "--no-renames", f"{base_ref}...HEAD"], timeout=120)
    return [line for line in result.stdout.splitlines() if line.strip()]


def head_differs_from(repo: str | Path, ref: str) -> bool:
    result = run_git(repo, ["rev-list", "--count", f"{ref}..HEAD"])
    try:
        return int(result.stdout.strip() or "0") > 0
    except ValueError:
        return True


def remove_worktree(repo: str | Path, worktree: str | Path) -> None:
    run_git(repo, ["worktree", "remove", "--force", str(worktree)], timeout=180, check=False)
    run_git(repo, ["worktree", "prune"], timeout=120, check=False)


def delete_local_branch(repo: str | Path, branch: str) -> None:
    if branch:
        run_git(repo, ["branch", "-D", branch], timeout=120, check=False)
