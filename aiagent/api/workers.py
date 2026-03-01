"""Workers API - node registration, heartbeat, and status (distributed)"""

import socket
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db

router = APIRouter(prefix="/api/workers", tags=["workers"])


@router.get("")
async def list_workers():
    """List all registered worker nodes"""
    db = get_db()
    workers = list(db.workers.find().sort("_id", 1))

    # Mark stale workers as offline
    now = datetime.now(timezone.utc)
    timeout_delta = timedelta(seconds=settings.heartbeat_timeout)
    for w in workers:
        hb = w.get("last_heartbeat")
        if hb:
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if now - hb > timeout_delta:
                w["status"] = "offline"
    return workers


@router.post("/register")
async def register_worker(node_id: str = None, capacity: int = None):
    """Register this node as a worker"""
    db = get_db()

    nid = node_id or settings.get_node_id()
    cap = capacity or settings.max_concurrent
    now = datetime.now(timezone.utc)

    # Get agents assigned to this node
    my_agents = [a["_id"] for a in db.agents.find({"node_id": nid})]

    worker = {
        "_id": nid,
        "hostname": socket.gethostname(),
        "ip": _get_local_ip(),
        "capacity": cap,
        "agents": my_agents,
        "status": "online",
        "last_heartbeat": now,
        "started_at": now,
    }

    db.workers.update_one({"_id": nid}, {"$set": worker}, upsert=True)
    logger.info(f"Worker registered: {nid} (capacity={cap}, agents={my_agents})")
    return worker


@router.post("/heartbeat")
async def heartbeat(node_id: str = None):
    """Send heartbeat from a worker node"""
    db = get_db()
    nid = node_id or settings.get_node_id()
    now = datetime.now(timezone.utc)

    # Update agents list
    my_agents = [a["_id"] for a in db.agents.find({"node_id": nid})]

    result = db.workers.update_one(
        {"_id": nid},
        {"$set": {
            "last_heartbeat": now,
            "status": "online",
            "agents": my_agents,
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Worker {nid} not registered")
    return {"success": True, "node_id": nid, "timestamp": now.isoformat()}


@router.get("/status")
async def cluster_status():
    """Get cluster overview"""
    db = get_db()
    now = datetime.now(timezone.utc)
    timeout = timedelta(seconds=settings.heartbeat_timeout)

    workers = list(db.workers.find())
    online = 0
    for w in workers:
        hb = w.get("last_heartbeat")
        if hb:
            if hb.tzinfo is None:
                hb = hb.replace(tzinfo=timezone.utc)
            if now - hb < timeout:
                online += 1
    total_capacity = sum(w.get("capacity", 0) for w in workers)

    running = db.executions.count_documents({"status": {"$in": ["pending", "running"]}})

    return {
        "nodes": {"total": len(workers), "online": online, "offline": len(workers) - online},
        "total_capacity": total_capacity,
        "running_tasks": running,
    }


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
