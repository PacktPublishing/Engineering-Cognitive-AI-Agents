# src/winston/ui/chainlit_app.py
"""Chainlit integration for generic agent chat interface."""

from typing import cast

import chainlit as cl

from winston.core.messages import Message, Response
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

    # Get history in proper format
    history = cl.user_session.get("history", [])

    # Track if we've created the response message
    msg: cl.Message | None = None
    accumulated_content: list[str] = []
    tool_responses: list[
      str
    ] = []  # Track tool responses

    # Stream response
    async for response in system.invoke_conversation(
      agent_id,
      message.content,
      context={"history": history},
    ):
      if response.metadata.get("tool_call"):
        # Create a tool execution step
        async with cl.Step(
          name=response.metadata["tool_name"],
          type="tool",
          show_input=True,
        ) as step:
          step.input = response.metadata["tool_args"]
          step.output = response.content

          # If there's a formatted response, create a message and track it
          if (
            formatted_response
            := response.metadata.get(
              "formatted_response"
            )
          ):
            tool_responses.append(formatted_response)
            msg = cl.Message(
              content=formatted_response
            )
            await msg.send()
      else:
        # Create message if this is first content
        if msg is None:
          msg = cl.Message(content="")
          await msg.send()

        accumulated_content.append(response.content)
        await msg.stream_token(response.content)

    # Update final message if we created one
    if msg is not None:
      await msg.update()

    # Update history with both user message and response
    history = cast(
      list[dict[str, str]],
      cl.user_session.get("history", []),
    )

    user_message = Message(content=message.content)
    # Include tool responses in the assistant's message if any
    assistant_content = (
      " ".join(tool_responses)
      if tool_responses
      else "".join(accumulated_content)
    )
    assistant_message = Response(
      content=assistant_content
    )

    history.extend(
      [
        user_message.to_history_format(),
        assistant_message.to_history_format(),
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
