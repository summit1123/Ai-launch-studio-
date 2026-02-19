"""Tests for AgentRuntime output coercion."""

from app.schemas import BizPlanningOutput
from app.services.agent_runtime import AgentRuntime


def test_coerce_output_repairs_biz_planning_numeric_map() -> None:
    runtime = AgentRuntime(model="gpt-5.2", api_key=None, use_agent_sdk=False)
    raw_output = {
        "summary": "예산안을 수립했습니다.",
        "key_points": "퍼포먼스 집중, 리타겟팅 강화",
        "risks": "광고 단가 상승",
        "budget_split_krw": {
            "performance": "70,000,000원",
            "crm": "15000000",
            "content": 12000000.2,
        },
        "kpi_targets": "주간 문의 120건, 전환율 2.8%",
    }

    result = runtime._coerce_output(
        final_output=raw_output,
        output_type=BizPlanningOutput,
    )

    assert result is not None
    assert result.summary == "예산안을 수립했습니다."
    assert result.budget_split_krw["performance"] == 70_000_000
    assert result.budget_split_krw["crm"] == 15_000_000
    assert result.budget_split_krw["content"] == 12_000_000
    assert len(result.kpi_targets) >= 2


def test_coerce_output_falls_back_when_summary_is_missing() -> None:
    runtime = AgentRuntime(model="gpt-5.2", api_key=None, use_agent_sdk=False)
    raw_output = {
        "budget_split_krw": {
            "performance": "정보 없음",
        },
    }

    result = runtime._coerce_output(
        final_output=raw_output,
        output_type=BizPlanningOutput,
    )

    assert result is not None
    assert result.summary.strip() != ""
