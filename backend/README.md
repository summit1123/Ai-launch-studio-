# 백엔드

## 실행 (uv)
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv sync
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

## 테스트 실행
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv run pytest -q
```

## 의존성 관리
- 표준 파일: `pyproject.toml`, `uv.lock`
- 신규 의존성 추가 후 lock 갱신:
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv lock
uv sync --frozen
```
- `requirements.txt`는 레거시 호환용으로 유지

## 주요 엔드포인트
- `GET /health`
- `POST /api/launch/run`
- `GET /api/launch/history?limit=20&offset=0&q=`
- `GET /api/launch/history/{request_id}`
- `DELETE /api/launch/history/{request_id}`
- `POST /api/chat/session`
- `GET /api/chat/session/{session_id}`
- `POST /api/chat/session/{session_id}/message`

## 참고
- 미디어 생성은 `OPENAI_API_KEY`가 필요합니다.
- 생성 파일은 `/static/assets`로 서빙됩니다.
- SQLite 경로는 `DB_PATH`로 설정합니다.

세부 명세:
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/api.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/db_schema.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/backend_architecture.md`
