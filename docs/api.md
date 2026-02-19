# API 명세

## 1. 현재 API (구현됨)
기본 prefix: `/api`

### 1.1 런치 패키지 실행
- `POST /api/launch/run`

요청 예시:
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

응답 예시:
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
    "marketing_assets": {
      "video_script": "...",
      "poster_brief": "...",
      "product_copy": "...",
      "video_url": "/static/assets/video_xxx.mp4",
      "poster_image_url": "/static/assets/poster_xxx.png"
    },
    "risks_and_mitigations": [],
    "timeline": []
  }
}
```

### 1.2 이력 API
- `GET /api/launch/history?limit=20&offset=0&q=`
- `GET /api/launch/history/{request_id}`
- `DELETE /api/launch/history/{request_id}`

### 1.3 헬스체크
- `GET /health`

## 2. 목표 API (대화형/음성형 MVP)

### 2.1 세션 시작
- `POST /api/chat/session`

요청:
```json
{
  "locale": "ko-KR",
  "mode": "standard"
}
```

응답:
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

### 2.2 텍스트 턴 스트리밍
- `POST /api/chat/session/{session_id}/message/stream`
- content type: `text/event-stream`

### 2.3 음성 턴
- `POST /api/chat/session/{session_id}/voice-turn`
- multipart/form-data (`audio` 파일 업로드)
- STT -> 슬롯 업데이트 -> 다음 질문 반환

응답 예시:
```json
{
  "transcript": "우리 제품은 비건 스킨케어예요",
  "slot_updates": [{"path": "product.category", "value": "비건 스킨케어"}],
  "next_question": "주요 타겟 고객은 누구인가요?",
  "state": "CHAT_COLLECTING"
}
```

### 2.4 어시스턴트 음성 생성
- `POST /api/chat/session/{session_id}/assistant-voice`
- 입력 텍스트를 TTS로 변환해 재생 URL 반환

### 2.5 실행 결과 조회/내보내기
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/export`

## 3. 스트리밍 이벤트
```text
event: planner.delta
data: {"text":"좋아요. 타겟을 조금 더 좁혀볼게요."}

event: slot.updated
data: {"path":"target.who","value":"25-34 직장인 여성"}

event: stage.changed
data: {"state":"GEN_STRATEGY"}

event: strategy.delta
data: {"text":"시장평가 요약..."}

event: creative.delta
data: {"text":"카피 초안..."}

event: voice.delta
data: {"text":"나레이션 초안..."}

event: run.completed
data: {"run_id":"run_xxx"}
```

## 4. 오류 포맷
```json
{
  "error": {
    "code": "TIMEOUT",
    "message": "에이전트 실행 시간이 초과되었습니다.",
    "retryable": true
  }
}
```

## 5. 버전 전략
- 현재 `/api/launch/*`는 호환성 유지
- 대화/음성/스트리밍 API는 신규 버전으로 점진 도입
