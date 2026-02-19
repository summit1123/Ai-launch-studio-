# 백엔드

## 실행 (uv)
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

## 주요 엔드포인트
- `GET /health`
- `POST /api/launch/run`
- `GET /api/launch/history?limit=20&offset=0&q=`
- `GET /api/launch/history/{request_id}`
- `DELETE /api/launch/history/{request_id}`

## 참고
- 미디어 생성은 `OPENAI_API_KEY`가 필요합니다.
- 생성 파일은 `/static/assets`로 서빙됩니다.
- SQLite 경로는 `DB_PATH`로 설정합니다.

세부 명세:
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/api.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/db_schema.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/backend_architecture.md`
