"""Schedules API - cron/interval trigger management"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from loguru import logger

from aiagent.database import get_db

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("")
async def list_schedules():
    """List all schedules"""
    db = get_db()
    return list(db.schedules.find().sort("_id", 1))


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    """Get schedule by ID"""
    db = get_db()
    schedule = db.schedules.find_one({"_id": schedule_id})
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return schedule


@router.post("")
async def create_schedule(data: dict):
    """Create a new schedule"""
    db = get_db()

    schedule_id = data.get("_id") or f"sched_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    schedule = {
        "_id": schedule_id,
        "name": data.get("name", schedule_id),
        "type": data.get("type", "cron"),  # cron | interval | event
        "cron": data.get("cron"),
        "interval_seconds": data.get("interval_seconds"),
        "event": data.get("event"),
        "target": data.get("target", {}),  # {type: "chain"|"execute", ...}
        "enabled": data.get("enabled", True),
        "last_run": None,
        "next_run": None,
        "created_at": now,
    }
    db.schedules.insert_one(schedule)
    logger.info(f"Schedule created: {schedule_id}")
    return schedule


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: str, data: dict):
    """Update a schedule"""
    db = get_db()
    if not db.schedules.find_one({"_id": schedule_id}):
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    allowed_fields = ["name", "type", "cron", "interval_seconds", "event", "target", "enabled"]
    update = {k: v for k, v in data.items() if k in allowed_fields}
    db.schedules.update_one({"_id": schedule_id}, {"$set": update})
    return db.schedules.find_one({"_id": schedule_id})


@router.post("/{schedule_id}/enable")
async def enable_schedule(schedule_id: str):
    """Enable a schedule"""
    db = get_db()
    result = db.schedules.update_one({"_id": schedule_id}, {"$set": {"enabled": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return {"success": True, "schedule_id": schedule_id, "enabled": True}


@router.post("/{schedule_id}/disable")
async def disable_schedule(schedule_id: str):
    """Disable a schedule"""
    db = get_db()
    result = db.schedules.update_one({"_id": schedule_id}, {"$set": {"enabled": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return {"success": True, "schedule_id": schedule_id, "enabled": False}


@router.post("/{schedule_id}/trigger")
async def trigger_schedule(schedule_id: str):
    """Manually trigger a schedule (execute immediately)"""
    from fastapi import BackgroundTasks
    db = get_db()

    schedule = db.schedules.find_one({"_id": schedule_id})
    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    # Import here to avoid circular imports
    from aiagent.engine.scheduler import get_scheduler
    scheduler = get_scheduler()
    await scheduler.trigger_schedule(schedule)

    return {"success": True, "message": f"Schedule {schedule_id} triggered"}


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    """Delete a schedule"""
    db = get_db()
    result = db.schedules.delete_one({"_id": schedule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")
    return {"success": True, "message": f"Schedule {schedule_id} deleted"}
