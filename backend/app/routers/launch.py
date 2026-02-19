"""Launch orchestration API."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.agents.orchestrator import MainOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    LaunchDeleteResponse,
    LaunchHistoryListResponse,
    LaunchRunRequest,
    LaunchRunResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/launch/run", response_model=LaunchRunResponse)
async def run_launch(request_body: LaunchRunRequest, request: Request) -> LaunchRunResponse:
    orchestrator: MainOrchestrator = request.app.state.orchestrator
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    try:
        launch_package = await orchestrator.run(request_body)
    except asyncio.TimeoutError:
        logger.error("Orchestration timed out for '%s'", request_body.brief.product_name)
        raise HTTPException(status_code=504, detail="에이전트 실행 시간이 초과되었습니다. 다시 시도해 주세요.")
    except Exception:
        logger.exception("Orchestration failed for '%s'", request_body.brief.product_name)
        raise HTTPException(status_code=500, detail="오케스트레이션 실행 중 오류가 발생했습니다.")
    history_repository.save_run(mode=request_body.mode, launch_package=launch_package)
    return LaunchRunResponse(package=launch_package)


@router.get("/launch/history", response_model=LaunchHistoryListResponse)
async def list_launch_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str = Query(default="", max_length=120),
) -> LaunchHistoryListResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    items, total = history_repository.list_runs(limit=limit, offset=offset, query=q)
    has_more = offset + len(items) < total
    return LaunchHistoryListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
        query=q,
    )


@router.get("/launch/history/{request_id}", response_model=LaunchRunResponse)
async def get_launch_history(request_id: str, request: Request) -> LaunchRunResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    launch_package = history_repository.get_run(request_id=request_id)
    if launch_package is None:
        raise HTTPException(status_code=404, detail="Launch run not found")
    return LaunchRunResponse(package=launch_package)


@router.delete("/launch/history/{request_id}", response_model=LaunchDeleteResponse)
async def delete_launch_history(request_id: str, request: Request) -> LaunchDeleteResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    deleted = history_repository.delete_run(request_id=request_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Launch run not found")
    return LaunchDeleteResponse(deleted=True)
