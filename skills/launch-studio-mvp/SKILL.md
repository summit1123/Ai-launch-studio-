---
name: "launch-studio-mvp"
description: "AI Launch Studio MVP 작업(브리프 수집/전략/크리에이티브/보이스)용 프로젝트 스킬 템플릿"
---

# Launch Studio MVP Skill

## 목적
제품 보유 사용자를 위한 프로모션 코파일럿 MVP를 일관된 방식으로 구현/수정한다.

## 실행 규칙
1. 먼저 `team.md`, `planning.md`, `docs/mvp.md`, `docs/voice_chat_mvp_spec.md`를 확인한다.
2. API/DB 변경 전 `docs/api.md`, `docs/db_schema.md`를 확인한다.
3. 오케스트레이터 변경 전 `docs/orchestrator_design.md`를 확인한다.
4. 보이스 관련 변경 시 `docs/voice_agent.md`를 확인한다.
5. OpenAI 기능/파라미터 변경 시 `docs/openai_stack.md`, `docs/sora_video_optimization.md`를 확인한다.

## 단계별 참조 우선순위
- 환경/온보딩: `docs/uv_setup.md`, `backend/README.md`, `frontend/README.md`
- 백엔드 계약: `docs/api.md`, `docs/db_schema.md`, `docs/orchestrator_design.md`
- 음성 경로: `docs/voice_chat_mvp_spec.md`, `docs/voice_agent.md`
- 크리에이티브/미디어: `docs/openai_stack.md`, `docs/sora_video_optimization.md`
- 협업/릴리즈: `team.md`, `docs/codex_workflow.md`, `docs/test_runbook.md`

## 출력 형식
- 변경 요약
- 영향 받는 API/DB
- 테스트 또는 검증 결과
- 후속 작업 제안(있을 때만)

## 실패 시 폴백
- STT 실패: 텍스트 입력으로 전환
- 영상 생성 실패: 영상 프롬프트와 보이스 패키지 우선 제공
- 구조화 출력 실패: 최소 요약 응답 + 재시도 안내
