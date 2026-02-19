# AI Launch Studio

AI Launch Studio는 **제품을 이미 보유한 팀을 위한 프로모션 코파일럿**입니다.

사용자는 챗봇(추후 음성 포함)과 대화하면서 브리프를 채우고, 아래 결과를 받습니다.
- 시장 평가 및 포지셔닝 제안
- 주간 홍보 실행 플랜
- 광고 카피/포스터/영상 프롬프트
- 나레이션 스크립트 및 음성 합성 경로

## 빠른 실행

### 백엔드 (uv 권장)
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8000
```

### 프론트엔드
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/frontend
npm install
npm run dev
```

선택 환경 변수:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## 현재 API
- `GET /health`
- `POST /api/launch/run`
- `GET /api/launch/history`
- `GET /api/launch/history/{request_id}`
- `DELETE /api/launch/history/{request_id}`

## 문서 안내
전체 명세는 `docs/README.md`를 참고하세요.

## 참고
현재 코드 베이스는 폼 중심 흐름이 포함되어 있고,
목표 MVP(대화형/스트리밍/음성)는 문서 기준으로 단계적 반영합니다.
