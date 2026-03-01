# Goal Orchestrator (Extension)

外部目标编排层（不改 aiagent 主系统）：
- 输入目标
- 自动拆解问题
- 生成 chain 并调用 aiagent 执行
- 查询链路状态与步骤结果
- 统一任务状态机（run / task_steps）
- 派单回执协议（CCB / 5005 / aiagent 协议占位）
- 自动反思回写（方法论权重）

## Run

```bash
cd /Users/kangbing/112/pythontest/aiagent
python -m extensions.goal_orchestrator.run
```

## API

- `GET /health`
- `POST /goals` `{ "goal": "...", "owner": "pm", "priority": "normal" }`
- `GET /goals`
- `GET /goals/{goal_id}`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /methodology`
- `POST /dispatch`
- `GET /dispatch/receipts`
- `GET /dispatch/receipts/{receipt_id}`

### Dispatch payload

```json
{
  "goal_id": "goal_xxx",
  "tasks": [
    {
      "task_id": "g2",
      "target": "ccb",
      "prompt": "请按 PM_PROTOCOL 汇报当前进度",
      "context": "task=G2"
    },
    {
      "task_id": "q1",
      "target": "5005",
      "prompt": "2+2=?",
      "context": "reply short"
    }
  ]
}
```

## Env (optional)

- `GOAL_ORCH_PORT=9110`
- `GOAL_ORCH_AIAGENT_BASE_URL=http://127.0.0.1:9100`
- `GOAL_ORCH_DISPATCH_5005_URL=http://127.0.0.1:5005/ask`
- `GOAL_ORCH_DISPATCH_5005_TOKEN=<your-token>`
