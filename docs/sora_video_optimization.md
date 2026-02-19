# Sora 영상 + 오디오 최적화 가이드

## 1. 목표
"짜치는" 결과를 줄이기 위해 영상과 음성을 분리 최적화한다.
- Sora: 화면 연출/모션/기본 앰비언스
- Voice Agent + TTS: 브랜드 톤이 고정된 내레이션
- 후반 합성: ducking, loudness, 자막

## 2. Sora 기본 파라미터
권장값:
- 모델: `sora-2`
- 길이: 10초 또는 15초
- 해상도: 가로 `1280x720`, 세로 `720x1280`

문서 기준 지원 값:
- duration: `5`, `10`, `15`, `20`
- size: `480x480`, `480x854`, `854x480`, `720x720`, `720x1280`, `1280x720`

현재 코드 참고:
- `backend/app/services/media_service.py`는 `4/8/12`로 정규화 중
- 실제 API 지원값과 맞추는 정합화 작업 필요

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
