"""Core agent interfaces and base implementation."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, cast

import yaml
from litellm import acompletion
from litellm.types.completion import (
  ChatCompletionMessageParam,
)
from litellm.types.utils import (
  ChatCompletionDeltaToolCall,
  Function,
  ModelResponse,
  StreamingChoices,
)
from litellm.utils import CustomStreamWrapper
from loguru import logger
from pydantic import BaseModel

from winston.core.messages import Message, Response
from winston.core.protocols import Agent, System
from winston.core.tools import (
  ToolManager,
)


class AgentConfig(BaseModel):
  """Enhanced agent configuration with validation."""

  id: str
  model: str
  system_prompt: str
  temperature: float = 0.7
  stream: bool = True
  max_retries: int = 3
  timeout: float = 30.0

  @classmethod
  def from_yaml(
    cls, path: str | Path
  ) -> "AgentConfig":
    """Load configuration from a YAML file.

    Parameters
    ----------
    path : str | Path
        Path to the YAML configuration file

    Returns
    -------
    AgentConfig
        Loaded and validated configuration

    Raises
    ------
    FileNotFoundError
        If the configuration file doesn't exist
    ValueError
        If the configuration is invalid
    """
    path = Path(path)
    with path.open() as f:
      config_data = yaml.safe_load(f)

    return cls.model_validate(config_data)

  @classmethod
  def from_json(
    cls, path: str | Path
  ) -> "AgentConfig":
    """Load configuration from a JSON file.

    Parameters
    ----------
    path : str | Path
        Path to the JSON configuration file

    Returns
    -------
    AgentConfig
        Loaded and validated configuration

    Raises
    ------
    FileNotFoundError
        If the configuration file doesn't exist
    ValueError
        If the configuration is invalid
    """
    path = Path(path)
    with path.open() as f:
      config_data = json.load(f)

    return cls.model_validate(config_data)


@dataclass
class AgentState:
  """State management for the agent."""

  last_response: str | None = None
  last_error: str | None = None
  context: dict[str, Any] = field(default_factory=dict)
  tool_calls: dict[str, Any] = field(
    default_factory=dict
  )


class BaseAgent(Agent):
  """Base agent implementation with LLM support."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
  ) -> None:
    """Initialize an Agent instance."""
    self.system = system
    self.config = config
    self.state = AgentState()
    self.tool_manager = ToolManager(system, config.id)

  @property
  def id(self) -> str:
    """Get the agent ID."""
    return self.config.id

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process an incoming message."""
    try:
      pattern = message.metadata.get(
        "pattern", "conversation"
      )

      if pattern == "conversation":
        async for (
          response
        ) in self._handle_conversation(message):
          yield response
      elif pattern == "function":
        yield await self._handle_function(message)
      elif pattern == "event":
        yield await self._handle_event(message)
      else:
        raise ValueError(f"Unknown pattern: {pattern}")

    except Exception as e:
      logger.error(
        "Error processing message", exc_info=True
      )
      yield Response(
        content=f"Error processing message: {str(e)}",
        metadata={"error": True},
      )

  async def _handle_conversation(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Handle conversation with LLM integration."""
    messages = self._prepare_messages(message)
    tools = self.tool_manager.get_tools_schema()
    try:
      response = await acompletion(
        model=self.config.model,
        messages=messages,
        temperature=self.config.temperature,
        stream=self.config.stream,
        tools=tools if tools else None,
        timeout=self.config.timeout,
      )

      if self.config.stream:
        async for (
          chunk
        ) in self._process_streaming_response(
          cast(CustomStreamWrapper, response)
        ):
          yield chunk
      else:
        yield await self._process_single_response(
          cast(ModelResponse, response)
        )

    except Exception as e:
      logger.error("LLM error", exc_info=True)
      yield Response(
        content=f"Error generating response: {str(e)}",
        metadata={"error": True},
      )

  def _prepare_messages(
    self, message: Message
  ) -> list[ChatCompletionMessageParam]:
    """Prepare messages for LLM."""
    messages: list[ChatCompletionMessageParam] = []

    if self.config.system_prompt:
      messages.append(
        Message.system(
          self.config.system_prompt
        ).to_chat_completion_message()
      )

    if history := message.context.get("history", []):
      messages.extend(
        Message.from_history(
          msg
        ).to_chat_completion_message()
        for msg in history
      )

    messages.append(
      message.to_chat_completion_message()
    )

    return messages

  async def _process_streaming_response(
    self,
    response: CustomStreamWrapper,
  ) -> AsyncIterator[Response]:
    """Process streaming LLM response."""
    tool_calls: list[ChatCompletionDeltaToolCall] = []
    accumulated_content: str = ""

    async for chunk in response:
      choices_list = cast(
        list[StreamingChoices],
        chunk["choices"],
      )
      choices: StreamingChoices = choices_list[0]

      # Handle tool calls completion
      if (
        hasattr(choices, "finish_reason")
        and choices["finish_reason"] == "tool_calls"
        and tool_calls
      ):
        for tool_call in tool_calls:
          result = (
            await self.tool_manager.execute_tool(
              {
                "name": tool_call.function["name"],
                "arguments": tool_call.function[
                  "arguments"
                ],
              }
            )
          )
          yield result
        return

      delta = choices.delta
      if delta.tool_calls:
        for tool_call in cast(
          list[ChatCompletionDeltaToolCall],
          delta["tool_calls"],
        ):
          if len(tool_calls) <= tool_call.index:
            assert len(tool_calls) == tool_call.index
            tool_calls.append(
              ChatCompletionDeltaToolCall(
                function=Function(
                  arguments=None,
                ),
                index=tool_call.index,
              )
            )

          if tool_call.function.name:
            tool_calls[
              tool_call.index
            ].function.name = tool_call.function.name

          if tool_call.function.arguments:
            tool_calls[
              tool_call.index
            ].function.arguments += (
              tool_call.function.arguments
            )

      # Handle content
      if (
        hasattr(delta, "content")
        and delta["content"] is not None
      ):
        accumulated_content += str(delta["content"])
        yield Response(
          content=delta["content"],
          metadata={"streaming": True},
        )

    if accumulated_content:
      self.state.last_response = accumulated_content

  async def _process_single_response(
    self, response: ModelResponse
  ) -> Response:
    """Process non-streaming LLM response."""
    if not response.choices:
      raise ValueError("No choices in response")

    message = response.choices[0].message
    if not message:
      raise ValueError("No message in response")

    if (
      hasattr(message, "tool_calls")
      and message.tool_calls
    ):
      results = []
      for tool_call in message.tool_calls:
        result = await self.tool_manager.execute_tool(
          {
            "name": tool_call.function.name,
            "arguments": tool_call.function.arguments,
          }
        )
        results.append(result)
      return Response(
        content=str(results),
        metadata={"tool_calls": True},
      )

    if message.content:
      self.state.last_response = message.content
      return Response(content=message.content)

    raise ValueError("No content in message")

  async def _handle_function(
    self, message: Message
  ) -> Response:
    """Handle function calls."""
    if not isinstance(message.content, dict):
      return Response(
        content="Invalid function call format",
        metadata={"error": True},
      )

    try:
      return await self.tool_manager.execute_tool(
        message.content
      )
    except Exception as e:
      logger.error(
        "Function execution error", exc_info=True
      )
      return Response(
        content=f"Error executing function: {str(e)}",
        metadata={"error": True},
      )

  async def _handle_event(
    self, message: Message
  ) -> Response:
    """Handle events."""
    event_type = message.metadata.get(
      "event_type", "unknown"
    )
    self.state.context[f"last_{event_type}"] = (
      message.content
    )
    return Response(
      content=f"Processed event: {event_type}",
      metadata={"event_type": event_type},
    )
