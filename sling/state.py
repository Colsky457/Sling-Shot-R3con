"""State management for scan persistence and resumption."""

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from .config import Config
from .logging import get_logger

logger = get_logger(__name__)


class ScanStatus(str, Enum):
    """Scan status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """Step status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StateManager:
    """Manages scan state persistence in SQLite."""

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.general.output_dir / "state.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    current_step TEXT,
                    config_snapshot TEXT
                );

                CREATE TABLE IF NOT EXISTS steps (
                    scan_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    output_path TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    PRIMARY KEY (scan_id, name),
                    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS artifacts (
                    scan_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    path TEXT NOT NULL,
                    count INTEGER DEFAULT 0,
                    created_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (scan_id, step_name, type),
                    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_scans_domain ON scans(domain);
                CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
                CREATE INDEX IF NOT EXISTS idx_steps_scan_id ON steps(scan_id);
                CREATE INDEX IF NOT EXISTS idx_artifacts_scan_id ON artifacts(scan_id);
            """)

    @contextmanager
    def _connect(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_scan(self, domain: str, config_snapshot: str = "") -> str:
        """Create a new scan record."""
        scan_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO scans (id, domain, created_at, updated_at, status, config_snapshot)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (scan_id, domain, now, now, ScanStatus.PENDING.value, config_snapshot)
            )
        logger.info("scan_created", scan_id=scan_id, domain=domain)
        return scan_id

    def update_scan_status(self, scan_id: str, status: ScanStatus, current_step: Optional[str] = None) -> None:
        """Update scan status."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            if current_step:
                conn.execute(
                    """UPDATE scans SET status = ?, current_step = ?, updated_at = ?
                       WHERE id = ?""",
                    (status.value, current_step, now, scan_id)
                )
            else:
                conn.execute(
                    """UPDATE scans SET status = ?, updated_at = ? WHERE id = ?""",
                    (status.value, now, scan_id)
                )

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get scan by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
            return dict(row) if row else None

    def get_scan_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all scans for a domain."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM scans WHERE domain = ? ORDER BY created_at DESC", (domain,)
            ).fetchall()
            return [dict(r) for r in rows]

    def list_scans(self, status: Optional[ScanStatus] = None) -> List[Dict[str, Any]]:
        """List all scans, optionally filtered by status."""
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM scans WHERE status = ? ORDER BY created_at DESC", (status.value,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM scans ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def create_step(self, scan_id: str, name: str) -> None:
        """Create a step record."""
        with self._connect() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO steps (scan_id, name, status)
                   VALUES (?, ?, ?)""",
                (scan_id, name, StepStatus.PENDING.value)
            )

    def update_step_status(
        self,
        scan_id: str,
        name: str,
        status: StepStatus,
        output_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Update step status."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            if status == StepStatus.RUNNING:
                conn.execute(
                    """UPDATE steps SET status = ?, started_at = ? WHERE scan_id = ? AND name = ?""",
                    (status.value, now, scan_id, name)
                )
            elif status in (StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED):
                conn.execute(
                    """UPDATE steps SET status = ?, completed_at = ?, output_path = ?, error = ?
                       WHERE scan_id = ? AND name = ?""",
                    (status.value, now, output_path, error, scan_id, name)
                )
            else:
                conn.execute(
                    """UPDATE steps SET status = ? WHERE scan_id = ? AND name = ?""",
                    (status.value, scan_id, name)
                )

    def increment_step_retry(self, scan_id: str, name: str) -> int:
        """Increment retry count for a step."""
        with self._connect() as conn:
            conn.execute(
                """UPDATE steps SET retry_count = retry_count + 1 WHERE scan_id = ? AND name = ?""",
                (scan_id, name)
            )
            row = conn.execute(
                "SELECT retry_count FROM steps WHERE scan_id = ? AND name = ?", (scan_id, name)
            ).fetchone()
            return row["retry_count"] if row else 0

    def get_step(self, scan_id: str, name: str) -> Optional[Dict[str, Any]]:
        """Get step by name."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM steps WHERE scan_id = ? AND name = ?", (scan_id, name)
            ).fetchone()
            return dict(row) if row else None

    def get_steps(self, scan_id: str) -> List[Dict[str, Any]]:
        """Get all steps for a scan."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM steps WHERE scan_id = ? ORDER BY started_at", (scan_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def add_artifact(
        self,
        scan_id: str,
        step_name: str,
        artifact_type: str,
        path: str,
        count: int = 0
    ) -> None:
        """Record an artifact produced by a step."""
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO artifacts (scan_id, step_name, type, path, count, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (scan_id, step_name, artifact_type, path, count, now)
            )

    def get_artifacts(self, scan_id: str, step_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get artifacts for a scan."""
        with self._connect() as conn:
            if step_name:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE scan_id = ? AND step_name = ?",
                    (scan_id, step_name)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM artifacts WHERE scan_id = ?", (scan_id,)
                ).fetchall()
            return [dict(r) for r in rows]

    def can_resume_step(self, scan_id: str, name: str) -> bool:
        """Check if a step can be resumed (already completed)."""
        step = self.get_step(scan_id, name)
        return step is not None and step["status"] == StepStatus.COMPLETED.value

    def get_last_completed_step(self, scan_id: str) -> Optional[str]:
        """Get the name of the last completed step."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT name FROM steps
                   WHERE scan_id = ? AND status = ?
                   ORDER BY completed_at DESC LIMIT 1""",
                (scan_id, StepStatus.COMPLETED.value)
            ).fetchone()
            return row["name"] if row else None