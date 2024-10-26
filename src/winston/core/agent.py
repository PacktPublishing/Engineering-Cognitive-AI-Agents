# src/winston/agents/base.py
import json
from dataclasses import dataclass, field
from typing import (
  Any,
  AsyncIterator,
)

from litellm import acompletion
from litellm.types.completion import (
  ChatCompletionMessageParam,
)
from pydantic import BaseModel, field_validator

from winston.core.behavior import Behavior
from winston.core.messages import (
  CommunicationType,
  Message,
  MessageContent,
)
from winston.core.tools import (
  Tool,
  ToolRegistry,
)


class AgentConfig(BaseModel):
  """Enhanced agent configuration with validation."""

  id: str
  type: str
  capabilities: set[str]
  behaviors: list[Behavior]
  prompts: dict[str, str]

  @field_validator("behaviors")
  @classmethod
  def validate_behaviors(
    cls,
    v: list[Behavior],
  ) -> list[Behavior]:
    """Validate behavior names are unique."""
    names: set[str] = set()
    for behavior in v:
      if behavior.name in names:
        raise ValueError(
          f"Duplicate behavior name: {behavior.name}"
        )
      names.add(behavior.name)
    return v


@dataclass
class AgentState:
  """State management for the agent."""

  last_response: str | None = None
  last_error: str | None = None
  context: dict[str, Any] = field(default_factory=dict)


class Agent:
  """Base agent class supporting configuration-driven behavior."""

  def __init__(
    self,
    config: AgentConfig,
  ) -> None:
    """Initialize an Agent instance."""
    self.id = config.id
    self.type = config.type
    self.capabilities = config.capabilities
    self.behaviors: dict[str, Behavior] = {}

    # Initialize behaviors
    for behavior in config.behaviors:
      behavior_config = Behavior(
        name=behavior.name,
        type=behavior.type,
        model=behavior.model,
        temperature=behavior.temperature,
        stream=behavior.stream,
        tool_ids=behavior.tool_ids,
      )
      self.behaviors[behavior.name] = behavior_config

    self.prompts = config.prompts
    self.state = AgentState()

  async def _handle_function_call(
    self,
    behavior: Behavior,
    function_name: str,
    arguments: str,
  ) -> str:
    """Handle function calls from LLM."""
    try:
      args = json.loads(arguments)
      tool_registry = ToolRegistry()
      tool = tool_registry.get_tool(function_name)

      if not tool:
        raise ValueError(
          f"Tool {function_name} not found"
        )

      result = await tool.handler(**args)

      # Convert Pydantic model to dict before JSON serialization
      if hasattr(result, "model_dump"):
        result_dict = result.model_dump()
      else:
        result_dict = result

      return json.dumps(result_dict)
    except Exception as e:
      error_response = {"error": str(e)}
      return json.dumps(error_response)

  async def _execute_behavior(
    self,
    behavior: Behavior,
    message: Message,
  ) -> AsyncIterator[str]:
    """Execute a behavior using the configured LLM."""
    messages: list[ChatCompletionMessageParam] = []

    if system_prompt := self.prompts.get("system"):
      messages.append(
        {"role": "system", "content": system_prompt}
      )

    # Convert history messages to proper format
    if history := message.context.get("history", []):
      for msg in history:
        messages.append(
          {
            "role": str(msg.get("role")),  # type: ignore
            "content": str(msg.get("content")),
          }
        )

    # Add current message
    content = (
      message.content.text
      if hasattr(message.content, "text")
      else str(message.content)
    )
    messages.append(
      {"role": "user", "content": content}
    )

    completion_params: dict[str, Any] = {
      "model": behavior.model.value,
      "messages": messages,
      "temperature": behavior.temperature,
      "stream": behavior.stream,
    }

    # Add tools if configured for this behavior
    if behavior.tool_ids:
      tool_registry = ToolRegistry()
      tools: list[Tool] = []
      for tool_id in behavior.tool_ids:
        tool = tool_registry.get_tool(tool_id)
        if tool is None:
          raise ValueError(
            f"Tool with ID '{tool_id}' not found in the tool registry"
          )
        tools.append(tool)

      functions = [
        {
          "name": tool.name,
          "description": tool.description,
          "parameters": {
            "type": "object",
            "properties": {
              name: {
                "type": param.type,
                "description": param.description,
                **(
                  {"enum": param.enum}
                  if param.enum
                  else {}
                ),
              }
              for name, param in tool.parameters.properties.items()
            },
            "required": tool.parameters.required,
          },
        }
        for tool in tools
      ]
      completion_params["functions"] = functions

    try:
      response = await acompletion(**completion_params)

      if behavior.stream:
        current_function_call: (
          dict[str, str] | None
        ) = None
        accumulated_content = ""

        async for chunk in response:
          if (
            not hasattr(chunk, "choices")
            or not chunk.choices
          ):
            continue

          delta = chunk.choices[0].delta
          if not delta:
            continue

          # Handle function calls
          if (
            hasattr(delta, "function_call")
            and delta.function_call
          ):
            if current_function_call is None:
              current_function_call = {
                "name": delta.function_call.name,
                "arguments": "",
              }
            if hasattr(
              delta.function_call, "arguments"
            ):
              current_function_call["arguments"] += (
                delta.function_call.arguments or ""
              )

          # Handle function call completion
          if (
            hasattr(chunk.choices[0], "finish_reason")
            and chunk.choices[0].finish_reason
            == "function_call"
            and current_function_call
          ):
            result = await self._handle_function_call(
              behavior,
              current_function_call["name"],
              current_function_call["arguments"],
            )
            yield result
            return

          # Handle content
          if (
            hasattr(delta, "content")
            and delta.content is not None
          ):
            accumulated_content += delta.content
            yield delta.content

        if accumulated_content:
          self.state.last_response = (
            accumulated_content
          )

      else:
        # Handle non-streaming response
        if (
          hasattr(response, "choices")
          and response.choices
          and hasattr(response.choices[0], "message")
          and response.choices[0].message
          and hasattr(
            response.choices[0].message, "content"
          )
        ):
          content = response.choices[0].message.content
          if content is not None:
            self.state.last_response = content
            yield content

    except Exception as e:
      error_msg = f"Error executing behavior: {str(e)}"
      self.state.last_error = error_msg
      yield error_msg

  async def emit_event(
    self,
    event_type: str,
    data: dict[str, Any],
  ) -> None:
    """Emit system events for monitoring and coordination."""
    message = Message(
      sender_id=self.id,
      recipient_id="system",
      type=CommunicationType.EVENT,
      content=MessageContent(
        text=f"Event: {event_type}"
      ),
    )
    async for _ in self.handle_message(message):
      pass

  async def handle_message(
    self,
    message: Message,
  ) -> AsyncIterator[str]:
    """Main entry point for message handling."""
    behavior_name = (
      "conversation"
      if message.type == CommunicationType.CONVERSATION
      else message.type.value
    )

    behavior = self.behaviors.get(behavior_name)
    if not behavior:
      yield (
        f"No behavior found for message type: {message.type}. "
        f"Available behaviors: {list(self.behaviors.keys())}"
      )
      return

    async for response in self._execute_behavior(
      behavior, message
    ):
      yield response


class AgentRegistry:
  """
  Central registry for agent discovery and management.

  This class provides functionality to register agents, retrieve agents by ID,
  and find agents based on their capabilities.

  Attributes:
      agents: A dictionary mapping agent IDs to Agent instances.
      capability_index: A dictionary mapping capabilities to sets of agent IDs.
  """

  def __init__(self) -> None:
    self.agents: dict[str, Agent] = {}
    self.capability_index: dict[str, set[str]] = {}

  async def register(self, agent: Agent) -> None:
    """
    Register an agent in the registry.

    This method adds the agent to the main registry and updates the capability index.

    Parameters
    ----------
    agent : Agent
        The agent to be registered.

    Returns
    -------
    None
    """
    self.agents[agent.id] = agent
    for capability in agent.capabilities:
      if capability not in self.capability_index:
        self.capability_index[capability] = set()
      self.capability_index[capability].add(agent.id)

  async def get_agent(
    self, agent_id: str
  ) -> Agent | None:
    """
    Retrieve an agent by its ID.

    Parameters
    ----------
    agent_id : str
        The ID of the agent to retrieve.

    Returns
    -------
    Agent | None
        The agent with the specified ID, or None if not found.
    """
    return self.agents.get(agent_id)

  async def find_agents_by_capability(
    self, capability: str
  ) -> list[Agent]:
    """
    Find agents that have a specific capability.

    Parameters
    ----------
    capability : str
        The capability to search for.

    Returns
    -------
    list[Agent]
        A list of agents that have the specified capability.
    """
    agent_ids = self.capability_index.get(
      capability, set()
    )
    return [self.agents[aid] for aid in agent_ids]
