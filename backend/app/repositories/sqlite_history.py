"""SQLite storage for launch run history."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from app.schemas import LaunchHistoryItem, LaunchPackage


class SQLiteHistoryRepository:
    """Persists launch outputs for replay and audit."""

    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path).expanduser().resolve()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS launch_runs (
                    request_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    core_kpi TEXT NOT NULL,
                    package_json TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_run(self, *, mode: str, launch_package: LaunchPackage) -> None:
        payload = launch_package.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO launch_runs (
                    request_id,
                    created_at,
                    mode,
                    product_name,
                    core_kpi,
                    package_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    launch_package.request_id,
                    launch_package.created_at.isoformat(),
                    mode,
                    launch_package.brief.product_name,
                    launch_package.brief.core_kpi,
                    payload,
                ),
            )
            conn.commit()

    def list_runs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        query: str = "",
    ) -> tuple[list[LaunchHistoryItem], int]:
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        safe_query = query.strip()
        like_query = f"%{safe_query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT request_id, created_at, mode, product_name, core_kpi
                FROM launch_runs
                WHERE (
                    ? = ''
                    OR product_name LIKE ? COLLATE NOCASE
                    OR core_kpi LIKE ? COLLATE NOCASE
                )
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (safe_query, like_query, like_query, safe_limit, safe_offset),
            ).fetchall()
            total_row = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM launch_runs
                WHERE (
                    ? = ''
                    OR product_name LIKE ? COLLATE NOCASE
                    OR core_kpi LIKE ? COLLATE NOCASE
                )
                """,
                (safe_query, like_query, like_query),
            ).fetchone()

        items = [self._row_to_history_item(row) for row in rows]
        total = int(total_row["total"]) if total_row else len(items)
        return items, total

    def get_run(self, *, request_id: str) -> LaunchPackage | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT package_json FROM launch_runs WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        if row is None:
            return None
        package_json = row["package_json"]
        return LaunchPackage.model_validate_json(package_json)

    def delete_run(self, *, request_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM launch_runs WHERE request_id = ?",
                (request_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    @staticmethod
    def _row_to_history_item(row: sqlite3.Row) -> LaunchHistoryItem:
        payload: dict[str, Any] = {
            "request_id": row["request_id"],
            "created_at": row["created_at"],
            "mode": row["mode"],
            "product_name": row["product_name"],
            "core_kpi": row["core_kpi"],
        }
        return LaunchHistoryItem.model_validate(payload)
