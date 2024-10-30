"""Winston with cognitive workspace and basic memory capabilities."""

from pathlib import Path
from typing import AsyncIterator

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
    self.workspace_manager = (
      system.get_workspace_manager(self.id)
    )

  async def _process_private(
    self,
    message: Message,
    workspace: str,
  ) -> AsyncIterator[tuple[str, Response]]:
    """Process message in private memory workspace."""
    print(
      f"MemoryWinston processing: {message.content}"
    )

    # Generate initial memory-focused response
    memory_prompt = f"""
    Given this message:
    {message.content}

    And your private memory context:
    {workspace}

    Generate initial thoughts focusing on:
    1. Personal recollections and experiences
    2. Individual preferences and patterns
    3. Key memory triggers and associations
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=memory_prompt,
        metadata={"type": "Private Memory Processing"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield (
        workspace,
        response,
      )  # Stream response with current workspace

    # After processing, update private workspace with complete memory
    if accumulated_content:
      updated_workspace = (
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={
              "type": "Private Memory Processing"
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
    """Integrate private memories with shared context."""
    integration_prompt = f"""
    Given your private recollections:
    {private_workspace}

    And the shared cognitive context:
    {shared_workspace}

    Provide a response that:
    1. Integrates personal and shared memories
    2. Shows understanding of collective context
    3. Maintains conversational relevance
    4. Is helpful and engaging
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=integration_prompt,
        metadata={"type": "Memory Integration"},
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
          metadata={"type": "Memory Integration"},
        ),
        self,
      )


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
