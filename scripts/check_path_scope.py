#!/usr/bin/env python3
"""Fail closed when changed paths include runtime, secret, or out-of-scope files."""
from __future__ import annotations

import argparse
import dataclasses
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Iterable, Sequence


@dataclasses.dataclass(frozen=True)
class Finding:
    path: str
    reason: str


FORBIDDEN_COMPONENTS = {
    "state",
    "logs",
    "log",
    "runtime",
    "cache",
    "caches",
    "db",
    "backups",
    ".backups",
    ".hermes_backups",
    "reports",
    "secret",
    "secrets",
    "raw",
    "raw_data",
    "private",
    "passwords",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "build",
}

FORBIDDEN_NAME_FRAGMENTS = (
    "credential",
    "credentials",
    "token",
    "tokens",
    "api_key",
    "apikey",
    "private_key",
    "password",
    "passwd",
    "service-account",
    "service_account",
)

FORBIDDEN_SUFFIXES = (
    ".env",
    ".key",
    ".pem",
    ".p12",
    ".pfx",
    ".crt",
    ".csr",
    ".kdbx",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".db-wal",
    ".db-shm",
    ".sqlite-wal",
    ".sqlite-shm",
    ".log",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".zip",
    ".7z",
    ".bak",
    ".backup",
    ".tmp",
    ".swp",
    ".pyc",
    ".pyo",
)

SAFE_DATA_PREFIXES = (
    "signal-hub/data/project_homepages/",
    "signal-hub/data/smactorio/",
)

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def normalize_changed_path(raw_path: str) -> tuple[str | None, str | None]:
    """Return a safe POSIX-normalized relative path, or a rejection reason."""
    raw = raw_path
    if not raw:
        return None, "empty path"
    if raw != raw.strip():
        return raw, "leading or trailing whitespace in paths is not allowed"

    candidate = raw.replace("\\", "/")
    if candidate.startswith("/"):
        return raw, "absolute paths are not allowed"
    if _DRIVE_PREFIX.match(candidate):
        return raw, "drive-letter paths are not allowed"
    if "://" in candidate:
        return raw, "URL-like paths are not allowed"

    normalized = posixpath.normpath(candidate)
    if normalized in {".", ".."} or normalized.startswith("../"):
        return raw, "path traversal outside the repository is not allowed"
    return normalized, None


def _is_allowed_data_path(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in SAFE_DATA_PREFIXES)


def normalize_allowed_prefix(raw_prefix: str) -> str | None:
    """Normalize an allowlist prefix while preserving path-component boundaries."""
    prefix = raw_prefix.replace("\\", "/")
    if not prefix or prefix != prefix.strip():
        return None
    if prefix.startswith("/") or _DRIVE_PREFIX.match(prefix) or "://" in prefix:
        return None
    normalized = posixpath.normpath(prefix)
    if normalized in {".", ".."} or normalized.startswith("../"):
        return None
    return normalized.rstrip("/")


def has_allowed_prefix(path: str, allowed_prefixes: Sequence[str]) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in allowed_prefixes)


def forbidden_reason(path: str) -> str | None:
    lower_path = path.lower()
    components = tuple(component.lower() for component in path.split("/"))
    basename = components[-1]

    for component in components:
        if component in FORBIDDEN_COMPONENTS:
            return f"runtime/generated path component is forbidden: {component}"

    if basename == ".env" or basename.startswith(".env.") or basename.endswith(".env"):
        return "environment files are forbidden"

    for suffix in FORBIDDEN_SUFFIXES:
        if lower_path.endswith(suffix):
            return f"forbidden file suffix: {suffix}"

    for component in components:
        for fragment in FORBIDDEN_NAME_FRAGMENTS:
            if fragment in component:
                return f"credential/token path component is forbidden: {component}"

    if "data" in components and not _is_allowed_data_path(path):
        return "broad data paths are forbidden; use an explicit sanitized source-data allowlist"

    return None


def check_paths(paths: Iterable[str], allowed_prefixes: Sequence[str] = ()) -> list[Finding]:
    normalized_prefixes = tuple(
        prefix
        for raw_prefix in allowed_prefixes
        if (prefix := normalize_allowed_prefix(raw_prefix)) is not None
    )
    findings: list[Finding] = []

    for raw_path in paths:
        path, reason = normalize_changed_path(raw_path)
        if reason:
            findings.append(Finding(path or raw_path, reason))
            continue
        assert path is not None

        if normalized_prefixes and not has_allowed_prefix(path, normalized_prefixes):
            display_prefixes = tuple(f"{prefix}/" for prefix in normalized_prefixes)
            findings.append(Finding(path, f"path is outside allowed prefixes: {', '.join(display_prefixes)}"))
            continue

        reason = forbidden_reason(path)
        if reason:
            findings.append(Finding(path, reason))

    return findings


def read_paths_from_files(files: Iterable[Path]) -> list[str]:
    paths: list[str] = []
    for file_path in files:
        try:
            paths.extend(line.rstrip("\n") for line in file_path.read_text(encoding="utf-8").splitlines())
        except OSError as exc:
            paths.append(str(file_path))
            print(f"failed to read changed-paths file {file_path}: {exc}", file=sys.stderr)
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Changed paths to check, relative to the repository root.")
    parser.add_argument("--from-file", action="append", default=[], type=Path, help="Read newline-delimited changed paths from a file.")
    parser.add_argument("--allow-prefix", action="append", default=[], help="Optional relative path prefix allowlist. Repeatable.")
    args = parser.parse_args(argv)

    paths = list(args.paths)
    paths.extend(read_paths_from_files(args.from_file))
    findings = check_paths(paths, allowed_prefixes=args.allow_prefix)
    print(json.dumps([dataclasses.asdict(finding) for finding in findings], indent=2, sort_keys=True))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
