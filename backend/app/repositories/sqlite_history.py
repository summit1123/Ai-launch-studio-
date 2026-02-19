"""SQLite storage for launch run history."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.schemas import BriefSlots, ChatState, LaunchHistoryItem, LaunchPackage


@dataclass
class ChatSessionRecord:
    session_id: str
    state: ChatState
    mode: str
    locale: str
    created_at: str
    updated_at: str
    brief_slots: BriefSlots
    completeness: float


@dataclass
class RunOutputRecord:
    run_id: str
    session_id: str
    request_id: str
    state: ChatState
    created_at: str
    updated_at: str
    package: LaunchPackage


@dataclass
class MediaAssetRecord:
    asset_id: str
    run_id: str
    asset_type: str
    local_path: str | None
    remote_url: str | None
    metadata: dict[str, Any]
    created_at: str


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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    locale TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS brief_slots (
                    session_id TEXT PRIMARY KEY,
                    product_json TEXT NOT NULL,
                    target_json TEXT NOT NULL,
                    channel_json TEXT NOT NULL,
                    goal_json TEXT NOT NULL,
                    completeness REAL NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session_created
                ON chat_messages(session_id, created_at)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated
                ON chat_sessions(updated_at DESC)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS run_outputs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    package_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS media_assets (
                    asset_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    local_path TEXT,
                    remote_url TEXT,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(run_id) REFERENCES run_outputs(run_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_run_outputs_session_created
                ON run_outputs(session_id, created_at DESC)
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

    def create_chat_session(
        self,
        *,
        session_id: str,
        mode: str,
        locale: str,
        state: ChatState,
        brief_slots: BriefSlots,
        completeness: float = 0.0,
    ) -> None:
        now = self._utc_now()
        product_json, target_json, channel_json, goal_json = self._encode_slots(brief_slots)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (
                    session_id, state, mode, locale, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, state, mode, locale, now, now),
            )
            conn.execute(
                """
                INSERT INTO brief_slots (
                    session_id,
                    product_json,
                    target_json,
                    channel_json,
                    goal_json,
                    completeness,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    product_json,
                    target_json,
                    channel_json,
                    goal_json,
                    max(0.0, min(1.0, completeness)),
                    now,
                ),
            )
            conn.commit()

    def get_chat_session(self, *, session_id: str) -> ChatSessionRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    s.session_id,
                    s.state,
                    s.mode,
                    s.locale,
                    s.created_at,
                    s.updated_at,
                    b.product_json,
                    b.target_json,
                    b.channel_json,
                    b.goal_json,
                    b.completeness
                FROM chat_sessions AS s
                LEFT JOIN brief_slots AS b
                    ON b.session_id = s.session_id
                WHERE s.session_id = ?
                """,
                (session_id,),
            ).fetchone()

        if row is None:
            return None

        slots = self._decode_slots(
            product_json=row["product_json"],
            target_json=row["target_json"],
            channel_json=row["channel_json"],
            goal_json=row["goal_json"],
        )
        completeness = float(row["completeness"] or 0.0)
        return ChatSessionRecord(
            session_id=row["session_id"],
            state=row["state"],
            mode=row["mode"],
            locale=row["locale"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            brief_slots=slots,
            completeness=max(0.0, min(1.0, completeness)),
        )

    def append_chat_message(self, *, session_id: str, role: str, content: str) -> str:
        message_id = f"msg_{uuid4().hex[:16]}"
        created_at = self._utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (message_id, session_id, role, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (message_id, session_id, role, content, created_at),
            )
            conn.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?
                WHERE session_id = ?
                """,
                (created_at, session_id),
            )
            conn.commit()
        return message_id

    def list_chat_messages(self, *, session_id: str, limit: int = 100) -> list[dict[str, str]]:
        safe_limit = max(1, min(limit, 500))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, safe_limit),
            ).fetchall()
        return [
            {"role": row["role"], "content": row["content"], "created_at": row["created_at"]}
            for row in rows
        ]

    def update_chat_state_and_slots(
        self,
        *,
        session_id: str,
        state: ChatState,
        brief_slots: BriefSlots,
        completeness: float,
    ) -> None:
        now = self._utc_now()
        product_json, target_json, channel_json, goal_json = self._encode_slots(brief_slots)
        safe_completeness = max(0.0, min(1.0, completeness))
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE chat_sessions
                SET state = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (state, now, session_id),
            )
            conn.execute(
                """
                INSERT INTO brief_slots (
                    session_id,
                    product_json,
                    target_json,
                    channel_json,
                    goal_json,
                    completeness,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    product_json = excluded.product_json,
                    target_json = excluded.target_json,
                    channel_json = excluded.channel_json,
                    goal_json = excluded.goal_json,
                    completeness = excluded.completeness,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    product_json,
                    target_json,
                    channel_json,
                    goal_json,
                    safe_completeness,
                    now,
                ),
            )
            conn.commit()

    def save_run_output(
        self,
        *,
        session_id: str,
        launch_package: LaunchPackage,
        state: ChatState = "DONE",
    ) -> str:
        run_id = launch_package.request_id
        now = self._utc_now()
        package_json = launch_package.model_dump_json()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO run_outputs (
                    run_id,
                    session_id,
                    request_id,
                    state,
                    package_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    session_id,
                    launch_package.request_id,
                    state,
                    package_json,
                    now,
                    now,
                ),
            )
            conn.commit()
        return run_id

    def get_run_output(self, *, run_id: str) -> RunOutputRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT run_id, session_id, request_id, state, package_json, created_at, updated_at
                FROM run_outputs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        package = LaunchPackage.model_validate_json(row["package_json"])
        return RunOutputRecord(
            run_id=row["run_id"],
            session_id=row["session_id"],
            request_id=row["request_id"],
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            package=package,
        )

    def list_run_outputs(self, *, session_id: str, limit: int = 20, offset: int = 0) -> list[RunOutputRecord]:
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT run_id, session_id, request_id, state, package_json, created_at, updated_at
                FROM run_outputs
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (session_id, safe_limit, safe_offset),
            ).fetchall()

        results: list[RunOutputRecord] = []
        for row in rows:
            package = LaunchPackage.model_validate_json(row["package_json"])
            results.append(
                RunOutputRecord(
                    run_id=row["run_id"],
                    session_id=row["session_id"],
                    request_id=row["request_id"],
                    state=row["state"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    package=package,
                )
            )
        return results

    def save_media_asset(
        self,
        *,
        run_id: str,
        asset_type: str,
        local_path: str | None = None,
        remote_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        asset_id = f"asset_{uuid4().hex[:16]}"
        created_at = self._utc_now()
        metadata_payload = json.dumps(metadata or {}, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO media_assets (
                    asset_id,
                    run_id,
                    asset_type,
                    local_path,
                    remote_url,
                    metadata_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset_id,
                    run_id,
                    asset_type,
                    local_path,
                    remote_url,
                    metadata_payload,
                    created_at,
                ),
            )
            conn.commit()
        return asset_id

    def list_media_assets(self, *, run_id: str) -> list[MediaAssetRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, run_id, asset_type, local_path, remote_url, metadata_json, created_at
                FROM media_assets
                WHERE run_id = ?
                ORDER BY created_at ASC
                """,
                (run_id,),
            ).fetchall()

        results: list[MediaAssetRecord] = []
        for row in rows:
            metadata_raw = row["metadata_json"] or "{}"
            try:
                metadata = json.loads(metadata_raw)
            except json.JSONDecodeError:
                metadata = {}
            if not isinstance(metadata, dict):
                metadata = {}
            results.append(
                MediaAssetRecord(
                    asset_id=row["asset_id"],
                    run_id=row["run_id"],
                    asset_type=row["asset_type"],
                    local_path=row["local_path"],
                    remote_url=row["remote_url"],
                    metadata=metadata,
                    created_at=row["created_at"],
                )
            )
        return results

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

    @staticmethod
    def _encode_slots(brief_slots: BriefSlots) -> tuple[str, str, str, str]:
        return (
            json.dumps(brief_slots.product.model_dump(), ensure_ascii=False),
            json.dumps(brief_slots.target.model_dump(), ensure_ascii=False),
            json.dumps(brief_slots.channel.model_dump(), ensure_ascii=False),
            json.dumps(brief_slots.goal.model_dump(), ensure_ascii=False),
        )

    @staticmethod
    def _decode_slots(
        *,
        product_json: str | None,
        target_json: str | None,
        channel_json: str | None,
        goal_json: str | None,
    ) -> BriefSlots:
        def _safe_load(payload: str | None) -> dict[str, Any]:
            if not payload:
                return {}
            try:
                loaded = json.loads(payload)
            except json.JSONDecodeError:
                return {}
            if isinstance(loaded, dict):
                return loaded
            return {}

        return BriefSlots.model_validate(
            {
                "product": _safe_load(product_json),
                "target": _safe_load(target_json),
                "channel": _safe_load(channel_json),
                "goal": _safe_load(goal_json),
            }
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
