"""
Core tool system providing type-safe function registration and execution.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import (
  Any,
  Awaitable,
  Callable,
  TypeVar,
)

from pydantic import BaseModel

from winston.core.messages import Response
from winston.core.protocols import System, Tool

logger = logging.getLogger(__name__)

# Type variable for tool return types
T = TypeVar("T", bound=BaseModel)


class ToolParameterType(str, Enum):
  """Valid parameter types for tools."""

  STRING = "string"
  NUMBER = "number"
  INTEGER = "integer"
  BOOLEAN = "boolean"
  ARRAY = "array"
  OBJECT = "object"


class ToolError(Exception):
  """Base exception for tool-related errors"""

  pass


class ToolValidationError(ToolError):
  """Raised when tool inputs or outputs fail validation"""

  pass


class ToolExecutionError(ToolError):
  """Raised when a tool fails during execution"""

  pass


@dataclass
class ParameterSchema:
  """Schema for a single tool parameter"""

  type: ToolParameterType
  description: str
  required: bool = False
  enum: list[str] | None = None
  default: Any | None = None


@dataclass
class ToolSchema(BaseModel):
  name: str
  description: str
  parameters: dict[str, dict[str, Any]]


class ToolImpl(Tool[T]):
  """Implementation of Tool protocol."""

  def __init__(
    self,
    name: str,
    description: str,
    parameters: dict[str, ParameterSchema],
    required_params: list[str],
    return_type: type[T],
    handler: Callable[..., Awaitable[T]],
  ):
    self.name = name
    self.description = description
    self.parameters = parameters
    self.required_params = required_params
    self.return_type = return_type
    self.handler = handler

  async def execute(self, **kwargs: Any) -> T:
    """Execute the tool with validation."""
    try:
      # Validate inputs
      missing = [
        p
        for p in self.required_params
        if p not in kwargs
      ]
      if missing:
        raise ToolValidationError(
          f"Missing required parameters: {missing}"
        )

      # Execute handler
      result = await self.handler(**kwargs)

      # Validate output
      if not isinstance(result, self.return_type):
        raise ToolValidationError(
          f"Invalid return type. Expected {self.return_type}"
        )

      return result

    except ToolValidationError:
      logger.error(
        "Tool validation error", exc_info=True
      )
      raise
    except Exception as e:
      logger.error(
        "Tool execution error", exc_info=True
      )
      raise ToolExecutionError(str(e)) from e


def create_tool(
  name: str,
  description: str,
  parameters: dict[str, ParameterSchema],
  handler: Callable[..., Awaitable[T]],
  required_params: list[str],
  return_type: type[T],
) -> Tool[T]:
  """Create a new tool instance."""
  return ToolImpl(
    name=name,
    description=description,
    parameters=parameters,
    handler=handler,
    required_params=required_params,
    return_type=return_type,
  )


class ToolManager:
  """Manages tool registration and execution."""

  def __init__(self, system: System, agent_id: str):
    self.system = system
    self.agent_id = agent_id

  def get_tools_schema(self) -> list[dict[str, Any]]:
    """Convert tools to OpenAI format."""
    if not self.system:
      return []

    agent_tools = self.system.get_agent_tools(
      self.agent_id
    )
    return [
      {
        "type": "function",
        "function": {
          "name": tool.name,
          "description": tool.description,
          "parameters": {
            "type": "object",
            "properties": {
              name: {
                "type": param.type.value,
                "description": param.description,
                **(
                  {"enum": param.enum}
                  if param.enum
                  else {}
                ),
                **(
                  {"default": param.default}
                  if param.default is not None
                  else {}
                ),
              }
              for name, param in tool.parameters.items()
            },
            "required": tool.required_params,
          },
        },
      }
      for tool in agent_tools.values()
    ]

  async def execute_tool(
    self, function_call: dict[str, Any]
  ) -> Response:
    """Execute a tool call."""
    try:
      tool = self.system.get_agent_tools(
        self.agent_id
      )[function_call["name"]]
      args = json.loads(function_call["arguments"])
      result = await tool.execute(**args)
      return Response(
        content=result.model_dump_json(),
      )
    except Exception as e:
      logger.error(
        f"Tool execution error: {str(e)}",
        exc_info=True,
      )
      return Response(
        content=f"Error executing function: {str(e)}",
        metadata={"error": True},
      )
