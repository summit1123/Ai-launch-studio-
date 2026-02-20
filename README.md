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

### 외부 공유 데모 (Cloudflare Tunnel)
백엔드 + 프론트 + 터널 2개를 한 번에 실행:
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio
chmod +x run_public_cloudflare.sh
./run_public_cloudflare.sh
```

- 실행 후 터미널에 `Frontend Public URL`이 출력됩니다.
- 종료는 `Ctrl+C`.

### 고정 URL 운영 (Cloudflare Named Tunnel)
사전 조건:
- Cloudflare Zero Trust에서 Named Tunnel 생성
- Public Hostname 매핑 설정
  - 예: `app.example.com -> http://localhost:5050`
  - 예: `api.example.com -> http://localhost:8090`
- 터널 토큰 발급 (`CF_TUNNEL_TOKEN`)

실행:
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio
chmod +x run_public_cloudflare_named.sh
CF_TUNNEL_TOKEN='발급받은_토큰' \
PUBLIC_API_BASE_URL='https://api.example.com/api' \
./run_public_cloudflare_named.sh
```

- 이 모드는 URL을 스크립트가 생성하지 않습니다.
- 고정 URL은 Cloudflare 대시보드에서 미리 지정한 도메인을 그대로 사용합니다.

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
