# 프론트엔드 아키텍처

## 1. 현재 구조 (As-Is)
- `frontend/src/pages/LaunchForm.tsx`: 폼 중심 브리프 입력
- `frontend/src/pages/LaunchResult.tsx`: 단일 결과 표시
- `frontend/src/api/client.ts`: 단건 실행 API 호출

## 2. 목표 구조 (To-Be)
대화 중심 + 스트리밍 + 음성 입력/출력 지원

## 3. 핵심 화면
1. 대화 워크스페이스
  - 플래너 질문/답변 스트림
  - 브리프 슬롯 충족 상태
  - 단계 진행 상태
2. 전략 탭
  - 시장평가
  - 포지셔닝 옵션
  - 주간 운영 체크리스트
3. 소재 탭
  - 카피 목록
  - 포스터 미리보기/다운로드
  - 영상 프롬프트/보이스 출력

## 4. 권장 컴포넌트
- `ChatComposer`
- `MessageStream`
- `VoiceInputButton`
- `VoicePlaybackToggle`
- `BriefSlotCard`
- `StageProgress`
- `StrategyPanel`
- `AssetPanel`
- `VoicePanel`

## 5. 클라이언트 상태
- `sessionId`
- `messages[]`
- `briefSlots`
- `stage`
- `partialOutputs`
- `finalPackage`
- `voiceState` (녹음/전송/재생)

## 6. UX 규칙
- 스트리밍 델타는 순서대로 렌더링
- 자동 스크롤 잠금 가능
- 스트림 끊김 시 재시도 버튼 제공
- 음성 실패 시 텍스트 입력으로 즉시 폴백
