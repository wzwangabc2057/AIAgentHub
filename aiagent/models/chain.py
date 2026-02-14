"""Chain model definitions"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Literal
from pydantic import BaseModel, Field


class ChainStep(BaseModel):
    """A single step in a chain"""
    step: Optional[int] = Field(default=None, description="Step number (1-based, auto-assigned if omitted)")
    agent_id: str = Field(description="Agent to execute this step")
    prompt_id: Optional[str] = Field(default=None, description="Prompt template ID")
    inline_prompt: Optional[str] = Field(default=None, description="Inline prompt")
    variables: Dict[str, str] = Field(default_factory=dict, description="Variables (supports {step_N_output})")
    depends_on: List[int] = Field(default_factory=list, description="Step numbers this depends on")
    timeout: int = Field(default=300)
    # Filled during execution
    execution_id: Optional[str] = None
    status: Literal["pending", "running", "completed", "failed", "timeout", "cancelled"] = "pending"


class Chain(BaseModel):
    """Chain definition - multi-agent pipeline"""
    id: str = Field(alias="_id", description="Chain ID")
    name: str = Field(description="Chain name")
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = Field(default="pending")
    current_step: Optional[int] = Field(default=None, description="Current executing step")
    steps: List[ChainStep] = Field(description="Ordered steps")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = {"populate_by_name": True}


class ChainCreate(BaseModel):
    """Create chain request"""
    name: str = Field(description="Chain name")
    steps: List[ChainStep] = Field(description="Chain steps")
