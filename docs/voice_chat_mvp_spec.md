# 대화형 온보딩 MVP 명세

## 1. 목적
사용자가 텍스트로 자유롭게 답하면 시스템이 필요한 정보만 조건부 질문하며 브리프를 채운다.
브리프 게이트가 충족되면 리서치/전략/소재 생성으로 자동 전환한다.

현재 범위:
- 입력 채널은 텍스트 채팅 단일 모드
- 음성 모드는 MVP 안정화 후 재도입 예정

## 2. 사용자 시나리오
1. 세션 시작
2. 어시스턴트 질문 텍스트 표시
3. 사용자 텍스트 입력
4. LLM+규칙 기반 슬롯 업데이트 + 부족 항목 판정
5. 다음 질문 생성
6. 게이트 통과 시 리서치/전략/소재 단계 진입

## 3. 대화 규칙
- 사용자 질문/요청이 있으면 먼저 직접 답변
- `CHAT_COLLECTING` 상태에서는 필요한 경우에만 후속 질문 1개 추가
- 이미 채워진 슬롯 재질문 금지
- 모호한 답변은 최대 2회 재확인
- 멀티턴 누적: 최근 대화 맥락을 사용해 슬롯을 점진적으로 보강
- 최대 20턴
- 20턴 초과 시 "현재 정보로 초안 생성" 또는 "추가 입력" 선택 제공

## 4. 브리프 슬롯 정의

### 제품
- `name`
- `category`
- `features` (3개 이상)
- `price_band` (`low` / `mid` / `premium`)
  - 숫자만 입력한 가격도 허용 (예: `39000`, `39,000`)

### 타겟
- `who`
- `why`

### 채널
- `channels` (1~2개)

### 목표
- `weekly_goal` (`reach` / `inquiry` / `purchase`)

게이트 조건:
- 필수 슬롯 전부 채움
- 슬롯 신뢰도 평균 0.7 이상

## 5. 상태 머신
- `IDLE`
- `CHAT_COLLECTING`
- `TRANSCRIBING` (음성 입력 시)
- `SLOT_UPDATING`
- `BRIEF_READY`
- `RUN_RESEARCH`
- `GEN_STRATEGY`
- `GEN_CREATIVES`
- `DONE`
- `FAILED`

## 6. API 초안
- `POST /api/chat/session`
- `POST /api/chat/session/{id}/message`
- `POST /api/chat/session/{id}/message/stream`
- `POST /api/chat/session/{id}/voice-turn`
- `POST /api/chat/session/{id}/assistant-voice`
- `GET /api/chat/session/{id}`
- `POST /api/runs/{id}/generate`

## 7. 이벤트
- `planner.delta`
- `slot.updated`
- `gate.ready`
- `stage.changed`
- `research.delta`
- `strategy.delta`
- `creative.delta`
- `voice.delta`
- `run.completed`
- `error`

## 8. OpenAI 기능 매핑
- 텍스트 모델: 슬롯 추출(대화 맥락 포함), 질문 생성, 리서치/전략/크리에이티브 생성
- Video API: 영상 생성
- Image generation: 포스터 생성

## 9. 성능 목표
- 턴 응답(질문 반환) 평균 2.5초 이내
- 텍스트 턴 슬롯 반영 성공률 85% 이상

## 10. 제외 범위
- 음성 입력/출력 모드
- 광고 매체 자동 집행
- 재고/매출 시스템 연동
