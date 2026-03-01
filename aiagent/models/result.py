"""Result model definitions"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class Result(BaseModel):
    """Execution result - stored by Claude via API callback"""
    id: str = Field(alias="_id", description="Result ID")
    execution_id: str = Field(description="Execution ID")
    agent_id: str = Field(description="Agent ID")
    chain_id: Optional[str] = Field(default=None, description="Chain ID")
    step: Optional[int] = Field(default=None, description="Step number in chain")
    data: str = Field(description="Result content (text)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class ResultCreate(BaseModel):
    """Claude callback to store result"""
    execution_id: str = Field(description="Execution ID")
    agent_id: str = Field(description="Agent ID")
    step: Optional[int] = Field(default=None, description="Step number")
    data: str = Field(description="Result data (text)")
