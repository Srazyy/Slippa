"""
SQLite database layer for Slippa job persistence.

Stores jobs so they survive server restarts. Uses a single
'jobs' table with JSON-serialized clips data.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "slippa.db")


@contextmanager
def _conn():
    """Yield a connection with WAL mode and auto-commit."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create the jobs table if it doesn't exist."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id          TEXT PRIMARY KEY,
                status      TEXT NOT NULL DEFAULT 'starting',
                progress    TEXT NOT NULL DEFAULT 'Starting...',
                video_title TEXT DEFAULT '',
                source      TEXT DEFAULT '',
                error       TEXT,
                clips       TEXT DEFAULT '[]',
                batch       INTEGER DEFAULT 0,
                created_at  TEXT NOT NULL
            )
        """)


def _row_to_dict(row) -> dict:
    """Convert a sqlite3.Row to the same dict format web.py expects."""
    d = dict(row)
    d["clips"] = json.loads(d["clips"]) if d["clips"] else []
    d["batch"] = bool(d["batch"])
    return d


# ---- CRUD ----

def create_job(job_id: str, source: str, batch: bool = False) -> dict:
    """Insert a new job and return its dict."""
    now = datetime.now().isoformat()
    status = "queued" if batch else "starting"
    progress = "Queued..." if batch else "Starting..."

    with _conn() as conn:
        conn.execute(
            """INSERT INTO jobs (id, status, progress, source, batch, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (job_id, status, progress, source, int(batch), now),
        )

    return {
        "id": job_id,
        "status": status,
        "progress": progress,
        "video_title": "",
        "source": source,
        "error": None,
        "clips": [],
        "batch": batch,
        "created_at": now,
    }


def get_job(job_id: str) -> dict | None:
    """Fetch one job by ID. Returns None if not found."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_job(job_id: str, **fields):
    """Update specific fields on a job.

    Usage:
        update_job("abc123", status="done", progress="All done!")
    """
    allowed = {"status", "progress", "video_title", "source", "error", "clips", "batch"}
    updates = {}
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "clips":
            v = json.dumps(v)
        if k == "batch":
            v = int(v)
        updates[k] = v

    if not updates:
        return

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [job_id]

    with _conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)


def list_jobs(limit: int = 100) -> list[tuple[str, dict]]:
    """Return all jobs as (id, dict) tuples, newest first."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [(row["id"], _row_to_dict(row)) for row in rows]
