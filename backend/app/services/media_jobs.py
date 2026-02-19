"""In-memory async job registry for long-running generation tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Literal
from uuid import uuid4

JobStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class MediaJobRecord:
    job_id: str
    type: str
    status: JobStatus
    progress: int
    session_id: str
    run_id: str | None
    error: str | None
    created_at: str
    updated_at: str


class MediaJobsService:
    """Tracks asynchronous job state for polling endpoints."""

    def __init__(self) -> None:
        self._jobs: dict[str, MediaJobRecord] = {}
        self._lock = Lock()

    def create_job(self, *, job_type: str, session_id: str) -> MediaJobRecord:
        now = self._utc_now()
        job = MediaJobRecord(
            job_id=f"job_{uuid4().hex[:16]}",
            type=job_type,
            status="queued",
            progress=0,
            session_id=session_id,
            run_id=None,
            error=None,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def mark_running(self, *, job_id: str, progress: int = 10) -> MediaJobRecord | None:
        return self._mutate(job_id=job_id, status="running", progress=progress, error=None)

    def mark_progress(self, *, job_id: str, progress: int) -> MediaJobRecord | None:
        return self._mutate(job_id=job_id, progress=progress)

    def mark_completed(
        self,
        *,
        job_id: str,
        run_id: str | None = None,
    ) -> MediaJobRecord | None:
        return self._mutate(
            job_id=job_id,
            status="completed",
            progress=100,
            run_id=run_id,
            error=None,
        )

    def mark_failed(self, *, job_id: str, error: str) -> MediaJobRecord | None:
        return self._mutate(
            job_id=job_id,
            status="failed",
            progress=100,
            error=error,
        )

    def get_job(self, *, job_id: str) -> MediaJobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None
            return self._copy(record)

    def list_jobs(
        self,
        *,
        run_id: str | None = None,
        session_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MediaJobRecord], int]:
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)

        with self._lock:
            items = [self._copy(job) for job in self._jobs.values()]

        if run_id:
            items = [item for item in items if item.run_id == run_id]
        if session_id:
            items = [item for item in items if item.session_id == session_id]

        items.sort(key=lambda item: item.created_at, reverse=True)
        total = len(items)
        sliced = items[safe_offset : safe_offset + safe_limit]
        return sliced, total

    def _mutate(
        self,
        *,
        job_id: str,
        status: JobStatus | None = None,
        progress: int | None = None,
        run_id: str | None = None,
        error: str | None = None,
    ) -> MediaJobRecord | None:
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return None

            if status is not None:
                record.status = status
            if progress is not None:
                record.progress = max(0, min(100, int(progress)))
            if run_id is not None:
                record.run_id = run_id
            if error is not None or status in {"running", "completed"}:
                record.error = error
            record.updated_at = self._utc_now()
            return self._copy(record)

    @staticmethod
    def _copy(record: MediaJobRecord) -> MediaJobRecord:
        return MediaJobRecord(
            job_id=record.job_id,
            type=record.type,
            status=record.status,
            progress=record.progress,
            session_id=record.session_id,
            run_id=record.run_id,
            error=record.error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
