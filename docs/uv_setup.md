# uv 개발환경 설정 가이드

## 1. 사전 요구사항
- Python 3.11 이상
- Node.js 20 이상
- `uv` 설치

uv 설치:
- macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows(PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

## 2. 백엔드 설정
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

실행:
```bash
uv run uvicorn app.main:app --reload --port 8000
```

## 3. 프론트엔드 설정
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/frontend
npm install
npm run dev
```

선택 환경 변수:
```bash
export VITE_API_BASE_URL=http://localhost:8000/api
```

## 4. 필수 환경 변수
백엔드 `.env` 예시:
```bash
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-5.2
USE_AGENT_SDK=true
DB_PATH=launch_studio.db
```

## 5. 팀 온보딩 체크리스트
1. 레포 클론
2. 백엔드 실행(uv)
3. 프론트 실행
4. 헬스체크 확인
5. 실행 1회 후 이력 저장 확인

## 6. 트러블슈팅
- `Invalid username or token`: `gh auth login`으로 재인증
- `OPENAI_API_KEY` 누락: 미디어 생성 스킵됨
- 프론트-백엔드 연결 실패: `VITE_API_BASE_URL` 확인
