"""Winston with cognitive workspace and multi-modal capabilities."""

from collections.abc import AsyncIterator
from pathlib import Path

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
      system.get_workspace_manager(
        agent_id=self.id,
      )
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process an incoming message."""
    # First update workspace with new information
    updated_workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Handle image analysis if present
    if "image_path" in message.metadata:
      # Accumulate the complete vision response
      accumulated_content = []
      async for (
        response
      ) in self.generate_streaming_vision_response(
        message.content,
        message.metadata["image_path"],
      ):
        accumulated_content.append(response.content)
        yield response

      # Update workspace once with complete vision observation
      if accumulated_content:
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={"type": "Visual Observation"},
          ),
          self,
        )
      return

    # Otherwise generate normal response using workspace context
    response_prompt = f"""
            Given this user message:
            {message.content}

            And your cognitive workspace:
            {updated_workspace}

            Provide a response that:
            1. Demonstrates awareness of previous interactions
            2. Shows understanding of user preferences
            3. Maintains conversation context
            4. Is helpful and engaging
            """

    async for response in super().process(
      Message(
        content=response_prompt,
        metadata={"workspace": updated_workspace},
      )
    ):
      yield response


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
