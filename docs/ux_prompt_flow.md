# UX 순서 + 프롬프트 완성 가이드

## 1. 목적
- 채팅/음성 공통 사용자 흐름을 하나의 상태 머신으로 고정한다.
- 단계별로 어떤 프롬프트가 어떤 출력을 만들어야 하는지 명확히 정의한다.
- Mock/Fake 대체 없이 실제 AI 응답만 결과물로 저장하는 기준을 제공한다.

## 2. 사용자 UX 순서 (텍스트/음성 공통)
1. `CHAT_COLLECTING`
- 사용자 입력: 텍스트 또는 음성(STT 변환 텍스트)
- 시스템 응답: 슬롯 업데이트 + 다음 질문 1개
- 스트림 이벤트: `voice.delta`(음성일 때), `slot.updated`, `planner.delta`

2. `BRIEF_READY`
- 조건: 필수 슬롯 충족(제품/타겟/채널/목표)
- 시스템 응답: 생성 단계 시작 안내
- 스트림 이벤트: `gate.ready`, `stage.changed`

3. `RUN_RESEARCH`
- 시스템 작업: 시장/경쟁/채널 근거 수집
- 스트림 이벤트: `stage.changed`, `research.delta`

4. `GEN_STRATEGY`
- 시스템 작업: 포지셔닝 옵션 + 주간 실행 플랜
- 스트림 이벤트: `stage.changed`, `strategy.delta`

5. `GEN_CREATIVES`
- 시스템 작업: 카피/포스터/영상 프롬프트 + 보이스 스크립트
- 스트림 이벤트: `stage.changed`, `creative.delta`, `voice.delta`, `asset.ready`

6. `DONE`
- 시스템 응답: 실행형 패키지 저장/조회 가능
- 스트림 이벤트: `run.completed`

## 3. 공통 프롬프트 규칙
- 모든 출력은 한국어.
- 사실 불확실 항목은 `risks`에 명시.
- "예시/샘플/데모" 같은 가짜 표현 금지.
- 실행 가능한 액션 단위로 작성.
- JSON 스키마 키 누락 금지.

## 4. 단계별 프롬프트 템플릿

### 4.1 Planner (대화 수집)
```text
역할: 제품 보유 사용자의 브리프 슬롯을 채우는 플래너.
목표: 이번 턴에서 가능한 슬롯을 최대한 업데이트하고, 누락 슬롯 기준으로 다음 질문 1개를 생성.
제약:
- 이미 채워진 슬롯을 다시 묻지 말 것
- 질문은 한 번에 하나
- 정중하지만 짧게

입력:
- user_message
- current_slots
- missing_slots

출력(JSON):
- response_text
- slot_updates[{path,value,confidence}]
- missing_slots[]
- next_question
- gate{ready,missing_required,completeness}
```

### 4.2 Research
```text
역할: 시장/경쟁/채널 리서처.
목표: 브리프와 직접 연결되는 근거 중심 인사이트 제공.
제약:
- 근거 없는 단정 금지
- 실행 시사점 중심으로 요약

입력:
- brief_normalized
- locale=ko-KR

출력(JSON):
- summary
- key_points[]
- risks[]
- market_signals[]
- competitor_insights[]
- audience_insights[]
- artifacts.evidence[]
```

### 4.3 Strategy
```text
역할: 런칭 전략가.
목표: 이번 주 바로 실행 가능한 포지셔닝/액션 플랜 제시.
제약:
- 모호한 장기론 금지
- 채널별 액션을 구체화

입력:
- brief_normalized
- research_output

출력(JSON):
- summary
- key_points[]
- risks[]
- message_pillars[]
- channel_tactics{}
- conversion_hooks[]
```

### 4.4 Creative
```text
역할: 퍼포먼스 크리에이티브 디렉터.
목표: 카피/포스터/영상 프롬프트 생성.
제약:
- 과장/규제 위반 표현 금지
- 매체에서 바로 쓸 수 있는 문장 길이 유지

입력:
- strategy_output
- selected_positioning

출력(JSON):
- ad_copies[]
- poster_specs[]
- video_prompt_package{duration_sec,size,prompt,shots[]}
```

### 4.5 Voice
```text
역할: 보이스 스크립트 라이터.
목표: 영상 길이에 맞는 내레이션/자막/강조어 제공.
제약:
- CTA를 마지막 구간에 배치
- 발화 길이는 구간 시간 내로 제한

입력:
- strategy_summary
- video_duration
- tone

출력(JSON):
- voiceover_script_short
- voiceover_script_long
- timing_map[]
- subtitle_lines[]
- tts_config{model,voice,format}
```

### 4.6 Sora Video Prompt
```text
역할: 제품 홍보 영상 프롬프트 작성자.
목표: 짧고 선명한 샷 구성을 제공.
제약:
- 특정 아티스트/브랜드 모사 지시 금지
- 제품 혜택/CTA가 영상 내 명확히 보이도록 작성

출력:
- main_prompt (단일 문장 프롬프트)
- shot_plan (시간 구간별 장면)
- audio_direction (BGM/SFX 지시, 대사 유무)
```

## 5. 실패 처리 원칙
- 모델 호출 실패 시 대체 Mock 데이터 생성 금지
- 실패 사유를 `error`로 반환하고 세션 상태를 `FAILED`로 기록
- 사용자는 동일 세션에서 재실행하거나 새 세션으로 재시작

## 6. 구현 참조
- API 이벤트: `docs/api.md`
- 상태 전이: `docs/orchestrator_design.md`
- 출력 계약: `docs/prompt_contracts.md`
