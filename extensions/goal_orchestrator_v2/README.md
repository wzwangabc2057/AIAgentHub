# Goal Orchestrator V2

新增两块能力：
- 自动触发与重规划（Scheduler + Policy Engine）
- 方法模板化与 A/B 验证（Method Memory + Evaluator）

## Run

```bash
cd /Users/kangbing/112/pythontest/aiagent
python -m extensions.goal_orchestrator_v2.run
```

默认端口：`9120`

## API

- `GET /health`
- `POST /goals`
- `GET /goals`
- `GET /goals/{goal_id}`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /methodology`
- `GET /experiments`
- `POST /dispatch`
- `GET /dispatch/receipts`
- `POST /scheduler/tick`

## Env

- `GOAL_ORCH_V2_PORT=9120`
- `GOAL_ORCH_V2_AIAGENT_BASE_URL=http://127.0.0.1:9100`
- `GOAL_ORCH_V2_DISPATCH_5005_URL=http://127.0.0.1:5005/ask`
- `GOAL_ORCH_V2_DISPATCH_5005_TOKEN=<token>`
- `GOAL_ORCH_V2_DAY_POLL_SECONDS=120`
- `GOAL_ORCH_V2_NIGHT_POLL_SECONDS=40`
- `GOAL_ORCH_V2_RUN_STALL_SECONDS=900`
- `GOAL_ORCH_V2_MAX_REPLANS=2`
- `GOAL_ORCH_V2_AB_EPSILON=0.2`
