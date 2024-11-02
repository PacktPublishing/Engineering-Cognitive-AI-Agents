"""Winston with cognitive workspace and basic memory capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class HumanWinston(BaseAgent):
  """Winston with basic cognitive capabilities."""

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process message in private memory workspace."""
    print(
      f"HumanWinston processing: {message.content}"
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

    Your goal is to create a complete cognitive behavioral profile of the user.  Engage in creative roleplay, ask hypothetical questions, make compelling claims designed to generate a response that allows you to gain insight on the user.  Carefully consider the the existing profile and prioritize traits you'd like to better understand.

    Always respond in two parts:
    1. A short response to the user
    2. Your inner monologue explaining what you're doing.  (The user won't see this part)
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


class HumanWinstonChat(AgentChat):
  """Chat interface for cognitive Winston."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston_human.yaml"
    )
    return HumanWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = HumanWinstonChat()
