"""Execution trigger + query + Claude completion callback API"""

import asyncio
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.models.execution import ExecuteRequest, ExecutionDoneRequest
from aiagent.engine.executor_pool import get_executor_pool
from aiagent.engine.prompt_renderer import render_prompt

router = APIRouter(prefix="/api", tags=["executions"])


@router.post("/execute/{agent_id}")
async def execute_agent(agent_id: str, req: ExecuteRequest, background_tasks: BackgroundTasks):
    """Trigger execution of an agent with a prompt"""
    db = get_db()

    # Verify agent exists
    agent = db.agents.find_one({"_id": agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Get prompt content
    prompt_content = ""
    if req.inline_prompt:
        prompt_content = req.inline_prompt
    elif req.prompt_id:
        prompt = db.prompts.find_one({"_id": req.prompt_id})
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {req.prompt_id} not found")
        prompt_content = prompt["content"]
    else:
        raise HTTPException(status_code=400, detail="Either prompt_id or inline_prompt is required")

    # Generate execution ID
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"

    # Render prompt
    rendered = render_prompt(
        template=prompt_content,
        variables=req.variables,
        execution_id=execution_id,
        agent_id=agent_id,
    )

    # Create execution record
    now = datetime.now(timezone.utc)
    execution = {
        "_id": execution_id,
        "agent_id": agent_id,
        "prompt_id": req.prompt_id,
        "prompt_content": rendered,
        "status": "pending",
        "timeout": req.timeout,
        "node_id": settings.get_node_id(),
        "created_at": now,
    }
    db.executions.insert_one(execution)

    # Execute in background
    pool = get_executor_pool()
    background_tasks.add_task(pool.execute, execution_id, agent_id, rendered, req.timeout)

    logger.info(f"Execution {execution_id} queued for {agent_id}")
    return {"execution_id": execution_id, "status": "pending"}


@router.get("/executions")
async def list_executions(agent_id: str = None, status: str = None, limit: int = 20):
    """List executions with optional filters"""
    db = get_db()
    query = {}
    if agent_id:
        query["agent_id"] = agent_id
    if status:
        query["status"] = status
    return list(db.executions.find(query).sort("created_at", -1).limit(limit))


@router.get("/executions/running")
async def list_running_executions(agent_id: str = None):
    """List currently running executions"""
    db = get_db()
    query = {"status": {"$in": ["pending", "running"]}}
    if agent_id:
        query["agent_id"] = agent_id
    return list(db.executions.find(query).sort("created_at", -1))


@router.get("/executions/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution details"""
    db = get_db()
    execution = db.executions.find_one({"_id": execution_id})
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    # Also fetch result if available
    result = db.results.find_one({"execution_id": execution_id})
    execution["result"] = result
    return execution


@router.post("/executions/{execution_id}/done")
async def execution_done(execution_id: str, req: ExecutionDoneRequest = None):
    """Claude callback to report execution completion"""
    db = get_db()

    execution = db.executions.find_one({"_id": execution_id})
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")

    now = datetime.now(timezone.utc)
    status = "completed"
    error = None
    if req:
        status = req.status
        error = req.error

    db.executions.update_one(
        {"_id": execution_id},
        {"$set": {
            "status": status,
            "completed_at": now,
            "error": error,
        }}
    )

    logger.info(f"Execution {execution_id} marked as {status}")
    return {"success": True, "execution_id": execution_id, "status": status}
