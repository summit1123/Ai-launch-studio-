# AGENTS.md

## 프로젝트 미션
AI Launch Studio는 **이미 제품을 가진 사용자를 위한 프로모션 코파일럿**입니다.
MVP 목표는 다음과 같습니다.
- 챗봇/음성 대화로 브리프 수집
- 시장 평가와 포지셔닝 제안
- 카피/포스터/영상/음성 에셋 생성
- 실행 가능한 주간 운영 플랜 제공

## 제품 범위 (현재 고정)
- 핵심 사용자: 판매 중인 제품을 보유한 운영자/브랜드 담당자
- 핵심 문제: "이번 주에 무엇을 어떻게 홍보해야 하는가"
- MVP 초점: 홍보 전략 + 소재 제작
- MVP 제외: 재고/매출 시스템 연동, 광고 집행 자동화

## 에이전트 구성 (목표)
1. 오케스트레이터 에이전트
2. 플래너 에이전트 (대화형 수집 + 슬롯 채우기)
3. 전략 에이전트 (시장평가/포지셔닝/실행안)
4. 크리에이티브 에이전트 (카피/포스터/영상 프롬프트)
5. 보이스 에이전트 (나레이션 스크립트 + TTS 설정)

## 기준 문서
- MVP 범위: `docs/mvp.md`
- 음성 대화 명세: `docs/voice_chat_mvp_spec.md`
- BM: `docs/business_model.md`
- 확장 로드맵: `docs/expansion.md`
- 프론트 설계: `docs/frontend_architecture.md`
- 백엔드 설계: `docs/backend_architecture.md`
- 오케스트레이션 설계: `docs/orchestrator_design.md`
- API 계약: `docs/api.md`
- DB 구조: `docs/db_schema.md`
- OpenAI 활용 설계: `docs/openai_stack.md`
- Sora 최적화: `docs/sora_video_optimization.md`
- 개발 환경(uv): `docs/uv_setup.md`

## 작업 규칙
- 코드 변경 시 관련 문서를 같은 PR에서 함께 수정합니다.
- API 변경 시 `docs/api.md`를 즉시 갱신합니다.
- DB 변경 시 `docs/db_schema.md`를 즉시 갱신합니다.
- 에이전트 책임 변경 시 `docs/orchestrator_design.md`, `docs/voice_agent.md`를 갱신합니다.
- 프롬프트/출력 스키마는 버전 정보를 남겨 재현성을 확보합니다.

## MVP 완료 기준
- 챗봇/음성 수집이 스트리밍 UX로 동작합니다.
- 브리프 게이트를 통과해야 전략 생성 단계로 넘어갑니다.
- 전략/카피/포스터/영상/보이스 결과가 구조화되어 저장됩니다.
- 실행 이력이 조회 가능하고 결과물을 복사/다운로드할 수 있습니다.

## OpenAI 사용 원칙
- 공식 OpenAI API만 사용합니다.
- 에이전트 간 계약은 구조화된 출력으로 고정합니다.
- 플래너/전략/크리에이티브 단계는 스트리밍 이벤트를 제공합니다.
- 광고 카피는 안전 필터(과장/금지표현)를 거친 후 제공해야 합니다.
- 보이스 톤은 보이스 에이전트 설정으로 일관되게 유지합니다.
