# src/winston/core/messages.py
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Message(BaseModel):
  """
  Universal message format for all communication.

  Parameters
  ----------
  content : Any
      The main content of the message.
  metadata : dict[str, Any]
      Additional metadata about the message.
  context : dict[str, Any]
      Contextual information for message processing.
  timestamp : datetime
      When the message was created.
  """

  content: Any
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )
  context: dict[str, Any] = Field(default_factory=dict)
  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )


class Response(BaseModel):
  """
  Universal response format.

  Parameters
  ----------
  content : Any
      The response content.
  metadata : dict[str, Any]
      Additional metadata about the response.
  timestamp : datetime
      When the response was created.
  """

  content: Any
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )
  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )
