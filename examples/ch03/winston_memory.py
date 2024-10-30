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

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process message in private memory workspace."""
    print(
      f"MemoryWinston processing: {message.content}"
    )

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

    Using your private context:
    {private_workspace}

    {shared_context}

    Generate initial thoughts focusing on:
    1. Personal recollections and experiences
    2. Individual preferences and patterns
    3. Key memory triggers and associations
    """

    # Stream responses and accumulate content
    accumulated_content: list[str] = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=response_prompt,
        metadata={"type": "Memory Processing"},
      )
    ):
      accumulated_content.append(response.content)
      yield response

    # After processing, update workspace(s)
    if not accumulated_content:
      return

    await self._update_workspaces(
      Message(
        content="".join(accumulated_content),
        metadata={
          **message.metadata,
          "type": "Memory Processing",
        },
      ),
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
