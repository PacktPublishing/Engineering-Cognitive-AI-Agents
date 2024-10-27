# src/winston/ui/chainlit_app.py
"""Chainlit integration for generic agent chat interface."""

from typing import cast

import chainlit as cl

from winston.core.protocols import Agent, System
from winston.core.system import AgentSystem


class AgentChat:
  """Generic Chainlit-based chat interface for any agent."""

  def __init__(self) -> None:
    """
    Initialize AgentChat with system and register Chainlit handlers.
    """
    self.system = AgentSystem()

    # Register class methods as Chainlit handlers
    cl.on_chat_start(self.start)
    cl.on_message(self.handle_message)

  async def start(self) -> None:
    """
    Initialize the chat session.

    Creates and registers an agent instance and initializes the chat history.
    """
    agent = self.create_agent(self.system)
    self.system.register_agent(agent)

    # Store system and agent_id in session
    cl.user_session.set("system", self.system)  # type: ignore
    cl.user_session.set("agent_id", agent.id)  # type: ignore
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
        If agent is not found in system.
    """
    system: AgentSystem = cast(
      AgentSystem,
      cl.user_session.get("system"),
    )
    agent_id: str = cast(
      str,
      cl.user_session.get("agent_id"),
    )

    # Create streaming message
    msg = cl.Message(content="")
    await msg.send()

    # Get history in proper format
    history = cl.user_session.get("history", [])

    # Stream response
    async for response in system.invoke_conversation(
      agent_id,
      message.content,
      context={"history": history},
    ):
      await msg.stream_token(response.content)

    # Update message
    await msg.update()

    # Update history
    history = cast(
      list[dict[str, str]],
      cl.user_session.get("history", []),
    )
    history.extend(
      [
        {"role": "user", "content": message.content},
        {"role": "assistant", "content": msg.content},
      ]
    )
    cl.user_session.set("history", history)  # type: ignore

  def create_agent(
    self,
    system: System,
  ) -> Agent:
    """
    Create the agent instance.

    Returns
    -------
    Agent
        The agent instance to use for chat.

    Raises
    ------
    NotImplementedError
        This method must be implemented by subclasses.
    """
    raise NotImplementedError(
      "Subclasses must implement create_agent method"
    )
