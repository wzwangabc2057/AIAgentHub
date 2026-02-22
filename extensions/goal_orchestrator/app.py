from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid
import urllib.request
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .client import AIAgentClient
from .config import settings
from .planner import build_steps
from .store import GoalStore


app = FastAPI(title="Goal Orchestrator", version="0.2.0")
store = GoalStore(settings.data_file)
client = AIAgentClient(settings.aiagent_base_url)


class GoalCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    owner: str = "default"
    priority: str = "normal"


class DispatchTask(BaseModel):
    task_id: str
    target: Literal["ccb", "5005", "aiagent"]
    prompt: str
    context: str = ""


class DispatchRequest(BaseModel):
    goal_id: str | None = None
    tasks: list[DispatchTask]


def _to_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_status_from_chain_status(status: str) -> str:
    mapping = {
        "pending": "queued",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
    }
    return mapping.get(status or "", "unknown")


def _sync_run_from_chain(run: dict[str, Any]) -> dict[str, Any]:
    chain_id = run.get("chain_id")
    if not chain_id:
        return run

    chain = client.get_chain(chain_id)
    steps = chain.get("steps", [])

    run["chain_status"] = chain.get("status")
    run["status"] = _run_status_from_chain_status(chain.get("status", ""))
    run["current_step"] = chain.get("current_step")

    task_steps: list[dict[str, Any]] = []
    for s in steps:
        task_steps.append(
            {
                "step": s.get("step"),
                "agent_id": s.get("agent_id"),
                "status": s.get("status"),
                "execution_id": s.get("execution_id"),
                "depends_on": s.get("depends_on", []),
                "output_preview": s.get("output_preview", ""),
            }
        )
    run["task_steps"] = task_steps

    terminal = run["status"] in {"completed", "failed", "cancelled"}
    if terminal and not run.get("reflected"):
        reflection = _reflect_and_update_methodology(run)
        run["reflection"] = reflection
        run["reflected"] = True

    run["updated_at"] = _to_iso()
    return run


def _reflect_and_update_methodology(run: dict[str, Any]) -> dict[str, Any]:
    """Very simple auto-reflection and methodology weight update."""
    steps = run.get("task_steps") or []
    updates = []
    success = 0
    failed = 0

    for s in steps:
        agent_id = s.get("agent_id") or "unknown"
        st = s.get("status")
        if st == "completed":
            success += 1
            delta = 0.02
            reason = f"step_{s.get('step')}_completed"
        elif st in {"failed", "timeout", "cancelled"}:
            failed += 1
            delta = -0.03
            reason = f"step_{s.get('step')}_{st}"
        else:
            delta = 0.0
            reason = f"step_{s.get('step')}_{st or 'unknown'}"

        if delta != 0.0:
            store.update_methodology_weight(agent_id, delta, reason)
            updates.append({"agent_id": agent_id, "delta": delta, "reason": reason})

    summary = (
        f"run={run.get('run_id')} status={run.get('status')} success_steps={success} failed_steps={failed}. "
        "Methodology weights updated by step outcome."
    )

    return {
        "at": _to_iso(),
        "summary": summary,
        "updates": updates,
    }


def _dispatch_5005(task: DispatchTask) -> dict[str, Any]:
    payload = {
        "token": settings.dispatch_5005_token,
        "question": task.prompt,
        "context": task.context,
        "system_prompt": "请返回结构化结论：结论/证据/风险/建议。",
    }
    req = urllib.request.Request(
        settings.dispatch_5005_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data


def _dispatch_ccb(task: DispatchTask) -> dict[str, Any]:
    # This extension does not directly drive tmux panes yet; produce standard receipt hint.
    return {
        "queued": True,
        "hint": f"/ask codex {task.prompt}",
        "target": "ccb",
    }


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "time": _to_iso(),
        "aiagent_base_url": settings.aiagent_base_url,
    }


@app.post("/goals")
def create_goal(req: GoalCreate) -> dict:
    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    steps = build_steps(req.goal)
    chain_name = f"{settings.default_chain_name_prefix}:{goal_id}"

    try:
        chain = client.create_chain(chain_name, steps)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"create_chain_failed: {e}")

    goal = {
        "goal_id": goal_id,
        "goal": req.goal,
        "owner": req.owner,
        "priority": req.priority,
        "status": "submitted",
        "run_id": run_id,
        "chain_id": chain.get("chain_id"),
        "chain_status": chain.get("status"),
        "steps": len(steps),
        "created_at": _to_iso(),
        "updated_at": _to_iso(),
    }
    run = {
        "run_id": run_id,
        "goal_id": goal_id,
        "goal": req.goal,
        "status": "queued",
        "chain_id": chain.get("chain_id"),
        "chain_status": chain.get("status"),
        "task_steps": [
            {
                "step": s["step"],
                "agent_id": s["agent_id"],
                "status": "pending",
                "execution_id": None,
                "depends_on": s.get("depends_on", []),
                "output_preview": "",
            }
            for s in steps
        ],
        "reflected": False,
        "created_at": _to_iso(),
        "updated_at": _to_iso(),
    }

    store.put_goal(goal_id, goal)
    store.put_run(run_id, run)
    return goal


@app.get("/goals")
def list_goals(limit: int = 20) -> dict:
    return {"items": store.list_goals(limit=limit)}


@app.get("/goals/{goal_id}")
def get_goal(goal_id: str) -> dict:
    goal = store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal_not_found")

    run_id = goal.get("run_id")
    if run_id:
        run = store.get_run(run_id)
        if run:
            try:
                run = _sync_run_from_chain(run)
                store.put_run(run_id, run)
                goal["status"] = run.get("status", goal.get("status"))
                goal["chain_status"] = run.get("chain_status", goal.get("chain_status"))
                goal["current_step"] = run.get("current_step")
                goal["run"] = run
                store.put_goal(goal_id, goal)
            except Exception as e:
                goal["chain_error"] = str(e)

    return goal


@app.get("/runs")
def list_runs(limit: int = 20) -> dict:
    return {"items": store.list_runs(limit=limit)}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")

    try:
        run = _sync_run_from_chain(run)
        store.put_run(run_id, run)
    except Exception as e:
        run["chain_error"] = str(e)

    return run


@app.get("/methodology")
def methodology() -> dict:
    return store.get_methodology()


@app.post("/dispatch")
def dispatch(req: DispatchRequest) -> dict:
    receipts = []

    for t in req.tasks:
        rid = f"receipt_{uuid.uuid4().hex[:12]}"
        base = {
            "receipt_id": rid,
            "task_id": t.task_id,
            "goal_id": req.goal_id,
            "target": t.target,
            "created_at": _to_iso(),
            "status": "queued",
            "output": None,
            "error": None,
            "evidence": [],
        }

        try:
            if t.target == "5005":
                out = _dispatch_5005(t)
                base["status"] = "done" if out.get("code") == 0 else "failed"
                base["output"] = out
            elif t.target == "ccb":
                out = _dispatch_ccb(t)
                base["status"] = "queued"
                base["output"] = out
            else:
                # reserved for direct aiagent execute/chain dispatch in protocol form
                base["status"] = "queued"
                base["output"] = {"hint": "use /goals or /api/chains for aiagent dispatch"}
        except Exception as e:
            base["status"] = "failed"
            base["error"] = str(e)

        base["finished_at"] = _to_iso()
        store.put_receipt(rid, base)
        receipts.append(base)

    return {"count": len(receipts), "receipts": receipts}


@app.get("/dispatch/receipts")
def list_receipts(limit: int = 50) -> dict:
    return {"items": store.list_receipts(limit=limit)}


@app.get("/dispatch/receipts/{receipt_id}")
def get_receipt(receipt_id: str) -> dict:
    item = store.get_receipt(receipt_id)
    if not item:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    return item
