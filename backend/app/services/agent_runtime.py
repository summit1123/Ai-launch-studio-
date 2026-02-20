"""Runtime wrapper that enforces live OpenAI Agent SDK calls."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import TypeVar
from typing import get_origin

import logging

logger = logging.getLogger(__name__)

from pydantic import ValidationError

from app.schemas import AgentPayload, LaunchBrief

try:
    from agents import Agent, AgentOutputSchema, Runner

    HAS_AGENT_SDK = True
except Exception:
    Agent = None  # type: ignore[assignment]
    AgentOutputSchema = None  # type: ignore[assignment]
    Runner = None  # type: ignore[assignment]
    HAS_AGENT_SDK = False

OutputT = TypeVar("OutputT", bound=AgentPayload)


class AgentRuntime:
    """Execute agent prompts via the OpenAI Agents SDK only."""

    def __init__(self, model: str, api_key: str | None, use_agent_sdk: bool = True) -> None:
        self._model = model
        if api_key and "OPENAI_API_KEY" not in os.environ:
            os.environ["OPENAI_API_KEY"] = api_key

        self._sdk_enabled = use_agent_sdk and HAS_AGENT_SDK and bool(
            os.getenv("OPENAI_API_KEY")
        )

    @property
    def using_live_sdk(self) -> bool:
        return self._sdk_enabled

    async def run(
        self,
        *,
        agent_name: str,
        instructions: str,
        prompt: str,
        brief: LaunchBrief,
        output_type: type[OutputT],
    ) -> OutputT:
        _ = brief  # kept for compatibility with agent call sites
        self._assert_live_ready(agent_name=agent_name)

        output = await self._run_with_sdk(
            agent_name=agent_name,
            instructions=instructions,
            prompt=prompt,
            output_type=output_type,
        )
        if output is None:
            raise RuntimeError(
                f"Live SDK output validation failed for '{agent_name}'. "
                "No mock fallback is allowed."
            )
        return output

    def _assert_live_ready(self, *, agent_name: str) -> None:
        if self._sdk_enabled:
            return

        if not HAS_AGENT_SDK:
            raise RuntimeError(
                f"Agent SDK is not installed; cannot run '{agent_name}' without fallback."
            )

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError(
                f"OPENAI_API_KEY is missing; cannot run '{agent_name}' without fallback."
            )

        raise RuntimeError(
            f"Live SDK is disabled by configuration; cannot run '{agent_name}' without fallback."
        )

    async def _run_with_sdk(
        self,
        *,
        agent_name: str,
        instructions: str,
        prompt: str,
        output_type: type[OutputT],
    ) -> OutputT | None:
        if not HAS_AGENT_SDK:
            return None

        if Agent is None or Runner is None:
            return None

        kwargs: dict[str, object] = {
            "name": agent_name,
            "instructions": instructions,
        }
        wrapped_output_type: object = output_type
        if AgentOutputSchema is not None:
            try:
                wrapped_output_type = AgentOutputSchema(output_type, strict_json_schema=False)
            except Exception:
                wrapped_output_type = output_type
        kwargs["output_type"] = wrapped_output_type

        try:
            kwargs["model"] = self._model
            live_agent = Agent(**kwargs)
        except TypeError:
            kwargs.pop("model", None)
            live_agent = Agent(**kwargs)

        try:
            result = await Runner.run(starting_agent=live_agent, input=prompt)
            final_output = result.final_output
        except Exception as exc:
            logger.exception("Agent SDK Runner.run failed for '%s'", agent_name)
            recovered = self._recover_output_from_exception(
                exc=exc,
                output_type=output_type,
            )
            if recovered is not None:
                logger.warning(
                    "Recovered SDK output for '%s' from exception payload",
                    agent_name,
                )
            return recovered

        return self._coerce_output(final_output=final_output, output_type=output_type)

    def _coerce_output(self, *, final_output: object, output_type: type[OutputT]) -> OutputT | None:
        if isinstance(final_output, output_type):
            return final_output

        if isinstance(final_output, str):
            as_json = self._extract_json_dict_from_text(final_output)
            if as_json is not None:
                validated = self._validate_dict_output(
                    output_type=output_type,
                    payload=as_json,
                )
                if validated is not None:
                    return validated
            return self._validate_minimal_output(
                output_type=output_type,
                summary=final_output,
                source="sdk-string",
            )

        if isinstance(final_output, dict):
            validated = self._validate_dict_output(
                output_type=output_type,
                payload=final_output,
            )
            if validated is not None:
                return validated

        if hasattr(final_output, "model_dump"):
            model_dump = getattr(final_output, "model_dump")
            if callable(model_dump):
                dumped = model_dump()
                if isinstance(dumped, dict):
                    validated = self._validate_dict_output(
                        output_type=output_type,
                        payload=dumped,
                    )
                    if validated is not None:
                        return validated

        return self._validate_minimal_output(
            output_type=output_type,
            summary=str(final_output),
            source="sdk-fallback-stringified",
        )

    def _recover_output_from_exception(
        self,
        *,
        exc: Exception,
        output_type: type[OutputT],
    ) -> OutputT | None:
        payload = self._extract_json_dict_from_text(str(exc))
        if payload is None:
            return None
        validated = self._validate_dict_output(output_type=output_type, payload=payload)
        if validated is not None:
            return validated
        return self._validate_minimal_output(
            output_type=output_type,
            summary=self._extract_summary_candidate(payload),
            source="sdk-exception-recovery",
        )

    def _validate_dict_output(
        self,
        *,
        output_type: type[OutputT],
        payload: dict[str, object],
    ) -> OutputT | None:
        try:
            return output_type.model_validate(payload)
        except ValidationError:
            logger.warning(
                "Output validation failed for %s, attempting repair",
                output_type.__name__,
            )

        repaired = self._repair_output_payload(payload=payload, output_type=output_type)
        try:
            return output_type.model_validate(repaired)
        except ValidationError:
            logger.warning("Output repair failed for %s", output_type.__name__)
            return None

    def _validate_minimal_output(
        self,
        *,
        output_type: type[OutputT],
        summary: str,
        source: str,
    ) -> OutputT | None:
        safe_summary = summary.strip() or "에이전트 응답을 요약하지 못했습니다."
        try:
            return output_type.model_validate(
                {
                    "summary": safe_summary,
                    "key_points": [],
                    "risks": [],
                    "artifacts": {"source": source},
                }
            )
        except ValidationError:
            return None

    def _repair_output_payload(
        self,
        *,
        payload: dict[str, object],
        output_type: type[OutputT],
    ) -> dict[str, object]:
        repaired: dict[str, object] = dict(payload)

        summary = repaired.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            summary = self._extract_summary_candidate(repaired)
        repaired["summary"] = summary

        repaired["key_points"] = self._coerce_text_list(repaired.get("key_points"))
        repaired["risks"] = self._coerce_text_list(repaired.get("risks"))
        artifacts = repaired.get("artifacts")
        repaired["artifacts"] = artifacts if isinstance(artifacts, dict) else {}

        for key, value in list(repaired.items()):
            if key.endswith("_krw") and isinstance(value, Mapping):
                repaired[key] = self._coerce_int_dict(value)

        for field_name, field in output_type.model_fields.items():
            if field_name not in repaired:
                continue
            origin = get_origin(field.annotation)
            if origin is list:
                repaired[field_name] = self._coerce_text_list(repaired[field_name])
            elif origin is dict and not isinstance(repaired[field_name], dict):
                repaired[field_name] = {}

        return repaired

    @staticmethod
    def _extract_summary_candidate(payload: dict[str, object]) -> str:
        for key in ("overview", "result", "message", "text", "요약"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        compact = str(payload).strip()
        if len(compact) > 300:
            compact = compact[:300]
        return compact or "에이전트 응답 요약"

    @staticmethod
    def _coerce_text_list(value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            parts = re.split(r"[,\n/|;·]+", value)
            return [part.strip() for part in parts if part.strip()]
        item = str(value).strip()
        return [item] if item else []

    @staticmethod
    def _coerce_int_dict(value: Mapping[object, object]) -> dict[str, int]:
        converted: dict[str, int] = {}
        for key, raw in value.items():
            numeric = AgentRuntime._coerce_int(raw)
            if numeric is None:
                continue
            converted[str(key)] = numeric
        return converted

    @staticmethod
    def _coerce_int(raw: object) -> int | None:
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            return raw
        if isinstance(raw, float):
            return int(round(raw))
        if isinstance(raw, Mapping):
            for candidate_key in ("amount", "value", "krw", "cost", "budget"):
                if candidate_key in raw:
                    nested = AgentRuntime._coerce_int(raw[candidate_key])
                    if nested is not None:
                        return nested
            return None
        if isinstance(raw, str):
            cleaned = raw.replace(",", "").replace(" ", "")
            match = re.search(r"-?\d+", cleaned)
            if match:
                return int(match.group(0))
        return None

    @staticmethod
    def _extract_json_dict_from_text(text: str) -> dict[str, object] | None:
        if not text:
            return None

        start = text.find("{")
        if start < 0:
            return None

        depth = 0
        in_string = False
        escaped = False
        end = -1
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == "{":
                depth += 1
                continue
            if char == "}":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break

        if end <= start:
            return None

        candidate = text[start:end]
        try:
            parsed = json.loads(candidate)
        except Exception:
            return None

        if isinstance(parsed, dict):
            return parsed
        return None
