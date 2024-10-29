"""Central system managing agent communication and tools."""

from typing import Any, AsyncIterator

from winston.core.messages import Message, Response
from winston.core.protocols import (
  Agent,
  MessagePattern,
  System,
)
from winston.core.tools import Tool
from winston.core.workspace import WorkspaceManager


class AgentSystem(System):
  """Central system managing agent communication and tools."""

  def __init__(self) -> None:
    self._agents: dict[str, Agent] = {}
    self._event_subscribers: dict[str, set[str]] = {}
    self._tools: dict[str, Tool[Any]] = {}
    self._agent_tools: dict[str, set[str]] = {}
    self._workspaces: dict[str, WorkspaceManager] = {}

  #
  # Agent management
  #

  def register_agent(
    self,
    agent: Agent,
    subscribed_events: list[str] | None = None,
  ) -> None:
    """
    Register an agent with its capabilities.

    Parameters
    ----------
    agent_id : str
        Unique identifier for the agent.
    agent : Agent
        The agent instance to register.
    subscribed_events : list[str] | None
        Events the agent should subscribe to.
    """
    self._agents[agent.id] = agent

    if subscribed_events:
      for event in subscribed_events:
        if event not in self._event_subscribers:
          self._event_subscribers[event] = set()
        self._event_subscribers[event].add(agent.id)

  #
  # Tools
  #

  def register_tool(self, tool: Tool[Any]) -> None:
    """
    Register a tool globally.

    Parameters
    ----------
    tool : Tool
        The tool to register.
    """
    self._tools[tool.name] = tool

  def grant_tool_access(
    self, agent_id: str, tool_names: list[str]
  ) -> None:
    """
    Grant an agent access to specific tools.

    Parameters
    ----------
    agent_id : str
        The agent to grant access to.
    tool_names : list[str]
        Names of tools to grant access to.
    """
    if agent_id not in self._agent_tools:
      self._agent_tools[agent_id] = set()
    self._agent_tools[agent_id].update(tool_names)

  def get_agent_tools(
    self, agent_id: str
  ) -> dict[str, Tool[Any]]:
    """
    Get all tools available to an agent.

    Parameters
    ----------
    agent_id : str
        ID of the agent.

    Returns
    -------
    dict[str, Tool]
        Dictionary of tool name to tool instance.
    """
    allowed_tools = self._agent_tools.get(
      agent_id, set()
    )
    return {
      name: tool
      for name, tool in self._tools.items()
      if name in allowed_tools
    }

  #
  # Message routing
  #

  async def route_message(
    self,
    recipient_id: str,
    message: Message,
  ) -> AsyncIterator[Response]:
    """
    Route a message to an agent.

    Parameters
    ----------
    recipient_id : str
        ID of the recipient agent.
    message : Message
        Message to route.

    Yields
    ------
    Response
        Responses from the agent.

    Raises
    ------
    ValueError
        If the recipient agent is not found.
    """
    agent = self._agents.get(recipient_id)
    if not agent:
      raise ValueError(
        f"Agent {recipient_id} not found"
      )

    async for response in agent.process(message):
      yield response

  #
  # Conversation handling
  #

  async def invoke_conversation(
    self,
    agent_id: str,
    content: str,
    context: dict[str, Any] | None = None,
  ) -> AsyncIterator[Response]:
    """Handle conversational pattern.

    Parameters
    ----------
    agent_id : str
        ID of the agent to converse with
    content : str
        The conversation content
    context : dict[str, Any] | None, optional
        Additional metadata for the conversation, by default None

    Yields
    ------
    Response
        Responses from the agent
    """
    metadata = {
      "pattern": MessagePattern.CONVERSATION,
    }
    # Merge any additional metadata from context
    if context:
      metadata.update(context)

    message = Message(
      content=content,
      metadata=metadata,
    )

    async for response in self.route_message(
      agent_id, message
    ):
      yield response

  #
  # Function handling
  #

  async def invoke_function(
    self,
    agent_id: str,
    function_name: str,
    args: dict[str, Any],
  ) -> Response:
    """
    Handle function call pattern.

    Parameters
    ----------
    agent_id : str
        ID of the agent to invoke.
    function_name : str
        Name of the function to call.
    args : dict[str, Any]
        Arguments for the function.

    Returns
    -------
    Response
        The function response.

    Raises
    ------
    ValueError
        If the agent doesn't have access to the tool.
    RuntimeError
        If no response is received.
    """
    agent_tools = self.get_agent_tools(agent_id)
    if function_name not in agent_tools:
      raise ValueError(
        f"Agent {agent_id} does not have access to tool {function_name}"
      )

    tool = agent_tools[function_name]
    message = Message(
      content={
        "function": function_name,
        "args": args,
      },
      metadata={
        "pattern": MessagePattern.FUNCTION,
        "schema": tool.parameters,
      },
    )

    async for response in self.route_message(
      agent_id, message
    ):
      return response
    raise RuntimeError("No response received")

  #
  # Event handling
  #

  async def emit_event(
    self,
    event_type: str,
    data: Any,
  ) -> None:
    """
    Handle event pattern.

    Parameters
    ----------
    event_type : str
        Type of event to emit.
    data : Any
        Event data.
    """
    subscribers = self._event_subscribers.get(
      event_type, set()
    )
    for agent_id in subscribers:
      message = Message(
        content=data,
        metadata={
          "pattern": MessagePattern.EVENT,
          "event_type": event_type,
        },
      )
      async for _ in self.route_message(
        agent_id, message
      ):
        pass

  #
  # Workspace management
  #

  def get_workspace_manager(
    self,
    agent_id: str,
  ) -> WorkspaceManager:
    """Get workspace manager for an agent.

    Parameters
    ----------
    agent_id : str
        ID of the agent

    Returns
    -------
    WorkspaceManager
        Workspace manager for the agent
    """
    if agent_id not in self._workspaces:
      agent = self._agents.get(agent_id)
      if not agent:
        raise ValueError(f"Agent {agent_id} not found")

      workspace_path = (
        agent.paths.workspaces / f"{agent_id}.md"
      )
      workspace_path.parent.mkdir(
        parents=True, exist_ok=True
      )
      self._workspaces[agent_id] = WorkspaceManager(
        workspace_path
      )
    return self._workspaces[agent_id]
