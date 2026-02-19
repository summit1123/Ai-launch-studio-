# API 명세 (전체 카탈로그)

## 1. 문서 목적
- 이 문서는 이 프로젝트에서 필요한 API를 **현재 구현(v1)**과 **목표 확장(v2)**으로 분리해 정의한다.
- 팀 분업 시 API 누락/중복을 방지하기 위해 엔드포인트 카탈로그와 이벤트 계약을 함께 제공한다.
- v2의 핵심 산출물은 "초기 기획서"가 아니라 **리서치 기반 실행형 런칭 패키지**다.

## 2. 공통 규칙
- 기본 prefix: `/api`
- 인증: MVP에서는 미적용 (후순위로 `anon_id` 또는 로그인 기반 확장)
- 공통 오류 포맷
```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "사용자 메시지",
    "retryable": true
  }
}
```
- 시간 필드: ISO-8601 UTC 문자열

## 3. API 그룹과 상태
- `PLATFORM`: 헬스/문서/정적 에셋
- `LAUNCH_V1`: 현재 단건 실행 API
- `CHAT_V2`: 세션 기반 채팅 API
- `VOICE_V2`: 음성 턴/STT/TTS API
- `RUN_V2`: 리서치+전략+소재 생성/조회 API
- `JOB_V2`: 비동기 작업 상태 API

`상태` 표기:
- `구현됨`: 현재 코드에 존재
- `계획`: 문서 기준 목표 API

## 4. PLATFORM API
### 4.1 헬스체크
- 상태: 구현됨
- `GET /health`
- 응답
```json
{"status": "ok"}
```

### 4.2 OpenAPI 문서
- 상태: 구현됨 (FastAPI 기본)
- `GET /openapi.json`
- `GET /docs`

### 4.3 정적 에셋
- 상태: 구현됨
- `GET /static/{path}`
- 용도: 생성된 포스터/영상/오디오 파일 제공

## 5. LAUNCH_V1 API (현재 운영)
### 5.1 런치 실행
- 상태: 구현됨
- `POST /api/launch/run`
- 설명: 브리프 단건 입력 -> 기존 런치 패키지 생성

요청 본문
```json
{
  "brief": {
    "product_name": "Glow Serum X",
    "product_category": "Skincare",
    "target_audience": "20-34 뷰티 얼리어답터",
    "price_band": "mid-premium",
    "total_budget_krw": 120000000,
    "launch_date": "2026-04-01",
    "core_kpi": "4주 내 재구매율 25%",
    "region": "KR",
    "channel_focus": ["Instagram", "YouTube"],
    "video_seconds": 8
  },
  "mode": "standard"
}
```

응답 본문 (요약)
```json
{
  "package": {
    "request_id": "uuid",
    "created_at": "2026-02-19T00:00:00Z",
    "brief": {},
    "research_summary": {},
    "product_strategy": {},
    "technical_plan": {},
    "launch_plan": {},
    "campaign_strategy": {},
    "budget_and_kpi": {},
    "marketing_assets": {},
    "risks_and_mitigations": [],
    "timeline": []
  }
}
```

### 5.2 런치 이력 목록
- 상태: 구현됨
- `GET /api/launch/history?limit=20&offset=0&q=`

### 5.3 런치 이력 상세
- 상태: 구현됨
- `GET /api/launch/history/{request_id}`

### 5.4 런치 이력 삭제
- 상태: 구현됨
- `DELETE /api/launch/history/{request_id}`

## 6. CHAT_V2 API (목표)
### 6.1 세션 시작
- 상태: 구현됨
- `POST /api/chat/session`

요청
```json
{
  "locale": "ko-KR",
  "mode": "standard"
}
```

응답
```json
{
  "session_id": "sess_xxx",
  "state": "CHAT_COLLECTING",
  "brief_slots": {
    "product": {},
    "target": {},
    "channel": {},
    "goal": {}
  }
}
```

### 6.2 세션 조회
- 상태: 구현됨
- `GET /api/chat/session/{session_id}`
- 설명: 현재 상태/슬롯/진행률 조회

### 6.3 텍스트 턴 (비스트림)
- 상태: 구현됨
- `POST /api/chat/session/{session_id}/message`
- 설명: 단건 응답 필요 시 사용

### 6.4 텍스트 턴 (스트림)
- 상태: 구현됨
- `POST /api/chat/session/{session_id}/message/stream`
- Content-Type: `text/event-stream`
- 설명: 플래너/리서치/전략/크리에이티브/보이스 이벤트를 순차 전달

## 7. VOICE_V2 API (목표)
### 7.1 음성 턴
- 상태: 계획
- `POST /api/chat/session/{session_id}/voice-turn`
- Content-Type: `multipart/form-data`
- 필드: `audio`, `format`, `locale`(선택)

응답
```json
{
  "transcript": "우리 제품은 비건 스킨케어예요",
  "slot_updates": [
    {"path": "product.category", "value": "비건 스킨케어", "confidence": 0.91}
  ],
  "next_question": "주요 타겟 고객은 누구인가요?",
  "state": "CHAT_COLLECTING"
}
```

### 7.2 어시스턴트 음성 생성
- 상태: 계획
- `POST /api/chat/session/{session_id}/assistant-voice`
- 설명: 질문 텍스트를 TTS 오디오로 변환

요청
```json
{
  "text": "좋아요. 주요 타겟 고객은 누구인가요?",
  "voice_preset": "friendly_ko",
  "format": "mp3"
}
```

응답
```json
{
  "audio_url": "/static/assets/tts_xxx.mp3",
  "duration_ms": 1820
}
```

## 8. RUN_V2 API (목표)
### 8.1 생성 트리거
- 상태: 계획
- `POST /api/runs/{session_id}/generate`
- 설명: 게이트 충족 후 `research -> strategy -> creative -> voice` 실행

응답
```json
{
  "run_id": "run_xxx",
  "state": "RUN_RESEARCH"
}
```

### 8.2 실행 결과 조회
- 상태: 계획
- `GET /api/runs/{run_id}`

응답 (요약)
```json
{
  "run_id": "run_xxx",
  "session_id": "sess_xxx",
  "state": "DONE",
  "brief_summary": {},
  "research_snapshot": {
    "market_signals": [],
    "competitor_notes": [],
    "channel_observations": [],
    "evidence": []
  },
  "strategy_plan": {},
  "creative_assets": {},
  "voice_assets": {},
  "kpi_next_actions": {}
}
```

### 8.3 실행 결과 내보내기
- 상태: 계획
- `POST /api/runs/{run_id}/export`
- 설명: zip 또는 다중 파일 링크 반환

### 8.4 실행 결과 목록
- 상태: 계획
- `GET /api/runs?session_id={session_id}&limit=20&offset=0`

## 9. JOB_V2 API (목표)
### 9.1 작업 상태 조회
- 상태: 계획
- `GET /api/jobs/{job_id}`
- 설명: 영상/오디오 합성 등 비동기 작업 상태

응답
```json
{
  "job_id": "job_xxx",
  "type": "video_render",
  "status": "queued",
  "progress": 32,
  "run_id": "run_xxx"
}
```

### 9.2 작업 목록 조회
- 상태: 계획
- `GET /api/jobs?run_id={run_id}`

## 10. 스트리밍 이벤트 계약 (CHAT_V2)
### 10.1 이벤트 엔벨로프
```json
{
  "event_id": "evt_00124",
  "seq": 124,
  "session_id": "sess_xxx",
  "type": "planner.delta",
  "created_at": "2026-02-19T15:00:00Z",
  "data": {}
}
```

### 10.2 이벤트 타입
- `session.started`
- `planner.delta`
- `slot.updated`
- `gate.ready`
- `stage.changed`
- `research.delta`
- `strategy.delta`
- `creative.delta`
- `voice.delta`
- `asset.ready`
- `run.completed`
- `error`

### 10.3 이벤트 처리 규칙
- `seq`는 단조 증가
- 중복 `event_id`는 무시
- `run.completed` 또는 `error` 수신 시 스트림 종료 처리

## 11. 주요 오류 코드
- `INVALID_INPUT`: 요청 본문 검증 실패
- `SESSION_NOT_FOUND`: 없는 세션 ID
- `GATE_NOT_READY`: 게이트 미충족 상태에서 생성 요청
- `RESEARCH_TIMEOUT`: 리서치 단계 타임아웃
- `MEDIA_TIMEOUT`: 영상/오디오 작업 타임아웃
- `UPSTREAM_ERROR`: 모델/API 호출 실패
- `INTERNAL_ERROR`: 서버 내부 오류

## 12. 버전 전략
- `LAUNCH_V1`은 기존 데모 호환을 위해 유지
- 신규 기능은 `CHAT_V2/VOICE_V2/RUN_V2/JOB_V2` 그룹으로 확장
- 프론트는 기능 플래그로 v1/v2 전환 가능하도록 설계

## 13. 관련 문서
- `docs/backend_architecture.md`
- `docs/frontend_architecture.md`
- `docs/orchestrator_design.md`
- `docs/voice_chat_mvp_spec.md`
- `docs/prompt_contracts.md`
- `docs/db_schema.md`
