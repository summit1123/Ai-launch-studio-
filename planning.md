# AI Launch Studio 챗+음성 MVP 상세 실행 계획 (커밋 단위)

## 0. 목적
- 채팅 입력과 음성 입력을 모두 지원하는 단일 세션 기반 MVP를 구현한다.
- 입력 방식(텍스트/음성)이 달라도 동일한 브리프 게이트, 오케스트레이션 상태 전이, 출력 계약을 보장한다.
- 브리프를 채운 뒤 리서치(시장/경쟁/채널)를 반영해 전략/소재를 생성한다.
- 오케스트레이터 중심 분업 개발(팀 병렬 작업)이 가능하도록 API/스키마/문서/테스트 기준을 먼저 고정한다.
- 커밋 단위를 작게 유지해 통합 리스크를 줄이고, 각 단계마다 재현 가능한 검증 명령으로 완료를 판정한다.
- 구현 순서는 문서 -> 데이터 계약 -> 백엔드 -> 프론트 -> 품질 안정화로 고정한다.
- 최종 산출물은 초기 아이디어 기획서가 아니라 실행형 런칭 패키지(시장 스냅샷 + 전략 + 소재 + KPI 액션)로 고정한다.

## 0-1. MVP 완료 정의 (필수)
- 텍스트만 사용한 대화로 `CHAT_COLLECTING -> DONE` 완주 가능
- 음성만 사용한 대화로 `CHAT_COLLECTING -> DONE` 완주 가능
- 텍스트+음성 혼합 대화로 `CHAT_COLLECTING -> DONE` 완주 가능
- 위 3가지 모두에서 동일한 `RUN_RESEARCH -> GEN_STRATEGY -> GEN_CREATIVES` 결과 계약을 만족

## 0-2. MVP 산출물 정의
- `brief_summary`: 제품/타겟/채널/목표 슬롯 요약
- `research_snapshot`: 시장 시그널/경쟁사/채널 관찰/근거
- `strategy_plan`: 포지셔닝 옵션/주간 실행 체크리스트
- `creative_assets`: 카피/포스터/영상 프롬프트
- `voice_assets`: 보이스 스크립트/타이밍/자막/TTS 설정
- `kpi_next_actions`: KPI와 다음 대화 입력 가이드

## 1. 작업 규칙
- 브랜치: `chat-voice-mvp`
- 커밋 컨벤션: `type(scope): 내용`
- 한 커밋 권장 범위: 파일 3~8개, 변경 300줄 내외
- 각 단계 종료 시 동작 확인 후 다음 단계로 이동
- API/DB 변경 시 문서(`docs/api.md`, `docs/db_schema.md`) 동시 업데이트
- 검증 항목은 반드시 `실행 명령 + 기대 결과`로 기록

## 1-1. 공통 검증 명령 템플릿
- 백엔드 의존성/임포트 확인:
  - `cd backend && uv sync && uv run python -c "from app.main import app; print(app.title)"`
- 백엔드 테스트(도입 후):
  - `cd backend && uv run pytest -q`
- 프론트 빌드 확인:
  - `cd frontend && npm run build`
- 프론트 테스트(도입 후):
  - `cd frontend && npm run test -- --run`

## 1-2. 문서/스킬 참조 맵
- 제품 범위/성공 기준
  - `PRD.md`
  - `docs/mvp.md`
  - `docs/voice_chat_mvp_spec.md`
  - `docs/business_model.md`
  - `docs/expansion.md`
- 팀 협업 규칙
  - `team.md`
  - `docs/codex_workflow.md`
- API/데이터 계약
  - `docs/api.md`
  - `docs/db_schema.md`
  - `docs/orchestrator_design.md`
  - `docs/prompt_contracts.md`
  - `docs/voice_agent.md`
  - `docs/test_runbook.md`
- OpenAI 기능/미디어
  - `docs/openai_stack.md`
  - `docs/sora_video_optimization.md`
- 환경/운영
  - `docs/uv_setup.md`
  - `backend/README.md`
  - `frontend/README.md`
- 스킬 참조
  - `skills/launch-studio-mvp/SKILL.md`
  - `docs/skills_guide.md`
- 단계 중 생성 예정 문서
  - `docs/release_notes_mvp.md` (R-02에서 생성)

## 2. 단계별 커밋 플랜

## Phase A. 준비/환경 고정 (문서 + uv)
- 필수 참조: `docs/uv_setup.md`, `backend/README.md`, `docs/README.md`, `team.md`, `skills/launch-studio-mvp/SKILL.md`

### A-01
- 커밋: `chore(backend): uv 프로젝트 설정 파일 추가`
- 목표: `pyproject.toml` 기반 의존성 관리 시작
- 변경 파일
  - `backend/pyproject.toml` (신규)
- 검증
  - 명령: `cd backend && uv sync && uv run python -c "import fastapi,pydantic; print('ok')"`
  - 기대 결과: `ok` 출력

### A-02
- 커밋: `chore(backend): uv lock 파일 생성`
- 목표: 팀원 환경 재현성 확보
- 변경 파일
  - `backend/uv.lock` (신규)
- 검증
  - 명령: `cd backend && uv sync --frozen`
  - 기대 결과: lock 기준으로 설치 완료

### A-03
- 커밋: `docs: uv 기반 개발 명령 문서 정합화`
- 목표: 실행 명령 단일화
- 변경 파일
  - `docs/uv_setup.md`
  - `backend/README.md`
- 검증
  - 명령: `cd backend && uv run python -c "from app.main import app; print(app.title)"`
  - 기대 결과: 앱 타이틀 문자열 출력

### A-04
- 커밋: `docs: prompt 계약서와 테스트 런북 추가`
- 목표: 구현 전 입출력 계약 고정
- 변경 파일
  - `docs/prompt_contracts.md` (신규)
  - `docs/test_runbook.md` (신규)
  - `docs/README.md`
- 검증
  - 명령: `rg -n "Planner|Research|Strategy|Creative|Voice" docs/prompt_contracts.md docs/test_runbook.md`
  - 기대 결과: 5개 에이전트 키워드 모두 검색됨

## Phase B. DB와 저장소 계층
- 필수 참조: `docs/db_schema.md`, `docs/api.md`, `docs/orchestrator_design.md`, `team.md`

### B-01
- 커밋: `feat(db): 채팅 세션 테이블 스키마 추가`
- 목표: 대화 세션 상태 영속화
- 변경 파일
  - `backend/app/repositories/sqlite_history.py`
  - `docs/db_schema.md`
- 검증
  - 명령: `cd backend && uv run python -c "import sqlite3; c=sqlite3.connect('launch_studio.db'); print(any(r[0]=='chat_sessions' for r in c.execute(\"select name from sqlite_master where type='table'\")))"`
  - 기대 결과: `True`

### B-02
- 커밋: `feat(db): chat_messages 테이블 추가`
- 목표: 턴별 대화 내역 저장
- 변경 파일
  - `backend/app/repositories/sqlite_history.py`
  - `docs/db_schema.md`
- 검증
  - 명령: `cd backend && uv run python -c "import sqlite3; c=sqlite3.connect('launch_studio.db'); print(any(r[0]=='chat_messages' for r in c.execute(\"select name from sqlite_master where type='table'\")))"`
  - 기대 결과: `True`

### B-03
- 커밋: `feat(db): brief_slots 테이블 추가`
- 목표: 슬롯 상태/완성도 저장
- 변경 파일
  - `backend/app/repositories/sqlite_history.py`
  - `docs/db_schema.md`
- 검증
  - 명령: `cd backend && uv run python -c "import sqlite3; c=sqlite3.connect('launch_studio.db'); print(any(r[0]=='brief_slots' for r in c.execute(\"select name from sqlite_master where type='table'\")))"`
  - 기대 결과: `True`

### B-04
- 커밋: `feat(db): run_outputs/media_assets 테이블 추가`
- 목표: 전략/크리에이티브/보이스 및 미디어 메타 저장
- 변경 파일
  - `backend/app/repositories/sqlite_history.py`
  - `docs/db_schema.md`
- 검증
  - 명령: `cd backend && uv run python -c "import sqlite3; c=sqlite3.connect('launch_studio.db'); tables={r[0] for r in c.execute(\"select name from sqlite_master where type='table'\")}; print('run_outputs' in tables and 'media_assets' in tables)"`
  - 기대 결과: `True`

### B-05
- 커밋: `refactor(repository): session/message/slot 저장소 클래스 분리`
- 목표: 책임 분리로 유지보수성 강화
- 변경 파일
  - `backend/app/repositories/session_repository.py` (신규)
  - `backend/app/repositories/chat_message_repository.py` (신규)
  - `backend/app/repositories/brief_slot_repository.py` (신규)
  - `backend/app/repositories/run_output_repository.py` (신규)
  - `backend/app/repositories/media_asset_repository.py` (신규)
  - `backend/app/repositories/__init__.py`
- 검증
  - 명령: `cd backend && uv run python -c "from app.repositories import SQLiteHistoryRepository; print('ok')"`
  - 기대 결과: `ok` 출력 + 기존 `/api/launch/history` 정상 응답

### B-06
- 커밋: `test(repository): sqlite 저장소 단위 테스트 추가`
- 목표: CRUD 회귀 방지
- 변경 파일
  - `backend/tests/test_repositories.py` (신규)
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_repositories.py`
  - 기대 결과: 실패 없이 통과

## Phase C. 텍스트 대화형 오케스트레이션
- 필수 참조: `docs/api.md`, `docs/orchestrator_design.md`, `docs/mvp.md`, `docs/voice_chat_mvp_spec.md`, `team.md`

### C-01
- 커밋: `feat(schema): chat session/slot 응답 스키마 추가`
- 목표: API 계약 타입 고정
- 변경 파일
  - `backend/app/schemas/launch_package.py`
  - `backend/app/schemas/__init__.py`
- 검증
  - 명령: `cd backend && uv run python -c "from app.schemas import LaunchRunRequest; print('ok')"`
  - 기대 결과: `ok` 출력

### C-02
- 커밋: `feat(api): POST /api/chat/session 추가`
- 목표: 대화 세션 시작 API 제공
- 변경 파일
  - `backend/app/routers/chat.py` (신규)
  - `backend/app/routers/__init__.py`
  - `backend/app/main.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); r=c.post('/api/chat/session', json={'locale':'ko-KR','mode':'standard'}); print(r.status_code)"`
  - 기대 결과: `200`

### C-03
- 커밋: `feat(api): GET /api/chat/session/{id} 추가`
- 목표: 현재 슬롯/상태 조회
- 변경 파일
  - `backend/app/routers/chat.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run python -c "from fastapi.testclient import TestClient; from app.main import app; c=TestClient(app); sid=c.post('/api/chat/session', json={'locale':'ko-KR','mode':'standard'}).json()['session_id']; r=c.get(f'/api/chat/session/{sid}'); print(r.status_code)"`
  - 기대 결과: `200`

### C-04
- 커밋: `feat(planner): 슬롯 추출 로직과 confidence 계산 추가`
- 목표: 대화 입력에서 슬롯 자동 채우기
- 변경 파일
  - `backend/app/agents/planner_agent.py`
  - `backend/app/services/slot_parser.py` (신규)
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_planner_slot_parser.py`
  - 기대 결과: 핵심 슬롯 추출 테스트 통과

### C-05
- 커밋: `feat(gate): 브리프 게이트 판정 서비스 구현`
- 목표: 필수 슬롯 충족 전 전략 생성 차단
- 변경 파일
  - `backend/app/services/gate_service.py` (신규)
  - `backend/app/agents/orchestrator.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_gate_service.py`
  - 기대 결과: 미충족/충족 케이스 모두 통과

### C-06
- 커밋: `feat(api): message stream SSE 엔드포인트 골격 추가`
- 목표: 단계별 스트리밍 UX 기반
- 변경 파일
  - `backend/app/routers/chat.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_chat_stream.py`
  - 기대 결과: `stage.changed`, `planner.delta` 이벤트 검증 통과

### C-07
- 커밋: `feat(orchestrator): CHAT_COLLECTING -> BRIEF_READY -> RUN_RESEARCH 전이 구현`
- 목표: 상태 머신 1차 완성 + 리서치 단계 진입
- 변경 파일
  - `backend/app/agents/orchestrator.py`
  - `docs/orchestrator_design.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_orchestrator_state.py`
  - 기대 결과: 슬롯 충족 시 `BRIEF_READY` 후 `RUN_RESEARCH` 전이 확인

### C-08
- 커밋: `test(api): chat session/message 통합 테스트 추가`
- 목표: API 회귀 방지
- 변경 파일
  - `backend/tests/test_chat_api.py` (신규)
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_chat_api.py`
  - 기대 결과: 세션 생성/메시지/게이트 판정 테스트 통과

## Phase D. 음성 턴 (채팅 병행)
- 필수 참조: `docs/voice_chat_mvp_spec.md`, `docs/voice_agent.md`, `docs/api.md`, `docs/openai_stack.md`, `team.md`

### D-01
- 커밋: `feat(api): POST /api/chat/session/{id}/voice-turn 추가`
- 목표: 음성 업로드 턴 처리
- 변경 파일
  - `backend/app/routers/voice.py` (신규)
  - `backend/app/main.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_api.py -k voice_turn`
  - 기대 결과: 음성 업로드 요청 처리 테스트 통과

### D-02
- 커밋: `feat(voice): STT 서비스 래퍼 구현`
- 목표: 음성 -> 텍스트 변환
- 변경 파일
  - `backend/app/services/voice_service.py` (신규)
  - `backend/app/core/config.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_service.py -k stt`
  - 기대 결과: 음성 입력에서 transcript 반환 확인

### D-03
- 커밋: `feat(voice): voice-turn에 슬롯 업데이트 연결`
- 목표: STT 결과를 플래너/게이트로 연결
- 변경 파일
  - `backend/app/routers/voice.py`
  - `backend/app/agents/planner_agent.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_slot_update.py`
  - 기대 결과: 음성 1턴 후 슬롯 업데이트 확인

### D-04
- 커밋: `feat(api): POST /api/chat/session/{id}/assistant-voice 추가`
- 목표: 다음 질문을 TTS로 제공
- 변경 파일
  - `backend/app/routers/voice.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_api.py -k assistant_voice`
  - 기대 결과: 질문 텍스트로 오디오 URL 반환 확인

### D-05
- 커밋: `feat(voice-agent): 질문 톤/속도 프리셋 추가`
- 목표: 탐색형 질문 톤 고정
- 변경 파일
  - `backend/app/agents/voice_agent.py` (신규)
  - `docs/voice_agent.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_agent.py -k preset`
  - 기대 결과: 톤 프리셋별 출력 차이 검증 통과

### D-06
- 커밋: `feat(orchestrator): voice 관련 이벤트 추가`
- 목표: 음성 입력 관련 이벤트가 공통 스트림 타입(`voice.delta`, `slot.updated`)으로 송출되도록 정합화
- 변경 파일
  - `backend/app/agents/orchestrator.py`
  - `docs/orchestrator_design.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_chat_stream.py -k voice`
  - 기대 결과: voice 이벤트 순서 검증 통과

### D-07
- 커밋: `test(voice): STT 실패 시 텍스트 폴백 테스트`
- 목표: 음성 실패 복구 보장
- 변경 파일
  - `backend/tests/test_voice_fallback.py` (신규)
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_voice_fallback.py`
  - 기대 결과: 강제 실패 시 텍스트 폴백 경로 통과

## Phase E. 리서치/전략/크리에이티브/보이스 패키지
- 필수 참조: `docs/prompt_contracts.md`, `docs/voice_agent.md`, `docs/orchestrator_design.md`, `docs/api.md`, `team.md`, `docs/openai_stack.md`

### E-01
- 커밋: `feat(schema): research 출력 스키마 고정`
- 목표: 시장/경쟁/채널/근거 구조화
- 변경 파일
  - `backend/app/schemas/launch_package.py`
  - `docs/prompt_contracts.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_output_schemas.py -k research`
  - 기대 결과: research 스키마 검증 통과

### E-02
- 커밋: `feat(schema): strategy 출력 스키마 고정`
- 목표: 시장평가/포지셔닝/주간 운영 플랜 타입 안정화
- 변경 파일
  - `backend/app/schemas/launch_package.py`
  - `docs/prompt_contracts.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_output_schemas.py -k strategy`
  - 기대 결과: strategy 스키마 검증 통과

### E-03
- 커밋: `feat(schema): creative 출력 스키마 고정`
- 목표: 카피/포스터/영상 프롬프트 계약 확정
- 변경 파일
  - `backend/app/schemas/launch_package.py`
  - `docs/prompt_contracts.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_output_schemas.py -k creative`
  - 기대 결과: creative 스키마 검증 통과

### E-04
- 커밋: `feat(schema): voice 출력 스키마 고정`
- 목표: 내레이션/타이밍/자막 계약 확정
- 변경 파일
  - `backend/app/schemas/launch_package.py`
  - `docs/voice_agent.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_output_schemas.py -k voice`
  - 기대 결과: `timing_map`, `subtitle_lines` 필수 필드 검증 통과

### E-05
- 커밋: `feat(api): POST /api/runs/{id}/generate 추가`
- 목표: 게이트 이후 생성 트리거 분리
- 변경 파일
  - `backend/app/routers/runs.py` (신규)
  - `backend/app/main.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_runs_api.py -k generate`
  - 기대 결과: 생성 요청 시 `run_id` 반환

### E-06
- 커밋: `feat(orchestrator): research -> strategy -> creative -> voice 순차 실행`
- 목표: 생성 파이프라인 일관화
- 변경 파일
  - `backend/app/agents/orchestrator.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_orchestrator_e2e.py -k sequential`
  - 기대 결과: research/strategy/creative/voice 순서 실행 검증 통과

### E-07
- 커밋: `feat(persistence): run_outputs/media_assets 저장 연결`
- 목표: 리서치 포함 결과 재조회 가능
- 변경 파일
  - `backend/app/repositories/run_output_repository.py`
  - `backend/app/repositories/media_asset_repository.py`
  - `backend/app/routers/runs.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_runs_api.py -k persistence`
  - 기대 결과: run 결과 조회 API 검증 통과

### E-08
- 커밋: `test(orchestrator): end-to-end 시나리오 테스트 추가`
- 목표: 전체 흐름 회귀 방지
- 변경 파일
  - `backend/tests/test_orchestrator_e2e.py` (신규)
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_orchestrator_e2e.py`
  - 기대 결과: 텍스트/음성 E2E 시나리오 통과

## Phase F. 프론트엔드 대화 UX
- 필수 참조: `docs/frontend_architecture.md`, `docs/api.md`, `docs/mvp.md`, `docs/voice_chat_mvp_spec.md`, `team.md`

### F-01
- 커밋: `feat(frontend-api): chat/voice API client 추가`
- 목표: 신규 백엔드 계약 소비
- 변경 파일
  - `frontend/src/api/client.ts`
  - `frontend/src/types.ts`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 타입 에러 없이 빌드 성공

### F-02
- 커밋: `feat(frontend): ChatWorkspace 페이지 추가`
- 목표: 대화 중심 화면 도입
- 변경 파일
  - `frontend/src/pages/ChatWorkspace.tsx` (신규)
  - `frontend/src/App.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 라우팅/컴포넌트 빌드 성공

### F-03
- 커밋: `feat(frontend): SSE 메시지 스트림 렌더링`
- 목표: 실시간 응답 표시
- 변경 파일
  - `frontend/src/components/MessageStream.tsx` (신규)
  - `frontend/src/pages/ChatWorkspace.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 스트림 렌더링 코드 포함 상태에서 빌드 성공

### F-04
- 커밋: `feat(frontend): 슬롯 카드 및 게이트 진행률 UI 추가`
- 목표: 사용자에게 준비 상태 명확히 제공
- 변경 파일
  - `frontend/src/components/BriefSlotCard.tsx` (신규)
  - `frontend/src/pages/ChatWorkspace.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 슬롯 카드 UI 포함 빌드 성공

### F-05
- 커밋: `feat(frontend): 음성 녹음 업로드 버튼 추가`
- 목표: voice-turn 입력 UX 지원
- 변경 파일
  - `frontend/src/components/VoiceInputButton.tsx` (신규)
  - `frontend/src/pages/ChatWorkspace.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 녹음/업로드 UI 포함 빌드 성공

### F-06
- 커밋: `feat(frontend): 어시스턴트 음성 재생 컴포넌트 추가`
- 목표: 질문 TTS 재생
- 변경 파일
  - `frontend/src/components/VoicePlaybackToggle.tsx` (신규)
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: TTS 재생 컴포넌트 포함 빌드 성공

### F-07
- 커밋: `refactor(frontend): 기존 Dashboard와 대화 플로우 통합`
- 목표: 진입 동선 단순화
- 변경 파일
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/pages/Home.tsx`
  - `frontend/src/components/Navbar.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 홈 -> 대화 플로우 코드 통합 후 빌드 성공

### F-08
- 커밋: `test(frontend): 대화/음성 주요 상호작용 테스트`
- 목표: 핵심 UX 회귀 방지
- 변경 파일
  - `frontend/package.json`
  - `frontend/vitest.config.ts` (신규)
  - `frontend/src/__tests__/chat_workspace.test.tsx` (신규)
  - `frontend/src/__tests__/voice_flow.test.tsx` (신규)
- 검증
  - 명령: `cd frontend && npm run test -- --run`
  - 기대 결과: 핵심 시나리오 테스트 통과

## Phase G. 미디어 품질/운영 안정화
- 필수 참조: `docs/openai_stack.md`, `docs/sora_video_optimization.md`, `docs/api.md`, `docs/test_runbook.md`, `team.md`

### G-01
- 커밋: `fix(media): 영상 길이 파라미터를 5/10/15/20으로 정합화`
- 목표: Videos API 지원값 일치
- 변경 파일
  - `backend/app/services/media_service.py`
  - `docs/sora_video_optimization.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_media_duration.py`
  - 기대 결과: `5/10/15/20` 외 duration 값 거부/정규화 테스트 통과

### G-02
- 커밋: `feat(media): ffmpeg ducking 및 자막 합성 추가`
- 목표: 영상 체감 품질 향상
- 변경 파일
  - `backend/app/services/media_pipeline.py` (신규)
  - `backend/app/routers/runs.py`
  - `backend/app/agents/orchestrator.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_media_pipeline.py -k ducking`
  - 기대 결과: 보이스 구간 배경음 감소 검증 통과

### G-03
- 커밋: `feat(media): 비동기 생성 상태조회 추가`
- 목표: 긴 작업 중 UX 안정화
- 변경 파일
  - `backend/app/services/media_jobs.py` (신규)
  - `backend/app/routers/jobs.py` (신규)
  - `backend/app/main.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_jobs_api.py`
  - 기대 결과: 생성 상태 폴링 API 테스트 통과

### G-04
- 커밋: `feat(safety): 광고 카피 금지표현 필터 추가`
- 목표: 정책/신뢰 리스크 감소
- 변경 파일
  - `backend/app/services/copy_safety.py` (신규)
  - `backend/app/agents/marketer_agent.py`
  - `backend/app/agents/product_copy_agent.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_copy_safety.py`
  - 기대 결과: 금지표현 탐지/완화 치환 테스트 통과

### G-05
- 커밋: `feat(ux): 카피 톤 재생성 옵션 추가`
- 목표: 실사용 편의 향상
- 변경 파일
  - `frontend/src/components/ToneRegenerateButtons.tsx` (신규)
  - `frontend/src/pages/ChatWorkspace.tsx`
  - `backend/app/routers/runs.py`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 톤 재생성 UI 포함 빌드 성공

### G-06
- 커밋: `chore(observability): session/request 단위 구조화 로깅`
- 목표: 디버깅/운영 추적성 강화
- 변경 파일
  - `backend/app/services/logging_service.py` (신규)
  - `backend/app/main.py`
  - `backend/app/routers/chat.py`
  - `backend/app/routers/voice.py`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_logging_context.py`
  - 기대 결과: 로그 컨텍스트에 session_id/request_id 포함 검증 통과

### G-07
- 커밋: `docs: 운영 런북 및 데모 체크리스트 최종화`
- 목표: 발표/인수인계 준비
- 변경 파일
  - `docs/test_runbook.md`
  - `docs/codex_workflow.md`
- 검증
  - 명령: `rg -n "데모|복구|fallback|체크리스트" docs/test_runbook.md docs/codex_workflow.md`
  - 기대 결과: 운영/복구/체크리스트 키워드 포함 확인

## 3. 릴리즈 직전 정리 커밋
- 필수 참조: `README.md`, `docs/release_notes_mvp.md`, `docs/codex_workflow.md`, `team.md`

### R-01
- 커밋: `chore: .env.example 및 실행 스크립트 정리`
- 목표: 실행 진입 장벽 최소화
- 변경 파일
  - `backend/.env.example`
  - `run_studio.ps1`
- 검증
  - 명령: `cd backend && cat .env.example`
  - 기대 결과: 필수 환경변수 키(`OPENAI_API_KEY`, `OPENAI_MODEL`, `DB_PATH`) 포함

### R-02
- 커밋: `docs: 최종 릴리즈 노트 및 변경 요약`
- 목표: 머지/배포 전 의사소통 완료
- 변경 파일
  - `README.md`
  - `docs/release_notes_mvp.md` (신규)
- 검증
  - 명령: `rg -n "변경 요약|Breaking|마이그레이션|검증 결과" README.md docs/release_notes_mvp.md`
  - 기대 결과: 릴리즈 핵심 항목 포함 확인

## 4. 권장 진행 순서 요약
1. A (환경/문서)
2. B (DB)
3. C (텍스트 대화)
4. D (음성 턴)
5. E (생성 파이프라인)
6. F (프론트 UX)
7. G (품질/운영)
8. R (릴리즈)

## 5. 즉시 시작용 커밋 3개
1. `chore(backend): uv 프로젝트 설정 파일 추가`
2. `chore(backend): uv lock 파일 생성`
3. `docs: prompt 계약서와 테스트 런북 추가`

## 6. 후순위 백로그 (회원가입 없는 히스토리 분리)
- 우선순위: 낮음 (MVP 핵심 플로우 구현 후 진행)
- 목적: 회원가입 없이도 사용자별 히스토리를 분리해 노출 사고를 방지한다.
- 접근: `anon_id`(httpOnly 쿠키) 기반 owner 분리
- 필수 참조: `docs/api.md`, `docs/db_schema.md`, `team.md`

### P-01
- 커밋: `feat(security): 익명 사용자 식별 쿠키 발급 미들웨어 추가`
- 목표: 최초 요청 시 `anon_id`를 발급하고 재방문 시 재사용
- 변경 파일
  - `backend/app/main.py`
  - `backend/app/services/identity_service.py` (신규)
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_identity_cookie.py`
  - 기대 결과: 쿠키 발급/재사용 테스트 통과

### P-02
- 커밋: `feat(db): launch_runs에 owner_anon_id 컬럼 추가`
- 목표: 이력 레코드에 소유자 식별자 저장
- 변경 파일
  - `backend/app/repositories/sqlite_history.py`
  - `docs/db_schema.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_history_owner_column.py`
  - 기대 결과: owner 컬럼 존재 및 저장 테스트 통과

### P-03
- 커밋: `feat(api): history 조회/상세/삭제 owner 필터 적용`
- 목표: 자신의 이력만 조회/삭제 가능하도록 제한
- 변경 파일
  - `backend/app/routers/launch.py`
  - `backend/app/repositories/sqlite_history.py`
  - `docs/api.md`
- 검증
  - 명령: `cd backend && uv run pytest -q backend/tests/test_history_owner_scope.py`
  - 기대 결과: 타 사용자 이력 접근 차단 테스트 통과

### P-04 (선택)
- 커밋: `feat(frontend): 익명 세션 만료 시 히스토리 재동기화 처리`
- 목표: 쿠키 만료/재발급 상황에서 UX 혼란 최소화
- 변경 파일
  - `frontend/src/api/client.ts`
  - `frontend/src/pages/Dashboard.tsx`
- 검증
  - 명령: `cd frontend && npm run build`
  - 기대 결과: 만료 처리 로직 포함 빌드 성공
