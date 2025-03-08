"""Core agent interfaces and base implementation."""

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, cast

import litellm
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

from winston.core.agent_config import AgentConfig
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
from winston.core.workspace import WorkspaceManager

# litellm.set_verbose = True
litellm.drop_params = True


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
    self._config = config
    self.paths = paths
    self.state = AgentState()
    self.tool_manager = ToolManager(system, config.id)

    # Register agent first
    system.register_agent(self)

  @property
  def id(self) -> str:
    """Get the agent ID."""
    return self.config.id

  @property
  def workspace_path(self) -> Path:
    """Get path to this agent's workspace."""
    return self.paths.workspaces / f"{self.id}.md"

  @property
  def config(self) -> AgentConfig:
    """Get the agent configuration."""
    return self._config

  @classmethod
  def can_handle(cls, message: Message) -> bool:
    """Check if this agent can handle the message."""
    return True

  def _get_workspaces(
    self,
    message: Message,
  ) -> tuple[str, str | None]:
    """Get private and shared workspace content.

    Parameters
    ----------
    message : Message
        Message that may contain shared workspace path

    Returns
    -------
    tuple[str, str | None]
        Private workspace content and optional shared workspace content
    """
    # Get private workspace content
    workspace_manager = WorkspaceManager()
    private_workspace = (
      workspace_manager.load_workspace(
        self.workspace_path
      )
    )

    # Check for shared workspace
    shared_workspace_path = message.metadata.get(
      "shared_workspace"
    )
    if shared_workspace_path:
      shared_workspace = (
        workspace_manager.load_workspace(
          shared_workspace_path
        )
      )
    else:
      shared_workspace = None

    return private_workspace, shared_workspace

  async def _update_workspaces(
    self,
    message: Message,
    private_update_template: str | None = None,
    shared_update_template: str | None = None,
    update_category: str | None = None,
  ) -> tuple[str, str | None]:
    """Update workspaces with new content."""
    workspace_manager = WorkspaceManager()

    private_workspace = (
      await workspace_manager.update_workspace(
        self.workspace_path,
        message,
        self,
        private_update_template,
        update_category,
      )
    )

    # Check for shared workspace
    shared_workspace_path = message.metadata.get(
      "shared_workspace"
    )
    if shared_workspace_path:
      shared_workspace = (
        await workspace_manager.update_workspace(
          shared_workspace_path,
          message,
          self,
          shared_update_template,
          update_category,
        )
      )
    else:
      shared_workspace = None

    return private_workspace, shared_workspace

  async def _handle_conversation(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Handle conversation with LLM integration."""
    logger.debug(
      f"Handling conversation for message: {message}"
    )
    messages = self._prepare_messages(message)
    tools = self.tool_manager.get_tools_schema()
    logger.debug(f"Tools schema: {tools}")
    logger.debug(
      f"Required tool: {self.config.required_tool}"
    )
    tool_choice = None
    if self.config.required_tool:
      # Validate required tool exists in schema
      available_tools = {
        tool["function"]["name"]
        for tool in tools
        if tool.get("type") == "function"
        and "function" in tool
      }
      if (
        self.config.required_tool
        not in available_tools
      ):
        logger.error(
          f"Required tool '{self.config.required_tool}' not found in available tools: {available_tools}"
        )
        yield Response(
          content=f"Configuration error: Required tool '{self.config.required_tool}' not available",
          metadata={"error": True},
        )
        return

      tool_choice = {
        "type": "function",  # OpenAI format
        "function": {
          "name": self.config.required_tool
        },
      }
    logger.trace(f"Tool choice: {tool_choice}")

    # Add retry logic for API connection issues
    max_retries = 2
    retry_count = 0
    backoff_time = 1.0  # Start with 1 second backoff

    while retry_count <= max_retries:
      try:
        logger.info(
          f"Starting LLM conversation (attempt {retry_count + 1}/{max_retries + 1})..."
        )
        response = await acompletion(
          model=self.config.model,
          messages=messages,
          temperature=self.config.temperature,
          stream=self.config.stream,
          tools=tools if tools else None,
          tool_choice=tool_choice,
          timeout=self.config.timeout,
        )
        logger.debug(
          f"LLM Response received: {response}"
        )
        logger.debug(
          f"Response type: {type(response)}"
        )
        if (
          hasattr(response, "choices")
          and response.choices
        ):
          logger.debug(
            f"First choice: {response.choices[0]}"
          )
        if self.config.stream:
          try:
            async for (
              chunk
            ) in self._process_streaming_response(
              cast(CustomStreamWrapper, response)
            ):
              yield chunk
            # If we get here without exception, break the retry loop
            break
          except Exception as stream_error:
            if (
              "cancel scope" in str(stream_error)
              and retry_count < max_retries
            ):
              # This is likely the specific error we're trying to handle
              logger.warning(
                f"Streaming error (attempt {retry_count + 1}): {stream_error}. Retrying..."
              )
              retry_count += 1
              await asyncio.sleep(backoff_time)
              backoff_time *= 2  # Exponential backoff
              continue
            else:
              # Different error or max retries reached, propagate it
              logger.exception(
                f"Unrecoverable streaming error: {stream_error}"
              )
              yield Response(
                content=f"Error in streaming response: {str(stream_error)}",
                metadata={"error": True},
              )
              break
        else:
          yield await self._process_single_response(
            cast(ModelResponse, response)
          )
          break  # Success, exit retry loop

      except Exception as e:
        if retry_count < max_retries:
          logger.warning(
            f"API error (attempt {retry_count + 1}): {str(e)}. Retrying..."
          )
          retry_count += 1
          await asyncio.sleep(backoff_time)
          backoff_time *= 2  # Exponential backoff
        else:
          logger.exception(
            f"Exception occurred during conversation handling after {max_retries + 1} attempts: {str(e)}"
          )
          yield Response(
            content=f"Error generating response after multiple attempts: {str(e)}",
            metadata={"error": True},
          )
          break

  def _prepare_messages(
    self, message: Message
  ) -> list[ChatCompletionMessageParam]:
    """Prepare messages for LLM."""
    messages: list[ChatCompletionMessageParam] = []

    if self.config.system_prompt_template:
      # Render template with message metadata
      system_prompt = self.config.render_system_prompt(
        message.metadata
      )
      messages.append(
        Message.system(
          system_prompt
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

    try:
      async for chunk in response:
        try:
          choices_list = cast(
            list[StreamingChoices],
            chunk["choices"],
          )
          choices: StreamingChoices = choices_list[0]
          # logger.trace(f"Choices: {choices}")
          # Handle tool calls completion
          if (
            hasattr(choices, "finish_reason")
            and choices["finish_reason"]
            in ("tool_calls", "stop")
            and not tool_calls
          ):
            logger.debug(
              "Stream completed with no tool calls present"
            )
            # Ensure tool calls are present if a tool choice was specified
            if self.config.required_tool:
              logger.warning(
                f"Expected tool call for {self.config.required_tool} but none found."
              )
              # Continue instead of raising an exception to avoid crashing
              continue
          elif (
            hasattr(choices, "finish_reason")
            and choices["finish_reason"]
            in ("tool_calls", "stop")
            and tool_calls
          ):
            results = []
            for tool_call in tool_calls:
              try:
                result = await self.tool_manager.execute_tool({
                  "name": tool_call.function["name"],
                  "arguments": tool_call.function[
                    "arguments"
                  ],
                })
                results.append(result)

                # Update the last response with the tool call result
                if (
                  formatted_response
                  := result.metadata.get(
                    "formatted_response"
                  )
                ):
                  self.state.last_response = (
                    formatted_response
                  )
                else:
                  self.state.last_response = (
                    result.content
                  )
              except Exception as e:
                logger.exception(
                  f"Error executing tool call: {e}"
                )
                results.append(
                  Response(
                    content=f"Error executing tool: {str(e)}",
                    metadata={"error": True},
                  )
                )

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
                assert (
                  len(tool_calls) == tool_call.index
                )
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
                ].function.name = (
                  tool_call.function.name
                )

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
            yield Response(
              content=delta["content"],
              metadata={"streaming": True},
            )
        except Exception as chunk_error:
          logger.exception(
            f"Error processing chunk: {chunk_error}"
          )
          yield Response(
            content=f"Error processing response chunk: {str(chunk_error)}",
            metadata={
              "error": True,
              "streaming": True,
            },
          )
    except Exception as stream_error:
      logger.exception(
        f"Error in streaming response: {stream_error}"
      )
      yield Response(
        content=f"Error in streaming response: {str(stream_error)}",
        metadata={"error": True, "streaming": True},
      )

  async def _process_single_response(
    self, response: ModelResponse
  ) -> Response:
    """Process non-streaming LLM response."""
    if not response.choices:
      raise ValueError("No choices in response")

    message = response.choices[0].message
    if not message:
      raise ValueError("No message in response")

    if not (
      hasattr(message, "tool_calls")
      and message.tool_calls
    ):
      logger.debug("No tool calls present in response")
      # Ensure tool calls are present if a tool choice was specified
      if self.config.required_tool:
        raise ValueError(
          "Expected tool call in response but none found."
        )
    elif (
      hasattr(message, "tool_calls")
      and message.tool_calls
    ):
      results = []
      for tool_call in message.tool_calls:
        result = await self.tool_manager.execute_tool({
          "name": tool_call.function.name,
          "arguments": tool_call.function.arguments,
        })
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
    logger.debug(
      f"Generating response for message: {message}"
    )
    messages = self._prepare_messages(message)
    try:
      logger.info(
        "Starting LLM response generation..."
      )
      response = await acompletion(
        model=self.config.model,
        messages=messages,
        temperature=self.config.temperature,
        stream=False,
        timeout=self.config.timeout,
      )
      model_response = cast(ModelResponse, response)
      if not model_response.choices:
        logger.error("No choices in response")
        raise ValueError("No choices in response")

      message = model_response.choices[0].message
      if not message:
        logger.error("No message in response")
        raise ValueError("No message in response")

      if message.content:
        return Response(content=message.content)
      else:
        logger.error("No content in message")
        raise ValueError("No content in message")

    except Exception as e:
      logger.exception(f"LLM error occurred: {str(e)}")
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

    # Add retry logic for API connection issues
    max_retries = 2
    retry_count = 0
    backoff_time = 1.0  # Start with 1 second backoff

    while retry_count <= max_retries:
      try:
        logger.info(
          f"Starting streaming response generation (attempt {retry_count + 1}/{max_retries + 1})..."
        )
        response = await acompletion(
          model=self.config.model,
          messages=messages,
          temperature=self.config.temperature,
          stream=True,
          timeout=self.config.timeout,
        )

        try:
          async for (
            chunk
          ) in self._process_streaming_response(
            cast(CustomStreamWrapper, response)
          ):
            yield chunk
          # If we get here without exception, break the retry loop
          break
        except Exception as stream_error:
          if (
            "cancel scope" in str(stream_error)
            and retry_count < max_retries
          ):
            # This is likely the specific error we're trying to handle
            logger.warning(
              f"Streaming error (attempt {retry_count + 1}): {stream_error}. Retrying..."
            )
            retry_count += 1
            await asyncio.sleep(backoff_time)
            backoff_time *= 2  # Exponential backoff
            continue
          else:
            # Different error or max retries reached, propagate it
            logger.exception(
              f"Unrecoverable streaming error: {stream_error}"
            )
            yield Response(
              content=f"Error in streaming response: {str(stream_error)}",
              metadata={"error": True},
            )
            break

      except Exception as e:
        if retry_count < max_retries:
          logger.warning(
            f"API error (attempt {retry_count + 1}): {str(e)}. Retrying..."
          )
          retry_count += 1
          await asyncio.sleep(backoff_time)
          backoff_time *= 2  # Exponential backoff
        else:
          logger.exception(
            f"LLM error after {max_retries + 1} attempts: {str(e)}"
          )
          yield Response(
            content=f"Error generating response after multiple attempts: {str(e)}",
            metadata={"error": True},
          )
          break

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

    # Add retry logic for API connection issues
    max_retries = 2
    retry_count = 0
    backoff_time = 1.0  # Start with 1 second backoff

    while retry_count <= max_retries:
      try:
        logger.info(
          f"Starting vision streaming response (attempt {retry_count + 1}/{max_retries + 1})..."
        )
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

        try:
          # Process streaming response directly
          async for chunk in cast(
            CustomStreamWrapper, response
          ):
            choices = chunk["choices"][0]
            if content := choices.delta.get("content"):
              yield Response(content=content)
          # If we get here without exception, break the retry loop
          break
        except Exception as stream_error:
          if (
            "cancel scope" in str(stream_error)
            and retry_count < max_retries
          ):
            # This is likely the specific error we're trying to handle
            logger.warning(
              f"Vision streaming error (attempt {retry_count + 1}): {stream_error}. Retrying..."
            )
            retry_count += 1
            await asyncio.sleep(backoff_time)
            backoff_time *= 2  # Exponential backoff
            continue
          else:
            # Different error or max retries reached, propagate it
            logger.exception(
              f"Unrecoverable vision streaming error: {stream_error}"
            )
            yield Response(
              content=f"Error in vision streaming response: {str(stream_error)}",
              metadata={"error": True},
            )
            break

      except Exception as e:
        if retry_count < max_retries:
          logger.warning(
            f"Vision API error (attempt {retry_count + 1}): {str(e)}. Retrying..."
          )
          retry_count += 1
          await asyncio.sleep(backoff_time)
          backoff_time *= 2  # Exponential backoff
        else:
          logger.exception(
            f"Vision model error after {max_retries + 1} attempts: {str(e)}"
          )
          yield Response(
            content=f"Error processing image after multiple attempts: {str(e)}",
            metadata={"error": True},
          )
          break

  def _get_response_metadata(self) -> dict[str, Any]:
    """Get metadata to be added to responses.

    This method is intended to be overridden by subclasses to provide
    specialized metadata for responses.

    Returns
    -------
    dict[str, Any]
        Metadata to be added to responses
    """
    return {}

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process messages through LLM conversation.

    This method handles common operations like extracting workspace content,
    calling _handle_conversation, and applying specialized metadata to responses.

    Parameters
    ----------
    message : Message
        The message to process

    Yields
    ------
    Response
        Responses from the LLM conversation
    """
    # Track accumulated content from streaming responses
    accumulated_content: list[str] = []

    # Let the LLM evaluate the message using system prompt and tools
    async for response in self._handle_conversation(
      message
    ):
      if response.metadata.get("streaming"):
        accumulated_content.append(response.content)
        yield response
        continue

      # For non-streaming responses, add specialized metadata
      metadata = response.metadata.copy()
      metadata.update(self._get_response_metadata())

      yield Response(
        content=response.content,
        metadata=metadata,
      )
      return

    # If we only got streaming responses, send a final non-streaming response
    if accumulated_content:
      final_content = "".join(accumulated_content)
      yield Response(
        content=final_content,
        metadata=self._get_response_metadata(),
      )
