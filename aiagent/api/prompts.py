"""Prompt CRUD + versioning API"""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from loguru import logger

from aiagent.database import get_db
from aiagent.models.prompt import PromptCreate, PromptUpdate

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("")
async def list_prompts(agent_id: str = None):
    """List prompts, optionally filtered by agent_id"""
    db = get_db()
    query = {"agent_id": agent_id} if agent_id else {}
    return list(db.prompts.find(query).sort("_id", 1))


@router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get a prompt by ID"""
    db = get_db()
    prompt = db.prompts.find_one({"_id": prompt_id})
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
    return prompt


@router.post("")
async def create_prompt(req: PromptCreate):
    """Create a new prompt"""
    db = get_db()

    if db.prompts.find_one({"_id": req.id}):
        raise HTTPException(status_code=409, detail=f"Prompt {req.id} already exists")

    now = datetime.now(timezone.utc)
    prompt = {
        "_id": req.id,
        "agent_id": req.agent_id,
        "name": req.name,
        "content": req.content,
        "variables": req.variables,
        "version": 1,
        "created_at": now,
        "updated_at": now,
    }
    db.prompts.insert_one(prompt)
    logger.info(f"Prompt created: {req.id}")
    return prompt


@router.put("/{prompt_id}")
async def update_prompt(prompt_id: str, req: PromptUpdate):
    """Update prompt content (creates a new version)"""
    db = get_db()

    current = db.prompts.find_one({"_id": prompt_id})
    if not current:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")

    # Save current version to history
    db.prompt_history.insert_one({
        "prompt_id": prompt_id,
        "version": current["version"],
        "content": current["content"],
        "updated_by": req.updated_by,
        "updated_at": current["updated_at"],
    })

    # Update with new version
    new_version = current["version"] + 1
    now = datetime.now(timezone.utc)
    db.prompts.update_one(
        {"_id": prompt_id},
        {"$set": {
            "content": req.content,
            "version": new_version,
            "updated_at": now,
        }}
    )

    logger.info(f"Prompt {prompt_id} updated to v{new_version}")
    return db.prompts.find_one({"_id": prompt_id})


@router.get("/{prompt_id}/history")
async def get_prompt_history(prompt_id: str):
    """Get version history for a prompt"""
    db = get_db()
    history = list(db.prompt_history.find({"prompt_id": prompt_id}).sort("version", -1))
    return history


@router.delete("/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt"""
    db = get_db()
    result = db.prompts.delete_one({"_id": prompt_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
    return {"success": True, "message": f"Prompt {prompt_id} deleted"}
