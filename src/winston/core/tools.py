"""
Core tool system providing type-safe function registration and execution.
"""

from typing import (
  Any,
  Awaitable,
  Callable,
  Generic,
  TypeVar,
)

import openai
from loguru import logger
from pydantic import BaseModel, Field

from winston.core.messages import Response
from winston.core.protocols import System

# Type variable for tool return types
T = TypeVar("T", bound=BaseModel)


class Tool(BaseModel, Generic[T]):
  """Tool definition using Pydantic."""

  name: str = Field(
    ..., description="Unique name for the tool"
  )
  description: str = Field(
    ..., description="Clear description for the LLM"
  )
  handler: Callable[[Any], Awaitable[T]] = Field(
    ...,
    description="Async function that implements the tool logic",
  )
  input_model: type[BaseModel] = Field(
    ...,
    description="Pydantic model defining the input parameters",
  )
  output_model: type[T] = Field(
    ...,
    description="Pydantic model defining the return type",
  )

  def to_openai_schema(self) -> dict[str, Any]:
    """Convert tool to OpenAI function format using official helper."""
    tool_param = openai.pydantic_function_tool(
      self.input_model,
      name=self.name,
      description=self.description,
    )
    # Convert to a regular dict
    return dict(tool_param)


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
      tool.to_openai_schema()
      for tool in agent_tools.values()
    ]

  async def execute_tool(
    self, function_call: dict[str, Any]
  ) -> Response:
    """Execute a tool call.

    Parameters
    ----------
    function_call : dict[str, Any]
        The function call parameters from OpenAI

    Returns
    -------
    Response
        The tool execution response
    """
    try:
      tool_name = function_call["name"]
      tool = self.system.get_agent_tools(
        self.agent_id
      )[tool_name]

      # Parse arguments using input model
      args = tool.input_model.model_validate_json(
        function_call["arguments"]
      )

      # Execute handler and validate output
      result = await tool.handler(args)

      # Validate output matches expected model
      if not isinstance(result, tool.output_model):
        raise ValueError(
          f"Handler returned {type(result)}, expected {tool.output_model}"
        )

      return Response(
        content=result.model_dump_json(),
        metadata={"tool_call": True},
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
