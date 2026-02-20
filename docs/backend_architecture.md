# 백엔드 아키텍처

## 1. 문서 목적
- 채팅+음성 세션 기반 MVP에서 백엔드의 모듈 경계, 스트림 처리 구조, 상태 전이 책임을 정의한다.
- API 레이어와 오케스트레이터를 분리해 팀 병렬 개발 시 충돌을 줄인다.
- 리서치 결과를 전략/소재 생성에 반영하는 데이터 경로를 명확히 한다.

## 2. 현재 구조 (As-Is)
- FastAPI 엔트리: `backend/app/main.py`
- 런치 라우터: `backend/app/routers/launch.py`
- 채팅 라우터(세션/조회/비스트림 턴): `backend/app/routers/chat.py`
- 오케스트레이터: `backend/app/agents/orchestrator.py`
- 채팅 오케스트레이터(슬롯 수집/게이트): `backend/app/agents/chat_orchestrator.py`
- 저장소: `backend/app/repositories/sqlite_history.py`
- 미디어 생성: `backend/app/services/media_service.py`
- 현재는 `/api/launch/*` 단건 실행 + `/api/chat/session*` 세션 API와 텍스트 스트림 API가 구현되어 있다.
- 기본 음성 API(`voice-turn`, `assistant-voice`, `voice-turn/stream`)가 구현되어 있다.
- 기본 runs API(`POST /api/runs/{session_id}/generate`, `GET /api/runs/{run_id}`)가 구현되어 있다.
- jobs API(`GET /api/jobs/{job_id}`, `GET /api/jobs`)와 비동기 생성 트리거(`POST /api/runs/{session_id}/generate/async`)가 구현되어 있다.

## 3. 목표 구조 (To-Be)
- `launch` API는 하위 호환으로 유지한다.
- 신규 `chat/voice/runs/jobs` API로 세션 기반 실행을 제공한다.
- 오케스트레이터는 내부 엔진 역할만 수행하고, 라우터는 프로토콜 변환에 집중한다.
- 생성 파이프라인은 `planner -> research -> strategy -> creative -> voice` 순으로 정렬한다.

## 4. 권장 모듈 구조
- 라우터
  - `routers/launch.py` (기존)
  - `routers/chat.py` (세션/텍스트 턴/스트림)
  - `routers/voice.py` (음성 턴/STT/TTS)
  - `routers/runs.py` (생성/결과/내보내기)
  - `routers/jobs.py` (비동기 상태 조회)
- 에이전트
  - `agents/orchestrator.py`
  - `agents/planner_agent.py`
  - `agents/research_agent.py`
  - `agents/strategy_agent.py`
  - `agents/creative_agent.py`
  - `agents/voice_agent.py`
- 서비스
  - `services/session_service.py`
  - `services/gate_service.py`
  - `services/stream_service.py`
  - `services/research_service.py`
  - `services/voice_service.py`
  - `services/media_pipeline.py`
  - `services/copy_safety.py`
- 저장소
  - `repositories/session_repository.py`
  - `repositories/chat_message_repository.py`
  - `repositories/brief_slot_repository.py`
  - `repositories/run_output_repository.py`
  - `repositories/media_asset_repository.py`

## 5. 요청 처리 플로우
### 5.1 텍스트 턴
1. `chat` 라우터가 입력 검증
2. 세션/메시지 저장
3. 오케스트레이터 호출
4. 오케스트레이터가 이벤트를 발행
5. 라우터가 스트림으로 전달

### 5.2 음성 턴
1. `voice` 라우터가 파일 검증
2. `voice_service`에서 STT 수행
3. 플래너 슬롯 업데이트
4. 다음 질문 생성
5. 필요 시 TTS URL 발급

### 5.3 생성 실행
1. 게이트 충족 확인
2. `research -> strategy -> creative -> voice` 순서 실행
3. 결과 저장(`run_outputs`, `media_assets`)
4. `run.completed` 이벤트 송출

## 6. 스트림 처리 설계
### 6.1 이벤트 발행 원칙
- 이벤트 타입: `planner.delta`, `slot.updated`, `gate.ready`, `stage.changed`, `research.delta`, `strategy.delta`, `creative.delta`, `voice.delta`, `asset.ready`, `run.completed`, `error`
- 이벤트는 `seq` 증가 순으로 발행한다.
- 라우터는 오케스트레이터 이벤트를 그대로 전달하고, 비즈니스 로직을 추가하지 않는다.

### 6.2 이벤트 엔벨로프
```json
{
  "event_id": "evt_00124",
  "seq": 124,
  "session_id": "sess_xxx",
  "type": "stage.changed",
  "created_at": "2026-02-19T15:00:00Z",
  "data": {"state": "RUN_RESEARCH"}
}
```

### 6.3 스트림 실패 대응
- 연결 종료 시 마지막 이벤트 ID를 기준으로 재요청 가능해야 한다.
- 오케스트레이터 오류는 `error` 이벤트로 송출하고 세션 상태를 `FAILED`로 기록한다.
- 타임아웃 시 partial 결과를 저장하고 재실행 포인트를 남긴다.

## 7. 상태 관리
- 오케스트레이터 상태: `CHAT_COLLECTING -> BRIEF_READY -> RUN_RESEARCH -> GEN_STRATEGY -> GEN_CREATIVES -> DONE/FAILED`
- 브리프 게이트는 독립 서비스(`gate_service`)에서 판단한다.
- 입력 경로(텍스트/음성)와 무관하게 동일 상태 머신을 사용한다.

## 8. 리서치 데이터 계약
리서치 결과는 최소 아래 필드를 갖는다.
- `market_signals`
- `competitor_notes`
- `channel_observations`
- `evidence` (source/title/url/observed_at/confidence)

전략 에이전트는 위 필드를 입력으로 받아 `positioning_options`, `weekly_plan`, `required_assets`를 만든다.

## 9. 신뢰성/성능
- 단계별 timeout budget 적용
- 에이전트별 재시도 제한(기본 1회)
- 리서치/전략/소재 생성 실패 시 `FAILED`로 종료(가짜 대체 데이터 금지)
- 고비용 미디어 작업은 비동기 잡으로 분리
- 비동기 잡 워커는 `threading + asyncio.run`을 사용하되, 워커마다 오케스트레이터/Async 클라이언트를 새로 생성해 루프 간 객체 재사용을 금지한다.
- run 단위 idempotency 키 고려

No-Fake 정책
- 런타임 mock/fake 응답 생성 금지
- 저장되는 본문/요약/전략/소재는 실제 AI 응답만 허용

## 10. 관측성
- 모든 로그에 `request_id`, `session_id`, `run_id` 포함
- 지표
  - 단계별 지연 시간
  - 리서치 성공률/타임아웃율
  - 에이전트 실패율
  - 스트림 중단율
  - 음성 턴 성공률

## 11. 보안/안전
- API 키는 환경변수만 사용
- 업로드 파일 크기/포맷 제한
- 광고 카피 안전 필터 적용
- 민감 정보 로그 마스킹

## 12. 구현 참고 문서
- `docs/api.md`
- `docs/db_schema.md`
- `docs/orchestrator_design.md`
- `docs/prompt_contracts.md`
- `docs/voice_agent.md`
- `docs/openai_stack.md`
- `docs/sora_video_optimization.md`
