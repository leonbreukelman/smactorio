#!/usr/bin/env python3
"""Small local secret scanner for generated Signal Hub artifacts."""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Iterable

@dataclasses.dataclass(frozen=True)
class Finding:
    path: str
    line: int
    pattern: str
    snippet: str

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"AKIA[A-Z0-9\.]{6,}")),
    ("github_token", re.compile(r"gh[pousr]_[A-Za-z0-9_\.]{8,}")),
    ("openai_key", re.compile(r"sk-[A-Za-z0-9\.]{8,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9\-.]{8,}")),
    ("generic_assignment", re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-]{16,}")),
]

SAFE_MARKERS = ["[REDACTED]", "placeholder", "example", "sk-…", "ghp_…", "xoxb-…", "AKIA…"]
TEXT_SUFFIXES = {".html", ".json", ".md", ".txt", ".py", ".yaml", ".yml", ".css", ".js"}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules"}


def should_scan(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in TEXT_SUFFIXES


def iter_files(paths: Iterable[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file():
            if should_scan(path):
                yield path
            continue
        if not path.exists():
            continue
        for child in path.rglob("*"):
            if any(part in SKIP_DIRS for part in child.parts):
                continue
            if should_scan(child):
                yield child


def is_safe_sample(line: str) -> bool:
    if any(marker in line for marker in SAFE_MARKERS):
        return True
    # Unicode ellipsis is used in documentation placeholders, but it must not mask a hard token pattern.
    if "…" in line:
        return not any(pattern.search(line) for _name, pattern in SECRET_PATTERNS)
    return False


def scan_file(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return findings
    for line_no, line in enumerate(lines, start=1):
        if is_safe_sample(line):
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                snippet = pattern.sub("[REDACTED]", line.strip())[:220]
                findings.append(Finding(str(path), line_no, name, snippet))
    return findings


def scan_paths(paths: Iterable[str | Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(Path(p) for p in paths):
        findings.extend(scan_file(path))
    return findings


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    findings = scan_paths(args.paths)
    print(json.dumps([dataclasses.asdict(f) for f in findings], indent=2))
    raise SystemExit(1 if findings else 0)
