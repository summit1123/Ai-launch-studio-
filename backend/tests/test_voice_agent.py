"""Tests for voice preset agent."""

from app.agents.voice_agent import VoiceAgent


def test_voice_agent_formats_question_by_preset() -> None:
    agent = VoiceAgent()
    friendly = agent.format_question(question="주요 타겟 고객은 누구인가요?", preset="friendly_ko")
    calm = agent.format_question(question="주요 타겟 고객은 누구인가요?", preset="calm_ko")

    assert friendly.startswith("좋아요.")
    assert calm.startswith("천천히 정리해볼게요.")
    assert friendly != calm


def test_voice_agent_tts_profile_contains_pace() -> None:
    agent = VoiceAgent()
    profile = agent.tts_profile("neutral_ko")
    assert profile["preset"] == "neutral_ko"
    assert profile["pace"] == "medium"


def test_voice_agent_supports_cute_preset() -> None:
    agent = VoiceAgent()
    cute = agent.format_question(question="채널은 어디로 갈까요?", preset="cute_ko")

    assert cute.startswith("좋아요.")
    profile = agent.tts_profile("cute_ko")
    assert profile["preset"] == "cute_ko"
    assert profile["pace"] == "medium"
