# src/winston/core/tools.py
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator


class ModelType(str, Enum):
  """Supported model types."""

  GPT4O_MINI = "gpt-4o-mini"


class ToolParameter(BaseModel):
  """Enhanced tool parameter validation."""

  type: str = Field(
    ...,
    pattern="^(string|number|boolean|array|object)$",
  )
  description: str | None = Field(None, min_length=1)
  enum: list[str] | None = None

  @field_validator("enum")
  @classmethod
  def validate_enum(
    cls,
    v: list[str] | None,
    info: Any,
  ) -> list[str] | None:
    """Validate enum values are only used with string type."""
    if v and info.data.get("type") != "string":
      raise ValueError(
        "Enum can only be used with string type"
      )
    return v


class ToolSchema(BaseModel):
  """Tool schema with enhanced validation."""

  type: str = "object"
  properties: dict[str, ToolParameter]
  required: list[str] = Field(default_factory=list)


T = TypeVar("T", bound=BaseModel)


class ToolResult(BaseModel, Generic[T]):
  """Generic result type for tool executions."""

  success: bool
  data: T | None = None
  error: str | None = None
  metadata: dict[str, Any] = Field(
    default_factory=dict
  )


@dataclass
class Tool:
  """Configuration for a tool/function that can be called by the agent."""

  name: str
  description: str
  parameters: ToolSchema
  handler: Callable[..., Any]


class ToolRegistry:
  """
  Central registry for tool definitions.

  This is a singleton class that maintains a global registry of tools
  that can be used by agents.

  Attributes
  ----------
  tools : dict[str, Tool]
      Dictionary mapping tool names to Tool instances.
  """

  _instance: Any = None
  tools: dict[str, Tool] = {}

  def __new__(cls) -> "ToolRegistry":
    """Ensure singleton instance."""
    if not cls._instance:
      cls._instance = super().__new__(cls)
      cls._instance.tools = {}
    return cls._instance

  def register(self, tool: Tool) -> None:
    """
    Register a tool in the registry.

    Parameters
    ----------
    tool : Tool
        The tool to register.
    """
    self.tools[tool.name] = tool

  def get_tool(self, tool_id: str) -> Tool | None:
    """
    Get a tool by its ID (name).

    Parameters
    ----------
    tool_id : str
        The ID (name) of the tool to retrieve.

    Returns
    -------
    Tool | None
        The requested tool, or None if not found.
    """
    return self.tools.get(tool_id)

  def get_tools(
    self, tool_ids: list[str]
  ) -> list[Tool]:
    """
    Get multiple tools by their IDs.

    Parameters
    ----------
    tool_ids : list[str]
        List of tool IDs to retrieve.

    Returns
    -------
    list[Tool]
        List of found tools. Skips any IDs that aren't found.
    """
    return [
      t for id in tool_ids if (t := self.tools.get(id))
    ]
