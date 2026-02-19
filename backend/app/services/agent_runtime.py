"""Runtime wrapper that enforces live OpenAI Agent SDK calls."""

from __future__ import annotations

import os
from typing import TypeVar

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
        except Exception:
            logger.exception("Agent SDK Runner.run failed for '%s'", agent_name)
            return None

        return self._coerce_output(final_output=final_output, output_type=output_type)

    def _coerce_output(self, *, final_output: object, output_type: type[OutputT]) -> OutputT | None:
        try:
            if isinstance(final_output, output_type):
                return final_output

            if isinstance(final_output, str):
                return output_type.model_validate(
                    {
                        "summary": final_output,
                        "key_points": [],
                        "risks": [],
                        "artifacts": {"source": "sdk-string"},
                    }
                )

            if isinstance(final_output, dict):
                return output_type.model_validate(final_output)

            if hasattr(final_output, "model_dump"):
                model_dump = getattr(final_output, "model_dump")
                if callable(model_dump):
                    return output_type.model_validate(model_dump())
        except ValidationError:
            logger.warning("Output validation failed for %s", output_type.__name__)
            return None

        try:
            return output_type.model_validate(
                {
                    "summary": str(final_output),
                    "key_points": [],
                    "risks": [],
                    "artifacts": {"source": "sdk-fallback-stringified"},
                }
            )
        except ValidationError:
            return None
