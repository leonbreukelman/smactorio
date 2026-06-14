#!/usr/bin/env python3
"""SQLite state for SmactorIO runtime runs.

The database is runtime state and must live outside the git repository in
normal service operation.
"""
from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS work_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_key TEXT NOT NULL UNIQUE,
  issue_number INTEGER NOT NULL,
  issue_url TEXT NOT NULL,
  title TEXT NOT NULL,
  branch TEXT NOT NULL,
  run_id TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'planned',
  pr_url TEXT,
  merge_commit TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  work_item_id INTEGER NOT NULL,
  from_state TEXT,
  to_state TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(work_item_id) REFERENCES work_items(id)
);
CREATE TABLE IF NOT EXISTS run_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issue_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo TEXT NOT NULL,
  issue_number INTEGER NOT NULL,
  run_id TEXT NOT NULL,
  durable_state TEXT NOT NULL,
  failure_class TEXT NOT NULL,
  failure_signature TEXT NOT NULL,
  base_sha TEXT,
  head_sha TEXT,
  evidence_ref TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 1,
  first_seen_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(repo, issue_number, failure_signature)
);
"""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def default_state_db() -> Path:
    raw = os.environ.get("SMACTORIO_STATE_DB")
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".local" / "state" / "smactorio" / "smactorio.sqlite"


def init_db(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path is not None else default_state_db()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def path_is_inside(path: str | Path, root: str | Path) -> bool:
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def upsert_work_item(
    conn: sqlite3.Connection,
    *,
    work_key: str,
    issue_number: int,
    issue_url: str,
    title: str,
    branch: str,
    run_id: str,
) -> int:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO work_items(work_key, issue_number, issue_url, title, branch, run_id, state, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, 'planned', ?, ?)
        ON CONFLICT(work_key) DO UPDATE SET
          issue_url=excluded.issue_url,
          title=excluded.title,
          branch=excluded.branch,
          run_id=excluded.run_id,
          updated_at=excluded.updated_at
        """,
        (work_key, issue_number, issue_url, title, branch, run_id, now, now),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM work_items WHERE work_key = ?", (work_key,)).fetchone()
    if row is None:
        raise RuntimeError(f"failed to upsert work item {work_key}")
    return int(row[0])


def transition(conn: sqlite3.Connection, work_item_id: int, from_state: str | None, to_state: str, reason: str) -> None:
    now = utc_now()
    conn.execute(
        "INSERT INTO transitions(work_item_id, from_state, to_state, reason, created_at) VALUES (?, ?, ?, ?, ?)",
        (work_item_id, from_state, to_state, reason, now),
    )
    conn.execute("UPDATE work_items SET state = ?, updated_at = ? WHERE id = ?", (to_state, now, work_item_id))
    conn.commit()


def set_pr(conn: sqlite3.Connection, work_item_id: int, *, pr_url: str, merge_commit: str | None = None) -> None:
    now = utc_now()
    conn.execute(
        "UPDATE work_items SET pr_url = ?, merge_commit = COALESCE(?, merge_commit), updated_at = ? WHERE id = ?",
        (pr_url, merge_commit, now, work_item_id),
    )
    conn.commit()


def record_issue_attempt(
    conn: sqlite3.Connection,
    *,
    repo: str,
    issue_number: int,
    run_id: str,
    durable_state: str,
    failure_class: str,
    failure_signature: str,
    base_sha: str | None = None,
    head_sha: str | None = None,
    evidence_ref: str | None = None,
) -> None:
    """Persist a durable attempt ledger entry for bounded retry decisions.

    Entries are keyed by repository, issue, and failure signature so service
    restarts/reopened connections increment the same retry bucket instead of
    losing context and leaving issues in permanent claimed/blocked limbo.
    """
    now = utc_now()
    conn.execute(
        """
        INSERT INTO issue_attempts(
          repo, issue_number, run_id, durable_state, failure_class, failure_signature,
          base_sha, head_sha, evidence_ref, attempt_count, first_seen_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(repo, issue_number, failure_signature) DO UPDATE SET
          run_id=excluded.run_id,
          durable_state=excluded.durable_state,
          failure_class=excluded.failure_class,
          base_sha=excluded.base_sha,
          head_sha=excluded.head_sha,
          evidence_ref=excluded.evidence_ref,
          attempt_count=issue_attempts.attempt_count + 1,
          updated_at=excluded.updated_at
        """,
        (repo, issue_number, run_id, durable_state, failure_class, failure_signature, base_sha, head_sha, evidence_ref, now, now),
    )
    conn.commit()


def issue_attempts(conn: sqlite3.Connection, *, repo: str, issue_number: int) -> list[dict[str, object]]:
    rows = conn.execute(
        """
        SELECT repo, issue_number, run_id, durable_state, failure_class, failure_signature,
               base_sha, head_sha, evidence_ref, attempt_count, first_seen_at, updated_at
        FROM issue_attempts
        WHERE repo = ? AND issue_number = ?
        ORDER BY updated_at DESC, id DESC
        """,
        (repo, issue_number),
    ).fetchall()
    keys = [
        "repo",
        "issue_number",
        "run_id",
        "durable_state",
        "failure_class",
        "failure_signature",
        "base_sha",
        "head_sha",
        "evidence_ref",
        "attempt_count",
        "first_seen_at",
        "updated_at",
    ]
    return [dict(zip(keys, row, strict=True)) for row in rows]


def exhausted_issue_attempt(
    conn: sqlite3.Connection,
    *,
    repo: str,
    issue_number: int,
    max_attempts: int,
    failure_signature_prefix: str | None = None,
) -> dict[str, object] | None:
    query = """
        SELECT repo, issue_number, run_id, durable_state, failure_class, failure_signature,
               base_sha, head_sha, evidence_ref, attempt_count, first_seen_at, updated_at
        FROM issue_attempts
        WHERE repo = ? AND issue_number = ? AND attempt_count >= ?
    """
    params: tuple[object, ...] = (repo, issue_number, max_attempts)
    if failure_signature_prefix:
        query += " AND failure_signature LIKE ?"
        params = (*params, f"{failure_signature_prefix}%")
    query += """
        ORDER BY attempt_count DESC, updated_at DESC, id DESC
        LIMIT 1
    """
    row = conn.execute(query, params).fetchone()
    if row is None:
        return None
    keys = [
        "repo",
        "issue_number",
        "run_id",
        "durable_state",
        "failure_class",
        "failure_signature",
        "base_sha",
        "head_sha",
        "evidence_ref",
        "attempt_count",
        "first_seen_at",
        "updated_at",
    ]
    return dict(zip(keys, row, strict=True))
