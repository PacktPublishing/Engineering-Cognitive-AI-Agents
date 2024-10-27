# src/winston/core/messages.py
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, TypeVar

from litellm.types.completion import (
  ChatCompletionMessageParam,
)
from pydantic import BaseModel, Field

T = TypeVar("T", bound=BaseModel)


class MessageRole(StrEnum):
  """Standard message roles."""

  SYSTEM = "system"
  USER = "user"
  ASSISTANT = "assistant"
  FUNCTION = "function"


class Message(BaseModel):
  """Universal message format for all communication."""

  content: Any
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )
  context: dict[str, Any] = Field(default_factory=dict)
  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )

  def to_chat_completion_message(
    self,
  ) -> ChatCompletionMessageParam:
    """Convert to OpenAI chat completion format.

    Returns
    -------
    ChatCompletionMessageParam
        Message in OpenAI format
    """
    role = self.metadata.get("role", MessageRole.USER)
    return {
      "role": role,
      "content": str(self.content),
    }

  @classmethod
  def from_chat_completion(
    cls,
    message: ChatCompletionMessageParam,
  ) -> "Message":
    """Create from chat completion format.

    Parameters
    ----------
    message : ChatCompletionMessageParam
        Message in OpenAI format

    Returns
    -------
    Message
        New message instance
    """
    return cls(
      content=message["content"],
      metadata={"role": message["role"]},
    )

  def to_history_format(self) -> dict[str, str]:
    """Convert to chat history format.

    Returns
    -------
    dict[str, str]
        Message in history format
    """
    role = self.metadata.get("role", MessageRole.USER)
    return {
      "role": role,
      "content": str(self.content),
    }

  @classmethod
  def from_history(
    cls, history_message: dict[str, str]
  ) -> "Message":
    """Create from history format.

    Parameters
    ----------
    history_message : dict[str, str]
        Message in history format

    Returns
    -------
    Message
        New message instance
    """
    return cls(
      content=history_message["content"],
      metadata={"role": history_message["role"]},
    )

  @classmethod
  def system(cls, content: str) -> "Message":
    """Create a system message.

    Parameters
    ----------
    content : str
        Message content

    Returns
    -------
    Message
        New system message
    """
    return cls(
      content=content,
      metadata={"role": MessageRole.SYSTEM},
    )


class Response(BaseModel):
  """Universal response format."""

  content: Any
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )
  timestamp: datetime = Field(
    default_factory=lambda: datetime.now(timezone.utc)
  )

  def to_history_format(self) -> dict[str, str]:
    """Convert to chat history format.

    Returns
    -------
    dict[str, str]
        Response in history format
    """
    return {
      "role": MessageRole.ASSISTANT,
      "content": str(self.content),
    }
