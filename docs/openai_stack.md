# OpenAI 스택 활용 계획 (MVP)

업데이트 날짜: 2026-02-19

## 1. 왜 이 스택인가
MVP에서 필요한 것은 대화/구조화 출력/이미지/영상/음성입니다.
각 기능을 OpenAI API로 일관되게 연결해 오케스트레이션 복잡도를 줄입니다.

## 2. 기능 매핑
| 제품 요구 | OpenAI 기능 | 활용 방식 |
|---|---|---|
| 플래너 대화 + 스트리밍 | Responses API + 스트리밍 이벤트 | 대화형 수집, 단계별 실시간 표시 |
| 에이전트 계약 안정화 | 구조화 출력(Structured Outputs) | 슬롯/전략/크리에이티브 스키마 고정 |
| 포스터 생성/편집 | Image generation (`gpt-image-1`) | 포스터 생성 및 이미지 기반 편집 |
| 영상 생성 | Videos API (`sora-2`, `sora-2-pro`) | 숏폼 광고 영상 생성 |
| 내레이션 음성 | TTS (`gpt-4o-mini-tts`) | 보이스 에이전트 스크립트 음성화 |
| 장시간 작업 처리 | Background + Webhook | 비동기 생성 진행 관리 |

## 3. 권장 런타임 패턴
1. 오케스트레이터가 대화/전략까지 실시간 처리
2. 크리에이티브/보이스를 구조화 출력으로 생성
3. 영상 생성은 비동기 작업으로 분리 가능
4. TTS로 보이스 생성 후 영상과 합성
5. 프론트는 스트림 + 상태조회로 진행률 표시

## 4. 모델 가이드
- 텍스트 추론/조정: 백엔드 기본 텍스트 모델
- 이미지: `gpt-image-1`
  - 현재 코드에 `gpt-image-1.5` 사용 흔적이 있어 모델명 정합성 점검 필요
- 영상: `sora-2` 기본, 고품질 필요 시 `sora-2-pro`
- 음성: `gpt-4o-mini-tts`

## 5. 안전/정책 체크
- 광고 카피는 과장/금지표현 필터 필수
- 저작권 침해 가능성이 있는 음악 모사 프롬프트 금지
- 정책 위반 가능성이 있는 영상 요청 차단
- 필요 시 AI 음성 사용 고지

## 6. 공식 문서
- [Streaming responses 가이드](https://developers.openai.com/api/docs/guides/streaming-responses)
- [Structured outputs 가이드](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Image generation 가이드](https://developers.openai.com/api/docs/guides/image-generation)
- [Video generation 가이드](https://developers.openai.com/api/docs/guides/video-generation)
- [Videos API 레퍼런스](https://platform.openai.com/docs/api-reference/videos)
- [Text-to-speech 가이드](https://developers.openai.com/api/docs/guides/text-to-speech)
- [Create speech API](https://platform.openai.com/docs/api-reference/audio/createSpeech)
- [Background 모드 가이드](https://platform.openai.com/docs/guides/background)
- [Webhooks 가이드](https://platform.openai.com/docs/guides/webhooks)
