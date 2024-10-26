# src/winston/core/messages.py
from datetime import datetime, timezone
from enum import StrEnum, auto
from typing import Any, Callable

from pydantic import BaseModel, Field


class CommunicationType(StrEnum):
  FUNCTION = auto()
  CONVERSATION = auto()
  EVENT = auto()


class MessageError(BaseModel):
  """Structured error information for messages."""

  code: str
  message: str
  details: dict[str, Any] | None = Field(default=None)


class MessageContent(BaseModel):
  """Content of a message with optional metadata."""

  text: str
  metadata: dict[str, Any] | None = Field(default=None)


class MessageResult(BaseModel):
  """Result of message processing."""

  content: str
  metadata: dict[str, Any] | None = Field(default=None)
  error: MessageError | None = Field(default=None)


class Message(BaseModel):
  """Complete message structure with enhanced error handling."""

  sender_id: str
  recipient_id: str
  type: CommunicationType
  content: MessageContent
  context: dict[str, Any] | None = Field(default=None)
  conversation_id: str | None = Field(default=None)
  result: MessageResult | None = Field(default=None)
  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )

  class Config:
    json_encoders: dict[
      type[CommunicationType],
      Callable[[CommunicationType], str],
    ] = {
      CommunicationType: lambda v: v.value,
    }


class Response(BaseModel):
  content: Any
  metadata: dict[str, Any] | None = Field(default=None)
