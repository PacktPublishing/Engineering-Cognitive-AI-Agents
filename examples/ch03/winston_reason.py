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
    """Do initial analysis in private workspace."""
    print(
      f"ReasoningWinston processing: {message.content}"
    )

    # Check if analysis needed
    needs_analysis = any(
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

    if not needs_analysis:
      return

    # Do private analysis
    analysis_prompt = f"""
      Analyze privately:
      {message.content}

      Current private context:
      {workspace}

      Develop initial analysis focusing on:
      1. Key elements and relationships
      2. Initial insights
      3. Areas needing deeper investigation
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=analysis_prompt,
        metadata={"type": "Private Analysis"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield (
        workspace,
        response,
      )  # Stream response with current workspace

    # After processing, update private workspace with complete analysis
    if accumulated_content:
      updated_workspace = (
        await self.workspace_manager.update_workspace(
          Message(
            content="".join(accumulated_content),
            metadata={"type": "Private Analysis"},
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
    """Refine analysis using shared context."""
    shared_prompt = f"""
      Given your private analysis:
      {private_workspace}

      And the shared context:
      {shared_workspace}

      Develop a comprehensive analysis that:
      1. Integrates private insights with shared context
      2. Provides clear, actionable conclusions
      3. Highlights relevant connections
    """

    # Stream responses and accumulate content
    accumulated_content = []

    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=shared_prompt,
        metadata={"type": "Shared Analysis"},
      )
    ):
      accumulated_content.append(
        response.content
      )  # Accumulate text
      yield response  # Stream to UI

    # After processing, update shared workspace with complete analysis
    if accumulated_content:
      await self.workspace_manager.update_workspace(
        Message(
          content="".join(accumulated_content),
          metadata={"type": "Shared Analysis"},
        ),
        self,
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
