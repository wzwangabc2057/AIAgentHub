from __future__ import annotations

from datetime import datetime, timezone
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .client import AIAgentClient
from .config import settings
from .planner import build_steps
from .store import GoalStore


app = FastAPI(title="Goal Orchestrator", version="0.1.0")
store = GoalStore(settings.data_file)
client = AIAgentClient(settings.aiagent_base_url)


class GoalCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    owner: str = "default"
    priority: str = "normal"


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "time": datetime.now(timezone.utc).isoformat(),
        "aiagent_base_url": settings.aiagent_base_url,
    }


@app.post("/goals")
def create_goal(req: GoalCreate) -> dict:
    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    steps = build_steps(req.goal)
    chain_name = f"{settings.default_chain_name_prefix}:{goal_id}"

    try:
        chain = client.create_chain(chain_name, steps)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"create_chain_failed: {e}")

    payload = {
        "goal_id": goal_id,
        "goal": req.goal,
        "owner": req.owner,
        "priority": req.priority,
        "status": "submitted",
        "chain_id": chain.get("chain_id"),
        "chain_status": chain.get("status"),
        "steps": len(steps),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    store.put_goal(goal_id, payload)
    return payload


@app.get("/goals")
def list_goals(limit: int = 20) -> dict:
    return {"items": store.list_goals(limit=limit)}


@app.get("/goals/{goal_id}")
def get_goal(goal_id: str) -> dict:
    goal = store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal_not_found")

    chain_id = goal.get("chain_id")
    if chain_id:
        try:
            chain = client.get_chain(chain_id)
            goal["chain_status"] = chain.get("status")
            goal["current_step"] = chain.get("current_step")
            goal["chain"] = {
                "status": chain.get("status"),
                "steps": chain.get("steps", []),
            }
            if chain.get("status") in {"completed", "failed", "cancelled"}:
                goal["status"] = chain.get("status")
            store.put_goal(goal_id, goal)
        except Exception as e:
            goal["chain_error"] = str(e)

    return goal
