"""FastAPI entrypoint."""

from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.agents import ChatOrchestrator, MainOrchestrator
from app.core.config import get_settings
from app.repositories import SQLiteHistoryRepository
from app.routers import chat, launch, voice
from app.services import AgentRuntime, VoiceService

settings = get_settings()
app = FastAPI(title=settings.app_name)

# Static files for assets
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if not os.path.exists(static_path):
    os.makedirs(static_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runtime = AgentRuntime(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    use_agent_sdk=settings.use_agent_sdk,
)
orchestrator = MainOrchestrator(runtime=runtime)
chat_orchestrator = ChatOrchestrator()
voice_service = VoiceService()
history_repository = SQLiteHistoryRepository(db_path=settings.db_path)
app.state.orchestrator = orchestrator
app.state.chat_orchestrator = chat_orchestrator
app.state.voice_service = voice_service
app.state.settings = settings
app.state.history_repository = history_repository

app.include_router(launch.router, prefix=settings.api_prefix, tags=["launch"])
app.include_router(chat.router, prefix=settings.api_prefix, tags=["chat"])
app.include_router(voice.router, prefix=settings.api_prefix, tags=["voice"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
