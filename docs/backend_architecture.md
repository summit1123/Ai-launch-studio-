# 백엔드 아키텍처

## 1. 현재 구조 (As-Is)
- FastAPI 엔트리: `backend/app/main.py`
- 런치 라우터: `backend/app/routers/launch.py`
- 오케스트레이터: `backend/app/agents/orchestrator.py`
- 이력 저장소: `backend/app/repositories/sqlite_history.py`
- 미디어 서비스: `backend/app/services/media_service.py`

## 2. 목표 구조 (To-Be)
대화 세션 + 스트리밍 + 음성 턴 처리 추가

## 3. 권장 모듈
- `routers/chat.py` (세션/메시지/스트림)
- `routers/voice.py` (음성 입력 STT, 질문 TTS)
- `services/session_service.py`
- `services/gate_service.py`
- `services/media_pipeline.py`
- `agents/voice_agent.py`
- `workers/media_jobs.py` (비동기 선택)

## 4. 책임 분리
- API 레이어: 검증/프로토콜
- 오케스트레이터: 상태 전이/에이전트 라우팅
- 서비스: STT/TTS/미디어 합성/안전 필터
- 저장소: 세션/메시지/실행 결과 영속화

## 5. 실패 대응
- 단계별 timeout budget
- 에이전트 실패 시 구조화 폴백 응답
- 부분 결과 저장 및 재시도
- 사용자 재실행 포인트 제공

## 6. 관측성
- session_id/request_id 공통 로깅
- 단계 전이 로그
- 모델/도구별 지연 시간
- 생성 성공/실패 지표
