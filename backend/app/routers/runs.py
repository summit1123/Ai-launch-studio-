"""Run generation API for session-based workflow."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Request

from app.agents import ChatOrchestrator, MainOrchestrator
from app.repositories import SQLiteHistoryRepository
from app.schemas import (
    BriefSlots,
    LaunchBrief,
    LaunchRunRequest,
    RunGenerateResponse,
    RunGetResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


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

    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state="RUN_RESEARCH",
        brief_slots=record.brief_slots,
        completeness=gate.completeness,
    )

    launch_request = LaunchRunRequest(
        brief=_to_launch_brief(record.brief_slots),
        mode=record.mode,
    )
    try:
        launch_package = await asyncio.wait_for(orchestrator.run(launch_request), timeout=180)
    except asyncio.TimeoutError:
        history_repository.update_chat_state_and_slots(
            session_id=session_id,
            state="FAILED",
            brief_slots=record.brief_slots,
            completeness=gate.completeness,
        )
        raise HTTPException(status_code=504, detail="Run generation timed out")
    except Exception:
        logger.exception("Run generation failed for session '%s'", session_id)
        history_repository.update_chat_state_and_slots(
            session_id=session_id,
            state="FAILED",
            brief_slots=record.brief_slots,
            completeness=gate.completeness,
        )
        raise HTTPException(status_code=500, detail="Run generation failed")

    history_repository.save_run(mode=record.mode, launch_package=launch_package)
    run_id = history_repository.save_run_output(
        session_id=session_id,
        launch_package=launch_package,
        state="DONE",
    )
    history_repository.update_chat_state_and_slots(
        session_id=session_id,
        state="DONE",
        brief_slots=record.brief_slots,
        completeness=gate.completeness,
    )
    return RunGenerateResponse(run_id=run_id, session_id=session_id, state="DONE")


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


def _to_launch_brief(slots: BriefSlots) -> LaunchBrief:
    goal = slots.goal.weekly_goal or "inquiry"
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
        video_seconds=8,
    )
