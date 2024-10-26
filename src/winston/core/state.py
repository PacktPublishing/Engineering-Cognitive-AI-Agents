# src/winston/core/state.py
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class LogLevel(StrEnum):
  """Log levels for agent logging."""

  DEBUG = "debug"
  INFO = "info"
  WARNING = "warning"
  ERROR = "error"


class AgentContext(BaseModel):
  """Structured context for agent state."""

  conversation_id: str | None = None
  user_id: str | None = None
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )


class AgentState(BaseModel):
  """Enhanced state management for agents."""

  last_response: str | None = None
  last_error: str | None = None
  context: AgentContext = Field(
    default_factory=AgentContext
  )
  created_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
  )
  updated_at: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
  )


class AgentLog(BaseModel):
  """Structured logging for agents."""

  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc),
  )
  level: LogLevel
  message: str
  agent_id: str
  behavior: str | None = None
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )
