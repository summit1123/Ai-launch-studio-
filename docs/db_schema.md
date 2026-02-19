# DB 스키마

## 1. 현재 스키마 (구현됨)
저장소: SQLite (WAL 모드)

테이블: `launch_runs`

```sql
CREATE TABLE IF NOT EXISTS launch_runs (
  request_id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  mode TEXT NOT NULL,
  product_name TEXT NOT NULL,
  core_kpi TEXT NOT NULL,
  package_json TEXT NOT NULL
);
```

특징:
- 기본키: `request_id`
- 목록 조회: `created_at DESC`
- 검색: `product_name`, `core_kpi` LIKE

## 2. 목표 스키마 (대화형 MVP)

### 2.1 `chat_sessions`
```sql
CREATE TABLE chat_sessions (
  session_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  mode TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

### 2.2 `chat_messages`
```sql
CREATE TABLE chat_messages (
  message_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
);
```

### 2.3 `brief_slots`
```sql
CREATE TABLE brief_slots (
  session_id TEXT PRIMARY KEY,
  product_json TEXT NOT NULL,
  target_json TEXT NOT NULL,
  channel_json TEXT NOT NULL,
  goal_json TEXT NOT NULL,
  completeness REAL NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
);
```

### 2.4 `run_outputs`
```sql
CREATE TABLE run_outputs (
  run_id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  request_id TEXT,
  strategy_json TEXT NOT NULL,
  creative_json TEXT NOT NULL,
  voice_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(session_id) REFERENCES chat_sessions(session_id)
);
```

### 2.5 `media_assets`
```sql
CREATE TABLE media_assets (
  asset_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  asset_type TEXT NOT NULL,
  local_path TEXT,
  remote_url TEXT,
  metadata_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES run_outputs(run_id)
);
```

## 3. 마이그레이션 전략
1. 기존 `launch_runs`는 유지
2. 신규 테이블을 단계적으로 추가
3. 필요 시 `package_json`에서 `run_outputs`로 백필

## 4. 운영 권장
- 실행 메타데이터는 길게 보관
- 대용량 미디어 파일은 정리 정책 적용
- 고아 파일(레코드 없는 파일) 정기 정리
