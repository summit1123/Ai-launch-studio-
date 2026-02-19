# 프론트엔드

## 실행
```bash
cd /Users/gimdonghyeon/Downloads/ai-launch-studio/frontend
npm install
npm run dev
```

선택 환경 변수:
```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## 현재 흐름
- 폼 중심 브리프 입력
- 실행 결과 렌더링
- 이력 조회

## 목표 흐름
- 챗봇 중심 브리프 수집
- 스트리밍 응답 표시
- 슬롯 게이트 진행률 시각화
- 음성 대화(스무고개 스타일) 지원

관련 문서:
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/frontend_architecture.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/voice_chat_mvp_spec.md`
- `/Users/gimdonghyeon/Downloads/ai-launch-studio/docs/api.md`
