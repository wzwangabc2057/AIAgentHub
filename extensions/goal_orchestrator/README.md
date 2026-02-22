# Goal Orchestrator (Extension)

外部目标编排层（不改 aiagent 主系统）：
- 输入目标
- 自动拆解问题
- 生成 chain 并调用 aiagent 执行
- 查询链路状态与步骤结果

## Run

```bash
cd /Users/kangbing/112/pythontest/aiagent
python -m extensions.goal_orchestrator.run
```

## API

- `GET /health`
- `POST /goals` `{ "goal": "..." }`
- `GET /goals`
- `GET /goals/{goal_id}`

## Env (optional)

- `GOAL_ORCH_PORT=9110`
- `GOAL_ORCH_AIAGENT_BASE_URL=http://127.0.0.1:9100`
