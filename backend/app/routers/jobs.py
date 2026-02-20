"""Async jobs API."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from app.schemas import JobGetResponse, JobListResponse
from app.services import MediaJobsService

router = APIRouter()


def _serialize_record(record: object) -> dict[str, object]:
    if not hasattr(record, "job_id"):
        return {}
    return {
        "job_id": getattr(record, "job_id"),
        "type": getattr(record, "type"),
        "status": getattr(record, "status"),
        "progress": getattr(record, "progress"),
        "note": getattr(record, "note"),
        "session_id": getattr(record, "session_id"),
        "run_id": getattr(record, "run_id"),
        "error": getattr(record, "error"),
        "created_at": getattr(record, "created_at"),
        "updated_at": getattr(record, "updated_at"),
    }


def _sse_event(event_type: str, data: dict[str, object]) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/jobs/{job_id}", response_model=JobGetResponse)
async def get_job(job_id: str, request: Request) -> JobGetResponse:
    media_jobs: MediaJobsService = request.app.state.media_jobs
    record = media_jobs.get_job(job_id=job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobGetResponse(
        job_id=record.job_id,
        type=record.type,
        status=record.status,
        progress=record.progress,
        note=record.note,
        session_id=record.session_id,
        run_id=record.run_id,
        error=record.error,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    request: Request,
    run_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobListResponse:
    media_jobs: MediaJobsService = request.app.state.media_jobs
    records, total = media_jobs.list_jobs(
        run_id=run_id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return JobListResponse(
        items=[
            JobGetResponse(
                job_id=record.job_id,
                type=record.type,
                status=record.status,
                progress=record.progress,
                note=record.note,
                session_id=record.session_id,
                run_id=record.run_id,
                error=record.error,
                created_at=datetime.fromisoformat(record.created_at),
                updated_at=datetime.fromisoformat(record.updated_at),
            )
            for record in records
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job(
    job_id: str,
    request: Request,
    poll_ms: int = Query(default=350, ge=100, le=2_000),
    timeout_seconds: int = Query(default=1_800, ge=3, le=7_200),
) -> StreamingResponse:
    media_jobs: MediaJobsService = request.app.state.media_jobs
    existing = media_jobs.get_job(job_id=job_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def _event_stream():
        elapsed = 0.0
        poll_seconds = poll_ms / 1_000
        last_signature: tuple[str, int, str, str | None, str | None] | None = None

        while elapsed <= timeout_seconds:
            if await request.is_disconnected():
                return

            current = media_jobs.get_job(job_id=job_id)
            if current is None:
                yield _sse_event(
                    "error",
                    {"message": "Job not found while streaming", "job_id": job_id},
                )
                return

            signature = (
                current.status,
                current.progress,
                current.updated_at,
                current.run_id,
                current.error,
            )
            if signature != last_signature:
                event_type = "job.progress"
                if last_signature is None:
                    event_type = "job.snapshot"
                elif current.status == "completed":
                    event_type = "job.completed"
                elif current.status == "failed":
                    event_type = "job.failed"
                payload = _serialize_record(current)
                yield _sse_event(event_type, payload)
                last_signature = signature

            if current.status in {"completed", "failed"}:
                return

            await asyncio.sleep(poll_seconds)
            elapsed += poll_seconds

        yield _sse_event(
            "error",
            {
                "message": "Job stream timed out before completion",
                "job_id": job_id,
                "timeout_seconds": timeout_seconds,
            },
        )

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )
