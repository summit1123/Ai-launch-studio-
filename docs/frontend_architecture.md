# 프론트엔드 아키텍처

## 1. 문서 목적
- 이 문서는 채팅+음성 MVP에서 프론트가 상태를 관리하고 스트리밍 이벤트를 처리하는 기준을 정의한다.
- 단일 요청/응답 UI가 아니라, 세션 기반 대화 UI로 전환하기 위한 구현 기준을 제공한다.
- 리서치 결과를 전략/소재와 함께 사용자에게 이해 가능한 실행 패키지 형태로 보여준다.

## 2. 현재 구조 (As-Is)
- `frontend/src/pages/LaunchForm.tsx`: 폼 중심 브리프 입력
- `frontend/src/pages/LaunchResult.tsx`: 단일 결과 요약 표시
- `frontend/src/api/client.ts`: 단건 실행 API 호출
- 현재는 스트리밍/SSE 전용 렌더러와 세션 상태 저장 구조가 없다.

## 3. 목표 구조 (To-Be)
- 채팅 입력(텍스트)과 음성 입력을 같은 세션 상태로 통합한다.
- 서버의 단계별 이벤트를 스트림으로 받아 화면에 점진 렌더링한다.
- `게이트 통과 전`에는 질문/슬롯 수집만 수행하고, `게이트 통과 후` 리서치/전략/소재를 같은 타임라인에 누적 표시한다.

## 4. 핵심 화면 구성
1. 대화 워크스페이스
- 메시지 타임라인
- 슬롯 카드(제품/타겟/채널/목표)
- 단계 상태 배지

2. 결과 패널
- 시장 탭: 시장 시그널/경쟁사/채널 관찰/근거
- 전략 탭: 포지셔닝/주간 운영 플랜
- 소재 탭: 카피/포스터/영상 프롬프트/보이스 스크립트

3. 음성 패널
- 녹음 시작/중지
- 음성 업로드 진행 상태
- 어시스턴트 TTS 재생

## 5. 권장 컴포넌트
- `ChatWorkspace`
- `MessageStream`
- `ChatComposer`
- `BriefSlotCard`
- `StageProgress`
- `ResearchPanel`
- `StrategyPanel`
- `AssetPanel`
- `VoiceInputButton`
- `VoicePlaybackToggle`

## 6. 클라이언트 상태 모델
- `sessionId`: 현재 대화 세션 식별자
- `stage`: `CHAT_COLLECTING | BRIEF_READY | RUN_RESEARCH | GEN_STRATEGY | GEN_CREATIVES | DONE | FAILED`
- `messages[]`: 사용자/어시스턴트 메시지
- `briefSlots`: 슬롯별 값/신뢰도/완성도
- `streamState`: `idle | connecting | open | retrying | closed`
- `lastEventId`: 재연결 시 resume 기준
- `researchSnapshot`: 시장/경쟁/채널/근거 데이터
- `partialOutputs`: 전략/크리에이티브/보이스 중간 결과
- `finalRun`: 최종 실행 결과
- `voiceState`: `idle | recording | uploading | transcribing | ready | error`

## 7. 스트림 처리 설계 (핵심)
### 7.1 전송 방식
- 1차 권장: `POST /api/chat/session/{id}/message/stream` (`text/event-stream`)
- 프론트는 `ReadableStream` 또는 SSE 파서를 사용해 이벤트를 순차 처리한다.

### 7.2 이벤트 엔벨로프
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

### 7.3 이벤트 처리 규칙
- `seq` 기준으로 정렬 적용
- 중복 `event_id`는 무시
- `lastEventId`를 저장해 재연결 시 누락 최소화
- `run.completed` 수신 시 해당 세션 스트림은 정상 종료

### 7.4 최소 처리 이벤트
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

## 8. 음성 턴 처리
- 사용자 음성 업로드: `POST /api/chat/session/{id}/voice-turn`
- 응답으로 `transcript`, `slot_updates`, `next_question`을 수신
- `next_question`은 필요 시 `POST /api/chat/session/{id}/assistant-voice`로 TTS 생성 후 재생
- STT 실패 시 즉시 텍스트 입력 UI로 폴백

## 9. UX 실패/복구 정책
- 스트림 단절: 재연결 버튼 + 마지막 이벤트 기준 재시도
- 음성 변환 실패: transcript 수동 입력창 노출
- 리서치 실패: "시장 데이터 제한" 배지 + 전략 단계 진행
- 게이트 미충족: 누락 슬롯 강조 + 다음 질문 CTA
- 생성 실패: 실패한 단계만 재실행 옵션 제공

## 10. 성능 및 품질 기준
- 메시지 첫 토큰 표시 지연 목표: 1.5초 이내
- 음성 업로드 후 질문 반환 목표: 평균 2.5초 이내
- 브라우저 새로고침 후 세션 복원 가능
- 모바일/데스크톱에서 동일 상태 전이 동작

## 11. 구현 참고 문서
- `docs/api.md`
- `docs/orchestrator_design.md`
- `docs/prompt_contracts.md`
- `docs/voice_chat_mvp_spec.md`
- `docs/voice_agent.md`
- `team.md`
