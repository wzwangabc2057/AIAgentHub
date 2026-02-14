"""Chain API - multi-agent pipeline management"""

import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger

from aiagent.database import get_db
from aiagent.models.chain import ChainCreate
from aiagent.engine.chain_executor import get_chain_executor

router = APIRouter(prefix="/api/chains", tags=["chains"])


@router.post("")
async def create_chain(req: ChainCreate, background_tasks: BackgroundTasks):
    """Create and start a chain execution"""
    db = get_db()

    chain_id = f"chain_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # Auto-number steps if not set, and set defaults
    steps = []
    for i, step in enumerate(req.steps):
        step_data = step.model_dump()
        if not step_data.get("step"):
            step_data["step"] = i + 1
        step_data["status"] = "pending"
        step_data["execution_id"] = None

        # Default depends_on: sequential if not specified
        if not step_data.get("depends_on") and step_data["step"] > 1:
            # Check if any step in the chain has explicit depends_on
            has_explicit_deps = any(s.depends_on for s in req.steps)
            if not has_explicit_deps:
                step_data["depends_on"] = [step_data["step"] - 1]

        steps.append(step_data)

    chain = {
        "_id": chain_id,
        "name": req.name,
        "status": "pending",
        "current_step": None,
        "steps": steps,
        "created_at": now,
    }
    db.chains.insert_one(chain)

    # Start chain execution in background
    executor = get_chain_executor()
    background_tasks.add_task(executor.start_chain, chain_id)

    logger.info(f"Chain {chain_id} created: {req.name} ({len(steps)} steps)")
    return {"chain_id": chain_id, "status": "pending", "steps": len(steps)}


@router.get("")
async def list_chains(status: str = None, limit: int = 20):
    """List chains with optional status filter"""
    db = get_db()
    query = {"status": status} if status else {}
    return list(db.chains.find(query).sort("created_at", -1).limit(limit))


@router.get("/{chain_id}")
async def get_chain(chain_id: str):
    """Get chain details with step statuses"""
    db = get_db()
    chain = db.chains.find_one({"_id": chain_id})
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")

    # Enrich with result data for completed steps
    for step in chain["steps"]:
        if step.get("execution_id"):
            result = db.results.find_one({"execution_id": step["execution_id"]})
            if result:
                # Include truncated output preview
                data = result.get("data", "")
                step["output_preview"] = data[:200] + "..." if len(data) > 200 else data

    return chain


@router.post("/{chain_id}/cancel")
async def cancel_chain(chain_id: str):
    """Cancel a running chain"""
    db = get_db()
    chain = db.chains.find_one({"_id": chain_id})
    if not chain:
        raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")

    if chain["status"] not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Chain is already {chain['status']}")

    db.chains.update_one(
        {"_id": chain_id},
        {"$set": {
            "status": "cancelled",
            "completed_at": datetime.now(timezone.utc),
        }}
    )

    # Cancel pending steps
    for step in chain["steps"]:
        if step["status"] in ("pending", "running"):
            db.chains.update_one(
                {"_id": chain_id, "steps.step": step["step"]},
                {"$set": {"steps.$.status": "cancelled"}}
            )

    return {"success": True, "chain_id": chain_id, "status": "cancelled"}
