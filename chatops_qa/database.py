"""SQLite persistence for users, test runs, metrics, and audit events."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp suitable for SQLite text storage."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Small connection-per-operation SQLite repository for thread-safe use."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        """Commit or roll back the operation, then always release the connection."""

        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create normalized tables and indexes if this is a fresh database."""

        with self._session() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;

                CREATE TABLE IF NOT EXISTS slack_users (
                    slack_user_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS test_runs (
                    run_id TEXT PRIMARY KEY,
                    suite TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'passed', 'failed', 'error')),
                    slack_user_id TEXT NOT NULL REFERENCES slack_users(slack_user_id),
                    channel_id TEXT NOT NULL DEFAULT '',
                    requested_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    total_count INTEGER NOT NULL DEFAULT 0,
                    passed_count INTEGER NOT NULL DEFAULT 0,
                    failed_count INTEGER NOT NULL DEFAULT 0,
                    skipped_count INTEGER NOT NULL DEFAULT 0,
                    error_log TEXT NOT NULL DEFAULT '',
                    output_log TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS run_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES test_runs(run_id) ON DELETE CASCADE,
                    event_type TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    occurred_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_test_runs_requested_at
                    ON test_runs(requested_at DESC);
                CREATE INDEX IF NOT EXISTS idx_test_runs_user
                    ON test_runs(slack_user_id, requested_at DESC);
                CREATE INDEX IF NOT EXISTS idx_run_events_run
                    ON run_events(run_id, occurred_at);
                """
            )

    def create_run(
        self, *, suite: str, slack_user_id: str, display_name: str, channel_id: str
    ) -> str:
        """Create the user/run records and an audit event before starting work."""

        run_id = str(uuid4())
        timestamp = utc_now()
        with self._session() as connection:
            connection.execute(
                """INSERT INTO slack_users (slack_user_id, display_name, first_seen_at, last_seen_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(slack_user_id) DO UPDATE SET
                     display_name = excluded.display_name,
                     last_seen_at = excluded.last_seen_at""",
                (slack_user_id, display_name or slack_user_id, timestamp, timestamp),
            )
            connection.execute(
                """INSERT INTO test_runs
                   (run_id, suite, status, slack_user_id, channel_id, requested_at)
                   VALUES (?, ?, 'queued', ?, ?, ?)""",
                (run_id, suite, slack_user_id, channel_id, timestamp),
            )
            self._insert_event(connection, run_id, "requested", {"suite": suite}, timestamp)
        return run_id

    def mark_started(self, run_id: str) -> None:
        timestamp = utc_now()
        with self._session() as connection:
            connection.execute(
                "UPDATE test_runs SET status = 'running', started_at = ? WHERE run_id = ?",
                (timestamp, run_id),
            )
            self._insert_event(connection, run_id, "started", {}, timestamp)

    def finish_run(self, run_id: str, result: dict[str, Any]) -> None:
        timestamp = utc_now()
        with self._session() as connection:
            connection.execute(
                """UPDATE test_runs SET status = ?, finished_at = ?, duration_ms = ?,
                   total_count = ?, passed_count = ?, failed_count = ?, skipped_count = ?,
                   error_log = ?, output_log = ? WHERE run_id = ?""",
                (
                    result["status"],
                    timestamp,
                    result["duration_ms"],
                    result["total_count"],
                    result["passed_count"],
                    result["failed_count"],
                    result["skipped_count"],
                    result["error_log"],
                    result["output_log"],
                    run_id,
                ),
            )
            self._insert_event(
                connection,
                run_id,
                "finished",
                {
                    "status": result["status"],
                    "total_count": result["total_count"],
                    "passed_count": result["passed_count"],
                    "failed_count": result["failed_count"],
                    "skipped_count": result["skipped_count"],
                },
                timestamp,
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._session() as connection:
            row = connection.execute(
                "SELECT * FROM test_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    def history(self, limit: int = 5) -> list[dict[str, Any]]:
        """Return recent runs, joined to the Slack display name that triggered them."""

        bounded_limit = max(1, min(int(limit), 20))
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT r.*, u.display_name
                   FROM test_runs AS r
                   JOIN slack_users AS u ON u.slack_user_id = r.slack_user_id
                   ORDER BY r.requested_at DESC
                   LIMIT ?""",
                (bounded_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        run_id: str,
        event_type: str,
        details: dict[str, Any],
        timestamp: str,
    ) -> None:
        connection.execute(
            """INSERT INTO run_events (run_id, event_type, details_json, occurred_at)
               VALUES (?, ?, ?, ?)""",
            (run_id, event_type, json.dumps(details, sort_keys=True), timestamp),
        )
