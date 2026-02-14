"""Execution model definitions"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class Execution(BaseModel):
    """Execution record"""
    id: str = Field(alias="_id", description="Execution ID")
    agent_id: str = Field(description="Agent ID")
    chain_id: Optional[str] = Field(default=None, description="Chain ID if part of a chain")
    step: Optional[int] = Field(default=None, description="Step number in chain")
    prompt_id: Optional[str] = Field(default=None, description="Prompt template ID")
    prompt_content: Optional[str] = Field(default=None, description="Rendered prompt")
    status: Literal["pending", "running", "completed", "failed", "timeout"] = Field(default="pending")
    node_id: Optional[str] = Field(default=None, description="Node executing this task")
    timeout: int = Field(default=300)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = {"populate_by_name": True}


class ExecuteRequest(BaseModel):
    """Request to execute an agent"""
    prompt_id: Optional[str] = Field(default=None, description="Prompt template ID")
    inline_prompt: Optional[str] = Field(default=None, description="Inline prompt text")
    variables: Dict[str, str] = Field(default_factory=dict, description="Template variables")
    timeout: int = Field(default=300)


class ExecutionDoneRequest(BaseModel):
    """Claude callback to report completion"""
    status: Literal["completed", "failed"] = Field(default="completed")
    error: Optional[str] = None
