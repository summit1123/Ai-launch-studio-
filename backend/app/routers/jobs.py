"""Async jobs API."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import JobGetResponse, JobListResponse
from app.services import MediaJobsService

router = APIRouter()


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
