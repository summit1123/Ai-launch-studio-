# 프롬프트/출력 계약서 (Prompt Contracts)

## 1. 문서 목적
- 플래너/리서치/전략/크리에이티브/보이스 에이전트 간 입출력 포맷을 고정한다.
- 팀 분업 시 출력 포맷 충돌을 방지한다.
- 오케스트레이터가 안정적으로 상태 전이를 수행할 수 있게 한다.

## 2. 공통 규칙
- 모든 에이전트 출력은 JSON 객체로 반환한다.
- 필수 키 누락 시 실패로 간주하고 1회 재시도한다.
- 문자열 필드는 trim 후 저장한다.
- 배열 필드는 빈 배열 허용 여부를 스키마에 명시한다.
- 금지: 마크다운 코드블록, 임의 키 추가, 타입 변경

## 2-1. 응답 원칙 (No Fake Data)
- Mock/Fake/샘플 고정 문구를 런타임에서 생성하지 않는다.
- 모든 본문/요약/전략/소재 텍스트는 실제 AI 모델 응답으로만 채운다.
- 모델 호출 실패 시 "가짜 결과 대체"를 하지 않고 오류를 반환한다.
- 불확실한 항목은 `risks`에 명시하고, 확정 정보처럼 단정하지 않는다.

## 2-2. UX 순서와 프롬프트 책임
1. `CHAT_COLLECTING`
- 입력: 사용자 자유 대화(텍스트/음성 변환 텍스트)
- Planner 책임: 슬롯 업데이트 + 다음 질문 1개 + 누락 슬롯 반환

2. `BRIEF_READY`
- 입력: 필수 슬롯 충족 브리프
- Planner 책임: 생성 단계 시작 안내(중복 질문 금지)

3. `RUN_RESEARCH`
- 입력: 정규화 브리프
- Research 책임: 시장/경쟁/채널 근거 수집 및 요약

4. `GEN_STRATEGY`
- 입력: 브리프 + 리서치 결과
- Strategy 책임: 포지셔닝 옵션/실행 체크리스트/리스크 제시

5. `GEN_CREATIVES`
- 입력: 전략 산출물
- Creative/Voice 책임: 카피/포스터/영상 프롬프트/보이스 스크립트 생성

## 3. 공통 메타 필드
```json
{
  "schema_version": "v1",
  "agent": "planner|research|strategy|creative|voice",
  "trace_id": "trc_xxx",
  "created_at": "2026-02-19T00:00:00Z"
}
```

## 4. Planner Agent 계약

### 4.1 입력
```json
{
  "session_id": "sess_xxx",
  "stage": "CHAT_COLLECTING",
  "user_message": "우리 제품은...",
  "brief_slots": {
    "product": {"name": null, "category": null, "features": [], "price_band": null},
    "target": {"who": null, "why": null},
    "channel": {"channels": []},
    "goal": {"weekly_goal": null}
  }
}
```

### 4.2 출력
```json
{
  "schema_version": "v1",
  "agent": "planner",
  "response_text": "좋아요. 주요 타겟 고객을 더 구체화해볼게요.",
  "slot_updates": [
    {"path": "product.category", "value": "비건 스킨케어", "confidence": 0.91}
  ],
  "missing_slots": ["target.who", "target.why", "goal.weekly_goal"],
  "next_question": "주요 타겟 고객은 누구인가요?",
  "gate": {"ready": false, "missing_required": ["target.who", "target.why", "goal.weekly_goal"]}
}
```

### 4.3 검증 규칙
- `response_text`, `next_question`는 비어있지 않아야 한다.
- `slot_updates[].confidence`는 `0.0 ~ 1.0` 범위여야 한다.
- `gate.ready=true`이면 `missing_required`는 빈 배열이어야 한다.

## 5. Research Agent 계약

### 5.1 입력
```json
{
  "session_id": "sess_xxx",
  "brief_normalized": {
    "product": {"name": "Glow X", "category": "Skincare", "features": ["A", "B", "C"], "price_band": "mid"},
    "target": {"who": "25-34 직장인", "why": "피부결 개선"},
    "channel": {"channels": ["Instagram", "YouTube"]},
    "goal": {"weekly_goal": "inquiry"}
  },
  "locale": "ko-KR"
}
```

### 5.2 출력
```json
{
  "schema_version": "v1",
  "agent": "research",
  "market_signals": [
    {"signal": "민감성 스킨케어 검색량 증가", "impact": "high"}
  ],
  "competitor_notes": [
    {"brand": "BrandA", "positioning": "저자극 고보습", "price_band": "mid"}
  ],
  "channel_observations": [
    {"channel": "Instagram", "observation": "UGC 후기형 콘텐츠 반응 높음"}
  ],
  "evidence": [
    {
      "source": "web",
      "title": "예시 리포트",
      "url": "https://example.com/report",
      "observed_at": "2026-02-19",
      "confidence": 0.78
    }
  ],
  "risk_flags": ["데이터 표본 편향 가능성"]
}
```

### 5.3 검증 규칙
- `market_signals`, `competitor_notes`, `channel_observations`는 각각 최소 1개.
- `evidence[].url`은 `https://` 형식 권장.
- `evidence[].confidence`는 `0.0 ~ 1.0` 범위.
- `evidence`가 비어 있으면 `risk_flags`에 원인을 포함해야 한다.

## 6. Strategy Agent 계약

### 6.1 입력
```json
{
  "session_id": "sess_xxx",
  "brief_normalized": {},
  "research": {
    "market_signals": [],
    "competitor_notes": [],
    "channel_observations": [],
    "evidence": []
  }
}
```

### 6.2 출력
```json
{
  "schema_version": "v1",
  "agent": "strategy",
  "market_assessment": {
    "strengths": ["타겟 명확", "메시지 단순"],
    "risks": ["채널 집중도 부족"],
    "uncertainties": ["초기 CTR 예측 오차"]
  },
  "positioning_options": [
    {"id": "pos_1", "title": "민감피부 집중", "message": "자극 없이 매일 쓰는 진정 루틴"},
    {"id": "pos_2", "title": "빠른 개선", "message": "7일 체감형 피부결 루틴"}
  ],
  "weekly_plan": [
    {"day": "Mon", "action": "핵심 카피 A/B 테스트"},
    {"day": "Wed", "action": "UGC 스타일 영상 업로드"},
    {"day": "Fri", "action": "FAQ 기반 전환 카피 발행"}
  ],
  "required_assets": ["ad_copy", "poster", "video_prompt", "voiceover"]
}
```

### 6.3 검증 규칙
- `positioning_options`는 최소 2개.
- `weekly_plan`은 최소 3개 액션.
- `required_assets`는 `ad_copy`, `poster`, `video_prompt`, `voiceover`를 포함.

## 7. Creative Agent 계약

### 7.1 입력
```json
{
  "session_id": "sess_xxx",
  "strategy": {"positioning_selected": "pos_1", "required_assets": ["ad_copy", "poster", "video_prompt", "voiceover"]},
  "brand_tone": "friendly"
}
```

### 7.2 출력
```json
{
  "schema_version": "v1",
  "agent": "creative",
  "ad_copies": [
    {"id": "copy_1", "text": "피부가 편안해지는 하루 1분 루틴"},
    {"id": "copy_2", "text": "예민한 날에도 가볍게 흡수"}
  ],
  "poster_specs": [
    {
      "id": "poster_1",
      "headline": "민감피부 루틴의 기준",
      "subheadline": "자극 부담은 낮추고 보습은 채우다",
      "visual_keywords": ["clean", "soft light", "product hero"]
    }
  ],
  "video_prompt_package": {
    "duration_sec": 10,
    "size": "720x1280",
    "prompt": "...",
    "shots": [
      "0-2.5s 훅: 제품 클로즈업",
      "2.5-8s 사용 장면",
      "8-10s CTA"
    ]
  }
}
```

### 7.3 검증 규칙
- `ad_copies` 최소 10개 권장(최소 5개 미만이면 실패).
- `poster_specs` 최소 1개.
- `video_prompt_package.duration_sec`는 `5|10|15|20` 중 하나.
- `video_prompt_package.size`는 `480x480|480x854|854x480|720x720|720x1280|1280x720` 중 하나.

## 8. Voice Agent 계약

### 8.1 입력
```json
{
  "session_id": "sess_xxx",
  "strategy_summary": "민감피부 타겟",
  "creative": {"video_prompt_package": {"duration_sec": 10}, "cta": "지금 시작"},
  "voice_preset": "friendly_ko"
}
```

### 8.2 출력
```json
{
  "schema_version": "v1",
  "agent": "voice",
  "voiceover_script_short": "예민한 피부도 편안하게, 오늘부터 가볍게 시작해보세요.",
  "voiceover_script_long": "...",
  "delivery_profile": {"pace": "medium", "emphasis_words": ["편안하게", "가볍게", "시작"]},
  "timing_map": [
    {"start": 0.0, "end": 2.5, "purpose": "hook", "text": "예민한 피부도 편안하게"},
    {"start": 2.5, "end": 8.0, "purpose": "benefit", "text": "매일 부담 없이 흡수되는 루틴"},
    {"start": 8.0, "end": 10.0, "purpose": "cta", "text": "지금 시작해보세요"}
  ],
  "subtitle_lines": [
    {"start": 0.0, "end": 2.5, "text": "예민한 피부도 편안하게"},
    {"start": 2.5, "end": 8.0, "text": "매일 부담 없이 흡수되는 루틴"},
    {"start": 8.0, "end": 10.0, "text": "지금 시작해보세요"}
  ],
  "tts_config": {"model": "gpt-4o-mini-tts", "voice": "alloy", "format": "mp3"}
}
```

### 8.3 검증 규칙
- `timing_map` 첫 구간 시작은 0.0이어야 한다.
- `subtitle_lines`의 시간 범위는 `timing_map`을 벗어나면 안 된다.
- `tts_config`는 `model`, `voice`, `format` 필수.

## 9. 최종 런 패키지 계약
오케스트레이터는 아래 구조로 최종 결과를 저장/응답한다.
```json
{
  "run_id": "run_xxx",
  "brief_summary": {},
  "research_snapshot": {},
  "strategy_plan": {},
  "creative_assets": {},
  "voice_assets": {},
  "kpi_next_actions": {}
}
```

## 10. 오케스트레이터 이벤트 계약
- 상세 이벤트 포맷은 `docs/api.md`를 따른다.
- 이벤트 타입은 `docs/orchestrator_design.md`를 따른다.
- 에이전트 출력은 이벤트 `data`에 전체 포함하지 않고, 필요한 델타/식별자 중심으로 전송한다.

## 11. 실패/폴백 규칙
- 출력 파싱 실패: 동일 프롬프트 1회 재시도
- 재시도 실패: `error.code=SCHEMA_VALIDATION_FAILED` 반환 후 런 종료
- 런타임에서 Mock/Fake 대체 응답 생성 금지
- 보이스 실패: 실패 사유를 반환하고 사용자 재시도 요청
- 미디어 실패: 실패 사유를 반환하고 해당 자산 상태를 `FAILED`로 저장

## 12. 버전 관리
- `schema_version` 기본값: `v1`
- 필드 추가는 하위 호환 방식으로만 진행
- 필수 필드 변경 시 `v2`로 올리고 `docs/api.md`/`docs/orchestrator_design.md` 동시 수정

## 13. 변경 체크리스트
- [ ] `docs/api.md` 이벤트/응답 영향 반영
- [ ] `docs/orchestrator_design.md` 상태 전이 영향 반영
- [ ] `docs/test_runbook.md` 검증 시나리오 반영
