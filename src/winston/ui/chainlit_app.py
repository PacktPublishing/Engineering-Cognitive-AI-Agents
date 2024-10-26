# src/winston/ui/chainlit_app.py
from typing import cast

import chainlit as cl

from winston.agents.base import (
  Agent,
  AgentConfig,
)
from winston.core.messages import (
  CommunicationType,
  Message,
  MessageContent,
)
from winston.core.registry import (
  AgentRegistry,  # Fix the import
)


class AgentChat:
  """Chainlit-based chat interface for an agent."""

  def __init__(self) -> None:
    """
    Initialize AgentChat with registry and register Chainlit handlers.
    """
    self.registry = AgentRegistry()

    # Register class methods as Chainlit handlers
    cl.on_chat_start(self.start)
    cl.on_message(self.handle_message)

  async def start(self) -> None:
    """
    Initialize the chat session.

    Creates and registers an agent instance and initializes the chat history.
    """
    config = self.load_config()
    agent = Agent(config)
    await self.registry.register(agent)

    # Store registry and agent_id in session
    cl.user_session.set("registry", self.registry)  # type: ignore
    cl.user_session.set("agent_id", config.id)  # type: ignore
    cl.user_session.set("history", [])  # type: ignore

  async def handle_message(
    self,
    message: cl.Message,
  ) -> None:
    """
    Handle incoming chat messages.

    Parameters
    ----------
    message : cl.Message
        The incoming message from the user.

    Raises
    ------
    ValueError
        If Winston agent is not found in registry.
    """
    registry: AgentRegistry = cast(
      AgentRegistry,
      cl.user_session.get("registry"),
    )
    agent_id: str = cast(
      str,
      cl.user_session.get("agent_id"),
    )

    agent = await registry.get_agent(agent_id)
    if agent is None:
      raise ValueError(
        f"Agent with id {agent_id} not found"
      )

    # Create streaming message
    msg = cl.Message(content="")
    await msg.send()

    # Get history in proper format
    history = cl.user_session.get("history", [])

    # Create Winston message with proper MessageContent
    winston_message = Message(
      sender_id="user",
      recipient_id=agent.id,
      type=CommunicationType.CONVERSATION,
      content=MessageContent(
        text=message.content
      ),  # Create MessageContent object
      context={"history": history},
    )

    # Stream response
    async for response_chunk in agent.handle_message(
      winston_message
    ):
      await msg.stream_token(response_chunk)

    # Update message
    await msg.update()

    # Update history
    history: list[dict[str, str]] = cast(
      list[dict[str, str]],
      cl.user_session.get("history", []),  # type: ignore
    )
    history.extend(
      [
        {"role": "user", "content": message.content},
        {"role": "assistant", "content": msg.content},
      ]
    )
    cl.user_session.set("history", history)  # type: ignore

  def load_config(self) -> AgentConfig:
    """
    Load agent configuration.

    Returns
    -------
    AgentConfig
        Configuration for the agent.
    """
    raise NotImplementedError(
      "Subclasses must implement load_config method"
    )
