# 오케스트레이터 설계

## 1. 상태 머신
- `CHAT_COLLECTING`
- `BRIEF_READY`
- `RUN_RESEARCH`
- `GEN_STRATEGY`
- `GEN_CREATIVES`
- `DONE`
- `FAILED`

전이 규칙:
- 필수 슬롯이 모두 채워질 때까지 `CHAT_COLLECTING` 유지
- 게이트 통과 시 `BRIEF_READY` 전이
- `BRIEF_READY` 직후 리서치 단계(`RUN_RESEARCH`) 실행
- 리서치 성공 시 `GEN_STRATEGY`
- 전략 완료 후 `GEN_CREATIVES`

## 2. 브리프 게이트

### 제품
- `name`
- `category`
- `features` (3개 이상)
- `price_band`

### 타겟
- `who`
- `why`

### 채널
- `channels` (1~2개)

### 목표
- `weekly_goal` (조회/문의/구매 중 1개)

## 3. 에이전트 책임
1. 플래너
- 사용자 입력 해석
- 슬롯 업데이트
- 다음 질문 1개 생성

2. 리서치
- 시장/경쟁사/채널 신호 수집
- 가격/포지셔닝 벤치마크
- 출처와 신뢰도 메타데이터 반환

3. 전략
- 리서치 결과를 브리프와 결합
- 위험/불확실 구간 정리
- 포지셔닝/메시지 옵션
- 주간 실행 체크리스트

4. 크리에이티브
- 광고 카피
- 포스터 콘셉트
- 영상 프롬프트

5. 보이스
- 내레이션 스크립트
- 톤/속도/강조어 설정
- 자막 타이밍

6. 오케스트레이터
- 상태 전이
- 이벤트 스트리밍
- 재시도/폴백
- 저장

## 4. 스트리밍 이벤트
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

## 5. 리서치 단계 정책
- 리서치 타임아웃: 10초(기본) / 20초(최대)
- 리서치 실패 시 폴백
  - `research.status=fallback` 저장
  - 최소 전략 생성은 계속 진행
  - UI에 "시장 데이터 제한" 배지 표시
- 리서치 결과는 최소 아래 필드를 포함
  - `market_signals`
  - `competitor_notes`
  - `channel_observations`
  - `evidence`

## 6. 의사코드
```text
start_session()
state = CHAT_COLLECTING
while state == CHAT_COLLECTING:
  planner = planner.run(user_message, slots)
  emit(planner.delta)
  apply(slots, planner.slot_updates)
  emit(slot.updated)
  if gate_passed(slots):
    state = BRIEF_READY
    emit(gate.ready)
    emit(stage.changed)

state = RUN_RESEARCH
emit(stage.changed)
research = research_agent.run(slots)
emit(research.delta)

state = GEN_STRATEGY
emit(stage.changed)
strategy = strategy_agent.run(slots, research)
emit(strategy.delta)

state = GEN_CREATIVES
emit(stage.changed)
creative = creative_agent.run(slots, strategy)
voice = voice_agent.run(slots, strategy, creative)
emit(creative.delta)
emit(voice.delta)

save_run()
state = DONE
emit(run.completed)
```

## 7. 재시도/타임아웃
- 플래너: 재시도 1회
- 리서치: 재시도 1회 + 폴백 허용
- 전략: 재시도 1회
- 크리에이티브/보이스: 각 1회
- 고비용 미디어 생성은 백그라운드 모드 허용

## 8. 결과 조립 규칙
최종 응답은 아래 묶음으로 조립한다.
1. `brief_summary`
2. `research_snapshot`
3. `strategy_plan`
4. `creative_assets`
5. `voice_assets`
6. `kpi_next_actions`
