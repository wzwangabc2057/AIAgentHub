"""System status API"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.engine.executor_pool import get_executor_pool
from aiagent.services.tmux_manager import tmux_manager

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/status")
async def get_system_status():
    """Get comprehensive system status"""
    db = get_db()
    pool = get_executor_pool()

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Agent stats
    total_agents = db.agents.count_documents({})
    active_agents = db.agents.count_documents({"status": "active"})

    # Execution stats
    running = db.executions.count_documents({"status": {"$in": ["pending", "running"]}})
    completed_today = db.executions.count_documents({
        "status": "completed",
        "completed_at": {"$gte": today_start}
    })

    # Chain stats
    running_chains = db.chains.count_documents({"status": "running"})
    completed_chains_today = db.chains.count_documents({
        "status": "completed",
        "completed_at": {"$gte": today_start}
    })

    # Schedule stats
    total_schedules = db.schedules.count_documents({})
    enabled_schedules = db.schedules.count_documents({"enabled": True})

    # tmux sessions
    sessions = tmux_manager.list_sessions()

    # Worker stats
    timeout_delta = timedelta(seconds=settings.heartbeat_timeout)
    workers = list(db.workers.find())
    online_workers = 0
    for w in workers:
        hb = w.get("last_heartbeat")
        if hb:
            # Ensure timezone-aware comparison
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if now - hb < timeout_delta:
                online_workers += 1

    return {
        "node_id": settings.get_node_id(),
        "server": {"port": settings.api_port, "api_base": settings.api_base_url},
        "agents": {"total": total_agents, "active": active_agents},
        "executions": {"running": running, "completed_today": completed_today},
        "chains": {"running": running_chains, "completed_today": completed_chains_today},
        "schedules": {"total": total_schedules, "enabled": enabled_schedules},
        "pool": pool.get_status(),
        "tmux_sessions": len(sessions),
        "workers": {"total": len(workers), "online": online_workers},
    }
