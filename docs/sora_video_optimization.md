# Sora 영상 + 오디오 최적화 가이드

## 1. 목표
"짜치는" 결과를 줄이기 위해 영상과 음성을 분리 최적화한다.
- Sora: 화면 연출/모션/기본 앰비언스
- Voice Agent + TTS: 브랜드 톤이 고정된 내레이션
- 후반 합성: ducking, loudness, 자막

## 2. Sora 기본 파라미터
권장값:
- 모델: `sora-2`
- 길이: `4`, `8`, `12`초
- 해상도: `1280x720`, `720x1280`, `1792x1024`, `1024x1792`
- MVP 기본 길이: `12`초

문서 기준 지원 값:
- duration: `4`, `8`, `12`
- size: `720x1280`, `1280x720`, `1024x1792`, `1792x1024`

현재 코드 참고:
- `backend/app/services/media_service.py`는 `4/8/12`로 정규화

### 2.1 나레이션 길이 예산(필수)
영상 길이 대비 멘트가 길면 끝부분이 잘리므로, 아래 예산을 기본값으로 고정한다.
- `4초`: 최대 1문장, 약 `18자` 이내
- `8초`: 최대 2문장, 약 `34자` 이내
- `12초`: 최대 3문장, 약 `52자` 이내
- CTA는 `8~12자`의 짧은 행동 문구만 사용

구현 메모(현재 코드):
- `backend/app/agents/orchestrator.py`에서 초수별 나레이션/장면 길이를 후처리로 강제 정규화
- 모델 출력이 길어도 패키지 저장 전 길이 예산 내로 축약
- `backend/app/services/media_service.py`는 후처리 인코딩 시 원본 비디오 해상도를 우선 유지해
  불필요한 1080p 업스케일로 인한 선명도 저하를 줄인다.

## 3. 프롬프트 설계 패턴

### 3.1 구조
1. 샷 리스트
2. 카메라/모션 지시
3. 제품 히어로 컷
4. 조명/색감
5. 화면 텍스트 제약
6. 오디오 지시(음악 분위기/SFX)

### 3.2 템플릿
```text
Create a {duration}s promotional video for {product_name}.
Target audience: {target}
Primary message: {positioning_message}

Shot 1 (0-2.5s): Hook visual, close-up product reveal.
Shot 2 (2.5-8s): Real usage scene, key benefit.
Shot 3 (8s-end): Clear CTA scene.

Style: {style_keywords}
Color: {color_direction}
Pacing: {pacing}
On-screen text: minimal and readable.
Audio: modern ambient bed + subtle transition SFX.
```

## 4. 포스터/영상 일관성
- 제품 이미지가 있으면 참조 이미지 기반 생성 사용
- 포스터와 영상의 팔레트/키워드를 공유
- 렌더 1회당 핵심 메시지 1개만 고정
- 구현 메모(현재 코드):
  - 포스터: `images.edit`에 참조 이미지 전달
  - 영상: Videos API `input_reference`로 참조 이미지 전달
  - 영상 참조 이미지: 요청 사이즈(`size`)에 맞게 자동 scale+crop 후 전달
  - 영상 fallback: 키프레임 생성 시 `images.edit` 참조 이미지 전달

## 5. 음성 품질 스택
1. Voice Agent가 스크립트/타이밍 생성
2. TTS를 고정 보이스로 생성
3. 영상 배경음 위에 합성
4. 발화 구간 ducking 적용
5. 자막(SRT) 동기화

## 6. ffmpeg 합성 예시
```bash
ffmpeg -i video.mp4 -i narration.wav \
-filter_complex "[0:a]volume=0.35[a0];[a0][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]" \
-map 0:v -map "[a]" -c:v copy -c:a aac -shortest out_with_voice.mp4
```

## 7. 안정성 패턴
- 생성 요청 제출
- 상태 폴링/웹훅 수신
- 완료 시 콘텐츠 다운로드
- 메타데이터와 함께 저장

## 8. 가드레일
- 저작권 캐릭터/음악 모사 금지
- 정책 민감 장면 차단
- 내보내기 전 안전 필터 적용

## 9. 운영 체크리스트
- 프롬프트 템플릿 버전 고정
- 채널별 해상도 프리셋 고정
- 브랜드별 보이스 프리셋 고정
- 톤 재생성 원클릭 제공
- 프롬프트/파라미터 기록 보관

## 10. 공식 문서
- [Video generation 가이드](https://developers.openai.com/api/docs/guides/video-generation)
- [Videos API 레퍼런스](https://platform.openai.com/docs/api-reference/videos)
- [Text-to-speech 가이드](https://developers.openai.com/api/docs/guides/text-to-speech)
- [Create speech API](https://platform.openai.com/docs/api-reference/audio/createSpeech)
