"""Winston with cognitive workspace and multi-modal capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class MultimodalWinston(BaseAgent):
  """Winston with multi-modal cognitive capabilities."""

  @classmethod
  def can_handle(cls, message: Message) -> bool:
    """Check if this agent can handle the message."""
    return "image_path" in message.metadata

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process an incoming message."""
    # Handle image analysis if present
    if not self.can_handle(message):
      return

    # Accumulate the complete vision response
    accumulated_content: list[str] = []
    async for (
      response
    ) in self.generate_streaming_vision_response(
      message.content,
      message.metadata["image_path"],
    ):
      accumulated_content.append(response.content)
      yield response

    # Update workspace once with complete vision observation
    if not accumulated_content:
      return

    private_workspace, shared_workspace = (
      self._get_workspaces(message)
    )

    shared_context = ""
    if shared_workspace:
      shared_context = f"""
      And considering the shared context:
      {shared_workspace}
      """

    # Generate initial memory-focused response
    response_prompt = f"""
    Given this message:
    {message.content}

    And the visual observation:
    {accumulated_content}

    Using your private context:
    {private_workspace}
    {shared_context}

    Generate initial thoughts focusing on:
    1. Personal recollections and experiences
    2. Individual preferences and patterns
    3. Key memory triggers and associations
    """

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=response_prompt,
        metadata={"type": "Visual Observation"},
      )
    ):
      accumulated_content.append(response.content)
      yield response

    if not accumulated_content:
      return

    await self._update_workspaces(
      Message(
        content="".join(accumulated_content),
        metadata={
          **message.metadata,
          "type": "Visual Observation",
        },
      ),
    )


class MultimodalWinstonChat(AgentChat):
  """Chat interface for multi-modal Winston."""

  def __init__(self) -> None:
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config
      / "agents/winston_multimodal.yaml",
    )
    return MultimodalWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = MultimodalWinstonChat()
