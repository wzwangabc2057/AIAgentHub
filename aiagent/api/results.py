"""Results API - Claude callback to store results + external query"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from loguru import logger

from aiagent.database import get_db
from aiagent.models.result import ResultCreate

router = APIRouter(prefix="/api/results", tags=["results"])


@router.post("")
async def store_result(req: ResultCreate):
    """
    Store execution result (called by Claude via curl).

    This is the primary callback endpoint for Claude to write its output.
    """
    db = get_db()

    # Get chain_id from execution if available
    chain_id = None
    execution = db.executions.find_one({"_id": req.execution_id})
    if execution:
        chain_id = execution.get("chain_id")

    result_id = f"result_{uuid.uuid4().hex[:12]}"
    result = {
        "_id": result_id,
        "execution_id": req.execution_id,
        "agent_id": req.agent_id,
        "chain_id": chain_id,
        "step": req.step,
        "data": req.data,
        "created_at": datetime.now(timezone.utc),
    }

    # Upsert: replace if result for this execution already exists
    db.results.update_one(
        {"execution_id": req.execution_id},
        {"$set": result},
        upsert=True
    )

    logger.info(f"Result stored for execution {req.execution_id} by {req.agent_id}")
    return {"success": True, "result_id": result_id}


@router.get("")
async def list_results(agent_id: str = None, chain_id: str = None, limit: int = 20):
    """Query results with optional filters"""
    db = get_db()
    query = {}
    if agent_id:
        query["agent_id"] = agent_id
    if chain_id:
        query["chain_id"] = chain_id
    return list(db.results.find(query).sort("created_at", -1).limit(limit))


@router.get("/execution/{execution_id}")
async def get_result_by_execution(execution_id: str):
    """Get result for a specific execution"""
    db = get_db()
    result = db.results.find_one({"execution_id": execution_id})
    if not result:
        raise HTTPException(status_code=404, detail=f"No result for execution {execution_id}")
    return result


@router.get("/chain/{chain_id}")
async def get_chain_results(chain_id: str):
    """Get all results for a chain, ordered by step"""
    db = get_db()
    results = list(db.results.find({"chain_id": chain_id}).sort("step", 1))
    return results
