from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class FeedbackCategory(str, Enum):
    TIP = "tip"
    DIFFICULTY = "difficulty"
    APPROACH = "approach"
    GOTCHA = "gotcha"
    TOOL_USAGE = "tool_usage"


class FeedbackEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    agent_id: str
    task_type: str
    category: FeedbackCategory
    title: str
    detail: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    harness: str = ""
    parent_tips_used: list[str] = Field(default_factory=list)
