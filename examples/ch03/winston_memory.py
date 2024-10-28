"""Winston with cognitive workspace and basic memory capabilities."""

from collections.abc import AsyncIterator
from pathlib import Path

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class MemoryWinston(BaseAgent):
  """Winston with basic cognitive capabilities."""

  def __init__(
    self,
    system: System,
    config: AgentConfig,
    paths: AgentPaths,
  ) -> None:
    super().__init__(system, config, paths)

    # Get workspace manager from system - no need to pass workspace_root
    self.workspace_manager = (
      system.get_workspace_manager(
        agent_id=self.id,
      )
    )

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    # Update workspace using the workspace manager
    updated_workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Generate response using workspace context
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
        context={"workspace": updated_workspace},
      )
    ):
      yield response


class MemoryWinstonChat(AgentChat):
  """Chat interface for cognitive Winston."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston_memory.yaml"
    )
    return MemoryWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = MemoryWinstonChat()
