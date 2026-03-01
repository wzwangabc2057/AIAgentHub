from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
import json
import uuid
import urllib.request
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .client import AIAgentClient
from .config import settings
from .planner import build_replan_steps, build_steps
from .policy import choose_method, evaluate_outcome
from .scheduler import AutoScheduler
from .store import GoalStore

store = GoalStore(settings.data_file)
client = AIAgentClient(settings.aiagent_base_url)


class GoalCreate(BaseModel):
    goal: str = Field(min_length=3, max_length=2000)
    owner: str = "default"
    priority: str = "normal"
    auto_enabled: bool = True
    run_now: bool = True


class DispatchTask(BaseModel):
    task_id: str
    target: Literal["ccb", "5005", "aiagent"]
    prompt: str
    context: str = ""


class DispatchRequest(BaseModel):
    goal_id: str | None = None
    tasks: list[DispatchTask]


def _to_iso(dt: datetime | None = None) -> str:
    value = dt or datetime.now(timezone.utc)
    return value.isoformat()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_night(now: datetime | None = None) -> bool:
    value = now or _utc_now()
    hour = value.hour
    start = settings.night_start_hour
    end = settings.night_end_hour
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def _auto_interval_seconds(now: datetime | None = None) -> int:
    return settings.night_poll_seconds if _is_night(now) else settings.day_poll_seconds


def _run_status_from_chain_status(status: str) -> str:
    mapping = {
        "pending": "queued",
        "running": "running",
        "completed": "completed",
        "failed": "failed",
        "cancelled": "cancelled",
    }
    return mapping.get(status or "", "unknown")


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
        return json.loads(resp.read().decode("utf-8"))


def _dispatch_ccb(task: DispatchTask) -> dict[str, Any]:
    return {
        "queued": True,
        "hint": f"/ask codex {task.prompt}",
        "target": "ccb",
    }


def _create_chain_run(goal: dict[str, Any], steps: list[dict[str, Any]], method: str, replan_of: str | None = None) -> dict[str, Any]:
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    chain_name = f"{settings.default_chain_name_prefix}:{goal['goal_id']}:{run_id}"
    chain = client.create_chain(chain_name, steps)

    now = _utc_now()
    run = {
        "run_id": run_id,
        "goal_id": goal["goal_id"],
        "goal": goal["goal"],
        "owner": goal.get("owner", "default"),
        "priority": goal.get("priority", "normal"),
        "status": "queued",
        "chain_id": chain.get("chain_id"),
        "chain_status": chain.get("status"),
        "method": method,
        "replan_of": replan_of,
        "replan_count": int(goal.get("replan_count", 0)),
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
        "started_at": _to_iso(now),
        "deadline_at": _to_iso(now + timedelta(seconds=settings.run_stall_seconds)),
        "created_at": _to_iso(now),
        "updated_at": _to_iso(now),
    }
    store.put_run(run_id, run)
    return run


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
        run["reflection"] = _reflect_and_learn(run)
        run["reflected"] = True

    run["updated_at"] = _to_iso()
    return run


def _reflect_and_learn(run: dict[str, Any]) -> dict[str, Any]:
    steps = run.get("task_steps") or []
    updates = []
    for s in steps:
        agent_id = s.get("agent_id") or "unknown"
        st = s.get("status")
        if st == "completed":
            delta = 0.02
        elif st in {"failed", "timeout", "cancelled"}:
            delta = -0.03
        else:
            delta = 0.0
        if delta != 0.0:
            reason = f"run={run.get('run_id')}:step_{s.get('step')}_{st}"
            store.update_agent_weight(agent_id, delta, reason)
            updates.append({"agent_id": agent_id, "delta": delta, "reason": reason})

    ok, bad, score = evaluate_outcome(run)
    method = run.get("method", "baseline")
    win = score > 0
    store.update_method_variant(method, score, win)
    store.add_experiment(
        {
            "at": _to_iso(),
            "run_id": run.get("run_id"),
            "goal_id": run.get("goal_id"),
            "method": method,
            "ok_steps": ok,
            "bad_steps": bad,
            "score": score,
            "win": win,
        }
    )

    return {
        "at": _to_iso(),
        "summary": f"method={method} ok={ok} bad={bad} score={score:.3f}",
        "updates": updates,
    }


def _trigger_goal_run(goal: dict[str, Any], replan_of: str | None = None, replan_steps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    methodology = store.get_methodology()
    method = choose_method(methodology, settings.ab_epsilon)
    steps = replan_steps if replan_steps is not None else build_steps(goal["goal"], method)
    run = _create_chain_run(goal, steps, method=method, replan_of=replan_of)

    goal["status"] = "running"
    goal["current_run_id"] = run["run_id"]
    goal["last_run_at"] = _to_iso()
    goal["total_runs"] = int(goal.get("total_runs", 0)) + 1
    goal["next_run_at"] = _to_iso(_utc_now() + timedelta(seconds=_auto_interval_seconds()))
    store.put_goal(goal["goal_id"], goal)
    return run


async def _scheduler_tick() -> None:
    active_runs = store.list_active_runs()
    for run in active_runs:
        run_id = run["run_id"]
        goal_id = run["goal_id"]
        try:
            run = _sync_run_from_chain(run)
            store.put_run(run_id, run)
        except Exception as e:
            run["chain_error"] = str(e)
            run["updated_at"] = _to_iso()
            store.put_run(run_id, run)
            continue

        goal = store.get_goal(goal_id)
        if goal:
            goal["status"] = run.get("status", goal.get("status"))
            goal["chain_status"] = run.get("chain_status")
            goal["current_step"] = run.get("current_step")
            if run.get("status") in {"completed", "failed", "cancelled", "stalled"}:
                goal["last_terminal_run_id"] = run_id
                if goal.get("auto_enabled"):
                    goal["status"] = "idle"
            store.put_goal(goal_id, goal)

        if run.get("status") not in {"queued", "running", "unknown"}:
            continue

        deadline = run.get("deadline_at")
        if not deadline:
            continue
        try:
            is_stalled = _utc_now() > datetime.fromisoformat(deadline)
        except Exception:
            is_stalled = False
        if not is_stalled:
            continue

        goal = store.get_goal(goal_id)
        if not goal:
            continue
        retries = int(goal.get("replan_count", 0))
        if retries >= settings.max_replans:
            run["status"] = "stalled"
            run["updated_at"] = _to_iso()
            store.put_run(run_id, run)
            continue

        replan_method = run.get("method", "baseline")
        replan_steps = build_replan_steps(goal["goal"], replan_method, run)
        goal["replan_count"] = retries + 1
        store.put_goal(goal_id, goal)

        new_run = _trigger_goal_run(goal, replan_of=run_id, replan_steps=replan_steps)
        run["status"] = "stalled"
        run["superseded_by"] = new_run["run_id"]
        run["updated_at"] = _to_iso()
        store.put_run(run_id, run)

    for goal in store.list_goals(limit=1000):
        if not goal.get("auto_enabled"):
            continue
        current_run_id = goal.get("current_run_id")
        if current_run_id:
            current_run = store.get_run(current_run_id)
            if current_run and current_run.get("status") in {"queued", "running", "unknown"}:
                continue

        next_run_at = goal.get("next_run_at")
        due = False
        if not next_run_at:
            due = True
        else:
            try:
                due = _utc_now() >= datetime.fromisoformat(next_run_at)
            except Exception:
                due = True

        if due:
            _trigger_goal_run(goal)


scheduler = AutoScheduler(_scheduler_tick)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="Goal Orchestrator V2", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "time": _to_iso(),
        "aiagent_base_url": settings.aiagent_base_url,
        "auto_mode": {
            "day_poll_seconds": settings.day_poll_seconds,
            "night_poll_seconds": settings.night_poll_seconds,
            "run_stall_seconds": settings.run_stall_seconds,
            "max_replans": settings.max_replans,
        },
    }


@app.post("/goals")
def create_goal(req: GoalCreate) -> dict[str, Any]:
    goal_id = f"goal_{uuid.uuid4().hex[:12]}"
    now = _utc_now()
    goal = {
        "goal_id": goal_id,
        "goal": req.goal,
        "owner": req.owner,
        "priority": req.priority,
        "auto_enabled": req.auto_enabled,
        "status": "submitted",
        "replan_count": 0,
        "total_runs": 0,
        "next_run_at": _to_iso(now),
        "created_at": _to_iso(now),
        "updated_at": _to_iso(now),
    }
    store.put_goal(goal_id, goal)

    if req.run_now:
        try:
            run = _trigger_goal_run(goal)
            goal["run_id"] = run["run_id"]
            goal["chain_id"] = run["chain_id"]
            goal["chain_status"] = run["chain_status"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"create_chain_failed: {e}")

    return goal


@app.get("/goals")
def list_goals(limit: int = 50) -> dict[str, Any]:
    return {"items": store.list_goals(limit=limit)}


@app.get("/goals/{goal_id}")
def get_goal(goal_id: str) -> dict[str, Any]:
    goal = store.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="goal_not_found")

    current_run_id = goal.get("current_run_id")
    if current_run_id:
        run = store.get_run(current_run_id)
        if run:
            try:
                run = _sync_run_from_chain(run)
                store.put_run(current_run_id, run)
                goal["status"] = run.get("status", goal.get("status"))
                goal["chain_status"] = run.get("chain_status")
                goal["current_step"] = run.get("current_step")
                store.put_goal(goal_id, goal)
            except Exception as e:
                goal["chain_error"] = str(e)
    return goal


@app.get("/runs")
def list_runs(limit: int = 100) -> dict[str, Any]:
    return {"items": store.list_runs(limit=limit)}


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
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
def methodology() -> dict[str, Any]:
    return store.get_methodology()


@app.get("/experiments")
def experiments(limit: int = 50) -> dict[str, Any]:
    return {"items": store.list_experiments(limit=limit)}


@app.post("/dispatch")
def dispatch(req: DispatchRequest) -> dict[str, Any]:
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
                base["status"] = "queued"
                base["output"] = _dispatch_ccb(t)
            else:
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
def list_receipts(limit: int = 100) -> dict[str, Any]:
    return {"items": store.list_receipts(limit=limit)}


@app.get("/dispatch/receipts/{receipt_id}")
def get_receipt(receipt_id: str) -> dict[str, Any]:
    item = store.get_receipt(receipt_id)
    if not item:
        raise HTTPException(status_code=404, detail="receipt_not_found")
    return item


@app.post("/scheduler/tick")
async def scheduler_tick() -> dict[str, Any]:
    await _scheduler_tick()
    return {"ok": True, "time": _to_iso()}
