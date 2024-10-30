"""Winston with cognitive workspace and reasoning capabilities."""

from pathlib import Path
from typing import AsyncIterator

from winston.core.agent import AgentConfig, BaseAgent
from winston.core.messages import Message, Response
from winston.core.paths import AgentPaths
from winston.core.protocols import Agent, System
from winston.ui.chainlit_app import AgentChat


class ReasoningWinston(BaseAgent):
  """Winston with memory and reasoning capabilities."""

  @classmethod
  def can_handle(cls, message: Message) -> bool:
    """Check if this agent can handle the message."""
    return any(
      trigger in message.content.lower()
      for trigger in [
        "analyze",
        "understand",
        "explain why",
        "what's causing",
        "help me understand",
        "struggling with",
        "having trouble",
      ]
    )

  async def process(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    """Process message using private and optionally shared context."""
    print(
      f"ReasoningWinston processing: {message.content}"
    )

    if not self.can_handle(message):
      return

    private_workspace, shared_workspace = (
      self._get_workspaces(message)
    )
    print("Got private workspace")

    shared_context = ""
    if shared_workspace:
      shared_context = f"""
      And considering the shared context:
      {shared_workspace}
      """

    # Generate analysis using all available context
    response_prompt = f"""
      Analyze this situation:
      {message.content}

      Using your private context:
      {private_workspace}

      {shared_context}

      Develop a comprehensive analysis that:
      1. Identifies key elements and relationships
      2. Draws on relevant private and shared context
      3. Provides clear insights and conclusions
    """

    # Stream responses and accumulate content
    accumulated_content: list[str] = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=response_prompt,
        metadata={"type": "Reasoning Analysis"},
      )
    ):
      accumulated_content.append(response.content)
      yield response

    # After processing, update workspace(s)
    if not accumulated_content:
      return

    complete_analysis = "".join(accumulated_content)

    await self._update_workspaces(
      Message(
        content=complete_analysis,
        metadata={
          **message.metadata,
          "type": "Reasoning Analysis",
        },
      ),
    )


class ReasoningWinstonChat(AgentChat):
  """Chat interface for reasoning Winston."""

  def __init__(self) -> None:
    # Set up paths relative to this file's location
    self.paths = AgentPaths(root=Path(__file__).parent)
    super().__init__()

  def create_agent(self, system: System) -> Agent:
    config = AgentConfig.from_yaml(
      self.paths.config / "agents/winston_reason.yaml"
    )
    return ReasoningWinston(
      system=system,
      config=config,
      paths=self.paths,
    )


# Create the application
app = ReasoningWinstonChat()
