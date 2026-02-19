# 음성 대화형 MVP 명세 (스무고개 스타일)

## 1. 목적
사용자가 음성으로 답하면 시스템이 필요한 정보만 질문하며 브리프를 채운다.
브리프 게이트가 충족되면 전략/소재 생성으로 자동 전환한다.

## 2. 사용자 시나리오
1. 세션 시작
2. 어시스턴트 질문 음성 재생(TTS)
3. 사용자 음성 답변 업로드/녹음
4. STT로 텍스트 변환
5. 슬롯 업데이트 + 부족 항목 판정
6. 다음 질문 생성
7. 게이트 통과 시 생성 단계 진입

## 3. 대화 규칙 (스무고개)
- 한 턴에 질문은 1개만
- 이미 채워진 슬롯 재질문 금지
- 모호한 답변은 최대 2회 재확인
- 최대 20턴
- 20턴 초과 시 "현재 정보로 초안 생성" 또는 "추가 입력" 선택 제공

## 4. 브리프 슬롯 정의

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
- `weekly_goal` (`reach` / `inquiry` / `purchase`)

게이트 조건:
- 필수 슬롯 전부 채움
- 슬롯 신뢰도 평균 0.7 이상

## 5. 상태 머신
- `IDLE`
- `VOICE_LISTENING`
- `TRANSCRIBING`
- `SLOT_UPDATING`
- `ASKING_NEXT`
- `BRIEF_READY`
- `GEN_STRATEGY`
- `GEN_CREATIVES`
- `DONE`
- `FAILED`

## 6. API 초안
- `POST /api/chat/session`
- `POST /api/chat/session/{id}/voice-turn`
- `POST /api/chat/session/{id}/assistant-voice`
- `GET /api/chat/session/{id}`
- `POST /api/runs/{id}/generate`
- (선택) `GET /api/chat/session/{id}/stream`

## 7. 이벤트
- `voice.transcribed`
- `slot.updated`
- `question.generated`
- `gate.ready`
- `stage.changed`
- `run.completed`
- `error`

## 8. OpenAI 기능 매핑
- STT: 사용자 음성을 텍스트로 변환
- 텍스트 모델: 슬롯 추출, 질문 생성, 전략/크리에이티브 생성
- TTS: 어시스턴트 질문 및 나레이션 음성 생성
- Video API: 영상 생성
- Image generation: 포스터 생성

## 9. 성능 목표
- 턴 응답(질문 반환) 평균 2.5초 이내
- STT 후 슬롯 반영 성공률 85% 이상
- 실패 시 텍스트 입력 폴백 100% 가능

## 10. 제외 범위
- 실시간 풀듀플렉스 음성 통화
- 광고 매체 자동 집행
- 재고/매출 시스템 연동
