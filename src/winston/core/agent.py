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
from winston.core.paths import AgentPaths
from winston.core.protocols import (
  Agent,
  System,
)
from winston.core.tools import (
  ToolManager,
)
from winston.core.vision import (
  create_vision_messages,
)

# litellm.set_verbose = True


class AgentConfig(BaseModel):
  """Enhanced agent configuration with validation."""

  id: str
  model: str
  vision_model: str | None = None
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
    paths: AgentPaths,
  ) -> None:
    """Initialize an Agent instance."""
    self.system = system
    self.config = config
    self.paths = paths
    self.state = AgentState()
    self.tool_manager = ToolManager(system, config.id)

    # Register agent first
    system.register_agent(self)

    # Then get workspace manager
    self.workspace_manager = (
      system.get_workspace_manager(self.id)
    )

  @property
  def id(self) -> str:
    """Get the agent ID."""
    return self.config.id

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process message using private workspace first, then shared if available."""
    print(
      f"BaseAgent.process called for {self.__class__.__name__}"
    )
    print(f"Message: {message.content}")

    # Get current private workspace
    private_workspace = (
      self.workspace_manager.load_workspace()
    )
    print("Got private workspace")

    # Process in private workspace and stream responses
    async for result in self._process_private(
      message, private_workspace
    ):
      if isinstance(result, tuple):
        # Unpack workspace and response from tuple
        workspace, response = result
        yield response
      else:
        # Direct response
        yield result

    # Check if we're part of a shared cognitive process
    shared_workspace = message.metadata.get(
      "shared_workspace"
    )
    if shared_workspace:
      # Process in shared context
      async for response in self._process_shared(
        message, private_workspace, shared_workspace
      ):
        yield response

  async def _process_private(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[Response]:
    """Default private processing."""
    # Update private workspace
    updated = (
      await self.workspace_manager.update_workspace(
        message, self
      )
    )
    # Default implementation yields nothing
    if False:
      yield Response(
        content=""
      )  # This makes it a valid AsyncIterator

  async def _process_shared(
    self,
    message: Message,
    private_workspace: str,
    shared_workspace: str,
  ) -> AsyncIterator[Response]:
    """Default shared processing."""
    # Default implementation yields nothing
    if False:
      yield Response(
        content=""
      )  # This makes it a valid AsyncIterator

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

    if history := message.metadata.get("history", []):
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
        results = []
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
          results.append(result)

          # Update the last response with the tool call result
          if formatted_response := result.metadata.get(
            "formatted_response"
          ):
            self.state.last_response = (
              formatted_response
            )
          else:
            self.state.last_response = result.content

        # Yield all results
        for result in results:
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

  async def generate_response(
    self, message: Message
  ) -> Response:
    """Generate a non-streaming response from the LLM."""
    messages = self._prepare_messages(message)
    try:
      response = await acompletion(
        model=self.config.model,
        messages=messages,
        temperature=self.config.temperature,
        stream=False,
        timeout=self.config.timeout,
      )
      model_response = cast(ModelResponse, response)
      if not model_response.choices:
        raise ValueError("No choices in response")

      message = model_response.choices[0].message
      if not message:
        raise ValueError("No message in response")

      if message.content:
        return Response(content=message.content)
      else:
        raise ValueError("No content in message")

    except Exception as e:
      logger.error("LLM error", exc_info=True)
      return Response(
        content=f"Error generating response: {str(e)}",
        metadata={"error": True},
      )

  async def generate_streaming_response(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Generate a streaming response from the LLM.

    Parameters
    ----------
    message : Message
        The input message to process

    Yields
    -------
    Response
        Streamed responses from the LLM
    """
    messages = self._prepare_messages(message)
    try:
      response = await acompletion(
        model=self.config.model,
        messages=messages,
        temperature=self.config.temperature,
        stream=True,
        timeout=self.config.timeout,
      )

      async for (
        chunk
      ) in self._process_streaming_response(
        cast(CustomStreamWrapper, response)
      ):
        yield chunk

    except Exception as e:
      logger.error("LLM error", exc_info=True)
      yield Response(
        content=f"Error generating response: {str(e)}",
        metadata={"error": True},
      )

  async def generate_vision_response(
    self,
    prompt: str,
    image_path: str | Path,
  ) -> Response:
    """Generate a non-streaming response from the vision model.

    Parameters
    ----------
    prompt : str
        Text prompt for the vision model
    image_path : str | Path
        Path to image file

    Returns
    -------
    Response
        The generated response from the vision model
    """
    messages = create_vision_messages(
      prompt, image_path
    )

    try:
      model = (
        self.config.vision_model or self.config.model
      )
      response = await acompletion(
        model=model,
        messages=messages,
        temperature=self.config.temperature,
        stream=False,
        timeout=self.config.timeout,
      )

      model_response = cast(ModelResponse, response)
      if not model_response.choices:
        raise ValueError("No choices in response")

      message = model_response.choices[0].message
      if not message:
        raise ValueError("No message in response")

      if message.content:
        return Response(content=message.content)
      else:
        raise ValueError("No content in message")

    except Exception as e:
      logger.error("Vision model error", exc_info=True)
      return Response(
        content=f"Error processing image: {str(e)}",
        metadata={"error": True},
      )

  async def generate_streaming_vision_response(
    self,
    prompt: str,
    image_path: str | Path,
  ) -> AsyncIterator[Response]:
    """Generate a streaming response from the vision model."""
    messages = create_vision_messages(
      prompt, image_path
    )

    try:
      model = (
        self.config.vision_model or self.config.model
      )
      response = await acompletion(
        model=model,
        messages=messages,
        temperature=self.config.temperature,
        stream=True,
        timeout=self.config.timeout,
      )

      # Process streaming response directly
      async for chunk in cast(
        CustomStreamWrapper, response
      ):
        choices = chunk["choices"][0]
        if content := choices.delta.get("content"):
          yield Response(content=content)

    except Exception as e:
      logger.error("Vision model error", exc_info=True)
      yield Response(
        content=f"Error processing image: {str(e)}",
        metadata={"error": True},
      )
