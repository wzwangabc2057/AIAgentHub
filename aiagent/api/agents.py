"""Agent CRUD API"""

import os
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from loguru import logger

from aiagent.config import settings
from aiagent.database import get_db
from aiagent.models.agent import AgentCreate, AgentUpdate

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("")
async def list_agents():
    """List all agents"""
    db = get_db()
    agents = list(db.agents.find().sort("_id", 1))
    return agents


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent by ID"""
    db = get_db()
    agent = db.agents.find_one({"_id": agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent


@router.post("")
async def create_agent(req: AgentCreate):
    """Create a new agent"""
    db = get_db()

    if db.agents.find_one({"_id": req.id}):
        raise HTTPException(status_code=409, detail=f"Agent {req.id} already exists")

    now = datetime.now(timezone.utc)
    agent = {
        "_id": req.id,
        "name": req.name,
        "description": req.description,
        "status": "active",
        "node_id": req.node_id or settings.get_node_id(),
        "config": req.config.model_dump() if req.config else {"timeout": 300, "execution_mode": "print"},
        "created_at": now,
        "updated_at": now,
    }
    db.agents.insert_one(agent)

    # Create agent working directory
    work_dir = os.path.join(os.path.abspath(settings.agents_dir), req.id)
    os.makedirs(work_dir, exist_ok=True)

    # Create default CLAUDE.md
    claude_md = os.path.join(work_dir, "CLAUDE.md")
    if not os.path.exists(claude_md):
        with open(claude_md, "w") as f:
            f.write(f"# {req.name}\n\n{req.description}\n")

    logger.info(f"Agent created: {req.id}")
    return agent


@router.put("/{agent_id}")
async def update_agent(agent_id: str, req: AgentUpdate):
    """Update an agent"""
    db = get_db()

    if not db.agents.find_one({"_id": agent_id}):
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    update = {"updated_at": datetime.now(timezone.utc)}
    for field in ["name", "description", "status", "node_id"]:
        value = getattr(req, field, None)
        if value is not None:
            update[field] = value
    if req.config is not None:
        update["config"] = req.config.model_dump()

    db.agents.update_one({"_id": agent_id}, {"$set": update})
    return db.agents.find_one({"_id": agent_id})


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str):
    """Delete an agent"""
    db = get_db()
    result = db.agents.delete_one({"_id": agent_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return {"success": True, "message": f"Agent {agent_id} deleted"}
