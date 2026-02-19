# 테스트 런북 (Runbook)

## 1. 문서 목적
- 채팅+음성 MVP의 기능, 안정성, 복구 시나리오를 반복 가능한 절차로 검증한다.
- 리서치 단계가 전략/소재 출력에 반영되는지 확인한다.
- 데모 전 점검 기준을 표준화한다.

## 2. 테스트 범위
- 대화 플로우: 텍스트/음성/혼합 입력
- 게이트: 미충족 차단, 충족 후 생성 전이
- 리서치: 시장/경쟁/채널/근거 필드 유효성
- 스트림: 이벤트 순서, 중단/복구
- 생성: 전략/크리에이티브/보이스 결과 유효성
- 히스토리: 저장/조회/삭제

## 3. 사전 준비
### 3.1 환경
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/frontend
npm install
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

### 3.2 체크
- `GET http://localhost:8000/health` 응답 `{"status":"ok"}` 확인
- 브라우저 콘솔 오류 없는지 확인

## 4. 실행 상태 구분
- `현재 가능(v1)`: launch 단건 실행/이력
- `구현 후 검증(v2)`: 세션 대화/음성/스트림/리서치 반영

## 5. 스모크 테스트
### T-00 서버 스모크 (현재 가능)
- 목적: 서버 기본 동작 확인
- 절차
1. `/health` 호출
2. `/api/launch/run` 최소 payload 호출
- 기대 결과
- 200 응답
- 이력 목록에서 실행 결과 조회 가능

## 6. 핵심 시나리오 (v2 구현 후)

### T-01 텍스트 전용 대화 완주
- 목적: 텍스트만으로 게이트 통과 및 생성 완료
- 절차
1. 세션 시작
2. 텍스트로 슬롯 채우기
3. 게이트 통과 후 생성 요청
- 기대 결과
- 상태 전이: `CHAT_COLLECTING -> BRIEF_READY -> RUN_RESEARCH -> GEN_STRATEGY -> GEN_CREATIVES -> DONE`
- 전략/크리에이티브/보이스 결과 포함

### T-02 음성 전용 대화 완주
- 목적: 음성만으로 동일 결과 달성
- 절차
1. 세션 시작
2. `voice-turn`만 사용하여 슬롯 채우기
3. 생성 요청
- 기대 결과
- STT 결과가 슬롯에 반영
- `assistant-voice`로 질문 음성 재생 가능
- 최종 상태 `DONE`

### T-03 텍스트+음성 혼합 완주
- 목적: 입력 경로 혼합 시 상태 일관성 검증
- 절차
1. 텍스트 2턴
2. 음성 2턴
3. 텍스트 1턴 후 생성
- 기대 결과
- 같은 세션에서 슬롯 충돌 없이 누적
- 최종 출력 계약 유지

### T-04 게이트 차단
- 목적: 미충족 상태에서 생성 차단
- 절차
1. 제품/타겟 일부만 입력
2. 생성 요청
- 기대 결과
- `GATE_NOT_READY` 오류
- 누락 슬롯 리스트 제공

### T-05 리서치 출력 검증
- 목적: 리서치 단계 산출물 품질 검증
- 절차
1. 게이트 충족 후 생성 수행
2. `research_snapshot` 확인
- 기대 결과
- `market_signals`, `competitor_notes`, `channel_observations` 최소 1개
- `evidence`가 존재하거나 fallback 사유가 `risk_flags`에 기록

### T-06 스트림 순서 보장
- 목적: 이벤트 순서/중복 처리 검증
- 절차
1. message stream 호출
2. 이벤트 `seq` 기록
- 기대 결과
- `seq` 단조 증가
- 중복 `event_id` 무시
- `research.delta` 이벤트가 `strategy.delta`보다 먼저 수신

### T-07 스트림 재연결
- 목적: 네트워크 단절 후 복구
- 절차
1. 스트림 수신 중 네트워크 차단/복구
2. 재연결 후 이벤트 수신
- 기대 결과
- 사용자에게 재연결 UI 노출
- 이후 이벤트 수신 재개

### T-08 STT 실패 폴백
- 목적: 음성 실패 복구
- 절차
1. 손상된 오디오 업로드
2. 실패 응답 확인
3. 텍스트로 동일 질문 진행
- 기대 결과
- 오류 메시지 노출
- 텍스트 입력 경로 정상 진행

### T-09 리서치 실패 폴백
- 목적: 리서치 실패 시 전체 중단 방지
- 절차
1. 리서치 의존 호출 실패 상황 유도
2. 생성 수행
- 기대 결과
- `research.status=fallback` 저장
- 전략/크리에이티브/보이스는 생성 계속

### T-10 미디어 실패 폴백
- 목적: 영상 실패 시 핵심 산출물 보존
- 절차
1. 미디어 API 실패 상황 유도
2. 생성 수행
- 기대 결과
- 카피/포스터 스펙/보이스 스크립트는 반환
- 미디어 상태는 `pending` 또는 `failed`로 분리

## 7. API 검증 명령 예시
### 7.1 v1 실행 (현재 가능)
```bash
curl -s -X POST http://localhost:8000/api/launch/run \
  -H "Content-Type: application/json" \
  -d '{
    "brief": {
      "product_name": "Test Product",
      "product_category": "Skincare",
      "target_audience": "20-34",
      "price_band": "mid",
      "total_budget_krw": 1000000,
      "launch_date": "2026-03-01",
      "core_kpi": "inquiry",
      "region": "KR",
      "channel_focus": ["Instagram"],
      "video_seconds": 10
    },
    "mode": "fast"
  }' | jq .
```

### 7.2 v2 세션 시작 (구현 후)
```bash
curl -s -X POST http://localhost:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -d '{"locale":"ko-KR","mode":"standard"}' | jq .
```

## 8. 릴리즈 게이트 (통과 조건)
- [ ] T-00 통과
- [ ] T-01~T-03 통과
- [ ] T-04~T-10 통과
- [ ] 치명도 높은 버그(P0/P1) 0건
- [ ] 문서 동기화 완료(`api`, `db_schema`, `orchestrator_design`, `prompt_contracts`)

## 9. 장애 기록 템플릿
```text
[이슈 ID]
- 발생 시각:
- 재현 단계:
- 기대 결과:
- 실제 결과:
- 영향 범위:
- 로그/스크린샷:
- 임시 조치:
- 영구 조치:
```

## 10. 관련 문서
- `docs/api.md`
- `docs/orchestrator_design.md`
- `docs/prompt_contracts.md`
- `docs/voice_chat_mvp_spec.md`
- `planning.md`
- `team.md`
