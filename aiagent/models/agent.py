"""Agent model definitions"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent execution configuration"""
    timeout: int = Field(default=300, description="Default timeout in seconds")
    execution_mode: Literal["print", "tmux"] = Field(default="print", description="Execution mode")


class Agent(BaseModel):
    """Agent definition"""
    id: str = Field(alias="_id", description="Agent ID")
    name: str = Field(description="Agent name")
    description: str = Field(default="", description="Agent description")
    status: Literal["active", "inactive"] = Field(default="active")
    node_id: Optional[str] = Field(default=None, description="Node this agent belongs to")
    config: AgentConfig = Field(default_factory=AgentConfig)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class AgentCreate(BaseModel):
    """Create agent request"""
    id: str = Field(description="Agent ID (e.g. researcher_001)")
    name: str = Field(description="Agent name")
    description: str = Field(default="")
    node_id: Optional[str] = Field(default=None)
    config: Optional[AgentConfig] = None


class AgentUpdate(BaseModel):
    """Update agent request"""
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None
    node_id: Optional[str] = None
    config: Optional[AgentConfig] = None
