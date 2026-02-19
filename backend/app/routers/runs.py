"""Run generation API for session-based workflow."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Request, status

from app.agents import ChatOrchestrator, MainOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    BriefSlots,
    LaunchBrief,
    LaunchPackage,
    LaunchRunRequest,
    RunGenerateAsyncResponse,
    RunGenerateResponse,
    RunGetResponse,
)
from app.services import MediaJobsService

logger = logging.getLogger(__name__)

router = APIRouter()
SYNC_RUN_TIMEOUT_SECONDS = 180
ASYNC_RUN_TIMEOUT_SECONDS = 1_800


@router.post("/runs/{session_id}/generate", response_model=RunGenerateResponse)
async def generate_run(session_id: str, request: Request) -> RunGenerateResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator
    orchestrator: MainOrchestrator = request.app.state.orchestrator

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    gate = chat_orchestrator.evaluate_gate(record.brief_slots)
    if not gate.ready:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "GATE_NOT_READY",
                "missing_required": gate.missing_required,
            },
        )

    try:
        run_id = await _run_pipeline(
            session_id=session_id,
            history_repository=history_repository,
            orchestrator=orchestrator,
            brief_slots=record.brief_slots,
            mode=record.mode,
            completeness=gate.completeness,
            timeout_seconds=SYNC_RUN_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        _set_session_failed(
            history_repository=history_repository,
            session_id=session_id,
            brief_slots=record.brief_slots,
            completeness=gate.completeness,
        )
        raise HTTPException(status_code=504, detail="Run generation timed out")
    except Exception:
        logger.exception("Run generation failed for session '%s'", session_id)
        _set_session_failed(
            history_repository=history_repository,
            session_id=session_id,
            brief_slots=record.brief_slots,
            completeness=gate.completeness,
        )
        raise HTTPException(status_code=500, detail="Run generation failed")

    return RunGenerateResponse(run_id=run_id, session_id=session_id, state="DONE")


@router.post(
    "/runs/{session_id}/generate/async",
    response_model=RunGenerateAsyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_run_async(session_id: str, request: Request) -> RunGenerateAsyncResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    chat_orchestrator: ChatOrchestrator = request.app.state.chat_orchestrator
    orchestrator: MainOrchestrator = request.app.state.orchestrator
    media_jobs: MediaJobsService = request.app.state.media_jobs

    record = history_repository.get_chat_session(session_id=session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Chat session not found")

    gate = chat_orchestrator.evaluate_gate(record.brief_slots)
    if not gate.ready:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "GATE_NOT_READY",
                "missing_required": gate.missing_required,
            },
        )

    job = media_jobs.create_job(job_type="run_generation", session_id=session_id)

    async def _worker() -> None:
        media_jobs.mark_running(job_id=job.job_id, progress=10)
        try:
            run_id = await _run_pipeline(
                session_id=session_id,
                history_repository=history_repository,
                orchestrator=orchestrator,
                brief_slots=record.brief_slots,
                mode=record.mode,
                completeness=gate.completeness,
                timeout_seconds=ASYNC_RUN_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            _set_session_failed(
                history_repository=history_repository,
                session_id=session_id,
                brief_slots=record.brief_slots,
                completeness=gate.completeness,
            )
            media_jobs.mark_failed(job_id=job.job_id, error="Run generation timed out")
            return
        except Exception as exc:
            logger.exception("Async run generation failed for session '%s'", session_id)
            _set_session_failed(
                history_repository=history_repository,
                session_id=session_id,
                brief_slots=record.brief_slots,
                completeness=gate.completeness,
            )
            media_jobs.mark_failed(job_id=job.job_id, error=str(exc))
            return

        media_jobs.mark_completed(job_id=job.job_id, run_id=run_id)

    def _run_worker() -> None:
        try:
            asyncio.run(_worker())
        except Exception:
            logger.exception("Async worker crashed for job '%s'", job.job_id)
            media_jobs.mark_failed(job_id=job.job_id, error="Async worker crashed")

    threading.Thread(target=_run_worker, daemon=True).start()

    return RunGenerateAsyncResponse(
        job_id=job.job_id,
        session_id=session_id,
        status=job.status,
    )


@router.get("/runs/{run_id}", response_model=RunGetResponse)
async def get_run(run_id: str, request: Request) -> RunGetResponse:
    history_repository: SQLiteHistoryRepository = request.app.state.history_repository
    record = history_repository.get_run_output(run_id=run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunGetResponse(
        run_id=record.run_id,
        session_id=record.session_id,
        state=record.state,
        package=record.package,
    )


async def _run_pipeline(
    *,
    session_id: str,
    history_repository: SQLiteHistoryRepository,
    orchestrator: MainOrchestrator,
    brief_slots: BriefSlots,
    mode: str,
    completeness: float,
    timeout_seconds: int,
) -> str:
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state="RUN_RESEARCH",
        brief_slots=brief_slots,
        completeness=completeness,
    )

    launch_request = LaunchRunRequest(
        brief=_to_launch_brief(brief_slots),
        mode=mode,
    )
    launch_package = await asyncio.wait_for(
        orchestrator.run(launch_request),
        timeout=timeout_seconds,
    )
    return _save_run_outputs(
        session_id=session_id,
        history_repository=history_repository,
        launch_package=launch_package,
        brief_slots=brief_slots,
        completeness=completeness,
        mode=mode,
    )


def _set_session_failed(
    *,
    history_repository: SQLiteHistoryRepository,
    session_id: str,
    brief_slots: BriefSlots,
    completeness: float,
) -> None:
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state="FAILED",
        brief_slots=brief_slots,
        completeness=completeness,
    )


def _save_run_outputs(
    *,
    session_id: str,
    history_repository: SQLiteHistoryRepository,
    launch_package: LaunchPackage,
    brief_slots: BriefSlots,
    completeness: float,
    mode: str,
) -> str:
    history_repository.save_run(mode=mode, launch_package=launch_package)
    run_id = history_repository.save_run_output(
        session_id=session_id,
        launch_package=launch_package,
        state="DONE",
    )
    _persist_media_assets(
        history_repository=history_repository,
        run_id=run_id,
        launch_package=launch_package,
    )
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state="DONE",
        brief_slots=brief_slots,
        completeness=completeness,
    )
    return run_id


def _to_launch_brief(slots: BriefSlots) -> LaunchBrief:
    goal = slots.goal.weekly_goal or "inquiry"
    safe_video_seconds = slots.goal.video_seconds
    if safe_video_seconds not in {5, 10, 15, 20}:
        safe_video_seconds = 10
    core_kpi_map = {
        "reach": "주간 조회수 증가",
        "inquiry": "주간 문의 증가",
        "purchase": "주간 구매 전환 증가",
    }
    core_kpi = core_kpi_map.get(goal, "주간 문의 증가")

    return LaunchBrief(
        product_name=slots.product.name or "미정 제품",
        product_category=slots.product.category or "기타",
        target_audience=slots.target.who or "미정 타겟",
        price_band=slots.product.price_band or "mid",
        total_budget_krw=1_000_000,
        launch_date=date.today() + timedelta(days=7),
        core_kpi=core_kpi,
        region="KR",
        channel_focus=slots.channel.channels,
        video_seconds=safe_video_seconds,
    )


def _persist_media_assets(
    *,
    history_repository: SQLiteHistoryRepository,
    run_id: str,
    launch_package: LaunchPackage,
) -> None:
    assets = launch_package.marketing_assets
    if assets.poster_image_url:
        history_repository.save_media_asset(
            run_id=run_id,
            asset_type="poster_image",
            local_path=assets.poster_image_url if assets.poster_image_url.startswith("/static/") else None,
            remote_url=assets.poster_image_url if assets.poster_image_url.startswith("http") else None,
            metadata={
                "headline": assets.poster_headline,
            },
        )
    if assets.video_url:
        history_repository.save_media_asset(
            run_id=run_id,
            asset_type="video",
            local_path=assets.video_url if assets.video_url.startswith("/static/") else None,
            remote_url=assets.video_url if assets.video_url.startswith("http") else None,
            metadata={
                "scene_count": len(assets.video_scene_plan),
            },
        )
