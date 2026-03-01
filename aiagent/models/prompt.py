"""Prompt model definitions"""

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


class Prompt(BaseModel):
    """Prompt template with versioning"""
    id: str = Field(alias="_id", description="Prompt ID")
    agent_id: str = Field(description="Agent ID this prompt belongs to")
    name: str = Field(description="Prompt name")
    content: str = Field(description="Prompt content template")
    variables: List[str] = Field(default_factory=list, description="Variable names used in template")
    version: int = Field(default=1, description="Current version")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"populate_by_name": True}


class PromptCreate(BaseModel):
    """Create prompt request"""
    id: str = Field(description="Prompt ID")
    agent_id: str = Field(description="Agent ID")
    name: str = Field(description="Prompt name")
    content: str = Field(description="Prompt content")
    variables: List[str] = Field(default_factory=list)


class PromptUpdate(BaseModel):
    """Update prompt request (creates new version)"""
    content: str = Field(description="New prompt content")
    updated_by: str = Field(default="user")


class PromptHistory(BaseModel):
    """Prompt version history entry"""
    prompt_id: str
    version: int
    content: str
    updated_by: str
    updated_at: datetime
