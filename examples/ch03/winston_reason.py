"""Winston with cognitive workspace and reasoning capabilities."""

from collections.abc import AsyncIterator
from pathlib import Path

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
      system.get_workspace_manager(
        agent_id=self.id,
      )
    )

  async def process(
    self, message: Message
  ) -> AsyncIterator[Response]:
    # Add metadata check to prevent recursion
    if message.metadata.get("type") == "analysis":
      # If this is already an analysis request, process normally
      async for response in super().process(message):
        yield response
      return

    # First update workspace with new information
    updated_workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Detect if this message needs analysis
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

    if needs_analysis:
      # Perform detailed analysis
      async for response in self.analyze_situation(
        message
      ):
        yield response
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
        context={"workspace": updated_workspace},
      )
    ):
      yield response

  async def analyze_situation(
    self,
    message: Message,
  ) -> AsyncIterator[Response]:
    # First update the workspace with the new information
    workspace = (
      await self.workspace_manager.update_workspace(
        message,
        self,
      )
    )

    # Generate analysis using the full context
    analysis_prompt = f"""
        Analyze this situation:
        {message.content}

        Using the context from your workspace:
        {workspace}

        Develop a detailed analysis through these steps:
        1. Identify key elements and relationships
        2. Connect with relevant past experiences
        3. Consider implications and consequences
        4. Refine initial insights

        Structure your analysis clearly in markdown format.
        """

    # Stream the analysis response
    accumulated_analysis = ""
    async for (
      response
    ) in self.generate_streaming_response(
      Message(
        content=analysis_prompt,
        metadata={"type": "Analysis Request"},
      ),
    ):
      accumulated_analysis += response.content
      yield response

    # Update workspace with the complete analysis
    _ = await self.workspace_manager.update_workspace(
      Message(
        content=accumulated_analysis,
        metadata={"type": "Analysis Result"},
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
