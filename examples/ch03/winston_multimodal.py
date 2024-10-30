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

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)
    self.workspace_manager = (
      system.get_workspace_manager(self.id)
    )

  async def _process_private(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Process visual input in private workspace."""
    if "image_path" not in message.metadata:
      return

    # Generate initial visual description
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_vision_response(
      message.content, message.metadata["image_path"]
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield (
        workspace,
        response,
      )  # Stream response with current workspace

    # After processing, update private workspace with visual observations
    if accumulated_content:
      updated_workspace = (
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={
              "type": "Private Visual Observation"
            },
          ),
          self,
        )
      )
      # Final yield with updated workspace
      yield updated_workspace, Response(content="")

  async def _process_shared(
    self,
    message: Message,
    private_workspace: str,
    shared_workspace: str,
  ) -> AsyncIterator[Response]:
    """Integrate visual observations with shared context."""
    integration_prompt = f"""
    Given your visual observations:
    {private_workspace}

    And the shared cognitive context:
    {shared_workspace}

    Provide an integrated understanding that:
    1. Connects visual elements with context
    2. Highlights relevant relationships
    3. Draws meaningful conclusions
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=integration_prompt,
        metadata={"type": "Visual Integration"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield response  # Stream to UI

    # After processing, update shared workspace with complete integration
    if accumulated_content:
      await self.workspace_manager.update_workspace(
        Message(
          content="".join(accumulated_content),
          metadata={"type": "Visual Integration"},
        ),
        self,
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
