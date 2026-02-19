# AI Launch Studio Backend

## Run

```bash
cd /Users/a311/Documents/GitHub/AI/ai-launch-studio/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## API

- `GET /health`
- `POST /api/launch/run`
- `GET /api/launch/history?limit=20&offset=0&q=keyword`
- `GET /api/launch/history/{request_id}`
- `DELETE /api/launch/history/{request_id}`

`/api/launch/run`는 에이전트별 전용 구조화 필드를 포함합니다.
- `research_summary.market_signals`
- `launch_plan.milestones`
- `campaign_strategy.channel_tactics`
- `budget_and_kpi.budget_split_krw`
- `marketing_assets.video_scene_plan`

Example body:

```json
{
  "brief": {
    "product_name": "Glow Serum X",
    "product_category": "Skincare",
    "target_audience": "20-34 뷰티 얼리어답터",
    "price_band": "mid-premium",
    "total_budget_krw": 120000000,
    "launch_date": "2026-04-01",
    "core_kpi": "런칭 후 4주 내 재구매율 25%",
    "region": "KR",
    "channel_focus": ["Instagram", "YouTube", "Naver SmartStore"]
  },
  "mode": "standard"
}
```
